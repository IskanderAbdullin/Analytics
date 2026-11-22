"""Public-only ABIDES sparse L2 + EXEC fill causal screen; source-free only.

Design frozen: docs/ABIDES_PUBLIC_SPARSE_L2_CAUSAL_PREREG_20261122.md
This family is NOT the LOBSTER paired visible-type4 event process.
No physical trader ID, real FDR, actual source completeness or live orders.
"""
from bisect import bisect_right
from dataclasses import dataclass
import re

from tools.public_intensity_rescaling import Abstain
from tools.public_abides_epoch_ns_clock import (
    UNIT, SOURCE_UNIT, PINNED_REVISION, qualify_abides_utc_ns_tape,
)

LAG_NS=1_000_000_000
MAX_QUOTE_AGE_NS=10_000_000_000
MAX_TOY_ROWS=100000
_ALLOWED_TRADE=frozenset(("epoch_ns","price_cents","quantity","aggressor_side"))
_ALLOWED_QUOTE=frozenset(("epoch_ns","bid_cents","ask_cents","depth_complete"))


@dataclass(frozen=True)
class PublicABIDESSparseL2Eligibility:
    unit: str
    public_trade_times_ns: tuple
    selected_lagged_public_ask_cents: tuple
    public_post_event_l2_quotes: tuple
    safe_aggregate: dict


def _price(x):
    return type(x) is int and 0<x<=((1<<63)-1)


def _trade_row(row):
    if type(row) is not dict or set(row)!=_ALLOWED_TRADE:
        raise Abstain("PRIVATE_OR_MISSING_ABIDES_PUBLIC_EXECUTION_FIELDS")
    if (not _price(row["price_cents"]) or
        type(row["quantity"]) is not int or not 0<row["quantity"]<=1_000_000_000 or
        type(row["aggressor_side"]) is not str or
        row["aggressor_side"] not in ("BUY","SELL")):
        raise Abstain("INVALID_ABIDES_PUBLIC_EXECUTION_PRICE_QUANTITY_SIDE")


def _quote_row(row):
    if type(row) is not dict or set(row)!=_ALLOWED_QUOTE:
        raise Abstain("PRIVATE_OR_MISSING_ABIDES_PUBLIC_L2_FIELDS")
    if (not _price(row["bid_cents"]) or not _price(row["ask_cents"]) or
        not row["bid_cents"]<row["ask_cents"] or
        type(row["depth_complete"]) is not bool or not row["depth_complete"]):
        raise Abstain("CROSSED_OR_INCOMPLETE_ABIDES_PUBLIC_L2_QUOTE")


def screen_abides_public_execution_sparse_l2(
    trades, sparse_books, *,
    source_run_id, simulation_date,
    window_start_ns, window_end_ns,
    source_family="ABIDES_SIMULATOR",
    source_clock_unit=SOURCE_UNIT,
    window_unit=UNIT,
    pinned_revision=PINNED_REVISION,
    trade_capture_complete=True,
    book_capture_complete=True,
):
    """Qualify source-free toy exec-to-prior-quote, not real L2/data rights."""
    if type(source_family) is not str or source_family!="ABIDES_SIMULATOR":
        raise Abstain("ABIDES_FAMILY_ONLY_NOT_LOBSTER_TYPE4")
    if type(window_unit) is not str or window_unit!=UNIT:
        raise Abstain("UNTYPED_OR_MISMATCHED_ABIDES_SIMULATION_CLOCK")
    if type(source_run_id) is not str or re.fullmatch(r"[A-Za-z0-9_.-]{1,128}",source_run_id) is None:
        raise Abstain("INVALID_OR_PRIVATE_ORIGINAL_SOURCE_RUN_LABEL")
    if (type(trade_capture_complete) is not bool or not trade_capture_complete or
        type(book_capture_complete) is not bool or not book_capture_complete):
        raise Abstain("SOURCE_EVENT_OR_L2_COVERAGE_NOT_ASSERTED_COMPLETE")
    if (type(window_start_ns) is not int or type(window_end_ns) is not int or
        not 34200*LAG_NS<=window_start_ns<window_end_ns<=57600*LAG_NS):
        raise Abstain("INVALID_ABIDES_SIMULATED_SOURCE_WINDOW")
    if (type(trades) not in (tuple,list) or type(sparse_books) not in (tuple,list) or
        not 1<=len(trades)<=MAX_TOY_ROWS or not 1<=len(sparse_books)<=MAX_TOY_ROWS):
        raise Abstain("MISSING_OR_EXCESSIVE_PUBLIC_EXECUTIONS_OR_SPARSE_L2")
    for row in trades:
        _trade_row(row)
    for row in sparse_books:
        _quote_row(row)
    t=qualify_abides_utc_ns_tape(
        [r["epoch_ns"] for r in trades],simulation_date=simulation_date,
        source_unit=source_clock_unit,pinned_revision=pinned_revision,
    )
    q=qualify_abides_utc_ns_tape(
        [r["epoch_ns"] for r in sparse_books],simulation_date=simulation_date,
        source_unit=source_clock_unit,pinned_revision=pinned_revision,
    )
    trade_times=t.ticks
    quote_times=q.ticks
    if any(not window_start_ns<x<window_end_ns for x in trade_times):
        raise Abstain("ABIDES_EXECUTION_OUTSIDE_DECLARED_TRAIN_EVAL_WINDOW")
    if any(x>=window_end_ns for x in quote_times):
        raise Abstain("ABIDES_QUOTE_FUTURE_SUFFIX_OUTSIDE_WINDOW")
    # Preserve source-array final book for each tied exact time, but never
    # expose this quote at its own timestamp due to 1-second feature lag.
    grouped=[]
    tied_quote_rows=0
    for qt,row in zip(quote_times,sparse_books):
        value=(qt,row["bid_cents"],row["ask_cents"])
        if grouped and grouped[-1][0]==qt:
            grouped[-1]=value
            tied_quote_rows+=1
        else:
            grouped.append(value)
    available_t=tuple(x[0] for x in grouped)
    selected=[]
    eligible=missing=stale=0
    for event_time in trade_times:
        i=bisect_right(available_t,event_time-LAG_NS)-1
        if i<0:
            selected.append(None)
            missing+=1
        elif event_time-available_t[i]>MAX_QUOTE_AGE_NS:
            selected.append(None)
            stale+=1
        else:
            selected.append(grouped[i][2])
            eligible+=1
    if eligible+missing+stale!=len(trade_times):
        raise Abstain("UNRECONCILED_ABIDES_PUBLIC_EXECUTION_ELIGIBILITY")
    distinct=len(set(trade_times))
    return PublicABIDESSparseL2Eligibility(
        UNIT,trade_times,tuple(selected),tuple(grouped),
        {
            "status":"SOURCE_FREE_ABIDES_PUBLIC_ONLY_CAUSAL_SCREEN_NOT_MARKET_VALIDATION",
            "source_family":"ABIDES_SIMULATOR",
            "public_exec_rows":len(trade_times),
            "distinct_exact_ns_public_exec_timestamp_clusters":distinct,
            "same_exact_timestamp_additional_public_exec_rows":len(trade_times)-distinct,
            "public_sparse_l2_input_rows":len(quote_times),
            "public_sparse_l2_distinct_exact_ns_quote_times":len(grouped),
            "same_time_l2_extra_rows_last_used_only_after_lag":tied_quote_rows,
            "trade_rows_with_strict_prior_lagged_BBO":eligible,
            "trade_rows_abstain_no_prior_lagged_BBO":missing,
            "trade_rows_abstain_stale_prior_BBO":stale,
            "whole_trade_window_eligible_under_assertions_only":eligible==len(trade_times),
            "full_window_L2_exposure_coverage_independently_proven":False,
            "public_source_trade_capture_independently_proven":False,
            "public_source_simulator_run_date_externally_verified":False,
            "private_agent_ids_used":False,
            "LOBSTER_visible_type4_equivalence_claimed":False,
            "physical_owner_identity_known":False,
            "real_market_fdr_known":False,
            "raw_public_source_rows_exported":False,
        },
    )
