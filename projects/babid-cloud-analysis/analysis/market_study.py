#!/usr/bin/env python3
"""Offline market microstructure summary. NOT a backtest or P&L forecast."""
import argparse
import csv
import gzip
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from report_safety import validate_report_output

MSK = timezone(timedelta(hours=3))
DEFAULT_LEVELS = (1, 3, 5, 10, 20, 50, 100, 120, 200, 500, 1000)


def levels(text):
    """Parse MarketRecording 'price@lots;price@lots' from an order-book row."""
    return [(float(p), int(v)) for p, v in (x.split("@", 1) for x in text.split(";"))] if text else []


def quote(bids, asks, tick, min_lots):
    """Feasible one-tick-inside quotes; never infer fills from this."""
    if not bids or not asks or tick <= 0:
        return False, False, 0.0, 0.0
    b = next((p for p, v in bids if v >= min_lots), None)
    a = next((p for p, v in asks if v >= min_lots), None)
    buy = b + tick if b is not None else None
    sell = a - tick if a is not None else None
    buy_ok = buy is not None and buy < asks[0][0]
    sell_ok = sell is not None and sell > bids[0][0]
    return (buy_ok, sell_ok,
            (asks[0][0] - buy) / tick if buy_ok else 0.0,
            (sell - bids[0][0]) / tick if sell_ok else 0.0)


def scan(path, thresholds, tick_override=None):
    op = gzip.open if path.suffix == ".gz" else open
    count = Counter()
    hourly = defaultdict(lambda: [0, 0, 0, 0.0, 0.0, 0.0])
    ticker, tick, pending_down, gap_ms = path.parent.name, tick_override, None, 0
    issues = set()
    try:
        with op(path, "rt", encoding="utf-8", errors="replace") as stream:
            for line in stream:
                if not line or line[0] == "#":
                    continue
                parts = line.rstrip("\r\n").split("\t")
                kind = parts[0]
                count[kind] += 1
                if kind == "I":
                    try:
                        obj = json.loads(parts[1])
                        ticker = obj.get("Ticker", ticker)
                        if tick_override is None:
                            tick = float(obj.get("PriceStep") or 0) or None
                    except (ValueError, IndexError, TypeError):
                        issues.add("invalid instrument header")
                    continue
                if kind not in ("B", "D", "U") or len(parts) < 2:
                    continue
                try:
                    ms = int(parts[1])
                except ValueError:
                    continue
                if kind == "D":
                    pending_down = ms
                    continue
                if kind == "U":
                    if pending_down is not None:
                        gap_ms += max(0, ms - pending_down)
                    pending_down = None
                    continue
                if not tick or tick <= 0:
                    issues.add("missing tick size: specify --tick")
                    continue
                try:
                    bids, asks = levels(parts[3]), levels(parts[4])
                    if not bids or not asks or bids[0][0] >= asks[0][0]:
                        continue
                    spread = (asks[0][0] - bids[0][0]) / tick
                    local = datetime.fromtimestamp(ms / 1000, MSK)
                    date, hour = local.strftime("%Y-%m-%d"), local.strftime("%H")
                    for threshold in thresholds:
                        n = hourly[(date, hour, threshold)]
                        b, s, be, se = quote(bids, asks, tick, threshold)
                        n[0] += 1
                        n[1] += int(b)
                        n[2] += int(s)
                        n[3] += spread
                        n[4] += be
                        n[5] += se
                except (IndexError, ValueError, OverflowError, OSError, ZeroDivisionError):
                    issues.add("invalid book row")
    except (OSError, EOFError) as error:
        issues.add("stream interrupted: " + str(error)[:100])
    if pending_down is not None:
        issues.add("recording ends during a stream outage")
    rows = []
    for (day, hour, threshold), (n, b, s, spread, bedge, sedge) in sorted(hourly.items()):
        rows.append(dict(ticker=ticker, date_msk=day, hour_msk=hour,
                         min_level_lots=threshold, books=n, buy_share=b / n,
                         sell_share=s / n, spread_ticks=spread / n,
                         buy_edge_ticks=bedge / b if b else 0,
                         sell_edge_ticks=sedge / s if s else 0))
    quality = dict(ticker=ticker, file=path.name, books=count["B"],
                   trades=count["T"], gap_trades=count["G"],
                   disconnects=count["D"], reconnects=count["U"],
                   known_outage_seconds=gap_ms / 1000,
                   issues="; ".join(sorted(issues)))
    return rows, quality


def write_table(path, rows, cols):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=cols)
        writer.writeheader()
        writer.writerows(rows)


def run(root, output, thresholds, tick):
    root, output = validate_report_output(root, output)
    if not (root / "recordings").is_dir():
        raise ValueError("root must contain recordings")
    rows, quality = [], []
    for file in sorted((root / "recordings").glob("*/*.tsv*")):
        if not file.is_file() or file.suffix not in (".tsv", ".gz"):
            continue
        if not file.resolve().is_relative_to(root):
            continue
        report, q = scan(file, thresholds, tick)
        rows.extend(report)
        quality.append(q)
    output.mkdir(parents=True, exist_ok=False)
    write_table(output / "opportunities.csv", rows,
                ["ticker", "date_msk", "hour_msk", "min_level_lots", "books",
                 "buy_share", "sell_share", "spread_ticks", "buy_edge_ticks", "sell_edge_ticks"])
    write_table(output / "market_quality.csv", quality,
                ["ticker", "file", "books", "trades", "gap_trades",
                 "disconnects", "reconnects", "known_outage_seconds", "issues"])
    summary = dict(files=len(quality), books=sum(q["books"] for q in quality),
                   scope="instantaneous quote feasibility only; not a backtest")
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--output", type=Path)
    ap.add_argument("--levels", default=",".join(map(str, DEFAULT_LEVELS)))
    ap.add_argument("--tick", type=float)
    args = ap.parse_args()
    try:
        thresholds = tuple(sorted({int(s.strip()) for s in args.levels.split(",")}))
        if not thresholds or thresholds[0] <= 0 or (args.tick is not None and args.tick <= 0):
            raise ValueError("invalid threshold or tick")
        result = run(args.root, args.output or args.root / "reports" / "market-study",
                     thresholds, args.tick)
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
