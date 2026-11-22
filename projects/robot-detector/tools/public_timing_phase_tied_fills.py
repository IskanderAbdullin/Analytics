#!/usr/bin/env python3
"""Precommitted source-free timestamp tie and fixed-grid phase counterexample.

The same synthetic background source has 13 unique execution times; whether
the 45s-only time produces ONE or ONE HUNDRED public partial fills has
no identifiable owner interpretation. This study shows why printing all fills
as independent clock observations changes a naive 45s/20s ratio.

Never a real-market trading or actor-identification tool. Only tiny
aggregates are exported; source event timestamps/owner IDs stay in memory.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from l2_trade_context import PublicExecution
from public_numeric import exact_nonnegative_integer as exact_int

ROOT=Path(__file__).resolve().parents[1]
PROTOCOL=ROOT/"research"/"public_phase_tied_fills_precommit_20261121.json"
DAY_NS=86_400_000_000_000
SESSION_START=34_200_000_000_000
SESSION_END=34_680_000_000_000
ANCHOR_NS=34_260_000_000_000
PERIODS=(20,45)
TOL_NS=250_000_000
FIXED_SHIFTS_MS=(-300,-250,0,250,300)
THRESHOLD=0.60
ALLOWED_PUBLIC=frozenset(PublicExecution.__dataclass_fields__)


def frozen_plan()->dict:
    p=json.loads(PROTOCOL.read_text(encoding="utf-8"))
    s=p.get("source_public_baseline",{})
    if (
        p.get("schema_version")!="public-timing-phase-and-tied-split-fills-protocol-v1"
        or p.get("research_stage")!="RD-PHASE-ROBUSTNESS-11"
        or p.get("triggering_original_source_runs")!=[44936592641,44937478576]
        or p.get("phase_anchor_exchange_local_seconds_after_midnight")!=34260
        or p.get("grid_periods_seconds")!=list(PERIODS)
        or p.get("clock_tolerance_nanoseconds")!=TOL_NS
        or p.get("diagnostic_shifts_milliseconds")!=list(FIXED_SHIFTS_MS)
        or p.get("observed_within_session")!=["09:30:00","09:38:00"]
        or p.get("source_type")!="fully synthetic construction, no new genuine ABIDES or vendor tape"
        or s.get("fixed_20s_grid_events_timestamps_synthetic_offset_periods")!=list(range(1,13))
        or s.get("additional_45s_only_timestamp_offset_seconds")!=45
        or s.get("single_public_fill_at_45_only_timestamp")!=1
        or s.get("split_public_fills_at_same_45_only_timestamp")!=100
        or s.get("all_synthetic_events_are_non_target_background") is not True
        or set(s.get("source_visible_fields",[]))!=ALLOWED_PUBLIC
        or p.get("fixed_descriptive_alarm_ratio_threshold")!=THRESHOLD
        or p.get("abstention_if_denominator_grid20_zero") is not True
        or p.get("private_owner_or_agent_IDs_forbidden_in_public_inputs") is not True
        or p.get("source_raw_timestamps_or_per_event_tapes_not_exported") is not True
        or p.get("real_market_owner_FDR_p_value_or_classifier_accuracy_unavailable") is not True
        or p.get("synthetic_ties_not_identification_of_parent_order") is not True
        or p.get("no_GitHub_source_network_download_required") is not True
        or p.get("preserve_negative_outcomes_if_rule_fails") is not True
    ):
        raise ValueError("Precommitted source-free timing/tied-fill scientific design drift")
    return p


def build_synthetic_public(*, split_fills:int)->tuple[PublicExecution,...]:
    frozen_plan()
    if type(split_fills) is not int or split_fills not in (1,100):
        raise ValueError("Only original frozen single vs split-fill constructions")
    t=[ANCHOR_NS+j*PERIODS[0]*1_000_000_000 for j in range(1,13)]
    special=ANCHOR_NS+45_000_000_000
    t.extend([special]*split_fills)
    # Anonymous prints; no private order/parent/owner IDs exist in this schema.
    return tuple(PublicExecution(time_ns=v,price_cents=100_100,
            quantity=1,reported_aggressor_side="BUY") for v in sorted(t))


def _strict_public(public:tuple[PublicExecution,...])->None:
    if type(public) is not tuple or not 1<=len(public)<=1000:
        raise ValueError("Expected bounded strict public executed print tuple")
    if ALLOWED_PUBLIC!=frozenset(("time_ns","price_cents","quantity",
                                "reported_aggressor_side")):
        raise AssertionError("Anonymous public source projection unexpectedly changed")
    last=-1
    source_days=set()
    for x in public:
        if type(x) is not PublicExecution:
            raise ValueError("Private oracle/source agent field not permitted")
        t=exact_int(x.time_ns,"public event time ns")
        if (not SESSION_START<=t%DAY_NS<SESSION_END or t<last
            or type(x.price_cents) is not int or x.price_cents<=0
            or type(x.quantity) is not int or x.quantity<=0
            or x.reported_aggressor_side not in ("BUY","SELL")):
            raise ValueError("Out-of-session, reordered or malformed public print")
        last=t
        source_days.add(t//DAY_NS)
    if len(source_days)!=1:
        raise ValueError("Public clock comparison requires one trading date")


def phase_counts(public:tuple[PublicExecution,...], *, shift_ms:int,
                 collapse_same_timestamp:bool)->dict:
    """All shifts specified IN ADVANCE; no best-phase fitting or p-values."""
    if type(shift_ms) is not int or shift_ms not in FIXED_SHIFTS_MS:
        raise ValueError("Only 5 preregistered source-free clock shifts")
    if type(collapse_same_timestamp) is not bool:
        raise ValueError("Timestamp-cluster option must be explicit bool")
    _strict_public(public)
    stamps=[x.time_ns for x in public]
    n_prints=len(stamps)
    stamps=sorted(set(stamps)) if collapse_same_timestamp else stamps
    hit_counts={}
    for period in PERIODS:
        p=period*1_000_000_000
        hit_counts[str(period)]=sum(
            min(rem,p-rem)<=TOL_NS
            for t in stamps
            for rem in (((t%DAY_NS)+shift_ms*1_000_000-ANCHOR_NS)%p,)
        )
    h20,h45=hit_counts["20"],hit_counts["45"]
    return {
        "unit":"unique_execution_timestamps" if collapse_same_timestamp else "public_execution_prints",
        "shift_milliseconds":shift_ms,
        "total_original_public_prints":n_prints,
        "counted_public_observations":len(stamps),
        "equal_timestamp_repeated_prints":n_prints-len(set(x.time_ns for x in public)),
        "hit_counts":hit_counts,
        "observed_ratio_45s_over_20s":round(h45/h20,8) if h20 else None,
        "fixed_ratio_0_60_alarm":h20>0 and h45/h20>=THRESHOLD,
        "abstained_zero_20s_denominator":h20==0,
        "physical_order_owner_identity_estimated":False
    }


def original_counterexample()->dict:
    frozen_plan()
    constructions={}
    for name,count in (("single_fill",1),("hundred_tied_fills",100)):
        tape=build_synthetic_public(split_fills=count)
        reports=[
            phase_counts(tape,shift_ms=shift,collapse_same_timestamp=collapse)
            for collapse in (False,True)
            for shift in FIXED_SHIFTS_MS
        ]
        constructions[name]={
            "original_source_public_prints":len(tape),
            "original_source_unique_timestamps":len(set(x.time_ns for x in tape)),
            "all_predeclared_phase_results":reports,
            "synthetic_non_target_background_only":True,
            "private_source_owner_labels_available":False
        }
    src=constructions["single_fill"]
    split=constructions["hundred_tied_fills"]
    def at0(x,kind):
        hits=[r for r in x["all_predeclared_phase_results"]
              if r["shift_milliseconds"]==0 and r["unit"]==kind]
        if len(hits)!=1: raise AssertionError("Zero-shift comparison missing")
        return hits[0]
    single=at0(src,"public_execution_prints")
    many=at0(split,"public_execution_prints")
    collapsed=at0(split,"unique_execution_timestamps")
    if not (
        single["counted_public_observations"]==13
        and many["counted_public_observations"]==112
        and collapsed["counted_public_observations"]==13
        and not single["fixed_ratio_0_60_alarm"]
        and many["fixed_ratio_0_60_alarm"]
        and not collapsed["fixed_ratio_0_60_alarm"]
        and single["hit_counts"]==collapsed["hit_counts"]
    ):
        raise AssertionError("Exact theoretical pseudo-replication counterexample failed")
    return {
        "schema_version":"public-clock-phase-tied-fill-negative-observed-v1",
        "frozen_protocol":"research/public_phase_tied_fills_precommit_20261121.json",
        "constructions":constructions,
        "original_fixed_grid_periods_seconds":list(PERIODS),
        "original_fixed_clock_shift_matrix_ms":list(FIXED_SHIFTS_MS),
        "synthetic_100_split_prints_are_not_100_independent_orders":True,
        "same_timestamp_grouping_cannot_prove_single_parent_order":True,
        "print_vs_event_weighted_source_claims_differ":True,
        "phase_results_are_descriptive_not_selected_best_phase":True,
        "real_market_order_owner_FDR_or_p_value_calibrated":False,
        "source_original_exchange_or_ABIDES_data_used":False,
        "real_broker_trading_enabled":False,
        "raw_event_timestamps_or_private_agent_IDs_exported":False,
        "scientific_limitations":[
            "Identical timestamp may include truly separate orders; collapse is a diagnostic.",
            "Printed executions of one parent market event can be split into many dependent fills.",
            "A fixed grid can be defeated by 300ms time shift at 250ms tolerance.",
            "These construction scores are not inferential p-values or real-bot probabilities.",
            "Real-world owner identity and full feed coverage remain unknown."
        ]
    }


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():
        p.error("Never overwrite original illustrative negative observation")
    r=original_counterexample()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("x",encoding="utf-8") as f:
        json.dump(r,f,indent=2,sort_keys=True,allow_nan=False)
        f.write("\n")
    def zero(construction,unit):
        return next(x for x in r["constructions"][construction]["all_predeclared_phase_results"]
                    if x["unit"]==unit and x["shift_milliseconds"]==0)
    print("PUBLIC_CLOCK_TIED_SPLIT_NEGATIVE",json.dumps({
        "single_print_score":zero("single_fill","public_execution_prints")["observed_ratio_45s_over_20s"],
        "hundred_split_fill_print_score":zero("hundred_tied_fills","public_execution_prints")["observed_ratio_45s_over_20s"],
        "hundred_split_fill_unique_time_score":zero("hundred_tied_fills","unique_execution_timestamps")["observed_ratio_45s_over_20s"],
        "public_pattern_is_not_owner_ID":True,
        "real_market_FDR_known":False
    },sort_keys=True))


if __name__=="__main__":
    main()
