#!/usr/bin/env python3
"""Threshold-free robustness audit: correlated phases never identify owners."""
from __future__ import annotations
from typing import Any
from abides_l2_binphase_sensitivity import (
    BACKGROUNDS, PHASES_SECONDS, SEEDS, aggregate
)

def evaluate_phase_fragility(summary: dict[str, Any]) -> dict[str, Any]:
    """Report descriptive instability on original simulations, not twelve samples.

    No thresholds are estimated, no phase is selected. The input case matrix
    is revalidated; full book content and provider source are NOT authenticated.
    """
    if type(summary) is not dict:
        raise ValueError("Missing phase study")
    checked = aggregate(summary.get("cases"))
    cases = checked["cases"]
    by_key = {(r["seed"],r["background"],r["phase_seconds"]):r for r in cases}
    per_simulation = []
    reversals = 0
    changed_counts = 0
    undefined = 0
    zero = 0
    for seed in SEEDS:
        for mode in BACKGROUNDS:
            rows=[by_key[(seed,mode,p)] for p in PHASES_SECONDS]
            rhos=[r["descriptive_rho"] for r in rows]
            defined=[x for x in rhos if x is not None]
            neg=any(x<0 for x in defined)
            pos=any(x>0 for x in defined)
            has_zero=any(x==0 for x in defined)
            crosses=neg and pos
            incomplete=len(defined)!=len(PHASES_SECONDS)
            drift=len({r["eligible_lagged_bins"] for r in rows})!=1
            reversals+=int(crosses)
            changed_counts+=int(drift)
            undefined+=int(incomplete)
            zero+=int(has_zero)
            per_simulation.append({
                "seed":seed,"background":mode,
                "defined_phase_coefficients":len(defined),
                "strict_rho_sign_reversal":crosses,
                "eligible_bin_count_changed":drift,
                "zero_rho_observed":has_zero,
                "eligible_counts_by_phase":[r["eligible_lagged_bins"] for r in rows],
                "rho_range":(max(defined)-min(defined) if len(defined)>=2 else None),
            })
    contrasts=[]
    opposing=0
    for mode in BACKGROUNDS:
        for phase in PHASES_SECONDS[1:]:
            deltas=[]
            for seed in SEEDS:
                a=by_key[(seed,mode,0)]["descriptive_rho"]
                b=by_key[(seed,mode,phase)]["descriptive_rho"]
                deltas.append(None if a is None or b is None else b-a)
            conflict=any(x is not None and x<0 for x in deltas) and any(
                x is not None and x>0 for x in deltas)
            opposing+=int(conflict)
            contrasts.append({
                "background":mode,"compared_origin_seconds":phase,
                "paired_deltas_by_seed":deltas,
                "opposing_signed_deltas_between_seeds":conflict,
                "original_simulation_count":len(SEEDS),
                "phase_views_are_independent":False,
            })
    if reversals:
        state="SIGN_REVERSAL_OBSERVED"
    elif undefined or zero:
        state="SIGN_STABILITY_UNDETERMINED"
    else:
        state="NO_REVERSAL_IN_TINY_SYNTHETIC_SAMPLE"
    return {
        "schema_version":"abides-public-l2-phase-fragility-audit-v1",
        "descriptive_state":state,
        "original_independent_market_simulations":len(SEEDS)*len(BACKGROUNDS),
        "correlated_analytic_views":len(cases),
        "simulations_with_strict_sign_reversal":reversals,
        "simulations_with_changed_eligible_bin_count":changed_counts,
        "simulations_with_undefined_phase_rho":undefined,
        "simulations_with_exact_zero_rho":zero,
        "contrasts_with_opposing_seed_directions":opposing,
        "per_original_simulation":per_simulation,
        "paired_contrast_sign_checks":contrasts,
        "complete_public_book_digest_available":checked[
            "full_public_tape_digest_available_all_phases"],
        "source_archive_complete_verified":False,
        "source_content_authenticated":False,
        "real_market_false_alarm_rate_estimated":False,
        "physical_owner_count_known":False,
        "scientific_stage2_release_allowed":False,
        "live_trading_allowed":False,
        "limitations":[
            "Clock-origin shifts of the same simulated tape are not independent.",
            "Differences in eligible clock bins confound changes in rho.",
            "Two seeds per background cannot support inferential calibration.",
            "Zero or undefined rho prevents a robust sign assertion.",
            "A repeated statistical pattern does not identify any physical bot.",
        ]
    }
