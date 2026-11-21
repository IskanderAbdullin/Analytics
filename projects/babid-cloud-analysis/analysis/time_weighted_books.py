#!/usr/bin/env python3
"""Time-weighted book geometry for Babid01 recordings, with a strict age cap.

Unlike per-snapshot counts, an unchanged book is not repeatedly counted.
Intervals after the last recorded event are intentionally NOT extrapolated.
Not a fill model, arbitrage test, or profitability optimizer.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from market_study import levels, quote
from report_safety import validate_report_output
from tape_integrity import good_book

MSK = timezone(timedelta(hours=3))
HOUR_MS = 3600000
OFFSET_MS = 10800000
THRESHOLDS = (1, 3, 5, 10, 20, 50, 100, 120, 200)
COLUMNS = (
    "instrument", "day_msk", "hour_msk", "min_level_lots", "observed_ms",
    "covered_ms", "uncovered_ms", "buy_geometry_ms", "sell_geometry_ms",
    "coverage_share", "buy_share_of_covered", "sell_share_of_covered",
)


def reader(path):
    op = gzip.open if path.suffix.lower() == ".gz" else open
    with op(path, "rt", encoding="utf-8-sig", errors="replace") as source:
        yield from source


def hourly_split(start: int, end: int):
    while start < end:
        index = (start + OFFSET_MS) // HOUR_MS
        boundary = (index + 1) * HOUR_MS - OFFSET_MS
        stop = min(end, boundary)
        when = datetime.fromtimestamp(start / 1000, MSK)
        yield when.strftime("%Y-%m-%d"), when.strftime("%H"), start, stop
        start = stop


def scan(path: Path, thresholds=THRESHOLDS, ttl_ms: int = 2000):
    if ttl_ms <= 0:
        raise ValueError("max book age must be positive")
    ticker = path.parent.name
    tick = None
    last = None
    current = None
    down = False
    stats = defaultdict(lambda: [0, 0, 0, 0])
    quality = dict(files=1, rows=0, valid_books=0, invalid_books=0,
                   resets=0, out_of_order=0, missing_tick=0)
    for raw in reader(path):
        if not raw.strip() or raw.startswith("#"):
            continue
        parts = raw.rstrip("\r\n").split("\t")
        kind = parts[0]
        if kind == "I":
            try:
                obj = json.loads(parts[1])
                header = str(obj.get("Ticker") or "")
                if header and header.casefold() != ticker.casefold():
                    raise ValueError("recording header instrument differs from directory")
                value = float(obj.get("PriceStep") or 0)
                if not math.isfinite(value):
                    raise ValueError("PriceStep must be finite")
                if value > 0:
                    tick = value
            except (IndexError, ValueError, TypeError) as error:
                raise ValueError("invalid instrument header") from error
            continue
        if kind not in ("B", "T", "G", "D", "U", "S"):
            continue
        try:
            ms = int(parts[1])
        except (IndexError, ValueError) as error:
            raise ValueError("invalid receipt timestamp") from error
        if last is not None and ms < last:
            quality["out_of_order"] += 1
            raise ValueError("out-of-order receipt time prevents duration allocation")

        # At every next event, attribute elapsed time from the PREVIOUS book
        # (never the book at current ms), no longer than its freshness TTL.
        if last is not None and ms > last:
            covered_stop = min(ms, current["at"] + ttl_ms) if current and not down else last
            for day, hour, start, stop in hourly_split(last, ms):
                duration = stop - start
                known = max(0, min(stop, covered_stop) - start)
                for level in thresholds:
                    accum = stats[(ticker, day, hour, level)]
                    accum[0] += duration
                    accum[1] += known
                    if known:
                        yes_buy, yes_sell = current["geometry"][level]
                        accum[2] += known if yes_buy else 0
                        accum[3] += known if yes_sell else 0

        quality["rows"] += 1
        last = ms
        if kind in ("D", "U"):
            down = kind == "D"
            current = None
            quality["resets"] += 1
        elif kind == "B":
            if len(parts) < 5 or not good_book(parts[3], parts[4]):
                quality["invalid_books"] += 1
                current = None
                continue
            if tick is None:
                quality["missing_tick"] += 1
                current = None
                continue
            bids, asks = levels(parts[3]), levels(parts[4])
            geometry = {}
            for threshold in thresholds:
                buy, sell, _, _ = quote(bids, asks, tick, threshold)
                geometry[threshold] = (buy, sell)
            if not down:
                current = {"at": ms, "geometry": geometry}
                quality["valid_books"] += 1

    records = []
    for (instrument, day, hour, threshold), (span, known, buy, sell) in sorted(stats.items()):
        records.append(dict(
            instrument=instrument, day_msk=day, hour_msk=hour,
            min_level_lots=threshold, observed_ms=span,
            covered_ms=known, uncovered_ms=span - known,
            buy_geometry_ms=buy, sell_geometry_ms=sell,
            coverage_share=round(known / span, 6) if span else "",
            buy_share_of_covered=round(buy / known, 6) if known else "",
            sell_share_of_covered=round(sell / known, 6) if known else "",
        ))
    return records, quality


def run(root: Path, output: Path, ttl_ms: int = 2000, thresholds=THRESHOLDS):
    root, output = validate_report_output(root, output)
    if not (root / "recordings").is_dir():
        raise ValueError("no recordings directory")
    if ttl_ms <= 0 or not thresholds or min(thresholds) < 1:
        raise ValueError("invalid TTL or threshold")
    rows = []
    checks = []
    errors = []
    # A copied recorder may contain both uncompressed and compressed
    # versions of the SAME session. Never count either without resolving
    # the ambiguity, even if combined observed time is less than one hour.
    sessions = defaultdict(list)
    for file in sorted((root / "recordings").glob("*/*.tsv*")):
        if not file.is_file() or file.suffix.lower() not in (".gz", ".tsv"):
            continue
        if not file.resolve().is_relative_to(root):
            continue
        logical_name = file.name[:-3] if file.suffix.lower() == ".gz" else file.name
        if not logical_name.lower().endswith(".tsv"):
            continue
        sessions[(file.parent.name, logical_name)].append(file)
    duplicate_sessions = 0
    for (instrument, _logical_name), variants in sorted(sessions.items()):
        if len(variants) != 1:
            duplicate_sessions += 1
            for file in variants:
                errors.append({"instrument": instrument, "file": file.name,
                               "issue": "ambiguous TSV and compressed TSV for same recording session"})
            continue
        file = variants[0]
        try:
            records, quality = scan(file, thresholds, ttl_ms)
            rows.extend(records)
            checks.append({"instrument": file.parent.name, "file": file.name, **quality})
        except (OSError, ValueError, EOFError) as error:
            errors.append({"instrument": file.parent.name, "file": file.name,
                           "issue": str(error)[:150]})
    output.mkdir(parents=True, exist_ok=False)
    with (output / "time_weighted_geometry.csv").open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    with (output / "file_quality.csv").open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=("instrument", "file", "files", "rows",
                                                     "valid_books", "invalid_books", "resets",
                                                     "out_of_order", "missing_tick"))
        writer.writeheader()
        writer.writerows(checks)
    summary = dict(
        recordings=len(checks), rejected_recordings=len(errors),
        duplicate_sessions=duplicate_sessions,
        rejected=errors, max_book_age_ms=ttl_ms,
        observed_seconds=round(sum(x["observed_ms"] for x in rows) / (1000 * len(thresholds)), 3)
            if thresholds else 0,
        covered_seconds=round(sum(x["covered_ms"] for x in rows) / (1000 * len(thresholds)), 3)
            if thresholds else 0,
        cautions=[
            "This is time-weighted book GEOMETRY, not a fill probability or executable order simulation.",
            "After a book becomes older than max_book_age_ms, the interval is uncovered.",
            "An unchanged book is not recorded; uncovered time is not proof of stream failure.",
            "The last event does not authorize extrapolating the book into the future.",
        ],
    )
    (output / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False),
                                         encoding="utf-8")
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--output", type=Path)
    p.add_argument("--max-book-age-ms", type=int, default=2000)
    p.add_argument("--levels", default=",".join(map(str, THRESHOLDS)))
    args = p.parse_args()
    root = args.root.resolve()
    try:
        chosen = tuple(sorted({int(s.strip()) for s in args.levels.split(",")}))
        result = run(root, args.output or root / "reports" / "time-weighted-books",
                     args.max_book_age_ms, chosen)
    except (ValueError, OSError) as error:
        print("Time-weighted scan refused:", error, file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
