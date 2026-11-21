#!/usr/bin/env python3
"""Offline per-state reconciliation: fills.csv versus journal.json and position history.

Never uses broker APIs or changes live state. A mismatch is evidence for further
investigation, not proof of a missed fill, because source files may be partial.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

from report_safety import validate_report_output

COLUMNS = ("state", "mode", "account_hash", "snapshot_day", "fill_rows", "fill_lots",
           "duplicates", "continuity_gaps", "out_of_order", "bad_rows",
           "snapshot_fills", "snapshot_lots", "snapshot_net", "snapshot_realized",
           "snapshot_fees", "last_fill_net", "last_fill_realized", "last_fill_fees",
           "sources_stable", "status", "flags")
ANOMALY_COLUMNS = ("state", "line", "time_msk", "order", "trade_id", "kind", "detail")


def decimal(raw: object) -> Decimal:
    result = Decimal(str(raw))
    if not result.is_finite():
        raise InvalidOperation("nonfinite numeric field")
    return result


def stamp(file: Path):
    try:
        stat = file.stat()
        return (stat.st_size, stat.st_mtime_ns)
    except OSError:
        return None


def scan_fills(path: Path, state: str, anomalies: list[dict], cap: int = 5000) -> dict:
    total = {"fill_rows": 0, "fill_lots": 0, "duplicates": 0,
             "continuity_gaps": 0, "out_of_order": 0, "bad_rows": 0,
             "last_fill_net": "", "last_fill_realized": "", "last_fill_fees": ""}
    previous_net = None
    previous_time = None
    seen = set()

    def note(line: int, row: dict, kind: str, description: str):
        if len(anomalies) < cap:
            anomalies.append(dict(state=state, line=line, time_msk=row.get("time_msk", ""),
                                  order=row.get("order", ""), trade_id=row.get("trade_id", ""),
                                  kind=kind, detail=description))

    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as stream:
        reader = csv.DictReader(stream, delimiter=";")
        required = {"time_msk", "side", "lots", "net_lots", "trade_id", "realized_total", "fees_total"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("fills.csv is missing required columns: " + ",".join(sorted(required)))
        for line, row in enumerate(reader, 2):
            # Babid may append an unfinished last line while live; do not count it as a fill.
            if not row.get("time_msk") or not row.get("lots") or not row.get("net_lots"):
                continue
            try:
                lots_dec = decimal(row["lots"])
                if lots_dec <= 0 or lots_dec != lots_dec.to_integral_value():
                    raise ValueError("non-positive or fractional lots")
                lots = int(lots_dec)
                net = decimal(row["net_lots"])
                actual_realized = decimal(row["realized_total"])
                actual_fees = decimal(row["fees_total"])
                side = row.get("side")
                if side not in ("Buy", "Sell"):
                    raise ValueError("invalid side")
            except (InvalidOperation, ValueError, TypeError) as error:
                total["bad_rows"] += 1
                note(line, row, "bad_row", str(error)[:160])
                continue
            actual_time = row["time_msk"]
            if previous_time is not None and actual_time < previous_time:
                total["out_of_order"] += 1
                note(line, row, "out_of_order", "file rows not chronologically ordered")
            previous_time = actual_time
            if previous_net is not None and net != previous_net + (lots if side == "Buy" else -lots):
                total["continuity_gaps"] += 1
                note(line, row, "net_discontinuity",
                     f"previous={previous_net}; side={side}; lots={lots}; actual={net}")
            previous_net = net
            trade_id, exchange_id = row.get("trade_id", ""), row.get("exchange_id", "")
            if trade_id:
                key = (exchange_id, trade_id)
                if key in seen:
                    total["duplicates"] += 1
                    note(line, row, "duplicate_trade", "repeated exchange_id + trade_id")
                seen.add(key)
            elif row.get("synthetic") != "1":
                total["bad_rows"] += 1
                note(line, row, "missing_trade_id", "non-synthetic execution lacks a trade id")
            total["fill_rows"] += 1
            total["fill_lots"] += lots
            total["last_fill_net"] = str(net)
            total["last_fill_realized"] = str(actual_realized)
            total["last_fill_fees"] = str(actual_fees)
    return total


def reconcile_state(folder: Path, root: Path, anomalies: list[dict]) -> dict:
    state = folder.name
    result = {k: "" for k in COLUMNS}
    result.update({"state": state, "status": "incomplete", "flags": "", "sources_stable": False})
    fills, journal = folder / "fills.csv", folder / "journal.json"
    if not fills.is_file() or not journal.is_file():
        result["flags"] = "missing fills.csv or journal.json"
        return result
    before = (stamp(fills), stamp(journal))
    try:
        p = scan_fills(fills, state, anomalies)
        result.update(p)
        with journal.open("r", encoding="utf-8-sig") as stream:
            snapshot = json.load(stream, parse_float=Decimal, parse_int=Decimal)
        pnl = snapshot.get("Pnl")
        required_pnl = {"FillCount", "LotsTraded", "NetLots", "Realized", "Fees"}
        if not isinstance(pnl, dict) or not required_pnl.issubset(pnl):
            raise ValueError("journal snapshot missing required Pnl fields")
        identity = str(snapshot.get("AccountId") or "")
        result.update({"mode": snapshot.get("Mode", ""),
                       "account_hash": hashlib.sha256(identity.encode()).hexdigest()[:12] if identity else "",
                       "snapshot_day": pnl.get("Day", ""),
                       "snapshot_fills": pnl.get("FillCount", ""),
                       "snapshot_lots": pnl.get("LotsTraded", ""),
                       "snapshot_net": pnl.get("NetLots", ""),
                       "snapshot_realized": pnl.get("Realized", ""),
                       "snapshot_fees": pnl.get("Fees", "")})
        stable = before == (stamp(fills), stamp(journal))
        result["sources_stable"] = stable
        flags = []
        if p["fill_rows"] == 0:
            flags.append("empty_fills_no_history_verification")
        if not stable:
            flags.append("sources_changed_during_read")
        for what, left, right in (("fill_count", p["fill_rows"], result["snapshot_fills"]),
                                  ("lots_traded", p["fill_lots"], result["snapshot_lots"]),
                                  ("net_lots", p["last_fill_net"], result["snapshot_net"]),
                                  ("realized", p["last_fill_realized"], result["snapshot_realized"]),
                                  ("fees", p["last_fill_fees"], result["snapshot_fees"])):
            if str(left) != "" and str(right) != "" and decimal(left) != decimal(right):
                flags.append("journal_diff_" + what)
        for what in ("duplicates", "continuity_gaps", "bad_rows", "out_of_order"):
            if p[what]:
                flags.append(what)
        result["flags"] = ";".join(flags)
        result["status"] = "unverified" if not stable else "review" if flags else "matches_local_journal"
    except (OSError, ValueError, TypeError, InvalidOperation, csv.Error, json.JSONDecodeError) as error:
        result["flags"] = "read_error: " + str(error)[:200]
        result["status"] = "incomplete"
    return result


def run(root: Path, output: Path) -> dict:
    root, output = validate_report_output(root, output)
    anomalies = []
    rows = []
    for folder in sorted(root.glob("state*")):
        if folder.is_dir() and folder.resolve().is_relative_to(root):
            rows.append(reconcile_state(folder, root, anomalies))
    output.mkdir(parents=True, exist_ok=False)
    with (output / "reconciliation.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: str(row.get(k, "")) for k in COLUMNS})
    with (output / "anomalies.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=ANOMALY_COLUMNS)
        writer.writeheader()
        writer.writerows(anomalies)
    summary = {"states": len(rows), "local_journal_matches": sum(x["status"] == "matches_local_journal" for x in rows),
               "needs_review": sum(x["status"] == "review" for x in rows),
               "incomplete_or_unverified": sum(x["status"] in ("incomplete", "unverified") for x in rows),
               "written_anomalies": len(anomalies),
               "limitation": "Matching local journal does not prove broker execution or recover a missing initial history."}
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    root = args.root.resolve()
    try:
        summary = run(root, args.output or root / "reports" / "fills-reconciliation")
    except (OSError, ValueError) as error:
        print("Reconciliation refused:", error, file=sys.stderr)
        return 1
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
