#!/usr/bin/env python3
"""Public-only ABIDES development-seed survey of lagged market-volume associations.

This script deliberately discards private maker/taker truth returned by the
simulator. It passes only the anonymous public CSV to the C# volume-response
descriptor. This is descriptive research, NOT a real trading bot detector.
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

MODES = ("null", "pov", "vwap")
SPENT_FINAL_HOLDOUTS = frozenset(range(901, 905))


def summarize(records: list[dict[str, Any]], seeds: list[int],
              modes: tuple[str, ...] = MODES) -> dict[str, Any]:
    if (not seeds or len(seeds) != len(set(seeds)) or
        any(s < 0 or s in SPENT_FINAL_HOLDOUTS for s in seeds) or
        not modes or len(set(modes)) != len(modes) or
        any(mode not in MODES for mode in modes)):
        raise ValueError("Only distinct, nonnegative development seeds and known modes are allowed")
    expected = {(seed, mode) for seed in seeds for mode in modes}
    if len(records) != len(expected) or {
        (r["seed"], r["mode"]) for r in records
    } != expected:
        raise ValueError("Incomplete or duplicated public-only development matrix")

    groups = []
    for mode in modes:
        cohort = [x for x in records if x["mode"] == mode]
        for direction in ("BUY", "SELL"):
            valid = [x["side"][direction]["rho"] for x in cohort
                     if x["side"][direction]["rho"] is not None]
            groups.append({
                "mode": mode, "reported_direction": direction,
                "simulated_runs": len(cohort),
                "runs_with_defined_rank_correlation": len(valid),
                "median_public_lag_rho": statistics.median(valid) if valid else None,
                "owner_identity_known": False,
                "significance_calibrated": False,
                "real_market_specificity_known": False,
            })
    return {
        "schema_version": "abides-public-volume-dev-v1",
        "upstream_simulator_revision": UPSTREAM_COMMIT,
        "development_seeds": seeds,
        "case_count": len(records),
        "cases": records,
        "public_summary": groups,
        "private_truth_exported": False,
        "bot_owner_identity_known": False,
        "real_market_specificity_known": False,
        "candidate_model_fitted": False,
        "limitations": [
            "NULL_CAN_BE_STRONGLER: market-wide lagged volume correlation may be greater in agent-free backgrounds.",
            "NO_CAUSALITY: group-level rank association does not identify POV/VWAP executions.",
            "NO_REAL_MARKET_CALIBRATION: these are ABIDES development seeds, not untouched exchange dates.",
            "NO_HOLDOUT_TUNING: original ABIDES holdout seeds 901-904 are intentionally excluded.",
            "NO_PRIVATE_TRUTH: actual exchange agent IDs are not written or read by this survey."
        ],
    }


def run(seeds: list[int], dll: Path) -> dict[str, Any]:
    if not dll.is_file():
        raise FileNotFoundError(dll)
    records = []
    with tempfile.TemporaryDirectory(prefix="abides-volume-dev-") as root:
        folder = Path(root)
        for seed in seeds:
            for mode in MODES:
                public, _unused_private_truth = simulate(seed, mode=mode)
                # Hidden truth is intentionally neither inspected nor written.
                csvpath = folder / f"public_{mode}_{seed}.csv"
                jsonpath = folder / f"summary_{mode}_{seed}.json"
                csvpath.write_bytes(public)
                subprocess.run([
                    "dotnet", str(dll), "volume-response",
                    "--input", str(csvpath), "--bin-seconds", "30",
                    "--min-pairs", "8", "--output", str(jsonpath)
                ], check=True, text=True, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, timeout=180)
                report = json.loads(jsonpath.read_text(encoding="utf-8"))
                if (not report["inputPublicPrints"] or report["skippedDenseGroups"] or
                    report["physicalBotCountKnown"] or
                    report["statisticalSignificanceEstablished"] or
                    report["sourceCoverageVerified"] or
                    len(report["sideProfiles"]) != 2):
                    raise ValueError(f"Unusable public volume evidence: {mode}/{seed}")
                side = {}
                for p in report["sideProfiles"]:
                    if p["ownerIdentityKnown"] or p["significanceCalibrated"]:
                        raise ValueError("Public-only research attributed private identity")
                    side[p["reportedDirection"]] = {
                        "rho": p["spearmanPreviousMarketLotsToCurrentSideLots"],
                        "adjacent_pairs": p["eligibleAdjacentPairs"],
                        "gaps": p["unobservedClockTransitions"],
                    }
                if set(side) != {"BUY", "SELL"}:
                    raise ValueError("Incomplete public side summaries")
                records.append({
                    "seed": seed, "mode": mode,
                    "public_prints": report["inputPublicPrints"],
                    "public_sha256": report["sourceSha256"],
                    "side": side
                })
    return summarize(records, seeds)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dev-seeds", nargs="+", type=int, default=[61, 62, 63])
    parser.add_argument("--cli-dll", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= len(args.dev_seeds) <= 8:
        parser.error("Require one to eight development seeds")
    if args.output.exists():
        parser.error("Refusing to overwrite previous public-only aggregate evidence")
    # Fail closed before invoking the ABIDES simulator.
    try:
        summarize([
            {"seed": seed, "mode": mode,
             "side": {"BUY": {"rho": None}, "SELL": {"rho": None}}}
            for seed in args.dev_seeds for mode in MODES
        ], args.dev_seeds)
    except ValueError as exc:
        parser.error(str(exc))
    result = run(args.dev_seeds, args.cli_dll)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as file:
        json.dump(result, file, sort_keys=True, indent=2)
        file.write("\n")
    for row in result["public_summary"]:
        print("ABIDES_PUBLIC_VOLUME_SURVEY", json.dumps(row, sort_keys=True))
    print("ABIDES_PUBLIC_VOLUME_SURVEY_DONE",
          json.dumps({"seeds": args.dev_seeds, "cases": result["case_count"]}))


if __name__ == "__main__":
    main()
