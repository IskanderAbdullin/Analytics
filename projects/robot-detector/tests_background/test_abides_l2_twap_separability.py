import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from abides_l2_twap_separability import (
    assess_descriptive_separation,reanalyse_frozen_json,main
)
from abides_l2_twap_phase_contrast import SEEDS,SCENARIOS,PHASES_SECONDS

def observed():
    path=Path(__file__).resolve().parents[1]/"fixtures"/"abides_l2_twap_phase_observed_20261121.json"
    return json.loads(path.read_text(encoding="utf-8"))["cases"]

class PhaseChoiceTrapTests(unittest.TestCase):
    def test_original_genuine_four_run_result_has_phase_choice_trap(self):
        out=assess_descriptive_separation(observed())
        self.assertEqual(out["original_simulation_runs"],4)
        self.assertEqual(out["correlated_public_views"],12)
        self.assertEqual([x["strict_observed_separation_twap_above_background"]
                          for x in out["in_sample_phase_range_checks"]],
                         [False,True,True])
        self.assertFalse(out["strict_separation_across_every_precommitted_phase"])
        self.assertTrue(out["apparent_separation_changes_with_phase_choice"])
        self.assertLess(out["whole_view_rho_range_gap"],0)
        self.assertFalse(out["single_best_phase_selected"])
        self.assertFalse(out["threshold_fitted_to_development_study"])
        self.assertFalse(out["scientific_stage2_release_allowed"])
        self.assertFalse(out["live_trading_allowed"])

    def test_paired_seed_changes_are_descriptive_not_causal(self):
        out=assess_descriptive_separation(observed())
        self.assertEqual(len(out["seed_aligned_between_scenario_contrasts"]),6)
        for item in out["seed_aligned_between_scenario_contrasts"]:
            self.assertIn(item["seed"],SEEDS)
            self.assertIn(item["phase_seconds"],PHASES_SECONDS)
            self.assertGreater(item["twap_minus_background_rho"],0)
            self.assertFalse(item["causal_agent_effect_established"])
        self.assertFalse(out["out_of_sample_detection_accuracy_established"])
        self.assertFalse(out["individual_physical_owner_identified"])

    def test_undefined_phase_abstains_without_inventing_zero(self):
        cases=[dict(r) for r in observed()]
        next(x for x in cases if x["scenario"]=="twap_injected"
             and x["phase_seconds"]==10)["rho"]=None
        out=assess_descriptive_separation(cases)
        self.assertIsNone(out["in_sample_phase_range_checks"][1][
            "strict_observed_separation_twap_above_background"])
        self.assertIsNone(out["strict_separation_across_every_precommitted_phase"])
        self.assertIsNone(out["apparent_separation_changes_with_phase_choice"])

    def test_equal_rho_counts_as_no_strict_range_separation(self):
        cases=[dict(r) for r in observed()]
        for row in cases:
            row["rho"]=0.1
        out=assess_descriptive_separation(cases)
        self.assertEqual(out["whole_view_rho_range_gap"],0)
        self.assertEqual([x["strict_observed_separation_twap_above_background"]
                          for x in out["in_sample_phase_range_checks"]],
                         [False,False,False])
        self.assertFalse(out["apparent_separation_changes_with_phase_choice"])

    def test_offline_cli_accepts_only_frozen_source_and_never_overwrites(self):
        fixture=(Path(__file__).resolve().parents[1]/"fixtures"
                 /"abides_l2_twap_phase_observed_20261121.json")
        doc=json.loads(fixture.read_text(encoding="utf-8"))
        self.assertFalse(reanalyse_frozen_json(doc)["scientific_stage2_release_allowed"])
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/"review.json"
            with patch("sys.argv",["separability","--input",str(fixture),
                                   "--output",str(out)]):
                with patch("abides_l2_twap_phase_contrast.run_case",
                           side_effect=AssertionError("Should never simulate")):
                    main()
            result=json.loads(out.read_text(encoding="utf-8"))
            self.assertFalse(result["strict_separation_across_every_precommitted_phase"])
            self.assertFalse(result["source_authenticity_independently_verified"])
            first=out.read_bytes()
            with patch("sys.argv",["separability","--input",str(fixture),
                                   "--output",str(out)]):
                with self.assertRaises(FileExistsError):
                    main()
            self.assertEqual(out.read_bytes(),first)
        for broken in (
            dict(doc,schema_version="unknown"),
            dict(doc,original_matching_runs=12),
            dict(doc,source_content_authenticated_by_external_provider=True),
            dict(doc,individual_owner_known=True),
        ):
            with self.assertRaises(ValueError):
                reanalyse_frozen_json(broken)

    def test_bad_source_matrix_and_forged_attribution_fail_closed(self):
        with self.assertRaises(ValueError):
            assess_descriptive_separation(observed()[:-1])
        corrupt=[dict(r) for r in observed()]
        corrupt[0]["private_identity_used_for_feature"]=True
        with self.assertRaises(ValueError):
            assess_descriptive_separation(corrupt)

if __name__=="__main__":
    unittest.main(verbosity=2)
