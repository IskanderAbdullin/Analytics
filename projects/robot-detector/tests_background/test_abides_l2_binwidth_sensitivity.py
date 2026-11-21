#!/usr/bin/env python3
"""Offline bin-width robustness matrix and public-tape conservation tests."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from abides_l2_binwidth_sensitivity import (
    SEEDS, BACKGROUNDS, BIN_WIDTHS_SECONDS, aggregate, frozen_plan
)


def case(seed, mode, width, rho):
    return {
        "seed": seed, "background": mode, "bin_seconds": width,
        "public_sha256": f"{seed}{mode}".encode().hex().ljust(64, "0"),
        "public_executed_prints": 900,
        "public_execution_lots": 2500,
        "public_l2_snapshots": 1400,
        "populated_public_trade_bins": 20,
        "eligible_lagged_bins": 12,
        "abstained_lagged_bins": 8,
        "lagged_spearman": rho,
        "private_agent_identified": False,
        "market_significance_calibrated": False,
        "source_completion_verified": False,
        "threshold_selected": False,
    }


def matrix(values=None):
    values = values or {10: 0.2, 30: 0.5, 60: -0.2}
    return [
        case(seed, mode, width, values[width])
        for seed in SEEDS for mode in BACKGROUNDS for width in BIN_WIDTHS_SECONDS
    ]


class PublicWidthRobustnessTests(unittest.TestCase):
    def test_frozen_plan_has_no_identity_or_detection_threshold(self):
        p = frozen_plan()
        self.assertEqual(p["development_seeds"], [1901, 1902])
        self.assertEqual(p["widths_seconds"], [10, 30, 60])
        self.assertEqual(p["backgrounds"], ["poisson", "fixed_cadence"])
        self.assertTrue(p["one_market_simulation_per_seed_background"])
        self.assertFalse(p["source_archive_coverage_attested"])
        self.assertFalse(p["private_truth_used_for_feature"])
        self.assertFalse(p["detector_threshold_fitted"])

    def test_matrix_yields_four_actual_simulations_not_twelve(self):
        r = aggregate(matrix())
        self.assertEqual(r["actual_matching_engine_simulations"], 4)
        self.assertEqual(len(r["cases"]), 12)
        self.assertEqual(len(r["cohorts"]), 6)
        self.assertEqual(len(r["per_simulation_sensitivity"]), 4)
        self.assertFalse(r["independent_simulations_across_widths"])
        self.assertFalse(r["private_truth_exported"])
        self.assertFalse(r["real_market_calibration_known"])
        self.assertFalse(r["individual_bot_identified"])
        self.assertFalse(r["model_threshold_selected"])
        for v in r["per_simulation_sensitivity"]:
            self.assertAlmostEqual(v["rho_span_across_widths"], 0.7)
            self.assertEqual(v["widths_with_defined_rho"], 3)
            self.assertFalse(v["independent_validation_across_widths"])
        for v in r["cohorts"]:
            self.assertEqual(v["simulations"], 2)
            self.assertEqual(v["eligible_lagged_bins"], 24)
            self.assertIsNone(v["market_false_discovery_rate"])
            self.assertFalse(v["physical_owner_count_known"])

    def test_undefined_is_not_zero_and_not_invented_significance(self):
        r = aggregate(matrix({10: None, 30: 0.1, 60: None}))
        for sensitivity in r["per_simulation_sensitivity"]:
            self.assertEqual(sensitivity["widths_with_defined_rho"], 1)
            self.assertIsNone(sensitivity["rho_span_across_widths"])
        undef = [c for c in r["cohorts"] if c["bin_seconds"] in (10, 60)]
        self.assertTrue(all(c["defined_rho_simulations"] == 0 and
                            c["median_descriptive_rho"] is None for c in undef))

    def test_reject_missing_duplicate_changed_design(self):
        data = matrix()
        with self.assertRaises(ValueError):
            aggregate(data[:-1])
        with self.assertRaises(ValueError):
            aggregate(data + [data[0]])
        replaced = [dict(x) for x in data]
        replaced[0]["seed"] = 901
        with self.assertRaises(ValueError):
            aggregate(replaced)

    def test_reject_source_tape_replacement_between_widths(self):
        for change in (
            {"public_sha256": "a" * 64},
            {"public_executed_prints": 901},
            {"public_execution_lots": 2501},
            {"public_l2_snapshots": 1401}
        ):
            data = [dict(x) for x in matrix()]
            data[0].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                aggregate(data)

    def test_reject_unreconciled_bins_and_forbidden_identity_claim(self):
        for change in (
            {"abstained_lagged_bins": 7},
            {"eligible_lagged_bins": 21},
            {"source_completion_verified": True},
            {"private_agent_identified": True},
            {"market_significance_calibrated": True},
            {"threshold_selected": True},
            {"lagged_spearman": 1.1}
        ):
            data = [dict(x) for x in matrix()]
            data[0].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                aggregate(data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
