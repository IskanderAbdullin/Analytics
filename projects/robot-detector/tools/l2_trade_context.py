#!/usr/bin/env python3
"""Strictly public, lagged ABIDES L2/trade context audit.

No actor identities, model fitting, order reconstruction or trading API.
An execution at the exact timestamp of any L2 mutation is deliberately
unclassified: nanosecond timestamps do not establish intra-time ordering.
This is an observed quote/print compatibility audit, NOT a bot detector.
"""
from __future__ import annotations

import argparse
from bisect import bisect_left
from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable

from abides_export import UPSTREAM_COMMIT
from l2_probe import audit_l2_public

MAX_SNAPSHOTS = 250_000
MAX_FILLS = 200_000
MODES = ("null", "pov", "vwap")


@dataclass(frozen=True, slots=True)
class PublicExecution:
    time_ns: int
    price_cents: int
    quantity: int
    reported_aggressor_side: str


def public_projection(raw_fills: Iterable[Any]) -> tuple[PublicExecution, ...]:
    """Drop ABIDES maker/taker agent IDs before any context computation."""
    result: list[PublicExecution] = []
    for trade in raw_fills:
        # TradeAttribution.side is the PASSIVE order side in ABIDES.
        # Only its public inverse is exposed; no agent IDs are accessed.
        passive = str(trade.side).upper()
        if passive not in ("BUY", "SELL"):
            raise ValueError("ABIDES side convention unknown")
        result.append(PublicExecution(
            int(trade.time_ns), int(trade.price_cents), int(trade.quantity),
            "SELL" if passive == "BUY" else "BUY"))
        if len(result) > MAX_FILLS:
            raise ValueError("Excessive public fill count")
    return tuple(result)


def rotated_public_prints(trades: tuple[PublicExecution, ...]) -> tuple[PublicExecution, ...]:
    """Descriptive placebo: rotate entire public (side,price,qty) tuples.

    Preserves exact event times, sides, prices, quantities and total lots,
    but breaks contemporaneous price/side alignment with the book.
    NOT a valid market conditional-null model or a calibrated p-value.
    """
    if len(trades) < 2:
        return trades
    payloads = [(p.price_cents, p.quantity, p.reported_aggressor_side)
                for p in trades]
    k = max(1, len(trades) // 2)
    shifted = payloads[k:] + payloads[:k]
    return tuple(PublicExecution(old.time_ns, price, qty, side)
                 for old, (price, qty, side) in zip(trades, shifted))


def audit_public_join(snapshots: Any,
                      trades: Iterable[PublicExecution],
                      *, max_depth: int = 5,
                      max_age_ns: int = 2_000_000_000) -> dict[str, Any]:
    """Find the latest strictly PRECEDING public L2 snapshot for each fill.

    Trades at any snapshot's exact timestamp are abstentions, never assigned
    a within-timestamp order. No future snapshot can affect an earlier fill.
    """
    if not 0 < max_age_ns <= 60_000_000_000:
        raise ValueError("Maximum quote age must be 1 ns to 60 s")
    if snapshots is None or len(snapshots.times_ns) > MAX_SNAPSHOTS:
        raise ValueError("Missing or oversized public quote tape")
    quote_quality = audit_l2_public(snapshots, max_depth=max_depth)
    times = tuple(int(x) for x in snapshots.times_ns)
    equal_times = set(times)
    public_trades = list(trades)
    if len(public_trades) > MAX_FILLS:
        raise ValueError("Excessive public fill count")
    for fill in public_trades:
        if (fill.time_ns < 0 or fill.price_cents <= 0 or
            fill.quantity <= 0 or
            fill.reported_aggressor_side not in ("BUY", "SELL")):
            raise ValueError("Invalid anonymous public fill")
    counts = Counter()
    lots = Counter()
    for fill in public_trades:
        if fill.time_ns in equal_times:
            label = "same_timestamp_ambiguous"
        else:
            previous = bisect_left(times, fill.time_ns) - 1
            if previous < 0:
                label = "no_prior_quote"
            elif fill.time_ns - times[previous] > max_age_ns:
                label = "stale_quote"
            else:
                bid = snapshots.bids[previous]
                ask = snapshots.asks[previous]
                if not bid or not ask:
                    label = "one_sided_or_empty_quote"
                elif int(bid[0][0]) >= int(ask[0][0]):
                    label = "crossed_or_locked_quote"
                elif (
                    fill.reported_aggressor_side == "BUY"
                    and fill.price_cents >= int(ask[0][0])
                ) or (
                    fill.reported_aggressor_side == "SELL"
                    and fill.price_cents <= int(bid[0][0])
                ):
                    label = "at_or_through_prior_opposite_best"
                else:
                    label = "not_at_prior_opposite_best"
        counts[label] += 1
        lots[label] += fill.quantity

    required = (
        "same_timestamp_ambiguous", "no_prior_quote", "stale_quote",
        "one_sided_or_empty_quote", "crossed_or_locked_quote",
        "at_or_through_prior_opposite_best", "not_at_prior_opposite_best"
    )
    counted = sum(counts.values())
    total_lots = sum(lots.values())
    if counted != len(public_trades) or total_lots != sum(x.quantity for x in public_trades):
        raise AssertionError("Public fill/lot conservation failed")
    eligible = (counts["at_or_through_prior_opposite_best"] +
                counts["not_at_prior_opposite_best"])
    return {
        "schema_version": "abides-public-l2-trade-join-v1",
        "public_fill_count": len(public_trades),
        "public_total_lots": total_lots,
        "l2_snapshot_count": quote_quality["l2_snapshot_events"],
        "same_timestamp_l2_updates_retained":
            quote_quality["same_timestamp_repeated_snapshots"],
        "maximum_quote_age_ns": max_age_ns,
        "join_rule": "strict_prior_snapshot_only_same_timestamp_abstains",
        "categories": {k: int(counts[k]) for k in required},
        "lots_by_category": {k: int(lots[k]) for k in required},
        "eligible_two_sided_fills": eligible,
        "descriptive_prior_quote_alignment_fraction":
            counts["at_or_through_prior_opposite_best"] / eligible
            if eligible else None,
        "physical_owner_identity_known": False,
        "statistical_significance_established": False,
        "broker_data_used": False,
        "order_placement_enabled": False,
        "interpretation": (
            "A contemporaneous public execution versus a strictly prior "
            "snapshot is a quote compatibility observation, not evidence "
            "of execution by any individual agent. Quotes can change "
            "between market events and observed feed receipt."
        )
    }


def simulate_public_context(seed: int = 1501, modes: tuple[str, ...] = MODES) -> dict:
    """Run actual ABIDES matching, stripping private attribution immediately."""
    from lagged_l2_bin import summarize_lagged_book
    from abides_markets.config_system import SimulationBuilder
    from abides_markets.config_system.agent_configs import (
        NoiseAgentConfig, POVExecutionAgentConfig, VWAPExecutionAgentConfig)
    from abides_markets.config_system.models import ExchangeConfig
    from abides_markets.simulation import ResultProfile, run_simulation

    if seed < 0 or not modes or len(set(modes)) != len(modes) or any(
        mode not in MODES for mode in modes
    ):
        raise ValueError("Use distinct known modes and nonnegative seed")
    cases = []
    for mode in modes:
        builder = (
            SimulationBuilder().apply_template("liquid_market")
            .ticker("ABM").start_time("09:30:00").end_time("09:40:00")
            .exchange(ExchangeConfig(book_capture="l2", book_log_depth=5))
            .enable_agent(NoiseAgentConfig(
                multi_wake=True, wake_up_freq="20s",
                noise_mkt_close_time="09:40:00"), count=40)
            .seed(seed)
        )
        execution_window = {
            "start_time_offset": "00:01:00",
            "end_time_offset": "00:01:00",
            "freq": "30s", "direction": "BID",
            "quantity": 1_200, "trade": True
        }
        if mode == "pov":
            builder = builder.enable_agent(
                POVExecutionAgentConfig(**execution_window, pov=0.25), count=1)
        elif mode == "vwap":
            builder = builder.enable_agent(
                VWAPExecutionAgentConfig(**execution_window, order_style="market"),
                count=1)
        result = run_simulation(
            builder.build(),
            profile=ResultProfile.L2_SERIES | ResultProfile.TRADE_ATTRIBUTION
                    | ResultProfile.SUMMARY)
        market = result.markets["ABM"]
        if market.trades is None or market.l2_series is None:
            raise RuntimeError("Actual ABIDES public fills and L2 unavailable")
        public = public_projection(market.trades)   # ONLY public field values survive.
        if not public:
            raise RuntimeError("No actual matching engine executions")
        natural = audit_public_join(market.l2_series, public)
        placebo = audit_public_join(
            market.l2_series, rotated_public_prints(public))
        # Unlike the within-timestamp as-of join, this evaluates the last
        # public L2 state of the strictly PREVIOUS COMPLETED clock bin.
        lagged = summarize_lagged_book(market.l2_series, public)
        if natural["public_fill_count"] != placebo["public_fill_count"] or (
            natural["public_total_lots"] != placebo["public_total_lots"]
        ):
            raise AssertionError("Placebo altered public market print/lot totals")
        cases.append({
            "mode": mode, "public_book": {
                "snapshot_events": natural["l2_snapshot_count"],
                "same_timestamp_updates":
                    natural["same_timestamp_l2_updates_retained"]
            },
            "natural": natural,
            "rotated_public_print_placebo": placebo,
            "lagged_previous_completed_book": lagged
        })
    return {
        "schema_version": "abides-public-l2-context-development-v1",
        "simulator_revision": UPSTREAM_COMMIT,
        "seed": seed,
        "cases": cases,
        "placebo_description": (
            "Rotates public executed side, price and quantity bundles across "
            "unchanged timestamps; only a sanity/sensitivity control, "
            "NOT a market-preserving conditional null."
        ),
        "private_execution_truth_used": False,
        "physical_owner_count_known": False,
        "market_false_discovery_rate_calibrated": False,
        "real_historical_l2_verified": False,
        "limitations": [
            "The simulator returned attribution with its fills, but only four "
            "anonymous scalar fields were projected; agent IDs were not accessed.",
            "ABIDES simulation, not an observed MOEX/SPB tape or live provider feed.",
            "Unknown same-time quote/execution ordering always abstains.",
            "Natural/rotated differences do not prove causation, "
            "significance or individual execution strategy.",
            "No validated parent-order IDs, real market FDR or trading signal.",
            "Previous completed 30-second book-bin imbalance is analyzed "
            "only against later whole-bin public prints, not individual IDs."
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=1501)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Refusing to overwrite prior L2 study")
    report = simulate_public_context(args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write("\n")
    for case in report["cases"]:
        print("L2_PUBLIC_JOIN_DEV", json.dumps({
            "mode": case["mode"],
            "book": case["public_book"],
            "natural": case["natural"]["categories"],
            "placebo": case["rotated_public_print_placebo"]["categories"],
            "real_market_calibrated": False
        }, sort_keys=True))


if __name__ == "__main__":
    main()
