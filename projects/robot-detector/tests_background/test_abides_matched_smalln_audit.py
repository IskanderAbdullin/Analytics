"""Source-free exact binomial small-N and paired ABIDES source guards.

The source scores are public anonymous aggregates from genuine synthetic
ABIDES, not 16 actual market dates or 16 independent market owners.
"""
import json
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from abides_matched_smalln_audit import (
    SOURCE,SEEDS,COHORTS,EXPECTED_SOURCE_SHA,
    clopper_pearson,validate_original_source_fixture,
    frozen_protocol,audit_matched_uncertainty
)


class ExactSmallSampleSyntheticSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=json.loads(SOURCE.read_text(encoding="utf-8"))

    def test_frozen_retrospective_not_new_blind_data_or_real_precision(self):
        p=frozen_protocol()
        self.assertEqual(p["source_seed_values"],list(SEEDS))
        self.assertEqual(p["cohorts"],list(COHORTS))
        self.assertEqual(p["original_source_run"],44938991772)
        self.assertEqual(p["original_source_uncompressed_json_sha256"],EXPECTED_SOURCE_SHA)
        self.assertEqual(p["new_source_replay"],"NONE")
        self.assertTrue(p["design_origin"].startswith("RETROSPECTIVE_"))
        self.assertTrue(p["source_snapshot_and_print_rows_not_independent_experimental_units"])
        self.assertTrue(p["no_real_market_FDR_precision_or_owner_identity_claim"])
        self.assertEqual(p["exact_nominal_binomial_interval"]["family"],
                         "two-sided Clopper-Pearson")
        self.assertEqual(p["exact_nominal_binomial_interval"]["confidence_level"],.95)

    def test_all_five_exact_binomial_95_intervals_four_source_trials(self):
        expected={
            0:(0.,.60236464),
            1:(.00630946,.80587955),
            2:(.06758599,.93241401),
            3:(.19412045,.99369054),
            4:(.39763536,1.)
        }
        for x,(low,high) in expected.items():
            with self.subTest(successes=x):
                interval=clopper_pearson(x,4)
                self.assertEqual(interval["source_seed_trials"],4)
                self.assertEqual(interval["successes"],x)
                self.assertAlmostEqual(interval["nominal_exact_CP_lower"],low,places=8)
                self.assertAlmostEqual(interval["nominal_exact_CP_upper"],high,places=8)
                self.assertEqual(interval["observed_synthetic_fraction"],round(x/4,8))
                self.assertFalse(interval["real_market_population_confidence_interval"])
                self.assertFalse(interval["iid_simulation_seed_sampling_assumption_confirmed"])

    def test_clopper_pearson_rejects_wrong_sample_unit_or_invented_precision(self):
        for val in (
            (0,16,.95),
            (1,5,.95),
            (4,3,.95),
            (-1,4,.95),
            (True,4,.95),
            (1,4,.9),
            (0,4,1),
            (0,4,False)
        ):
            with self.subTest(args=val),self.assertRaises(ValueError):
                clopper_pearson(*val)

    def test_original_fixture_all_16_and_every_cohort_conserved(self):
        cases=validate_original_source_fixture(self.source)
        self.assertEqual(len(cases),16)
        self.assertEqual({(r["seed"],r["cohort"]) for r in cases},
                         {(s,c) for s in SEEDS for c in COHORTS})
        self.assertEqual(sum(r["prints"] for r in cases),16142)
        self.assertEqual(sum(r["unique_time_groups"] for r in cases),14801)
        self.assertEqual(sum(r["source_L2"] for r in cases),26498)
        self.assertEqual(sum(r["posthoc_TWAP_fills"] for r in cases),61)
        self.assertTrue(all(r["real_market_FDR_known"] is False for r in cases))
        self.assertEqual(self.source["original_source_artifact_id"],14720831681)

    def test_paired_source_weak_power_and_real_market_caveats(self):
        x=audit_matched_uncertainty(self.source)
        self.assertTrue(x["already_inspected_same_synthetic_source_tapes"])
        self.assertEqual(x["new_independent_matching_engine_runs"],0)
        self.assertFalse(x["real_market_FDR_calibrated"])
        self.assertFalse(x["market_population_confidence_claim"])
        self.assertFalse(x["IID_simulation_seed_sampling_certified"])
        self.assertFalse(x["p_values_or_significant_winner_claimed"])
        self.assertTrue(x["paired_decision_risk_not_an_independent_32_source_sample"])
        twap=x["each_cohort"]["twap_45s_positive"]
        self.assertEqual(twap["paired_decisions"],{
            "both_positive":3,"print_only_positive":1,
            "grouped_only_positive":0,"both_negative":0,
            "at_least_one_abstain":0
        })
        self.assertEqual(twap["source_oracle_controlled_TWAP_fills"],61)
        self.assertEqual(twap["naive_print_positive_alarm"]["successes"],4)
        self.assertEqual(twap["grouped_timestamp_positive_alarm"]["successes"],3)
        poison=x["each_cohort"]["poisson_noise_null"]
        self.assertEqual(poison["paired_decisions"]["both_positive"],1)
        self.assertEqual(poison["paired_decisions"]["both_negative"],3)
        self.assertEqual(poison["naive_print_positive_alarm"]["successes"],1)
        self.assertEqual(poison["grouped_timestamp_positive_alarm"]["successes"],1)
        self.assertEqual(x["each_cohort"]["fixed_20s_noise_hard_negative"][
            "grouped_timestamp_positive_alarm"]["successes"],0)
        self.assertEqual(x["each_cohort"]["momentum_noise_hard_negative"][
            "naive_print_positive_alarm"]["successes"],0)
        q=x["descriptive_background_sum_not_a_real_market_FDR"]
        self.assertEqual(q["original_negative_source_cases"],12)
        self.assertEqual(q["print_based_false_alarms_descriptive_only"],1)
        self.assertEqual(q["grouped_false_alarms_descriptive_only"],1)
        self.assertTrue(q["pooling_three_different_backgrounds_as_one_iid_cohort_prohibited"])

    def test_forged_source_counts_missing_seed_or_change_outcome_fail(self):
        for mutator in (
            lambda x: x.update({"original_source_artifact_id":0}),
            lambda x: x["original_all_16_case_public_summary"].pop(),
            lambda x: x["original_all_16_case_public_summary"][0].update({"seed":3202}),
            lambda x: x["original_all_16_case_public_summary"][0].update({"prints":1}),
            lambda x: x["original_all_16_case_public_summary"][0].update({"real_market_FDR_known":True}),
            lambda x: x["original_all_16_case_public_summary"][0].update({"naive_classification":"TARGET_PATTERN"}),
            lambda x: x.update({"no_posthoc_threshold_or_phase_change":False}),
            lambda x: x["original_cohort_aggregates"]["twap_45s_positive"].update({
                "original_print_based_positive_alarms":3
            }),
            lambda x: x["totals"].update({"unique_exchange_timestamps":123}),
        ):
            bad=deepcopy(self.source)
            mutator(bad)
            with self.assertRaises(ValueError):
                audit_matched_uncertainty(bad)

    def test_original_frozen_uncertainty_protocol_cannot_be_rewritten(self):
        p=frozen_protocol()
        for key,val in (
            ("original_source_run",0),
            ("new_source_replay","YES"),
            ("source_seed_values",[3201,3202]),
            ("no_pvalue_or_bayesian_posterior_claim",False),
            ("source_snapshot_and_print_rows_not_independent_experimental_units",False)
        ):
            changed=deepcopy(p)
            changed[key]=val
            with self.subTest(key=key),patch.object(
                Path,"read_text",return_value=json.dumps(changed)
            ),self.assertRaises(ValueError):
                frozen_protocol()
        changed=deepcopy(p)
        changed["exact_nominal_binomial_interval"]["confidence_level"]=0.99
        with patch.object(Path,"read_text",return_value=json.dumps(changed)):
            with self.assertRaises(ValueError):
                frozen_protocol()

if __name__=="__main__":
    unittest.main(verbosity=2)
