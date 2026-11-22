#!/usr/bin/env python3
"""Frozen 16-case public-only ABIDES background-conditioned ratio evaluation.

The threshold (45s grid hits)/(20s grid hits) >= 0.60 is a POSTHOC
hypothesis from previously seen seeds 2901-2903, registered BEFORE new
3001-3004 source engine runs. This is not a market-actor detector or
real-market accuracy/FDR estimate. The oracle is read ONLY AFTER public
features, coverage checks and classification are complete.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from abides_export import UPSTREAM_COMMIT
from abides_multiscale_public_l2 import (
    public_multiscale_l2_summary, CASE_ALLOWED_FIELDS,
    BOOK_DEPTH, START, END
)
from l2_trade_context import public_projection
from research_seed_registry import read_ledger

ROOT=Path(__file__).resolve().parents[1]
PROTOCOL=ROOT/"research"/"abides_background_conditioned_ratio_precommit_20261121.json"
SEEDS=(3001,3002,3003,3004)
COHORTS=("poisson_noise_null","fixed_20s_noise_hard_negative",
         "momentum_noise_hard_negative","twap_45s_positive")
THRESHOLD=0.60
MIN_PRINTS=200
MIN_20S_GRID_HITS=8
MIN_LAGGED_L2_BINS=5
SRC_PLAN="genuine-abides-public-background-conditioned-ratio-precommit-v1"
# Exact fields from the existing public-only projection. No owner ID permitted.
ORACLE_FIELDS=frozenset((
    "seed","cohort","posthoc_target_present","posthoc_controlled_execution_count",
    "classification_correct_when_decided","false_positive_background",
    "false_negative_injected_target"
))
PUBLIC_MEASURED_FIELDS=CASE_ALLOWED_FIELDS-frozenset((
    "seed","cohort","injected_target_present_only_after_public_inference",
    "controlled_twap_fills_posthoc","true_owner_IDs_exposed",
    "real_market_bot_FDR_known",
))
RESULT_FIELDS=frozenset((
    "seed","cohort","public_prints","public_l2_snapshots",
    "public_tape_sha256","public_20s_hits","public_45s_hits",
    "observed_ratio_45s_over_20s","eligible_completed_prior_l2_bins_30s",
    "abstained_l2_bins_30s","quote_stream_completeness_known",
    "legacy_10s_alarm","decision","abstain_reason",
    "posthoc_target_present","posthoc_controlled_execution_count",
    "classification_correct_when_decided","false_positive_background",
    "false_negative_injected_target",
    "public_features_accessed_oracle_agent_IDs",
    "real_market_actor_accuracy_or_FDR_calibrated"
))
ALLOWED_STATUSES=("TARGET_PATTERN","NO_TARGET_PATTERN","ABSTAIN")
ABSTAIN_CODES=("TOO_FEW_PUBLIC_PRINTS","TOO_FEW_20S_CLOCK_HITS",
               "TOO_FEW_ELIGIBLE_COMPLETED_L2_BINS")


def frozen_plan()->dict:
    data=json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if (
        data.get("schema_version")!=SRC_PLAN
        or data.get("upstream_abides_commit")!=UPSTREAM_COMMIT
        or data.get("derived_from_inspected_source_run")!=44935340284
        or data.get("hypothesis_origin")!="POSTHOC_EXPLORATORY_FROM_PREVIOUS_2901_2903_SOURCE_NOT_INDEPENDENT"
        or data.get("new_evaluation_source_status")!="NOT_RUN"
        or data.get("local_new_seed_candidates")!=list(SEEDS)
        or data.get("local_ledger_newness_only") is not True
        or data.get("globally_blind_independence_not_certified") is not True
        or data.get("simulator_cohorts")!=list(COHORTS)
        or data.get("original_independent_source_runs_planned")!=16
        or data.get("abides_symbol")!="ABM"
        or (data.get("start"),data.get("end"))!=(START,END)
        or data.get("book_capture_levels_per_side")!=BOOK_DEPTH
        or data.get("grid_anchor_exchange_local_seconds_after_midnight")!=34260
        or data.get("grid_period_seconds")!=[20,45]
        or data.get("grid_tolerance_milliseconds")!=250
        or data.get("target_positive_if_ratio_greater_or_equal")!=THRESHOLD
        or data.get("minimum_public_execution_prints")!=MIN_PRINTS
        or data.get("minimum_20s_grid_hits_for_classification")!=MIN_20S_GRID_HITS
        or data.get("minimum_eligible_previous_completed_30s_L2_bins")!=MIN_LAGGED_L2_BINS
        or data.get("abstain_if_any_coverage_requirement_not_met") is not True
        or data.get("oracle_target_labels_only_after_public_inference") is not True
        or data.get("private_agent_or_order_reference_IDs_prohibited_in_features") is not True
        or data.get("preregistered_source_results_must_include_all_cohorts_and_seeds") is not True
        or data.get("no_real_owner_accuracy_or_market_FDR_claim") is not True
        or data.get("no_raw_public_or_private_source_tapes_in_repository") is not True
    ):
        raise ValueError("Original ABIDES source-ratio preregistration changed")
    return data


def check_seed_registry()->None:
    ledger=read_ledger()
    entries=[x for x in ledger["studies"]
             if x["id"]=="genuine_abides_background_ratio_16run"]
    if len(entries)!=1 or entries[0]["seeds"]!=list(SEEDS):
        raise ValueError("New source seeds not reserved as canonical frozen cohort")
    if (entries[0].get("source_file")!="tools/abides_background_ratio_holdout.py"
            or entries[0].get("source_constant")!="SEEDS"):
        raise ValueError("New source seed registry provenance invalid")


def public_ratio_decision(measured:dict)->dict:
    """Use only source-public clock and PREVIOUS completed L2 stats."""
    if type(measured) is not dict or set(measured)!=PUBLIC_MEASURED_FIELDS:
        raise ValueError("Unexpected public or injected oracle field in feature path")
    n=measured["public_prints"]
    hits=measured["grid_hit_counts"]
    if (type(n) is not int or n<1 or
        type(hits) is not dict or set(hits)!={"10","20","45","90"} or
        any(type(v) is not int or v<0 or v>n for v in hits.values())
        or type(measured["public_l2_snapshots"]) is not int
        or measured["public_l2_snapshots"]<=0
        or measured["public_only_feature_input_type_verified"] is not True
        or measured["actual_private_agent_ids_accessed"] is not False
        or measured["real_market_owner_accuracy_calibrated"] is not False
        or measured["private_id_leakage_from_L2_features"] is not False
        or measured["source_complete_exchange_sequence_proven"] is not False
        or measured["raw_quote_rows_or_l2_observations_exported"] is not False):
        raise ValueError("Public source field invalid or fabricated provenance")
    lag=measured["l2_binned_lagged"]
    if type(lag) is not dict or set(lag)!={"30","60"}:
        raise ValueError("No full preregistered lagged L2 book record")
    b=lag["30"]
    eligible=b.get("eligible_previous_completed_book_bins")
    populated=b.get("populated_trade_bins")
    reasons=b.get("abstained_bins_by_reason")
    if (type(eligible) is not int or eligible<0 or
        type(populated) is not int or populated<0 or
        type(reasons) is not dict or
        any(type(x) is not int or x<0 for x in reasons.values()) or
        eligible+sum(reasons.values())!=populated):
        raise ValueError("L2 coverage/abstention accounting invalid")
    if n<MIN_PRINTS:
        abstain="TOO_FEW_PUBLIC_PRINTS"
    elif hits["20"]<MIN_20S_GRID_HITS:
        abstain="TOO_FEW_20S_CLOCK_HITS"
    elif eligible<MIN_LAGGED_L2_BINS:
        abstain="TOO_FEW_ELIGIBLE_COMPLETED_L2_BINS"
    else:
        abstain=None
    # Zero denominator is an ABSTENTION, never an infinite score or a
    # substituted epsilon. It would already fail hits20>=8.
    ratio=round(hits["45"]/hits["20"],8) if hits["20"] else None
    decision=("ABSTAIN" if abstain else
              "TARGET_PATTERN" if hits["45"]/hits["20"]>=THRESHOLD
              else "NO_TARGET_PATTERN")
    out={
        "public_prints":n,
        "public_l2_snapshots":measured["public_l2_snapshots"],
        "public_tape_sha256":measured["public_tape_sha256"],
        "public_20s_hits":hits["20"],
        "public_45s_hits":hits["45"],
        "observed_ratio_45s_over_20s":ratio,
        "eligible_completed_prior_l2_bins_30s":eligible,
        "abstained_l2_bins_30s":dict(reasons),
        "quote_stream_completeness_known":False,
        "legacy_10s_alarm":measured["original_legacy_10s_rule_alarm"],
        "decision":decision,
        "abstain_reason":abstain,
        "public_features_accessed_oracle_agent_IDs":False,
        "real_market_actor_accuracy_or_FDR_calibrated":False
    }
    return out


def simulate_case(seed:int,cohort:str)->dict:
    frozen_plan()
    check_seed_registry()
    if type(seed) is not int or seed not in SEEDS or cohort not in COHORTS:
        raise ValueError("Only 16 preregistered source cases may run")
    from abides_markets.config_system import SimulationBuilder
    from abides_markets.config_system.agent_configs import (
        NoiseAgentConfig,MomentumAgentConfig,TWAPExecutionAgentConfig)
    from abides_markets.config_system.models import ExchangeConfig
    from abides_markets.simulation import ResultProfile,run_simulation
    builder=(SimulationBuilder().apply_template("liquid_market")
             .ticker("ABM").start_time(START).end_time(END)
             .exchange(ExchangeConfig(book_capture="l2",book_log_depth=BOOK_DEPTH))
             .seed(seed))
    poisson=cohort!="fixed_20s_noise_hard_negative"
    background_count=50 if cohort=="momentum_noise_hard_negative" else 60
    builder=builder.enable_agent(NoiseAgentConfig(
        multi_wake=True,wake_up_freq="20s",poisson_arrival=poisson,
        noise_mkt_close_time=END),count=background_count)
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
        raise RuntimeError("Missing genuine original matching-engine trades or L2")
    public=public_projection(market.trades)
    measured=public_multiscale_l2_summary(public,market.l2_series)
    decision=public_ratio_decision(measured)
    # Private oracle data first touched HERE, after public-only inference.
    controlled={int(x.agent_id) for x in sim.agents
                if str(x.agent_name).startswith("TWAP_EXECUTION_AGENT_")}
    target=cohort=="twap_45s_positive"
    if len(controlled)!=(1 if target else 0):
        raise RuntimeError("Preregistered ABIDES agent configuration changed")
    fills=sum(t.passive_agent_id in controlled or
              t.aggressive_agent_id in controlled for t in market.trades)
    if target != (fills>0):
        raise RuntimeError("Synthetic posthoc target execution truth invalid")
    chosen=decision["decision"]
    result={
        "seed":seed,"cohort":cohort,**decision,
        "posthoc_target_present":target,
        "posthoc_controlled_execution_count":fills,
        "classification_correct_when_decided":(
            None if chosen=="ABSTAIN" else
            (chosen=="TARGET_PATTERN")==target
        ),
        "false_positive_background":chosen=="TARGET_PATTERN" and not target,
        "false_negative_injected_target":chosen=="NO_TARGET_PATTERN" and target
    }
    if set(result)!=RESULT_FIELDS:
        raise AssertionError("Unapproved aggregate field from source simulation")
    return result


def validate_all_cases(cases:list[dict])->dict:
    frozen_plan()
    check_seed_registry()
    expected={(s,c) for s in SEEDS for c in COHORTS}
    if (type(cases) is not list or len(cases)!=16 or
        any(type(r) is not dict or set(r)!=RESULT_FIELDS for r in cases) or
        {(r["seed"],r["cohort"]) for r in cases}!=expected):
        raise ValueError("Original 16 source cases missing/duplicate/unsafely extended")
    result_cohorts={}
    for c in COHORTS:
        group=[r for r in cases if r["cohort"]==c]
        counter=Counter(x["decision"] for x in group)
        for r in group:
            seed=r["seed"]
            n=r["public_prints"]
            h20=r["public_20s_hits"]
            h45=r["public_45s_hits"]
            d=r["decision"]
            target=c=="twap_45s_positive"
            if (type(seed) is not int or type(n) is not int or n<=0 or
                any(type(z) is not int or z<0 or z>n for z in (h20,h45)) or
                d not in ALLOWED_STATUSES or
                r["posthoc_target_present"] is not target or
                type(r["posthoc_controlled_execution_count"]) is not int or
                (r["posthoc_controlled_execution_count"]>0)!=target or
                r["observed_ratio_45s_over_20s"]!=
                    (round(h45/h20,8) if h20 else None) or
                (d=="ABSTAIN")!=(r["abstain_reason"] is not None) or
                r["abstain_reason"] not in (None,)+ABSTAIN_CODES or
                r["classification_correct_when_decided"]!=(
                    None if d=="ABSTAIN" else (d=="TARGET_PATTERN")==target) or
                r["false_positive_background"] is not (d=="TARGET_PATTERN" and not target) or
                r["false_negative_injected_target"] is not (d=="NO_TARGET_PATTERN" and target) or
                r["public_features_accessed_oracle_agent_IDs"] is not False or
                r["real_market_actor_accuracy_or_FDR_calibrated"] is not False or
                r["quote_stream_completeness_known"] is not False):
                raise ValueError("Preregistered public ratio/source oracle outcome inconsistent")
            digest=r["public_tape_sha256"]
            if (type(digest) is not str or len(digest)!=64 or
                any(ch not in "0123456789abcdef" for ch in digest)):
                raise ValueError("Missing exact public-only tape fingerprint")
            lag=r["eligible_completed_prior_l2_bins_30s"]
            reasons=r["abstained_l2_bins_30s"]
            if (type(lag) is not int or lag<0 or
                type(reasons) is not dict or
                any(type(z) is not int or z<0 for z in reasons.values()) or
                type(r["legacy_10s_alarm"]) is not bool):
                raise ValueError("Unknown L2/legacy source coverage")
            expected_reason=(
                "TOO_FEW_PUBLIC_PRINTS" if n<MIN_PRINTS else
                "TOO_FEW_20S_CLOCK_HITS" if h20<MIN_20S_GRID_HITS else
                "TOO_FEW_ELIGIBLE_COMPLETED_L2_BINS" if lag<MIN_LAGGED_L2_BINS else None
            )
            if r["abstain_reason"]!=expected_reason:
                raise ValueError("Unfrozen abstention rule was applied")
            if expected_reason is None and d!=(
                "TARGET_PATTERN" if h45/h20>=THRESHOLD else "NO_TARGET_PATTERN"
            ):
                raise ValueError("Changed frozen ratio threshold/decision")
        result_cohorts[c]={
            "matching_engine_runs":len(group),
            "alarms":counter["TARGET_PATTERN"],
            "negative":counter["NO_TARGET_PATTERN"],
            "abstains":counter["ABSTAIN"],
            "false_alarms":sum(x["false_positive_background"] for x in group),
            "missed_targets":sum(x["false_negative_injected_target"] for x in group),
            "posthoc_controlled_fills":sum(x["posthoc_controlled_execution_count"] for x in group),
            "abstention_reasons":dict(Counter(
                x["abstain_reason"] for x in group if x["abstain_reason"]
            ))
        }
    return {
        "schema_version":"genuine-abides-public-ratio-16source-holdout-v1",
        "precommitted_source_plan":"research/abides_background_conditioned_ratio_precommit_20261121.json",
        "original_matching_engine_runs":len(cases),
        "locally_reserved_but_not_globally_certified_seeds":list(SEEDS),
        "all_cohort_source_cases":cases,
        "cohort_results":result_cohorts,
        "ratio_threshold_selected_after_prior_development_data_not_this_holdout":True,
        "source_original_matching_engine_ABIDES_synthetic_only":True,
        "source_replicates_not_real_market_actors":True,
        "any_real_market_owner_FDR_or_precision_claim":False,
        "raw_trade_l2_or_private_agent_IDs_exported":False,
        "incomplete_real_exchange_source_feed_certification_absent":True,
        "negative_results_retained_without_posthoc_tuning":True,
        "limitations":[
            "Ratio>=0.60 was chosen after inspecting development seeds 2901-2903.",
            "The present independent *local* seeds are not a certified globally blind sample.",
            "Classification is only synthetic target-presence vs background, not real robot ID.",
            "Source prints and L2 have no independently certified real exchange completeness.",
            "Fixed 20s background may produce 45s clock aliases with zero injected TWAP.",
            "No commercial trading logic or broker connection is enabled."
        ]
    }


def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        parser.error("Do not overwrite original preregistered source evidence")
    result=validate_all_cases([
        simulate_case(seed,cohort)
        for seed in SEEDS for cohort in COHORTS
    ])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x",encoding="utf-8") as f:
        json.dump(result,f,sort_keys=True,indent=2,allow_nan=False)
        f.write("\n")
    print("ABIDES_PUBLIC_RATIO_16_SOURCE_COHORTS",json.dumps(
        result["cohort_results"],sort_keys=True))
    print("ABIDES_PUBLIC_RATIO_16_RUN_COMPLETED",json.dumps({
        "source_matching_engine_runs":len(result["all_cohort_source_cases"]),
        "original_source_only":True,"real_market_owner_accuracy":False
    },sort_keys=True))


if __name__=="__main__":
    main()
