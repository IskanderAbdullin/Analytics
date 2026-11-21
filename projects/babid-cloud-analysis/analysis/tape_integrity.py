#!/usr/bin/env python3
"""Stream Babid01 v1 market recordings to inspect data integrity, not strategy P&L.

Source format: I JSON; S recvMs status; B recvMs exchangeMs bids asks;
T/G recvMs tradeMs price lots aggressor; D recvMs reason; U recvMs.
Receipt and exchange clocks must NOT be treated as interchangeable.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import sys
from collections import Counter
from pathlib import Path

from report_safety import validate_report_output

COLUMNS = (
    "instrument", "file", "books", "valid_books", "invalid_books",
    "trades", "gap_trades", "status_messages", "disconnects", "reconnects",
    "unknown_resume", "open_outage", "known_outage_seconds", "max_outage_seconds",
    "non_monotonic_receipt", "negative_exchange_age", "exchange_age_count",
    "exchange_age_mean_ms", "exchange_age_max_ms", "exchange_age_gt_500ms",
    "book_intervals_gt_10s", "book_intervals_gt_60s", "recording_errors",
    "error_kinds",
)


def recording_lines(path: Path):
    reader = gzip.open if path.suffix.lower() == ".gz" else open
    with reader(path, "rt", encoding="utf-8-sig", errors="replace") as stream:
        yield from stream


def good_book(raw_bid: str, raw_ask: str) -> bool:
    """Strictly ordered positive-price book, no crossed/locked best prices."""
    def side(raw: str, descending: bool):
        result = []
        for item in raw.split(";"):
            price_text, sep, lots_text = item.partition("@")
            if not sep:
                return None
            price = float(price_text)
            lots = int(lots_text)
            if not math.isfinite(price) or price <= 0 or lots <= 0:
                return None
            if result and ((descending and price >= result[-1]) or (not descending and price <= result[-1])):
                return None
            result.append(price)
        return result or None

    bid, ask = side(raw_bid, True), side(raw_ask, False)
    return bool(bid and ask and bid[0] < ask[0])


def summarize(path: Path) -> dict:
    counts = Counter()
    issues = Counter()
    ticker = path.parent.name
    previous_received = None
    previous_book = None
    down_at = None
    outage_ms = 0
    max_outage = 0
    age_count = 0
    age_sum = 0
    age_max = 0
    try:
        for raw in recording_lines(path):
            if not raw.strip() or raw.startswith("#"):
                continue
            parts = raw.rstrip("\r\n").split("\t")
            kind = parts[0]
            if kind == "I":
                try:
                    name = json.loads(parts[1]).get("Ticker")
                    if name and str(name) != ticker:
                        issues["instrument_name_differs_from_directory"] += 1
                except (IndexError, ValueError, TypeError):
                    issues["bad_instrument_header"] += 1
                continue
            if kind not in ("B", "T", "G", "D", "U", "S"):
                issues["unknown_record_type"] += 1
                continue
            try:
                ms = int(parts[1])
                if ms <= 0:
                    raise ValueError("invalid receipt timestamp")
                if previous_received is not None and ms < previous_received:
                    counts["non_monotonic_receipt"] += 1
                previous_received = ms
                if kind == "B":
                    counts["books"] += 1
                    if len(parts) < 5:
                        raise ValueError("short book row")
                    if not good_book(parts[3], parts[4]):
                        counts["invalid_books"] += 1
                        issues["bad_or_crossed_book"] += 1
                    else:
                        counts["valid_books"] += 1
                    exchange_ms = int(parts[2])
                    if exchange_ms > 0:
                        if exchange_ms > ms:
                            counts["negative_exchange_age"] += 1
                        else:
                            age = ms - exchange_ms
                            age_sum += age
                            age_max = max(age_max, age)
                            age_count += 1
                            counts["exchange_age_gt_500ms"] += int(age > 500)
                    else:
                        issues["exchange_timestamp_missing"] += 1
                    if previous_book is not None:
                        interval = ms - previous_book
                        if interval > 10000:
                            counts["book_intervals_gt_10s"] += 1
                        if interval > 60000:
                            counts["book_intervals_gt_60s"] += 1
                    previous_book = ms
                    if down_at is not None:
                        issues["book_during_outage"] += 1
                elif kind == "T":
                    if len(parts) < 6:
                        raise ValueError("short market trade")
                    float(parts[3])
                    if int(parts[4]) <= 0:
                        raise ValueError("trade volume <= 0")
                    counts["trades"] += 1
                elif kind == "G":
                    if len(parts) < 6:
                        raise ValueError("short recovered trade")
                    float(parts[3])
                    if int(parts[4]) <= 0:
                        raise ValueError("recovered volume <= 0")
                    counts["gap_trades"] += 1
                elif kind == "S":
                    if len(parts) < 5:
                        raise ValueError("short trading status")
                    counts["status_messages"] += 1
                elif kind == "D":
                    counts["disconnects"] += 1
                    if down_at is not None:
                        issues["repeated_disconnect"] += 1
                    else:
                        down_at = ms
                    previous_book = None
                elif kind == "U":
                    counts["reconnects"] += 1
                    if down_at is None:
                        counts["unknown_resume"] += 1
                    else:
                        duration = max(0, ms - down_at)
                        outage_ms += duration
                        max_outage = max(max_outage, duration)
                    down_at = None
                    previous_book = None
            except (IndexError, ValueError, TypeError, OverflowError) as error:
                counts["recording_errors"] += 1
                issues["parse_error_" + kind] += 1
    except (OSError, EOFError, UnicodeError) as error:
        counts["recording_errors"] += 1
        issues["stream_read_error"] += 1
    return dict(
        instrument=ticker, file=path.name,
        books=counts["books"], valid_books=counts["valid_books"],
        invalid_books=counts["invalid_books"], trades=counts["trades"],
        gap_trades=counts["gap_trades"], status_messages=counts["status_messages"],
        disconnects=counts["disconnects"], reconnects=counts["reconnects"],
        unknown_resume=counts["unknown_resume"], open_outage=bool(down_at is not None),
        known_outage_seconds=round(outage_ms / 1000, 3),
        max_outage_seconds=round(max_outage / 1000, 3),
        non_monotonic_receipt=counts["non_monotonic_receipt"],
        negative_exchange_age=counts["negative_exchange_age"],
        exchange_age_count=age_count,
        exchange_age_mean_ms=round(age_sum / age_count, 3) if age_count else "",
        exchange_age_max_ms=age_max if age_count else "",
        exchange_age_gt_500ms=counts["exchange_age_gt_500ms"],
        book_intervals_gt_10s=counts["book_intervals_gt_10s"],
        book_intervals_gt_60s=counts["book_intervals_gt_60s"],
        recording_errors=counts["recording_errors"],
        error_kinds=";".join(f"{key}:{n}" for key, n in sorted(issues.items())),
    )


def run(root: Path, output: Path) -> dict:
    root, output = validate_report_output(root, output)
    recordings = root / "recordings"
    if not recordings.is_dir():
        raise ValueError("no market recordings")
    rows = []
    for file in sorted(recordings.glob("*/*.tsv*")):
        if not file.is_file() or file.suffix.lower() not in (".gz", ".tsv"):
            continue
        if not file.resolve().is_relative_to(root):
            continue
        rows.append(summarize(file))
    output.mkdir(parents=True, exist_ok=False)
    with (output / "tape_quality.csv").open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    summary = dict(
        recordings=len(rows),
        books=sum(x["books"] for x in rows),
        malformed_books=sum(x["invalid_books"] for x in rows),
        unreadable_rows=sum(x["recording_errors"] for x in rows),
        negative_exchange_age=sum(x["negative_exchange_age"] for x in rows),
        open_outages=sum(int(x["open_outage"]) for x in rows),
        known_outage_seconds=round(sum(x["known_outage_seconds"] for x in rows), 3),
        cautions=[
            "The recorder suppresses unchanged books; long intervals do NOT prove missing market data.",
            "Exchange-to-receipt age measures timing differences, not one-way network latency.",
            "Recovered G trades are delivered later than their exchange timestamps; replay must use receipt order.",
            "No execution/P&L or trading-parameter recommendation is inferred.",
        ],
    )
    (output / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        result = run(root, args.output or root / "reports" / "tape-integrity")
    except (ValueError, OSError) as error:
        print("Market tape integrity failure:", error, file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
