#!/usr/bin/env python3
"""Deterministic public common-market nulls are not robot ground truth."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from l2_common_factor_null import (
    FAMILIES, public_null_tape, summarize_null_families
)
from lagged_l2_bin import summarize_lagged_book
from l2_trade_context import audit_public_join


class PublicMarketConditionalCounterexamples(unittest.TestCase):
    def test_strong_positive_lag_correlation_without_parent_order_identity(self):
        report = summarize_null_families(seed=1701, bins=24)
        self.assertEqual(report["underlying_source"],
                         "deterministic_educational_synthetic_not_ABIDES")
        self.assertFalse(report["private_agent_labels_created"])
        self.assertFalse(report["real_market_significance_calibrated"])
        self.assertFalse(report["unique_physical_actor_count_identifiable"])
        self.assertEqual(len(report["families"]), 4)
        common = next(x for x in report["families"]
                      if x["family"] == "common_factor")
        shock = next(x for x in report["families"]
                     if x["family"] == "market_wide_shock")
        self.assertGreater(common["descriptive_spearman"], .99999)
        self.assertGreater(shock["descriptive_spearman"], .99999)
        for case in report["families"]:
            self.assertFalse(case["single_identified_parent_order_present"])
            self.assertFalse(case["real_market_null_calibrated"])
            self.assertEqual(case["public_execution_lots"], 2400)
            self.assertEqual(case["anonymous_public_execution_prints"], 144)
            self.assertEqual(case["eligible_past_book_to_next_bin_pairs"], 24)

    def test_synchronized_venue_clock_defeats_strict_event_join_but_not_lag(self):
        book, public = public_null_tape(
            "synchronized_clock", seed=1701, bins=12)
        exact = audit_public_join(book, public)
        lag = summarize_lagged_book(book, public)
        self.assertEqual(exact["categories"]["same_timestamp_ambiguous"],
                         len(public))
        self.assertEqual(exact["eligible_two_sided_fills"], 0)
        self.assertEqual(lag["eligible_lagged_bins"], 12)
        self.assertTrue(lag["previous_completed_bin_only"])
        self.assertFalse(lag["individual_robot_detected"])

    def test_margins_and_past_exposure_survive_future_append(self):
        book_short, trades_short = public_null_tape(
            "common_factor", seed=1701, bins=8)
        r1 = summarize_lagged_book(book_short, trades_short)
        self.assertEqual(sum(o["current_prints"] for o in r1["observations"]),
                         len(trades_short))
        self.assertEqual(sum(o["current_buy_lots"]+o["current_sell_lots"]
                             for o in r1["observations"]),
                         sum(t.quantity for t in trades_short))
        self.assertTrue(all(
            o["previous_last_l2_time_ns"] < o["current_bin_ordinal"]*30*1000000000
            for o in r1["observations"]))
        # The shorter generated null is a different whole-session factor
        # schedule. Prefix invariance is tested on the *same* feed using
        # append-only snapshots in test_lagged_l2_bin.py.

    def test_deterministic_seed_and_side_marginals(self):
        a = summarize_null_families(seed=1701, bins=12)
        b = summarize_null_families(seed=1701, bins=12)
        self.assertEqual(json.dumps(a, sort_keys=True),
                         json.dumps(b, sort_keys=True))
        self.assertEqual([x["family"] for x in a["families"]],
                         list(FAMILIES))
        self.assertTrue(a["no_actual_orders_sent"])
        for kind in FAMILIES:
            book, tape = public_null_tape(kind, seed=1701, bins=12)
            self.assertEqual(len(tape), 72)
            self.assertEqual(sum(t.quantity for t in tape), 1200)
            self.assertTrue(all(t.reported_aggressor_side in ("BUY", "SELL")
                                and t.quantity > 0 for t in tape))
            self.assertTrue(all(not hasattr(t, "agent_id") for t in tape))

    def test_invalid_public_null_families_rejected(self):
        for kind,bins,seed in (
            ("invalid",24,1701),("common_factor",7,1701),
            ("common_factor",25,1701),("common_factor",12,-1)
        ):
            with self.subTest(kind=kind,bins=bins,seed=seed):
                with self.assertRaises(ValueError):
                    public_null_tape(kind, seed=seed, bins=bins)


if __name__ == "__main__":
    unittest.main(verbosity=2)
