#!/usr/bin/env python3
"""Research-only event-time L2 features: exact negative, schema and conservation."""
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"tools"))

from lobster_event_time_features import (
    event_time_features, OUTPUT_ALLOWED_TOP_FIELDS,
    LOCALLY_PINNED_SAMPLE_SHA256,
)
from test_lobster_public_sample_format_audit import (
    archive, book_row, MSG, DUMMY_ASK, DUMMY_BID
)


class RealL2EventTimeSyntheticTests(unittest.TestCase):
    def test_event_time_counts_correct_resting_side_and_safe_source_only_output(self):
        raw=archive()
        result=event_time_features(raw)
        self.assertEqual(set(result),OUTPUT_ALLOWED_TOP_FIELDS)
        self.assertEqual(result["schema_version"],
                         "lobster-event-time-10level-descriptive-replay-v1")
        self.assertEqual(result["event_count"],5)
        self.assertEqual(result["paired_l2_post_event_states"],5)
        self.assertEqual(result["event_type_counts"]["1"],1)
        self.assertEqual(result["event_type_counts"]["4"],2)
        self.assertEqual(result["visible_aggressor_buy_executions"],1)
        self.assertEqual(result["visible_aggressor_sell_executions"],1)
        self.assertEqual(result["hidden_executions_resting_side_not_aggressor"],1)
        self.assertEqual(result["distinct_event_timestamp_groups"],4)
        self.assertEqual(result["same_timestamp_repeated_event_pairs"],1)
        self.assertEqual(result["max_events_in_one_exact_timestamp_group"],2)
        self.assertEqual(result["event_time_gap_zero"],1)
        self.assertEqual(result["event_time_gap_positive"],3)
        self.assertEqual(result["max_positive_event_gap_seconds"],"0.001")
        self.assertEqual(result["half_hour_event_counts"][0],5)
        self.assertEqual(sum(result["half_hour_event_counts"]),5)
        self.assertEqual(len(result["half_hour_event_counts"]),13)
        self.assertEqual(result["valid_two_sided_quote_events"],5)
        self.assertEqual(result["mean_event_weighted_spread_x10000"],1000)
        self.assertEqual(result["mean_event_weighted_top_depth_shares"],190)
        self.assertEqual(result["mean_event_weighted_top_two_level_depth_shares"],380)
        self.assertAlmostEqual(result["mean_event_weighted_top_imbalance"],-10/190)
        self.assertEqual(result["top_bid_ask_price_change_after_event"],0)
        self.assertEqual(result["top_bid_ask_size_change_after_event"],0)
        self.assertEqual(result["number_of_events_without_prior_snapshot_for_prepost_comparison"],1)
        self.assertFalse(result["original_locally_pinned_sha256_matched"])
        self.assertEqual(result["locally_observed_source_zip_sha256"],sha256(raw).hexdigest())
        for no_claim in (
            "provider_signed_checksum_available",
            "raw_event_rows_exported", "source_order_reference_ids_exported",
            "event_timestamp_or_price_series_exported",
            "individual_agent_labels_available",
            "real_market_robot_accuracy_or_FDR_calibrated",
            "commercial_trade_or_signal_authorized"
        ):
            self.assertFalse(result[no_claim],no_claim)
        self.assertTrue(result["post_event_snapshot_semantics"])
        self.assertTrue(result["same_timestamp_order_of_events_preserved"])
        self.assertTrue(result["not_complete_market_depth"])

    def test_quote_changes_use_previous_post_event_snapshot_not_current_pre(self):
        rows=[
            book_row(ask=1186000,bid=1185000),
            book_row(ask=1186100,bid=1185000),
            book_row(ask=1186100,bid=1184900),
            book_row(ask=1186100,bid=1184900),
            book_row(ask=1186100,bid=1184900),
        ]
        result=event_time_features(archive(books=rows))
        self.assertEqual(result["top_bid_ask_price_change_after_event"],2)
        self.assertEqual(result["visible_execution_prepost_quote_price_change"],2)
        self.assertEqual(result["nonexecution_prepost_quote_price_change"],0)
        self.assertEqual(result["same_timestamp_prepost_quote_price_change"],1)
        self.assertEqual(result["top_bid_ask_size_change_after_event"],0)
        self.assertEqual(result["both_quote_price_and_size_change_after_event"],0)
        self.assertEqual(result["number_of_events_without_prior_snapshot_for_prepost_comparison"],1)
        self.assertTrue(result["post_event_snapshot_semantics"])
        self.assertFalse(result["real_market_robot_accuracy_or_FDR_calibrated"])

    def test_size_and_quote_change_independent(self):
        rows=[book_row().split(",") for _ in MSG]
        rows[1][1]="150"   # top ask grows with unchanged price
        rows[2][0]="1186050"  # top ask changes without breaking ten-level quote order
        rows[2][1]="150"
        rows[3]=rows[2].copy()
        rows[4]=rows[2].copy()
        result=event_time_features(archive(books=[",".join(r) for r in rows]))
        self.assertEqual(result["top_bid_ask_price_change_after_event"],1)
        self.assertEqual(result["top_bid_ask_size_change_after_event"],1)
        self.assertEqual(result["both_quote_price_and_size_change_after_event"],0)
        self.assertEqual(result["visible_execution_prepost_quote_price_change"],1)

    def test_all_event_identifiers_are_excluded_from_export_and_statistics(self):
        changed=[]
        for row in MSG:
            fields=row.split(",")
            fields[2]="7777777777777"
            changed.append(",".join(fields))
        original=event_time_features(archive())
        modified=event_time_features(archive(messages=changed))
        drop={"locally_observed_source_zip_sha256"}
        for key in original:
            if key not in drop:
                self.assertEqual(original[key], modified[key],key)
        self.assertNotEqual(original["locally_observed_source_zip_sha256"],
                            modified["locally_observed_source_zip_sha256"])

    def test_same_timestamp_groups_keep_event_conservation_and_do_not_infer_owners(self):
        rows=[
            "34200.000,1,1,10,1186000,-1",
            "34200.000,1,2,10,1186000,-1",
            "34200.000,4,3,10,1186000,-1",
            "34200.000,4,4,10,1186000,-1",
            "34200.000,4,5,10,1186000,-1",
        ]
        report=event_time_features(archive(messages=rows))
        self.assertEqual(report["distinct_event_timestamp_groups"],1)
        self.assertEqual(report["max_events_in_one_exact_timestamp_group"],5)
        self.assertEqual(report["event_time_gap_zero"],4)
        self.assertEqual(report["visible_aggressor_buy_executions"],3)
        self.assertEqual(report["top_bid_ask_price_change_after_event"],0)
        self.assertFalse(report["individual_agent_labels_available"])

    def test_missing_quote_state_counted_without_misleading_spread(self):
        noquote = ",".join(str(v) for i in range(10)
            for v in (DUMMY_ASK,0,DUMMY_BID,0))
        rows=[book_row(),noquote,book_row(),noquote,book_row()]
        report=event_time_features(archive(books=rows))
        self.assertEqual(report["one_sided_or_missing_quote_events"],2)
        self.assertEqual(report["valid_two_sided_quote_events"],3)
        self.assertEqual(report["top_bid_ask_price_change_after_event"],4)
        self.assertIsNotNone(report["mean_event_weighted_spread_x10000"])

    def test_strict_local_source_pinning_is_opt_in_and_never_provider_signed(self):
        self.assertEqual(len(LOCALLY_PINNED_SAMPLE_SHA256),64)
        with self.assertRaises(ValueError):
            event_time_features(archive(),require_original_sha=True)
        for bad in (1,0,"yes",None):
            with self.subTest(flag=bad),self.assertRaises(ValueError):
                event_time_features(archive(),require_original_sha=bad)

    def test_empty_malformed_wrong_row_count_and_size_cap_fail_closed(self):
        for raw in (
            b"", b"not zip",archive(messages=MSG[:1]+["34200.003,4"]),
            archive(messages=MSG[:1],books=[book_row(),book_row()]),
        ):
            with self.subTest(size=len(raw)),self.assertRaises(ValueError):
                event_time_features(raw)
        with patch("lobster_event_time_features.MAX_ROWS",4):
            with self.assertRaises(ValueError):
                event_time_features(archive())

    def test_no_network_or_trade_method_in_replay(self):
        with patch("lobster_event_time_features.download_exact_demo") as net:
            summary=event_time_features(archive())
            self.assertEqual(summary["event_count"],5)
            net.assert_not_called()
        self.assertFalse(summary["commercial_trade_or_signal_authorized"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
