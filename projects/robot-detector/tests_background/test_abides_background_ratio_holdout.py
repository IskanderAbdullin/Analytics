"""No-network adversarial tests for the frozen 16-case ABIDES source ratio.

Synthetic fixtures here are hand-built; no genuine matching-engine success
is claimed until a separately recorded original source run completes.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from abides_multiscale_public_l2 import public_multiscale_l2_summary
from abides_background_ratio_holdout import (
    SEEDS, COHORTS, THRESHOLD, MIN_PRINTS, MIN_20S_GRID_HITS,
    MIN_LAGGED_L2_BINS, RESULT_FIELDS, frozen_plan,
    check_seed_registry, public_ratio_decision, validate_all_cases
)
from test_abides_multiscale_public_l2 import source_trades,source_book


def public_fixture(*, n=300,h20=20,h45=15,eligible=6):
    """Public-only summary with controlled public synthetic counts."""
    result=deepcopy(public_multiscale_l2_summary(source_trades(),source_book()))
    result["public_prints"]=n
    result["grid_hit_counts"]["20"]=h20
    result["grid_hit_counts"]["45"]=h45
    result["grid_fractions"]["20"]=round(h20/n,8)
    result["grid_fractions"]["45"]=round(h45/n,8)
    z=result["l2_binned_lagged"]["30"]
    z["eligible_previous_completed_book_bins"]=eligible
    z["populated_trade_bins"]=eligible+1
    z["abstained_bins_by_reason"]={"synthetic_missing_prior":1}
    return result


def source_case(seed,cohort, *, h20=20,h45=15):
    # No agent fields enter public_ratio_decision().
    d=public_ratio_decision(public_fixture(h20=h20,h45=h45))
    truth=cohort=="twap_45s_positive"
    decision=d["decision"]
    result={
        "seed":seed,"cohort":cohort,**d,
        "posthoc_target_present":truth,
        "posthoc_controlled_execution_count":3 if truth else 0,
        "classification_correct_when_decided":(
            None if decision=="ABSTAIN" else
            (decision=="TARGET_PATTERN")==truth),
        "false_positive_background":decision=="TARGET_PATTERN" and not truth,
        "false_negative_injected_target":decision=="NO_TARGET_PATTERN" and truth
    }
    assert set(result)==RESULT_FIELDS
    return result


class FrozenABIDESBackgroundRatioStudyTests(unittest.TestCase):
    def test_frozen_study_and_canonical_new_seed_registry(self):
        plan=frozen_plan()
        self.assertEqual(plan["simulator_cohorts"],list(COHORTS))
        self.assertEqual(plan["local_new_seed_candidates"],list(SEEDS))
        self.assertEqual(plan["original_independent_source_runs_planned"],16)
        self.assertEqual(THRESHOLD,0.60)
        self.assertEqual(MIN_PRINTS,200)
        self.assertEqual(MIN_20S_GRID_HITS,8)
        self.assertEqual(MIN_LAGGED_L2_BINS,5)
        self.assertTrue(plan["globally_blind_independence_not_certified"])
        self.assertEqual(plan["new_evaluation_source_status"],"NOT_RUN")
        self.assertTrue(plan["oracle_target_labels_only_after_public_inference"])
        check_seed_registry()

    def test_ratio_exact_frozen_rule_and_source_only_fields(self):
        x=public_ratio_decision(public_fixture(h20=10,h45=6))
        self.assertEqual(x["decision"],"TARGET_PATTERN")
        self.assertAlmostEqual(x["observed_ratio_45s_over_20s"],0.6)
        self.assertIsNone(x["abstain_reason"])
        self.assertFalse(x["quote_stream_completeness_known"])
        self.assertFalse(x["public_features_accessed_oracle_agent_IDs"])
        self.assertFalse(x["real_market_actor_accuracy_or_FDR_calibrated"])
        q=public_ratio_decision(public_fixture(h20=10,h45=5))
        self.assertEqual(q["decision"],"NO_TARGET_PATTERN")
        self.assertEqual(q["observed_ratio_45s_over_20s"],0.5)

    def test_abstention_priority_public_prints_hits_and_l2_quality(self):
        variants=[
            (dict(n=199,h20=0,h45=0,eligible=0),"TOO_FEW_PUBLIC_PRINTS"),
            (dict(n=300,h20=7,h45=7,eligible=0),"TOO_FEW_20S_CLOCK_HITS"),
            (dict(n=300,h20=8,h45=8,eligible=4),"TOO_FEW_ELIGIBLE_COMPLETED_L2_BINS"),
            (dict(n=300,h20=0,h45=1,eligible=8),"TOO_FEW_20S_CLOCK_HITS")
        ]
        for args,code in variants:
            with self.subTest(reason=code):
                out=public_ratio_decision(public_fixture(**args))
                self.assertEqual(out["decision"],"ABSTAIN")
                self.assertEqual(out["abstain_reason"],code)
                if args["h20"]==0:
                    self.assertIsNone(out["observed_ratio_45s_over_20s"])

    def test_strict_public_only_schema_rejects_private_or_invalid_coverage(self):
        root=public_fixture()
        for changed in (
            {"owner_id":"PRIVATE"},
            {"actual_private_agent_ids_accessed":True},
            {"private_id_leakage_from_L2_features":True},
            {"source_complete_exchange_sequence_proven":True},
            {"raw_quote_rows_or_l2_observations_exported":True},
            {"public_only_feature_input_type_verified":False},
            {"public_prints":0},
            {"grid_hit_counts":{"10":0,"20":301,"45":2,"90":0}},
            {"l2_binned_lagged":{"30":root["l2_binned_lagged"]["30"]}}
        ):
            x=deepcopy(root)
            x.update(changed)
            with self.subTest(changed=list(changed)),self.assertRaises(ValueError):
                public_ratio_decision(x)
        x=deepcopy(root)
        x["l2_binned_lagged"]["30"]["eligible_previous_completed_book_bins"]=-1
        with self.assertRaises(ValueError):
            public_ratio_decision(x)

    def test_all_sixteen_cases_keep_hard_false_alarms_and_misses(self):
        cases=[]
        for seed in SEEDS:
            for cohort in COHORTS:
                # Construct both negative controls and a positive miss so
                # results are not silently filtered or relabelled.
                hits45=(
                    1 if cohort=="poisson_noise_null" else
                    15 if cohort=="fixed_20s_noise_hard_negative" else
                    2 if cohort=="momentum_noise_hard_negative" else 3
                )
                cases.append(source_case(seed,cohort,h20=20,h45=hits45))
        result=validate_all_cases(cases)
        self.assertEqual(result["original_matching_engine_runs"],16)
        summary=result["cohort_results"]
        self.assertEqual(summary["fixed_20s_noise_hard_negative"]["false_alarms"],4)
        self.assertEqual(summary["twap_45s_positive"]["missed_targets"],4)
        self.assertEqual(summary["poisson_noise_null"]["alarms"],0)
        self.assertEqual(summary["twap_45s_positive"]["posthoc_controlled_fills"],12)
        self.assertTrue(result["negative_results_retained_without_posthoc_tuning"])
        self.assertFalse(result["any_real_market_owner_FDR_or_precision_claim"])
        self.assertFalse(result["raw_trade_l2_or_private_agent_IDs_exported"])

    def test_missing_duplicates_and_fabricated_outcomes_fail(self):
        cases=[source_case(s,c) for s in SEEDS for c in COHORTS]
        for rows in (cases[:-1],cases+cases[:1]):
            with self.assertRaises(ValueError):
                validate_all_cases(rows)
        bad=deepcopy(cases)
        bad[0]["posthoc_target_present"]=True
        with self.assertRaises(ValueError):
            validate_all_cases(bad)
        bad=deepcopy(cases)
        bad[1]["oracle_agent_id"]=17
        with self.assertRaises(ValueError):
            validate_all_cases(bad)
        bad=deepcopy(cases)
        bad[1]["observed_ratio_45s_over_20s"]=0.55
        with self.assertRaises(ValueError):
            validate_all_cases(bad)
        bad=deepcopy(cases)
        bad[1]["decision"]="ABSTAIN"
        with self.assertRaises(ValueError):
            validate_all_cases(bad)

    def test_all_original_sixteen_source_results_and_false_alarm_integrity(self):
        source=Path(__file__).resolve().parents[1]/"fixtures"/"abides_background_ratio_original_20261121.json"
        original=json.loads(source.read_text(encoding="utf-8"))
        self.assertEqual(original["original_genuine_abides_run_id"],44936592641)
        self.assertEqual(original["source_aggregate_artifact_id"],14720095531)
        self.assertEqual(original["independent_matching_engine_runs"],16)
        self.assertEqual(original["local_seeds"],list(SEEDS))
        cases=original["original_anonymous_case_aggregates"]
        self.assertEqual(len(cases),16)
        self.assertEqual(sum(x["prints"] for x in cases),15949)
        self.assertEqual(sum(x["L2"] for x in cases),25727)
        self.assertEqual(sum(x["posthoc_target_fills"] for x in cases),74)
        self.assertEqual({(x["seed"],x["cohort"]) for x in cases},
                         {(s,c) for s in SEEDS for c in COHORTS})
        for row in cases:
            self.assertGreaterEqual(row["prints"],MIN_PRINTS)
            self.assertGreaterEqual(row["20s_hits"],MIN_20S_GRID_HITS)
            self.assertGreaterEqual(row["eligible_prev_l2_bins"],MIN_LAGGED_L2_BINS)
            self.assertEqual(row["ratio"],round(row["45s_hits"]/row["20s_hits"],8))
            self.assertEqual(row["decision"],
                "TARGET_PATTERN" if row["45s_hits"]/row["20s_hits"]>=THRESHOLD
                else "NO_TARGET_PATTERN")
            self.assertIsNone(row["abstain_reason"])
            self.assertFalse(row["real_market_FDR_known"])
        cohorts=original["source_cohorts"]
        self.assertEqual(cohorts["twap_45s_positive"]["alarms"],4)
        self.assertEqual(cohorts["twap_45s_positive"]["posthoc_controlled_fills"],74)
        self.assertEqual(cohorts["fixed_20s_noise_hard_negative"]["false_alarms"],0)
        self.assertEqual(cohorts["poisson_noise_null"]["false_alarms"],0)
        self.assertEqual(cohorts["momentum_noise_hard_negative"]["false_alarms"],2)
        self.assertEqual(original["source_abstention_total"],0)
        self.assertFalse(original["real_market_actor_ownership_and_FDR_calibrated"])
        self.assertTrue(original["ratio_is_not_calibrated_market_probability"])

    def test_posthoc_threshold_rewrite_detected_in_frozen_plan(self):
        cfg=frozen_plan()
        for field,value in (
            ("target_positive_if_ratio_greater_or_equal",0.7),
            ("local_new_seed_candidates",[3001,3002]),
            ("new_evaluation_source_status","SUCCESS"),
            ("oracle_target_labels_only_after_public_inference",False),
            ("original_independent_source_runs_planned",12)
        ):
            changed=deepcopy(cfg)
            changed[field]=value
            with patch.object(Path,"read_text",return_value=json.dumps(changed)):
                with self.subTest(field=field),self.assertRaises(ValueError):
                    frozen_plan()


if __name__=="__main__":
    unittest.main(verbosity=2)
