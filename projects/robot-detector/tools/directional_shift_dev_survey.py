#!/usr/bin/env python3
"""ABIDES-NG public-only directional-shift *development* survey.

This script uses fresh synthetic seeds, and intentionally discards the
simulator's private maker/taker truth. The C# model sees anonymous public
prints only. No actor recognition, confidence calibration or real orders.
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from abides_export import UPSTREAM_COMMIT, simulate

MODES = ("null", "vwap", "pov")
SPENT_SEEDS = frozenset((41, 42, 43, 44, 61, 62, 63, 901, 902, 903, 904))


def aggregate(rows: list[dict[str, Any]], seeds: list[int]) -> dict[str, Any]:
    if (not 1 <= len(seeds) <= 10 or len(set(seeds)) != len(seeds)
            or any(s < 0 or s in SPENT_SEEDS for s in seeds)):
        raise ValueError("Only distinct unused nonnegative development seeds allowed")
    expected = {(seed, mode) for seed in seeds for mode in MODES}
    if len(rows) != len(expected) or {
        (row["seed"], row["mode"]) for row in rows
    } != expected:
        raise ValueError("Incomplete or repeated development-mode matrix")
    aggregates = []
    for mode in MODES:
        matching = [row for row in rows if row["mode"] == mode]
        aggregate_alerts = sum(row["shift_windows"] for row in matching)
        evaluated_bins = sum(row["evaluated_bins"] for row in matching)
        aggregates.append({
            "mode": mode,
            "simulations": len(matching),
            "public_prints": sum(row["public_prints"] for row in matching),
            "evaluated_bins": evaluated_bins,
            "observed_directional_shift_windows": aggregate_alerts,
            "simulations_with_one_or_more_shift_windows": sum(
                row["shift_windows"] > 0 for row in matching),
            "median_shift_windows_per_simulation": statistics.median(
                row["shift_windows"] for row in matching),
            "descriptive_shift_windows_per_100_evaluated_bins":
                100 * aggregate_alerts / evaluated_bins if evaluated_bins else None,
            "market_false_alarm_rate_calibrated": False,
            "robot_identity_known": False,
        })
    return {
        "schema_version": "abides-direction-shift-dev-v1",
        "simulator_revision": UPSTREAM_COMMIT,
        "development_seeds": seeds,
        "cases": rows,
        "cohorts": aggregates,
        "input_mode": "public_only",
        "private_truth_used_for_detection": False,
        "physical_owner_count_known": False,
        "statistical_significance_established": False,
        "trading_enabled": False,
        "interpretation": (
            "A public reported-direction change is not a robot or "
            "metaorder attribution. Null and positive modes are distinct "
            "simulated processes, not causal pairs."
        ),
    }


def run(seeds: list[int], dll: Path) -> dict[str, Any]:
    aggregate([
        {"seed": seed, "mode": mode, "shift_windows": 0,
         "evaluated_bins": 0, "public_prints": 0}
        for seed in seeds for mode in MODES
    ], seeds)  # Validate the frozen plan before contacting the simulator.
    if not dll.is_file():
        raise FileNotFoundError(dll)

    rows = []
    with tempfile.TemporaryDirectory(prefix="abides-public-shifts-") as tmp:
        root = Path(tmp)
        for seed in seeds:
            for mode in MODES:
                public_csv, _discarded_truth = simulate(seed, mode=mode)
                # The simulator constructs truth for its own internal checks,
                # but NO private truth is persisted, inspected or passed onward.
                public_path = root / f"public_{mode}_{seed}.csv"
                out_path = root / f"summary_{mode}_{seed}.json"
                public_path.write_bytes(public_csv)
                subprocess.run([
                    "dotnet", str(dll), "direction-shift",
                    "--input", str(public_path), "--bin-seconds", "30",
                    "--reference-bins", "6", "--min-share-shift", "0.25",
                    "--output", str(out_path)
                ], check=True, timeout=180, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, text=True)
                report = json.loads(out_path.read_text(encoding="utf-8"))
                if (report["inputPublicPrints"] <= 0
                        or report["sourceGroups"] != 1
                        or report["skippedDenseSourceGroups"]
                        or report["physicalBotCountKnown"]
                        or report["statisticalSignificanceEstablished"]
                        or report["sourceCoverageVerified"]
                        or report["candidateShiftWindows"] != len(report["shiftWindows"])
                        or any(point["physicalOwnerIdentified"]
                               or point["significanceCalibrated"]
                               for point in report["shiftWindows"])):
                    raise ValueError("Public only shift invariant failed")
                rows.append({
                    "seed": seed,
                    "mode": mode,
                    "public_sha256": report["sourceSha256"],
                    "public_prints": report["inputPublicPrints"],
                    "evaluated_bins": report["evaluatedClockBins"],
                    "shift_windows": report["candidateShiftWindows"],
                    "gap_transitions": report["clockGapTransitions"],
                    "unknown_side_quality_bins": report["unscorableSideQualityBins"],
                })
    return aggregate(rows, seeds)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dev-seeds", type=int, nargs="+", default=[71, 72, 73])
    parser.add_argument("--cli-dll", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Refusing to overwrite previous research result")
    try:
        data = run(args.dev_seeds, args.cli_dll)
    except ValueError as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")
    for row in data["cohorts"]:
        print("ABIDES_DIRECTIONAL_SHIFT_DEV", json.dumps(row, sort_keys=True))
    print("ABIDES_DIRECTIONAL_SHIFT_DONE",
          json.dumps({"seeds": args.dev_seeds, "cases": len(data["cases"])}))


if __name__ == "__main__":
    main()
