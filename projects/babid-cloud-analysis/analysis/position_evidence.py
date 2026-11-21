#!/usr/bin/env python3
"""Correlate logged broker/journal position deltas with local fill net changes.

A difference is EVIDENCE TO INVESTIGATE, not proof of a manual trade or a
lost broker execution. All files are read-only and all joins are timestamped.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import json
import re
import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from config_epochs import LINE
from report_safety import validate_report_output

BROKER = re.compile(r"\bbroker\s+([+-]?\d+(?:\.\d+)?),\s*journal\s+([+-]?\d+(?:\.\d+)?)", re.I)
BASELINE = re.compile(
    r"Broker position:\s*([+-]?\d+(?:\.\d+)?)\s+lots;\s*"
    r"robot journal:\s*([+-]?\d+(?:\.\d+)?)\s+lots;\s*"
    r"outside the robot:\s*([+-]?\d+(?:\.\d+)?)\s+lots", re.I
)
CHANGED = re.compile(r"position outside the robot changed from\s+"
                     r"([+-]?\d+(?:\.\d+)?)\s+to\s+([+-]?\d+(?:\.\d+)?)\s+lots", re.I)
RESTART = re.compile(r"position outside the robot was\s+([+-]?\d+(?:\.\d+)?)\s+lots.*?"
                     r"\bis\s+([+-]?\d+(?:\.\d+)?)\s+now", re.I)
OBS_FIELDS = ("at_msk", "kind", "broker_lots", "journal_lots", "external_lots",
              "previous_external_lots", "reported_external_lots",
              "reported_transition_lots", "reported_consistent",
              "source_file", "source_line")
DELTA_FIELDS = (
    "from_msk", "to_msk", "broker_delta_lots", "journal_delta_lots",
    "external_delta_lots", "fill_net_lots_in_window", "fills_in_window",
    "synthetic_fills_in_window", "journal_fill_delta_consistent",
    "position_arithmetic_consistent", "outside_position_changed",
    "sample_trade_ids", "note",
)


def dec(value):
    result = Decimal(str(value))
    if not result.is_finite():
        raise InvalidOperation("non-finite position")
    return result


def observations(folder: Path):
    result = []
    seen = set()
    for file in sorted(folder.glob("*.log")):
        if not file.is_file():
            continue
        with file.open("r", encoding="utf-8-sig", errors="replace") as stream:
            for line_no, line in enumerate(stream, 1):
                match = LINE.match(line.rstrip("\r\n"))
                if not match:
                    continue
                stamp, message = match.groups()
                base = BASELINE.search(message)
                broker_match = BROKER.search(message)
                if base:
                    broker, journal, reported = map(dec, base.groups())
                    kind = "baseline"
                    prev = ""
                elif broker_match:
                    broker, journal = map(dec, broker_match.groups())
                    delta = CHANGED.search(message) or RESTART.search(message)
                    if not delta:
                        continue
                    prev, reported = map(dec, delta.groups())
                    kind = "changed" if CHANGED.search(message) else "restart_comparison"
                else:
                    continue
                external = broker - journal
                # An identical exported notice may repeat, but a baseline and a
                # transition (or different reported 'from' values) are distinct
                # evidence even at the exact same timestamp and position.
                key = (stamp, kind, broker, journal, external, prev, reported)
                if key in seen:
                    continue
                seen.add(key)
                result.append(dict(at_msk=stamp, kind=kind, broker_lots=broker,
                                   journal_lots=journal, external_lots=external,
                                   previous_external_lots=prev,
                                   reported_external_lots=reported,
                                   reported_transition_lots=(reported - prev)
                                       if kind != "baseline" else "",
                                   reported_consistent=(external == reported),
                                   source_file=file.name, source_line=line_no))
    result.sort(key=lambda x: (x["at_msk"], x["source_file"], x["source_line"]))
    return result


def reconcile(root: Path, state: str, logs: str):
    root = root.resolve(strict=True)
    for value, expected in ((state, "state"), (logs, "logs")):
        if not re.fullmatch(rf"{expected}[\w.-]*", value) or "/" in value or "\\" in value:
            raise ValueError("state/log names must be simple scoped folders")
    state_path, log_path = (root / state).resolve(), (root / logs).resolve()
    if (not state_path.is_dir() or not log_path.is_dir() or
            not state_path.is_relative_to(root) or not log_path.is_relative_to(root)):
        raise ValueError("missing or escaping state/log directory")
    execution_file = state_path / "fills.csv"
    if not execution_file.is_file():
        raise ValueError("missing fills.csv")

    positions = observations(log_path)
    intervals = []
    times = [datetime.fromisoformat(r["at_msk"]) for r in positions]
    for prev, current in zip(positions, positions[1:], strict=False):
        d_broker = current["broker_lots"] - prev["broker_lots"]
        d_journal = current["journal_lots"] - prev["journal_lots"]
        d_external = current["external_lots"] - prev["external_lots"]
        intervals.append(dict(
            from_msk=prev["at_msk"], to_msk=current["at_msk"],
            broker_delta_lots=d_broker, journal_delta_lots=d_journal,
            external_delta_lots=d_external, fill_net_lots_in_window=Decimal(0),
            fills_in_window=0, synthetic_fills_in_window=0,
            sample_trade_ids=[], position_arithmetic_consistent=(
                d_broker - d_journal == d_external),
            outside_position_changed=d_external != 0,
            journal_fill_delta_consistent=False,
            note="Broker minus journal changes are observations, not proven causes.",
        ))
    unseen = 0
    bad = 0
    duplicate = 0
    boundary = 0
    seen = set()
    with execution_file.open("r", encoding="utf-8-sig", errors="replace", newline="") as stream:
        reader = csv.DictReader(stream, delimiter=";")
        fields = {"time_msk", "trade_id", "side", "lots", "synthetic"}
        if not reader.fieldnames or not fields.issubset(reader.fieldnames):
            raise ValueError("fills.csv missing columns for position reconciliation")
        for row in reader:
            try:
                if not row.get("time_msk"):
                    bad += 1
                    continue
                at = datetime.fromisoformat(row["time_msk"].replace(" ", "T"))
                if at.tzinfo:
                    raise ValueError("fill time must be Moscow local without offset")
                lots = dec(row["lots"])
                if lots < 1 or lots != lots.to_integral_value() or row["side"] not in ("Buy", "Sell"):
                    raise ValueError("invalid fill lots/side")
                trade = row.get("trade_id", "")
                key = (row.get("exchange_id", ""), trade)
                if trade and key in seen:
                    duplicate += 1
                    continue
                if trade:
                    seen.add(key)
                # Strict inequality avoids attributing a fill at the instant
                # of a position check when ordering within that millisecond is unknown.
                i = bisect.bisect_left(times, at)
                if i < 1 or i >= len(times):
                    unseen += 1
                    continue
                if times[i - 1] == at or times[i] == at:
                    boundary += 1
                    continue
                entry = intervals[i - 1]
                entry["fill_net_lots_in_window"] += lots if row["side"] == "Buy" else -lots
                entry["fills_in_window"] += 1
                entry["synthetic_fills_in_window"] += int(row.get("synthetic") == "1")
                if trade and len(entry["sample_trade_ids"]) < 20:
                    entry["sample_trade_ids"].append(trade)
            except (ValueError, InvalidOperation, TypeError, KeyError, OverflowError):
                bad += 1
    for row in intervals:
        row["journal_fill_delta_consistent"] = (
            row["journal_delta_lots"] == row["fill_net_lots_in_window"])
        row["sample_trade_ids"] = ",".join(row["sample_trade_ids"])
    transition_reports = [p for p in positions
                          if p["kind"] in ("changed", "restart_comparison")
                          and p["reported_transition_lots"] != 0]
    prior_position_disagreements = 0
    for previous, current in zip(positions, positions[1:], strict=False):
        if (current["kind"] != "baseline" and
                current["previous_external_lots"] != previous["external_lots"]):
            prior_position_disagreements += 1
    summary = dict(state=state, logs=logs, observations=len(positions),
                   comparison_intervals=len(intervals),
                   external_changes=sum(x["outside_position_changed"] for x in intervals),
                   reported_external_transitions=len(transition_reports),
                   first_observation_transition_unanchored=bool(
                       positions and positions[0]["kind"] != "baseline"),
                   reported_prior_position_disagreements=prior_position_disagreements,
                   journal_fill_mismatches=sum(not x["journal_fill_delta_consistent"] for x in intervals),
                   inconsistent_observation_arithmetic=sum(not x["reported_consistent"] for x in positions),
                   duplicate_fill_ids=duplicate, invalid_fills=bad,
                   fills_outside_observed_windows=unseen, fills_on_timestamp_boundaries=boundary,
                   limitations=[
                       "A first 'changed from ... to ...' log is a reported transition even without a prior broker snapshot.",
                       "external_changes counts paired observed endpoints; reported_external_transitions counts log notices.",
                       "A mismatch between a logged prior value and an earlier sample may reflect skipped checks or stale responses.",
                       "Broker position samples are sparse and may be stale or delayed.",
                       "Fills use exchange timestamps, logs use robot observation timestamps.",
                       "Net change in external lots does not prove manual trades, missing executions or a software bug.",
                       "Missing fills and duplicate event delivery may invalidate interval completeness.",
                       "This audit does not request broker positions or change trading risk state.",
                   ])
    return positions, intervals, summary


def run(root: Path, output: Path, state: str, logs: str):
    root, output = validate_report_output(root, output)
    positions, intervals, summary = reconcile(root, state, logs)
    output.mkdir(parents=True, exist_ok=False)
    with (output / "broker_journal_observations.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OBS_FIELDS)
        writer.writeheader()
        writer.writerows(positions)
    with (output / "position_deltas.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=DELTA_FIELDS)
        writer.writeheader()
        writer.writerows(intervals)
    (output / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--logs", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        result = run(root, args.output or root / "reports" / "position-evidence",
                     args.state, args.logs)
    except (ValueError, OSError, InvalidOperation) as error:
        print("Position evidence scan refused:", error, file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
