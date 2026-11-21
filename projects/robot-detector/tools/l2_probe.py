#!/usr/bin/env python3
"""Read-only ABIDES-NG L2 availability and data-integrity probe.

Evaluates whether the pinned exchange simulation exposes timestamped public
best-to-worst L2 quote snapshots. Only aggregate counts leave the runner.
No private agent IDs, orders, account access or execution of real trades.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from abides_export import UPSTREAM_COMMIT
from public_numeric import exact_nonnegative_integer as exact_int


def audit_l2_public(snapshots: Any, *, max_depth: int) -> dict:
    max_depth = exact_int(max_depth, "max_depth", positive=True)
    if snapshots is None:
        raise ValueError("No L2 capture")
    times = [exact_int(x, "book time ns") for x in snapshots.times_ns]
    if not times or len(times) != len(snapshots.bids) or len(times) != len(snapshots.asks):
        raise ValueError("Empty, truncated, or mismatched L2 time arrays")
    if any(t < 0 for t in times) or any(b < a for a, b in zip(times, times[1:])):
        raise ValueError("L2 exchange timestamps are invalid or not monotonically ordered")

    unique = len(set(times))
    two_sided = one_sided = empty = 0
    max_bid_depth = max_ask_depth = 0
    top_positive_spreads = 0
    for bids, asks in zip(snapshots.bids, snapshots.asks):
        if len(bids) > max_depth or len(asks) > max_depth:
            raise ValueError("Captured L2 orderbook exceeds declared maximum depth")
        for levels, side in ((bids, "bid"), (asks, "ask")):
            prev_price = None
            for price, qty in levels:
                price = exact_int(price, "book price", positive=True)
                qty = exact_int(qty, "book quantity", positive=True)
                if prev_price is not None:
                    if side == "bid" and price > prev_price:
                        raise ValueError("Bid levels not in best-to-worst order")
                    if side == "ask" and price < prev_price:
                        raise ValueError("Ask levels not in best-to-worst order")
                prev_price = price

        max_bid_depth = max(max_bid_depth, len(bids))
        max_ask_depth = max(max_ask_depth, len(asks))
        if bids and asks:
            two_sided += 1
            if int(asks[0][0]) > int(bids[0][0]):
                top_positive_spreads += 1
        elif bids or asks:
            one_sided += 1
        else:
            empty += 1

    return {
        "l2_snapshot_events": len(times),
        "unique_exchange_timestamps": unique,
        "same_timestamp_repeated_snapshots": len(times) - unique,
        "two_sided_snapshots": two_sided,
        "one_sided_snapshots": one_sided,
        "empty_snapshots": empty,
        "max_observed_bid_depth": max_bid_depth,
        "max_observed_ask_depth": max_ask_depth,
        "two_sided_with_positive_spread": top_positive_spreads,
        "source_capture_depth": max_depth,
        "source_timestamp_order_monotonic": True,
        "all_input_snapshots_preserved": True,
        "order_level_owner_ids_exposed": False,
    }


def simulate_l2(seed: int = 1401) -> dict:
    from abides_markets.config_system import SimulationBuilder
    from abides_markets.config_system.agent_configs import NoiseAgentConfig
    from abides_markets.config_system.models import ExchangeConfig
    from abides_markets.simulation import ResultProfile, run_simulation

    if seed < 0:
        raise ValueError("Seed cannot be negative")
    depth = 5
    config = (
        SimulationBuilder().apply_template("liquid_market")
        .ticker("ABM").start_time("09:30:00").end_time("09:35:00")
        .exchange(ExchangeConfig(book_capture="l2", book_log_depth=depth))
        .enable_agent(
            NoiseAgentConfig(multi_wake=True, wake_up_freq="10s",
                             noise_mkt_close_time="09:35:00"), count=40
        ).seed(seed).build()
    )
    result = run_simulation(config, profile=ResultProfile.QUANT)
    market = result.markets["ABM"]
    counts = audit_l2_public(market.l2_series, max_depth=depth)
    if counts["two_sided_snapshots"] == 0:
        raise RuntimeError("No two-sided book snapshots: L2 probe is inconclusive")
    return {
        "schema_version": "abides-l2-feasibility-v1",
        "simulator": "abides-ng",
        "simulator_revision": UPSTREAM_COMMIT,
        "seed": seed,
        "simulated_session": "09:30:00–09:35:00",
        "public_book": counts,
        "public_trade_print_count": len(market.trades or []),
        "real_exchange_l2_archive_availability_verified": False,
        "physical_owner_identity_known": False,
        "statistical_accuracy_calibrated": False,
        "live_trading_enabled": False,
        "limitations": [
            "ABIDES_ONLY: genuine simulated exchange L2 book, not T-Invest historical or live L2 data.",
            "QUOTE_LEVELS_ARE_AGGREGATED: no causal owner, parent order, or individual bot count.",
            "TIMESTAMP_DOES_NOT_PROVE_RECEIPT: simulation clock is not real API message latency.",
            "NO_HOLDOUT: seed is exploratory and spent after this probe.",
            "NO_ORDER_API: no real user accounts, broker orders, or exchange-side market activity."
        ]
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=1401)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Refusing to overwrite prior L2 research evidence")
    report = simulate_l2(args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write("\n")
    print("ABIDES_L2_FEASIBILITY", json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
