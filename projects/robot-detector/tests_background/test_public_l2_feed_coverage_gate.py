#!/usr/bin/env python3
"""Adversarial source event and post-event book observability gates."""
from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from public_l2_feed_coverage_gate import (
    PublicFrame, analyze_coverage, SESSION_START_US
)


def synthetic_frames():
    return tuple(PublicFrame(
        SESSION_START_US+i*1_000_000,
        SESSION_START_US+i*1_000_000,
        200+i,1186000,1185000
    ) for i in range(5))


class L2CoverageAbstentionTests(unittest.TestCase):
    def test_only_synthetic_oracle_boundary_can_pass_contiguous_coverage(self):
        full=synthetic_frames()
        result=analyze_coverage(
            full,trusted_synthetic_expected_sequence_range=(200,204))
        self.assertEqual(result["status"],"SYNTHETIC_COVERAGE_ELIGIBLE_ONLY")
        self.assertEqual(result["observed_frame_count"],5)
        self.assertEqual(result["source_expected_total_events_if_oracle_attested"],5)
        self.assertEqual(result["source_sequence_coverage_fraction_if_oracle_attested"],1)
        self.assertEqual(result["event_book_timestamp_aligned_count"],5)
        self.assertEqual(result["two_sided_noncrossed_book_count"],5)
        self.assertEqual(result["reason_codes"],[])
        self.assertFalse(result["unattested_real_source_completeness_declared"])
        self.assertFalse(result["physical_robot_owner_accuracy_or_market_FDR_calibrated"])
        self.assertFalse(result["real_trading_or_order_placement_authorized"])
        self.assertFalse(result["raw_market_frames_or_order_ids_exported"])

    def test_real_like_public_stream_without_independent_provenance_stays_unknown(self):
        known_frames=synthetic_frames()
        r=analyze_coverage(known_frames)
        self.assertEqual(r["status"],"UNKNOWN_SOURCE_COMPLETENESS")
        self.assertEqual(r["distinct_observed_sequence_ids"],5)
        self.assertEqual(r["source_expected_total_events_if_oracle_attested"],None)
        self.assertEqual(r["source_sequence_coverage_fraction_if_oracle_attested"],None)
        no_sequence=tuple(replace(x,source_event_sequence=None)
                          for x in known_frames)
        r=analyze_coverage(no_sequence)
        self.assertEqual(r["status"],"UNKNOWN_SOURCE_COMPLETENESS")
        self.assertIn("MISSING_EVENT_SEQUENCE",r["reason_codes"])
        self.assertEqual(r["distinct_observed_sequence_ids"],0)
        self.assertIsNone(r["source_sequence_coverage_fraction_if_oracle_attested"])
        self.assertFalse(r["unattested_real_source_completeness_declared"])

    def test_missing_sequence_abstains_with_explicit_known_denominator(self):
        all_frames=synthetic_frames()
        partial=all_frames[:2]+all_frames[3:]
        r=analyze_coverage(
            partial,trusted_synthetic_expected_sequence_range=(200,204))
        self.assertEqual(r["status"],"ABSTAIN_SOURCE_OR_BOOK_INTEGRITY")
        self.assertEqual(r["missing_sequence_ids_in_observed_range"],1)
        self.assertIn("GAP_IN_OBSERVED_EVENT_SEQUENCE",r["reason_codes"])
        self.assertIn("TRUSTED_SOURCE_BOUNDARY_MISMATCH",r["reason_codes"])
        self.assertEqual(r["source_sequence_coverage_fraction_if_oracle_attested"],0.8)
        self.assertEqual(r["source_expected_total_events_if_oracle_attested"],5)

    def test_duplicate_reordered_or_partial_source_ids_cannot_pass(self):
        variants=(
            (synthetic_frames()[:2]+(replace(synthetic_frames()[2],
                        source_event_sequence=201),)+synthetic_frames()[3:],
             "DUPLICATE_EVENT_SEQUENCE"),
            (synthetic_frames()[:2]+(replace(synthetic_frames()[2],
                        source_event_sequence=199),)+synthetic_frames()[3:],
             "REVERSED_EVENT_SEQUENCE"),
            (synthetic_frames()[:2]+(replace(synthetic_frames()[2],
                        source_event_sequence=None),)+synthetic_frames()[3:],
             "PARTIAL_EVENT_SEQUENCE"),
        )
        for rows,why in variants:
            with self.subTest(reason=why):
                r=analyze_coverage(
                    rows,trusted_synthetic_expected_sequence_range=(200,204))
                self.assertEqual(r["status"],"ABSTAIN_SOURCE_OR_BOOK_INTEGRITY")
                self.assertIn(why,r["reason_codes"])
                self.assertFalse(r["unattested_real_source_completeness_declared"])

    def test_missing_or_desynchronised_book_cannot_be_scored_as_complete(self):
        source=synthetic_frames()
        for altered,reason in (
            (replace(source[2],book_time_us=None),"BOOK_ROW_MISSING"),
            (replace(source[2],book_time_us=source[2].book_time_us+100),
             "EVENT_AND_BOOK_TIMESTAMP_DIFFER"),
            (replace(source[2],best_ask_price_x10000=None),"TOP_OF_BOOK_UNAVAILABLE"),
            (replace(source[2],best_bid_price_x10000=1186000),
             "LOCKED_OR_CROSSED_BOOK"),
        ):
            rows=source[:2]+(altered,)+source[3:]
            with self.subTest(reason=reason):
                r=analyze_coverage(
                    rows,trusted_synthetic_expected_sequence_range=(200,204))
                self.assertEqual(r["status"],"ABSTAIN_SOURCE_OR_BOOK_INTEGRITY")
                self.assertIn(reason,r["reason_codes"])
                self.assertEqual(r["source_sequence_coverage_fraction_if_oracle_attested"],1)
                # A full event count alone is not proof of valid aligned L2.
                self.assertFalse(r["unattested_real_source_completeness_declared"])

    def test_quote_staleness_without_a_sequence_gap_still_causes_abstention(self):
        f=tuple(PublicFrame(SESSION_START_US+int(i*31_000_000),
                            SESSION_START_US+int(i*31_000_000),
                            100+i,1186000,1185000) for i in range(3))
        r=analyze_coverage(
            f,trusted_synthetic_expected_sequence_range=(100,102))
        self.assertEqual(r["missing_sequence_ids_in_observed_range"],0)
        self.assertEqual(r["observed_previous_quote_holds_over_30s"],2)
        self.assertIn("QUOTE_HOLD_EXCEEDS_30_SECONDS",r["reason_codes"])
        self.assertEqual(r["status"],"ABSTAIN_SOURCE_OR_BOOK_INTEGRITY")

    def test_timestamp_reversal_with_ascending_source_sequence_fails(self):
        source=synthetic_frames()
        rev=replace(source[2],event_time_us=SESSION_START_US,
                    book_time_us=SESSION_START_US)
        rows=source[:2]+(rev,)+source[3:]
        result=analyze_coverage(rows,
            trusted_synthetic_expected_sequence_range=(200,204))
        self.assertIn("EVENT_TIMESTAMP_REGRESSION",result["reason_codes"])
        self.assertEqual(result["status"],"ABSTAIN_SOURCE_OR_BOOK_INTEGRITY")

    def test_zero_timestamp_gap_not_confused_with_missing_sequence(self):
        data=synthetic_frames()
        e=replace(data[2],event_time_us=data[1].event_time_us,
                  book_time_us=data[1].book_time_us)
        rows=data[:2]+(e,)+data[3:]
        report=analyze_coverage(rows,
            trusted_synthetic_expected_sequence_range=(200,204))
        self.assertEqual(report["status"],"SYNTHETIC_COVERAGE_ELIGIBLE_ONLY")
        self.assertEqual(report["same_exchange_time_adjacent_event_pairs"],1)
        self.assertEqual(report["missing_sequence_ids_in_observed_range"],0)

    def test_no_synthetic_truth_licence_or_unbounded_results(self):
        for bad_expected in ((200,100),(True,204),(-1,204),
                             (0,200001),[200,204],"200..204"):
            with self.subTest(expected=str(bad_expected)),self.assertRaises(ValueError):
                analyze_coverage(synthetic_frames(),
                    trusted_synthetic_expected_sequence_range=bad_expected)
        with self.assertRaises(ValueError):
            analyze_coverage(tuple())
        with self.assertRaises(ValueError):
            analyze_coverage(tuple({} for _ in range(3)))
        invalid=replace(synthetic_frames()[0],source_event_sequence=True)
        with self.assertRaises(ValueError):
            analyze_coverage((invalid,))

    def test_total_coverage_cannot_be_deduced_from_vendor_order_reference_count(self):
        # Same real-looking order reference may appear in multiple
        # executions; it must NEVER substitute for a source event sequence.
        f=synthetic_frames()
        absent_seq=tuple(replace(x,source_event_sequence=None) for x in f)
        result=analyze_coverage(absent_seq)
        self.assertIsNone(result["source_expected_total_events_if_oracle_attested"])
        self.assertIsNone(result["source_sequence_coverage_fraction_if_oracle_attested"])
        self.assertFalse(result["source_missing_events_proven_absent_from_unattested_data"])
        self.assertFalse(result["physical_robot_owner_accuracy_or_market_FDR_calibrated"])

if __name__=="__main__":
    unittest.main(verbosity=2)
