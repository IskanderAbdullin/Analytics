#!/usr/bin/env python3
"""Frozen source-free public event-time versus anchored clock negative.

A 20-second background with NO injected TWAP has 89 consecutive unique 20s
interarrivals, even after translating every timestamp +1s; the 250ms-anchored
absolute-clock detections vanish. Adding 100 prints at a different 45s-only
timestamp creates a false per-print 45s concentration without target.
This is diagnostic, NOT a valid real-market FDR/p-value or owner inference.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from l2_trade_context import PublicExecution

ROOT=Path(__file__).resolve().parents[1]
PROTOCOL=ROOT/"research"/"public_interarrival_period_scan_precommit_20261121.json"
PERIODS=(10,15,20,30,45,60,90)
SHIFTS_NS=(0,1_000_000_000)
ANCHOR_NS=34_260_000_000_000
TOLERANCE_NS=250_000_000
N_BACKGROUND=90
BACKGROUND_STEP_NS=20_000_000_000
SPLIT_OFFSET_NS=45_000_000_000
SPLIT_FILLS=100
ALLOWED_PUBLIC_FIELDS=frozenset(("time_ns","price_cents","quantity","reported_aggressor_side"))


def frozen_protocol()->dict:
    p=json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if (
        p.get("schema_version")!="public-clustered-interarrival-period-scan-preregistered-negative-v1"
        or p.get("scientific_stage")!="RD-PUBLIC-CONDITIONAL-NULL-16"
        or p.get("motivation_original_genuine_source_runs")!=[44944144915,44944168231]
        or p.get("source_kind")!="fully constructed public-only exact timestamp toy, no new ABIDES or real market data"
        or p.get("source_unique_event_count")!=N_BACKGROUND
        or p.get("source_period_seconds")!=20
        or p.get("source_start_exchange_local_seconds_after_midnight")!=34260
        or p.get("source_global_clock_shifts_ns")!=list(SHIFTS_NS)
        or p.get("source_equal_timestamp_extra_prints_in_split_variant")!=SPLIT_FILLS-1
        or p.get("split_variant_45s_only_offset_seconds")!=45
        or p.get("scan_periods_seconds")!=list(PERIODS)
        or p.get("grid_anchor_exchange_local_seconds_after_midnight")!=34260
        or p.get("grid_tolerance_ns")!=TOLERANCE_NS
        or p.get("consecutive_interarrival_tolerance_ns")!=TOLERANCE_NS
        or p.get("min_unique_event_timestamps")!=10
        or any(p.get(key) is not True for key in (
            "no_source_oracle_agent_IDs_or_real_parent_orders",
            "no_hidden_best_phase_or_period_selection_for_phenomenological_significance",
            "all_candidate_periods_and_phase_shift_cases_output",
            "no_market_FDR_p_value_or_owner_identity_claim",
            "zero_interarrival_from_same_timestamp_split_prints_not_independent_events",
            "pure_source_free_no_vendor_archive_or_broker_connection",
            "negative_cases_not_selectively_discarded"
        ))
    ):
        raise ValueError("Frozen public interarrival/phase protocol changed")
    return p


def make_public(*, global_shift_ns:int, add_split_fills:bool
               )->tuple[PublicExecution,...]:
    frozen_protocol()
    if type(global_shift_ns) is not int or global_shift_ns not in SHIFTS_NS:
        raise ValueError("Global source shift must be precommitted exactly")
    if type(add_split_fills) is not bool:
        raise ValueError("Split-fill variant requires exact bool")
    timestamps=[ANCHOR_NS+j*BACKGROUND_STEP_NS+global_shift_ns
                for j in range(N_BACKGROUND)]
    if add_split_fills:
        timestamps.extend([ANCHOR_NS+SPLIT_OFFSET_NS+global_shift_ns]*SPLIT_FILLS)
    return tuple(PublicExecution(t,100100,1,"BUY") for t in sorted(timestamps))


def audit_public(executions:tuple[PublicExecution,...])->dict:
    frozen_protocol()
    if type(executions) is not tuple or not 10<=len(executions)<=200:
        raise ValueError("Expected bounded public trade print tuple")
    if ALLOWED_PUBLIC_FIELDS!=frozenset(PublicExecution.__dataclass_fields__):
        raise ValueError("Source public projection was modified")
    prev=-1
    timestamps=[]
    for x in executions:
        if type(x) is not PublicExecution:
            raise ValueError("Private owner attributes are forbidden")
        t=x.time_ns
        if (type(t) is not int or t<0 or t<prev
            or type(x.price_cents) is not int or x.price_cents<=0
            or type(x.quantity) is not int or x.quantity<=0
            or x.reported_aggressor_side not in ("BUY","SELL")):
            raise ValueError("Invalid or unordered anonymous public print")
        timestamps.append(t)
        prev=t
    unique=sorted(set(timestamps))
    if len(unique)<10:
        raise ValueError("Insufficient unique public execution times")
    result={}
    for period in PERIODS:
        step_ns=period*1_000_000_000
        hits_print=sum(
            min(rem,step_ns-rem)<=TOLERANCE_NS for t in timestamps
            for rem in ((t-ANCHOR_NS)%step_ns,)
        )
        hits_unique=sum(
            min(rem,step_ns-rem)<=TOLERANCE_NS for t in unique
            for rem in ((t-ANCHOR_NS)%step_ns,)
        )
        hits_delta_print=sum(abs(b-a-step_ns)<=TOLERANCE_NS
            for a,b in zip(timestamps,timestamps[1:]))
        hits_delta_unique=sum(abs(b-a-step_ns)<=TOLERANCE_NS
            for a,b in zip(unique,unique[1:]))
        result[str(period)]={
            "period_seconds":period,
            "absolute_grid_print_hits":hits_print,
            "absolute_grid_unique_time_hits":hits_unique,
            "consecutive_print_interarrival_hits":hits_delta_print,
            "consecutive_unique_interarrival_hits":hits_delta_unique,
            "executed_prints":len(timestamps),
            "unique_time_groups":len(unique),
            "print_intervals":len(timestamps)-1,
            "unique_time_intervals":len(unique)-1
        }
    return {
        "source_prints":len(timestamps),
        "source_unique_times":len(unique),
        "same_timestamp_extra_prints":len(timestamps)-len(unique),
        "zero_length_print_interarrival_count":sum(a==b for a,b in zip(timestamps,timestamps[1:])),
        "period_grid_all_frozen_candidates":result,
        "owner_or_parent_order_IDs_in_public_features":False,
        "calibrated_market_significance_or_FDR":False
    }


def original_negative_matrix()->dict:
    frozen_protocol()
    cases=[]
    for split in (False,True):
        for shift in SHIFTS_NS:
            row=audit_public(make_public(global_shift_ns=shift,add_split_fills=split))
            cases.append({
                "synthetic_case":"unrelated_tied_100_prints" if split else "fixed_20s_no_target",
                "precommitted_global_shift_ns":shift,
                **row
            })
    base,shifted,tied,tied_shifted=cases
    if (
        len(cases)!=4 or base["source_prints"]!=90
        or shifted["source_prints"]!=90
        or tied["source_prints"]!=190
        or tied["source_unique_times"]!=91
        or tied["same_timestamp_extra_prints"]!=99
        or tied["zero_length_print_interarrival_count"]!=99
    ):
        raise AssertionError("Original frozen source-free sample count drift")
    for period in PERIODS:
        key=str(period)
        for orig,translated in ((base,shifted),(tied,tied_shifted)):
            original=orig["period_grid_all_frozen_candidates"][key]
            moved=translated["period_grid_all_frozen_candidates"][key]
            if (moved["absolute_grid_print_hits"]!=0
                or moved["absolute_grid_unique_time_hits"]!=0
                or original["consecutive_unique_interarrival_hits"]!=
                   moved["consecutive_unique_interarrival_hits"]):
                raise AssertionError("Absolute grid shift vs event-time invariance failed")
    if (
        base["period_grid_all_frozen_candidates"]["20"]["consecutive_unique_interarrival_hits"]!=89
        or tied["period_grid_all_frozen_candidates"]["20"]["consecutive_unique_interarrival_hits"]!=88
        or tied["period_grid_all_frozen_candidates"]["45"]["absolute_grid_print_hits"]!=110
        or tied["period_grid_all_frozen_candidates"]["45"]["absolute_grid_unique_time_hits"]!=11
    ):
        raise AssertionError("Public split-fill false rhythmic concentration counterexample drift")
    return {
        "schema_version":"public-interarrival-period-scan-source-free-negative-v1",
        "frozen_original_protocol":"research/public_interarrival_period_scan_precommit_20261121.json",
        "four_precommitted_public_source_cases":cases,
        "seven_frozen_candidate_periods_seconds":list(PERIODS),
        "two_frozen_clock_shifts_ns":list(SHIFTS_NS),
        "no_source_injected_45s_agent_in_any_case":True,
        "interarrival_shift_invariance_does_not_identify_owner":True,
        "timestamp_split_fills_not_independent_parent_orders":True,
        "posthoc_best_period_or_phase_was_not_selected":True,
        "real_market_pvalues_FDR_or_actor_labels_calibrated":False,
        "no_raw_event_time_series_or_private_IDs_exported":True,
        "actual_exchange_or_ABIDES_source_accessed":False
    }


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():
        p.error("Do not overwrite original precommitted source-free report")
    report=original_negative_matrix()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("x",encoding="utf-8") as f:
        json.dump(report,f,indent=2,sort_keys=True,allow_nan=False)
        f.write("\n")
    x=report["four_precommitted_public_source_cases"]
    print("FROZEN_PUBLIC_INTERARRIVAL_COUNTEREXAMPLE",json.dumps({
        "source_free_cases":4,
        "no_target_20s_interarrival_hits":x[0]["period_grid_all_frozen_candidates"]["20"]["consecutive_unique_interarrival_hits"],
        "shifted_absolute_grid_20s_hits":x[1]["period_grid_all_frozen_candidates"]["20"]["absolute_grid_print_hits"],
        "unrelated_100_tied_45s_grid_print_hits":x[2]["period_grid_all_frozen_candidates"]["45"]["absolute_grid_print_hits"],
        "unique_timestamps_45s_hits":x[2]["period_grid_all_frozen_candidates"]["45"]["absolute_grid_unique_time_hits"],
        "real_market_FDR_known":False
    },sort_keys=True))


if __name__=="__main__":
    main()
