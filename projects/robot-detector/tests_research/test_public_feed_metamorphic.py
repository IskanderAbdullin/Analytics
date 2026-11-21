#!/usr/bin/env python3
"""Public-only feed metamorphic stress; no ABIDES or broker data."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from public_feed_metamorphic import run_checks, evaluate_trial


class PublicFeedMetamorphicTests(unittest.TestCase):
    def test_repeated_generated_books_preserve_completed_prefix(self):
        result = run_checks(trials=24)
        self.assertEqual(result["fixture_count"],24)
        self.assertTrue(result["future_append_closed_prefix_stable"])
        self.assertTrue(result["all_public_bin_accounting_conserved"])

    def test_separate_public_gaps_monotonically_remove_eligibility(self):
        for i in (0, 2, 7, 13):
            case=evaluate_trial(i)
            self.assertTrue(case["all_invariants_passed"])
            self.assertLessEqual(case["both_gaps_closed_bins"],
                                 case["book_gap_closed_bins"])
            self.assertLessEqual(case["both_gaps_closed_bins"],
                                 case["trade_gap_closed_bins"])
            self.assertEqual(case["base_closed_bins"],8)
            self.assertEqual(case["book_gap_closed_bins"],7)
            self.assertEqual(case["trade_gap_closed_bins"],7)
            self.assertEqual(case["both_gaps_closed_bins"],6)

    def test_earlier_watermark_only_truncates_closed_tail(self):
        case=evaluate_trial(31)
        self.assertEqual(case["early_watermark_closed_bins"],6)
        self.assertLess(case["early_watermark_closed_bins"],
                        case["base_closed_bins"])

    def test_trial_generator_deterministic_and_no_false_market_evidence(self):
        a=run_checks(trials=4)
        b=run_checks(trials=4)
        self.assertEqual(json.dumps(a,sort_keys=True),json.dumps(b,sort_keys=True))
        self.assertEqual(a["source"],
                         "deterministic_synthetic_software_tests_not_genuine_ABIDES")
        self.assertFalse(a["provider_completeness_independently_verified"])
        self.assertFalse(a["private_agent_truth_used"])
        self.assertFalse(a["real_market_accuracy_calibrated"])
        self.assertFalse(a["live_trading_enabled"])

    def test_bad_trial_counts_fail_closed(self):
        for invalid in (0,129,-1,True,1.0,"32"):
            with self.subTest(invalid=invalid),self.assertRaises(ValueError):
                run_checks(trials=invalid)


if __name__ == "__main__":
    unittest.main(verbosity=2)
