"""Guard aggregate-only reporting of preregistered constructed A/B/C controls."""
import unittest
from public_abc_report import build_report


class TestPublicABCReport(unittest.TestCase):
    def test_all_frozen_scenarios_and_models(self):
        report = build_report()
        self.assertEqual(report["randomization_seed"], 404)
        self.assertEqual(report["randomization_replicates_per_model"], 64)
        self.assertEqual(report["independent_market_or_abides_source_runs"], 0)
        self.assertEqual(set(report["scenarios"]), {
            "poisson_like_quantized", "momentum_like_bursts", "unrelated_periodic_20s",
        })
        for row in report["scenarios"].values():
            self.assertEqual(set(row["candidates"]), {
                "A_uniform_5s", "B_offset_5s", "C_intensity_500ms",
            })
            self.assertTrue(all(len(c["all_replicates"]) == 64
                                for c in row["candidates"].values()))

    def test_negative_outcomes_are_not_rebranded_as_significance(self):
        report = build_report()
        self.assertFalse(report["calibrated_p_values"])
        self.assertFalse(report["real_market_fdr_known"])
        self.assertFalse(report["physical_owners_identifiable"])
        self.assertEqual(report["scenarios"]["momentum_like_bursts"]["observed"], 168)
        self.assertEqual(report["scenarios"]["unrelated_periodic_20s"]["observed"], 0)
        self.assertEqual(report["scenarios"]["momentum_like_bursts"]["candidates"]["B_offset_5s"]["min"], 168)
        self.assertEqual(report["scenarios"]["momentum_like_bursts"]["candidates"]["B_offset_5s"]["max"], 168)

    def test_deterministic_report(self):
        self.assertEqual(build_report(), build_report())


if __name__ == "__main__":
    unittest.main()
