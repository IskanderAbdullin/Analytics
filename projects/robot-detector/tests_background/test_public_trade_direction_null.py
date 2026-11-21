import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from public_trade_direction_null import (
    evaluate_public_side_null, PHASES_SECONDS, NULL_SEEDS, DAY_US
)

def example():
    # One-sided first 30s, sell-only second 30s, same 60s minute.
    # Crossing an origin at 10s or 20s changes eligible event membership.
    return [(1_000_000,False),(2_000_000,False),(3_000_000,False),
            (33_000_000,True),(34_000_000,True),(35_000_000,True),
            (65_000_000,False),(65_000_000,False),(70_000_000,True)]

class MinutePreservingControlTests(unittest.TestCase):
    def test_preregistered_controls_reproducible_and_no_owner_claim(self):
        a=evaluate_public_side_null(example(),utc_day_start_us=0)
        b=evaluate_public_side_null(example(),utc_day_start_us=0)
        self.assertEqual(a,b)
        self.assertEqual(a["source_event_count"],9)
        self.assertEqual(a["clock_phases_seconds"],[0,10,20])
        self.assertEqual(len(a["variants"]),3)
        self.assertFalse(a["physical_robot_identification_validated"])
        self.assertFalse(a["market_false_discovery_rate_calibrated"])
        self.assertFalse(a["commercial_or_live_trading_allowed"])
        self.assertFalse(a["raw_print_timestamps_or_labels_exported"])
        for variant in a["variants"]:
            self.assertEqual(variant["predeclared_null_seeds"],list(NULL_SEEDS))
            self.assertEqual(variant["num_predeclared_weak_null_replicates"],8)
            self.assertLessEqual(variant["null_one_sided_bin_count_min"],
                                 variant["null_one_sided_bin_count_median"])
            self.assertLessEqual(variant["null_one_sided_bin_count_median"],
                                 variant["null_one_sided_bin_count_max"])
            self.assertFalse(variant["statistical_p_value_or_FDR_calibrated"])
        self.assertEqual(a["variants"][0]["observed_one_sided_bins"],2)

    def test_clock_phase_membership_and_source_boundary_exclusion(self):
        rows=example()+[(DAY_US-1,False)]
        report=evaluate_public_side_null(rows,utc_day_start_us=0)
        self.assertEqual([x["complete_utc_clock_bins"] for x in report["variants"]],
                         [2880,2879,2879])
        self.assertEqual([x["excluded_utc_edge_prints"] for x in report["variants"]],
                         [0,4,4])
        self.assertEqual([x["observed_prints_in_full_bins"] for x in report["variants"]],
                         [10,6,6])

    def test_translation_invariance_of_absolute_utc_clock(self):
        first=evaluate_public_side_null(example(),utc_day_start_us=0)
        shifted=[(t+1800000000000,s) for t,s in example()]
        second=evaluate_public_side_null(shifted,utc_day_start_us=1800000000000)
        self.assertEqual(first,second)

    def test_known_participant_count_not_derived_from_any_control(self):
        all_buy=[(i*1000000,False) for i in range(120)]
        r=evaluate_public_side_null(all_buy,utc_day_start_us=0)
        self.assertEqual(r["variants"][0]["observed_one_sided_bins"],4)
        self.assertEqual(r["variants"][0]["null_one_sided_bin_count_min"],4)
        self.assertEqual(r["variants"][0]["null_one_sided_bin_count_max"],4)
        self.assertFalse(r["physical_robot_identification_validated"])

    def test_pinned_real_provider_replay_scalars_never_imply_owners(self):
        import json
        path=(Path(__file__).resolve().parents[1]/"fixtures"
              /"binance_spot_weak_direction_nulls_20261121.json")
        item=json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(item["original_run_id"],44918585645)
        self.assertEqual(item["actual_distinct_utc_market_days"],2)
        self.assertEqual(item["shuffles_per_day"],len(NULL_SEEDS))
        self.assertTrue(item["experiments_after_the_two_market_days_were_already_inspected"])
        self.assertTrue(item["no_physical_bot_count_or_real_market_fdr"])
        self.assertEqual(item["phase_offsets_seconds"],[0,10,20])
        self.assertEqual(sum(c["source_public_prints"] for c in item["cases"]),278403)
        for source in item["cases"]:
            self.assertEqual(len(source["provider_zip_sha256"]),64)
            self.assertEqual([p["origin_seconds"] for p in source["phases"]],[0,10,20])
            for phase in source["phases"]:
                self.assertGreater(phase["observed_one_sided"],phase["weak_null_max"])
                self.assertLessEqual(phase["weak_null_min"],phase["weak_null_median"])
                self.assertLessEqual(phase["weak_null_median"],phase["weak_null_max"])

    def test_exact_timestamp_clusters_are_preserved_as_joint_vectors(self):
        # Equal-size groups at distinct timestamps within the *same*
        # minute. The stronger null may swap whole 3-print vectors, never
        # mix BUY and SELL inside one of the two source timestamps.
        rows=[(5_000_000,False)]*3 + [(35_000_000,True)]*3
        strict=evaluate_public_side_null(
            rows,utc_day_start_us=0,preserve_same_timestamp_clusters=True)
        weak=evaluate_public_side_null(rows,utc_day_start_us=0)
        self.assertTrue(strict["same_timestamp_side_vector_clusters_preserved"])
        self.assertFalse(weak["same_timestamp_side_vector_clusters_preserved"])
        self.assertEqual(strict["variants"][0]["observed_one_sided_bins"],2)
        self.assertEqual(strict["variants"][0]["null_one_sided_bin_count_min"],2)
        self.assertEqual(strict["variants"][0]["null_one_sided_bin_count_max"],2)
        self.assertLess(weak["variants"][0]["null_one_sided_bin_count_min"],2)
        self.assertEqual(strict["source_event_count"],6)
        self.assertFalse(strict["market_false_discovery_rate_calibrated"])
        self.assertFalse(strict["physical_robot_identification_validated"])

    def test_cluster_preserving_controls_still_conserve_three_origin_source_events(self):
        rows=example()+[(DAY_US-1,False)]
        strict=evaluate_public_side_null(
            rows,utc_day_start_us=0,preserve_same_timestamp_clusters=True)
        self.assertEqual([r["excluded_utc_edge_prints"] for r in strict["variants"]],
                         [0,4,4])
        self.assertEqual([r["observed_prints_in_full_bins"] for r in strict["variants"]],
                         [10,6,6])
        self.assertEqual(strict["variants"][0]["num_predeclared_weak_null_replicates"],8)
        self.assertTrue(strict["same_timestamp_side_vector_clusters_preserved"])
        for wrong in (0,1,"yes",None):
            with self.assertRaises(ValueError):
                evaluate_public_side_null(rows,utc_day_start_us=0,
                    preserve_same_timestamp_clusters=wrong)

    def test_invalid_public_payload_and_source_bounds_fail_closed(self):
        rows=example()
        for bad in (
            [],None,tuple(rows),rows[:2]+[(500_000,True)]+rows[3:],
            rows+[(DAY_US,False)],[(True,False)],[(1.0,False)],
            [(0,1)],[(0,None)],[("0",False)],[(0,"SELL")],
        ):
            with self.subTest(bad=str(bad)[:40]),self.assertRaises(ValueError):
                evaluate_public_side_null(bad,utc_day_start_us=0)
        for start in (True,1.0,-1):
            with self.assertRaises(ValueError):
                evaluate_public_side_null(rows,utc_day_start_us=start)

if __name__=="__main__":
    unittest.main(verbosity=2)
