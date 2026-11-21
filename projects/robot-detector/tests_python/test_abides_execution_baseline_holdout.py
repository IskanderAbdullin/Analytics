#!/usr/bin/env python3
"""Reproducible model/seed matrix and public/private accounting contract."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from abides_execution_baseline_holdout import (
    FROZEN_SEEDS, MODES, MODELS, preregister, aggregate
)


def case(seed, mode, controlled):
    if mode == "null":
        fixed = {"attributed": 2, "tp": 0, "fp": 2, "missed": 0}
        variable = {"attributed": 0, "tp": 0, "fp": 0, "missed": 0}
    else:
        fixed = {"attributed": 3, "tp": 2, "fp": 1,
                 "missed": controlled - 2}
        variable = {"attributed": 0, "tp": 0, "fp": 0,
                    "missed": controlled}
    return {"seed": seed, "mode": mode, "public_prints": 500,
            "controlled_prints": controlled, "public_sha256": "d"*64,
            "models": {"fixed_quantity": fixed, "variable_quantity": variable}}


class StrategyBaselineTests(unittest.TestCase):
    def test_pre_registered_exact_seed_and_model_plan(self):
        plan = preregister([1301, 1302, 1303, 1304])
        self.assertEqual(tuple(plan["seeds"]), FROZEN_SEEDS)
        self.assertEqual(plan["modes"], list(MODES))
        self.assertEqual(plan["screens"], list(MODELS))
        self.assertFalse(plan["physical_owner_identity_known"])
        self.assertFalse(plan["real_market_accuracy_calibrated"])

    def test_executable_accounting_and_null_recall(self):
        cases = [case(seed, mode, 0 if mode == "null" else 10)
                 for seed in FROZEN_SEEDS for mode in MODES]
        result = aggregate(cases, list(FROZEN_SEEDS))
        self.assertEqual(result["case_count"], 16)
        self.assertFalse(result["models_tuned_on_frozen_seeds"])
        self.assertFalse(result["private_truth_retained_in_artifact"])
        self.assertEqual(len(result["aggregates"]), 8)
        null_fixed = next(r for r in result["aggregates"]
                          if r["mode"] == "null" and r["model"] == "fixed_quantity")
        self.assertEqual(null_fixed["false_positive_prints"], 8)
        self.assertIsNone(null_fixed["pooled_event_recall"])
        pov_fixed = next(r for r in result["aggregates"]
                         if r["mode"] == "pov" and r["model"] == "fixed_quantity")
        self.assertEqual(pov_fixed["true_positive_prints"], 8)
        self.assertEqual(pov_fixed["missed_controlled_prints"], 32)
        self.assertEqual(pov_fixed["false_positive_prints"], 4)
        self.assertAlmostEqual(pov_fixed["pooled_event_recall"], .2)
        self.assertAlmostEqual(pov_fixed["pooled_event_precision"], 2/3)

    def test_reject_incomplete_matrix_and_truth_mismatch(self):
        cases = [case(seed, mode, 0 if mode == "null" else 10)
                 for seed in FROZEN_SEEDS for mode in MODES]
        with self.assertRaises(ValueError):
            aggregate(cases[:-1], list(FROZEN_SEEDS))
        with self.assertRaises(ValueError):
            aggregate(cases, [1301, 1302, 1303, 1311])
        corrupt = [dict(c) for c in cases]
        corrupt[0]["controlled_prints"] = 1
        with self.assertRaises(ValueError):
            aggregate(corrupt, list(FROZEN_SEEDS))
        corrupt = [dict(c) for c in cases]
        corrupt[1]["models"] = dict(corrupt[1]["models"])
        corrupt[1]["models"]["fixed_quantity"] = dict(
            corrupt[1]["models"]["fixed_quantity"], tp=999)
        with self.assertRaises(ValueError):
            aggregate(corrupt, list(FROZEN_SEEDS))


if __name__ == "__main__":
    unittest.main(verbosity=2)
