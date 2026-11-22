#!/usr/bin/env python3
"""Genuine 16-run source-controlled ABIDES public timestamp-cluster diagnostics.

Frozen on locally new seeds 3201..3204 after the toy exact 13-cluster
permutation study, not independent real market bot identity evidence.
Compare prior *per print* 45s/20s ratio >= .60 against an identical
*per distinct exchange timestamp* ratio >= .60, without fitting phase.
Source-agent oracle is consulted only AFTER all public inference.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from abides_export import UPSTREAM_COMMIT
from abides_background_ratio_holdout import (
    public_ratio_decision, THRESHOLD as LEGACY_THRESHOLD,
    MIN_PRINTS, MIN_20S_GRID_HITS, MIN_LAGGED_L2_BINS
)
from abides_multiscale_public_l2 import (
    START, END, BOOK_DEPTH, public_multiscale_l2_summary
)
from l2_trade_context import PublicExecution,public_projection,MAX_FILLS
from research_seed_registry import read_ledger

ROOT=Path(__file__).resolve().parents[1]
PLAN=ROOT/"research"/"abides_clustered_grid_source_precommit_20261121.json"
SEEDS=(3201,3202,3203,3204)
COHORTS=("poisson_noise_null","fixed_20s_noise_hard_negative",
         "momentum_noise_hard_negative","twap_45s_positive")
DAY_NS=86_400_000_000_000
ANCHOR_NS=34_260_000_000_000
PERIODS=(20,45)
TOL_NS=250_000_000
THRESHOLD=0.60
CLUSTER_MIN_HITS20=8
FIELDS=frozenset((
    "seed","cohort","public_execution_prints","public_l2_snapshot_events",
    "public_tape_sha256","distinct_execution_timestamp_clusters",
    "dependent_same_timestamp_extra_prints","largest_exact_timestamp_cluster",
    "print_grid_hits20","print_grid_hits45","grouped_grid_hits20",
    "grouped_grid_hits45","per_print_observed_ratio",
    "per_unique_timestamp_observed_ratio",
    "original_per_print_decision","original_per_print_abstain_reason",
    "grouped_timestamp_decision","grouped_timestamp_abstain_reason",
    "eligible_completed_previous_30s_l2_bins",
    "posthoc_injected_target_present","posthoc_source_controlled_TWAP_fills",
    "original_per_print_false_alarm","grouped_timestamp_false_alarm",
    "original_per_print_target_miss","grouped_timestamp_target_miss",
    "original_per_print_target_abstained","grouped_timestamp_target_abstained",
    "actual_real_owner_IDs_available","public_feature_touched_private_agent_IDs",
    "original_source_complete_real_exchange_feed_proven",
    "source_raw_execution_or_L2_rows_exported","real_market_FDR_calibrated"
))
STATUSES=("ABSTAIN","TARGET_PATTERN","NO_TARGET_PATTERN")
ABSTAIN_CODES=("TOO_FEW_PUBLIC_PRINTS","TOO_FEW_DISTINCT_20S_HITS",
               "TOO_FEW_ELIGIBLE_COMPLETED_L2_BINS")


def frozen_plan()->dict:
    p=json.loads(PLAN.read_text(encoding="utf-8"))
    f=p.get("frozen_clock_feature",{})
    source=p.get("configurations",{})
    if (
        p.get("schema_version")!="abides-public-clustered-grid-16source-precommit-v1"
        or p.get("source_type")!="genuine ABIDES-NG matching engine synthetic ONLY"
        or p.get("new_source_status")!="NOT_RUN"
        or p.get("motivating_exact_toy_source_ci")!=44938416432
        or p.get("previous_inspected_source_runs")!=[44936592641,44937478576]
        or p.get("upstream_engine_source_commit")!=UPSTREAM_COMMIT
        or p.get("new_local_seed_candidates")!=list(SEEDS)
        or p.get("globally_blind_seed_novelty_not_certified") is not True
        or p.get("source_clock_interval_exchange_local")!=[START,END]
        or p.get("market_symbol")!="ABM"
        or p.get("book_depth_levels")!=BOOK_DEPTH
        or p.get("cohorts")!=list(COHORTS)
        or p.get("planned_independent_matching_engine_runs")!=16
        or f.get("clock_anchor_seconds_after_exchange_midnight")!=34260
        or f.get("periods_seconds")!=list(PERIODS)
        or f.get("tolerance_ns")!=TOL_NS
        or f.get("legacy_print_grid_ratio_threshold")!=THRESHOLD
        or f.get("new_timestamp_cluster_grid_ratio_threshold")!=THRESHOLD
        or f.get("no_optimizer_fit_threshold_or_phase_on_new_source") is not True
        or f.get("min_public_prints_for_either_rule")!=MIN_PRINTS
        or f.get("min_grid20_print_hits_for_legacy_decision")!=MIN_20S_GRID_HITS
        or f.get("min_grid20_distinct_timestamp_hits_for_cluster_decision")!=CLUSTER_MIN_HITS20
        or f.get("min_eligible_prior_completed_30second_l2_bins")!=MIN_LAGGED_L2_BINS
        or f.get("same_timestamp_exact_ns_only") is not True
        or f.get("timestamp_cluster_not_equivalent_to_parent_or_owner") is not True
        or p.get("posthoc_private_TWAP_agent_labels_only_after_both_public_scores") is not True
        or p.get("no_raw_execution_tape_l2_snapshots_or_private_oracle_agent_ID_export") is not True
        or p.get("all_negative_results_and_seed_cohorts_retained") is not True
        or p.get("not_real_market_owner_precision_pvalue_or_FDR_calibration") is not True
    ):
        raise ValueError("Precommitted ABIDES clustered source and threshold were altered")
    expected={
        "poisson_noise_null":(60,True,0,0),
        "fixed_20s_noise_hard_negative":(60,False,0,0),
        "momentum_noise_hard_negative":(50,True,10,0),
        "twap_45s_positive":(60,True,0,1)
    }
    if set(source)!=set(expected):
        raise ValueError("Unknown or missing source background family")
    for name,(noise,poisson,momentum,twap) in expected.items():
        v=source[name]
        if (
            v.get("noise_agents")!=noise or v.get("poisson_arrival") is not poisson
            or v.get("noise_wakeup_seconds")!=20
            or v.get("momentum_agents")!=momentum
            or v.get("twap_agents")!=twap
        ):
            raise ValueError("Prior background/target simulator settings changed")
    m=source["momentum_noise_hard_negative"]
    t=source["twap_45s_positive"]
    if (
        (m.get("momentum_wakeup_seconds"),m.get("momentum_poisson"),
         m.get("short_window"),m.get("long_window"))!=(25,True,5,15)
        or (t.get("twap_period_seconds"),t.get("twap_quantity_lots"),
            t.get("twap_direction"),t.get("twap_order_style"),
            t.get("twap_offset_session_seconds"))!=(45,1200,"BID","market",60)
    ):
        raise ValueError("Original injected TWAP or momentum source drift")
    return p


def check_seed_registry()->None:
    l=read_ledger()
    matches=[x for x in l["studies"] if x["id"]=="genuine_abides_public_cluster_ratio_16run"]
    if len(matches)!=1 or matches[0].get("seeds")!=list(SEEDS):
        raise ValueError("New canonical genuinely synthetic local seed study is not registered")
    if (matches[0].get("source_file")!="tools/abides_clustered_grid_holdout.py"
        or matches[0].get("source_constant")!="SEEDS"):
        raise ValueError("Frozen source seed provenance does not match file")


def score_public_timestamp_clusters(
    public:tuple[PublicExecution,...],original_measured:dict
)->dict:
    """Only source-visible print fields, no ABIDES owner, even when equal-time."""
    if type(public) is not tuple or not 1<=len(public)<=MAX_FILLS:
        raise ValueError("Missing or oversized anonymous source-execution tape")
    legacy=public_ratio_decision(original_measured)
    if legacy["public_prints"]!=len(public):
        raise ValueError("Public source count inconsistent with original measured L2")
    stamps=[]
    prev=-1
    day=None
    for x in public:
        if type(x) is not PublicExecution:
            raise ValueError("Synthetic private oracle field not allowed in public projection")
        t=x.time_ns
        if (type(t) is not int or t<0 or t<prev
            or type(x.quantity) is not int or x.quantity<=0
            or type(x.price_cents) is not int or x.price_cents<=0
            or x.reported_aggressor_side not in ("BUY","SELL")):
            raise ValueError("Invalid public source print ordering or payload")
        if day is None:day=t//DAY_NS
        if day!=t//DAY_NS:
            raise ValueError("Cannot combine multiple exchange session dates")
        if not 34_200_000_000_000<=t%DAY_NS<34_680_000_000_000:
            raise ValueError("Public source execution outside frozen local session")
        prev=t
        stamps.append(t)
    mult=Counter(stamps)
    unique=tuple(sorted(mult))
    if not 1<=len(unique)<=len(public):
        raise AssertionError("Distinct execution-time cluster counting failed")
    grouped={}
    for period in PERIODS:
        cycle=period*1_000_000_000
        grouped[str(period)]=sum(
            min(rem,cycle-rem)<=TOL_NS
            for timestamp in unique
            for rem in ((timestamp-ANCHOR_NS)%cycle,)
        )
    h20,h45=grouped["20"],grouped["45"]
    eligible=legacy["eligible_completed_prior_l2_bins_30s"]
    if len(public)<MIN_PRINTS:
        why="TOO_FEW_PUBLIC_PRINTS"
    elif h20<CLUSTER_MIN_HITS20:
        why="TOO_FEW_DISTINCT_20S_HITS"
    elif eligible<MIN_LAGGED_L2_BINS:
        why="TOO_FEW_ELIGIBLE_COMPLETED_L2_BINS"
    else:
        why=None
    decision=(
        "ABSTAIN" if why else
        "TARGET_PATTERN" if h45/h20>=THRESHOLD else
        "NO_TARGET_PATTERN"
    )
    result={
        "public_execution_prints":len(public),
        "public_l2_snapshot_events":legacy["public_l2_snapshots"],
        "public_tape_sha256":legacy["public_tape_sha256"],
        "distinct_execution_timestamp_clusters":len(unique),
        "dependent_same_timestamp_extra_prints":len(public)-len(unique),
        "largest_exact_timestamp_cluster":max(mult.values()),
        "print_grid_hits20":legacy["public_20s_hits"],
        "print_grid_hits45":legacy["public_45s_hits"],
        "grouped_grid_hits20":h20,
        "grouped_grid_hits45":h45,
        "per_print_observed_ratio":legacy["observed_ratio_45s_over_20s"],
        "per_unique_timestamp_observed_ratio":round(h45/h20,8) if h20 else None,
        "original_per_print_decision":legacy["decision"],
        "original_per_print_abstain_reason":legacy["abstain_reason"],
        "grouped_timestamp_decision":decision,
        "grouped_timestamp_abstain_reason":why,
        "eligible_completed_previous_30s_l2_bins":eligible,
        "actual_real_owner_IDs_available":False,
        "public_feature_touched_private_agent_IDs":False,
        "original_source_complete_real_exchange_feed_proven":False,
        "source_raw_execution_or_L2_rows_exported":False,
        "real_market_FDR_calibrated":False
    }
    return result


def simulate_case(seed:int,cohort:str)->dict:
    frozen_plan()
    check_seed_registry()
    if type(seed) is not int or seed not in SEEDS or cohort not in COHORTS:
        raise ValueError("Only 16 preregistered source seed/cohort cases allowed")
    from abides_markets.config_system import SimulationBuilder
    from abides_markets.config_system.agent_configs import (
        NoiseAgentConfig,MomentumAgentConfig,TWAPExecutionAgentConfig)
    from abides_markets.config_system.models import ExchangeConfig
    from abides_markets.simulation import ResultProfile,run_simulation
    builder=(SimulationBuilder().apply_template("liquid_market")
             .ticker("ABM").start_time(START).end_time(END)
             .exchange(ExchangeConfig(book_capture="l2",book_log_depth=BOOK_DEPTH))
             .seed(seed))
    settings=frozen_plan()["configurations"][cohort]
    builder=builder.enable_agent(NoiseAgentConfig(
        multi_wake=True,wake_up_freq="20s",
        poisson_arrival=settings["poisson_arrival"],
        noise_mkt_close_time=END),count=settings["noise_agents"])
    if cohort=="momentum_noise_hard_negative":
        builder=builder.enable_agent(MomentumAgentConfig(
            min_size=1,max_size=10,wake_up_freq="25s",
            poisson_arrival=True,short_window=5,long_window=15),count=10)
    if cohort=="twap_45s_positive":
        builder=builder.enable_agent(TWAPExecutionAgentConfig(
            start_time_offset="00:01:00",end_time_offset="00:01:00",
            freq="45s",direction="BID",quantity=1200,trade=True,
            order_style="market"),count=1)
    sim=run_simulation(builder.build(),profile=ResultProfile.QUANT)
    market=sim.markets["ABM"]
    if not market.trades or market.l2_series is None:
        raise RuntimeError("Original source matching engine public executions/L2 missing")
    public=public_projection(market.trades)
    public_measured=public_multiscale_l2_summary(public,market.l2_series)
    inferred=score_public_timestamp_clusters(public,public_measured)
    # SOURCE PRIVATE ORACLE READ ONLY AFTER BOTH PUBLIC SCORES FINISHED.
    controlled={int(a.agent_id) for a in sim.agents
                if str(a.agent_name).startswith("TWAP_EXECUTION_AGENT_")}
    target=cohort=="twap_45s_positive"
    if len(controlled)!=(1 if target else 0):
        raise RuntimeError("Source controlled target configuration drift")
    controlled_fills=sum(x.passive_agent_id in controlled or
                         x.aggressive_agent_id in controlled for x in market.trades)
    if (controlled_fills>0)!=target:
        raise RuntimeError("Injected source posthoc target execution missing")
    old=inferred["original_per_print_decision"]
    new=inferred["grouped_timestamp_decision"]
    result={
        "seed":seed,"cohort":cohort,**inferred,
        "posthoc_injected_target_present":target,
        "posthoc_source_controlled_TWAP_fills":controlled_fills,
        "original_per_print_false_alarm":old=="TARGET_PATTERN" and not target,
        "grouped_timestamp_false_alarm":new=="TARGET_PATTERN" and not target,
        "original_per_print_target_miss":old=="NO_TARGET_PATTERN" and target,
        "grouped_timestamp_target_miss":new=="NO_TARGET_PATTERN" and target,
        "original_per_print_target_abstained":old=="ABSTAIN" and target,
        "grouped_timestamp_target_abstained":new=="ABSTAIN" and target
    }
    if set(result)!=FIELDS:
        raise AssertionError("Result leaked private oracle/missing published fields")
    return result


def validate_original_cases(cases:list[dict])->dict:
    frozen_plan()
    check_seed_registry()
    expected={(s,c) for s in SEEDS for c in COHORTS}
    if (type(cases) is not list or len(cases)!=16 or
        any(type(x) is not dict or set(x)!=FIELDS for x in cases)
        or {(x["seed"],x["cohort"]) for x in cases}!=expected):
        raise ValueError("Missing, duplicated or altered original ABIDES cohort/seed")
    cohort_summaries={}
    for cohort in COHORTS:
        subset=[x for x in cases if x["cohort"]==cohort]
        for x in subset:
            target=cohort=="twap_45s_positive"
            n=x["public_execution_prints"]
            uniq=x["distinct_execution_timestamp_clusters"]
            h20=x["grouped_grid_hits20"]
            h45=x["grouped_grid_hits45"]
            ph20=x["print_grid_hits20"]
            ph45=x["print_grid_hits45"]
            eligible=x["eligible_completed_previous_30s_l2_bins"]
            if (type(n) is not int or n<=0 or
                type(uniq) is not int or not 0<uniq<=n or
                any(type(q) is not int or q<0 or q>n for q in
                    (ph20,ph45)) or
                any(type(q) is not int or q<0 or q>uniq for q in
                    (h20,h45)) or
                type(x["dependent_same_timestamp_extra_prints"]) is not int or
                x["dependent_same_timestamp_extra_prints"]!=n-uniq or
                type(x["largest_exact_timestamp_cluster"]) is not int or
                not 1<=x["largest_exact_timestamp_cluster"]<=n or
                type(eligible) is not int or eligible<0 or
                type(x["public_l2_snapshot_events"]) is not int or
                x["public_l2_snapshot_events"]<=0):
                raise ValueError("Invalid public source cluster cardinality or L2")
            if (x["per_print_observed_ratio"]!=(round(ph45/ph20,8) if ph20 else None)
                or x["per_unique_timestamp_observed_ratio"]!=
                   (round(h45/h20,8) if h20 else None)):
                raise ValueError("Source public clock ratio not conserved")
            oldwhy=("TOO_FEW_PUBLIC_PRINTS" if n<MIN_PRINTS else
                    "TOO_FEW_20S_CLOCK_HITS" if ph20<MIN_20S_GRID_HITS else
                    "TOO_FEW_ELIGIBLE_COMPLETED_L2_BINS" if eligible<MIN_LAGGED_L2_BINS else None)
            newwhy=("TOO_FEW_PUBLIC_PRINTS" if n<MIN_PRINTS else
                    "TOO_FEW_DISTINCT_20S_HITS" if h20<CLUSTER_MIN_HITS20 else
                    "TOO_FEW_ELIGIBLE_COMPLETED_L2_BINS" if eligible<MIN_LAGGED_L2_BINS else None)
            old=("ABSTAIN" if oldwhy else
                 "TARGET_PATTERN" if ph45/ph20>=THRESHOLD else "NO_TARGET_PATTERN")
            new=("ABSTAIN" if newwhy else
                 "TARGET_PATTERN" if h45/h20>=THRESHOLD else "NO_TARGET_PATTERN")
            if (x["original_per_print_decision"]!=old
                or x["original_per_print_abstain_reason"]!=oldwhy
                or x["grouped_timestamp_decision"]!=new
                or x["grouped_timestamp_abstain_reason"]!=newwhy
                or x["posthoc_injected_target_present"] is not target
                or type(x["posthoc_source_controlled_TWAP_fills"]) is not int
                or (x["posthoc_source_controlled_TWAP_fills"]>0)!=target
                or x["original_per_print_false_alarm"] is not (old=="TARGET_PATTERN" and not target)
                or x["grouped_timestamp_false_alarm"] is not (new=="TARGET_PATTERN" and not target)
                or x["original_per_print_target_miss"] is not (old=="NO_TARGET_PATTERN" and target)
                or x["grouped_timestamp_target_miss"] is not (new=="NO_TARGET_PATTERN" and target)
                or x["original_per_print_target_abstained"] is not (old=="ABSTAIN" and target)
                or x["grouped_timestamp_target_abstained"] is not (new=="ABSTAIN" and target)
                or any(x[key] is not False for key in (
                    "actual_real_owner_IDs_available",
                    "public_feature_touched_private_agent_IDs",
                    "original_source_complete_real_exchange_feed_proven",
                    "source_raw_execution_or_L2_rows_exported",
                    "real_market_FDR_calibrated"))
                or type(x["public_tape_sha256"]) is not str or
                len(x["public_tape_sha256"])!=64):
                raise ValueError("Frozen score, oracle scope, completeness or decision changed")
        cohort_summaries[cohort]={
            "independent_original_matching_engine_runs":4,
            "original_print_based_false_alarms":sum(x["original_per_print_false_alarm"] for x in subset),
            "grouped_timestamp_false_alarms":sum(x["grouped_timestamp_false_alarm"] for x in subset),
            "original_print_based_missed_TWAP":sum(x["original_per_print_target_miss"] for x in subset),
            "grouped_timestamp_missed_TWAP":sum(x["grouped_timestamp_target_miss"] for x in subset),
            "original_print_based_abstentions":sum(x["original_per_print_decision"]=="ABSTAIN" for x in subset),
            "grouped_timestamp_abstentions":sum(x["grouped_timestamp_decision"]=="ABSTAIN" for x in subset),
            "original_print_based_positive_alarms":sum(x["original_per_print_decision"]=="TARGET_PATTERN" for x in subset),
            "grouped_timestamp_positive_alarms":sum(x["grouped_timestamp_decision"]=="TARGET_PATTERN" for x in subset),
            "posthoc_controlled_TWAP_fills":sum(x["posthoc_source_controlled_TWAP_fills"] for x in subset),
            "public_prints_total":sum(x["public_execution_prints"] for x in subset),
            "unique_event_timestamp_clusters_total":sum(x["distinct_execution_timestamp_clusters"] for x in subset),
            "extra_same_timestamp_prints_total":sum(x["dependent_same_timestamp_extra_prints"] for x in subset)
        }
    return {
        "schema_version":"genuine-abides-public-clustered-timestamp-16case-original-v1",
        "original_preregistered_protocol":"research/abides_clustered_grid_source_precommit_20261121.json",
        "independent_genuine_matching_engine_cases":16,
        "locally_new_seed_values_not_globally_blind":list(SEEDS),
        "original_anonymous_case_aggregates":cases,
        "source_cohort_comparison":cohort_summaries,
        "same_timestamp_group_does_not_prove_same_parent_market_order":True,
        "threshold_or_phase_selected_after_source":False,
        "private_simulated_oracle_used_only_after_public_inference":True,
        "real_market_owner_FDR_or_precision_calibrated":False,
        "source_original_exchange_data_or_commercial_trading_used":False,
        "raw_event_l2_rows_or_private_agent_IDs_exported":False,
        "limitations":[
            "Synthetic ABIDES markets not real-world exchange account/parent-order ground truth.",
            "Same timestamp may contain independent aggressive orders as well as split fills.",
            "Original ratio 0.60 selected using prior inspected seeds, not new holdout.",
            "Grouping exact nanosecond timestamps changes effective weighting and sensitivity.",
            "No valid market conditional p-values, original full exchange depth or actor FDR.",
            "No privately identifiable agent IDs enter source-public features."
        ]
    }


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    if a.output.exists():
        p.error("Refuse to overwrite original genuine source experiment")
    cases=[simulate_case(s,c) for s in SEEDS for c in COHORTS]
    result=validate_original_cases(cases)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("x",encoding="utf-8") as f:
        json.dump(result,f,sort_keys=True,indent=2,allow_nan=False)
        f.write("\n")
    print("ABIDES_CLUSTERED_TIMESTAMP_16_SOURCE_RESULTS",json.dumps(
        result["source_cohort_comparison"],sort_keys=True))
    print("ABIDES_CLUSTERED_TIMESTAMP_ORIGINAL_COMPLETED",json.dumps({
        "source_matching_engine_cases":16,"no_real_market_FDR":True,
        "no_private_oracle_agent_ID_export":True
    },sort_keys=True))


if __name__=="__main__":
    main()
