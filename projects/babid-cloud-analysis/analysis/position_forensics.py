#!/usr/bin/env python3
"""Read-only reconstruction of one Babid01 position discrepancy window.

The script correlates order/fill rows with available logs, but preserves
separate source-native event order and clock domains: exchange-reported fill
execution time is not robot log observation/processing time. It does NOT
contact T-Invest, cancel orders, reset risk, or change journal state.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from report_safety import validate_report_output

LOG = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d(?:\.\d+)?)\s+([A-Z]{3})\s+(.*)$")
BROKER = re.compile(r"\(broker\s+([+-]?\d+(?:\.\d+)?),\s+journal\s+([+-]?\d+(?:\.\d+)?)\)")
OUTSIDE = re.compile(r"position outside the robot.*?(?:from\s+([+-]?\d+(?:\.\d+)?)\s+to\s+([+-]?\d+(?:\.\d+)?))", re.I)
RELEVANT = re.compile(r"position|RISK:|Risk manager|FILL|SYNTHETIC|Order \d+:|replac|cancel|reconnect|resync|stream", re.I)


def time_between(value: str, start: str, end: str) -> bool:
    return start <= value[:19] <= end


def output_csv(path: Path, names: list[str], rows: list[dict]):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def examine_fills(source: Path, start: str, end: str,
                  execution_lookback_sec: int = 0):
    """Select ledger fills by *execution* time with an optional prior margin.

    This margin admits an execution earlier than the robot observation window
    that was delivered late. It does not prove when a fill was delivered.
    """
    if not 0 <= execution_lookback_sec <= 86400:
        raise ValueError("execution lookback must be 0..86400 seconds")
    first_execution = (datetime.fromisoformat(start)
                       - timedelta(seconds=execution_lookback_sec)).isoformat(sep=" ")
    rows = []
    duplicates = []
    continuity = []
    seen = set()
    last_net = None
    total_buy = total_sell = 0
    with source.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        if not reader.fieldnames or not {"time_msk", "trade_id", "lots", "net_lots", "side"}.issubset(reader.fieldnames):
            raise ValueError("fills.csv schema does not match Babid01")
        for line_no, row in enumerate(reader, 2):
            if not row.get("time_msk") or not row.get("lots"):
                continue
            key = (row.get("exchange_id", ""), row["trade_id"])
            if key[1]:
                if key in seen:
                    duplicates.append(dict(source="fills.csv", line=line_no,
                                           timestamp=row["time_msk"], anomaly="duplicate exchange/trade key",
                                           detail=row["trade_id"]))
                seen.add(key)
            lots = int(row["lots"])
            side = row["side"]
            sign = 1 if side == "Buy" else -1 if side == "Sell" else 0
            net = int(row["net_lots"])
            # The entire file is replayed to anchor the window's position correctly.
            if last_net is not None and sign and net != last_net + sign * lots:
                continuity.append(dict(source="fills.csv", line=line_no,
                                       timestamp=row["time_msk"], anomaly="non-contiguous net-lots",
                                       detail=f"{last_net} + {sign}*{lots} != {net}"))
            last_net = net
            if not time_between(row["time_msk"], first_execution, end):
                continue
            total_buy += lots if sign == 1 else 0
            total_sell += lots if sign == -1 else 0
            rows.append(dict(timestamp=row["time_msk"], source="fills.csv", level="FILL",
                             category="synthetic" if row.get("synthetic") == "1" else "execution",
                             clock_domain="broker_reported_execution", source_sequence=line_no,
                             execution_lookback=(row["time_msk"][:19] < start[:19]),
                             order=row.get("order", ""), trade_id=row["trade_id"],
                             side=side, lots=lots, net_lots=net,
                             detail=f"price={row.get('price','')}; role={row.get('kind','')}; realized={row.get('realized','')}"))
    return rows, duplicates, continuity, total_buy, total_sell, last_net


def examine_logs(folder: Path, start: str, end: str):
    events = []
    checks = []
    for path in sorted(folder.glob("*.log")):
        with path.open("r", encoding="utf-8-sig", errors="replace") as f:
            for line_no, line in enumerate(f, 1):
                match = LOG.match(line.rstrip("\r\n"))
                if not match:
                    continue
                at, level, message = match.groups()
                if not time_between(at, start, end) or not RELEVANT.search(message):
                    continue
                category = ("position" if "position outside" in message.lower()
                            else "risk" if "RISK:" in message or "Risk manager" in message
                            else "execution" if "FILL " in message
                            else "order" if re.search(r"Order \d+:", message)
                            else "connection" if "stream" in message.lower() else "other")
                events.append(dict(timestamp=at, source=path.name, level=level,
                                   category=category, clock_domain="robot_log_observation", execution_lookback=False,
                                   source_sequence=line_no, order="", trade_id="",
                                   side="", lots="", net_lots="", detail=message[:700]))
                if "position outside" in message.lower():
                    match_position, match_delta = BROKER.search(message), OUTSIDE.search(message)
                    checks.append(dict(timestamp=at, log=path.name, line=line_no,
                                       broker_lots=match_position.group(1) if match_position else "",
                                       journal_lots=match_position.group(2) if match_position else "",
                                       previous_external=match_delta.group(1) if match_delta else "",
                                       new_external=match_delta.group(2) if match_delta else "",
                                       message=message[:700]))
    return events, checks


def run(root: Path, state_name: str, logs_name: str,
        start: str, end: str, output: Path,
        execution_lookback_sec: int = 0):
    root, output = validate_report_output(root, output)
    state, logs = (root / state_name).resolve(), (root / logs_name).resolve()
    for source in (state, logs):
        if not source.is_relative_to(root) or not source.is_dir():
            raise ValueError("required input is missing or outside the selected copy")
    if not (state / "fills.csv").is_file():
        raise ValueError("missing fills.csv")
    datetime.fromisoformat(start)
    datetime.fromisoformat(end)
    if end < start:
        raise ValueError("end precedes start")
    fills, dupes, gaps, buy, sell, last_net = examine_fills(
        state / "fills.csv", start, end, execution_lookback_sec)
    events, checks = examine_logs(logs, start, end)
    # These are distinct clocks. Do NOT merge-sort by timestamp: a delayed
    # broker execution can predate a cancel that the engine observed first.
    # Preserve ledger physical row order and each robot log's native line order.
    all_events = sorted(fills + events, key=lambda r: (
        r["clock_domain"], r["source"], r["source_sequence"]))
    output.mkdir(parents=True, exist_ok=False)
    output_csv(output / "incident_evidence.csv",
               ["timestamp", "clock_domain", "source_sequence", "execution_lookback", "source", "level", "category",
                "order", "trade_id", "side",
                "lots", "net_lots", "detail"], all_events)
    output_csv(output / "broker_journal_checks.csv",
               ["timestamp", "log", "line", "broker_lots", "journal_lots",
                "previous_external", "new_external", "message"], checks)
    output_csv(output / "fill_anomalies.csv",
               ["source", "line", "timestamp", "anomaly", "detail"], dupes + gaps)
    risk_file = state / "risk.json"
    risk = {}
    if risk_file.is_file():
        try:
            data = json.loads(risk_file.read_text(encoding="utf-8-sig"))
            risk = dict(level=data.get("Level", ""), reason=data.get("Reason", ""),
                        since_utc=data.get("SinceUtc", ""))
        except (OSError, ValueError):
            risk = dict(error="unreadable risk snapshot")
    summary = dict(state=state_name, logs=logs_name, window_start_msk=start,
                   window_end_msk=end, fill_rows=len(fills),
                   buy_lots=buy, sell_lots=sell, net_change_lots=buy-sell,
                   full_fills_last_net_lots=last_net,
                   duplicate_trade_ids=len(dupes), fill_continuity_gaps=len(gaps),
                   position_check_events=len(checks), log_events=len(events),
                   risk_snapshot=risk, result="evidence only: no causal claim without broker trades",
                   source_native_order_preserved=True,
                   execution_lookback_seconds=execution_lookback_sec,
                   selected_prior_execution_rows=sum(
                       row["execution_lookback"] for row in fills),
                   selection_caveat="A fill selected by broker-reported execution time "
                                    "cannot establish its local arrival time",
                   cross_clock_temporal_causality="not_inferred",
                   clock_domains={
                       "fills.csv": "reported execution timestamp; ledger physical rows retained",
                       "logs": "robot log observation timestamp; file line order retained",
                   },
                   timeline_limitation="incident_evidence.csv groups by time domain and native "
                                       "record order, not a merged causal timeline")
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--state", default="state-nvda-iis-live")
    p.add_argument("--logs", default="logs-nvda-iis-live")
    p.add_argument("--from-msk", dest="start", default="2026-11-21 14:40:00")
    p.add_argument("--to-msk", dest="end", default="2026-11-21 15:10:00")
    p.add_argument("--output", type=Path)
    p.add_argument("--fill-execution-lookback-sec", type=int, default=0,
                   help="Additional execution-time seconds before requested observation window, "
                        "for late fills; output retains explicit clock domains (max 86400)")
    a = p.parse_args()
    try:
        root = a.root.resolve()
        summary = run(root, a.state, a.logs, a.start, a.end,
                      a.output or root / "reports" / "nvda-incident",
                      execution_lookback_sec=a.fill_execution_lookback_sec)
    except (ValueError, OSError) as error:
        print("Forensic study failed: " + str(error), file=sys.stderr)
        return 1
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
