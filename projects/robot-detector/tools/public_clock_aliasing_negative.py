#!/usr/bin/env python3
"""Exact, source-free modular aliasing counterexample for public trade rhythms.

This establishes that an *unrelated* fixed 20-second background can
periodically coincide with a fixed 45-second clock grid. It does NOT
identify a real trading bot, infer causal agent relationships, or turn
a deterministic lattice into a probabilistic/null market calibration.
"""
from __future__ import annotations

from math import gcd
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
PROTOCOL=ROOT/"research"/"abides_multiscale_public_l2_protocol_20261121.json"
OBSERVED=ROOT/"fixtures"/"abides_multiscale_public_l2_observed_20261121.json"
NS=1_000_000_000
ANCHOR=34_260
TOL_NS=250_000_000


def aliasing_lattice(
    source_period_seconds:int,
    observed_grid_seconds:int,
    *,
    source_phase_ns:int=0,
    n_source_events:int=90,
    grid_origin_ns:int=ANCHOR*NS,
    tolerance_ns:int=TOL_NS
)->dict:
    """Public schedule only: t_i = grid origin + source phase + i*P.

    No source IDs, hidden labels, statistical fitting or original L2 rows.
    Invariant: calendar timestamps are not inferred from exchange order IDs.
    """
    for name,val in (
        ("source_period",source_period_seconds),
        ("grid_period",observed_grid_seconds),
        ("source_phase",source_phase_ns),
        ("n",n_source_events),
        ("grid_origin",grid_origin_ns),
        ("tolerance",tolerance_ns)
    ):
        if type(val) is not int:
            raise ValueError(f"Clock aliasing expects exact integer {name}")
    if (
        not 1<=source_period_seconds<=3600
        or not 1<=observed_grid_seconds<=3600
        or not 1<=n_source_events<=10000
        or not 0<=source_phase_ns<observed_grid_seconds*NS
        or grid_origin_ns<0
        or not 0<=tolerance_ns<min(source_period_seconds,observed_grid_seconds)*NS//2
    ):
        raise ValueError("Unsupported or posthoc-unbounded clock lattice")
    source_ns=source_period_seconds*NS
    grid_ns=observed_grid_seconds*NS
    hits=0
    for i in range(n_source_events):
        t=grid_origin_ns+source_phase_ns+i*source_ns
        rem=(t-grid_origin_ns)%grid_ns
        hits+=min(rem,grid_ns-rem)<=tolerance_ns
    common=gcd(source_period_seconds,observed_grid_seconds)
    lcm_seconds=source_period_seconds//common*observed_grid_seconds
    return {
        "schema_version":"public-clock-exact-lattice-aliasing-negative-v1",
        "source_background_period_seconds":source_period_seconds,
        "independent_observation_grid_period_seconds":observed_grid_seconds,
        "source_phase_ns":source_phase_ns,
        "fixed_observation_grid_origin_ns":grid_origin_ns,
        "fixed_tolerance_ns":tolerance_ns,
        "source_events_tested":n_source_events,
        "observed_public_grid_hits":hits,
        "descriptive_fraction_on_grid":round(hits/n_source_events,8),
        "gcd_of_periods_seconds":common,
        "lcm_of_periods_seconds":lcm_seconds,
        "complete_periodic_source_cycle_events":lcm_seconds//source_period_seconds,
        "public_clock_pattern_implies_injected_target":False,
        "real_market_owner_accuracy_or_FDR_measured":False,
        "oracle_agent_labels_used":False,
        "raw_event_timestamps_exported":False,
    }


def report_frozen_aliasing_negative()->dict:
    protocol=json.loads(PROTOCOL.read_text(encoding="utf-8"))
    observed=json.loads(OBSERVED.read_text(encoding="utf-8"))
    if (
        protocol["cohort_definitions"]["fixed_20s_noise_hard_negative"][
            "noise_wake"]!="20s"
        or 45 not in protocol["public_only_multiscale_features"][
            "grid_periods_seconds"]
        or protocol["public_only_multiscale_features"][
            "fixed_anchor_exchange_local_seconds_after_midnight"]!=ANCHOR
        or protocol["public_only_multiscale_features"][
            "fraction_window_ms"]!=TOL_NS//1_000_000
        or observed["original_research_run_id"]!=44935340284
        or observed["original_independent_simulation_runs"]!=12
        or observed["fixed_noise_45sec_grid_fraction_exceeds_twap_fraction"] is not True
    ):
        raise ValueError("Frozen prior multiscale source/aliasing evidence has changed")
    no_target=aliasing_lattice(20,45,n_source_events=90)
    shifted=aliasing_lattice(20,45,source_phase_ns=1*NS,n_source_events=90)
    if (
        no_target["gcd_of_periods_seconds"]!=5
        or no_target["lcm_of_periods_seconds"]!=180
        or no_target["observed_public_grid_hits"]!=10
        or shifted["observed_public_grid_hits"]!=0
    ):
        raise AssertionError("Exact modular source-free negative control drifted")
    return {
        "schema_version":"predeclared-public-20s-vs-45s-aliasing-control-v1",
        "frozen_prior_source_run":44935340284,
        "fixed_20s_no_twap_periodic_background":no_target,
        "one_second_shifted_20s_background":shifted,
        "45s_original_ABIDES_hard_negative_mean_fraction":observed[
            "source_cohort_descriptive_aggregates"][
                "fixed_20s_noise_hard_negative"][
                    "descriptive_mean_fraction_by_period"]["45"],
        "45s_original_ABIDES_positive_mean_fraction":observed[
            "source_cohort_descriptive_aggregates"][
                "twap_45s_positive"][
                    "descriptive_mean_fraction_by_period"]["45"],
        "interpretation":"An equal clock-grid timestamp is not unique evidence for injected TWAP: common period divides unrelated fixed background and observed grid; source-level market outcomes remain descriptive.",
        "neither_true_owner_identity_nor_market_FDR_established":True,
        "no_original_market_event_rows_or_agent_ids_used":True,
        "not_a_posthoc_optimized_classification_threshold":True,
    }


def main()->None:
    print("CLOCK_ALIASING_BACKGROUND_NEGATIVE",
          json.dumps(report_frozen_aliasing_negative(),sort_keys=True))


if __name__=="__main__":
    main()
