#!/usr/bin/env python3
"""No-dependency tests of the public simulated L2 projection contract."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from l2_probe import audit_l2_public


def book(times, bids, asks):
    return SimpleNamespace(times_ns=times, bids=bids, asks=asks)


class PublicL2FeasibilityTests(unittest.TestCase):
    def test_same_timestamp_snapshots_are_never_deduplicated(self):
        snap = book(
            [100, 100, 200],
            [[(100, 10), (99, 9)], [(100, 9)], []],
            [[(101, 8), (102, 5)], [(102, 10)], [(101, 6)]],
        )
        report = audit_l2_public(snap, max_depth=5)
        self.assertEqual(report["l2_snapshot_events"], 3)
        self.assertEqual(report["unique_exchange_timestamps"], 2)
        self.assertEqual(report["same_timestamp_repeated_snapshots"], 1)
        self.assertEqual(report["two_sided_snapshots"], 2)
        self.assertEqual(report["one_sided_snapshots"], 1)
        self.assertEqual(report["max_observed_bid_depth"], 2)
        self.assertEqual(report["max_observed_ask_depth"], 2)
        self.assertTrue(report["all_input_snapshots_preserved"])
        self.assertFalse(report["order_level_owner_ids_exposed"])

    def test_bad_book_depth_price_and_order_are_rejected(self):
        bad = [
            book([1], [[(100, 1), (99, 2)]], [[]]),
            book([1], [[(100, 1), (101, 2)]], [[]]),
            book([1], [[]], [[(101, 1), (100, 2)]]),
            book([1], [[(100, 0)]], [[]]),
            book([1], [[(0, 1)]], [[]]),
            book([1, 2], [[(100, 1)]], [[(101, 1)]]),
            book([2, 1], [[(100, 1)], [(100, 1)]], [[(101, 1)], [(101, 1)]]),
        ]
        for i, snapshot in enumerate(bad):
            with self.subTest(i=i), self.assertRaises(ValueError):
                audit_l2_public(snapshot, max_depth=1 if i == 0 else 5)

    def test_empty_source_and_invalid_depth_rejected(self):
        with self.assertRaises(ValueError):
            audit_l2_public(None, max_depth=5)
        with self.assertRaises(ValueError):
            audit_l2_public(book([], [], []), max_depth=5)
        with self.assertRaises(ValueError):
            audit_l2_public(book([1], [[]], [[]]), max_depth=0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
