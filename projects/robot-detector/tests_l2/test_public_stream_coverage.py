#!/usr/bin/env python3
"""Offline two-source coverage gates; do not claim real provider attestation."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from public_stream_coverage import (
    PublicStreamClaim, DualPublicStreamClaim, disclose_claim
)
from lagged_l2_bin import summarize_lagged_book
from l2_trade_context import PublicExecution

NS = 1_000_000_000
STEP = 10 * NS


def stream(kind, *, gap=(), instrument="ABM", session="simulated-day",
           start=0, end=7*STEP):
    return PublicStreamClaim(
        stream_kind=kind, venue="SIM-EXCHANGE",
        instrument=instrument, session=session, source="public-abides",
        starts_ns=start, complete_through_ns=end, gaps=gap)


def public_tapes():
    book = SimpleNamespace(
        times_ns=[i*STEP+2*NS for i in range(6)],
        bids=[[(100, 30+i*7)] for i in range(6)],
        asks=[[(102, 70-i*7)] for i in range(6)])
    prints = []
    for ordinal in range(1, 7):
        buys = 15+ordinal*10
        prints.append(PublicExecution(ordinal*STEP+3*NS, 102, buys, "BUY"))
        prints.append(PublicExecution(ordinal*STEP+4*NS, 100, 100-buys, "SELL"))
    return book, tuple(prints)


class DualCoverageContractTests(unittest.TestCase):
    def test_separate_book_and_trade_gaps_fail_closed(self):
        book, prints = public_tapes()
        coverage = DualPublicStreamClaim(
            stream("book", gap=((4*STEP,5*STEP),), end=6*STEP),
            stream("trades", gap=((3*STEP,4*STEP),), start=STEP))
        report = summarize_lagged_book(
            book, prints, bin_seconds=10, source_coverage=coverage)
        self.assertEqual(report["populated_execution_clock_bins"], 6)
        self.assertEqual(report["eligible_lagged_bins"], 4)
        self.assertEqual(report["abstained_clock_bins"]["declared_current_trade_stream_uncovered"], 1)
        self.assertEqual(report["abstained_clock_bins"]["declared_previous_book_stream_uncovered"], 1)
        self.assertEqual(sum(report["abstained_clock_bins"].values())+4, 6)
        self.assertEqual(
            [x["current_bin_ordinal"] for x in report["observations"]],
            [1,2,4,6])
        self.assertTrue(report["dual_public_source_claim_supplied"])
        self.assertFalse(report["stream_coverage_independently_verified"])
        self.assertFalse(report["raw_stream_source_identity_verified"])
        self.assertFalse(report["dual_public_source_claim"]["market_completeness_certified"])
        self.assertFalse(report["dual_public_source_claim"]["raw_tape_labels_independently_verified"])

    def test_closed_interval_boundary_and_exclusive_watermark(self):
        book, prints = public_tapes()
        coverage = DualPublicStreamClaim(
            stream("book", end=6*STEP),
            stream("trades", start=STEP, end=7*STEP))
        a = summarize_lagged_book(
            book, prints, bin_seconds=10, source_coverage=coverage)
        b = summarize_lagged_book(
            book, prints, bin_seconds=10, source_coverage=coverage,
            complete_through_ns=6*STEP)
        self.assertEqual(a["eligible_lagged_bins"], 6)
        self.assertEqual(b["eligible_lagged_bins"], 5)
        self.assertEqual(b["abstained_clock_bins"]["current_bin_not_closed_by_watermark"], 1)
        self.assertEqual(a["observations"][:-1], b["observations"])
        self.assertFalse(b["completion_watermark_independently_verified"])
        self.assertFalse(b["real_l2_feed_coverage_proven"])

    def test_adjacent_gaps_do_not_confuse_half_open_windows(self):
        claim = stream("book", gap=((2*STEP,3*STEP),(3*STEP,4*STEP)))
        self.assertTrue(claim.covers(0,2*STEP))
        self.assertFalse(claim.covers(2*STEP,3*STEP))
        self.assertFalse(claim.covers(3*STEP,4*STEP))
        self.assertTrue(claim.covers(4*STEP,5*STEP))
        self.assertFalse(claim.covers(6*STEP,8*STEP))

    def test_cross_instrument_session_venue_and_kind_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            DualPublicStreamClaim(stream("book"),stream("trades",instrument="OTHER"))
        with self.assertRaises(ValueError):
            DualPublicStreamClaim(stream("book"),stream("trades",session="other"))
        with self.assertRaises(ValueError):
            DualPublicStreamClaim(stream("trades"),stream("book"))
        with self.assertRaises(ValueError):
            PublicStreamClaim("book","different","ABM","S","",0,10)

    def test_gap_validation_cannot_swallow_duplicates_bad_types_or_reversed(self):
        for gaps in (
            ((30,20),), ((10,20),(15,30)), ((50,70),(30,40)),
            ((-1,10),), ((0,1000),), ((10,10),),
            ([10,20],), ((10.0,20),), ((10,True),)
        ):
            with self.subTest(gaps=gaps), self.assertRaises(ValueError):
                stream("book",gap=gaps,start=0,end=100)
        for invalid in (True,1.2,"100",-1):
            with self.subTest(val=invalid), self.assertRaises(ValueError):
                stream("book",start=invalid,end=100)

    def test_no_metadata_preserves_legacy_and_marks_unverified(self):
        book, prints = public_tapes()
        result = summarize_lagged_book(book, prints,bin_seconds=10)
        self.assertEqual(result["eligible_lagged_bins"], 6)
        self.assertFalse(result["dual_public_source_claim_supplied"])
        self.assertIsNone(result["dual_public_source_claim"])
        self.assertFalse(result["stream_coverage_independently_verified"])
        self.assertTrue(result["terminal_bin_may_be_partial_without_watermark"])

    def test_non_claim_objects_never_accepted_as_integrity_evidence(self):
        book, prints = public_tapes()
        with self.assertRaises(ValueError):
            summarize_lagged_book(book,prints,bin_seconds=10,source_coverage={
                "coverage_complete":True})
        proper = DualPublicStreamClaim(stream("book"),stream("trades"))
        d = disclose_claim(proper)
        self.assertTrue(d["coverage_is_caller_declared_not_provider_verified"])
        self.assertFalse(d["market_completeness_certified"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
