#!/usr/bin/env python3
"""Public-only L2 quote/print join: negative controls and causality guards."""
import sys
import unittest
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from l2_trade_context import (
    PublicExecution, audit_public_join, public_projection,
    rotated_public_prints
)


def book(times, bids, asks):
    return SimpleNamespace(times_ns=times, bids=bids, asks=asks)


def fill(t, price, qty=5, side="BUY"):
    return PublicExecution(t, price, qty, side)


class PublicBookTradeContextTests(unittest.TestCase):
    def test_ambiguous_same_timestamp_never_uses_future_snapshot(self):
        l2 = book(
            [100, 100, 200, 300],
            [[(100, 10)], [(101, 10)], [(101, 7)], []],
            [[(102, 10)], [(103, 11)], [(102, 8)], [(104, 5)]],
        )
        stream = [fill(100, 104), fill(101, 104),
                  fill(201, 101, side="SELL"),
                  fill(301, 105)]
        result = audit_public_join(l2, stream, max_age_ns=200)
        self.assertEqual(result["public_fill_count"], 4)
        self.assertEqual(result["l2_snapshot_count"], 4)
        self.assertEqual(result["same_timestamp_l2_updates_retained"], 1)
        self.assertEqual(result["categories"]["same_timestamp_ambiguous"], 1)
        self.assertEqual(result["categories"]["at_or_through_prior_opposite_best"], 2)
        self.assertEqual(result["categories"]["one_sided_or_empty_quote"], 1)
        self.assertEqual(sum(result["categories"].values()), 4)
        self.assertEqual(sum(result["lots_by_category"].values()), 20)
        self.assertFalse(result["physical_owner_identity_known"])
        self.assertFalse(result["statistical_significance_established"])

    def test_stale_unseen_crossed_and_incompatible_not_auto_assigned(self):
        l2 = book(
            [100, 300],
            [[(100, 3)], [(103, 8)]],
            [[(102, 3)], [(102, 8)]],
        )
        trades = [fill(50, 102), fill(130, 101), fill(250, 104),
                  fill(301, 105)]
        result = audit_public_join(l2, trades, max_age_ns=80)
        self.assertEqual(result["categories"]["no_prior_quote"], 1)
        self.assertEqual(result["categories"]["not_at_prior_opposite_best"], 1)
        self.assertEqual(result["categories"]["stale_quote"], 1)
        self.assertEqual(result["categories"]["crossed_or_locked_quote"], 1)
        self.assertEqual(result["eligible_two_sided_fills"], 1)
        self.assertEqual(result["descriptive_prior_quote_alignment_fraction"], 0.0)

    def test_future_snapshot_append_never_rewrites_existing_trades(self):
        public = [fill(150, 102), fill(151, 100, side="SELL")]
        past = book([100], [[(100, 3)]], [[(102, 8)]])
        future = book([100, 200, 200, 250], [
            [(100, 3)], [(110, 2)], [(111, 2)], [(112, 2)]
        ], [
            [(102, 8)], [(120, 2)], [(121, 2)], [(122, 2)]
        ])
        a = audit_public_join(past, public, max_age_ns=100)
        b = audit_public_join(future, public, max_age_ns=100)
        self.assertEqual(a["categories"], b["categories"])
        self.assertEqual(a["lots_by_category"], b["lots_by_category"])
        self.assertEqual(a["eligible_two_sided_fills"], 2)
        self.assertEqual(b["eligible_two_sided_fills"], 2)

    def test_rotation_preserves_public_marginals_without_actor_truth(self):
        tape = (fill(200, 102, 4), fill(210, 100, 3, "SELL"),
                fill(210, 105, 2), fill(260, 104, 5, "SELL"))
        shifted = rotated_public_prints(tape)
        self.assertEqual([t.time_ns for t in shifted],
                         [t.time_ns for t in tape])
        self.assertEqual(Counter((t.price_cents, t.quantity, t.reported_aggressor_side)
                                 for t in shifted),
                         Counter((t.price_cents, t.quantity, t.reported_aggressor_side)
                                 for t in tape))
        l2 = book([100], [[(100, 10)]], [[(102, 10)]])
        normal = audit_public_join(l2, tape)
        rotated = audit_public_join(l2, shifted)
        self.assertEqual(normal["public_total_lots"], rotated["public_total_lots"])
        self.assertEqual(normal["public_fill_count"], rotated["public_fill_count"])
        self.assertTrue(normal["interpretation"].startswith("A contemporaneous"))
        self.assertFalse(rotated["broker_data_used"])
        self.assertFalse(rotated["order_placement_enabled"])

    def test_projection_drops_private_agent_fields(self):
        raw = [SimpleNamespace(
            time_ns=100, side="SELL", quantity=10, price_cents=102,
            passive_agent_id=987, aggressive_agent_id=654)]
        anonymous = public_projection(raw)
        self.assertEqual(anonymous, (fill(100, 102, 10, "BUY"),))
        self.assertFalse(hasattr(anonymous[0], "passive_agent_id"))
        self.assertFalse(hasattr(anonymous[0], "aggressive_agent_id"))

    def test_strict_input_validation(self):
        clean = book([100], [[(100, 10)]], [[(101, 10)]])
        for malformed in (
            [fill(101, 0)], [fill(101, 101, 0)],
            [fill(-1, 101)], [fill(101, 101, 1, "UNKNOWN")],
        ):
            with self.subTest(malformed=malformed), self.assertRaises(ValueError):
                audit_public_join(clean, malformed)
        with self.assertRaises(ValueError):
            audit_public_join(clean, [fill(101, 101)], max_age_ns=0)
        with self.assertRaises(ValueError):
            audit_public_join(clean, [fill(101, 101)], max_depth=0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
