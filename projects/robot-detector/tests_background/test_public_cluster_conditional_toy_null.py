"""Exact cluster-size-preserving toy conditional null, without market FDR claims."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from public_cluster_conditional_toy_null import (
    frozen_plan, exhaustive_public_cluster_placements, N_TIMES, TOTAL_FILLS,
    FROZEN_CLUSTER_SIZES
)


class ClusterConditionalNullAdversarialTests(unittest.TestCase):
    def test_original_frozen_all_thirteen_placements_and_only_toy_scope(self):
        p=frozen_plan()
        self.assertEqual(p["exhaustive_permutation_count"],13)
        self.assertEqual(p["cluster_cardinality_multiset"],[1]*12+[100])
        self.assertEqual(p["fixed_grid_periods_seconds"],[20,45])
        self.assertEqual(p["ratio_threshold"],0.60)
        self.assertTrue(p["no_random_seeds_or_sampling_required"])
        self.assertTrue(p["tail_frequency_is_toy_conditional_not_market_p_value_or_FDR"])
        self.assertTrue(p["all_13_placements_required_even_if_non_alarm"])
        self.assertEqual(len(FROZEN_CLUSTER_SIZES),N_TIMES)
        self.assertEqual(sum(FROZEN_CLUSTER_SIZES),TOTAL_FILLS)

    def test_exact_source_free_public_tape_counts_and_group_invariance(self):
        r=exhaustive_public_cluster_placements()
        self.assertEqual(r["schema_version"],"public-cluster-permutation-toy-null-original-v1")
        self.assertEqual(r["exact_exchangeable_cluster_placements"],13)
        self.assertEqual(len(r["all_placements"]),13)
        self.assertEqual({x["synthetic_placement_ordinal"] for x in r["all_placements"]},
                         set(range(13)))
        self.assertEqual(r["large_cluster_position_categories"],
                         {"20_only":11,"both":1,"45_only":1})
        self.assertEqual(r["print_weighted_false_alarms_under_toy_no_target"],2)
        self.assertEqual(r["grouped_timestamp_false_alarms_under_toy_no_target"],0)
        self.assertAlmostEqual(r["toy_exchangeable_placement_alarm_frequency"],2/13)
        for x in r["all_placements"]:
            self.assertEqual(x["public_execution_prints"],112)
            self.assertEqual(x["unique_timestamps"],13)
            self.assertEqual(x["grouped_unique_timestamp_ratio"],round(2/12,8))
            self.assertFalse(x["grouped_unique_timestamp_alarm"])
            self.assertFalse(x["source_owner_labels_known"])
        self.assertFalse(r["phase_or_threshold_fitted_posthoc"])
        self.assertFalse(r["no_source_raw_public_timestamp_series_exported"] is False)
        self.assertTrue(r["not_a_real_market_p_value_or_FDR"])
        self.assertTrue(r["no_owner_or_parent_order_identity_recovered"])
        self.assertTrue(r["source_constructed_not_original_market_or_ABIDES"])

    def test_one_hundred_prints_at_45_only_timestamp_produce_false_alarm(self):
        r=exhaustive_public_cluster_placements()
        by_cat={}
        for x in r["all_placements"]:
            by_cat.setdefault(x["large_cluster_grid_category"],[]).append(x)
        x=by_cat["45_only"][0]
        self.assertEqual(x["print_weighted_grid20_hits"],12)
        self.assertEqual(x["print_weighted_grid45_hits"],101)
        self.assertAlmostEqual(x["print_weighted_ratio"],101/12)
        self.assertTrue(x["print_weighted_threshold_alarm"])
        both=by_cat["both"][0]
        self.assertEqual((both["print_weighted_grid20_hits"],
                          both["print_weighted_grid45_hits"]),(111,101))
        self.assertAlmostEqual(both["print_weighted_ratio"],101/111)
        self.assertTrue(both["print_weighted_threshold_alarm"])
        for x in by_cat["20_only"]:
            self.assertEqual((x["print_weighted_grid20_hits"],
                              x["print_weighted_grid45_hits"]),(111,2))
            self.assertAlmostEqual(x["print_weighted_ratio"],2/111)
            self.assertFalse(x["print_weighted_threshold_alarm"])

    def test_no_raw_timestamp_or_agent_owner_id_emitted(self):
        r=exhaustive_public_cluster_placements()
        s=json.dumps(r)
        for forbidden in (
            "private_agent_id","aggressive_agent_id",
            "passive_agent_id","physical_owner_id",
            "order_reference","raw_market_trade","time_ns"
        ):
            with self.subTest(name=forbidden):
                self.assertNotIn('"'+forbidden+'"',s)
        self.assertFalse(r["original_market_trading_or_broker_placement_enabled"])
        self.assertTrue(r["no_source_raw_public_timestamp_series_exported"])

    def test_modified_frozen_protocol_is_rejected_not_optimized(self):
        p=frozen_plan()
        cases=(
            ("ratio_threshold",0.8),
            ("fixed_grid_periods_seconds",[20,40]),
            ("exhaustive_permutation_count",12),
            ("cluster_cardinality_multiset",[1]*12+[99]),
            ("all_13_placements_required_even_if_non_alarm",False),
            ("timestamp_support_unchanged",False),
            ("no_best_grid_phase_or_threshold_selection",False),
        )
        for key,value in cases:
            broken=deepcopy(p)
            broken[key]=value
            with self.subTest(key=key),patch.object(
                Path,"read_text",return_value=json.dumps(broken)
            ),self.assertRaises(ValueError):
                frozen_plan()

if __name__=="__main__":
    unittest.main(verbosity=2)
