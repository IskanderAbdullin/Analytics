"""Source-free exact Decimal LOBSTER post-event lag and precision controls."""
from decimal import Decimal as D
import unittest

from tools.public_lobster_clock_lag_audit import (
    source_free_timing_eligibility as audit, audit_pinned_public_demo,
)


def r(t,typ,valid=True):
    return (D(str(t)),typ,valid)


class HistoricalClockLagSourceFreeNegatives(unittest.TestCase):
    def test_current_post_event_book_cannot_help_visible_execution_before_one_second(self):
        x=audit([r("0",1),r(".5",4)])
        self.assertEqual(x["visible_executions_abstain_no_lagged_bbo"],1)
        self.assertFalse(x["post_event_book_used_as_same_event_prestatement"])

    def test_previous_post_event_bbo_eligible_after_one_second(self):
        x=audit([r("0",1),r("1.1",4)])
        self.assertEqual(x["visible_executions_locally_eligible_lagged_bbo"],1)
        self.assertEqual(x["visible_executions_abstain_no_lagged_bbo"],0)

    def test_older_than_ten_seconds_stale_explicit_abstention(self):
        x=audit([r("0",1),r("12",4)])
        self.assertEqual(x["visible_executions_abstain_stale_over_10s"],1)
        self.assertEqual(x["original_event_gaps_strictly_over_10_seconds"],1)

    def test_post_event_invalid_quote_and_hidden_execution_are_separate(self):
        x=audit([r("0",1,False),r("1.1",4),r("1.1",5)])
        self.assertEqual(x["visible_executions_abstain_invalid_post_event_bbo"],1)
        self.assertEqual(x["hidden_type5_executions"],1)
        self.assertEqual(x["exact_same_timestamp_adjacent_event_pairs"],1)

    def test_coarsening_millisecond_merges_distinct_exchange_timestamps_without_authorization(self):
        x=audit([r("0.0001",1),r("0.0009",4)])
        self.assertEqual(x["raw_source_rows_with_submillisecond_decimal_remainder"],2)
        self.assertEqual(x["adjacent_distinct_exact_times_merged_by_millisecond_floor"],1)
        self.assertFalse(x["integer_millisecond_normalization_automatically_approved"])

    def test_exact_millisecond_and_exact_tie_are_different(self):
        x=audit([r("0.001",1),r("0.001",4),r("0.002",4)])
        self.assertEqual(x["raw_source_rows_with_submillisecond_decimal_remainder"],0)
        self.assertEqual(x["exact_same_timestamp_adjacent_event_pairs"],1)
        self.assertEqual(x["distinct_exact_exchange_event_timestamps"],2)

    def test_coverage_conservation_in_multiple_statuses(self):
        x=audit([r("0",1),r("0.5",4),r("1.2",4),r("12.5",4)])
        self.assertEqual(x["visible_type4_executions"],3)
        self.assertEqual(sum(x[k] for k in (
            "visible_executions_locally_eligible_lagged_bbo",
            "visible_executions_abstain_no_lagged_bbo",
            "visible_executions_abstain_stale_over_10s",
            "visible_executions_abstain_invalid_post_event_bbo")),3)
        self.assertFalse(x["real_market_fdr_known"])

    def test_unsorted_non_decimal_invalid_event_type_and_coverage_abstain(self):
        for rows in ([r("2",1),r("1",4)],[(1,4,True)],[r("0",True)],
                     [(D("NaN"),4,True)],[(D("0"),4,1)],[]):
            with self.subTest(rows=repr(rows)),self.assertRaises(ValueError):
                audit(rows)

    def test_original_zip_hash_and_invalid_source_byte_gate(self):
        for raw in (b"invalid",b"",None,b"x"*2):
            with self.subTest(raw=repr(raw)[:40]),self.assertRaises(ValueError):
                audit_pinned_public_demo(raw)

    def test_safe_summary_strict_aggregate_no_raw_source_rows(self):
        x=audit([r("0",1),r("1.1",4)])
        self.assertEqual(x["paired_source_event_book_rows"],2)
        for forbidden in ("order_id","event_timestamp_list","event_rows","book_rows","agent_id"):
            self.assertNotIn(forbidden,x)
        self.assertFalse(x["raw_vendor_rows_or_order_references_exported"])


if __name__=="__main__":
    unittest.main()
