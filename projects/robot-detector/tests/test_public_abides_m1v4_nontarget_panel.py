"""Preregistered ABIDES non-target LL, including positive spurious gain."""
from math import log
import json
import unittest

from tools.public_abides_m1v4_nontarget_panel import (
    fixed_nontarget_public_panel_aggregate as panel,
)


class ABIDESSourceFreeNonTargetLLFalsifierTests(unittest.TestCase):
    def test_all_three_non_target_original_constructed_cases_retained(self):
        a=panel()
        self.assertEqual(a["source_free_constructed_case_count"],3)
        self.assertEqual([x["constructed_non_target_case"] for x in a["cases"]],[
            "SINGLE_PUBLIC_LOW_CLUSTER",
            "UNRELATED_REGULAR_LOW_CLUSTER_BACKGROUND",
            "UNRELATED_MOMENTUM_LIKE_HIGH_CLUSTER_BURST"])
        self.assertTrue(a["all_precommitted_public_background_cases_reported"])

    def test_single_low_cluster_source_free_m1_worse(self):
        a=panel()["cases"][0]
        self.assertEqual(a["public_unique_execution_timestamp_clusters"],1)
        self.assertAlmostEqual(a["M1v4_minus_M0_LL"],log(.75/.625)-.375,places=12)
        self.assertLess(a["M1v4_minus_M0_LL"],0)

    def test_regular_non_target_can_improve_M1_LL_without_bots(self):
        a=panel()["cases"][1]
        self.assertEqual(a["public_unique_execution_timestamp_clusters"],3)
        self.assertAlmostEqual(a["M1v4_minus_M0_LL"],3*log(.75/.625)-.375,places=12)
        self.assertGreater(a["M1v4_minus_M0_LL"],0)
        self.assertFalse(a["pattern_classifier_label_calibrated"])

    def test_high_microburst_non_target_m1_worse(self):
        a=panel()["cases"][2]
        self.assertEqual(a["public_unique_execution_timestamp_clusters"],3)
        self.assertAlmostEqual(a["M1v4_minus_M0_LL"],3*log(.5/.625)-.375,places=12)
        self.assertLess(a["M1v4_minus_M0_LL"],-1.)

    def test_same_public_tape_unobserved_owner_story_invariant(self):
        a=panel()
        self.assertTrue(a["same_public_tape_under_different_unobserved_owner_stories_has_same_score"])
        self.assertFalse(a["actual_market_owner_count_known"])

    def test_no_owner_probability_or_real_market_fdr_created(self):
        a=panel()
        self.assertTrue(a["source_model_predictions_are_not_robot_classifications"])
        self.assertFalse(a["real_market_fdr_known"])
        self.assertFalse(a["source_feed_completeness_externally_verified"])
        self.assertEqual(a["original_independent_ABIDES_engine_source_cases_generated"],0)

    def test_only_aggregate_allows_no_raw_public_timestamps_or_prices(self):
        x=json.dumps(panel(),sort_keys=True)
        for forbidden in ('"epoch_ns"','"agent_id"','"order_id"','"bid_cents"',
                          '"ask_cents"','"price_cents"','"raw_trade_rows"'):
            self.assertNotIn(forbidden,x)

    def test_all_cases_have_same_full_observation_integral(self):
        a=panel()["cases"]
        self.assertEqual(len({round(x["M1v4_full_window_LL"]-
                                 x["M0_full_window_LL"],10) for x in a}),3)
        self.assertTrue(all(x["physical_owner_identity_known"] is False for x in a))


if __name__=="__main__":
    unittest.main()
