#!/usr/bin/env python3
"""Walk-forward descriptive check of market quote opportunities, NOT a P&L optimizer.

Uses per-Moscow-hour book feasibility aggregates from market_study.py. Reports
an earlier-day baseline and the held-out last day without assuming executions.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from datetime import date
from pathlib import Path

from report_safety import validate_report_output

FIELDS = ("ticker", "min_level_lots", "days", "train_days", "held_out_day",
          "train_books", "test_books", "train_buy_share", "train_sell_share",
          "test_buy_share", "test_sell_share", "worst_daily_buy_share",
          "worst_daily_sell_share", "min_daily_books", "ready_for_comparison",
          "qualifications")


def load_daily(source: Path) -> tuple[dict, list[str]]:
    data = defaultdict(lambda: [0, Decimal(0), Decimal(0)])
    warnings = []
    with source.open("r", encoding="utf-8-sig", newline="") as input_stream:
        reader = csv.DictReader(input_stream)
        required = {"ticker", "date_msk", "min_level_lots", "books", "buy_share", "sell_share"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("market opportunities CSV schema mismatch")
        for line, row in enumerate(reader, 2):
            try:
                name, day = row["ticker"], row["date_msk"]
                date.fromisoformat(day)
                threshold = int(row["min_level_lots"])
                books = int(row["books"])
                buy = Decimal(row["buy_share"])
                sell = Decimal(row["sell_share"])
                if (not name or len(day) != 10 or threshold < 1 or books <= 0 or
                        not (buy.is_finite() and sell.is_finite()) or
                        not (0 <= buy <= 1 and 0 <= sell <= 1)):
                    raise ValueError("invalid opportunity values")
                key = (name, threshold, day)
                data[key][0] += books
                data[key][1] += buy * books
                data[key][2] += sell * books
            except (KeyError, ValueError, TypeError, InvalidOperation) as error:
                warnings.append(f"line {line}: {str(error)[:80]}")
    return data, warnings


def summarize(data: dict, *, min_days: int, min_books: int) -> list[dict]:
    groups = defaultdict(list)
    for (ticker, threshold, day), (books, bsum, ssum) in data.items():
        groups[(ticker, threshold)].append((day, books, bsum / books, ssum / books))
    rows = []
    for (ticker, threshold), days in sorted(groups.items()):
        days.sort(key=lambda row: row[0])
        train, test = days[:-1], days[-1]
        train_n = sum(x[1] for x in train)
        test_n = test[1]
        train_buy = sum((x[2] * x[1] for x in train), Decimal(0)) / train_n if train_n else None
        train_sell = sum((x[3] * x[1] for x in train), Decimal(0)) / train_n if train_n else None
        has_history = len(days) >= min_days and all(day[1] >= min_books for day in days)
        qualifications = []
        if len(days) < min_days:
            qualifications.append("insufficient_days")
        if any(day[1] < min_books for day in days):
            qualifications.append("insufficient_book_samples")
        rows.append(dict(ticker=ticker, min_level_lots=threshold,
                         days=len(days), train_days=len(train), held_out_day=test[0],
                         train_books=train_n, test_books=test_n,
                         train_buy_share=str(train_buy) if train_buy is not None else "",
                         train_sell_share=str(train_sell) if train_sell is not None else "",
                         test_buy_share=str(test[2]), test_sell_share=str(test[3]),
                         worst_daily_buy_share=str(min(x[2] for x in days)),
                         worst_daily_sell_share=str(min(x[3] for x in days)),
                         min_daily_books=min(x[1] for x in days),
                         ready_for_comparison=has_history,
                         qualifications=";".join(qualifications)))
    return rows


def run(root: Path, source: Path, output: Path, min_days: int = 3, min_books: int = 100) -> dict:
    root, output = validate_report_output(root, output)
    source = source.resolve(strict=True)
    if not source.is_file() or not source.is_relative_to(root / "reports"):
        raise ValueError("input must be a market-study CSV within reports/")
    if min_days < 2 or min_books < 1:
        raise ValueError("min_days >= 2 and min_books >= 1 are required")
    data, warnings = load_daily(source)
    rows = summarize(data, min_days=min_days, min_books=min_books)
    output.mkdir(parents=True, exist_ok=False)
    with (output / "out_of_sample_feasibility.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    summary = {"groups": len(rows), "comparable_groups": sum(x["ready_for_comparison"] for x in rows),
               "warnings": warnings[:100], "warnings_total": len(warnings),
               "held_out_last_day": True, "min_days": min_days, "min_books": min_books,
               "limits": ["No live configuration recommendations: quote eligibility is not fill probability or P&L.",
                          "Book snapshots are serially correlated, not independent samples.",
                          "No latency, fee, carry, adverse selection, or partial fills modeled."]}
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path)
    p.add_argument("--min-days", type=int, default=3)
    p.add_argument("--min-books", type=int, default=100)
    a = p.parse_args()
    try:
        report = run(a.root, a.input, a.output or a.root / "reports" / "strategy-feasibility",
                     a.min_days, a.min_books)
    except (OSError, ValueError) as error:
        print("Feasibility comparison refused:", error, file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
