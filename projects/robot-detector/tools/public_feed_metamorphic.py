#!/usr/bin/env python3
"""Deterministic public-source metamorphic invariants (no simulator/trading).

Generated test books/prints are synthetic *fixtures*, not market outcomes or
new blind ABIDES studies. This tool tests that later messages, a stricter
coverage claim or a tighter watermark cannot retroactively add observations
to a previously closed public analysis window.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
from types import SimpleNamespace

from lagged_l2_bin import summarize_lagged_book
from l2_trade_context import PublicExecution
from public_stream_coverage import PublicStreamClaim, DualPublicStreamClaim

STEP = 10_000_000_000
MAX_TRIALS = 128


def _claim(kind: str, gaps=()) -> PublicStreamClaim:
    return PublicStreamClaim(
        kind, "SIMULATED", "ABM", "fixture-session", "fixture-source",
        0, 14 * STEP, tuple(gaps))


def _coverage(book_gaps=(), trade_gaps=()) -> DualPublicStreamClaim:
    return DualPublicStreamClaim(
        _claim("book", book_gaps), _claim("trades", trade_gaps))


def fixture(seed: int):
    rng = random.Random(seed)
    times, bids, asks = [], [], []
    for i in range(12):
        # Fully ordered and unique-price aggregated L2 with one level/side.
        times.append(i * STEP + 2_000_000_000)
        bids.append([(100, rng.randrange(5, 90))])
        asks.append([(102, rng.randrange(5, 90))])
    snapshots = SimpleNamespace(times_ns=times, bids=bids, asks=asks)
    public = []
    for i in range(1, 13):
        qty = rng.randrange(1, 100)
        public.append(PublicExecution(i * STEP + 3_000_000_000, 102, qty, "BUY"))
        public.append(PublicExecution(i * STEP + 4_000_000_000, 100, 100 - qty, "SELL"))
    return snapshots, tuple(public)


def evaluate_trial(seed: int) -> dict:
    book, public = fixture(seed)
    claimed = _coverage()
    watermark = 9 * STEP

    def score(snapshots=book, trades=public, coverage=claimed, complete=watermark):
        return summarize_lagged_book(
            snapshots, trades, bin_seconds=10, maximum_quote_age_seconds=10,
            complete_through_ns=complete, source_coverage=coverage)

    baseline = score()
    if baseline["eligible_lagged_bins"] != 8:
        raise AssertionError("Fixture did not provide eight fully closed pairs")
    if baseline["abstained_clock_bins"]["current_bin_not_closed_by_watermark"] != 4:
        raise AssertionError("Future unclosed fixture bins were not excluded")

    # Append *only* later public snapshots and a later print, never a backfill
    # to an already closed interval. The source declares coverage all the way
    # through bin 13 but the completion watermark still stops at bin 9.
    extended_book = SimpleNamespace(
        times_ns=list(book.times_ns) + [12*STEP+2_000_000_000],
        bids=list(book.bids) + [[(100, 20)]],
        asks=list(book.asks) + [[(102, 25)]])
    extended = score(
        extended_book,
        public + (PublicExecution(13*STEP+3_000_000_000,102,5,"BUY"),))
    if baseline["observations"] != extended["observations"]:
        raise AssertionError("Future appended public records rewrote closed observations")
    if (
        baseline["descriptive_lagged_imbalance_to_next_buy_share_spearman"]
        != extended["descriptive_lagged_imbalance_to_next_buy_share_spearman"]
    ):
        raise AssertionError("Future appended records changed closed-bin rho")

    # More documented loss of either public stream cannot create additional
    # eligible observations. These are caller-declared gaps, not observed
    # real-provider continuity records.
    blocked_book = score(coverage=_coverage(book_gaps=((3*STEP,4*STEP),)))
    blocked_trade = score(coverage=_coverage(trade_gaps=((5*STEP,6*STEP),)))
    both = score(coverage=_coverage(
        book_gaps=((3*STEP,4*STEP),),
        trade_gaps=((5*STEP,6*STEP),)))
    if not (
        both["eligible_lagged_bins"] <= blocked_book["eligible_lagged_bins"]
        <= baseline["eligible_lagged_bins"]
        and both["eligible_lagged_bins"] <= blocked_trade["eligible_lagged_bins"]
        <= baseline["eligible_lagged_bins"]
    ):
        raise AssertionError("Declared source loss increased eligible bins")
    if blocked_book["abstained_clock_bins"]["declared_previous_book_stream_uncovered"] != 1:
        raise AssertionError("Known missing prior L2 book bin did not abstain")
    if blocked_trade["abstained_clock_bins"]["declared_current_trade_stream_uncovered"] != 1:
        raise AssertionError("Known missing current trade bin did not abstain")

    # Delaying the completion watermark can only remove eligible bins, not
    # manufacture earlier observations.
    earlier = score(complete=7*STEP)
    if not (
        earlier["observations"] == baseline["observations"][:6]
        and earlier["eligible_lagged_bins"] == 6
    ):
        raise AssertionError("Earlier watermark changed the already closed prefix")
    for result in (baseline, extended, blocked_book, blocked_trade, both, earlier):
        if result["eligible_lagged_bins"] + sum(
            result["abstained_clock_bins"].values()
        ) != result["populated_execution_clock_bins"]:
            raise AssertionError("Public clock-bin accounting no longer conserves bins")
        if (result["real_l2_feed_coverage_proven"]
            or result["stream_coverage_independently_verified"]
            or result["individual_robot_detected"]
            or result["real_market_significance_calibrated"]):
            raise AssertionError("Metamorphic source check fabricated empirical identity")

    return {
        "source_seed_label": "deterministic_test_fixture_not_ABIDES",
        "base_closed_bins": baseline["eligible_lagged_bins"],
        "book_gap_closed_bins": blocked_book["eligible_lagged_bins"],
        "trade_gap_closed_bins": blocked_trade["eligible_lagged_bins"],
        "both_gaps_closed_bins": both["eligible_lagged_bins"],
        "early_watermark_closed_bins": earlier["eligible_lagged_bins"],
        "all_invariants_passed": True,
        "independent_market_accuracy_calibrated": False,
    }


def run_checks(*, trials: int = 32) -> dict:
    if type(trials) is not int or not 1 <= trials <= MAX_TRIALS:
        raise ValueError("Trial count must be a bounded positive integer")
    results = [evaluate_trial(i) for i in range(trials)]
    if any(not r["all_invariants_passed"] for r in results):
        raise AssertionError("A metamorphic test failed")
    return {
        "schema_version": "robot-detector-public-metamorphic-v1",
        "fixture_count": trials,
        "source": "deterministic_synthetic_software_tests_not_genuine_ABIDES",
        "future_append_closed_prefix_stable": True,
        "book_and_trade_coverage_loss_does_not_increase_eligibility": True,
        "watermark_tightening_never_adds_eligible_observations": True,
        "all_public_bin_accounting_conserved": True,
        "provider_completeness_independently_verified": False,
        "private_agent_truth_used": False,
        "real_market_accuracy_calibrated": False,
        "live_trading_enabled": False,
        "reference_counts": results[0],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=32)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Refuse overwriting previous test evidence")
    summary = run_checks(trials=args.trials)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(summary, output, indent=2, sort_keys=True)
        output.write("\n")
    print("PUBLIC_FEED_METAMORPHIC_CHECKS", json.dumps(summary,sort_keys=True))


if __name__ == "__main__":
    main()
