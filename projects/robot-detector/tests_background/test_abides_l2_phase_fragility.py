import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from abides_l2_phase_fragility import evaluate_phase_fragility
from abides_l2_binphase_sensitivity import aggregate, SEEDS, BACKGROUNDS, PHASES_SECONDS

def prepared(shape=None):
    rows=[]
    for seed in SEEDS:
        for mode in BACKGROUNDS:
            for phase in PHASES_SECONDS:
                rho=(shape or {0:-0.2,10:0.1,20:-0.4})[phase]
                rows.append({
                    "seed":seed,"background":mode,"phase_seconds":phase,
                    "public_sha256":"a"*64,"public_prints":80,"public_lots":100,
                    "l2_snapshots":90,"eligible_lagged_bins":8,
                    "populated_trade_bins":10,"abstained_bins":2,
                    "descriptive_rho":rho,
                    "claimed_real_feed_completeness":False,
                    "private_identity_accessed":False,"model_selected":False})
    return aggregate(rows)

class FragilityTests(unittest.TestCase):
    def test_strict_sign_reversal_is_per_original_simulation(self):
        report=evaluate_phase_fragility(prepared())
        self.assertEqual(report["descriptive_state"],"SIGN_REVERSAL_OBSERVED")
        self.assertEqual(report["original_matching_engine_runs"],4)
        self.assertFalse(report["independence_between_background_regimes_established"])
        self.assertEqual(report["correlated_analytic_views"],12)
        self.assertEqual(report["simulations_with_strict_sign_reversal"],4)
        self.assertFalse(report["scientific_stage2_release_allowed"])
        self.assertFalse(report["physical_owner_count_known"])

    def test_stable_sign_still_never_licenses_owner_or_live_signal(self):
        report=evaluate_phase_fragility(prepared({0:-0.1,10:-0.2,20:-0.3}))
        self.assertEqual(report["descriptive_state"],
                         "NO_REVERSAL_IN_TINY_SYNTHETIC_SAMPLE")
        self.assertFalse(report["scientific_stage2_release_allowed"])
        self.assertFalse(report["live_trading_allowed"])
        self.assertEqual(report["simulations_with_strict_sign_reversal"],0)

    def test_missing_and_zero_coefficient_never_count_as_stable(self):
        for vals in ({0:None,10:-0.1,20:-0.2},
                     {0:0,10:-0.1,20:-0.2}):
            with self.subTest(vals=vals):
                report=evaluate_phase_fragility(prepared(vals))
                self.assertEqual(report["descriptive_state"],
                                 "SIGN_STABILITY_UNDETERMINED")
                self.assertFalse(report["scientific_stage2_release_allowed"])

    def test_counteracting_deltas_in_two_seeds_are_not_a_small_effect(self):
        data=prepared({0:-0.2,10:-0.1,20:-0.4})
        for row in data["cases"]:
            if row["seed"]==2102 and row["phase_seconds"]==10:
                row["descriptive_rho"]=-0.3
        report=evaluate_phase_fragility(data)
        c=next(x for x in report["paired_contrast_sign_checks"]
               if x["background"]=="poisson" and x["compared_origin_seconds"]==10)
        self.assertTrue(c["opposing_signed_deltas_between_seeds"])
        self.assertEqual(report["contrasts_with_opposing_seed_directions"],2)

    def test_real_original_scalar_fixture_exposes_one_sign_flip_and_drift(self):
        import json
        fixture=Path(__file__).resolve().parents[1]/"fixtures"/"abides_l2_phase_observed_scalars_20261121.json"
        src=json.loads(fixture.read_text(encoding="utf-8"))
        cases=[]
        for r in src["cases"]:
            cases.append(dict(r,public_sha256="a"*64,public_prints=80,
                              public_lots=100,l2_snapshots=90,
                              abstained_bins=(r["populated_trade_bins"]
                                              -r["eligible_lagged_bins"]),
                              claimed_real_feed_completeness=False,
                              private_identity_accessed=False,model_selected=False))
        audit=evaluate_phase_fragility(aggregate(cases))
        self.assertEqual(audit["simulations_with_strict_sign_reversal"],1)
        self.assertEqual(audit["simulations_with_changed_eligible_bin_count"],4)
        self.assertEqual(audit["contrasts_with_opposing_seed_directions"],1)
        self.assertEqual(audit["descriptive_state"],"SIGN_REVERSAL_OBSERVED")
        self.assertFalse(audit["complete_public_book_digest_available"])

    def test_wrong_missing_frozen_matrix_is_rejected(self):
        for bad in (None,{},{"cases":[]},{"cases":[None]}):
            with self.assertRaises(ValueError):
                evaluate_phase_fragility(bad)

if __name__=="__main__":
    unittest.main(verbosity=2)
