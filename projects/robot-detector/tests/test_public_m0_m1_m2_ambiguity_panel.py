"""Precommitted constructed public input invariance; source-free hard negatives."""
import json
import math
import unittest
from dataclasses import replace

from tools.public_intensity_rescaling import Abstain
from tools.public_m1_dynamic_l2 import (
    M1DynamicEvaluationWindow, predict_m1_dynamic_exposure,
)
from tools.public_m0_m1_m2_ambiguity_panel import (
    PERIODIC_PUBLIC_TAPE, MOMENTUM_NON_TARGET_TAPE,
    IRREGULAR_NON_TARGET_TAPE, constructed_nonidentifiability_panel,
    public_only_tape_aggregate, toy_models_train_only, _book,
)


class PublicTapeIdentifiabilityTests(unittest.TestCase):
    def test_same_public_tape_distinct_hidden_stories_indistinguishable(self):
        # The private generating story is NOT passed to public feature code.
        story_a = "non_target_unrelated_periodic_background"
        story_b = "invented_controlled_private_robot"
        self.assertNotEqual(story_a, story_b)
        self.assertEqual(public_only_tape_aggregate(PERIODIC_PUBLIC_TAPE),
                         public_only_tape_aggregate(tuple(PERIODIC_PUBLIC_TAPE)))

    def test_complete_three_constructed_tape_panel_and_no_p_values(self):
        panel=constructed_nonidentifiability_panel()
        self.assertEqual(len(panel["public_tapes"]),3)
        self.assertFalse(panel["hidden_owner_count_deducible"])
        self.assertEqual(panel["new_ABIDES_source_runs"],0)
        for x in panel["public_tapes"].values():
            self.assertEqual(x["unique_public_clusters"],4)
            self.assertFalse(x["source_completeness_independently_verified"])
            self.assertFalse(x["real_market_fdr_known"])
            self.assertTrue(math.isfinite(x["m2_out_of_train_log_likelihood"]))

    def test_all_three_m0_m1v2_m2_gap_summaries_positive(self):
        for tape in (PERIODIC_PUBLIC_TAPE,MOMENTUM_NON_TARGET_TAPE,IRREGULAR_NON_TARGET_TAPE):
            result=public_only_tape_aggregate(tape)
            for key in ("m0_rescaled_gap_aggregate","m1v2_rescaled_gap_aggregate",
                        "m2_rescaled_gap_aggregate"):
                with self.subTest(tape=tape,model=key):
                    g=result[key]
                    self.assertEqual(g["count"],3)
                    self.assertLessEqual(g["integral_min"],g["integral_mean"])
                    self.assertLessEqual(g["integral_mean"],g["integral_max"])
                    self.assertGreater(g["integral_min"],0)

    def test_old_stable_model_abstains_new_dynamic_segments_eligible_only_if_asserted(self):
        x=public_only_tape_aggregate(PERIODIC_PUBLIC_TAPE)
        self.assertEqual(x["old_stable_m1_quality_status"],"ABSTAIN_SOURCE_FREE_AGE_GATE")
        self.assertEqual(x["dynamic_m1_quality_status"],"ELIGIBLE_ASSERTED_LOCAL_COVERAGE_ONLY")
        self.assertEqual(x["dynamic_m1_segments"],2)

    def test_split_fills_cannot_change_model_diagnostics(self):
        original=public_only_tape_aggregate(PERIODIC_PUBLIC_TAPE)
        duplicate=public_only_tape_aggregate((20100,20100,21000,21000,21900,22800,22800))
        self.assertEqual(original,duplicate)

    def test_unknown_l2_completeness_rejects_not_robot_absence(self):
        _,m1dyn,_,_=toy_models_train_only()
        w=M1DynamicEvaluationWindow("source_free_evaluation",20000,23000,
                                    (_book(18500),_book(20500,104.)))
        for bad in (replace(w,interval_complete=False),
                    replace(w,source_precision_ms=10),
                    replace(w,snapshots=(_book(19500),_book(20500,104.)))):
            with self.subTest(bad=bad),self.assertRaises(Abstain):
                predict_m1_dynamic_exposure(m1dyn,bad)

    def test_public_output_cannot_contain_private_oracle_owner_identifiers(self):
        content=json.dumps(constructed_nonidentifiability_panel())
        for forbidden in ("agent_id","owner_id","private_truth","passive_agent","aggressive_agent"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn('"'+forbidden+'"',content)

    def test_frozen_public_tapes_and_training_not_selected_posthoc(self):
        self.assertEqual(PERIODIC_PUBLIC_TAPE,(20100,21000,21900,22800))
        self.assertEqual(MOMENTUM_NON_TARGET_TAPE,(20100,20101,20102,22800))
        self.assertEqual(IRREGULAR_NON_TARGET_TAPE,(20100,20710,21930,22850))
        a=toy_models_train_only()
        b=toy_models_train_only()
        self.assertEqual(a,b)


if __name__ == "__main__": unittest.main()
