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
OCCUPANCY_CLASSES = ("1", "2", "3-4", "5-9", "10+")


def occupancy_class(public_prints: int) -> str:
    """Precommitted mutually exclusive 30-second public-print-count bins."""
    if type(public_prints) is not int or public_prints < 1:
        raise ValueError("Occupancy only defined for nonempty public print bins")
    if public_prints == 1:
        return "1"
    if public_prints == 2:
        return "2"
    if public_prints <= 4:
        return "3-4"
    if public_prints <= 9:
        return "5-9"
    return "10+"



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
    per_phase = []
    for i, phase in enumerate(PHASES_SECONDS):
        occupancy = {k: {"eligible_bins": 0, "one_sided_bins": 0}
                     for k in OCCUPANCY_CLASSES}
        for buy, sell in bins[i].values():
            key = occupancy_class(buy + sell)
            occupancy[key]["eligible_bins"] += 1
            occupancy[key]["one_sided_bins"] += int(buy == 0 or sell == 0)
        if occupancy["1"]["eligible_bins"] != occupancy["1"]["one_sided_bins"]:
            raise AssertionError("One-trade bin must be mechanically one-sided")
        per_phase.append({
            "origin_seconds": phase,
            "complete_nonempty_bins": len(bins[i]),
            "one_sided_bins": sum(0 in pair for pair in bins[i].values()),
            "buy_dominant_bins": sum(pair[0] > pair[1] for pair in bins[i].values()),
            "sell_dominant_bins": sum(pair[0] < pair[1] for pair in bins[i].values()),
            "tied_print_count_bins": sum(pair[0] == pair[1] for pair in bins[i].values()),
            "included_public_prints": sum(sum(pair) for pair in bins[i].values()),
            "occupancy_strata": occupancy,
        })
    return per_phase


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
    controls_ge5 = [[] for _ in PHASES_SECONDS]
    occupancy_controls = [{key: [] for key in OCCUPANCY_CLASSES}
                          for _ in PHASES_SECONDS]
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
            for key in OCCUPANCY_CLASSES:
                original = observed[i]["occupancy_strata"][key]
                randomized = row["occupancy_strata"][key]
                if original["eligible_bins"] != randomized["eligible_bins"]:
                    raise AssertionError("Bin print occupancy moved under side shuffle")
                occupancy_controls[i][key].append(randomized["one_sided_bins"])
            controls_ge5[i].append(
                row["occupancy_strata"]["5-9"]["one_sided_bins"]+
                row["occupancy_strata"]["10+"]["one_sided_bins"]
            )

    variants = []
    for i, phase in enumerate(PHASES_SECONDS):
        row = observed[i]
        if (row["buy_dominant_bins"] + row["sell_dominant_bins"]
                + row["tied_print_count_bins"] != row["complete_nonempty_bins"]):
            raise AssertionError("Observed direction bins do not reconcile")
        full_count = (DAY_US - phase * 1_000_000)//BIN_US
        nulls = controls[i]
        strata = []
        for key in OCCUPANCY_CLASSES:
            observed_group = row["occupancy_strata"][key]
            shuffled = occupancy_controls[i][key]
            strata.append({
                "class": key,
                "eligible_complete_bins": observed_group["eligible_bins"],
                "observed_one_sided_bins": observed_group["one_sided_bins"],
                "null_one_sided_min": min(shuffled),
                "null_one_sided_median": median(shuffled),
                "null_one_sided_max": max(shuffled),
                "above_all_eight_controls": observed_group["one_sided_bins"]>max(shuffled),
            })
        if (sum(x["eligible_complete_bins"] for x in strata)
                != row["complete_nonempty_bins"]
                or sum(x["observed_one_sided_bins"] for x in strata)
                != row["one_sided_bins"]):
            raise AssertionError("Occupancy partition lost source public prints")
        qualifying = sum(x["eligible_complete_bins"] for x in strata[3:])
        one_sided_ge5 = sum(x["observed_one_sided_bins"] for x in strata[3:])
        strong_controls_ge5 = controls_ge5[i]
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
            "occupancy_classes_predeclared": list(OCCUPANCY_CLASSES),
            "one_sided_bins_by_public_print_occupancy": strata,
            "qualifying_bins_with_at_least_five_prints": qualifying,
            "one_sided_bins_with_at_least_five_prints": one_sided_ge5,
            "null_ge5_one_sided_min": min(strong_controls_ge5),
            "null_ge5_one_sided_median": median(strong_controls_ge5),
            "null_ge5_one_sided_max": max(strong_controls_ge5),
            "observed_ge5_one_sided_above_all_eight_nulls": (
                one_sided_ge5 > max(strong_controls_ge5)
            ),
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
        "bin_occupancy_classes": list(OCCUPANCY_CLASSES),
        "primary_conditioned_bin_occupancy_minimum": 5,
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
            "Every exactly-one-trade bin is mechanically 100% one-sided, regardless of any actor or exchange behavior.",
            "Five-print-minimum conditioning is precommitted ONLY for separately frozen unseen source dates, not retroactive proof for inspected development days.",
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
