import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from volume_response_dev_survey import summarize


def sample(seed, mode, buy, sell):
    return {"seed": seed, "mode": mode, "public_prints": 300,
            "public_sha256": "a" * 64,
            "side": {
                "BUY": {"rho": buy, "adjacent_pairs": 59, "gaps": 0},
                "SELL": {"rho": sell, "adjacent_pairs": 59, "gaps": 0}
            }}


class SurveyIntegrityTests(unittest.TestCase):
    def test_null_can_have_higher_public_association_than_execution(self):
        rows = [
            sample(61, "null", 0.8, 0.9),
            sample(61, "pov", 0.2, 0.3),
            sample(61, "vwap", 0.4, 0.5),
            sample(62, "null", 0.7, 0.6),
            sample(62, "pov", 0.1, 0.2),
            sample(62, "vwap", 0.3, 0.4),
        ]
        result = summarize(rows, [61, 62])
        self.assertEqual(result["case_count"], 6)
        self.assertFalse(result["bot_owner_identity_known"])
        self.assertFalse(result["candidate_model_fitted"])
        self.assertFalse(result["private_truth_exported"])
        self.assertFalse(result["real_market_specificity_known"])
        null_buy = next(x for x in result["public_summary"]
                        if x["mode"] == "null" and x["reported_direction"] == "BUY")
        pov_buy = next(x for x in result["public_summary"]
                       if x["mode"] == "pov" and x["reported_direction"] == "BUY")
        self.assertAlmostEqual(null_buy["median_public_lag_rho"], 0.75)
        self.assertAlmostEqual(pov_buy["median_public_lag_rho"], 0.15)
        self.assertGreater(null_buy["median_public_lag_rho"],
                           pov_buy["median_public_lag_rho"])
        self.assertTrue(all(not r["owner_identity_known"] and
                            not r["significance_calibrated"] for r in result["public_summary"]))

    def test_spent_holdout_seeds_are_rejected(self):
        rows = [sample(901, mode, None, None) for mode in ("null", "pov", "vwap")]
        with self.assertRaises(ValueError):
            summarize(rows, [901])

    def test_missing_and_duplicate_cases_rejected(self):
        with self.assertRaises(ValueError):
            summarize([sample(61, "null", .2, .1)], [61])
        rows = [sample(61, mode, .2, .1) for mode in ("null", "pov", "vwap")]
        with self.assertRaises(ValueError):
            summarize(rows + [rows[0]], [61])
        with self.assertRaises(ValueError):
            summarize(rows, [61, 61])


if __name__ == "__main__":
    unittest.main(verbosity=2)
