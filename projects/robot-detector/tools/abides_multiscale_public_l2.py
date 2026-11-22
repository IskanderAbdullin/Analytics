#!/usr/bin/env python3
"""Preregistered ABIDES public-only multiscale execution/L2 observations.

Twelve ORIGINAL matching-engine cohorts on three locally unspent seeds;
no private oracle identity in public feature computation. Output contains
ONLY small source-aggregate metadata, not the original market tape.
Fixed-grid fractions/lifts are DESCRIPTIVE and are not p-values, probabilities,
nor optimized classifiers. Quote/book metrics are lagged, not contemporary
source-private order attributes.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from abides_export import UPSTREAM_COMMIT
from l2_trade_context import PublicExecution, public_projection, MAX_FILLS, MAX_SNAPSHOTS
from lagged_l2_bin import summarize_lagged_book
from l2_probe import audit_l2_public
from abides_fixed_clock_transfer import score_abides_public_only

ROOT=Path(__file__).resolve().parents[1]
PROTOCOL=ROOT/"research"/"abides_multiscale_public_l2_protocol_20261121.json"
SEEDS=(2901,2902,2903)
COHORTS=("poisson_noise_null","fixed_20s_noise_hard_negative",
         "momentum_noise_hard_negative","twap_45s_positive")
PERIODS=(10,20,45,90)
LAGGED_BIN_WIDTHS=(30,60)
CASE_ALLOWED_FIELDS=frozenset((
    "seed","cohort","public_prints","public_tape_sha256",
    "grid_hit_counts","grid_fractions",
    "descriptive_grid_lifts_not_probability_or_significance",
    "original_legacy_10s_rule_alarm","original_legacy_10s_rule_fraction",
    "public_only_feature_input_type_verified",
    "actual_private_agent_ids_accessed","real_market_owner_accuracy_calibrated",
    "public_l2_snapshots","public_l2_same_timestamp_repeats",
    "l2_binned_lagged","source_complete_exchange_sequence_proven",
    "private_id_leakage_from_L2_features",
    "raw_quote_rows_or_l2_observations_exported",
    "injected_target_present_only_after_public_inference",
    "controlled_twap_fills_posthoc","true_owner_IDs_exposed",
    "real_market_bot_FDR_known"
))
ANCHOR_NS=34_260_000_000_000
TOLERANCE_NS=250_000_000
BOOK_DEPTH=5
START="09:30:00"
END="09:38:00"


def frozen_protocol()->dict:
    p=json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if (
        p.get("schema_version")!="abides_multiscale_public_l2_precommit_v1"
        or p.get("registered_before_simulation") is not True
        or UPSTREAM_COMMIT not in p.get("source","")
        or p.get("market")!="ABM"
        or (p.get("start"),p.get("end"))!=(START,END)
        or p.get("l2_levels_each_side")!=BOOK_DEPTH
        or p.get("local_ledger_unused_seed_candidates")!=list(SEEDS)
        or p.get("global_blind_status")!="not established; seed novelty only checked against local registry"
        or p.get("cohorts")!=list(COHORTS)
        or p.get("original_matching_engine_runs")!=len(SEEDS)*len(COHORTS)
        or p.get("no_oracle_agent_id_in_public_feature") is not True
        or p.get("source_synthetic_only") is not True
        or p.get("negative_cases_must_never_be_filtered") is not True
        or p.get("raw_market_trades_books_or_oracle_ids_exported") is not False
        or p.get("not_real_market_accuracy_or_FDR") is not True
    ):
        raise ValueError("Frozen multiscale protocol or source scope has drifted")
    f=p["public_only_multiscale_features"]
    if (
        f.get("grid_periods_seconds")!=list(PERIODS)
        or f.get("fixed_anchor_exchange_local_seconds_after_midnight")!=ANCHOR_NS//1_000_000_000
        or f.get("fraction_window_ms")!=TOLERANCE_NS//1_000_000
        or f.get("max_threshold_optimization") is not False
        or f.get("l2_lagged_bin_seconds")!=list(LAGGED_BIN_WIDTHS)
        or f.get("max_quote_age_seconds_equals_bin_seconds") is not True
        or f.get("min_eligible_lagged_bins_for_spearman")!=5
    ):
        raise ValueError("Frozen grid, clock anchor, L2 or timing gate changed")
    expected=[
        (COHORTS[0],60,True,0,0),
        (COHORTS[1],60,False,0,0),
        (COHORTS[2],50,True,10,0),
        (COHORTS[3],60,True,0,1)
    ]
    for item,target in zip(p["cohort_definitions"].items(),expected):
        name,x=item
        if (
            name!=target[0] or x.get("noise_agents")!=target[1]
            or x.get("noise_poisson") is not target[2]
            or x.get("momentum_agents")!=target[3]
            or x.get("twap_agents")!=target[4]
            or x.get("noise_wake")!="20s"
        ):
            raise ValueError("Original cohort size/source identity was modified")
    mn=p["cohort_definitions"][COHORTS[2]]
    tw=p["cohort_definitions"][COHORTS[3]]
    if (
        (mn.get("momentum_wake"),mn.get("momentum_poisson"),
         mn.get("short_window"),mn.get("long_window"))!=("25s",True,5,15)
        or (tw.get("twap_frequency_seconds"),
            tw.get("twap_quantity_lots"),
            tw.get("twap_start_offset_seconds"),
            tw.get("twap_end_offset_seconds"),
            tw.get("twap_style"),tw.get("twap_direction")) !=
            (45,1200,60,60,"market","BID")
    ):
        raise ValueError("Momentum/TWAP configuration changed after source freeze")
    legacy=p["legacy_frozen_10s_alarm"]
    if (
        legacy.get("period_seconds")!=10 or legacy.get("phase_origin_seconds")!=0
        or legacy.get("tolerance_ms")!=250
        or legacy.get("threshold_fraction")!=0.22
    ):
        raise ValueError("Original legacy frozen baseline was altered")
    return p


def _clock_grid_features(public:tuple[PublicExecution,...])->dict:
    """Public executed prints only; oracle agent IDs excluded by type."""
    if type(public) is not tuple or not 1<=len(public)<=MAX_FILLS:
        raise ValueError("Expected bounded nonempty tuple of anonymous executions")
    last=-1
    hasher=sha256()
    hits={str(p):0 for p in PERIODS}
    for row in public:
        if type(row) is not PublicExecution:
            raise ValueError("Expected strictly public-only execution type")
        t=row.time_ns
        if (
            type(t) is not int or t<0 or t<last
            or type(row.quantity) is not int or row.quantity<=0
            or type(row.price_cents) is not int or row.price_cents<=0
            or row.reported_aggressor_side not in ("BUY","SELL")
        ):
            raise ValueError("Invalid or reordered public executed print")
        last=t
        hasher.update(
            f"{t}|{row.price_cents}|{row.quantity}|{row.reported_aggressor_side}\n"
            .encode("ascii")
        )
        for period in PERIODS:
            period_ns=period*1_000_000_000
            phase=(t-ANCHOR_NS)%period_ns
            if min(phase,period_ns-phase)<=TOLERANCE_NS:
                hits[str(period)]+=1
    n=len(public)
    ratios={str(p):round(hits[str(p)]/n,8) for p in PERIODS}
    lifts={str(p):round(
        (hits[str(p)]/n)/(2*TOLERANCE_NS/(p*1_000_000_000)),8
    ) for p in PERIODS}
    legacy=score_abides_public_only(public)
    return {
        "public_prints":n,
        "public_tape_sha256":hasher.hexdigest(),
        "grid_hit_counts":hits,
        "grid_fractions":ratios,
        "descriptive_grid_lifts_not_probability_or_significance":lifts,
        "original_legacy_10s_rule_alarm":legacy["fixed_clock_alarm"],
        "original_legacy_10s_rule_fraction":legacy["fixed_clock_fraction"],
        "public_only_feature_input_type_verified":True,
        "actual_private_agent_ids_accessed":False,
        "real_market_owner_accuracy_calibrated":False
    }


def public_multiscale_l2_summary(
    public:tuple[PublicExecution,...],book
)->dict:
    frozen_protocol()
    original=_clock_grid_features(public)
    if book is None or len(book.times_ns)>MAX_SNAPSHOTS:
        raise ValueError("Missing or oversized public L2 source")
    source=audit_l2_public(book,max_depth=BOOK_DEPTH)
    lagged={}
    for span in LAGGED_BIN_WIDTHS:
        obs=summarize_lagged_book(
            book,public,bin_seconds=span,
            maximum_quote_age_seconds=span,
            maximum_depth=BOOK_DEPTH
        )
        if (
            obs["public_execution_prints"]!=len(public)
            or obs["source_l2_snapshot_count"]!=source["l2_snapshot_events"]
            or obs["private_agent_identifiers_used"] is not False
            or obs["individual_robot_detected"] is not False
            or obs["real_market_significance_calibrated"] is not False
            or obs["previous_completed_bin_only"] is not True
            or obs["eligible_lagged_bins"]+
                sum(obs["abstained_clock_bins"].values()) !=
                obs["populated_execution_clock_bins"]
        ):
            raise AssertionError("Lagged source/oracle/coverage conservation failed")
        lagged[str(span)]={
            "populated_trade_bins":obs["populated_execution_clock_bins"],
            "eligible_previous_completed_book_bins":obs["eligible_lagged_bins"],
            "abstained_bins_by_reason":obs["abstained_clock_bins"],
            "descriptive_lagged_spearman":obs[
                "descriptive_lagged_imbalance_to_next_buy_share_spearman"],
            "rotated_bin_placebo_spearman":obs[
                "rotated_next_bin_share_placebo_spearman"],
            "terminal_bin_may_be_partial":obs[
                "terminal_bin_may_be_partial_without_watermark"],
            "calibrated_p_value_or_actor_accuracy_available":False,
        }
    return {
        **original,
        "public_l2_snapshots":source["l2_snapshot_events"],
        "public_l2_same_timestamp_repeats":source[
            "same_timestamp_repeated_snapshots"],
        "l2_binned_lagged":lagged,
        "source_complete_exchange_sequence_proven":False,
        "private_id_leakage_from_L2_features":False,
        "raw_quote_rows_or_l2_observations_exported":False,
    }


def simulate_case(seed:int,cohort:str)->dict:
    frozen_protocol()
    if type(seed) is not int or seed not in SEEDS or cohort not in COHORTS:
        raise ValueError("Only preregistered synthetic matching-engine inputs")
    from abides_markets.config_system import SimulationBuilder
    from abides_markets.config_system.agent_configs import (
        NoiseAgentConfig,MomentumAgentConfig,TWAPExecutionAgentConfig
    )
    from abides_markets.config_system.models import ExchangeConfig
    from abides_markets.simulation import ResultProfile,run_simulation
    builder=(SimulationBuilder().apply_template("liquid_market")
             .ticker("ABM").start_time(START).end_time(END)
             .exchange(ExchangeConfig(book_capture="l2",book_log_depth=BOOK_DEPTH))
             .seed(seed))
    cohort_params=frozen_protocol()["cohort_definitions"][cohort]
    builder=builder.enable_agent(NoiseAgentConfig(
        multi_wake=True,wake_up_freq="20s",
        poisson_arrival=cohort_params["noise_poisson"],
        noise_mkt_close_time=END),count=cohort_params["noise_agents"])
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
        raise RuntimeError("Simulation lacks public traded prints or L2 capture")
    public=public_projection(market.trades)
    measured=public_multiscale_l2_summary(public,market.l2_series)

    # PRIVATE SOURCE TRUTH ONLY AFTER public-only summary completed.
    controlled={int(a.agent_id) for a in simulation.agents
                if str(a.agent_name).startswith("TWAP_EXECUTION_AGENT_")}
    present=cohort=="twap_45s_positive"
    if len(controlled)!=(1 if present else 0):
        raise RuntimeError("Simulated target oracle configuration changed")
    controlled_fills=sum(t.passive_agent_id in controlled or
                         t.aggressive_agent_id in controlled
                         for t in market.trades)
    if (present and controlled_fills<=0) or (not present and controlled_fills):
        raise RuntimeError("Actual posthoc target execution verification failed")
    result={
        "seed":seed,"cohort":cohort,
        **measured,
        "injected_target_present_only_after_public_inference":present,
        "controlled_twap_fills_posthoc":controlled_fills,
        "true_owner_IDs_exposed":False,
        "real_market_bot_FDR_known":False,
    }
    if set(result)!=CASE_ALLOWED_FIELDS:
        raise AssertionError("Accidentally exported or omitted private/source research fields")
    return result


def validate_results(rows:list[dict])->dict:
    frozen_protocol()
    expected={(s,c) for s in SEEDS for c in COHORTS}
    if (
        type(rows) is not list or len(rows)!=len(expected)
        or {(r.get("seed"),r.get("cohort"))
            for r in rows if type(r) is dict}!=expected
    ):
        raise ValueError("Missing, duplicate or substituted source case")
    safe=[]
    for x in rows:
        if type(x) is not dict or set(x)!=CASE_ALLOWED_FIELDS:
            raise ValueError("Source private field or missing required aggregate")
        if type(x["public_prints"]) is not int or not 0<x["public_prints"]<=MAX_FILLS:
            raise ValueError("Original public executed tape missing")
        if (type(x["public_l2_snapshots"]) is not int
                or not 0<x["public_l2_snapshots"]<=MAX_SNAPSHOTS
                or x["source_complete_exchange_sequence_proven"] is not False):
            raise ValueError("Unknown source completeness or missing L2")
        if (type(x["public_tape_sha256"]) is not str or
                len(x["public_tape_sha256"])!=64 or
                any(ch not in "0123456789abcdef" for ch in x["public_tape_sha256"])):
            raise ValueError("Source-public print fingerprint unavailable")
        if type(x["controlled_twap_fills_posthoc"]) is not int or x["controlled_twap_fills_posthoc"]<0:
            raise ValueError("Invalid private oracle count")
        for attr in ("public_only_feature_input_type_verified",):
            if x[attr] is not True:
                raise ValueError("Public projection validation failed")
        for attr in ("actual_private_agent_ids_accessed",
                     "private_id_leakage_from_L2_features",
                     "real_market_owner_accuracy_calibrated",
                     "raw_quote_rows_or_l2_observations_exported",
                     "true_owner_IDs_exposed","real_market_bot_FDR_known"):
            if x.get(attr) is not False:
                raise ValueError("Unsupported private-market inference/source field")
        if (
            x["injected_target_present_only_after_public_inference"] is not
            (x["cohort"]=="twap_45s_positive")
            or (x["controlled_twap_fills_posthoc"]>0) is not
            x["injected_target_present_only_after_public_inference"]
        ):
            raise ValueError("Posthoc truth does not reconcile")
        if set(x["grid_fractions"])!=set(map(str,PERIODS)):
            raise ValueError("Multiscale source feature set was altered")
        for p in PERIODS:
            num=x["grid_hit_counts"][str(p)]
            if (
                type(num) is not int or not 0<=num<=x["public_prints"]
                or x["grid_fractions"][str(p)]!=round(num/x["public_prints"],8)
            ):
                raise ValueError("Public clock grid numerator/denominator changed")
        if set(x["l2_binned_lagged"])!=set(map(str,LAGGED_BIN_WIDTHS)):
            raise ValueError("Missing one of two lagged quote-width negatives")
        for width in LAGGED_BIN_WIDTHS:
            z=x["l2_binned_lagged"][str(width)]
            if (
                z["eligible_previous_completed_book_bins"]+
                sum(z["abstained_bins_by_reason"].values())!=
                z["populated_trade_bins"]
            ):
                raise ValueError("L2 abstention count lost")
        safe.append(x)
    cohorts={}
    for c in COHORTS:
        group=[x for x in safe if x["cohort"]==c]
        cohorts[c]={
            "independent_engine_runs":len(group),
            "total_executed_prints":sum(z["public_prints"] for z in group),
            "total_l2_snapshots":sum(z["public_l2_snapshots"] for z in group),
            "total_posthoc_controlled_twap_fills":sum(
                z["controlled_twap_fills_posthoc"] for z in group),
            "original_10s_legacy_false_alarms_or_hits":sum(
                z["original_legacy_10s_rule_alarm"] for z in group),
            "descriptive_mean_fraction_by_period":{
                str(p):round(sum(z["grid_fractions"][str(p)]
                                 for z in group)/len(group),8) for p in PERIODS
            },
            "total_abstained_trade_bins_30s":sum(sum(z[
                "l2_binned_lagged"]["30"]["abstained_bins_by_reason"].values())
                for z in group),
            "total_abstained_trade_bins_60s":sum(sum(z[
                "l2_binned_lagged"]["60"]["abstained_bins_by_reason"].values())
                for z in group),
        }
    return {
        "schema_version":"genuine-abides-public-only-multiscale-l2-research-v1",
        "precommitted_protocol":str(PROTOCOL.relative_to(ROOT)),
        "simulator_upstream_commit":UPSTREAM_COMMIT,
        "completed_independent_source_engine_runs":len(rows),
        "all_original_source_cases":safe,
        "cohort_aggregates":cohorts,
        "regression_source_study":"Legacy 10s gave 2/2 fixed noise false alarms, 2/2 TWAP misses; kept unchanged",
        "market_user_identity_or_real_FDR_established":False,
        "thresholds_selected_from_new_results":False,
        "source_global_seed_novelty_certified":False,
        "no_raw_source_market_trades_or_agent_ids_uploaded":True,
        "limitations":[
            "Genuine ABIDES matching engine only, not original live exchange.",
            "This is a descriptive preregistered feature comparison, not a trained classifier.",
            "Fixed clock grids can match non-target background periodicity.",
            "Previous-completed L2 bins use an uncertified last-bin source watermark; abstentions are explicit.",
            "No true physical owner labels, real market FDR, independent coverage proof or trading permissions.",
        ]
    }


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():
        p.error("Refusing to replace original frozen research result")
    rows=[simulate_case(seed,cohort) for seed in SEEDS for cohort in COHORTS]
    result=validate_results(rows)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("x",encoding="utf-8") as f:
        json.dump(result,f,indent=2,sort_keys=True,allow_nan=False)
        f.write("\n")
    for c,v in result["cohort_aggregates"].items():
        print("ABIDES_MULTISCALE_COHORT",json.dumps({
            "cohort":c,**v,"real_market_accuracy_established":False
        },sort_keys=True))
    print("ABIDES_MULTISCALE_SOURCE_RESEARCH_DONE",json.dumps({
        "independent_source_runs":len(rows),
        "negative_hard_controls_retained":True,
        "true_owner_labels_in_public_features":False
    },sort_keys=True))


if __name__=="__main__":
    main()
