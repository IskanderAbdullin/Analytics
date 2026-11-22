"""Adversarial source-free test of original 160-case ABIDES posthoc audit.

Original source data inspected before audit; all power intervals nominal
hypothetical synthetic IID seed-trial only, not independent real markets.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from abides_160_original_audit import (
    FIXTURE,SEEDS,COHORTS,EXPECTED_SHA,
    audit_fixture,nominal_cp_95,validate_original_source_bytes
)


class Original160SourceUncertaintyAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_posthoc_source_provenance_unchanged_and_not_real_market(self):
        out=audit_fixture(self.fixture)
        self.assertEqual(out["original_source_cases"],160)
        self.assertEqual(out["independent_source_ensembles_per_cohort"],40)
        self.assertFalse(out["physical_owner_count_or_real_market_FDR_known"])
        self.assertFalse(out["repeat_same_seeds_is_new_holdout"])
        self.assertTrue(out["all_negative_source_cohorts_retained"])
        self.assertEqual(out["source_json_uncompressed_sha256"],EXPECTED_SHA)
        self.assertEqual(len(SEEDS),40)
        self.assertEqual(len(COHORTS),4)

    def test_exact_nominal_clopper_pearson_frozen_40_trial_integer_cases(self):
        cases={0:(0.,.08809730),6:(.05710226,.29835267),
               7:(.07338273,.32779013),32:(.64352198,.90947759),
               39:(.86841414,.99936726),40:(.91190270,1.)}
        for k,(low,high) in cases.items():
            with self.subTest(successes=k):
                interval=nominal_cp_95(k)
                self.assertAlmostEqual(interval[0],low,places=8)
                self.assertAlmostEqual(interval[1],high,places=8)
        for k,n in ((-1,40),(41,40),(7,39),(True,40),(7,160)):
            with self.assertRaises(ValueError):
                nominal_cp_95(k,n)

    def test_all_four_original_cohorts_negative_errors_and_misses(self):
        x=audit_fixture(self.fixture)["per_cohort"]
        self.assertEqual(x["poisson_noise_null"]["naive_positive"],7)
        self.assertEqual(x["poisson_noise_null"]["grouped_positive"],6)
        self.assertEqual(x["poisson_noise_null"]["paired_print_only_positive"],1)
        self.assertEqual(x["fixed_20s_noise_hard_negative"]["naive_positive"],0)
        self.assertEqual(x["fixed_20s_noise_hard_negative"]["naive_abstain"],1)
        self.assertEqual(x["momentum_noise_hard_negative"]["naive_positive"],7)
        self.assertEqual(x["momentum_noise_hard_negative"]["grouped_positive"],7)
        self.assertEqual(x["twap_45s_positive"]["naive_positive"],39)
        self.assertEqual(x["twap_45s_positive"]["grouped_positive"],32)
        self.assertEqual(x["twap_45s_positive"]["grouped_missed_TWAP"],7)
        self.assertEqual(x["twap_45s_positive"]["naive_abstain"],1)
        self.assertEqual(x["twap_45s_positive"]["paired_print_only_positive"],7)
        self.assertEqual(x["twap_45s_positive"]["paired_group_only_positive"],0)
        self.assertEqual(self.fixture["totals"]["source_L2_snapshots"],253386)
        self.assertEqual(self.fixture["totals"]["source_public_prints"],156234)

    def test_no_posthoc_source_cases_or_decisions_can_be_hidden(self):
        for mutation in (
            lambda x: x["seeds"].pop(),
            lambda x: x["source_cohorts"]["momentum_noise_hard_negative"]["naive_positive_seeds"].pop(),
            lambda x: x["source_cohorts"]["twap_45s_positive"]["grouped_missed_twap_seeds"].pop(),
            lambda x: x["source_cohorts"]["poisson_noise_null"]["naive_abstain_seeds"].append(3316),
            lambda x: x["source_cohorts"].pop("fixed_20s_noise_hard_negative"),
            lambda x: x["source_cohorts"]["poisson_noise_null"].update({"public_prints":0}),
            lambda x: x["source_cohorts"]["poisson_noise_null"].update({"private_agent_id":123}),
            lambda x: x["totals"].update({"source_L2_snapshots":0}),
            lambda x: x.update({"source_full_case_count":320}),
            lambda x: x.update({"original_source_run":0}),
            lambda x: x.update({"original_uncompressed_full_source_json_sha256":"0"*64}),
            lambda x: x["interpretation_flags"].update({"physical_owner_identity_unknown":False}),
            lambda x: x["interpretation_flags"].update({"market_FDR_is_known":True}),
        ):
            d=deepcopy(self.fixture)
            mutation(d)
            with self.assertRaises(ValueError):
                audit_fixture(d)

    def test_missing_or_swapped_source_bytes_cannot_claim_reconciliation(self):
        for raw in (b"",b"{}",b"not even json",json.dumps(self.fixture).encode()):
            with self.assertRaises(ValueError):
                validate_original_source_bytes(raw,self.fixture)


if __name__=="__main__":
    unittest.main(verbosity=2)
