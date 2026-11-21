#!/usr/bin/env python3
"""No simulator dependency: frozen ABIDES background design/accounting tests."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from abides_l2_background_nulls import (
    COHORTS, SEEDS, frozen_plan, summarize_cases
)


def fake(seed, cohort, rho):
    return {
        "seed": seed, "cohort": cohort,
        "public_projection_sha256": "f" * 64,
        "public_executed_prints": 800,
        "public_executed_lots": 4000,
        "public_l2_snapshots": 1100,
        "same_timestamp_l2_repeats": 300,
        "same_timestamp_ambiguous_prints": 700,
        "populated_trade_bins": 20,
        "eligible_previous_book_bins": 12,
        "lagged_spearman": rho,
        "rotated_bin_placebo_spearman": 0.1,
        "private_agent_identifiers_accessed": False,
        "named_execution_agent_injected": False,
        "real_market_accuracy_calibrated": False
    }


class FrozenGenuineBackgroundNullTests(unittest.TestCase):
    def test_plan_cannot_infer_single_algorithm_or_significance(self):
        p = frozen_plan()
        self.assertEqual(p["seeds"], [1801, 1802])
        self.assertEqual(p["cohorts"], list(COHORTS))
        self.assertEqual(p["book_depth"], 5)
        self.assertEqual(p["bin_seconds"], 30)
        self.assertTrue(p["no_injected_twap_vwap_or_pov_execution_program"])
        self.assertTrue(p["no_private_truth_used_by_feature"])
        self.assertTrue(p["no_inference_of_physical_owner"])
        self.assertTrue(p["no_strategy_selection_from_these_seeds"])

    def test_exact_matrix_counts_null_probabilities_unavailable(self):
        cases = [fake(seed, cohort, 0.2 if seed == 1801 else -0.4)
                 for seed in SEEDS for cohort in COHORTS]
        report = summarize_cases(list(reversed(cases)))
        self.assertEqual(len(report["cases"]), 6)
        self.assertEqual(len(report["cohorts"]), 3)
        self.assertEqual(report["cases"][0]["seed"], 1801)
        self.assertEqual(report["cases"][0]["cohort"], COHORTS[0])
        self.assertFalse(report["private_truth_read_or_published"])
        self.assertFalse(report["real_market_statistical_significance_calibrated"])
        self.assertFalse(report["physical_owner_count_known"])
        self.assertFalse(report["trading_enabled"])
        for row in report["cohorts"]:
            self.assertEqual(row["simulations"], 2)
            self.assertEqual(row["public_executed_prints"], 1600)
            self.assertEqual(row["eligible_previous_book_bins"], 24)
            self.assertEqual(row["simulations_with_evaluable_spearman"], 2)
            self.assertAlmostEqual(row["median_descriptive_spearman"], -0.1)
            self.assertIsNone(row["real_market_false_alarm_rate"])
            self.assertFalse(row["one_parent_order_identified"])

    def test_partial_undefined_is_explicit_not_imputed_as_zero(self):
        cases = [fake(seed, cohort, None if seed == 1801 else 0.8)
                 for seed in SEEDS for cohort in COHORTS]
        result = summarize_cases(cases)
        for r in result["cohorts"]:
            self.assertEqual(r["simulations_with_evaluable_spearman"], 1)
            self.assertEqual(r["median_descriptive_spearman"], 0.8)
        self.assertEqual(json.loads(json.dumps(result))["cases"][0]
                         ["lagged_spearman"], None)

    def test_reject_missing_duplicate_and_cross_protocol(self):
        cases = [fake(seed, cohort, .3)
                 for seed in SEEDS for cohort in COHORTS]
        with self.assertRaises(ValueError):
            summarize_cases(cases[:-1])
        with self.assertRaises(ValueError):
            summarize_cases(cases + [cases[0]])
        corrupt = [dict(c) for c in cases]
        corrupt[0]["seed"] = 901
        with self.assertRaises(ValueError):
            summarize_cases(corrupt)

    def test_reject_private_attribution_and_impossible_public_values(self):
        original = [fake(seed, cohort, .1)
                    for seed in SEEDS for cohort in COHORTS]
        for patch in (
            {"private_agent_identifiers_accessed": True},
            {"named_execution_agent_injected": True},
            {"real_market_accuracy_calibrated": True},
            {"public_executed_prints": 0},
            {"eligible_previous_book_bins": 30},
            {"same_timestamp_ambiguous_prints": 999},
            {"lagged_spearman": 1.01}
        ):
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                cases = [dict(c) for c in original]
                cases[0].update(patch)
                summarize_cases(cases)


if __name__ == "__main__":
    unittest.main(verbosity=2)
