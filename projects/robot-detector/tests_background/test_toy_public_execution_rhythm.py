#!/usr/bin/env python3
"""No-network preregistered synthetic public-only clock-grid false positives."""
from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from toy_public_execution_rhythm import (
    PublicExecutedPrint, SEEDS_DEVELOPMENT, SEEDS_HOLDOUT,
    COHORTS, START_US, END_US, GRID_PERIOD_US, GRID_TOLERANCE_US,
    THRESHOLD, public_prints, public_fingerprint,
    score_public, evaluate_fixed_cohorts, check_protocol
)
from research_seed_registry import read_ledger


class PrecommittedToyRhythmTests(unittest.TestCase):
    def test_fixed_protocol_and_ledger_seeds(self):
        s=check_protocol()
        self.assertEqual(s["uninspected_holdout_seed_ids_at_freeze"],
                         [2701,2702,2703,2704])
        self.assertEqual(s["development_seeds"],[2601,2602,2603,2604])
        self.assertEqual(s["threshold_fraction_of_public_executed_prints_on_grid"],0.22)
        self.assertEqual(s["within_phase_grid_tolerance_microseconds"],250000)
        self.assertEqual(s["periodic_clock_grid_seconds"],10)
        self.assertTrue(s["private_truth_used_only_after_detection"])
        self.assertTrue(s["must_record_false_positives_in_periodic_noise_cohort"])
        ledger=read_ledger()
        known={x["id"]:x["seeds"] for x in ledger["studies"]}
        self.assertEqual(known["toy_fixed_grid_execution_development"],
                         list(SEEDS_DEVELOPMENT))
        self.assertEqual(known["toy_fixed_grid_execution_holdout"],
                         list(SEEDS_HOLDOUT))

    def test_hard_negative_and_target_positive_are_identical_public_streams(self):
        for seed in SEEDS_DEVELOPMENT:
            with self.subTest(seed=seed):
                a=public_prints(seed,"periodic_noise_hard_negative")
                b=public_prints(seed,"periodic_target_positive")
                self.assertEqual(a,b)
                self.assertEqual(public_fingerprint(a),public_fingerprint(b))
                self.assertEqual(score_public(a),score_public(b))
                self.assertGreater(score_public(a)["fraction_near_fixed_grid"],THRESHOLD)
                self.assertTrue(score_public(a)["predicted_fixed_clock_pattern_present"])
                self.assertEqual(len(a),180)
                self.assertNotIn("agent_id",PublicExecutedPrint.__dataclass_fields__)
                self.assertNotIn("oracle_target",PublicExecutedPrint.__dataclass_fields__)

    def test_independent_background_and_periodic_noise_negative_cases_not_hidden(self):
        result=evaluate_fixed_cohorts(SEEDS_DEVELOPMENT)
        self.assertEqual(len(result["cases"]),12)
        self.assertEqual(result["schema_version"],"toy-public-execution-fixed-clock-holdout-v1")
        self.assertEqual(result["cohorts"],list(COHORTS))
        summaries=result["scenario_summary"]
        self.assertEqual(summaries["independent_noise_null"]["predicted_periodic"],0)
        self.assertEqual(summaries["periodic_noise_hard_negative"]["false_positive"],4)
        self.assertEqual(summaries["periodic_target_positive"]["true_positive"],4)
        self.assertFalse(result["real_market_precision_recall_or_FDR_calibrated"])
        self.assertFalse(result["any_true_physical_owner_labels_from_real_market"])
        self.assertFalse(result["real_market_trade_or_l2_archive_loaded"])
        self.assertFalse(result["phase_or_threshold_selected_after_holdout"])
        self.assertTrue(result["same_public_tape_for_periodic_noise_and_positive_each_seed"])
        self.assertTrue(result["seeds_local_project_ledger_globally_unseen_not_verified"])

    def test_frozen_grid_includes_boundary_and_excludes_just_beyond_tolerance(self):
        rows=tuple(PublicExecutedPrint(ts,1,True,100000) for ts in (
            START_US,
            START_US+GRID_TOLERANCE_US,
            START_US+GRID_TOLERANCE_US+1,
            START_US+GRID_PERIOD_US-GRID_TOLERANCE_US,
        ))
        report=score_public(rows)
        self.assertEqual(report["observed_public_trade_prints"],4)
        self.assertEqual(report["public_prints_near_fixed_grid"],3)
        self.assertEqual(report["fraction_near_fixed_grid"],0.75)
        self.assertTrue(report["predicted_fixed_clock_pattern_present"])
        self.assertFalse(report["physical_owner_count_or_true_bot_identity_inferred"])

    def test_private_labels_and_wrong_timestamps_fail_public_only_schema(self):
        original=public_prints(SEEDS_DEVELOPMENT[0],"independent_noise_null")
        for invalid in (
            replace(original[0],exchange_local_time_us=START_US-1),
            replace(original[0],exchange_local_time_us=END_US),
            replace(original[0],executed_lots=0),
            replace(original[0],buyer_initiated=1),
            replace(original[0],executed_price_ticks=-1),
            {"timestamp":START_US,"owner_id":"PRIVATE"},
        ):
            with self.subTest(invalid=str(invalid)[:55]),self.assertRaises(ValueError):
                score_public((invalid,))
        with self.assertRaises(ValueError):
            score_public(original[::-1])
        with self.assertRaises(ValueError):
            score_public(tuple())
        for seed in (1,0,True,99999):
            with self.subTest(seed=seed),self.assertRaises(ValueError):
                public_prints(seed,"periodic_target_positive")
        with self.assertRaises(ValueError):
            public_prints(SEEDS_DEVELOPMENT[0],"posthoc_new_cohort")
        with self.assertRaises(ValueError):
            evaluate_fixed_cohorts(tuple(SEEDS_DEVELOPMENT[:2]))
        with self.assertRaises(ValueError):
            evaluate_fixed_cohorts(tuple(SEEDS_HOLDOUT[::-1]))

    def test_frozen_null_feature_is_not_a_physical_owner_classifier(self):
        original=public_prints(SEEDS_DEVELOPMENT[0],"periodic_noise_hard_negative")
        result=score_public(original)
        self.assertTrue(result["predicted_fixed_clock_pattern_present"])
        # Oracle says NO injected target, so a public rhythm alarm here
        # is a false positive if interpreted as target-owner presence.
        truth_injected_target=False
        self.assertFalse(truth_injected_target)
        self.assertFalse(result["physical_owner_count_or_true_bot_identity_inferred"])

if __name__=="__main__":
    unittest.main(verbosity=2)
