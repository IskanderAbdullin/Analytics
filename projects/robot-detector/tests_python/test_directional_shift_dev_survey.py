#!/usr/bin/env python3
"""Static contract checks for the public-only directional-shift survey."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from directional_shift_dev_survey import aggregate


def case(seed, mode, windows, evaluated=50):
    return {
        "seed": seed, "mode": mode,
        "public_prints": 1000, "public_sha256": "a" * 64,
        "evaluated_bins": evaluated, "shift_windows": windows,
        "gap_transitions": 0, "unknown_side_quality_bins": 0,
    }


class DirectionalSurveyTests(unittest.TestCase):
    def test_null_with_more_shifts_is_not_a_robot(self):
        rows = [
            case(71, "null", 6), case(71, "vwap", 1), case(71, "pov", 3),
            case(72, "null", 4), case(72, "vwap", 0), case(72, "pov", 1),
        ]
        report = aggregate(rows, [71, 72])
        self.assertEqual(report["input_mode"], "public_only")
        self.assertFalse(report["private_truth_used_for_detection"])
        self.assertFalse(report["physical_owner_count_known"])
        self.assertFalse(report["statistical_significance_established"])
        self.assertEqual(len(report["cases"]), 6)
        null = next(r for r in report["cohorts"] if r["mode"] == "null")
        self.assertEqual(null["observed_directional_shift_windows"], 10)
        self.assertEqual(null["simulations_with_one_or_more_shift_windows"], 2)
        self.assertAlmostEqual(
            null["descriptive_shift_windows_per_100_evaluated_bins"], 10.0)
        self.assertTrue(all(not x["robot_identity_known"]
                            and not x["market_false_alarm_rate_calibrated"]
                            for x in report["cohorts"]))

    def test_reject_spent_seeds(self):
        for spent in (41, 62, 901):
            with self.subTest(spent=spent), self.assertRaises(ValueError):
                aggregate([case(spent, mode, 0) for mode in
                           ("null", "vwap", "pov")], [spent])

    def test_reject_incomplete_duplicate_and_zero_denominator(self):
        with self.assertRaises(ValueError):
            aggregate([case(71, "null", 0)], [71])
        rows = [case(71, m, 0, evaluated=0)
                for m in ("null", "vwap", "pov")]
        report = aggregate(rows, [71])
        self.assertTrue(all(r["descriptive_shift_windows_per_100_evaluated_bins"]
                            is None for r in report["cohorts"]))
        with self.assertRaises(ValueError):
            aggregate(rows + [rows[0]], [71])
        with self.assertRaises(ValueError):
            aggregate(rows, [71, 71])


if __name__ == "__main__":
    unittest.main(verbosity=2)
