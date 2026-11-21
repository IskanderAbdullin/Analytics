#!/usr/bin/env python3
"""Fail-closed archive completion watermark tests; no simulator needed."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from lagged_l2_bin import summarize_lagged_book
from l2_trade_context import PublicExecution

NS = 1_000_000_000
STEP = 10 * NS


def samples():
    # Quote in bins 0..6 and executions in bins 1..7.
    books = SimpleNamespace(
        times_ns=[i * STEP + 2 * NS for i in range(7)],
        bids=[[(100, 30 + i * 5)] for i in range(7)],
        asks=[[(102, 70 - i * 5)] for i in range(7)])
    fills = [
        PublicExecution(i * STEP + 3 * NS, 102, 20 + i * 5, "BUY")
        for i in range(1, 8)
    ] + [
        PublicExecution(i * STEP + 4 * NS, 100, 80 - i * 5, "SELL")
        for i in range(1, 8)
    ]
    return books, fills


class ExclusiveCompletionWatermark(unittest.TestCase):
    def test_unattested_archive_is_explicitly_unverified(self):
        book, prints = samples()
        r = summarize_lagged_book(book, prints, bin_seconds=10)
        self.assertEqual(r["eligible_lagged_bins"], 7)
        self.assertFalse(r["archive_completion_watermark_supplied"])
        self.assertIsNone(r["complete_through_ns"])
        self.assertTrue(r["terminal_bin_may_be_partial_without_watermark"])
        self.assertFalse(r["completion_watermark_independently_verified"])
        self.assertFalse(r["real_l2_feed_coverage_proven"])

    def test_terminal_bin_abstains_until_exclusive_end_watermark(self):
        book, prints = samples()
        before = summarize_lagged_book(
            book, prints, bin_seconds=10, complete_through_ns=7 * STEP)
        after = summarize_lagged_book(
            book, prints, bin_seconds=10, complete_through_ns=8 * STEP)
        self.assertEqual(before["eligible_lagged_bins"], 6)
        self.assertEqual(after["eligible_lagged_bins"], 7)
        self.assertEqual(before["abstained_clock_bins"][
            "current_bin_not_closed_by_watermark"], 1)
        self.assertEqual(after["abstained_clock_bins"][
            "current_bin_not_closed_by_watermark"], 0)
        self.assertTrue(before["archive_completion_watermark_supplied"])
        self.assertFalse(before["terminal_bin_may_be_partial_without_watermark"])
        self.assertFalse(before["completion_watermark_independently_verified"])
        self.assertEqual(before["complete_through_ns"], 7 * STEP)
        self.assertEqual(before["observations"], after["observations"][:-1])
        self.assertEqual(sum(before["abstained_clock_bins"].values()) +
                         before["eligible_lagged_bins"],
                         before["populated_execution_clock_bins"])

    def test_later_unclosed_print_cannot_rewrite_closed_prefix(self):
        book, prints = samples()
        initial = summarize_lagged_book(
            book, [p for p in prints if p.time_ns < 7 * STEP],
            bin_seconds=10, complete_through_ns=7 * STEP)
        extension = summarize_lagged_book(
            book, prints, bin_seconds=10, complete_through_ns=7 * STEP)
        self.assertEqual(initial["observations"], extension["observations"])
        self.assertEqual(
            initial["descriptive_lagged_imbalance_to_next_buy_share_spearman"],
            extension["descriptive_lagged_imbalance_to_next_buy_share_spearman"])
        self.assertEqual(extension["abstained_clock_bins"][
            "current_bin_not_closed_by_watermark"], 1)

    def test_before_first_closed_bin_is_all_abstained(self):
        book, prints = samples()
        r = summarize_lagged_book(
            book, prints, bin_seconds=10, complete_through_ns=STEP)
        self.assertEqual(r["eligible_lagged_bins"], 0)
        self.assertEqual(r["abstained_clock_bins"][
            "current_bin_not_closed_by_watermark"], 7)
        self.assertIsNone(
            r["descriptive_lagged_imbalance_to_next_buy_share_spearman"])

    def test_invalid_watermark_values_fail_closed(self):
        book, prints = samples()
        for bad in (-1, 3.5, True, "40000000000"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                summarize_lagged_book(
                    book, prints, bin_seconds=10, complete_through_ns=bad)

    def test_prior_book_does_not_bypass_unclosed_trade_bin(self):
        book, prints = samples()
        # Even with a valid preceding book, the terminal trade bin is excluded.
        r = summarize_lagged_book(
            book, prints, bin_seconds=10, complete_through_ns=7 * STEP)
        self.assertEqual(r["observations"][-1]["current_bin_ordinal"], 6)
        self.assertTrue(all(
            (o["current_bin_ordinal"] + 1) * STEP <= r["complete_through_ns"]
            for o in r["observations"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
