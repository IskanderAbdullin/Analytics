#!/usr/bin/env python3
"""Deterministic aggregation tests; do not require installing ABIDES-NG."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from abides_batch import summarize  # noqa: E402


def item(seed, mode, controlled, tp_fixed, fp_fixed, tp_variable, fp_variable):
    return {
        "seed": seed, "mode": mode, "public_sha256": "b" * 64,
        "public_prints": 30, "controlled_prints": controlled,
        "models": [
            {"model": "fixed_quantity", "truePositivePrints": tp_fixed,
             "falsePositivePrints": fp_fixed, "attributedPublicPrints": tp_fixed + fp_fixed,
             "missedInjectedPrints": controlled - tp_fixed},
            {"model": "variable_quantity", "truePositivePrints": tp_variable,
             "falsePositivePrints": fp_variable, "attributedPublicPrints": tp_variable + fp_variable,
             "missedInjectedPrints": controlled - tp_variable},
        ],
    }


class BatchSummaryTests(unittest.TestCase):
    def test_aggregate_conservation_and_null_recall(self):
        cases = [
            item(901, "twap", 6, 4, 1, 2, 1),
            item(901, "null", 0, 0, 1, 0, 0),
            item(902, "twap", 7, 5, 2, 3, 0),
            item(902, "null", 0, 0, 0, 0, 2),
        ]
        result = summarize(cases, [901, 902])
        self.assertEqual(result["case_count"], 4)
        self.assertFalse(result["market_accuracy_calibrated"])
        fixed = next(x for x in result["aggregates"]
                     if x["mode"] == "twap" and x["model"] == "fixed_quantity")
        self.assertEqual(fixed["true_positive_prints"], 9)
        self.assertEqual(fixed["false_positive_prints"], 3)
        self.assertEqual(fixed["missed_controlled_prints"], 4)
        self.assertEqual(fixed["micro_event_recall"], 9 / 13)
        null_variable = next(x for x in result["aggregates"]
                             if x["mode"] == "null" and x["model"] == "variable_quantity")
        self.assertEqual(null_variable["case_false_alarm_count"], 1)
        self.assertIsNone(null_variable["micro_event_recall"])

    def test_incomplete_matrix_rejected(self):
        with self.assertRaises(ValueError):
            summarize([item(901, "twap", 6, 4, 1, 0, 0)], [901])
        with self.assertRaises(ValueError):
            summarize([
                item(901, "twap", 6, 4, 1, 0, 0),
                item(901, "null", 0, 0, 0, 0, 0)
            ], [901, 901])

    def test_null_control_rejected(self):
        with self.assertRaises(ValueError):
            summarize([
                item(901, "twap", 6, 4, 0, 0, 0),
                item(901, "null", 3, 2, 0, 0, 0)
            ], [901])


if __name__ == "__main__":
    unittest.main()
