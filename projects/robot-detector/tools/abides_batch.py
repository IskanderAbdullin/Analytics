#!/usr/bin/env python3
"""Frozen-seed genuine ABIDES-NG validation batch; emits aggregate evidence only.

The whole exchange simulation runs first, then the detector reads the public
projection only. Private maker/taker labels are used exclusively by the
post-detection C# scorer. Never commit raw tapes or private manifests.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

from abides_export import UPSTREAM_COMMIT, simulate


def summarize(cases: list[dict[str, Any]], seeds: list[int]) -> dict[str, Any]:
    if not cases or len(seeds) != len(set(seeds)) or any(s < 0 for s in seeds):
        raise ValueError("Missing cases or invalid frozen holdout seeds")
    expected = {(s, kind) for s in seeds for kind in ("twap", "null")}
    observed = {(c["seed"], c["mode"]) for c in cases}
    if observed != expected or len(cases) != len(expected):
        raise ValueError("Frozen positive/null case matrix is incomplete or duplicated")
    aggregate: list[dict[str, Any]] = []
    for mode in ("twap", "null"):
        selected = [case for case in cases if case["mode"] == mode]
        for model in ("fixed_quantity", "variable_quantity"):
            row = [next(m for m in case["models"] if m["model"] == model)
                   for case in selected]
            injected = sum(c["controlled_prints"] for c in selected)
            tp = sum(r["truePositivePrints"] for r in row)
            fp = sum(r["falsePositivePrints"] for r in row)
            attributed = sum(r["attributedPublicPrints"] for r in row)
            missed = sum(r["missedInjectedPrints"] for r in row)
            if tp + missed != injected or tp + fp != attributed:
                raise ValueError("Source execution print conservation failure")
            if mode == "null" and (injected or tp):
                raise ValueError("Null scenario has controlled execution truth")
            aggregate.append({
                "mode": mode,
                "model": model,
                "cases": len(selected),
                "public_prints": sum(c["public_prints"] for c in selected),
                "controlled_prints": injected,
                "true_positive_prints": tp,
                "false_positive_prints": fp,
                "missed_controlled_prints": missed,
                "attributed_public_prints": attributed,
                "case_false_alarm_count": sum(r["attributedPublicPrints"] > 0 for r in row),
                "micro_event_precision": None if attributed == 0 else tp / attributed,
                "micro_event_recall": None if injected == 0 else tp / injected,
                "market_accuracy_calibrated": False,
            })
    return {
        "schema_version": "abides-frozen-seed-batch-v1",
        "simulator": "abides-ng",
        "upstream_commit": UPSTREAM_COMMIT,
        "holdout_seeds": seeds,
        "case_count": len(cases),
        "cases": cases,
        "aggregates": aggregate,
        "physical_owner_count_known": False,
        "market_accuracy_calibrated": False,
        "pre_registered_parameter_freeze": "existing-detector-defaults-no-holdout-tuning",
        "limitations": [
            "SIMULATED_HOLDOUT_ONLY: frozen seeds are not untouched real market days or instruments.",
            "SMALL_SAMPLE: seed count is small and background may not span real exchange microstructure.",
            "NO_PROBABILITY_CLAIMS: event-level aggregates are not calibrated market FDR or p-values.",
            "BLINDED_TRUTH: maker/taker labels remain outside the detector input and this report.",
            "NO_REAL_OWNERS: physical participant count in MOEX/SPB is not identifiable.",
        ],
    }


def run_batch(seeds: list[int], cli_dll: Path) -> dict[str, Any]:
    if not cli_dll.is_file():
        raise FileNotFoundError(f"Built RobotDetector.Cli assembly missing: {cli_dll}")
    cases: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="abides-holdout-") as tmp:
        root = Path(tmp)
        for seed in seeds:
            for mode in ("twap", "null"):
                public, truth = simulate(seed, mode=mode)
                base = root / f"{mode}_{seed}"
                public_path = base.with_suffix(".csv")
                truth_path = base.with_suffix(".private.json")
                report_path = base.with_suffix(".score.json")
                public_path.write_bytes(public)
                truth_path.write_text(json.dumps(truth, sort_keys=True), encoding="utf-8")
                subprocess.run([
                    "dotnet", str(cli_dll), "benchmark-abides-blind",
                    "--public", str(public_path), "--truth", str(truth_path),
                    "--output", str(report_path)
                ], check=True, text=True, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, timeout=180)
                report = json.loads(report_path.read_text(encoding="utf-8"))
                control = set(truth["controlled_agent_ids"])
                expected_controlled = sum(
                    e["passive_agent_id"] in control or e["aggressive_agent_id"] in control
                    for e in truth["events"]
                )
                if report["controlledPrints"] != expected_controlled or not public:
                    raise ValueError("Detector score violates independent private truth")
                if mode == "twap" and expected_controlled == 0:
                    raise ValueError("Controlled agent did not execute any fills")
                if report["physicalOwnerIdentityKnown"] or report["realMarketAccuracyCalibrated"]:
                    raise ValueError("Unjustified release claim")
                cases.append({
                    "seed": seed,
                    "mode": mode,
                    "public_sha256": truth["public_sha256"],
                    "public_prints": report["publicPrints"],
                    "controlled_prints": expected_controlled,
                    "models": report["models"],
                })
    return summarize(cases, seeds)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--holdout-seeds", type=int, nargs="+", default=[901, 902, 903, 904])
    parser.add_argument("--cli-dll", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (not args.holdout_seeds or len(args.holdout_seeds) > 10 or
        len(set(args.holdout_seeds)) != len(args.holdout_seeds) or
        any(s < 0 for s in args.holdout_seeds)):
        parser.error("Require 1..10 unique nonnegative holdout seeds")
    if args.output.exists():
        parser.error("Refusing to overwrite previous research evidence")
    result = run_batch(args.holdout_seeds, args.cli_dll)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as file:
        json.dump(result, file, indent=2, sort_keys=True)
        file.write("\n")
    for line in result["aggregates"]:
        print("ABIDES_FROZEN_HOLDOUT", json.dumps(line, sort_keys=True))
    print("ABIDES_HOLDOUT_DONE",
          json.dumps({"seeds": args.holdout_seeds, "cases": result["case_count"],
                      "upstream": UPSTREAM_COMMIT}))


if __name__ == "__main__":
    main()
