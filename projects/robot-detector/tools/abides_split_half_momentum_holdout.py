#!/usr/bin/env python3
"""Frozen independent ABIDES split-half cadence check vs momentum hard negatives.

This study was designed AFTER reviewing 3001-3004 where the whole-session
45s/20s ratio produced 2/4 momentum false alarms. Split, thresholds and
source seeds 3101..3104 were committed BEFORE new original source runs.
All inference consumes strictly public trades and L2. Oracle is read AFTER.
No inference about real actor identity, market FDR or live trading.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from abides_export import UPSTREAM_COMMIT
from abides_background_ratio_holdout import (
    public_ratio_decision,
    MIN_PRINTS,MIN_20S_GRID_HITS,MIN_LAGGED_L2_BINS,
    THRESHOLD as ORIGINAL_THRESHOLD
)
from abides_multiscale_public_l2 import (
    _clock_grid_features,public_multiscale_l2_summary,
    START,END,BOOK_DEPTH
)
from l2_trade_context import PublicExecution,public_projection,MAX_FILLS,MAX_SNAPSHOTS
from lagged_l2_bin import summarize_lagged_book
from research_seed_registry import read_ledger

ROOT=Path(__file__).resolve().parents[1]
PLAN=ROOT/"research"/"abides_split_half_momentum_precommit_20261121.json"
SEEDS=(3101,3102,3103,3104)
COHORTS=("poisson_noise_null","fixed_20s_noise_hard_negative",
         "momentum_noise_hard_negative","twap_45s_positive")
BEGIN_NS=34_200_000_000_000
SPLIT_NS=34_440_000_000_000
END_NS=34_680_000_000_000
HALF_NAMES=("early","late")
HALF_MIN_PRINTS=100
HALF_MIN_HITS20=4
HALF_MIN_ELIGIBLE_LAG=2
RATIO_THRESHOLD=0.60
ABSTENTION_CODES=(
    "NO_PUBLIC_PRINTS","HALF_PUBLIC_PRINTS_BELOW_100",
    "HALF_20S_GRID_HITS_BELOW_4","HALF_PREVIOUS_L2_BINS_BELOW_2"
)
HALF_FIELDS=frozenset((
    "half","public_execution_prints","fixed_20s_grid_hits",
    "fixed_45s_grid_hits","observed_hit_ratio_45_over_20",
    "eligible_completed_previous_30s_l2_bins",
    "previous_l2_abstain_reasons","passes_minimum_observability",
    "abstain_reason","private_agent_IDs_used"
))
CASE_FIELDS=frozenset((
    "seed","cohort","public_executed_prints","public_l2_snapshots",
    "public_tape_sha256","original_whole_session_baseline_decision",
    "original_whole_session_ratio_45_over_20",
    "new_split_half_decision","new_split_half_abstain_reason",
    "per_half_public_only","posthoc_injected_target_present",
    "posthoc_controlled_twap_execution_count","new_source_false_alarm",
    "new_source_target_missed","new_source_target_abstained",
    "public_feature_touched_private_agent_IDs",
    "real_market_owner_FDR_or_accuracy_calibrated",
    "source_complete_exchange_feed_proven",
    "original_source_raw_print_or_l2_rows_exported"
))
STATUSES=("ABSTAIN","TARGET_PATTERN","NO_TARGET_PATTERN")


def frozen_plan()->dict:
    p=json.loads(PLAN.read_text(encoding="utf-8"))
    f=p.get("public_only_feature",{})
    old=p.get("whole_session_comparator",{})
    if (
        p.get("schema_version")!="abides-public-two-half-ratio-momentum-negative-precommit-v1"
        or p.get("research_stage")!="RD-MOMENTUM-NEGATIVE-10"
        or p.get("original_previous_source_run_inspected")!=44936592641
        or p.get("upstream_abides_commit")!=UPSTREAM_COMMIT
        or p.get("new_locally_unused_seed_candidates")!=list(SEEDS)
        or p.get("globally_blind_unseen_seed_claim") is not False
        or p.get("original_matching_engine_cases_planned")!=16
        or p.get("cohorts")!=list(COHORTS)
        or p.get("same_simulator_cohort_configuration_as_ratio_source") is not True
        or p.get("simulator_clock_session_exchange_local")!=[START,END]
        or p.get("fixed_split_clock_exchange_local")!="09:34:00"
        or p.get("half_open_intervals_exchange_local")!=[
            ["09:30:00","09:34:00"],["09:34:00","09:38:00"]]
        or f.get("period_grid_seconds")!=[20,45]
        or f.get("fixed_phase_origin_exchange_local_seconds_after_midnight")!=34260
        or f.get("tolerance_ns")!=250000000
        or f.get("frozen_ratio_threshold_greater_or_equal")!=RATIO_THRESHOLD
        or f.get("half_minimum_public_execution_prints")!=HALF_MIN_PRINTS
        or f.get("half_minimum_public_20s_hits")!=HALF_MIN_HITS20
        or f.get("half_minimum_eligible_previous_completed_30s_l2_bins")!=HALF_MIN_ELIGIBLE_LAG
        or f.get("abstain_if_any_half_unqualified") is not True
        or f.get("no_phase_or_threshold_selection_after_results") is not True
        or old.get("original_source_run_id")!=44936592641
        or p.get("synthetic_oracle_agent_ids_only_accessible_after_all_public_feature_scoring") is not True
        or p.get("raw_source_trade_snapshots_or_agent_ids_must_not_be_exported") is not True
        or p.get("original_16_case_results_must_all_be_retained") is not True
        or p.get("no_market_FDR_pvalue_or_significance_claim") is not True
    ):
        raise ValueError("Frozen split-half ratio hypothesis/source design changed")
    return p


def check_seeds()->None:
    ledger=read_ledger()
    matching=[x for x in ledger["studies"]
              if x["id"]=="genuine_abides_split_half_momentum_16run"]
    if (len(matching)!=1 or matching[0]["seeds"]!=list(SEEDS)
            or matching[0].get("source_file")!=
               "tools/abides_split_half_momentum_holdout.py"
            or matching[0].get("source_constant")!="SEEDS"):
        raise ValueError("Missing independent seed reservation/source ledger")


def public_half_stability(public:tuple[PublicExecution,...],book)->dict:
    """No private-truth parameters. Previous completed L2 bin only."""
    frozen_plan()
    if type(public) is not tuple or not 0<len(public)<=MAX_FILLS:
        raise ValueError("Expected nonempty bounded public-only executed prints")
    if book is None or len(book.times_ns)>MAX_SNAPSHOTS:
        raise ValueError("Missing/oversized anonymous public L2")
    if any(type(x) is not PublicExecution or type(x.time_ns) is not int or
           not BEGIN_NS<=x.time_ns<END_NS for x in public):
        raise ValueError("Unknown public print class or out-of-session source time")
    # This recomputes all original and lagged source statistics on public-only
    # projections; the private truth is not even an argument.
    measured=public_multiscale_l2_summary(public,book)
    original=public_ratio_decision(measured)
    halves=[]
    for name,start,end in (
        (HALF_NAMES[0],BEGIN_NS,SPLIT_NS),
        (HALF_NAMES[1],SPLIT_NS,END_NS)
    ):
        trades=tuple(row for row in public if start<=row.time_ns<end)
        if not trades:
            half={
                "half":name,"public_execution_prints":0,
                "fixed_20s_grid_hits":0,"fixed_45s_grid_hits":0,
                "observed_hit_ratio_45_over_20":None,
                "eligible_completed_previous_30s_l2_bins":0,
                "previous_l2_abstain_reasons":{},
                "passes_minimum_observability":False,
                "abstain_reason":"NO_PUBLIC_PRINTS",
                "private_agent_IDs_used":False,
            }
        else:
            clock=_clock_grid_features(trades)
            h20,h45=(clock["grid_hit_counts"][key] for key in ("20","45"))
            l2=summarize_lagged_book(book,trades,bin_seconds=30,
                                    maximum_quote_age_seconds=30,
                                    maximum_depth=BOOK_DEPTH)
            eligible=l2["eligible_lagged_bins"]
            reasons=l2["abstained_clock_bins"]
            if (eligible+sum(reasons.values())!=
                l2["populated_execution_clock_bins"]
                or l2["private_agent_identifiers_used"] is not False
                or l2["previous_completed_bin_only"] is not True):
                raise AssertionError("One-half L2 conservation/causality failure")
            why=("HALF_PUBLIC_PRINTS_BELOW_100" if len(trades)<HALF_MIN_PRINTS else
                 "HALF_20S_GRID_HITS_BELOW_4" if h20<HALF_MIN_HITS20 else
                 "HALF_PREVIOUS_L2_BINS_BELOW_2" if eligible<HALF_MIN_ELIGIBLE_LAG else
                 None)
            half={
                "half":name,"public_execution_prints":len(trades),
                "fixed_20s_grid_hits":h20,"fixed_45s_grid_hits":h45,
                "observed_hit_ratio_45_over_20":round(h45/h20,8) if h20 else None,
                "eligible_completed_previous_30s_l2_bins":eligible,
                "previous_l2_abstain_reasons":reasons,
                "passes_minimum_observability":why is None,
                "abstain_reason":why,
                "private_agent_IDs_used":False,
            }
        if set(half)!=HALF_FIELDS:
            raise AssertionError("Split-half public result missing or extra field")
        halves.append(half)
    if sum(x["public_execution_prints"] for x in halves)!=len(public):
        raise AssertionError("Nonoverlapping public session halves do not conserve fills")
    failing=[f"{x['half']}:{x['abstain_reason']}" for x in halves if x["abstain_reason"]]
    if failing:
        decision="ABSTAIN"
        reason=";".join(failing)
    elif all(x["fixed_45s_grid_hits"]/x["fixed_20s_grid_hits"]>=RATIO_THRESHOLD
             for x in halves):
        decision="TARGET_PATTERN"
        reason=None
    else:
        decision="NO_TARGET_PATTERN"
        reason=None
    return {
        "public_executed_prints":len(public),
        "public_l2_snapshots":measured["public_l2_snapshots"],
        "public_tape_sha256":measured["public_tape_sha256"],
        "original_whole_session_baseline_decision":original["decision"],
        "original_whole_session_ratio_45_over_20":
            original["observed_ratio_45s_over_20s"],
        "new_split_half_decision":decision,
        "new_split_half_abstain_reason":reason,
        "per_half_public_only":halves,
        "public_feature_touched_private_agent_IDs":False,
        "real_market_owner_FDR_or_accuracy_calibrated":False,
        "source_complete_exchange_feed_proven":False,
        "original_source_raw_print_or_l2_rows_exported":False,
    }


def simulate_case(seed:int,cohort:str)->dict:
    frozen_plan()
    check_seeds()
    if type(seed) is not int or seed not in SEEDS or cohort not in COHORTS:
        raise ValueError("Only preregistered source seed/cohort can be evaluated")
    from abides_markets.config_system import SimulationBuilder
    from abides_markets.config_system.agent_configs import (
        NoiseAgentConfig,MomentumAgentConfig,TWAPExecutionAgentConfig)
    from abides_markets.config_system.models import ExchangeConfig
    from abides_markets.simulation import ResultProfile,run_simulation
    builder=(SimulationBuilder().apply_template("liquid_market")
             .ticker("ABM").start_time(START).end_time(END)
             .exchange(ExchangeConfig(book_capture="l2",book_log_depth=BOOK_DEPTH))
             .seed(seed))
    is_momentum=cohort=="momentum_noise_hard_negative"
    is_fixed=cohort=="fixed_20s_noise_hard_negative"
    builder=builder.enable_agent(NoiseAgentConfig(
        multi_wake=True,wake_up_freq="20s",poisson_arrival=not is_fixed,
        noise_mkt_close_time=END),count=50 if is_momentum else 60)
    if is_momentum:
        builder=builder.enable_agent(MomentumAgentConfig(
            min_size=1,max_size=10,wake_up_freq="25s",poisson_arrival=True,
            short_window=5,long_window=15),count=10)
    if cohort=="twap_45s_positive":
        builder=builder.enable_agent(TWAPExecutionAgentConfig(
            start_time_offset="00:01:00",end_time_offset="00:01:00",
            freq="45s",direction="BID",quantity=1200,trade=True,
            order_style="market"),count=1)
    sim=run_simulation(builder.build(),profile=ResultProfile.QUANT)
    market=sim.markets["ABM"]
    if not market.trades or market.l2_series is None:
        raise RuntimeError("Original matching-engine public tape or L2 missing")
    public=public_projection(market.trades)
    scored=public_half_stability(public,market.l2_series)
    # PRIVATE ORACLE IDS FIRST ACCESSED HERE AFTER BOTH SCORES COMPUTED.
    controlled={int(a.agent_id) for a in sim.agents
                if str(a.agent_name).startswith("TWAP_EXECUTION_AGENT_")}
    target=cohort=="twap_45s_positive"
    if len(controlled)!=(1 if target else 0):
        raise RuntimeError("Source target configuration changed")
    fills=sum(x.passive_agent_id in controlled or
              x.aggressive_agent_id in controlled
              for x in market.trades)
    if target != (fills>0):
        raise RuntimeError("Posthoc controlled TWAP execution witness absent")
    decision=scored["new_split_half_decision"]
    case={
        "seed":seed,"cohort":cohort,**scored,
        "posthoc_injected_target_present":target,
        "posthoc_controlled_twap_execution_count":fills,
        "new_source_false_alarm":decision=="TARGET_PATTERN" and not target,
        "new_source_target_missed":decision=="NO_TARGET_PATTERN" and target,
        "new_source_target_abstained":decision=="ABSTAIN" and target,
    }
    if set(case)!=CASE_FIELDS:
        raise AssertionError("Preregistered result schema drift/possible data leak")
    return case


def validate_source_cases(cases:list[dict])->dict:
    frozen_plan()
    check_seeds()
    expected={(s,c) for s in SEEDS for c in COHORTS}
    if (type(cases) is not list or len(cases)!=16 or
        any(type(x) is not dict or set(x)!=CASE_FIELDS for x in cases) or
        {(x["seed"],x["cohort"]) for x in cases}!=expected):
        raise ValueError("Changed/missing original independent simulation cases")
    sums={}
    for cohort in COHORTS:
        rows=[x for x in cases if x["cohort"]==cohort]
        counts=Counter(x["new_split_half_decision"] for x in rows)
        for x in rows:
            target=cohort=="twap_45s_positive"
            halves=x["per_half_public_only"]
            if (type(halves) is not list or len(halves)!=2 or
                any(type(h) is not dict or set(h)!=HALF_FIELDS for h in halves)
                or [h["half"] for h in halves]!=list(HALF_NAMES)
                or x["new_split_half_decision"] not in STATUSES
                or x["posthoc_injected_target_present"] is not target
                or type(x["posthoc_controlled_twap_execution_count"]) is not int
                or (x["posthoc_controlled_twap_execution_count"]>0)!=target
                or x["new_source_false_alarm"] is not
                   (x["new_split_half_decision"]=="TARGET_PATTERN" and not target)
                or x["new_source_target_missed"] is not
                   (x["new_split_half_decision"]=="NO_TARGET_PATTERN" and target)
                or x["new_source_target_abstained"] is not
                   (x["new_split_half_decision"]=="ABSTAIN" and target)
                or x["public_feature_touched_private_agent_IDs"] is not False
                or x["real_market_owner_FDR_or_accuracy_calibrated"] is not False
                or x["source_complete_exchange_feed_proven"] is not False
                or x["original_source_raw_print_or_l2_rows_exported"] is not False):
                raise ValueError("Source public half-oracle/metadata mismatch")
            if (type(x["public_executed_prints"]) is not int or
                x["public_executed_prints"]<=0 or
                sum(h["public_execution_prints"] for h in halves)!=x["public_executed_prints"]
                or type(x["public_l2_snapshots"]) is not int or
                x["public_l2_snapshots"]<=0 or
                type(x["public_tape_sha256"]) is not str or
                len(x["public_tape_sha256"])!=64 or
                any(c not in "0123456789abcdef" for c in x["public_tape_sha256"])):
                raise ValueError("Source time-bin conservation or SHA invalid")
            failing=[]
            for h in halves:
                n=h["public_execution_prints"]
                a=h["fixed_20s_grid_hits"]
                b=h["fixed_45s_grid_hits"]
                elig=h["eligible_completed_previous_30s_l2_bins"]
                if (any(type(v) is not int or v<0 for v in (n,a,b,elig))
                        or a>n or b>n
                        or type(h["previous_l2_abstain_reasons"]) is not dict
                        or any(type(v) is not int or v<0 for v in
                               h["previous_l2_abstain_reasons"].values())
                        or h["private_agent_IDs_used"] is not False
                        or h["observed_hit_ratio_45_over_20"]!=
                           (round(b/a,8) if a else None)):
                    raise ValueError("Time half public count/feature drift")
                reason=("NO_PUBLIC_PRINTS" if n==0 else
                        "HALF_PUBLIC_PRINTS_BELOW_100" if n<HALF_MIN_PRINTS else
                        "HALF_20S_GRID_HITS_BELOW_4" if a<HALF_MIN_HITS20 else
                        "HALF_PREVIOUS_L2_BINS_BELOW_2" if elig<HALF_MIN_ELIGIBLE_LAG else None)
                if h["abstain_reason"]!=reason or
                    h["passes_minimum_observability"] is not (reason is None)):
                    raise ValueError("Time-half minimum gates changed after source")
                if reason:
                    failing.append(f"{h['half']}:{reason}")
            if failing:
                proper="ABSTAIN"
                why=";".join(failing)
            else:
                proper=("TARGET_PATTERN" if all(
                    h["fixed_45s_grid_hits"]/h["fixed_20s_grid_hits"]>=RATIO_THRESHOLD
                    for h in halves) else "NO_TARGET_PATTERN")
                why=None
            if (x["new_split_half_decision"]!=proper or
                    x["new_split_half_abstain_reason"]!=why):
                raise ValueError("Splitting, abstention or threshold altered")
        sums[cohort]={
            "original_matching_engine_runs":len(rows),
            "new_positive_alarms":counts["TARGET_PATTERN"],
            "new_negative_classifications":counts["NO_TARGET_PATTERN"],
            "new_abstentions":counts["ABSTAIN"],
            "false_positive_background":sum(x["new_source_false_alarm"] for x in rows),
            "false_negative_injected_TWAP":sum(x["new_source_target_missed"] for x in rows),
            "positive_TWAP_abstentions":sum(x["new_source_target_abstained"] for x in rows),
            "posthoc_controlled_fills":sum(x["posthoc_controlled_twap_execution_count"] for x in rows),
            "whole_session_baseline_alarms":sum(
                x["original_whole_session_baseline_decision"]=="TARGET_PATTERN"
                for x in rows),
        }
    return {
        "schema_version":"genuine-abides-split-half-momentum-16case-original-v1",
        "source_frozen_protocol":"research/abides_split_half_momentum_precommit_20261121.json",
        "original_matching_engine_cases":16,
        "new_local_seed_set_without_global_blindness_claim":list(SEEDS),
        "all_cases":cases,
        "cohort_results":sums,
        "experiment_frozen_after_prior_3001_3004_source_inspection":True,
        "real_market_FDR_or_actor_owners_unknown":True,
        "source_complete_exchange_order_sequence_certified":False,
        "injected_agent_or_account_IDs_in_public_data":False,
        "all_original_cohorts_negative_results_preserved":True,
        "no_real_trading_or_order_placement":True,
        "limitations":[
            "New half consistency rule chosen after reviewing prior 3001-3004 source results.",
            "New 3101..3104 are unspent only in local ledger, not globally certified blind.",
            "Synthetic ABIDES agent IDs are private oracle available after source scoring.",
            "Snapshot clock must represent original exchange-local time; no future L2 snapshots used.",
            "Partial/equal-timestamp fills may be dependent; source completeness not certified real.",
            "No real owner-level precision, FDR, causal influence or trading inference."
        ]
    }


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    if args.output.exists():
        p.error("Refuse to overwrite previously recorded source report")
    result=validate_source_cases([
        simulate_case(seed,cohort)
        for seed in SEEDS for cohort in COHORTS
    ])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x",encoding="utf-8") as f:
        json.dump(result,f,indent=2,sort_keys=True,allow_nan=False)
        f.write("\n")
    print("ABIDES_SPLIT_HALF_MOMENTUM_COHORTS",json.dumps(
        result["cohort_results"],sort_keys=True))
    print("ABIDES_SPLIT_HALF_ORIGINAL_16_DONE",json.dumps({
        "source_cases":16,
        "public_only":True,
        "original_matching_engine":True,
        "real_market_actor_FDR_known":False
    },sort_keys=True))


if __name__=="__main__":
    main()
