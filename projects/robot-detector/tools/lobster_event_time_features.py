#!/usr/bin/env python3
"""Read-only event-time features for paired public LOBSTER demo messages/book.

All statistics are EVENT-weighted or explicitly count-weighted; no event,
book, order ID, price level or interval with a unique timestamp is exported.
Only descriptive research, no actor attribution or financial trading.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from decimal import Decimal
from hashlib import sha256
import io
from itertools import zip_longest
import json
from pathlib import Path
from zipfile import ZipFile

if __package__:
    from .l2_duration_weighting import DurationWeightedBBO
    from .lobster_public_sample_format_audit import (
        SOURCE_URL, MAX_ZIP_BYTES, MAX_ROWS, _members, _validate_book,
        _validate_message, audit_sample_zip, download_exact_demo, is_zipfile
    )
else:
    from l2_duration_weighting import DurationWeightedBBO
    from lobster_public_sample_format_audit import (
        SOURCE_URL, MAX_ZIP_BYTES, MAX_ROWS, _members, _validate_book,
        _validate_message, audit_sample_zip, download_exact_demo, is_zipfile
    )

# This is a LOCAL historical digest observed on a prior run; the publisher
# supplies no signed/published SHA-256. It must never be called official.
LOCALLY_PINNED_SAMPLE_SHA256 = (
    "5cff62a609b27aef82285382ad646c4c2facc0a692a60bedda633de64c4aa54f"
)
HALF_HOUR_SECONDS = 1800
SESSION_START = Decimal(34200)
SESSION_END = Decimal(57600)
HALF_HOUR_BUCKETS = 13
OUTPUT_ALLOWED_TOP_FIELDS = frozenset((
    "schema_version","source_url","sample_symbol","sample_date",
    "locally_observed_source_zip_sha256","original_locally_pinned_sha256_matched",
    "provider_signed_checksum_available","event_count","paired_l2_post_event_states",
    "event_type_counts","visible_aggressor_buy_executions",
    "visible_aggressor_sell_executions","hidden_executions_resting_side_not_aggressor",
    "distinct_event_timestamp_groups","same_timestamp_repeated_event_pairs",
    "max_events_in_one_exact_timestamp_group","event_time_gap_zero",
    "event_time_gap_positive","max_positive_event_gap_seconds",
    "half_hour_event_counts","half_hour_bucket_count","half_hour_bucket_seconds",
    "mean_event_weighted_spread_x10000","mean_event_weighted_top_depth_shares",
    "mean_event_weighted_top_imbalance","mean_event_weighted_top_two_level_depth_shares",
    "valid_two_sided_quote_events","one_sided_or_missing_quote_events",
    "crossed_or_locked_event_states","top_bid_ask_price_change_after_event",
    "top_bid_ask_size_change_after_event","both_quote_price_and_size_change_after_event",
    "visible_execution_prepost_quote_price_change",
    "nonexecution_prepost_quote_price_change",
    "same_timestamp_prepost_quote_price_change",
    "number_of_events_without_prior_snapshot_for_prepost_comparison",
    "raw_event_rows_exported","source_order_reference_ids_exported",
    "event_timestamp_or_price_series_exported","individual_agent_labels_available",
    "real_market_robot_accuracy_or_FDR_calibrated","commercial_trade_or_signal_authorized",
    "not_complete_market_depth","post_event_snapshot_semantics",
    "same_timestamp_order_of_events_preserved",
    "post_event_clock_weighted_bbo","limitations"
))


def _safe_mean(total: float | int, count: int) -> float | None:
    if not count:
        return None
    return round(float(total)/count,8)


def event_time_features(raw: bytes, *, require_original_sha: bool = False) -> dict:
    """Compute only bounded aggregates from one paired archived demo sample.

    The output does not expose order references or event-level features.
    The preceding observed *post-event* snapshot is an operational proxy
    for the next event's pre-state; it is not a true execution causal effect.
    """
    if type(require_original_sha) is not bool:
        raise ValueError("Source authentication option must be strict bool")
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_ZIP_BYTES:
        raise ValueError("Invalid vendor source byte size")
    local_sha = sha256(raw).hexdigest()
    if require_original_sha and local_sha != LOCALLY_PINNED_SAMPLE_SHA256:
        raise ValueError("Demo ZIP does not match previously observed LOCAL SHA256")
    qa = audit_sample_zip(raw)  # checks row alignment, 10 levels, ordering, source zip caps
    if not is_zipfile(io.BytesIO(raw)):
        raise ValueError("Source ZIP invalid")
    counts = Counter()
    half_hours = [0] * HALF_HOUR_BUCKETS
    prior_time = None
    prior_book = None
    weighted_clock = DurationWeightedBBO()
    n = distinct_times = max_tied = same_time = gap_pos = gap_zero = 0
    cluster_size = 0
    max_gap = Decimal(0)
    crossed = incomplete = valid_quotes = 0
    total_spread = total_depth = total_two_depth = 0
    imbalance_sum = 0.
    quote_change = depth_change = both_change = 0
    visible_with_quote_change = other_with_quote_change = 0
    tied_with_quote_change = 0
    aggressive_buy = aggressive_sell = hidden_exec = 0
    no_pre_state = 0

    with ZipFile(io.BytesIO(raw)) as z:
        members = _members(z)
        with z.open(members["messages"]) as me, z.open(members["books"]) as bo:
            msgs = csv.reader(io.TextIOWrapper(me, encoding="utf-8-sig", newline=""))
            books = csv.reader(io.TextIOWrapper(bo, encoding="utf-8-sig", newline=""))
            for msg, book in zip_longest(msgs, books):
                if msg is None or book is None:
                    raise ValueError("Paired market event/book rows changed")
                n += 1
                if n > MAX_ROWS:
                    raise ValueError("Unbounded sample events")
                stamp, event_type, shares, resting_side = _validate_message(
                    msg, prior_time
                )
                ask, bid, empty, invalid, top_depth = _validate_book(book)
                weighted_clock.observe_post_event(
                    stamp, ask, bid, int(book[1]), int(book[3])
                )
                counts[event_type] += 1
                if event_type == 4:
                    if resting_side == -1:
                        aggressive_buy += 1
                    else:
                        aggressive_sell += 1
                elif event_type == 5:
                    hidden_exec += 1

                slot = min(int((stamp - SESSION_START) // HALF_HOUR_SECONDS),
                           HALF_HOUR_BUCKETS - 1)
                if not 0 <= slot < HALF_HOUR_BUCKETS:
                    raise ValueError("Event timestamp outside exact session buckets")
                half_hours[slot] += 1
                tied = prior_time is not None and stamp == prior_time
                if prior_time is None or stamp > prior_time:
                    if cluster_size:
                        max_tied = max(max_tied, cluster_size)
                    cluster_size = 1
                    distinct_times += 1
                    if prior_time is not None:
                        gap_pos += 1
                        max_gap = max(max_gap, stamp - prior_time)
                else:
                    gap_zero += 1
                    same_time += 1
                    cluster_size += 1

                if invalid:
                    crossed += 1
                if ask is None or bid is None:
                    incomplete += 1
                else:
                    valid_quotes += 1
                    total_spread += ask - bid
                    total_depth += top_depth
                    top_bid_size = int(book[3])
                    top_ask_size = int(book[1])
                    if top_bid_size + top_ask_size > 0:
                        imbalance_sum += (
                            (top_bid_size - top_ask_size) /
                            (top_bid_size + top_ask_size)
                        )
                    total_two_depth += (
                        top_depth + int(book[5]) + int(book[7])
                    )

                # Book row is the state AFTER its corresponding message.
                current_book = (ask, bid, int(book[1]), int(book[3]))
                if prior_book is None:
                    no_pre_state += 1
                else:
                    moved_price = current_book[:2] != prior_book[:2]
                    moved_size = current_book[2:] != prior_book[2:]
                    if moved_price:
                        quote_change += 1
                        if event_type == 4:
                            visible_with_quote_change += 1
                        else:
                            other_with_quote_change += 1
                        if tied:
                            tied_with_quote_change += 1
                    if moved_size:
                        depth_change += 1
                    if moved_price and moved_size:
                        both_change += 1
                prior_time = stamp
                prior_book = current_book
    max_tied = max(max_tied, cluster_size)
    if (n != qa["paired_event_and_book_rows"] or sum(counts.values()) != n
            or sum(half_hours) != n or gap_pos + gap_zero != n - 1
            or distinct_times + same_time != n
            or aggressive_buy + aggressive_sell != counts[4]
            or hidden_exec != counts[5] or valid_quotes + incomplete != n
            or quote_change != visible_with_quote_change + other_with_quote_change
            or no_pre_state != 1):
        raise AssertionError("Event-time research metrics fail source conservation")
    result = {
        "schema_version": "lobster-event-time-10level-descriptive-replay-v1",
        "source_url": SOURCE_URL,
        "sample_symbol": "AMZN",
        "sample_date": "2012-06-21",
        "locally_observed_source_zip_sha256": local_sha,
        "original_locally_pinned_sha256_matched":
            local_sha == LOCALLY_PINNED_SAMPLE_SHA256,
        "provider_signed_checksum_available": False,
        "event_count": n,
        "paired_l2_post_event_states": n,
        "event_type_counts": {str(i): counts[i] for i in range(1,8)},
        "visible_aggressor_buy_executions": aggressive_buy,
        "visible_aggressor_sell_executions": aggressive_sell,
        "hidden_executions_resting_side_not_aggressor": hidden_exec,
        "distinct_event_timestamp_groups": distinct_times,
        "same_timestamp_repeated_event_pairs": same_time,
        "max_events_in_one_exact_timestamp_group": max_tied,
        "event_time_gap_zero": gap_zero,
        "event_time_gap_positive": gap_pos,
        "max_positive_event_gap_seconds": str(max_gap),
        "half_hour_event_counts": half_hours,
        "half_hour_bucket_count": HALF_HOUR_BUCKETS,
        "half_hour_bucket_seconds": HALF_HOUR_SECONDS,
        "mean_event_weighted_spread_x10000": _safe_mean(total_spread,valid_quotes),
        "mean_event_weighted_top_depth_shares": _safe_mean(total_depth,valid_quotes),
        "mean_event_weighted_top_imbalance": _safe_mean(imbalance_sum,valid_quotes),
        "mean_event_weighted_top_two_level_depth_shares":
            _safe_mean(total_two_depth,valid_quotes),
        "valid_two_sided_quote_events": valid_quotes,
        "one_sided_or_missing_quote_events": incomplete,
        "crossed_or_locked_event_states": crossed,
        "top_bid_ask_price_change_after_event": quote_change,
        "top_bid_ask_size_change_after_event": depth_change,
        "both_quote_price_and_size_change_after_event": both_change,
        "visible_execution_prepost_quote_price_change": visible_with_quote_change,
        "nonexecution_prepost_quote_price_change": other_with_quote_change,
        "same_timestamp_prepost_quote_price_change": tied_with_quote_change,
        "number_of_events_without_prior_snapshot_for_prepost_comparison": no_pre_state,
        "raw_event_rows_exported": False,
        "source_order_reference_ids_exported": False,
        "event_timestamp_or_price_series_exported": False,
        "individual_agent_labels_available": False,
        "real_market_robot_accuracy_or_FDR_calibrated": False,
        "commercial_trade_or_signal_authorized": False,
        "not_complete_market_depth": True,
        "post_event_snapshot_semantics": True,
        "same_timestamp_order_of_events_preserved": True,
        "post_event_clock_weighted_bbo": weighted_clock.summary(),
        "limitations": [
            "Original sample is historical AMZN 2012 NASDAQ; not present-day or a labelled bot dataset.",
            "Primary source metrics are event-weighted; a separate nested right-continuous duration-weighted BBO estimate is supplied.",
            "Clock-weighted quotes use last post-event BBO until next event, excluding pre-first and post-last intervals.",
            "Large interevent gaps are carried forward by convention and flagged as potential stale-quote uncertainty.",
            "Previous post-event quote is a pre-state proxy, not a proven causal counterfactual.",
            "Event type 4 indicates passive order side; aggressive trade side is opposite.",
            "Hidden type-5 execution direction is not counted as observed aggressive side.",
            "Tied timestamps are grouped; intra-timestamp ordering may be vendor-specific.",
            "Ten occupied price levels per side are not complete market-by-order depth.",
            "Source SHA256 was locally observed, not published/signed by provider.",
            "No p-value, bot actor identification, true market FDR or trading rights are established.",
        ],
    }
    if set(result) != OUTPUT_ALLOWED_TOP_FIELDS:
        raise AssertionError("Research summary exposed or lost an output contract field")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Refuse to overwrite previous real scientific observations")
    raw = download_exact_demo()
    summary = event_time_features(raw, require_original_sha=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, sort_keys=True, allow_nan=False)
        f.write("\n")
    print("LOBSTER_EVENT_TIME_PUBLIC_L2_RESEARCH",json.dumps({
        "pairs":summary["event_count"],
        "original_local_sha_matched":summary[
            "original_locally_pinned_sha256_matched"],
        "price_changes":summary["top_bid_ask_price_change_after_event"],
        "count_not_real_robot_FDR":True,
        "raw_events_exported":False
    },sort_keys=True))


if __name__ == "__main__":
    main()
