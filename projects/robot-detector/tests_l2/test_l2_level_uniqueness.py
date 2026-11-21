#!/usr/bin/env python3
"""Public L2 levels are per-unique-price; duplicate entries fail closed."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from l2_probe import audit_l2_public
from lagged_l2_bin import summarize_lagged_book
from l2_trade_context import PublicExecution, audit_public_join


def snap(bids, asks, times=(100,)):
    return SimpleNamespace(times_ns=list(times), bids=bids, asks=asks)


class StrictAggregatedL2LevelsTests(unittest.TestCase):
    def test_duplicate_bid_price_at_different_quantities_rejected(self):
        book=snap([[(100,7),(100,12)]],[[(102,4)]])
        with self.assertRaises(ValueError):
            audit_l2_public(book,max_depth=5)

    def test_duplicate_ask_price_at_different_quantities_rejected(self):
        book=snap([[(99,7)]],[[(102,4),(102,20)]])
        with self.assertRaises(ValueError):
            audit_l2_public(book,max_depth=5)

    def test_duplicate_price_remains_invalid_at_any_depth(self):
        cases=[
            snap([[(102,1),(101,2),(101,3),(100,2)]],[[(104,1)]]),
            snap([[(100,1)]],[[(102,1),(103,2),(103,3),(104,2)]]),
            snap([[(100,1),(99,2),(100,3)]],[[(104,1)]]),
        ]
        for case in cases:
            with self.subTest(book=case),self.assertRaises(ValueError):
                audit_l2_public(case,max_depth=5)

    def test_valid_depth_five_strictly_sorted_levels_accepted(self):
        book=snap([[(100,10),(99,9),(98,8),(97,7),(96,6)]],
                  [[(102,5),(103,6),(104,7),(105,8),(106,9)]])
        result=audit_l2_public(book,max_depth=5)
        self.assertEqual(result["l2_snapshot_events"],1)
        self.assertEqual(result["two_sided_snapshots"],1)
        self.assertEqual(result["two_sided_with_positive_spread"],1)
        self.assertEqual(result["max_observed_bid_depth"],5)
        self.assertEqual(result["max_observed_ask_depth"],5)

    def test_duplicate_timestamp_does_not_mean_duplicate_book_price(self):
        book=snap(
            [[(100,7),(99,4)],[(101,5),(100,2)]],
            [[(102,9),(103,8)],[(103,7),(104,5)]],
            times=(100,100))
        result=audit_l2_public(book,max_depth=5)
        self.assertEqual(result["same_timestamp_repeated_snapshots"],1)
        self.assertEqual(result["l2_snapshot_events"],2)
        self.assertEqual(result["two_sided_snapshots"],2)

    def test_duplicate_levels_never_enter_quote_fill_or_lagged_statistics(self):
        book=snap([[(100,7),(100,4)]],[[(102,7)]],times=(2_000_000_000,))
        public=[PublicExecution(13_000_000_000,102,10,"BUY")]
        with self.assertRaises(ValueError):
            summarize_lagged_book(book,public,bin_seconds=10)
        with self.assertRaises(ValueError):
            audit_public_join(book,public)


if __name__ == "__main__":
    unittest.main(verbosity=2)
