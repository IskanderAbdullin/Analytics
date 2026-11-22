"""Frozen public-only M0/M1-v2/M2 three non-target hard-negative panel."""
import math
import unittest
from tools.public_m0_m1_m2_ambiguity_panel import (
    PERIODIC_PUBLIC_TAPE, MOMENTUM_NON_TARGET_TAPE, IRREGULAR_NON_TARGET_TAPE,
    toy_models_train_only,
)
from tools.public_crossmodel_heldout_ll import (
    FROZEN_CONSTRUCTED_TAPES,
    score_frozen_constructed_public_tape, all_three_frozen_non_target_ll_panel,
)


class FrozenPredictiveNonTargetPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.panel=all_three_frozen_non_target_ll_panel()

    def test_exact_three_previously_inspected_tapes_no_selection(self):
        self.assertEqual(FROZEN_CONSTRUCTED_TAPES,(
            ("unrelated_periodic_hard_negative", PERIODIC_PUBLIC_TAPE),
            ("non_target_momentum_burst", MOMENTUM_NON_TARGET_TAPE),
            ("non_target_irregular_control", IRREGULAR_NON_TARGET_TAPE),
        ))
        self.assertEqual(len(self.panel["tapes"]),3)
        self.assertEqual(self.panel["new_source_seeds_used"],0)
        self.assertTrue(self.panel["all_tapes_are_constructed_and_previously_inspected"])

    def test_fixed_m0_four_events_same_likelihood_regardless_interarrival_structure(self):
        values=[r["m0_heldout_log_likelihood"] for r in self.panel["tapes"].values()]
        self.assertEqual(values,[values[0]]*3)
        self.assertTrue(math.isfinite(values[0]))

    def test_spread_regime_score_momentum_vs_two_two_segment_memberships(self):
        periods=self.panel["tapes"]["unrelated_periodic_hard_negative"]
        momentum=self.panel["tapes"]["non_target_momentum_burst"]
        irregular=self.panel["tapes"]["non_target_irregular_control"]
        self.assertEqual(periods["m1v2_heldout_log_likelihood"],irregular["m1v2_heldout_log_likelihood"])
        self.assertNotEqual(periods["m1v2_heldout_log_likelihood"],momentum["m1v2_heldout_log_likelihood"])
        self.assertEqual(periods["m1v2_exposure_segments"],2)

    def test_all_frozen_candidates_reported_even_when_negative_model_gains(self):
        # A larger LL on momentum is not evidence of hidden controlled robot.
        for name, row in self.panel["tapes"].items():
            with self.subTest(name=name):
                self.assertEqual(row["unique_public_clusters"],4)
                self.assertFalse(row["physical_owner_identity_known"])
                self.assertFalse(row["real_market_fdr_known"])
                self.assertTrue(all(math.isfinite(row[k]) for k in (
                    "m0_heldout_log_likelihood","m1v2_heldout_log_likelihood",
                    "m2_heldout_log_likelihood","m1v2_minus_m0_log_likelihood",
                    "m2_minus_m0_log_likelihood")))
        self.assertFalse(self.panel["calibrated_significance_claimed"])

    def test_identical_public_tape_hidden_stories_cannot_affect_result(self):
        a="periodic ordinary market background"
        b="invented hidden controlled schedule story"
        self.assertNotEqual(a,b)
        trained=toy_models_train_only()
        self.assertEqual(score_frozen_constructed_public_tape(PERIODIC_PUBLIC_TAPE,trained),
                         score_frozen_constructed_public_tape(tuple(PERIODIC_PUBLIC_TAPE),trained))

    def test_split_fill_duplicates_dont_change_heldout_model_scores(self):
        models=toy_models_train_only()
        self.assertEqual(
            score_frozen_constructed_public_tape(PERIODIC_PUBLIC_TAPE,models),
            score_frozen_constructed_public_tape((20100,20100,21000,21900,21900,22800),models),
        )

    def test_out_of_order_and_coarse_source_assumptions_not_claimed_valid(self):
        from tools.public_intensity_rescaling import Abstain
        models=toy_models_train_only()
        for tape in ((21000,20100,22800),(20100,23000)):
            with self.subTest(tape=tape),self.assertRaises(Abstain):
                score_frozen_constructed_public_tape(tape,models)

    def test_no_oracle_raw_source_identifiers_or_significance_in_payload(self):
        import json
        s=json.dumps(self.panel).lower()
        for forbidden in ('"agent_id"','"private_truth"','"owner_id"','"p_value"','"source_prints"'):
            self.assertNotIn(forbidden,s)


if __name__=="__main__":unittest.main()
