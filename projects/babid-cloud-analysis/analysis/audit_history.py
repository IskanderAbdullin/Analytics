#!/usr/bin/env python3
"""Read-only, streaming forensic inventory of Babid01 trading archives.

Runs only on a COPY of the trading directory. Never contacts a broker or modifies
state/config/log/recording files. Requires Python 3.10+; stdlib only.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from report_safety import validate_report_output

MSK = timezone(timedelta(hours=3))
LOG = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d(?:\.\d+)?)\s+([A-Z]{3})\s+(.*)$")
CODE = re.compile(r"(?<!\d)(?:30042|30049|30059|80006|80005|80001|30032)(?!\d)")
INCIDENT = re.compile(
    r"position outside|position check|broker position|RISK:|risk manager|"
    r"FILL |SYNTHETIC|replac|cancel|resync|stream|order \d+:", re.I
)
FIELDNAMES = ("day", "state", "fills", "lots", "realized", "fee_estimate",
              "synthetic", "duplicate_trade_ids", "last_net_lots",
              "invalid_rows", "missing_realized", "missing_fees")


def read_jsonc(path: Path) -> dict:
    """Remove JSONC comments without corrupting // inside quoted strings."""
    data = path.read_text(encoding="utf-8-sig")
    out = []
    quoted = False
    escaped = False
    i = 0
    while i < len(data):
        c = data[i]
        n = data[i + 1] if i + 1 < len(data) else ""
        if quoted:
            out.append(c)
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                quoted = False
            i += 1
        elif c == '"':
            quoted = True
            out.append(c)
            i += 1
        elif c == "/" and n == "/":
            i += 2
            while i < len(data) and data[i] not in "\r\n":
                i += 1
        elif c == "/" and n == "*":
            i += 2
            while i + 1 < len(data) and data[i:i + 2] != "*/":
                i += 1
            i = min(i + 2, len(data))
        else:
            out.append(c)
            i += 1
    clean = "".join(out)
    # Strip trailing commas only outside strings (JSONC allows them).
    cleaned = []
    quoted = escaped = False
    for idx, c in enumerate(clean):
        if quoted:
            cleaned.append(c)
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                quoted = False
        elif c == '"':
            quoted = True
            cleaned.append(c)
        elif c == "," and clean[idx + 1:].lstrip().startswith(("}", "]")):
            continue
        else:
            cleaned.append(c)
    return json.loads("".join(cleaned))


def safe_child(root: Path, path: str) -> Path | None:
    """Do not follow configured paths outside the user's selected copy."""
    child = Path(path)
    if not child.is_absolute():
        child = root / child
    child = child.resolve()
    return child if child.is_relative_to(root.resolve()) else None


def account_fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12] if value else ""


def strict_decimal(value: str | None) -> Decimal:
    if value is None or not str(value).strip():
        raise InvalidOperation("numeric field is absent")
    amount = Decimal(str(value))
    if not amount.is_finite():
        raise InvalidOperation("numeric field is not finite")
    return amount


def table(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_inventory(root: Path, problems: list[dict]) -> list[dict]:
    result = []
    for file in sorted(root.glob("config*.json")):
        try:
            conf = read_jsonc(file)
            instrument = conf.get("instrument") or {}
            strategy = conf.get("strategy") or {}
            conn = conf.get("connection") or {}
            name = file.name
            # No token, tokenFile, secrets, or raw account ID in the report.
            result.append(dict(
                file=name, mode=conf.get("mode", ""),
                ticker=instrument.get("ticker", ""), class_code=instrument.get("classCode", ""),
                account_hash=account_fingerprint(str(conf.get("accountId", ""))),
                state_dir=conf.get("stateDir", "state"), log_dir=conf.get("logDir", "logs"),
                regime=strategy.get("regime", ""), max_position=strategy.get("maxPositionLots", ""),
                buy_level=strategy.get("buyMinLevelLots", ""),
                sell_level=strategy.get("sellMinLevelLots", ""),
                buy_quote=strategy.get("buyQuoteLots", ""),
                sell_quote=strategy.get("sellQuoteLots", ""),
                close_level=strategy.get("closeMinLevelLots", ""),
                close_no_loss=strategy.get("closeNoLoss", ""),
                distance_percent=strategy.get("minDistancePercent", ""),
                take_lots=strategy.get("takeBlockingLots", ""),
                replace_order=conn.get("useReplaceOrder", ""),
                paper_fills=conf.get("paperFills", "queue")
            ))
        except (ValueError, OSError, TypeError) as error:
            problems.append(dict(type="invalid_config", file=file.name, detail=str(error)[:180]))
    return result


def audit_fills(path: Path, state: str, problems: list[dict]) -> list[dict]:
    """Retain only financially complete daily totals, using exact decimals.

    Unknown/malformed accounting is NOT zero. Duplicate and incomplete rows
    mean realized results cannot be certified from this source copy.
    """
    days = defaultdict(lambda: dict(
        fills=0, lots=0, realized=Decimal(0), fee_estimate=Decimal(0),
        synthetic=0, duplicate_trade_ids=0, last_net_lots="",
        invalid_rows=0, missing_realized=0, missing_fees=0))
    seen: set[tuple[str, str]] = set()
    undated_bad_rows = 0
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as stream:
            reader = csv.DictReader(stream, delimiter=";")
            if not reader.fieldnames or not {"time_msk", "trade_id", "lots"}.issubset(reader.fieldnames):
                raise ValueError("missing required fills.csv columns")
            for row in reader:
                timestamp = row.get("time_msk") or ""
                day = timestamp[:10]
                try:
                    datetime.strptime(day, "%Y-%m-%d")
                except ValueError:
                    undated_bad_rows += 1
                    continue
                stat = days[day]
                try:
                    volume = strict_decimal(row.get("lots"))
                    if volume <= 0 or volume != volume.to_integral_value():
                        raise ValueError("invalid positive integer lot count")
                    lots = int(volume)
                except (InvalidOperation, ValueError, TypeError, OverflowError):
                    stat["invalid_rows"] += 1
                    continue

                stat["fills"] += 1
                stat["lots"] += lots
                stat["synthetic"] += int(row.get("synthetic") == "1")
                stat["last_net_lots"] = row.get("net_lots", "")
                key = (row.get("exchange_id", ""), row.get("trade_id", ""))
                if key[1]:
                    if key in seen:
                        stat["duplicate_trade_ids"] += 1
                    seen.add(key)
                for source, target, missing in (
                    ("realized", "realized", "missing_realized"),
                    ("fee_estimate", "fee_estimate", "missing_fees"),
                ):
                    try:
                        stat[target] += strict_decimal(row.get(source))
                    except (InvalidOperation, ValueError, TypeError):
                        stat[missing] += 1
    except (OSError, ValueError, csv.Error) as error:
        problems.append(dict(type="fills_read_error", file=path.name, detail=str(error)[:180]))

    if undated_bad_rows:
        problems.append(dict(type="fills_undated_rows", file=path.name,
                             detail=f"{undated_bad_rows} rows have no valid Moscow date"))
    results = []
    for day, stat in sorted(days.items()):
        partial = bool(stat["invalid_rows"] or stat["duplicate_trade_ids"])
        if partial or stat["missing_realized"] or stat["missing_fees"]:
            problems.append(dict(type="fills_day_uncertain", file=path.name,
                                 detail=f"{state}:{day} has incomplete financial coverage"))
        realized = "" if partial or stat["missing_realized"] else str(stat["realized"])
        fees = "" if partial or stat["missing_fees"] else str(stat["fee_estimate"])
        results.append(dict(day=day, state=state,
                            **(stat | {"realized": realized, "fee_estimate": fees})))
    return results


def audit_equity(path: Path, state: str, problems: list[dict]) -> list[dict]:
    days: dict[str, dict] = {}
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as stream:
            for line in stream:
                parts = line.strip().split(";")
                if len(parts) != 2:
                    continue
                try:
                    ts, value = float(parts[0]), float(parts[1])
                    if ts < 1e12:
                        continue
                    day = datetime.fromtimestamp(ts / 1000, MSK).strftime("%Y-%m-%d")
                except (ValueError, OverflowError, OSError):
                    continue
                if day not in days:
                    days[day] = dict(day=day, state=state, samples=0, first=value,
                                     last=value, minimum=value, maximum=value,
                                     peak=value, max_drawdown=0.0)
                row = days[day]
                row["samples"] += 1
                row["last"] = value
                row["minimum"] = min(row["minimum"], value)
                row["maximum"] = max(row["maximum"], value)
                row["peak"] = max(row["peak"], value)
                row["max_drawdown"] = max(row["max_drawdown"], row["peak"] - value)
    except OSError as error:
        problems.append(dict(type="equity_read_error", file=str(path), detail=str(error)[:180]))
    return [dict((k, v) for k, v in row.items() if k != "peak") |
            {"change": row["last"] - row["first"]} for row in days.values()]


def classify(message: str) -> str:
    low = message.lower()
    if "position outside" in low or "position check:" in low:
        return "position_mismatch"
    if "synthetic" in low or "without trades" in low:
        return "synthetic_fill"
    if "risk: halted" in low or "risk manager" in low:
        return "risk_stop"
    found = CODE.search(message)
    if found:
        return "api_" + found.group()
    if "replac" in low:
        return "replace"
    if "cancel" in low:
        return "cancel"
    if "reconnect" in low or "stream" in low:
        return "connection"
    return "other"


def audit_logs(path: Path, logdir: str, focus_start: str, focus_end: str,
               error_counts: Counter, incident: list[dict], problems: list[dict],
               incident_stats: Counter, incident_limit: int) -> None:
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as stream:
            for line_no, line in enumerate(stream, 1):
                match = LOG.match(line.rstrip("\r\n"))
                if not match:
                    continue
                stamp, level, message = match.groups()
                day = stamp[:10]
                if level in ("WRN", "ERR"):
                    error_counts[(day, logdir, level, classify(message))] += 1
                if focus_start <= stamp[:19].replace(" ", "T") <= focus_end and INCIDENT.search(message):
                    incident_stats["matched"] += 1
                    # Redact path/user-specific details; raw logs stay only at source.
                    # Every omitted event is counted, even after the storage cap.
                    if len(incident) < incident_limit:
                        incident.append(dict(at_msk=stamp, log_dir=logdir,
                                             level=level, category=classify(message),
                                             file=path.name, line=line_no,
                                             message=message[:400]))
    except OSError as error:
        problems.append(dict(type="log_read_error", file=str(path), detail=str(error)[:180]))


def audit_recording(path: Path, problems: list[dict]) -> dict:
    # Stream .gz; never decompress to disk and never load the market file into RAM.
    count = gaps = 0
    first = last = ""
    op = gzip.open if path.suffix == ".gz" else open
    try:
        with op(path, "rt", encoding="utf-8", errors="replace") as data:
            for line in data:
                count += 1
                if not first:
                    first = line[:90].strip()
                last = line[:90].strip()
                if line.startswith("G\t"):
                    gaps += 1
    except (OSError, EOFError) as error:
        problems.append(dict(type="recording_read_error", file=str(path), detail=str(error)[:180]))
    return dict(instrument=path.parent.name, filename=path.name,
                records=count, recovered_or_gap_markers=gaps,
                first_line_preview=first, last_line_preview=last)


def run(root: Path, output: Path, focus_start: str, focus_end: str,
        incident_limit: int = 25000) -> dict:
    if not 1 <= incident_limit <= 1000000:
        raise ValueError("incident_limit must be 1..1000000")
    root, output = validate_report_output(root, output)
    problems: list[dict] = []
    configs = load_inventory(root, problems)
    state_dirs = {entry["state_dir"] for entry in configs}
    log_dirs = {entry["log_dir"] for entry in configs}
    # Also inspect historical directories not referenced by current configs.
    state_dirs.update(p.name for p in root.glob("state*") if p.is_dir())
    log_dirs.update(p.name for p in root.glob("logs*") if p.is_dir())
    fills, equity, snapshots, incidents = [], [], [], []
    errors: Counter = Counter()
    incident_stats: Counter = Counter()
    for name in sorted(state_dirs):
        folder = safe_child(root, name)
        if folder is None or not folder.is_dir():
            problems.append(dict(type="missing_state", file=name, detail="unavailable or outside root"))
            continue
        if (folder / "fills.csv").is_file():
            fills.extend(audit_fills(folder / "fills.csv", name, problems))
        if (folder / "pnl-curve.csv").is_file():
            equity.extend(audit_equity(folder / "pnl-curve.csv", name, problems))
        snapshot = folder / "journal.json"
        if snapshot.is_file():
            try:
                j = json.loads(snapshot.read_text(encoding="utf-8-sig"))
                pnl = j.get("Pnl") or {}
                snapshots.append(dict(state=name, mode=j.get("Mode", ""),
                    account_hash=account_fingerprint(str(j.get("AccountId", ""))),
                    net_lots=pnl.get("NetLots", ""), external_lots=j.get("ExternalLots", ""),
                    realized=pnl.get("Realized", ""), fees=pnl.get("Fees", ""),
                    fill_count=pnl.get("FillCount", ""),
                    lots_traded=pnl.get("LotsTraded", ""),
                    turnover=pnl.get("Turnover", ""), pnl_day=pnl.get("Day", "")))
            except (ValueError, OSError) as error:
                problems.append(dict(type="snapshot_read_error", file=str(snapshot),
                                     detail=str(error)[:180]))
    for name in sorted(log_dirs):
        folder = safe_child(root, name)
        if folder is None or not folder.is_dir():
            continue
        for log in sorted(folder.glob("*.log")):
            if log.is_file():
                audit_logs(log, name, focus_start, focus_end, errors, incidents,
                           problems, incident_stats, incident_limit)
    recordings = []
    rec = root / "recordings"
    if rec.is_dir():
        for file in sorted(rec.glob("*/*.tsv*")):
            if file.is_file():
                recordings.append(audit_recording(file, problems))
    output.mkdir(parents=True, exist_ok=False)
    table(output / "configs.csv", list(configs[0]) if configs else ["file"], configs)
    table(output / "snapshots.csv", list(snapshots[0]) if snapshots else ["state"], snapshots)
    table(output / "fills_daily.csv", list(FIELDNAMES), fills)
    table(output / "pnl_daily.csv",
          ["day", "state", "samples", "first", "last", "minimum", "maximum", "max_drawdown", "change"], equity)
    table(output / "errors_daily.csv", ["day", "log_dir", "level", "category", "count"],
          [dict(zip(["day", "log_dir", "level", "category"], k, strict=True), count=v) for k, v in sorted(errors.items())])
    table(output / "incident_timeline.csv", ["at_msk", "log_dir", "level", "category", "file", "line", "message"],
          sorted(incidents, key=lambda x: x["at_msk"]))
    table(output / "recordings.csv", ["instrument", "filename", "records",
          "recovered_or_gap_markers", "first_line_preview", "last_line_preview"], recordings)
    table(output / "issues.csv", ["type", "file", "detail"], problems)
    report = dict(source=str(root), focus_start_msk=focus_start, focus_end_msk=focus_end,
                  configurations=len(configs), states=len(snapshots), days_with_fills=len(fills),
                  equity_days=len(equity), error_events=sum(errors.values()),
                  incident_events=len(incidents),
                  incident_events_total=incident_stats["matched"],
                  incident_events_omitted=incident_stats["matched"] - len(incidents),
                  incident_timeline_truncated=incident_stats["matched"] > len(incidents),
                  incident_limit=incident_limit, recordings=len(recordings),
                  problems=len(problems), limitations=[
                      "Current config values are not historical config epochs",
                      "Broker-side operations, overnight charges and funding are not reconciled",
                      "Live journal snapshots can be changing while the audit runs",
                      "Paper execution is a model, not evidence of exchange fills"])
    (output / "summary.json").write_text(json.dumps(report, indent=2, ensure_ascii=False),
                                         encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Copy of Babid01-TInvest")
    parser.add_argument("--output", type=Path, help="New directory for reports (within root)")
    parser.add_argument("--focus-start", default="0001-01-01T00:00:00")
    parser.add_argument("--focus-end", default="9999-12-31T23:59:59")
    parser.add_argument("--incident-limit", type=int, default=25000,
                        help="max incident detail rows stored; all matches are counted")
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output or (root / "reports" / "history-audit")
    try:
        result = run(root, output, args.focus_start, args.focus_end, args.incident_limit)
    except (OSError, ValueError) as error:
        print("Audit refused/failed:", error, file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
