#!/usr/bin/env python3
"""Construct explicit, anonymous *public-book common-factor* null families.

These are synthetic data-generation counterexamples, NOT real exchange
simulations and NOT statistically calibrated market-conditional nulls.
No one hidden parent order/physical owner is created. Many independent
public prints can react to the same synthetic market-wide latent state.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import random
from types import SimpleNamespace

from l2_probe import audit_l2_public
from l2_trade_context import PublicExecution, audit_public_join
from lagged_l2_bin import summarize_lagged_book

NANO = 1_000_000_000
WIDTH_SECONDS = 30
FAMILIES = ("common_factor", "independent_flow",
            "market_wide_shock", "synchronized_clock")


def _three_positive_parts(qty: int) -> tuple[int, int, int]:
    a = qty // 3
    if a <= 0:
        raise ValueError("Split lot count must be >= 3")
    return a, a, qty - 2*a


def public_null_tape(kind: str, *, seed: int = 1701, bins: int = 24):
    """Public clocked L2 and anonymous fills; deliberately no actor label."""
    if kind not in FAMILIES or seed < 0 or not 8 <= bins <= 24:
        raise ValueError("Unsupported public null family, seed or session width")
    rng = random.Random(seed)
    factors = [6 + 3*i for i in range(bins)]
    rng.shuffle(factors)
    if kind == "market_wide_shock":
        factors = [20 if i < bins // 2 else 65 for i in range(bins)]
    outcomes = list(factors)
    if kind == "independent_flow":
        rng2 = random.Random(seed + 1_337)
        rng2.shuffle(outcomes)

    times = []
    bids = []
    asks = []
    for i, factor in enumerate(factors):
        times.append((i * WIDTH_SECONDS + 2) * NANO)
        # Public aggregated depth reacts to one common latent state.
        # Single price per side so level order remains unambiguous.
        bids.append([(100, 20 + factor)])
        asks.append([(102, 80 - factor)])

    if kind == "synchronized_clock":
        # The exchange clock stamps book mutations and fills at the same
        # time, so strict event-level quote/print joining must abstain.
        times.append((bins*WIDTH_SECONDS + 2)*NANO)
        bids.append([(100, 50)])
        asks.append([(102, 50)])

    snapshots = SimpleNamespace(times_ns=times, bids=bids, asks=asks)
    audit_l2_public(snapshots, max_depth=5)
    trades = []
    for current, factor in enumerate(outcomes, start=1):
        buy = 20 + factor
        sell = 80 - factor
        stamp = (current*WIDTH_SECONDS +
                 (2 if kind == "synchronized_clock" else 3))*NANO
        for quantity in _three_positive_parts(buy):
            trades.append(PublicExecution(stamp, 102, quantity, "BUY"))
        for quantity in _three_positive_parts(sell):
            trades.append(PublicExecution(stamp, 100, quantity, "SELL"))
    return snapshots, tuple(trades)


def summarize_null_families(*, seed: int = 1701, bins: int = 24) -> dict:
    cases = []
    for kind in FAMILIES:
        book, trades = public_null_tape(kind, seed=seed, bins=bins)
        lagged = summarize_lagged_book(
            book, trades, bin_seconds=WIDTH_SECONDS,
            maximum_quote_age_seconds=WIDTH_SECONDS)
        joined = audit_public_join(book, trades)
        if lagged["eligible_lagged_bins"] != bins:
            raise AssertionError("Synthetic market null lost an expected lagged bin")
        if lagged["public_execution_lots"] != bins*100 or len(trades) != bins*6:
            raise AssertionError("Anonymous public execution/lot conservation failed")
        if sum(joined["categories"].values()) != len(trades):
            raise AssertionError("Quote/print category conservation failed")
        if kind == "synchronized_clock" and (
            joined["categories"]["same_timestamp_ambiguous"] != len(trades)
        ):
            raise AssertionError("Synchronized time must force strict-join abstention")
        cases.append({
            "family": kind,
            "public_l2_snapshots": lagged["source_l2_snapshot_count"],
            "anonymous_public_execution_prints": len(trades),
            "public_execution_lots": lagged["public_execution_lots"],
            "eligible_past_book_to_next_bin_pairs": lagged["eligible_lagged_bins"],
            "descriptive_spearman":
                lagged["descriptive_lagged_imbalance_to_next_buy_share_spearman"],
            "rotated_bin_placebo_spearman":
                lagged["rotated_next_bin_share_placebo_spearman"],
            "strict_same_timestamp_execution_abstentions":
                joined["categories"]["same_timestamp_ambiguous"],
            "single_identified_parent_order_present": False,
            "real_market_null_calibrated": False,
        })

    return {
        "schema_version": "public-l2-common-market-factor-null-v1",
        "seed": seed,
        "clock_bin_seconds": WIDTH_SECONDS,
        "session_bins": bins,
        "families": cases,
        "underlying_source": "deterministic_educational_synthetic_not_ABIDES",
        "unique_physical_actor_count_identifiable": False,
        "private_agent_labels_created": False,
        "real_market_significance_calibrated": False,
        "no_actual_orders_sent": True,
        "interpretation": (
            "A large previous-book-imbalance/next-flow correlation can be "
            "generated entirely by a common public market-wide factor "
            "without constructing an identifiable hidden parent order."
        ),
        "limitations": [
            "Mechanism is intentionally synthetic and not an ABIDES engine run.",
            "Independent public fills share a generated latent market condition; "
            "they are not validated independent human actors.",
            "A deterministic rho near one is a counterexample to unique owner "
            "inference, not proof of realistic false positive probability.",
            "Market shocks and synchronous exchange clocks confound public "
            "footprint signals; conditional market nulls still need validation.",
            "No real MOEX/SPB calibration, physical account identity or trading edge."
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=1701)
    parser.add_argument("--bins", type=int, default=24)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Refusing to overwrite public null evidence")
    result = summarize_null_families(seed=args.seed, bins=args.bins)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as target:
        json.dump(result, target, indent=2, sort_keys=True)
        target.write("\n")
    for case in result["families"]:
        print("L2_PUBLIC_COMMON_FACTOR_NULL", json.dumps(case, sort_keys=True))


if __name__ == "__main__":
    main()
