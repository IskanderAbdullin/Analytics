#!/usr/bin/env python3
"""Held-out quality check for time-weighted book geometry, NOT an optimizer."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from report_safety import validate_report_output

COLUMNS = (
    "instrument", "min_level_lots", "days", "train_days", "held_out_day",
    "train_observed_ms", "train_covered_ms", "test_observed_ms", "test_covered_ms",
    "train_coverage_share", "test_coverage_share", "min_daily_coverage_share",
    "train_buy_share", "train_sell_share", "test_buy_share", "test_sell_share",
    "worst_daily_buy_share", "worst_daily_sell_share",
    "min_daily_covered_ms", "possible_overlapping_hours",
    "eligible_for_descriptive_comparison", "qualifications",
)
REQUIRED = {"instrument", "day_msk", "hour_msk", "min_level_lots",
            "observed_ms", "covered_ms", "buy_geometry_ms", "sell_geometry_ms"}


def share(a: int, b: int) -> str:
    return str(Decimal(a) / b) if b else ""


def read_daily(path: Path):
    hourly = defaultdict(lambda: [0, 0, 0, 0])
    rejected = []
    overlaps = set()
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = csv.DictReader(stream)
        if not rows.fieldnames or not REQUIRED.issubset(rows.fieldnames):
            raise ValueError("missing time-weighted geometry columns")
        for line, row in enumerate(rows, 2):
            try:
                ticker, day, hour = row["instrument"], row["day_msk"], row["hour_msk"]
                date.fromisoformat(day)
                if not ticker or len(day) != 10 or not hour.isdigit() or not 0 <= int(hour) <= 23:
                    raise ValueError("invalid instrument/day/hour")
                threshold = int(row["min_level_lots"])
                numbers = []
                for field in ("observed_ms", "covered_ms", "buy_geometry_ms", "sell_geometry_ms"):
                    amount = Decimal(row[field])
                    if not amount.is_finite() or amount != amount.to_integral_value():
                        raise ValueError("non-integer or non-finite milliseconds")
                    numbers.append(int(amount))
                observed, covered, buy, sell = numbers
                if threshold < 1 or observed <= 0 or not 0 <= buy <= covered <= observed or not 0 <= sell <= covered:
                    raise ValueError("invalid book geometry durations")
                key = (ticker, threshold, day, int(hour))
                if key in hourly:
                    # Two rows for a single hour cannot be assumed disjoint:
                    # the common case is two copies of the same recording.
                    # Never add the second row and silently double-count it.
                    overlaps.add((ticker, threshold))
                    continue
                for i, number in enumerate(numbers):
                    hourly[key][i] += number
                if hourly[key][0] > 3600000:
                    overlaps.add((ticker, threshold))
            except (KeyError, ValueError, InvalidOperation, TypeError, OverflowError) as error:
                rejected.append(f"row {line}: {str(error)[:75]}")
    daily = defaultdict(lambda: [0, 0, 0, 0])
    for (ticker, threshold, day, _hour), values in hourly.items():
        for i, number in enumerate(values):
            daily[(ticker, threshold, day)][i] += number
    return daily, rejected, overlaps


def summarize(daily, rejected, overlaps, min_days, min_daily_ms, min_coverage):
    grouped = defaultdict(list)
    for (ticker, threshold, day), (observed, covered, buy, sell) in daily.items():
        grouped[(ticker, threshold)].append(dict(day=day, observed=observed, covered=covered,
                                                 buy=buy, sell=sell))
    result = []
    for (ticker, threshold), days in sorted(grouped.items()):
        days.sort(key=lambda x: x["day"])
        train, test = days[:-1], days[-1]
        train_observed = sum(x["observed"] for x in train)
        train_covered = sum(x["covered"] for x in train)
        coverages = [Decimal(d["covered"]) / d["observed"] for d in days]
        reasons = []
        if len(days) < min_days:
            reasons.append("insufficient_days")
        if min(d["covered"] for d in days) < min_daily_ms:
            reasons.append("insufficient_fresh_book_time")
        if min(coverages) < min_coverage:
            reasons.append("insufficient_coverage_share")
        if (ticker, threshold) in overlaps:
            reasons.append("possible_overlapping_hourly_recordings")
        if rejected:
            reasons.append("invalid_input_rows")
        result.append(dict(
            instrument=ticker, min_level_lots=threshold, days=len(days), train_days=len(train),
            held_out_day=test["day"], train_observed_ms=train_observed,
            train_covered_ms=train_covered, test_observed_ms=test["observed"],
            test_covered_ms=test["covered"], train_coverage_share=share(train_covered, train_observed),
            test_coverage_share=share(test["covered"], test["observed"]),
            min_daily_coverage_share=str(min(coverages)),
            train_buy_share=share(sum(x["buy"] for x in train), train_covered),
            train_sell_share=share(sum(x["sell"] for x in train), train_covered),
            test_buy_share=share(test["buy"], test["covered"]),
            test_sell_share=share(test["sell"], test["covered"]),
            worst_daily_buy_share=str(min(Decimal(x["buy"]) / x["covered"] if x["covered"]
                                          else Decimal(0) for x in days)),
            worst_daily_sell_share=str(min(Decimal(x["sell"]) / x["covered"] if x["covered"]
                                           else Decimal(0) for x in days)),
            min_daily_covered_ms=min(x["covered"] for x in days),
            possible_overlapping_hours=(ticker, threshold) in overlaps,
            eligible_for_descriptive_comparison=not reasons, qualifications=";".join(reasons)))
    return result


def run(root: Path, source: Path, output: Path, min_days: int = 4,
        min_daily_covered_ms: int = 900000, min_coverage: str = "0.60"):
    root, output = validate_report_output(root, output)
    source = source.resolve(strict=True)
    if not source.is_file() or not source.is_relative_to(root / "reports"):
        raise ValueError("source must be a time-weighted report below reports/")
    coverage = Decimal(min_coverage)
    if not coverage.is_finite() or not 0 <= coverage <= 1 or min_days < 2 or min_daily_covered_ms < 1:
        raise ValueError("invalid day, coverage or minimum fresh-book time constraint")
    daily, rejected, overlaps = read_daily(source)
    rows = summarize(daily, rejected, overlaps, min_days, min_daily_covered_ms, coverage)
    output.mkdir(parents=True, exist_ok=False)
    with (output / "held_out_book_geometry.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    summary = dict(groups=len(rows),
                   eligible_for_descriptive_comparison=sum(x["eligible_for_descriptive_comparison"] for x in rows),
                   invalid_source_rows=len(rejected), invalid_source_examples=rejected[:30],
                   possible_overlapping_groups=len(overlaps),
                   min_days=min_days, min_daily_covered_ms=min_daily_covered_ms,
                   min_coverage=str(coverage),
                   limits=[
                       "Descriptive quote geometry is NOT a profitability model or validated setting.",
                       "Correlated market snapshots are not independent execution observations.",
                       "No broker fills, order queues, latency, adverse selection, fees or funding modeled.",
                       "No live config or risk parameter changes may follow automatically.",
                   ])
    (output / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path)
    p.add_argument("--min-days", type=int, default=4)
    p.add_argument("--min-daily-covered-ms", type=int, default=900000)
    p.add_argument("--min-coverage", default="0.60")
    a = p.parse_args()
    try:
        result = run(a.root, a.input, a.output or a.root / "reports" / "geometry-validation",
                     a.min_days, a.min_daily_covered_ms, a.min_coverage)
    except (OSError, ValueError, InvalidOperation) as error:
        print("Geometry comparison refused:", error, file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
