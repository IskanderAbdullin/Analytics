#!/usr/bin/env python3
"""Conservative realized-fill attribution to OBSERVED log configuration epochs.

This is an accounting study, NOT a causal strategy comparison: a trade can
execute after the order was created under an earlier regime, and open inventory
P&L, broker fees/funding and slippage may be missing.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from config_epochs import LINE, reconstruct
from report_safety import validate_report_output

FIELDS = ("group_id", "epoch_start_msk", "epoch_end_msk", "event_kind",
          "confidence", "settings_digest", "regime", "buy_min_level_lots",
          "sell_min_level_lots", "max_position_lots", "fills",
          "buy_lots", "sell_lots", "close_fills", "synthetic_fills",
          "gross_realized", "fee_estimate", "net_realized_after_estimated_fees",
          "first_fill_msk", "last_fill_msk", "note")
QUALITY = ("kind", "count")


def decimal(raw):
    value = Decimal(str(raw))
    if not value.is_finite():
        raise InvalidOperation("non-finite accounting field")
    return value


def tail_log_time(folder: Path):
    """Last observable log event, not an assertion of uninterrupted operation."""
    latest = None
    for path in sorted(folder.glob("*.log")):
        if not path.is_file():
            continue
        with path.open("r", encoding="utf-8-sig", errors="replace") as stream:
            for line in stream:
                match = LINE.match(line)
                if match is not None:
                    stamp = datetime.fromisoformat(match.group(1))
                    latest = max(latest, stamp) if latest else stamp
    return latest


def run_analysis(root: Path, state: str, logs: str) -> tuple[list[dict], dict]:
    root = root.resolve(strict=True)
    for value, prefix in ((state, "state"), (logs, "logs")):
        if not re.fullmatch(rf"{prefix}[\w.-]*", value) or "/" in value or "\\" in value:
            raise ValueError("state/log path must be a simple scoped folder name")
    state_dir = (root / state).resolve()
    log_dir = (root / logs).resolve()
    if (not state_dir.is_dir() or not log_dir.is_dir() or
            not state_dir.is_relative_to(root) or not log_dir.is_relative_to(root)):
        raise ValueError("state or logs missing / outside the selected copy")
    source = state_dir / "fills.csv"
    if not source.is_file():
        raise ValueError("no fills.csv in selected state")
    epochs, notices = reconstruct(log_dir)
    starts = [datetime.fromisoformat(e["start_msk"]) for e in epochs]
    end_of_evidence = tail_log_time(log_dir)
    buckets = defaultdict(lambda: dict(
        fills=0, buy_lots=0, sell_lots=0, close_fills=0, synthetic_fills=0,
        gross_realized=Decimal(0), fee_estimate=Decimal(0),
        first_fill_msk="", last_fill_msk=""
    ))
    rejected = defaultdict(int)
    dedup = set()
    with source.open("r", encoding="utf-8-sig", errors="replace", newline="") as stream:
        reader = csv.DictReader(stream, delimiter=";")
        required = {"time_msk", "trade_id", "side", "kind", "lots", "realized", "fee_estimate"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("incomplete fills.csv header")
        for row in reader:
            try:
                if not row.get("time_msk"):
                    rejected["incomplete_fill_row"] += 1
                    continue
                when = datetime.fromisoformat(row["time_msk"].replace(" ", "T"))
                if when.tzinfo is not None:
                    raise ValueError("fill must use naive Moscow time")
                side = row["side"]
                lots = int(row["lots"])
                realized = decimal(row["realized"])
                fee = decimal(row["fee_estimate"])
                if side not in ("Buy", "Sell") or lots <= 0:
                    raise ValueError("invalid lot count/side")
                key = (row.get("exchange_id", ""), row.get("trade_id", ""))
                if key[1] and key in dedup:
                    rejected["duplicate_fill"] += 1
                    continue
                if key[1]:
                    dedup.add(key)
                # For equal timestamps we cannot establish which event came first.
                i = bisect.bisect_left(starts, when) - 1
                if i < 0:
                    group = "unknown_before_first_setting"
                elif epochs[i]["end_msk"] and when >= datetime.fromisoformat(epochs[i]["end_msk"]):
                    group = "unknown_after_observed_stop"
                elif end_of_evidence is None or when > end_of_evidence:
                    group = "unknown_after_last_log_event"
                else:
                    group = "epoch_" + str(i)
                stats = buckets[group]
                stats["fills"] += 1
                stats["buy_lots"] += lots if side == "Buy" else 0
                stats["sell_lots"] += lots if side == "Sell" else 0
                stats["close_fills"] += int(row.get("kind") == "close")
                stats["synthetic_fills"] += int(row.get("synthetic") == "1")
                stats["gross_realized"] += realized
                stats["fee_estimate"] += fee
                stamp = row["time_msk"]
                if not stats["first_fill_msk"] or stamp < stats["first_fill_msk"]:
                    stats["first_fill_msk"] = stamp
                if stamp > stats["last_fill_msk"]:
                    stats["last_fill_msk"] = stamp
            except (ValueError, InvalidOperation, TypeError, KeyError, OverflowError):
                rejected["invalid_numeric_or_timestamp"] += 1
    results = []
    for key, stat in sorted(buckets.items()):
        if key.startswith("epoch_"):
            source_epoch = epochs[int(key[6:])]
            desc = {
                "epoch_start_msk": source_epoch["start_msk"],
                "epoch_end_msk": source_epoch["end_msk"],
                "event_kind": source_epoch["event_kind"],
                "confidence": source_epoch["confidence"],
                "settings_digest": source_epoch["settings_digest"],
                "regime": source_epoch["regime"],
                "buy_min_level_lots": source_epoch["buy_min_level_lots"],
                "sell_min_level_lots": source_epoch["sell_min_level_lots"],
                "max_position_lots": source_epoch["max_position_lots"],
            }
            warning = "Booked while observed log settings were effective; order may have been created earlier."
        else:
            desc = {name: "" for name in ("epoch_start_msk", "epoch_end_msk", "event_kind", "confidence",
                                         "settings_digest", "regime", "buy_min_level_lots",
                                         "sell_min_level_lots", "max_position_lots")}
            warning = "UNKNOWN: execution has no verified active configuration evidence."
        results.append(dict(
            group_id=key, **desc,
            fills=stat["fills"], buy_lots=stat["buy_lots"], sell_lots=stat["sell_lots"],
            close_fills=stat["close_fills"], synthetic_fills=stat["synthetic_fills"],
            gross_realized=str(stat["gross_realized"]),
            fee_estimate=str(stat["fee_estimate"]),
            net_realized_after_estimated_fees=str(stat["gross_realized"] - stat["fee_estimate"]),
            first_fill_msk=stat["first_fill_msk"], last_fill_msk=stat["last_fill_msk"],
            note=warning,
        ))
    summary = dict(state=state, logs=logs, total_fills=sum(x["fills"] for x in results),
                   setting_epochs=len(epochs), observed_log_end_msk=str(end_of_evidence) if end_of_evidence else "",
                   unknown_fills=sum(x["fills"] for x in results if x["group_id"].startswith("unknown")),
                   rejected=dict(rejected), config_notices=len(notices),
                   limitations=[
                       "State-to-log identity is supplied by the operator and not proven by historical config.",
                       "Booked realized P&L is NOT strategy P&L: mark-to-market, carry and broker fees may be omitted.",
                       "An execution can belong to an order CREATED under a prior epoch.",
                       "Missing logs, changes at equal timestamps and observed stops produce UNKNOWN time buckets.",
                       "A local execution ledger cannot prove broker-side positions and commissions.",
                   ])
    return results, summary


def run(root: Path, output: Path, state: str, logs: str) -> dict:
    root, output = validate_report_output(root, output)
    rows, summary = run_analysis(root, state, logs)
    output.mkdir(parents=True, exist_ok=False)
    with (output / "booked_fills_by_epoch.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    with (output / "invalid_fills.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=QUALITY)
        writer.writeheader()
        writer.writerows([dict(kind=key, count=value) for key, value in summary["rejected"].items()])
    (output / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--state", required=True, help="state* directory within copy")
    parser.add_argument("--logs", required=True, help="logs* directory within copy")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        result = run(root, args.output or root / "reports" / "booked-epoch-pnl",
                     args.state, args.logs)
    except (ValueError, OSError, InvalidOperation) as error:
        print("Per-epoch attribution refused:", error, file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
