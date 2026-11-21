#!/usr/bin/env python3
"""Pure tests for lagged prior-clock-book features (no ABIDES dependency)."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from lagged_l2_bin import summarize_lagged_book
from l2_trade_context import PublicExecution


NANO = 1_000_000_000


def quote_book(times, imbalance_values):
    bids, asks = [], []
    for x in imbalance_values:
        # Qty sums vary with x; bids+asks remain 100.
        bids.append([(100, 50 + x)])
        asks.append([(102, 50 - x)])
    return SimpleNamespace(times_ns=times, bids=bids, asks=asks)


def trades_per_bin(shares, *, bin_seconds=10):
    result = []
    for ordinal, buy_pct in enumerate(shares, start=1):
        at = (ordinal * bin_seconds + 3) * NANO
        buy, sell = buy_pct, 100 - buy_pct
        if buy:
            result.append(PublicExecution(at, 102, buy, "BUY"))
        if sell:
            result.append(PublicExecution(at, 100, sell, "SELL"))
    return result


class LaggedPriorL2Tests(unittest.TestCase):
    def test_prior_completed_book_imbalance_correlates_with_next_bin_share(self):
        # Eight previous completed book bins, plus eight next-bin outcomes.
        previous = [2 + 10 * i for i in range(8)]
        imbalance = [-40, -30, -20, -10, 10, 20, 30, 40]
        book = quote_book([x*NANO for x in previous], imbalance)
        tape = trades_per_bin([10, 20, 30, 40, 60, 70, 80, 90])
        report = summarize_lagged_book(
            book, tape, bin_seconds=10, maximum_quote_age_seconds=10)
        self.assertEqual(report["eligible_lagged_bins"], 8)
        self.assertEqual(report["populated_execution_clock_bins"], 8)
        self.assertEqual(report["public_execution_lots"], 800)
        self.assertEqual(report["public_execution_prints"], 16)
        self.assertGreater(report[
            "descriptive_lagged_imbalance_to_next_buy_share_spearman"], .99999)
        self.assertTrue(all(
            o["previous_last_l2_time_ns"] < o["current_bin_ordinal"]*10*NANO
            for o in report["observations"]))
        self.assertTrue(report["previous_completed_bin_only"])
        self.assertFalse(report["individual_robot_detected"])
        self.assertFalse(report["private_agent_identifiers_used"])
        self.assertFalse(report["real_market_significance_calibrated"])
        self.assertNotEqual(report[
            "descriptive_lagged_imbalance_to_next_buy_share_spearman"],
            report["rotated_next_bin_share_placebo_spearman"])

    def test_source_gap_and_stale_previous_bin_never_zero_imputed(self):
        tape = trades_per_bin([30, 40, 50], bin_seconds=10)
        # Previous completed book bins: 0, missing 1, 2.
        book = quote_book([2*NANO, 22*NANO], [-10, 10])
        report = summarize_lagged_book(book, tape, bin_seconds=10)
        self.assertEqual(report["eligible_lagged_bins"], 2)
        self.assertEqual(report["abstained_clock_bins"][
            "missing_immediately_previous_book_bin"], 1)
        self.assertIsNone(report[
            "descriptive_lagged_imbalance_to_next_buy_share_spearman"])
        short_age = summarize_lagged_book(
            book, tape, bin_seconds=10, maximum_quote_age_seconds=5)
        self.assertEqual(short_age["eligible_lagged_bins"], 0)
        self.assertEqual(short_age["abstained_clock_bins"][
            "prior_quote_too_old"], 2)

    def test_future_quotes_never_change_prior_completed_bin_observations(self):
        first = quote_book([2*NANO, 12*NANO], [-10, 10])
        more = quote_book([2*NANO, 12*NANO, 20*NANO,
                           20*NANO, 22*NANO], [-10, 10, 9, 8, 7])
        public = trades_per_bin([25, 75], bin_seconds=10)
        early = summarize_lagged_book(first, public, bin_seconds=10)
        later = summarize_lagged_book(more, public, bin_seconds=10)
        self.assertEqual(early["observations"], later["observations"])
        self.assertEqual(later["source_same_time_l2_updates_retained"], 1)
        self.assertEqual(early["eligible_lagged_bins"], 2)

    def test_last_observed_snapshot_of_completed_prior_bin_is_used(self):
        book = quote_book([2*NANO, 3*NANO, 3*NANO], [-20, 0, 25])
        public = trades_per_bin([75], bin_seconds=10)
        r = summarize_lagged_book(book, public, bin_seconds=10)
        self.assertEqual(r["eligible_lagged_bins"], 1)
        self.assertEqual(r["source_same_time_l2_updates_retained"], 1)
        self.assertAlmostEqual(
            r["observations"][0]["previous_book_imbalance"], .5)
        self.assertEqual(r["observations"][0][
            "previous_quote_age_at_current_bin_open_ns"], 7*NANO)
        self.assertFalse(r["real_l2_feed_coverage_proven"])

    def test_null_constant_market_book_cannot_invent_correlation(self):
        book = quote_book([i*10*NANO+2*NANO for i in range(8)], [0]*8)
        tape = trades_per_bin([20,30,40,50,60,70,80,90])
        r = summarize_lagged_book(book, tape, bin_seconds=10)
        self.assertIsNone(r[
            "descriptive_lagged_imbalance_to_next_buy_share_spearman"])
        self.assertIsNone(r["rotated_next_bin_share_placebo_spearman"])
        self.assertFalse(r["individual_robot_detected"])

    def test_rejects_bad_configs_and_invalid_public_fills(self):
        valid = quote_book([2*NANO], [0])
        one = trades_per_bin([25])
        for opts in (
            {"bin_seconds": 0}, {"maximum_quote_age_seconds": 0},
            {"bin_seconds": 10, "maximum_quote_age_seconds": 11},
            {"maximum_depth": 0}
        ):
            with self.subTest(opts=opts), self.assertRaises(ValueError):
                summarize_lagged_book(valid, one, **opts)
        with self.assertRaises(ValueError):
            summarize_lagged_book(valid, [
                PublicExecution(13*NANO, 100, 0, "BUY")], bin_seconds=10)
        with self.assertRaises(ValueError):
            summarize_lagged_book(valid, [
                PublicExecution(13*NANO, 100, 10, "UNKNOWN")], bin_seconds=10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
