#!/usr/bin/env python3
"""Public-only *previous completed bin* L2 book vs next-bin prints.

All features at time bin t are taken from the COMPLETED bin t-1. This avoids
the same-timestamp L2/fill ordering impossibility shown by the exact-time
ABIDES audit. The output is descriptive, NOT a VWAP/POV detector or an
inference about individual owners or causal order placement.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable
import math

from l2_probe import audit_l2_public
from l2_trade_context import PublicExecution, MAX_FILLS, MAX_SNAPSHOTS


@dataclass(frozen=True, slots=True)
class LaggedBinRecord:
    current_bin_ordinal: int
    previous_bin_end_ns: int
    previous_last_l2_time_ns: int
    previous_book_bid_lots: int
    previous_book_ask_lots: int
    previous_book_imbalance: float
    current_buy_lots: int
    current_sell_lots: int
    current_prints: int

    @property
    def current_buy_share(self) -> float:
        return self.current_buy_lots / (self.current_buy_lots + self.current_sell_lots)


def _average_ranks(v: list[float]) -> list[float]:
    ordered = sorted(range(len(v)), key=lambda i: (v[i], i))
    ranks = [0.0] * len(v)
    k = 0
    while k < len(v):
        j = k + 1
        while j < len(v) and v[ordered[j]] == v[ordered[k]]:
            j += 1
        mid = ((k + 1) + j) / 2.0
        for n in range(k, j):
            ranks[ordered[n]] = mid
        k = j
    return ranks


def _spearman(x: list[float], y: list[float]) -> float | None:
    if len(x) < 5 or len(x) != len(y):
        return None
    a, b = _average_ranks(x), _average_ranks(y)
    center = (len(x) + 1) / 2.0
    u, v = [p - center for p in a], [p - center for p in b]
    xx, yy = sum(p * p for p in u), sum(p * p for p in v)
    if xx == 0 or yy == 0:
        return None
    return max(-1.0, min(1.0, sum(p * q for p, q in zip(u, v)) / math.sqrt(xx * yy)))


def summarize_lagged_book(
    snapshots: Any,
    public_executions: Iterable[PublicExecution],
    *, bin_seconds: int = 30,
    maximum_quote_age_seconds: int = 30,
    maximum_depth: int = 5
) -> dict:
    if (bin_seconds < 1 or bin_seconds > 3600 or
        maximum_quote_age_seconds < 1 or
        maximum_quote_age_seconds > bin_seconds or
        maximum_depth < 1 or maximum_depth > 20):
        raise ValueError("Invalid bounded previous-completed-bin settings")
    if snapshots is None or len(snapshots.times_ns) > MAX_SNAPSHOTS:
        raise ValueError("Missing or excessive L2 snapshots")
    source = audit_l2_public(snapshots, max_depth=maximum_depth)
    executions = tuple(public_executions)
    if len(executions) > MAX_FILLS:
        raise ValueError("Excessive public executed prints")
    duration = bin_seconds * 1_000_000_000

    # L2 quote event order is preserved; equal timestamps are NOT deduplicated.
    # However, all quote observations from bin t-1 precede ALL prints in t
    # regardless of unknown intra-timestamp order.
    last_prior_by_bin = {}
    for idx, time_ns in enumerate(snapshots.times_ns):
        ordinal = int(time_ns) // duration
        last_prior_by_bin[ordinal] = idx

    fills_by_bin: dict[int, dict] = {}
    for fill in executions:
        if (fill.time_ns < 0 or fill.price_cents <= 0 or fill.quantity <= 0 or
            fill.reported_aggressor_side not in ("BUY", "SELL")):
            raise ValueError("Invalid public execution fields")
        ordinal = fill.time_ns // duration
        counts = fills_by_bin.setdefault(ordinal, {
            "buy": 0, "sell": 0, "count": 0
        })
        side = "buy" if fill.reported_aggressor_side == "BUY" else "sell"
        counts[side] += fill.quantity
        counts["count"] += 1

    abstain = Counter()
    observations: list[LaggedBinRecord] = []
    for ordinal, trade_bin in sorted(fills_by_bin.items()):
        prev_idx = last_prior_by_bin.get(ordinal - 1)
        if prev_idx is None:
            abstain["missing_immediately_previous_book_bin"] += 1
            continue
        previous_time = int(snapshots.times_ns[prev_idx])
        current_start = ordinal * duration
        age = current_start - previous_time
        if not (0 < age <= maximum_quote_age_seconds * 1_000_000_000):
            abstain["prior_quote_too_old"] += 1
            continue
        bids = snapshots.bids[prev_idx]
        asks = snapshots.asks[prev_idx]
        if not bids or not asks:
            abstain["one_sided_or_empty_prior_book"] += 1
            continue
        if int(bids[0][0]) >= int(asks[0][0]):
            abstain["locked_or_crossed_prior_book"] += 1
            continue
        bid_qty = sum(int(qty) for _, qty in bids)
        ask_qty = sum(int(qty) for _, qty in asks)
        if bid_qty <= 0 or ask_qty <= 0:
            raise ValueError("Invalid previous book quote quantity")
        observations.append(LaggedBinRecord(
            current_bin_ordinal=ordinal,
            previous_bin_end_ns=current_start,
            previous_last_l2_time_ns=previous_time,
            previous_book_bid_lots=bid_qty,
            previous_book_ask_lots=ask_qty,
            previous_book_imbalance=(bid_qty - ask_qty) / (bid_qty + ask_qty),
            current_buy_lots=trade_bin["buy"],
            current_sell_lots=trade_bin["sell"],
            current_prints=trade_bin["count"],
        ))

    x = [o.previous_book_imbalance for o in observations]
    y = [o.current_buy_share for o in observations]
    k = len(observations)
    # Rotate next-bin public outcomes, preserving the original set of
    # (BUY,SELL) aggregate pairs, but deliberately breaking alignment with
    # previous book states. NOT a realistic conditional market null.
    p = max(1, k // 2)
    placebo_y = y[p:] + y[:p] if k > 1 else y
    observed = _spearman(x, y)
    placebo = _spearman(x, placebo_y)
    if sum(o.current_prints for o in observations) > len(executions):
        raise AssertionError("Selected public fills exceed raw feed")
    if k + sum(abstain.values()) != len(fills_by_bin):
        raise AssertionError("Populated current-bin conservation failure")

    return {
        "schema_version": "abides-public-lagged-book-bin-v1",
        "bin_seconds": bin_seconds,
        "source_l2_snapshot_count": source["l2_snapshot_events"],
        "source_same_time_l2_updates_retained":
            source["same_timestamp_repeated_snapshots"],
        "public_execution_prints": len(executions),
        "public_execution_lots": sum(t.quantity for t in executions),
        "populated_execution_clock_bins": len(fills_by_bin),
        "eligible_lagged_bins": k,
        "abstained_clock_bins": {name: int(abstain[name]) for name in (
            "missing_immediately_previous_book_bin",
            "prior_quote_too_old",
            "one_sided_or_empty_prior_book",
            "locked_or_crossed_prior_book"
        )},
        "observations": [
            {
                "current_bin_ordinal": o.current_bin_ordinal,
                "previous_last_l2_time_ns": o.previous_last_l2_time_ns,
                "previous_quote_age_at_current_bin_open_ns":
                    o.previous_bin_end_ns - o.previous_last_l2_time_ns,
                "previous_book_bid_lots": o.previous_book_bid_lots,
                "previous_book_ask_lots": o.previous_book_ask_lots,
                "previous_book_imbalance": o.previous_book_imbalance,
                "current_buy_lots": o.current_buy_lots,
                "current_sell_lots": o.current_sell_lots,
                "current_prints": o.current_prints,
                "current_reported_buy_share": o.current_buy_share,
            } for o in observations
        ],
        "descriptive_lagged_imbalance_to_next_buy_share_spearman": observed,
        "rotated_next_bin_share_placebo_spearman": placebo,
        "at_least_five_eligible_bins": k >= 5,
        "previous_completed_bin_only": True,
        "private_agent_identifiers_used": False,
        "individual_robot_detected": False,
        "real_market_significance_calibrated": False,
        "real_l2_feed_coverage_proven": False,
        "limitations": [
            "Lagged bin feature is available only after the preceding bin closes; "
            "current buy share is an ex-post outcome, never a future prediction.",
            "Markets with many participants can show the same correlation.",
            "Rotated-bin placebo is NOT a market-preserving conditional null.",
            "ABIDES source book sequence is not proof of real broker L2 ordering.",
            "A low/high correlation does not identify execution parent orders or bots."
        ]
    }
