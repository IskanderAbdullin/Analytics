#!/usr/bin/env python3
"""Exhaustive 13-position cluster-cardinality permutation under a TOY null.

All timestamps fixed, exactly one 100-fill cluster and twelve single fills.
Reassigning which timestamp has the large cluster preserves public timestamp
support and multiset of cluster sizes. This is an exact combinatorial
counterexample, NOT a realistic market-shuffle p-value or bot-owner FDR.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from l2_trade_context import PublicExecution
from public_timing_phase_tied_fills import (
    build_synthetic_public,phase_counts,ANCHOR_NS,PERIODS,TOL_NS,THRESHOLD
)

ROOT=Path(__file__).resolve().parents[1]
PLAN=ROOT/"research"/"public_cluster_permutation_precommit_20261121.json"
N_TIMES=13
LARGE_CLUSTER=100
SMALL_CLUSTER=1
TOTAL_FILLS=112
FROZEN_CLUSTER_SIZES=(1,)*12+(100,)


def frozen_plan()->dict:
    p=json.loads(PLAN.read_text(encoding="utf-8"))
    if (p.get("schema_version")!="public-clock-cluster-size-permutation-exact-precommit-v1"
        or p.get("scientific_stage")!="RD-CONDITIONAL-NULL-12"
        or p.get("source_type")!="constructed toy only, no source market vendor or ABIDES raw tape"
        or p.get("previous_source_free_control_run")!=44937958809
        or p.get("source_public_model")!="13 unique timestamp clusters; exactly one cluster size 100, twelve size 1"
        or p.get("source_grid_clock_anchor_exchange_local_seconds_after_midnight")!=ANCHOR_NS//1_000_000_000
        or p.get("fixed_grid_periods_seconds")!=list(PERIODS)
        or p.get("tolerance_ns")!=TOL_NS
        or p.get("ratio_threshold")!=THRESHOLD
        or p.get("exhaustive_permutation_count")!=N_TIMES
        or p.get("cluster_cardinality_multiset")!=list(FROZEN_CLUSTER_SIZES)
        or p.get("timestamp_support_unchanged") is not True
        or p.get("total_public_fill_count_unchanged") is not True
        or p.get("all_13_placements_required_even_if_non_alarm") is not True
        or p.get("no_random_seeds_or_sampling_required") is not True
        or p.get("no_best_grid_phase_or_threshold_selection") is not True
        or p.get("event_parent_owner_identity_unidentifiable") is not True
        or p.get("tail_frequency_is_toy_conditional_not_market_p_value_or_FDR") is not True
        or p.get("raw_source_event_timestamps_or_owner_IDs_not_exported") is not True):
        raise ValueError("Source-free cluster conditional null drifted after preregistration")
    return p


def exhaustive_public_cluster_placements()->dict:
    frozen_plan()
    canonical=build_synthetic_public(split_fills=1)
    timestamp_support=sorted({x.time_ns for x in canonical})
    if len(timestamp_support)!=N_TIMES or len(canonical)!=N_TIMES:
        raise AssertionError("Original prior 13-timestamp scenario changed")
    rows=[]
    unique_ratio=None
    for large_at in range(N_TIMES):
        obs=[]
        for i,t in enumerate(timestamp_support):
            repeats=LARGE_CLUSTER if i==large_at else SMALL_CLUSTER
            for _ in range(repeats):
                obs.append(PublicExecution(t,100100,1,"BUY"))
        public=tuple(obs)
        if len(public)!=TOTAL_FILLS or len(set(x.time_ns for x in public))!=N_TIMES:
            raise AssertionError("Conditional cluster cardinality changed")
        original=phase_counts(public,shift_ms=0,collapse_same_timestamp=False)
        grouped=phase_counts(public,shift_ms=0,collapse_same_timestamp=True)
        if unique_ratio is None:
            unique_ratio=grouped["observed_ratio_45s_over_20s"]
        if grouped["observed_ratio_45s_over_20s"]!=unique_ratio:
            raise AssertionError("Cluster-grouped timestamp statistics should be invariant")
        # Report only time-grid CLASS, not raw timestamp/price/order data.
        original_t=timestamp_support[large_at]
        period_hits=[]
        for p in PERIODS:
            period_ns=p*1_000_000_000
            phase=(original_t-ANCHOR_NS)%period_ns
            period_hits.append(min(phase,period_ns-phase)<=TOL_NS)
        category=("both" if period_hits==[True,True] else
                  "20_only" if period_hits==[True,False] else
                  "45_only" if period_hits==[False,True] else
                  "neither")
        rows.append({
            "synthetic_placement_ordinal":large_at,
            "large_cluster_grid_category":category,
            "public_execution_prints":len(public),
            "unique_timestamps":N_TIMES,
            "print_weighted_grid20_hits":original["hit_counts"]["20"],
            "print_weighted_grid45_hits":original["hit_counts"]["45"],
            "print_weighted_ratio":original["observed_ratio_45s_over_20s"],
            "print_weighted_threshold_alarm":original["fixed_ratio_0_60_alarm"],
            "grouped_unique_timestamp_ratio":grouped["observed_ratio_45s_over_20s"],
            "grouped_unique_timestamp_alarm":grouped["fixed_ratio_0_60_alarm"],
            "source_owner_labels_known":False
        })
    if len(rows)!=N_TIMES or len({x["synthetic_placement_ordinal"] for x in rows})!=N_TIMES:
        raise AssertionError("Missing one of exact 13 precommitted cluster placements")
    alarms=sum(x["print_weighted_threshold_alarm"] for x in rows)
    categories=Counter(x["large_cluster_grid_category"] for x in rows)
    if (categories!={"20_only":11,"both":1,"45_only":1}
        or alarms!=2
        or unique_ratio!=round(2/12,8)
        or any(x["grouped_unique_timestamp_alarm"] for x in rows)):
        raise AssertionError("Exact cluster-placement combinatorics not replicated")
    return {
        "schema_version":"public-cluster-permutation-toy-null-original-v1",
        "original_precommitted_protocol":"research/public_cluster_permutation_precommit_20261121.json",
        "source_constructed_not_original_market_or_ABIDES":True,
        "fixed_public_unique_event_timestamps":N_TIMES,
        "fixed_public_fill_count_in_every_case":TOTAL_FILLS,
        "exact_exchangeable_cluster_placements":N_TIMES,
        "all_placements":rows,
        "large_cluster_position_categories":dict(categories),
        "print_weighted_false_alarms_under_toy_no_target":alarms,
        "grouped_timestamp_false_alarms_under_toy_no_target":0,
        "toy_exchangeable_placement_alarm_frequency":round(alarms/N_TIMES,8),
        "not_a_real_market_p_value_or_FDR":True,
        "no_owner_or_parent_order_identity_recovered":True,
        "no_source_raw_public_timestamp_series_exported":True,
        "phase_or_threshold_fitted_posthoc":False,
        "original_market_trading_or_broker_placement_enabled":False,
        "limitations":[
            "Toy placement exchangeability is an assumption, not real market temporal causality.",
            "Equal timestamps might reflect separate aggressive parent orders.",
            "Holding timestamp support and cluster sizes fixed does not preserve arbitrary latent background processes.",
            "2/13 is a combinatorial toy conditional frequency, NOT real exchange FDR or calibrated statistical p-value.",
            "Clock phase fixed in advance; no hidden best phase selection."
        ]
    }


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():
        p.error("Never overwrite exact conditional-null source-free evidence")
    x=exhaustive_public_cluster_placements()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("x",encoding="utf-8") as f:
        json.dump(x,f,sort_keys=True,indent=2,allow_nan=False)
        f.write("\n")
    print("EXHAUSTIVE_CLUSTER_SIZE_NULL",json.dumps({
        "exact_placements":x["exact_exchangeable_cluster_placements"],
        "false_alarms_naive_print_weighted":x["print_weighted_false_alarms_under_toy_no_target"],
        "false_alarms_unique_time":x["grouped_timestamp_false_alarms_under_toy_no_target"],
        "conditional_toy_alarms":x["toy_exchangeable_placement_alarm_frequency"],
        "real_market_FDR_known":False
    },sort_keys=True))


if __name__=="__main__":
    main()
