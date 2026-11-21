#!/usr/bin/env python3
"""Genuine ABIDES source replication: 40 locally new seeds x 4 frozen cohorts.

Source protocol frozen BEFORE running any new matching-engine original case.
The same 20s/45s public-only scores and .60 threshold are retained without
retraining. Exact timestamps ARE NOT an exchange owner/parent-order oracle.
No broker trading, no real-market FDR or physical actor identification.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from abides_export import UPSTREAM_COMMIT
from abides_multiscale_public_l2 import START,END,BOOK_DEPTH,public_multiscale_l2_summary
from abides_clustered_grid_holdout import score_public_timestamp_clusters
from l2_trade_context import public_projection,MAX_FILLS,MAX_SNAPSHOTS
from research_seed_registry import read_ledger

ROOT=Path(__file__).resolve().parents[1]
PLAN=ROOT/"research"/"abides_public_grid_160case_precommit_20261121.json"
SEEDS=(3301,3302,3303,3304,3305,3306,3307,3308,3309,3310,3311,3312,3313,3314,3315,3316,3317,3318,3319,3320,3321,3322,3323,3324,3325,3326,3327,3328,3329,3330,3331,3332,3333,3334,3335,3336,3337,3338,3339,3340)
COHORTS=("poisson_noise_null","fixed_20s_noise_hard_negative",
         "momentum_noise_hard_negative","twap_45s_positive")
THRESHOLD=.60
MIN_PRINTS=200
MIN_PRINT_HITS20=8
MIN_CLUSTER_HITS20=8
MIN_PREV_L2=5
CASE_FIELDS=frozenset((
    "source_seed","source_cohort","synthetic_target_present_posthoc",
    "public_prints","unique_execution_timestamps","same_timestamp_extra_prints",
    "largest_timestamp_cluster_prints","public_L2_snapshot_events",
    "eligible_previous_completed_30s_L2_bins","public_tape_sha256",
    "per_print_hits20","per_print_hits45",
    "per_unique_timestamp_hits20","per_unique_timestamp_hits45",
    "per_print_ratio_45_over_20","per_unique_ratio_45_over_20",
    "per_print_decision","per_unique_decision",
    "per_print_abstain_reason","per_unique_abstain_reason",
    "posthoc_controlled_TWAP_fills",
    "per_print_false_alarm","per_unique_false_alarm",
    "per_print_missed_TWAP","per_unique_missed_TWAP",
    "private_oracle_agent_IDs_entered_public_features",
    "actual_market_owner_identity_or_FDR_known",
    "source_complete_real_exchange_feed_proven",
    "raw_prints_or_L2_snapshots_exported"
))
STATUSES=("ABSTAIN","TARGET_PATTERN","NO_TARGET_PATTERN")


def frozen_protocol()->dict:
    p=json.loads(PLAN.read_text(encoding="utf-8"))
    f=p.get("frozen_baseline",{})
    if (
        p.get("schema_version")!="genuine-abides-40seed-public-grid-replication-precommit-v1"
        or p.get("stage")!="RD-ABIDES-POWER-15"
        or p.get("source_status_at_design")!="NOT_RUN"
        or p.get("original_source_evidence")!=[44938991772,44943333914]
        or p.get("source_engine_revision")!=UPSTREAM_COMMIT
        or p.get("source_engine")!="genuine ABIDES-NG matching engine synthetic only"
        or p.get("fixed_new_seed_values")!=list(SEEDS)
        or p.get("seeds_per_cohort")!=40
        or p.get("planned_engine_cases")!=160
        or p.get("cohorts")!=list(COHORTS)
        or p.get("local_seed_novelty_only_not_globally_blind") is not True
        or p.get("source_mkt")!="ABM"
        or p.get("session_start_exchange_local")!=START
        or p.get("session_end_exchange_local")!=END
        or p.get("public_l2_depth_per_side")!=BOOK_DEPTH
        or f.get("fixed_anchor_exchange_local_seconds_after_midnight")!=34260
        or f.get("grid_periods_seconds")!=[20,45]
        or f.get("grid_window_tolerance_ns")!=250_000_000
        or f.get("per_print_ratio_threshold_greater_equal")!=THRESHOLD
        or f.get("per_unique_timestamp_ratio_threshold_greater_equal")!=THRESHOLD
        or f.get("min_public_prints")!=MIN_PRINTS
        or f.get("min_public_20sec_hits")!=MIN_PRINT_HITS20
        or f.get("min_unique_timestamp_20sec_hits")!=MIN_CLUSTER_HITS20
        or f.get("min_previous_completed_30sec_l2_bins")!=MIN_PREV_L2
        or f.get("all_missing_data_abstain_not_negative") is not True
        or f.get("same_timestamp_group_not_physical_parent_order") is not True
        or f.get("no_posthoc_best_phase_or_seed_selection") is not True
        or p.get("no_real_market_FDR_or_owner_accuracy_claim") is not True
        or p.get("no_raw_trades_L2_rows_private_agent_or_order_ids_in_artifact") is not True
        or p.get("must_not_change_existing_16_source_frozen_protocol") is not True
        or p.get("original_actions_workflow_bounded_then_manual_only") is not True
    ):
        raise ValueError("Frozen 40-seed preregistration or source is changed")
    source=p.get("unchanged_original_cohort_config",{})
    if type(source) is not dict or set(source)!=set(COHORTS):
        raise ValueError("Original source cohort names have changed")
    for cohort in COHORTS:
        v=source[cohort]
        expected={
          "poisson_noise_null":(60,True,0,0),
          "fixed_20s_noise_hard_negative":(60,False,0,0),
          "momentum_noise_hard_negative":(50,True,10,0),
          "twap_45s_positive":(60,True,0,1)
        }[cohort]
        if (v.get("noise_agents"),v.get("poisson_arrival"),
            v.get("momentum_agents"),v.get("twap_agents"))!=expected:
            raise ValueError("Original source family agent composition changed")
        if v.get("noise_wake")!="20s":
            raise ValueError("ABIDES noise wakeup convention changed")
    m=source["momentum_noise_hard_negative"]
    t=source["twap_45s_positive"]
    if ((m.get("momentum_wake"),m.get("momentum_poisson"),
         m.get("short_window"),m.get("long_window"))!=("25s",True,5,15)
        or (t.get("twap_frequency_seconds"),t.get("twap_quantity_lots"),
            t.get("twap_direction"),t.get("twap_style"),t.get("twap_offset_seconds"))!=
            (45,1200,"BID","market",60)):
        raise ValueError("Frozen source agent cadence, momentum or TWAP changed")
    return p


def check_ledger()->None:
    l=read_ledger()
    study=[x for x in l["studies"]
           if x.get("id")=="genuine_abides_public_grid_replicate_40seeds"]
    if (len(study)!=1 or study[0]["seeds"]!=list(SEEDS)
        or study[0].get("source_file")!="tools/abides_grid_replication_160.py"
        or study[0].get("source_constant")!="SEEDS"):
        raise ValueError("Original 40-seed source registry reservation drift")


def _decode_decision(n,h20,h45,eligible,*,grouped:bool)->tuple[str,str|None]:
    if type(n) is not int or type(h20) is not int or type(h45) is not int or type(eligible) is not int:
        raise ValueError("Non-integer public source decision count")
    if n<0 or not 0<=h20<=n or not 0<=h45<=n or eligible<0:
        raise ValueError("Invalid public executed trade/group count")
    if n<MIN_PRINTS:
        why="TOO_FEW_PUBLIC_PRINTS"
    elif h20<(MIN_CLUSTER_HITS20 if grouped else MIN_PRINT_HITS20):
        why=("TOO_FEW_DISTINCT_20S_HITS" if grouped
             else "TOO_FEW_20S_CLOCK_HITS")
    elif eligible<MIN_PREV_L2:
        why="TOO_FEW_ELIGIBLE_COMPLETED_L2_BINS"
    else:
        why=None
    decision=("ABSTAIN" if why else
              "TARGET_PATTERN" if h45/h20>=THRESHOLD else
              "NO_TARGET_PATTERN")
    return decision,why


def simulate_source_case(seed:int,cohort:str)->dict:
    frozen_protocol()
    check_ledger()
    if type(seed) is not int or seed not in SEEDS or cohort not in COHORTS:
        raise ValueError("Only 160 precommitted ABIDES original source cases allowed")
    from abides_markets.config_system import SimulationBuilder
    from abides_markets.config_system.agent_configs import (
        NoiseAgentConfig,MomentumAgentConfig,TWAPExecutionAgentConfig)
    from abides_markets.config_system.models import ExchangeConfig
    from abides_markets.simulation import ResultProfile,run_simulation
    setting=frozen_protocol()["unchanged_original_cohort_config"][cohort]
    builder=(SimulationBuilder().apply_template("liquid_market")
             .ticker("ABM").start_time(START).end_time(END)
             .exchange(ExchangeConfig(book_capture="l2",book_log_depth=BOOK_DEPTH))
             .seed(seed))
    builder=builder.enable_agent(NoiseAgentConfig(
        multi_wake=True,wake_up_freq="20s",
        poisson_arrival=setting["poisson_arrival"],
        noise_mkt_close_time=END),count=setting["noise_agents"])
    if cohort=="momentum_noise_hard_negative":
        builder=builder.enable_agent(MomentumAgentConfig(
            min_size=1,max_size=10,wake_up_freq="25s",
            poisson_arrival=True,short_window=5,long_window=15),count=10)
    if cohort=="twap_45s_positive":
        builder=builder.enable_agent(TWAPExecutionAgentConfig(
            start_time_offset="00:01:00",end_time_offset="00:01:00",
            freq="45s",direction="BID",quantity=1200,trade=True,
            order_style="market"),count=1)
    simulation=run_simulation(builder.build(),profile=ResultProfile.QUANT)
    market=simulation.markets["ABM"]
    if not market.trades or market.l2_series is None:
        raise RuntimeError("Missing original public market executed trades/L2")
    public=public_projection(market.trades)
    measured=public_multiscale_l2_summary(public,market.l2_series)
    comparison=score_public_timestamp_clusters(public,measured)
    n=comparison["public_execution_prints"]
    elig=comparison["eligible_completed_previous_30s_l2_bins"]
    old,oldwhy=_decode_decision(
        n,comparison["print_grid_hits20"],comparison["print_grid_hits45"],
        elig,grouped=False)
    new,newwhy=_decode_decision(
        n,comparison["grouped_grid_hits20"],comparison["grouped_grid_hits45"],
        elig,grouped=True)
    if ((old,oldwhy)!=(comparison["original_per_print_decision"],
                      comparison["original_per_print_abstain_reason"])
        or (new,newwhy)!=(comparison["grouped_timestamp_decision"],
                          comparison["grouped_timestamp_abstain_reason"])):
        raise RuntimeError("Frozen original source score/coverage mismatch")
    # Private simulator owner attribution is read exclusively AFTER BOTH
    # public-only methods and all L2 coverage/abstain checks are complete.
    controlled={int(a.agent_id) for a in simulation.agents
                if str(a.agent_name).startswith("TWAP_EXECUTION_AGENT_")}
    target=cohort=="twap_45s_positive"
    if len(controlled)!=(1 if target else 0):
        raise RuntimeError("Frozen positive/negative simulator agent ID unexpected")
    fills=sum(t.passive_agent_id in controlled or
              t.aggressive_agent_id in controlled for t in market.trades)
    if (fills>0)!=target:
        raise RuntimeError("Injected TWAP did not execute according to posthoc oracle")
    x={
        "source_seed":seed,"source_cohort":cohort,
        "synthetic_target_present_posthoc":target,
        "public_prints":n,
        "unique_execution_timestamps":comparison["distinct_execution_timestamp_clusters"],
        "same_timestamp_extra_prints":comparison["dependent_same_timestamp_extra_prints"],
        "largest_timestamp_cluster_prints":comparison["largest_exact_timestamp_cluster"],
        "public_L2_snapshot_events":comparison["public_l2_snapshot_events"],
        "eligible_previous_completed_30s_L2_bins":elig,
        "public_tape_sha256":comparison["public_tape_sha256"],
        "per_print_hits20":comparison["print_grid_hits20"],
        "per_print_hits45":comparison["print_grid_hits45"],
        "per_unique_timestamp_hits20":comparison["grouped_grid_hits20"],
        "per_unique_timestamp_hits45":comparison["grouped_grid_hits45"],
        "per_print_ratio_45_over_20":comparison["per_print_observed_ratio"],
        "per_unique_ratio_45_over_20":comparison["per_unique_timestamp_observed_ratio"],
        "per_print_decision":old,"per_unique_decision":new,
        "per_print_abstain_reason":oldwhy,
        "per_unique_abstain_reason":newwhy,
        "posthoc_controlled_TWAP_fills":fills,
        "per_print_false_alarm":not target and old=="TARGET_PATTERN",
        "per_unique_false_alarm":not target and new=="TARGET_PATTERN",
        "per_print_missed_TWAP":target and old=="NO_TARGET_PATTERN",
        "per_unique_missed_TWAP":target and new=="NO_TARGET_PATTERN",
        "private_oracle_agent_IDs_entered_public_features":False,
        "actual_market_owner_identity_or_FDR_known":False,
        "source_complete_real_exchange_feed_proven":False,
        "raw_prints_or_L2_snapshots_exported":False
    }
    if set(x)!=CASE_FIELDS:
        raise AssertionError("Original source report private field leakage/missing")
    return x


def validate_source_report(rows:list[dict])->dict:
    frozen_protocol()
    check_ledger()
    expected={(seed,c) for seed in SEEDS for c in COHORTS}
    if (type(rows) is not list or len(rows)!=160
        or any(type(x) is not dict or set(x)!=CASE_FIELDS for x in rows)
        or {(x["source_seed"],x["source_cohort"]) for x in rows}!=expected):
        raise ValueError("Original 160 ABIDES cases missing/duplicate/replaced")
    outcomes={}
    for cohort in COHORTS:
        sub=[x for x in rows if x["source_cohort"]==cohort]
        decision_pairs=Counter((x["per_print_decision"],x["per_unique_decision"]) for x in sub)
        for x in sub:
            target=cohort=="twap_45s_positive"
            n=x["public_prints"]
            unique=x["unique_execution_timestamps"]
            l2=x["public_L2_snapshot_events"]
            elig=x["eligible_previous_completed_30s_L2_bins"]
            if (type(n) is not int or type(unique) is not int or
                not 0<unique<=n<=MAX_FILLS or type(l2) is not int or
                not 0<l2<=MAX_SNAPSHOTS or type(elig) is not int or elig<0
                or type(x["same_timestamp_extra_prints"]) is not int
                or x["same_timestamp_extra_prints"]!=n-unique
                or type(x["largest_timestamp_cluster_prints"]) is not int
                or not 1<=x["largest_timestamp_cluster_prints"]<=n):
                raise ValueError("Source event/L2/group conservation failed")
            for grouped,prefix,count in (
                (False,"per_print",n),
                (True,"per_unique",unique)
            ):
                h20=x[prefix+"_hits20"]
                h45=x[prefix+"_hits45"]
                ratio=x[prefix+"_ratio_45_over_20"]
                if (any(type(y) is not int or not 0<=y<=count for y in (h20,h45))
                    or ratio!=(round(h45/h20,8) if h20 else None)):
                    raise ValueError("Source print/group clock ratio invalid")
                expected_status,expected_why=_decode_decision(
                    n,h20,h45,elig,grouped=grouped)
                if (x[prefix+"_decision"],x[prefix+"_abstain_reason"])!=(
                        expected_status,expected_why):
                    raise ValueError("Posthoc rule, phase or abstention threshold changed")
            old,new=x["per_print_decision"],x["per_unique_decision"]
            if (x["synthetic_target_present_posthoc"] is not target
                or type(x["posthoc_controlled_TWAP_fills"]) is not int
                or (x["posthoc_controlled_TWAP_fills"]>0)!=target
                or x["per_print_false_alarm"] is not (not target and old=="TARGET_PATTERN")
                or x["per_unique_false_alarm"] is not (not target and new=="TARGET_PATTERN")
                or x["per_print_missed_TWAP"] is not (target and old=="NO_TARGET_PATTERN")
                or x["per_unique_missed_TWAP"] is not (target and new=="NO_TARGET_PATTERN")
                or any(x[key] is not False for key in (
                    "private_oracle_agent_IDs_entered_public_features",
                    "actual_market_owner_identity_or_FDR_known",
                    "source_complete_real_exchange_feed_proven",
                    "raw_prints_or_L2_snapshots_exported"))
                or type(x["public_tape_sha256"]) is not str
                or len(x["public_tape_sha256"])!=64
                or any(ch not in "0123456789abcdef" for ch in x["public_tape_sha256"])):
                raise ValueError("Actual oracle/private source or statistics inconsistent")
        outcomes[cohort]={
            "independent_local_seed_engine_runs":40,
            "source_executions":sum(x["public_prints"] for x in sub),
            "source_unique_timestamps":sum(x["unique_execution_timestamps"] for x in sub),
            "posthoc_controlled_TWAP_fills":sum(x["posthoc_controlled_TWAP_fills"] for x in sub),
            "per_print_positive_alarms":sum(x["per_print_decision"]=="TARGET_PATTERN" for x in sub),
            "per_unique_positive_alarms":sum(x["per_unique_decision"]=="TARGET_PATTERN" for x in sub),
            "per_print_false_alarms":sum(x["per_print_false_alarm"] for x in sub),
            "per_unique_false_alarms":sum(x["per_unique_false_alarm"] for x in sub),
            "per_print_missed_TWAP":sum(x["per_print_missed_TWAP"] for x in sub),
            "per_unique_missed_TWAP":sum(x["per_unique_missed_TWAP"] for x in sub),
            "per_print_abstentions":sum(x["per_print_decision"]=="ABSTAIN" for x in sub),
            "per_unique_abstentions":sum(x["per_unique_decision"]=="ABSTAIN" for x in sub),
            "paired_both_positive":decision_pairs[("TARGET_PATTERN","TARGET_PATTERN")],
            "paired_print_only_positive":decision_pairs[("TARGET_PATTERN","NO_TARGET_PATTERN")],
            "paired_unique_only_positive":decision_pairs[("NO_TARGET_PATTERN","TARGET_PATTERN")],
            "paired_both_negative":decision_pairs[("NO_TARGET_PATTERN","NO_TARGET_PATTERN")],
            "paired_any_abstention":sum("ABSTAIN" in (x["per_print_decision"],x["per_unique_decision"]) for x in sub),
        }
        if sum(outcomes[cohort][k] for k in (
                "paired_both_positive","paired_print_only_positive",
                "paired_unique_only_positive","paired_both_negative",
                "paired_any_abstention"))!=40:
            raise AssertionError("Paired same source tapes were duplicated/lost")
    return {
        "schema_version":"genuine-abides-public-clock-160source-replication-original-v1",
        "source_frozen_protocol":"research/abides_public_grid_160case_precommit_20261121.json",
        "genuine_abides_engine_revision":UPSTREAM_COMMIT,
        "original_matching_engine_source_case_count":160,
        "local_new_source_seeds_not_certified_globally_blind":list(SEEDS),
        "all_original_160_anonymous_case_aggregates":rows,
        "source_cohorts":outcomes,
        "frozen_thresholds_and_grid_phases_modified_after_inspection":False,
        "original_source_cases_or_false_alarms_omitted":False,
        "synthetic_source_only_not_real_exchange_data":True,
        "oracle_used_only_after_public_feature":True,
        "physical_owner_or_real_market_FDR_calibrated":False,
        "raw_source_trades_L2_books_private_agent_IDs_exported":False,
        "source_complete_exchange_sequence_certified":False,
        "limitations":[
            "Only one fixed ABIDES model/generative family; seeds are locally distinct, not globally blind.",
            "A success fraction within simulator does not calibrate real-market physical owner labels or FDR.",
            "The .60 ratio originally chosen after earlier development data, but not reoptimized on these 40 new seeds.",
            "Unique timestamps may represent different orders; split fills are not independent actors.",
            "Statistical confidence bounds assume hypothetical IID simulator seed trials; source pseudorandomness does not independently certify IID.",
            "All original background false alarms, abstentions, misses and non-target sources are retained."
        ]
    }


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    if args.output.exists():
        p.error("Refuse to overwrite original precommitted source results")
    frozen_protocol()
    check_ledger()
    rows=[simulate_source_case(seed,cohort) for seed in SEEDS for cohort in COHORTS]
    result=validate_source_report(rows)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x",encoding="utf-8") as f:
        json.dump(result,f,sort_keys=True,indent=2,allow_nan=False)
        f.write("\n")
    print("GENUINE_ABIDES_160_SOURCE_COHORT_SUMMARY",json.dumps(
        result["source_cohorts"],sort_keys=True))
    print("GENUINE_ABIDES_160_SOURCE_COMPLETED",json.dumps({
        "original_matching_engine_runs":160,
        "local_seeds":40,"all_cohorts_retained":True,
        "real_market_fdr_or_owners_known":False
    },sort_keys=True))


if __name__=="__main__":
    main()
