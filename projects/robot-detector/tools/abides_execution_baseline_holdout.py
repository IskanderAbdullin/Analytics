#!/usr/bin/env python3
"""Pre-registered ABIDES-NG *execution-fill* baseline for existing C# screens.

Independent synthetic seeds compare fixed-/variable-clip screener evidence
against private maker/taker truth strictly after detection. This does NOT
train, tune or identify any real market participant.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from abides_export import UPSTREAM_COMMIT, simulate

FROZEN_SEEDS = (1301, 1302, 1303, 1304)
MODES = ("null", "twap", "vwap", "pov")
MODELS = ("fixed_quantity", "variable_quantity")


def preregister(seeds: list[int]) -> dict[str, Any]:
    if tuple(seeds) != FROZEN_SEEDS:
        raise ValueError("Fixed baseline seed list and order cannot be modified")
    return {
        "protocol": "abides-existing-detector-frozen-v1",
        "seeds": seeds,
        "modes": list(MODES),
        "screens": list(MODELS),
        "simulator_revision": UPSTREAM_COMMIT,
        "detector_configs": "current-code-defaults-unchanged",
        "private_truth_used_only_after_detection": True,
        "physical_owner_identity_known": False,
        "real_market_accuracy_calibrated": False,
    }


def aggregate(cases: list[dict[str, Any]], seeds: list[int]) -> dict[str, Any]:
    plan = preregister(seeds)
    expected = {(seed, mode) for seed in seeds for mode in MODES}
    if len(cases) != len(expected) or {
        (case["seed"], case["mode"]) for case in cases
    } != expected:
        raise ValueError("Missing, repeated or extra exchange scenarios")
    summary = []
    for mode in MODES:
        matches = [c for c in cases if c["mode"] == mode]
        if mode == "null" and any(c["controlled_prints"] for c in matches):
            raise ValueError("Null scenario contains controlled prints")
        if mode != "null" and any(c["controlled_prints"] <= 0 for c in matches):
            raise ValueError("Positive execution strategy did not trade")
        for model in MODELS:
            records = [c["models"][model] for c in matches]
            tp = sum(r["tp"] for r in records)
            fp = sum(r["fp"] for r in records)
            missed = sum(r["missed"] for r in records)
            attributed = sum(r["attributed"] for r in records)
            controlled = sum(c["controlled_prints"] for c in matches)
            if tp + fp != attributed or tp + missed != controlled:
                raise ValueError("Private-truth/public attribution reconciliation failed")
            summary.append({
                "mode": mode,
                "model": model,
                "cases": len(matches),
                "public_prints": sum(c["public_prints"] for c in matches),
                "controlled_prints": controlled,
                "true_positive_prints": tp,
                "false_positive_prints": fp,
                "missed_controlled_prints": missed,
                "attributed_public_prints": attributed,
                "cases_with_any_attribution": sum(r["attributed"] > 0 for r in records),
                "pooled_event_precision": None if attributed == 0 else tp / attributed,
                "pooled_event_recall": None if controlled == 0 else tp / controlled,
                "real_market_accuracy_calibrated": False,
                "physical_owner_count_known": False,
            })
    return {
        "schema_version": "abides-strategy-executed-fill-baseline-v1",
        "frozen_plan": plan,
        "case_count": len(cases),
        "cases": cases,
        "aggregates": summary,
        "private_truth_retained_in_artifact": False,
        "models_tuned_on_frozen_seeds": False,
        "physical_owner_count_known": False,
        "real_market_accuracy_calibrated": False,
        "limitations": [
            "SYNTHETIC_ONLY: ABIDES matching-engine executions are not MOEX/SPB real market labels.",
            "PRINT_TRUTH_ONLY: synthetic maker/taker agent labels do not reveal real market owner IDs.",
            "NULL_RECALL_UNDEFINED: no controlled fills means no positive-recall denominator.",
            "PRE_REGISTERED_DEFAULTS: no detector fitting against this frozen seed cohort.",
            "DESCRIPTIVE: four simulations per mode cannot establish exchange-calibrated precision or FDR."
        ],
    }


def run(dll: Path) -> dict[str, Any]:
    if not dll.is_file():
        raise FileNotFoundError(dll)
    cases = []
    with tempfile.TemporaryDirectory(prefix="abides-baseline-") as tmp:
        directory = Path(tmp)
        for seed in FROZEN_SEEDS:
            for mode in MODES:
                public, truth = simulate(seed, mode=mode)
                # Private labels reside in temporary files only, destroyed
                # before aggregate-only artifact upload.
                stem = f"{mode}_{seed}"
                public_path = directory / f"{stem}.csv"
                truth_path = directory / f"{stem}.private.json"
                report_path = directory / f"{stem}.score.json"
                public_path.write_bytes(public)
                truth_path.write_text(json.dumps(truth), encoding="utf-8")
                subprocess.run([
                    "dotnet", str(dll), "benchmark-abides-blind",
                    "--public", str(public_path), "--truth", str(truth_path),
                    "--output", str(report_path)
                ], check=True, timeout=180, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, text=True)
                report = json.loads(report_path.read_text(encoding="utf-8"))
                control = set(truth["controlled_agent_ids"])
                injected = sum(e["passive_agent_id"] in control or
                               e["aggressive_agent_id"] in control
                               for e in truth["events"])
                if (report["publicPrints"] != len(truth["events"])
                        or not public
                        or report["publicSha256"] !=
                            hashlib.sha256(public).hexdigest()
                        or report["publicSha256"] != truth["public_sha256"]
                        or report["controlledPrints"] != injected
                        or report["physicalOwnerIdentityKnown"]
                        or report["realMarketAccuracyCalibrated"]
                        or report["liveTradingEnabled"]):
                    raise ValueError("Private public execution reconciliation failed")
                scored = {}
                for row in report["models"]:
                    name = row["model"]
                    if name not in MODELS or name in scored:
                        raise ValueError("Unexpected detector baseline")
                    if row["physicalProducerCountInferred"]:
                        raise ValueError("Forbidden physical-robot inference")
                    scored[name] = {
                        "attributed": row["attributedPublicPrints"],
                        "tp": row["truePositivePrints"],
                        "fp": row["falsePositivePrints"],
                        "missed": row["missedInjectedPrints"],
                    }
                if set(scored) != set(MODELS):
                    raise ValueError("Missing baseline model")
                cases.append({
                    "seed": seed,
                    "mode": mode,
                    "public_sha256": report["publicSha256"],
                    "public_prints": report["publicPrints"],
                    "controlled_prints": injected,
                    "models": scored
                })
    return aggregate(cases, list(FROZEN_SEEDS))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli-dll", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Refusing to overwrite prior baseline evidence")
    preregister(list(FROZEN_SEEDS))  # Verifiable plan before executing simulation.
    report = run(args.cli_dll)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as file:
        json.dump(report, file, indent=2, sort_keys=True)
        file.write("\n")
    for row in report["aggregates"]:
        print("ABIDES_STRATEGY_BASELINE", json.dumps(row, sort_keys=True))
    print("ABIDES_STRATEGY_BASELINE_DONE",
          json.dumps({"seeds": list(FROZEN_SEEDS), "cases": report["case_count"]}))


if __name__ == "__main__":
    main()
