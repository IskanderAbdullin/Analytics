#!/usr/bin/env python3
"""Precommitted genuine ABIDES public-only fixed-clock rhythm transfer.

The tested feature derives ONLY from public executed print timestamps and
the preregistered 10-second 250ms/0.22 toy score, not private agent IDs.
Post-hoc controlled-TWAP truth is counted after public features are frozen.
A fixed cadence background may be detected even without an injected target.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from abides_export import UPSTREAM_COMMIT
from l2_trade_context import public_projection, PublicExecution, MAX_FILLS, MAX_SNAPSHOTS
from toy_public_execution_rhythm import (
    GRID_PERIOD_US, GRID_TOLERANCE_US, THRESHOLD
)

ROOT=Path(__file__).resolve().parents[1]
PROTOCOL=ROOT/"research"/"genuine_abides_fixed_clock_transfer_precommit_20261121.json"
SEEDS=(2801,2802)
COHORTS=("poisson_noise_null","fixed_cadence_noise_hard_negative",
         "twap_injected_positive")
START="09:30:00"
END="09:38:00"
BOOK_DEPTH=5
GRID_PERIOD_NS=GRID_PERIOD_US*1000
GRID_TOLERANCE_NS=GRID_TOLERANCE_US*1000

ALLOWED_CASE_FIELDS={
    "seed","cohort","original_public_prints","original_public_l2_snapshots",
    "public_tape_sha256","public_prints_within_frozen_10s_grid",
    "public_fraction_within_frozen_grid","fixed_threshold_0_22_alarm",
    "posthoc_injected_target_present","posthoc_source_controlled_trade_count",
    "correct_synthetic_target_classification","false_alarm_on_background",
    "public_feature_accessed_private_agent_identifiers",
    "private_agent_identifiers_exported","original_market_actor_truth_known",
    "genuine_ABIDES_matching_engine_simulation","real_market_FDR_calibrated",
}


def frozen_plan()->dict:
    p=json.loads(PROTOCOL.read_text(encoding="utf-8"))
    expected=[("poisson_noise_null",True,0),
              ("fixed_cadence_noise_hard_negative",False,0),
              ("twap_injected_positive",True,1)]
    if (p.get("schema_version")!="genuine-abides-public-fixed-grid-transfer-precommit-v1"
            or p.get("frozen_before_first_new_seed_simulation") is not True
            or p.get("abides_upstream_git_commit")!=UPSTREAM_COMMIT
            or p.get("new_locally_uninspected_seeds")!=list(SEEDS)
            or p.get("global_unseen_seed_certification") is not False
            or p.get("simulation_start_exchange_time")!=START
            or p.get("simulation_end_exchange_time")!=END
            or p.get("simulator_instrument")!="ABM"
            or p.get("genuine_abides_l2_book_capture_depth")!=BOOK_DEPTH
            or p.get("source_matching_engine_runs")!=len(SEEDS)*len(COHORTS)
            or p.get("frozen_period_seconds")!=10
            or p.get("frozen_grid_tolerance_ns")!=GRID_TOLERANCE_NS
            or p.get("frozen_fraction_threshold")!=THRESHOLD
            or p.get("fixed_phase_origin_ns")!=0
            or p.get("no_best_phase_model_threshold_or_seed_selection") is not True
            or p.get("private_simulated_owner_ids_only_accessible_posthoc_after_public_feature_computed") is not True
            or p.get("exact_negative_and_positive_cases_must_be_reported") is not True
            or p.get("real_market_FDR_calibrated") is not False
            or [(
                c.get("key"),c.get("poisson"),c.get("injected_twap_agents")
              ) for c in p.get("cohorts",[])]!=expected):
        raise ValueError("Precommitted genuine ABIDES source/score setup changed")
    for cohort in p["cohorts"]:
        if (cohort.get("background_agents")!=60 or
                cohort.get("noise_wakeup_seconds")!=20):
            raise ValueError("Altered original Poisson/fixed-noise background")
    twap=p["cohorts"][2]
    if (twap.get("twap_frequency_seconds")!=45 or
            twap.get("twap_start_and_end_offsets_seconds")!=60 or
            twap.get("twap_order_style")!="market" or
            twap.get("twap_direction")!="BID" or
            twap.get("twap_quantity_lots")!=1200):
        raise ValueError("Injected TWAP schedule altered")
    return p


def score_abides_public_only(prints:tuple[PublicExecution,...])->dict:
    """DO NOT accept source-private matching IDs, simulated agent handles."""
    if type(prints) is not tuple or not 1<=len(prints)<=MAX_FILLS:
        raise ValueError("Expected public-only matched executions")
    last=None
    hits=0
    hasher=sha256()
    for x in prints:
        if type(x) is not PublicExecution:
            raise ValueError("No simulated agent/trade attribution reaches feature")
        ts=x.time_ns
        if (type(ts) is not int or ts<0 or
                type(x.price_cents) is not int or x.price_cents<=0 or
                type(x.quantity) is not int or x.quantity<=0 or
                x.reported_aggressor_side not in ("BUY","SELL")):
            raise ValueError("Malformed public ABIDES execution")
        if last is not None and ts<last:
            raise ValueError("Nonmonotone public exchange execution times")
        last=ts
        phase=ts%GRID_PERIOD_NS
        hits+=min(phase,GRID_PERIOD_NS-phase)<=GRID_TOLERANCE_NS
        hasher.update((
            str(ts)+"|"+str(x.price_cents)+"|"+
            str(x.quantity)+"|"+x.reported_aggressor_side+"\n"
        ).encode("ascii"))
    ratio=hits/len(prints)
    return {
        "public_prints":len(prints),
        "fixed_clock_hit_count":int(hits),
        "fixed_clock_fraction":round(ratio,8),
        "fixed_clock_alarm":ratio>=THRESHOLD,
        "public_tape_sha256":hasher.hexdigest(),
        "actual_private_oracle_data_accessed":False,
        "physical_owner_count_identified":False,
    }


def simulate_case(seed:int,cohort:str)->dict:
    frozen_plan()
    if type(seed) is not int or seed not in SEEDS or cohort not in COHORTS:
        raise ValueError("Missing exact original source experiment seed/cohort")
    from abides_markets.config_system import SimulationBuilder
    from abides_markets.config_system.agent_configs import (
        NoiseAgentConfig,TWAPExecutionAgentConfig
    )
    from abides_markets.config_system.models import ExchangeConfig
    from abides_markets.simulation import ResultProfile,run_simulation

    builder=(SimulationBuilder().apply_template("liquid_market")
             .ticker("ABM").start_time(START).end_time(END)
             .exchange(ExchangeConfig(book_capture="l2",book_log_depth=BOOK_DEPTH))
             .seed(seed))
    builder=builder.enable_agent(NoiseAgentConfig(
        multi_wake=True,wake_up_freq="20s",
        poisson_arrival=(cohort!="fixed_cadence_noise_hard_negative"),
        noise_mkt_close_time=END),count=60)
    if cohort=="twap_injected_positive":
        builder=builder.enable_agent(TWAPExecutionAgentConfig(
            start_time_offset="00:01:00",end_time_offset="00:01:00",
            freq="45s",direction="BID",quantity=1200,trade=True,
            order_style="market"),count=1)
    simulation=run_simulation(builder.build(),profile=ResultProfile.QUANT)
    market=simulation.markets["ABM"]
    if not market.trades or market.l2_series is None:
        raise RuntimeError("Genuine original matching-engine executed tape/L2 unavailable")
    public=public_projection(market.trades)
    evidence=score_abides_public_only(public)
    quote_count=len(market.l2_series.times_ns)
    if not 0<quote_count<=MAX_SNAPSHOTS:
        raise ValueError("Missing or oversized ABIDES public L2 snapshots")

    # Private simulated execution attribution is read ONLY here, AFTER
    # the public feature is fully calculated and fingerprinted.
    controlled={int(agent.agent_id) for agent in simulation.agents
                if str(agent.agent_name).startswith("TWAP_EXECUTION_AGENT_")}
    target=cohort=="twap_injected_positive"
    if len(controlled)!=(1 if target else 0):
        raise RuntimeError("Original requested agent configuration drifted")
    controlled_trades=sum(
        t.passive_agent_id in controlled or t.aggressive_agent_id in controlled
        for t in market.trades
    )
    if target and controlled_trades==0:
        raise RuntimeError("Frozen positive TWAP had no actual controlled fills")
    if not target and controlled_trades:
        raise RuntimeError("Background-only cohort has impossible controlled fills")
    alarm=evidence["fixed_clock_alarm"]
    result={
        "seed":seed,"cohort":cohort,
        "original_public_prints":len(public),
        "original_public_l2_snapshots":quote_count,
        "public_tape_sha256":evidence["public_tape_sha256"],
        "public_prints_within_frozen_10s_grid":evidence["fixed_clock_hit_count"],
        "public_fraction_within_frozen_grid":evidence["fixed_clock_fraction"],
        "fixed_threshold_0_22_alarm":alarm,
        "posthoc_injected_target_present":target,
        "posthoc_source_controlled_trade_count":controlled_trades,
        "correct_synthetic_target_classification":alarm==target,
        "false_alarm_on_background":alarm and not target,
        "public_feature_accessed_private_agent_identifiers":False,
        "private_agent_identifiers_exported":False,
        "original_market_actor_truth_known":False,
        "genuine_ABIDES_matching_engine_simulation":True,
        "real_market_FDR_calibrated":False,
    }
    if set(result)!=ALLOWED_CASE_FIELDS:
        raise AssertionError("Original source output field leaked")
    return result


def audit_result(cases:list[dict])->dict:
    plan=frozen_plan()
    expected={(seed,cohort) for seed in SEEDS for cohort in COHORTS}
    if (type(cases) is not list or len(cases)!=len(expected)
            or {(x.get("seed"),x.get("cohort")) for x in cases
                if type(x) is dict}!=expected):
        raise ValueError("Missing, duplicate or substituted genuine engine cases")
    cohorts={}
    for case in cases:
        if type(case) is not dict or set(case)!=ALLOWED_CASE_FIELDS:
            raise ValueError("Unknown real/private metadata in ABIDES result")
        for key in ("seed","original_public_prints","original_public_l2_snapshots",
                    "public_prints_within_frozen_10s_grid",
                    "posthoc_source_controlled_trade_count"):
            if type(case[key]) is not int or case[key]<0:
                raise ValueError("Noninteger/negative source aggregate "+key)
        n=case["original_public_prints"]
        h=case["public_prints_within_frozen_10s_grid"]
        if (n<=0 or case["original_public_l2_snapshots"]<=0
                or h>n or case["public_fraction_within_frozen_grid"]!=round(h/n,8)
                or case["fixed_threshold_0_22_alarm"] is not (h/n>=THRESHOLD)
                or case["posthoc_injected_target_present"] is not
                     (case["cohort"]=="twap_injected_positive")
                or case["correct_synthetic_target_classification"] is not
                     (case["fixed_threshold_0_22_alarm"]==
                      case["posthoc_injected_target_present"])
                or case["false_alarm_on_background"] is not
                     (case["fixed_threshold_0_22_alarm"] and
                      not case["posthoc_injected_target_present"])):
            raise ValueError("Inconsistent public timing/latent truth score")
        digest=case["public_tape_sha256"]
        if type(digest) is not str or not all(c in "0123456789abcdef" for c in digest) or len(digest)!=64:
            raise ValueError("Missing original public tape SHA256")
        for key in ("public_feature_accessed_private_agent_identifiers",
                    "private_agent_identifiers_exported",
                    "original_market_actor_truth_known","real_market_FDR_calibrated"):
            if case[key] is not False:
                raise ValueError("Source-private/real-world unsupported claim")
        if case["genuine_ABIDES_matching_engine_simulation"] is not True:
            raise ValueError("Not original genuine matching engine source")
        if (case["posthoc_source_controlled_trade_count"]==0)!=(case["cohort"]!="twap_injected_positive"):
            raise ValueError("Posthoc TWAP control count incorrect")
    for cohort in COHORTS:
        group=[x for x in cases if x["cohort"]==cohort]
        cohorts[cohort]={
            "original_matching_engine_simulations":len(group),
            "fixed_grid_alarms":sum(x["fixed_threshold_0_22_alarm"] for x in group),
            "false_alarms_on_background":sum(x["false_alarm_on_background"] for x in group),
            "posthoc_controlled_prints":sum(x["posthoc_source_controlled_trade_count"] for x in group),
            "false_negative_real_TWAP_count":sum(
                x["posthoc_injected_target_present"] and
                not x["fixed_threshold_0_22_alarm"] for x in group),
        }
    return {
        "schema_version":"genuine-abides-frozen-public-clock-transfer-v1",
        "plan":plan,
        "independent_matching_engine_runs":len(cases),
        "source_public_tape_cases":cases,
        "cohort_results":cohorts,
        "new_seeds_not_in_original_local_ledger_before_freeze":list(SEEDS),
        "global_seed_newness_confirmed":False,
        "threshold_or_phase_selected_after_results":False,
        "no_market_personal_identity_or_trading_signal":True,
        "real_market_robot_precision_or_FDR_calibrated":False,
        "private_agent_identifiers_read_only_after_public_feature":True,
        "raw_source_trade_or_l2_book_rows_exported":False,
        "limitations":[
            "Genuine ABIDES market simulation only, not real market or actor identity.",
            "Toy 10sec grid may mismatch genuine injected TWAP freq45sec; negative transfer is valid outcome.",
            "Fixed-cadence background has no separately injected target; public rhythm alone cannot identify target.",
            "Each original simulation seed/cohort is one experiment; no phases chosen posthoc.",
            "No independent real-market false discovery rate or full live source completeness established.",
        ],
    }


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    if args.output.exists():
        p.error("Do not overwrite original controlled source evidence")
    cases=[simulate_case(seed,cohort) for seed in SEEDS for cohort in COHORTS]
    output=audit_result(cases)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x",encoding="utf-8") as f:
        json.dump(output,f,indent=2,sort_keys=True,allow_nan=False)
        f.write("\n")
    for cohort,s in output["cohort_results"].items():
        print("GENUINE_ABIDES_FIXED_GRID_COHORT",json.dumps({
            "cohort":cohort,**s,"real_market_robot_FDR_known":False
        },sort_keys=True))
    print("GENUINE_ABIDES_FIXED_GRID_COMPLETED",json.dumps({
        "actual_matching_engine_runs":len(cases),
        "source_only_aggregate":True,
        "global_blindness_not_asserted":True,
        "real_world_owner_detection_proven":False
    },sort_keys=True))


if __name__=="__main__":
    main()
