"""Precommitted old CSV nanosecond loss bias in frozen public source-free LL."""
from math import log
import json
import unittest

from tools.abides_export import _date_utc
from tools.public_abides_m1v4_nontarget_panel import _ns
from tools.public_abides_export_precision_ll import abides_lossy_us_clock_LL_falsifier as panel


class ABIDESExactNsVsCsvMicrosecondsLLNegativeTests(unittest.TestCase):
    def test_source_free_3_fixed_clock_cases_all_retained(self):
        a=panel()
        self.assertEqual(len(a["cases"]),3)
        self.assertEqual([x["constructed_source_free_case"] for x in a["cases"]],[
            "ONE_EXACT_NS_EXEC",
            "TWO_EXACT_SAME_NS_SPLIT_FILLS",
            "TWO_SOURCE_EVENTS_ONE_NS_APART",
        ])

    def test_exact_ns_same_timestamp_multi_fills_model_invariant(self):
        a,b=panel()["cases"][:2]
        self.assertEqual((a["exact_distinct_ns_public_clusters"],
                          b["exact_distinct_ns_public_clusters"]),(1,1))
        self.assertEqual(b["source_public_executions"],2)
        self.assertEqual((a["M0_LL"],a["M1v4_LL"]),(b["M0_LL"],b["M1v4_LL"]))

    def test_adjacent_1ns_two_clusters_but_one_exported_microsecond(self):
        b,c=panel()["cases"][1:]
        self.assertEqual(c["exact_distinct_ns_public_clusters"],2)
        self.assertEqual(c["old_csv_distinct_microsecond_text_timestamps"],1)
        self.assertEqual(_ns("34222.500000001")-_ns("34222.5"),1)
        self.assertEqual(_date_utc(_ns("34222.5")),_date_utc(_ns("34222.500000001")))

    def test_existing_exporter_preserves_one_microsecond_difference(self):
        self.assertNotEqual(_date_utc(_ns("34222.5")),
                            _date_utc(_ns("34222.500001")))
        self.assertEqual(_ns("34222.500001")-_ns("34222.5"),1000)

    def test_extra_one_ns_public_cluster_changes_models_by_frozen_logs(self):
        r=panel()
        self.assertAlmostEqual(r["M0_LL_one_extra_distinct_ns_cluster_delta"],log(.625),places=12)
        self.assertAlmostEqual(r["M1v4_LL_one_extra_distinct_ns_cluster_delta"],log(.75),places=12)
        self.assertAlmostEqual(r["conditional_minus_constant_LL_change_due_to_1ns_clock_distinction"],
                               log(.75/.625),places=12)
        self.assertGreater(r["conditional_minus_constant_LL_change_due_to_1ns_clock_distinction"],0)

    def test_compensators_are_unchanged_by_time_cluster_multiplicity(self):
        x=panel()["cases"]
        self.assertEqual([row["M0_complete_time_integral"] for row in x],[2.5]*3)
        self.assertEqual([row["M1v4_complete_time_integral"] for row in x],[2.875]*3)

    def test_no_original_160_source_corruption_or_new_original_source_claims(self):
        a=panel()
        self.assertFalse(a["old_160_original_matching_engine_used_legacy_CSV_for_source_scoring"])
        self.assertFalse(a["actual_original_ABIDES_submicrosecond_collisions_measured"])
        self.assertEqual(a["original_matching_engine_source_worlds_generated"],0)
        self.assertFalse(a["physical_owner_identity_known"])
        self.assertFalse(a["real_market_fdr_known"])

    def test_output_only_aggregate_does_not_leak_trade_times_prices_or_ids(self):
        s=json.dumps(panel(),sort_keys=True)
        for key in ('"epoch_ns"','"timestamp_ns"','"bid_cents"',
                    '"ask_cents"','"agent_id"','"order_id"','"private_truth"'):
            self.assertNotIn(key,s)


if __name__=="__main__":
    unittest.main()
