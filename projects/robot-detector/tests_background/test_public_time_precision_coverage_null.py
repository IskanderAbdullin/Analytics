"""Source-free precision quantization, cluster inflation and lagged-L2 tests.

All views derived from FOUR toy tapes, not 52 independent market trials.
"""
import json
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from public_time_precision_coverage_null import (
    Q,COHORTS,L2_COVERAGE,PublicPrint,frozen_protocol,constructed_public_tape,
    precision_view,public_clock_score,full_matrix
)

class FrozenPublicTimePrecisionCoverageControls(unittest.TestCase):
    def test_preregistration_before_source_free_cases(self):
        p=frozen_protocol()
        self.assertEqual(p["source_mode"],
                         "SOURCE_FREE_DETERMINISTIC_PUBLIC_ONLY_TOY_NO_NEW_ENGINE_OR_MARKET_DATA")
        self.assertEqual(p["new_source_seed_values"],[])
        self.assertEqual(p["fixed_public_scoring"]["ratio_threshold_greater_equal"],.60)
        self.assertEqual(p["precision_grid_ns"],list(Q))
        self.assertEqual(p["fixed_source_generation"]["variants"],list(COHORTS))
        self.assertEqual(p["fixed_public_scoring"]["prior_l2_bins_test_values"],list(L2_COVERAGE))
        self.assertTrue(p["frozen_after_source_3301_3340_inspection"])
        self.assertTrue(p["do_not_use_as_independent_real_market_or_new_ABIDES_evidence"])

    def test_all_52_negative_and_positive_views_retained_not_new_holdout(self):
        result=full_matrix()
        self.assertEqual(result["source_free_dependent_views"],52)
        self.assertEqual(result["independent_market_or_ABIDES_source_runs"],0)
        self.assertFalse(result["corresponding_physical_agent_ID_or_market_FDR_known"])
        self.assertTrue(result["all_precommitted_negative_control_views_retained"])
        self.assertEqual(len(result["rows"]),52)
        self.assertEqual({r["cohort"] for r in result["rows"]},set(COHORTS))
        self.assertEqual(sum(r["coverage_or_precision_abstain_reason"]==
                             "UNKNOWN_SOURCE_TIMESTAMP_PRECISION"
                             for r in result["rows"]),4)
        self.assertTrue(all(r["real_market_owner_identity_or_FDR_known"] is False
                            and r["parent_orders_inferred_from_same_timestamp"] is False
                            and r["synthetic_coverage_number_not_actual_L2"] is True
                            for r in result["rows"]))

    def test_nested_rounding_conserves_prints_lots_and_public_order(self):
        for cohort in COHORTS:
            src=constructed_public_tape(cohort)
            sizes=[]
            for q in Q:
                v=precision_view(src,q)
                self.assertEqual(len(src),len(v))
                self.assertEqual(sum(x.lots for x in src),sum(x.lots for x in v))
                self.assertEqual([x.side for x in src],[x.side for x in v])
                self.assertEqual([x.lots for x in src],[x.lots for x in v])
                self.assertEqual(tuple(sorted(x.time_ns for x in v)),
                                 tuple(x.time_ns for x in v))
                sizes.append(len(set(x.time_ns for x in v)))
            self.assertEqual(sizes,sorted(sizes,reverse=True))
            self.assertGreater(sizes[0],sizes[1])
            self.assertEqual(len(src),240+(100 if cohort=="split_100_at_45sec_only_null"
                                         else 0 if cohort=="paired_background_null" else 9))

    def test_no_target_split_fill_is_false_alarm_for_naive_not_timestamp_group(self):
        src=constructed_public_tape("split_100_at_45sec_only_null")
        obs=public_clock_score(
            precision_view(src,1),quantum_ns=1,
            prior_completed_l2_bins=10,precision_certified=True
        )
        self.assertEqual(obs["per_print_decision"],"TARGET_PATTERN")
        self.assertEqual(obs["per_timestamp_decision"],"NO_TARGET_PATTERN")
        self.assertGreater(obs["per_print_ratio"],.60)
        self.assertLess(obs["per_timestamp_ratio"],.60)
        self.assertGreaterEqual(obs["largest_exact_timestamp_print_cluster"],100)
        self.assertFalse(obs["parent_orders_inferred_from_same_timestamp"])

    def test_missing_lagged_l2_or_uncertified_or_coarse_precision_abstains(self):
        src=constructed_public_tape("split_100_at_45sec_only_null")
        cases=((1,4,True,"TOO_FEW_PRIOR_COMPLETED_L2_BINS"),
               (1,10,False,"UNKNOWN_SOURCE_TIMESTAMP_PRECISION"),
               (10_000_000,10,True,"SOURCE_TIMESTAMP_PRECISION_TOO_COARSE"),
               (100_000_000,10,True,"SOURCE_TIMESTAMP_PRECISION_TOO_COARSE"))
        for q,coverage,certified,reason in cases:
            with self.subTest(q=q,coverage=coverage,certified=certified):
                obs=public_clock_score(precision_view(src,q),
                                     quantum_ns=q,
                                     prior_completed_l2_bins=coverage,
                                     precision_certified=certified)
                self.assertEqual(obs["coverage_or_precision_abstain_reason"],reason)
                self.assertEqual(obs["per_print_decision"],"ABSTAIN")
                self.assertEqual(obs["per_timestamp_decision"],"ABSTAIN")
        eligible=public_clock_score(precision_view(src,1),
                                     quantum_ns=1,
                                     prior_completed_l2_bins=5,
                                     precision_certified=True)
        self.assertIsNone(eligible["coverage_or_precision_abstain_reason"])

    def test_strong_negative_and_injected_sparse_pattern_are_reported_not_optimized(self):
        x=full_matrix()["rows"]
        for cohort in COHORTS:
            source=[r for r in x if r["cohort"]==cohort and
                    r["quantization_ns"]==1 and r["previous_only_L2_bin_count"]==10
                    and r["certified_public_time_precision"]]
            self.assertEqual(len(source),1)
        # The constructed positive is *sparse*, and need not pass the
        # frozen ratio. A missed toy pattern must remain an observed outcome.
        pos=next(r for r in x if r["cohort"]=="sparse_public_45sec_positive"
                 and r["quantization_ns"]==1
                 and r["previous_only_L2_bin_count"]==10
                 and r["certified_public_time_precision"])
        self.assertEqual(pos["per_print_decision"],"NO_TARGET_PATTERN")

    def test_private_source_attributes_and_wrong_clock_assumptions_fail_closed(self):
        with self.assertRaises(ValueError):PublicPrint(0,1,"BUY")
        with self.assertRaises(ValueError):PublicPrint(34200000000000,0,"BUY")
        with self.assertRaises(ValueError):PublicPrint(34200000000000,1,"UNKNOWN")
        src=constructed_public_tape("paired_background_null")
        for bad in (0,2_000_000,True):
            with self.assertRaises(ValueError):
                precision_view(src,bad)
        with self.assertRaises(ValueError):
            precision_view(({"time_ns":34200000000000,"agent_id":7},),1)
        with self.assertRaises(ValueError):
            public_clock_score(src,quantum_ns=1,
                               prior_completed_l2_bins=6,precision_certified=True)
        with self.assertRaises(ValueError):
            public_clock_score(src,quantum_ns=1,
                               prior_completed_l2_bins=10,precision_certified="yes")

    def test_frozen_source_plan_cannot_be_rewritten_after_evaluation(self):
        p=frozen_protocol()
        for key,val in (
            ("precision_grid_ns",[1,1_000_000]),
            ("new_source_seed_values",[3301]),
            ("frozen_after_source_3301_3340_inspection",False),
            ("original_inspected_source_seed_range",[3201,3204])
        ):
            change=deepcopy(p)
            change[key]=val
            with patch.object(Path,"read_text",return_value=json.dumps(change)):
                with self.assertRaises(ValueError):
                    frozen_protocol()
        q=deepcopy(p)
        q["fixed_public_scoring"]["ratio_threshold_greater_equal"]=.70
        with patch.object(Path,"read_text",return_value=json.dumps(q)):
            with self.assertRaises(ValueError):
                frozen_protocol()


if __name__=="__main__":
    unittest.main(verbosity=2)
