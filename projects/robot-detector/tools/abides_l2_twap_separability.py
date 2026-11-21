#!/usr/bin/env python3
"""No-threshold post-hoc phase-choice separation warning on simulated L2 rho."""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
from typing import Any
from abides_l2_twap_phase_contrast import (
    SEEDS,SCENARIOS,PHASES_SECONDS,aggregate,frozen_plan
)
from abides_l2_phase_review import parse_input


def assess_descriptive_separation(cases: list[dict[str,Any]]) -> dict[str,Any]:
    """Check complete synthetic rho range ordering at ALL frozen origins.

    No detector is fitted, no best origin selected. These four markets share
    seeds across scenarios and the twelve phase views are correlated.
    """
    study=aggregate(cases)
    lookup={(r["seed"],r["scenario"],r["phase_seconds"]):r
            for r in study["cases"]}
    phases=[]
    for phase in PHASES_SECONDS:
        background=[lookup[(s,SCENARIOS[0],phase)]["rho"] for s in SEEDS]
        controlled=[lookup[(s,SCENARIOS[1],phase)]["rho"] for s in SEEDS]
        all_defined=all(x is not None for x in background+controlled)
        # This range gap is NOT a predictive threshold or an inference on
        # unseen independent markets. A strict positive gap is merely the
        # in-sample ordering of two source-controlled developer runs.
        gap=min(controlled)-max(background) if all_defined else None
        phases.append({
            "phase_seconds":phase,
            "original_background_runs":len(background),
            "original_twap_runs":len(controlled),
            "rho_range_gap_twap_min_minus_background_max":gap,
            "strict_observed_separation_twap_above_background": (
                gap>0 if gap is not None else None
            ),
            "all_four_development_coefficients_defined":all_defined,
        })
    all_rhos=[r["rho"] for r in study["cases"]]
    if all(x is not None for x in all_rhos):
        injected=[r["rho"] for r in study["cases"]
                  if r["scenario"]==SCENARIOS[1]]
        background=[r["rho"] for r in study["cases"]
                    if r["scenario"]==SCENARIOS[0]]
        combined_gap=min(injected)-max(background)
        robust=combined_gap>0
    else:
        combined_gap=None
        robust=None
    decisive=[x["strict_observed_separation_twap_above_background"]
              for x in phases]
    phase_dependence=(
        (any(decisive) and not all(decisive))
        if all(x is not None for x in decisive) else None
    )
    paired=[]
    for seed in SEEDS:
        for phase in PHASES_SECONDS:
            base=lookup[(seed,SCENARIOS[0],phase)]["rho"]
            altered=lookup[(seed,SCENARIOS[1],phase)]["rho"]
            paired.append({
                "seed":seed,"phase_seconds":phase,
                "twap_minus_background_rho": (
                    altered-base if base is not None and altered is not None else None
                ),
                "same_seed_but_separate_simulated_market_runs":True,
                "causal_agent_effect_established":False,
            })
    return {
        "schema_version":"abides-l2-twap-phase-choice-trap-v1",
        "original_simulation_runs":4,"correlated_public_views":12,
        "in_sample_phase_range_checks":phases,
        "strict_separation_across_every_precommitted_phase":robust,
        "whole_view_rho_range_gap":combined_gap,
        "apparent_separation_changes_with_phase_choice":phase_dependence,
        "seed_aligned_between_scenario_contrasts":paired,
        "single_best_phase_selected":False,
        "threshold_fitted_to_development_study":False,
        "independent_source_completeness_verified":False,
        "out_of_sample_detection_accuracy_established":False,
        "individual_physical_owner_identified":False,
        "scientific_stage2_release_allowed":False,
        "live_trading_allowed":False,
        "limitations":[
            "Range separation of two development cases is descriptive and prone to data snooping.",
            "A positive range gap is not a calibrated predictive classifier.",
            "Phase views of one tape are correlated and may have different eligible bins.",
            "Injected TWAP changes the whole endogenous simulated market, not only its own prints.",
            "Reusing a seed across background/TWAP scenarios does not establish independent draws.",
            "No real MOEX/SPB/NEO market specificity or physical owner count is established.",
        ],
    }


def reanalyse_frozen_json(data: dict[str,Any]) -> dict[str,Any]:
    """Recheck either original full aggregate or committed scalar-only fixture."""
    if type(data) is not dict:
        raise ValueError("Missing source report")
    schema=data.get("schema_version")
    if schema=="abides-l2-controlled-twap-phase-contrast-v1":
        if data.get("frozen_plan")!=frozen_plan():
            raise ValueError("Original source protocol is not frozen")
        for field in ("private_truth_used_for_feature","private_truth_exported",
                      "real_market_significance_established",
                      "physical_bot_count_known","trade_execution_enabled"):
            if data.get(field) is not False:
                raise ValueError("Forbidden or missing original provenance claim")
        reconstructed=aggregate(data.get("cases"))
        if data.get("cohorts")!=reconstructed["cohorts"]:
            raise ValueError("Original cohort summaries disagree with source cases")
    elif schema=="abides-l2-twap-phase-observed-aggregate-fixture-v1":
        if (data.get("original_matching_runs")!=4 or
                data.get("correlated_analytic_views")!=12 or
                data.get("individual_owner_known") is not False or
                data.get("real_market_accuracy_known") is not False or
                data.get("raw_event_archive_included") is not False or
                data.get("source_content_authenticated_by_external_provider") is not False):
            raise ValueError("Misleading scalar fixture source metadata")
    else:
        raise ValueError("Unsupported source-controlled ABIDES schema")
    return assess_descriptive_separation(data.get("cases"))


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    raw=args.input.read_bytes()
    out=reanalyse_frozen_json(parse_input(raw))
    out["input_file_sha256"]=sha256(raw).hexdigest()
    out["source_authenticity_independently_verified"]=False
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x",encoding="utf-8") as file:
        json.dump(out,file,indent=2,sort_keys=True,allow_nan=False)
        file.write("\n")
    print("ABIDES_L2_PHASE_CHOICE_TRAP",json.dumps({
        "runs":out["original_simulation_runs"],
        "strict_all_phase_separation":out["strict_separation_across_every_precommitted_phase"],
        "calibrated":False,
    },sort_keys=True))


if __name__=="__main__":
    main()
