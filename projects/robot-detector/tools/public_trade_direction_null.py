#!/usr/bin/env python3
"""Weak within-minute public side-permutation controls for observed trade times.

In-sample, descriptive-only. This intentionally does NOT preserve all
timestamp-cluster, queue or same-parent fill dependence. It cannot
calibrate a bot false-alarm rate or justify use for real trading.
"""
from __future__ import annotations

from random import Random
from statistics import median

PHASES_SECONDS = (0, 10, 20)
BIN_US = 30_000_000
MINUTE_US = 60_000_000
DAY_US = 86_400_000_000
NULL_SEEDS = (32001, 32003, 32009, 32027, 32029, 32051, 32057, 32063)
MAX_PRINTS = 3_000_000


def _stats(slots: list[list[int]], sides: list[bool]) -> list[dict]:
    # Keep only the three dictionaries; every slot corresponds to one
    # *completely contained* 30s UTC-day interval.
    bins = [{ } for _ in PHASES_SECONDS]
    for membership, buyer_maker in zip(slots, sides):
        for i, bucket in enumerate(membership):
            if bucket < 0:
                continue
            pair = bins[i].setdefault(bucket, [0, 0])
            pair[int(buyer_maker)] += 1
    return [
        {
            "origin_seconds": phase,
            "complete_nonempty_bins": len(bins[i]),
            "one_sided_bins": sum(0 in pair for pair in bins[i].values()),
            "buy_dominant_bins": sum(pair[0] > pair[1] for pair in bins[i].values()),
            "sell_dominant_bins": sum(pair[0] < pair[1] for pair in bins[i].values()),
            "tied_print_count_bins": sum(pair[0] == pair[1] for pair in bins[i].values()),
            "included_public_prints": sum(sum(pair) for pair in bins[i].values()),
        }
        for i, phase in enumerate(PHASES_SECONDS)
    ]


def evaluate_public_side_null(
    observations: list[tuple[int, bool]], *, utc_day_start_us: int,
    preserve_same_timestamp_clusters: bool = False
) -> dict:
    """Evaluate exactly eight fixed shuffles on identical anonymous timestamps.

    `observations`: monotonically ordered (absolute exchange timestamp
    microseconds, Binance isBuyerMaker boolean). No IDs/quantities leave
    the calling source validator. Each 60s UTC minute preserves its exact
    BUY/SELL counts and all timestamp positions. A 30s bin that touches
    either UTC-day boundary is excluded in its entirety.
    """
    if type(utc_day_start_us) is not int or utc_day_start_us < 0:
        raise ValueError("Expected integer UTC-day microsecond origin")
    if type(preserve_same_timestamp_clusters) is not bool:
        raise ValueError("Null unit selection must be a strict boolean")
    if type(observations) is not list or not 0 < len(observations) <= MAX_PRINTS:
        raise ValueError("Expected bounded public trade observations")
    slots = []
    sides = []
    minute_groups = []
    start_index = 0
    previous_time = None
    current_minute = None
    for i, row in enumerate(observations):
        if (type(row) is not tuple or len(row) != 2
                or type(row[0]) is not int or type(row[1]) is not bool):
            raise ValueError("Expected exact anonymous (int microseconds, bool side)")
        ts, buyer_maker = row
        offset = ts - utc_day_start_us
        if not 0 <= offset < DAY_US or (
            previous_time is not None and ts < previous_time
        ):
            raise ValueError("Malformed UTC source tape or reversed timestamp")
        previous_time = ts
        minute = offset // MINUTE_US
        if current_minute is not None and minute != current_minute:
            minute_groups.append((start_index, i))
            start_index = i
        current_minute = minute
        sides.append(buyer_maker)
        membership = []
        for phase in PHASES_SECONDS:
            phase_origin = phase * 1_000_000
            full_bins = (DAY_US - phase_origin) // BIN_US
            end = phase_origin + full_bins * BIN_US
            membership.append(
                (offset - phase_origin) // BIN_US
                if phase_origin <= offset < end else -1
            )
        slots.append(membership)
    minute_groups.append((start_index, len(sides)))

    observed = _stats(slots, sides)
    controls = [[] for _ in PHASES_SECONDS]
    for seed in NULL_SEEDS:
        shuffled = sides.copy()
        rng = Random(seed)
        if preserve_same_timestamp_clusters:
            # Shuffle entire SAME-SIZE timestamp blocks, never individual
            # fills. This preserves event timestamps, exact multiplicity,
            # equal-time side vectors and full per-minute BUY/SELL totals.
            for lo, hi in minute_groups:
                by_length = {}
                begin = lo
                for index in range(lo + 1, hi + 1):
                    if (index == hi or
                            observations[index][0] != observations[begin][0]):
                        by_length.setdefault(index-begin, []).append((begin,index))
                        begin = index
                for ranges in by_length.values():
                    patterns = [shuffled[left:right] for left,right in ranges]
                    rng.shuffle(patterns)
                    for (left,right), pattern in zip(ranges,patterns):
                        shuffled[left:right] = pattern
        else:
            for lo, hi in minute_groups:
                group = shuffled[lo:hi]
                rng.shuffle(group)
                shuffled[lo:hi] = group
        shuffled_stats = _stats(slots, shuffled)
        for i, row in enumerate(shuffled_stats):
            if (row["included_public_prints"] != observed[i]["included_public_prints"]
                    or row["complete_nonempty_bins"] !=
                    observed[i]["complete_nonempty_bins"]):
                raise AssertionError("Fixed timestamp permutation changed source coverage")
            controls[i].append(row["one_sided_bins"])

    variants = []
    for i, phase in enumerate(PHASES_SECONDS):
        row = observed[i]
        if (row["buy_dominant_bins"] + row["sell_dominant_bins"]
                + row["tied_print_count_bins"] != row["complete_nonempty_bins"]):
            raise AssertionError("Observed direction bins do not reconcile")
        full_count = (DAY_US - phase * 1_000_000)//BIN_US
        nulls = controls[i]
        variants.append({
            "origin_seconds": phase,
            "bin_width_seconds": 30,
            "observed_complete_nonempty_bins": row["complete_nonempty_bins"],
            "observed_one_sided_bins": row["one_sided_bins"],
            "observed_buy_dominant_bins": row["buy_dominant_bins"],
            "observed_sell_dominant_bins": row["sell_dominant_bins"],
            "observed_tied_print_count_bins": row["tied_print_count_bins"],
            "observed_prints_in_full_bins": row["included_public_prints"],
            "excluded_utc_edge_prints": len(sides)-row["included_public_prints"],
            "complete_utc_clock_bins": full_count,
            "null_one_sided_bin_count_min": min(nulls),
            "null_one_sided_bin_count_median": median(nulls),
            "null_one_sided_bin_count_max": max(nulls),
            "num_predeclared_weak_null_replicates": len(nulls),
            "predeclared_null_seeds": list(NULL_SEEDS),
            "source_archive_independence_claimed": False,
            "statistical_p_value_or_FDR_calibrated": False,
        })

    return {
        "schema_version": (
            "public-real-spot-within-minute-cluster-shuffle-v1"
            if preserve_same_timestamp_clusters else
            "public-real-spot-within-minute-side-shuffle-v1"
        ),
        "source_event_count": len(observations),
        "independent_market_days_in_this_report": 1,
        "same_public_tape_reused_in_phase_and_null_analyses": True,
        "clock_phases_seconds": list(PHASES_SECONDS),
        "null_type": (
            "same_size_same_timestamp_side_vector_cluster_shuffle_within_utc_minute"
            if preserve_same_timestamp_clusters else
            "within_utc_minute_side_shuffle_exact_timestamp_positions"
        ),
        "preserved": [
            "all_public_trade_timestamps_us",
            "original_timestamp_order_including_ties",
            "exact_buy_sell_counts_per_source_utc_minute",
            "original_source_event_count",
        ] + (["same_timestamp_cluster_size_and_joint_side_vector"]
              if preserve_same_timestamp_clusters else []),
        "not_preserved": (
            [] if preserve_same_timestamp_clusters else
            ["same_timestamp_execution_side_clusters"]
        ) + [
            "cross_timestamp_execution_order_dependence",
            "cross_minute_trade_side_dependence",
            "order_book_and_market_queue_effects",
            "true_parent_order_or_participant_labels",
        ],
        "variants": variants,
        "same_timestamp_side_vector_clusters_preserved": (
            preserve_same_timestamp_clusters
        ),
        "source_real_market_completeness_independently_verified": False,
        "physical_robot_identification_validated": False,
        "market_false_discovery_rate_calibrated": False,
        "optimal_phase_selected": False,
        "commercial_or_live_trading_allowed": False,
        "raw_print_timestamps_or_labels_exported": False,
        "limitations": [
            "Eight fixed shuffles per UTC day are descriptive controls, not an inferential null distribution.",
            ("Whole timestamp clusters are shuffled only across equal-size groups; "
             "unmodelled order queues and within-minute timing relations remain."
             if preserve_same_timestamp_clusters else
             "Shuffling per execution may destroy same-time partial-fill side dependencies."),
            "Data are already inspected development samples, never a fresh robot-detector holdout.",
            "Within-minute side balance does not model Hawkes clustering or exchange order queues.",
            "No L2 snapshots or individual physical-owner attribution are present.",
            "Real source terms permit only non-commercial research without separate licensing.",
        ],
    }
