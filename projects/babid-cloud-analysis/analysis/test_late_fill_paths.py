"""Synthetic-only tests for the source-derived predicate and alternatives."""
from __future__ import annotations

from dataclasses import replace
import unittest

from late_fill_paths import (
    OrderSnapshot,
    after_fill_synthetic_paths,
    precredit_prior_baseline,
    source_prune_predicate,
    window_ms,
)


class LateFillSourcePredicateTests(unittest.TestCase):
    def setUp(self):
        self.zero = OrderSnapshot(
            terminal=True, filled_by_state=0, filled_by_fills=0,
            updated_ms=1000, now_ms=6000,
        )

    def test_zero_cancel_only_after_grace(self):
        self.assertTrue(source_prune_predicate(self.zero))
        self.assertFalse(source_prune_predicate(replace(self.zero, now_ms=5999)))
        self.assertFalse(source_prune_predicate(replace(self.zero, terminal=False)))

    def test_silent_state_credit_blocks_prune(self):
        s = replace(self.zero, filled_by_state=2)
        self.assertEqual(s.filled, 2)
        self.assertFalse(s.fills_synchronized)
        self.assertFalse(source_prune_predicate(s))

    def test_booked_trade_blocks_prune(self):
        self.assertFalse(source_prune_predicate(replace(self.zero, filled_by_fills=2)))

    def test_unsettled_flags_block_prune(self):
        for name in ("needs_check", "resync_needed", "query_in_flight"):
            with self.subTest(flag=name):
                self.assertFalse(source_prune_predicate(replace(self.zero, **{name: True})))

    def test_negative_lots_grace_rejected(self):
        with self.assertRaises(ValueError):
            source_prune_predicate(replace(self.zero, filled_by_state=-1))
        with self.assertRaises(ValueError):
            source_prune_predicate(self.zero, grace_ms=-1)

    def test_two_alternatives_leave_flat_journal_at_fill(self):
        paths = after_fill_synthetic_paths(36, 2)
        for name, p in paths.items():
            with self.subTest(path=name):
                self.assertEqual(p["journal_after_fill"], p["journal_before_fill"])
                self.assertEqual(p["pnl_delta_at_fill"], -2)
        self.assertNotEqual(
            paths["detached"]["journal_before_fill"],
            paths["precredited"]["journal_before_fill"],
        )

    def test_precredit_requires_earlier_offset(self):
        self.assertEqual(precredit_prior_baseline(36, 2), 38)
        with self.assertRaises(ValueError):
            precredit_prior_baseline(36, 0)

    def test_grace_window_is_not_archive_proof(self):
        self.assertEqual(window_ms(0, 38285), 33285)
        self.assertEqual(window_ms(0, 4500), 0)

    def test_argument_guards(self):
        with self.assertRaises(ValueError):
            window_ms(0, 10000, -1)
        with self.assertRaises(ValueError):
            after_fill_synthetic_paths(0, 0)


if __name__ == "__main__":
    unittest.main()
