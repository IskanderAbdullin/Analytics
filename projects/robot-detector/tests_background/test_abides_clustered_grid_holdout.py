"""Research-only ABIDES public timestamp clustering and negative/oracle contracts."""
from copy import deepcopy
from pathlib import Path
import json
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from l2_trade_context import PublicExecution
from abides_multiscale_public_l2 import public_multiscale_l2_summary
from abides_clustered_grid_holdout import (
    SEEDS,COHORTS,FIELDS,THRESHOLD,MIN_PRINTS,
    CLUSTER_MIN_HITS20,frozen_plan,check_seed_registry,
    score_public_timestamp_clusters,validate_original_cases
)
from test_abides_multiscale_public_l2 import source_trades,source_book


def synthetic_public_and_measured():
    original=source_trades()
    observed=public_multiscale_l2_summary(original,source_book())
    return original,observed


def fake_case(seed,cohort,scored):
    result=deepcopy(scored)
    target=cohort=="twap_45s_positive"
    old=result["original_per_print_decision"]
    new=result["grouped_timestamp_decision"]
    result.update({
        "seed":seed,"cohort":cohort,
        "posthoc_injected_target_present":target,
        "posthoc_source_controlled_TWAP_fills":5 if target else 0,
        "original_per_print_false_alarm":old=="TARGET_PATTERN" and not target,
        "grouped_timestamp_false_alarm":new=="TARGET_PATTERN" and not target,
        "original_per_print_target_miss":old=="NO_TARGET_PATTERN" and target,
        "grouped_timestamp_target_miss":new=="NO_TARGET_PATTERN" and target,
        "original_per_print_target_abstained":old=="ABSTAIN" and target,
        "grouped_timestamp_target_abstained":new=="ABSTAIN" and target,
    })
    assert set(result)==FIELDS
    return result


class OriginalABIDESClusterStudyOfflineNegatives(unittest.TestCase):
    def test_original_frozen_protocol_and_new_local_seed_reservation(self):
        p=frozen_plan()
        self.assertEqual(p["new_local_seed_candidates"],[3201,3202,3203,3204])
        self.assertEqual(p["cohorts"],list(COHORTS))
        self.assertEqual(p["planned_independent_matching_engine_runs"],16)
        self.assertEqual(p["previous_inspected_source_runs"],[44936592641,44937478576])
        self.assertEqual(p["motivating_exact_toy_source_ci"],44938416432)
        self.assertEqual(p["new_source_status"],"NOT_RUN")
        self.assertEqual(p["source_type"],
                         "genuine ABIDES-NG matching engine synthetic ONLY")
        self.assertTrue(p["globally_blind_seed_novelty_not_certified"])
        self.assertEqual(p["frozen_clock_feature"][
            "min_grid20_distinct_timestamp_hits_for_cluster_decision"],8)
        self.assertEqual(p["frozen_clock_feature"][
            "new_timestamp_cluster_grid_ratio_threshold"],0.6)
        self.assertTrue(p["posthoc_private_TWAP_agent_labels_only_after_both_public_scores"])
        check_seed_registry()

    def test_public_tiny_source_has_no_private_owner_and_abstains(self):
        public,measured=synthetic_public_and_measured()
        x=score_public_timestamp_clusters(public,measured)
        self.assertEqual(x["public_execution_prints"],len(public))
        self.assertEqual(x["distinct_execution_timestamp_clusters"],len(public))
        self.assertEqual(x["dependent_same_timestamp_extra_prints"],0)
        self.assertEqual(x["largest_exact_timestamp_cluster"],1)
        self.assertEqual(x["original_per_print_decision"],"ABSTAIN")
        self.assertEqual(x["grouped_timestamp_decision"],"ABSTAIN")
        self.assertEqual(x["grouped_timestamp_abstain_reason"],"TOO_FEW_PUBLIC_PRINTS")
        self.assertFalse(x["public_feature_touched_private_agent_IDs"])
        self.assertFalse(x["actual_real_owner_IDs_available"])
        self.assertFalse(x["real_market_FDR_calibrated"])
        self.assertFalse(x["original_source_complete_real_exchange_feed_proven"])
        self.assertEqual(len(x["public_tape_sha256"]),64)

    def test_same_timestamp_cluster_diagnostic_changes_denominator(self):
        base=source_trades()
        same=PublicExecution(base[1].time_ns,base[1].price_cents,1,
                             base[1].reported_aggressor_side)
        combined=tuple(sorted(base+(same,)*20,key=lambda x:x.time_ns))
        m=public_multiscale_l2_summary(combined,source_book())
        r=score_public_timestamp_clusters(combined,m)
        self.assertEqual(r["public_execution_prints"],len(base)+20)
        self.assertEqual(r["distinct_execution_timestamp_clusters"],len(base))
        self.assertEqual(r["dependent_same_timestamp_extra_prints"],20)
        self.assertEqual(r["largest_exact_timestamp_cluster"],21)
        self.assertGreaterEqual(r["print_grid_hits20"],r["grouped_grid_hits20"])
        self.assertGreaterEqual(r["print_grid_hits45"],r["grouped_grid_hits45"])
        self.assertFalse(r["real_market_FDR_calibrated"])

    def test_invalid_owner_fields_out_of_order_or_data_mismatch_fail(self):
        public,measured=synthetic_public_and_measured()
        bad=deepcopy(measured)
        bad["oracle_owner"]="DO_NOT_PASS"
        with self.assertRaises(ValueError):
            score_public_timestamp_clusters(public,bad)
        with self.assertRaises(ValueError):
            score_public_timestamp_clusters(public[:-1],measured)
        with self.assertRaises(ValueError):
            score_public_timestamp_clusters(public[::-1],measured)
        with self.assertRaises(ValueError):
            score_public_timestamp_clusters(tuple(),measured)
        with self.assertRaises(ValueError):
            score_public_timestamp_clusters(list(public),measured)
        with self.assertRaises(ValueError):
            score_public_timestamp_clusters(
                ({"time_ns":public[0].time_ns,"owner_id":999},),measured)
        invalid=(PublicExecution(-1,100000,1,"BUY"),)
        with self.assertRaises(ValueError):
            score_public_timestamp_clusters(invalid,measured)

    def test_original_abides_day_timestamp_translation_does_not_shift_grid(self):
        from abides_clustered_grid_holdout import DAY_NS
        p,m=synthetic_public_and_measured()
        later=tuple(PublicExecution(
            x.time_ns+19_000*DAY_NS,x.price_cents,x.quantity,
            x.reported_aggressor_side
        ) for x in p)
        book=source_book()
        from types import SimpleNamespace
        later_book=SimpleNamespace(
            times_ns=tuple(t+19_000*DAY_NS for t in book.times_ns),
            bids=book.bids,asks=book.asks
        )
        later_measured=public_multiscale_l2_summary(later,later_book)
        a=score_public_timestamp_clusters(p,m)
        b=score_public_timestamp_clusters(later,later_measured)
        for k in (
            "print_grid_hits20","print_grid_hits45",
            "grouped_grid_hits20","grouped_grid_hits45",
            "per_print_observed_ratio","per_unique_timestamp_observed_ratio",
            "grouped_timestamp_decision","original_per_print_decision"
        ):
            self.assertEqual(a[k],b[k])
        self.assertNotEqual(a["public_tape_sha256"],b["public_tape_sha256"])

    def test_validate_all_cohorts_can_retain_negative_and_positive_abstentions(self):
        public,measured=synthetic_public_and_measured()
        scored=score_public_timestamp_clusters(public,measured)
        cases=[fake_case(seed,cohort,scored) for seed in SEEDS for cohort in COHORTS]
        report=validate_original_cases(cases)
        self.assertEqual(report["independent_genuine_matching_engine_cases"],16)
        self.assertEqual(len(report["original_anonymous_case_aggregates"]),16)
        self.assertEqual(report["locally_new_seed_values_not_globally_blind"],list(SEEDS))
        self.assertEqual(report["source_cohort_comparison"]["twap_45s_positive"][
            "grouped_timestamp_abstentions"],4)
        self.assertEqual(report["source_cohort_comparison"]["poisson_noise_null"][
            "original_print_based_false_alarms"],0)
        self.assertTrue(report["private_simulated_oracle_used_only_after_public_inference"])
        self.assertFalse(report["real_market_owner_FDR_or_precision_calibrated"])
        self.assertFalse(report["raw_event_l2_rows_or_private_agent_IDs_exported"])

    def test_missing_case_or_false_owner_claim_fail_closed(self):
        p,m=synthetic_public_and_measured()
        scored=score_public_timestamp_clusters(p,m)
        cases=[fake_case(seed,cohort,scored) for seed in SEEDS for cohort in COHORTS]
        for wrong in (cases[:15],cases+cases[:1]):
            with self.assertRaises(ValueError):
                validate_original_cases(wrong)
        for key,value in (
            ("real_market_FDR_calibrated",True),
            ("public_feature_touched_private_agent_IDs",True),
            ("source_raw_execution_or_L2_rows_exported",True),
            ("posthoc_injected_target_present",True),
            ("grouped_timestamp_decision","TARGET_PATTERN"),
            ("private_owner_ID",123),
            ("dependent_same_timestamp_extra_prints",100)
        ):
            corrupted=deepcopy(cases)
            corrupted[0][key]=value
            with self.subTest(field=key),self.assertRaises(ValueError):
                validate_original_cases(corrupted)

    def test_modifying_original_source_precommit_is_rejected(self):
        p=frozen_plan()
        for key,v in (
            ("new_local_seed_candidates",[3201]),
            ("planned_independent_matching_engine_runs",4),
            ("source_type","fake exchange source"),
            ("new_source_status","SUCCESS"),
            ("posthoc_private_TWAP_agent_labels_only_after_both_public_scores",False)
        ):
            wrong=deepcopy(p)
            wrong[key]=v
            with self.subTest(key=key),patch.object(
                Path,"read_text",return_value=json.dumps(wrong)
            ),self.assertRaises(ValueError):
                frozen_plan()
        wrong=deepcopy(p)
        wrong["frozen_clock_feature"]["new_timestamp_cluster_grid_ratio_threshold"]=0.8
        with patch.object(Path,"read_text",return_value=json.dumps(wrong)):
            with self.assertRaises(ValueError):
                frozen_plan()

if __name__=="__main__":
    unittest.main(verbosity=2)
