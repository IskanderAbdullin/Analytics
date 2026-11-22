"""Public event-type projection for exact-ns visible LOBSTER-style executions.

Precommitted: docs/LOBSTER_NS_PUBLIC_EXECUTION_PROJECTION_PREREG_20261122.md
Source-free toy rows only; no original ZIP, order refs or private actor data.
The selected quote is always POST-event and can be used only after model lag.
"""
from dataclasses import dataclass
from tools.public_intensity_rescaling import Abstain
from tools.public_lobster_ns_time import UNIT
from tools.public_m1_v3_ns_l2 import _valid_ns, _valid_price

MAX_PAIRED_ROWS=100000
_FIELDS=frozenset(("timestamp_ns","event_type","resting_side","bid_price","ask_price","complete"))


@dataclass(frozen=True)
class NsVisibleExecutionAndPostEventBBO:
    unit: str
    visible_type4_trade_cluster_times_ns: tuple
    post_event_bbo_snapshots: tuple
    safe_aggregate: dict


def project_public_ns_visible_executions(
    paired_rows, *, source_time_unit, source_precision_ns, interval_complete,
):
    """Separate type-4 visible executions from all post-event book updates.

    The source metadata is asserted by the caller, NOT independently certified.
    Internal timestamp/quote tuples must never be printed as a vendor artifact.
    """
    if type(source_time_unit) is not str or source_time_unit!=UNIT:
        raise Abstain("INCORRECT_SOURCE_NANOSECOND_TIME_UNIT")
    if type(source_precision_ns) is not int or source_precision_ns!=1:
        raise Abstain("UNVERIFIED_OR_COARSE_SOURCE_EVENT_PRECISION")
    if type(interval_complete) is not bool or not interval_complete:
        raise Abstain("UNVERIFIED_OR_INCOMPLETE_PAIRED_PUBLIC_SOURCE")
    if type(paired_rows) not in (list,tuple) or not 1<=len(paired_rows)<=MAX_PAIRED_ROWS:
        raise Abstain("INVALID_OR_EXCESSIVE_PAIRED_PUBLIC_EVENT_ROWS")
    books=[]
    visible=[]
    previous_time=None
    total_visible=hidden=buy=sell=nontrade=all_exact_ties=0
    for row in paired_rows:
        if type(row) is not dict or set(row)!=_FIELDS:
            raise Abstain("FORBIDDEN_OR_MISSING_PUBLIC_EVENT_FIELDS")
        ts,etype,side = row["timestamp_ns"],row["event_type"],row["resting_side"]
        if not _valid_ns(ts) or type(etype) is not int or etype not in range(1,8):
            raise Abstain("INVALID_NS_TIME_OR_PUBLIC_EVENT_TYPE")
        if type(side) is not int or side not in (-1,1):
            raise Abstain("INVALID_PUBLIC_RESTING_SIDE")
        if type(row["complete"]) is not bool or not row["complete"]:
            raise Abstain("MISSING_POST_EVENT_PUBLIC_BBO")
        bid,ask=row["bid_price"],row["ask_price"]
        if not _valid_price(bid) or not _valid_price(ask) or bid>ask:
            raise Abstain("INVALID_POST_EVENT_PUBLIC_BBO")
        if previous_time is not None and ts<previous_time:
            raise Abstain("UNSORTED_PUBLIC_NANOSECOND_MESSAGE_HISTORY")
        clean={"timestamp_ns":ts,"bid_price":bid,"ask_price":ask,"complete":True}
        if books and ts==books[-1]["timestamp_ns"]:
            books[-1]=clean  # last POST-event state within exact source time group
            all_exact_ties += 1
        else:
            books.append(clean)
        if etype==4:
            total_visible += 1
            if side==-1:
                buy += 1  # resting SELL; visible aggressive BUY
            else:
                sell += 1
            if not visible or ts!=visible[-1]:
                visible.append(ts)
        elif etype==5:
            hidden += 1  # do not infer aggressor from hidden executions
        else:
            nontrade += 1
        previous_time=ts
    if (total_visible != buy+sell or total_visible+hidden+nontrade!=len(paired_rows)
            or len(books)+all_exact_ties != len(paired_rows)):
        raise Abstain("UNRECONCILED_PUBLIC_MESSAGE_EXECUTION_PROJECTION")
    return NsVisibleExecutionAndPostEventBBO(
        UNIT,tuple(visible),tuple(books),
        {
            "status":"SOURCE_FREE_VISIBLE_TYPE4_EXECUTIONS_NOT_FULL_TRADE_TRUTH",
            "source_message_and_post_event_book_rows":len(paired_rows),
            "exact_source_timestamp_groups_all_messages":len(books),
            "all_message_exact_timestamp_ties":all_exact_ties,
            "visible_type4_executions":total_visible,
            "visible_type4_exact_trade_timestamp_clusters":len(visible),
            "visible_type4_tied_additional_fills":total_visible-len(visible),
            "visible_aggressive_buy_inferred_from_resting_sell":buy,
            "visible_aggressive_sell_inferred_from_resting_buy":sell,
            "hidden_type5_executions_not_direction_inferred":hidden,
            "other_source_message_events_not_visible_type4_trades":nontrade,
            "source_time_unit":UNIT,
            "source_completeness_independently_verified":False,
            "true_market_trade_only_ms_collision_rate_known":False,
            "physical_owner_identity_known":False,
            "real_market_fdr_known":False,
            "raw_vendor_event_order_or_book_rows_exported":False,
        }
    )
