"""Source-free negative controls for independent split-half momentum ABIDES study.

These synthetic prints/books are NOT a genuine ABIDES outcome. Source run
must independently cover original seeds 3101..3104 after this test passes.
"""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch
import json

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from l2_trade_context import PublicExecution
from abides_split_half_momentum_holdout import (
    SEEDS,COHORTS,BEGIN_NS,SPLIT_NS,END_NS,CASE_FIELDS,
    HALF_MIN_PRINTS,HALF_MIN_HITS20,HALF_MIN_ELIGIBLE_LAG,
    RATIO_THRESHOLD,frozen_plan,check_seeds,
    public_half_stability,validate_source_cases
)

NS=1_000_000_000
ANCHOR=34_260*NS

def fake_book():
    t=tuple(BEGIN_NS+i*5*NS for i in range(96))
    return SimpleNamespace(
        times_ns=t,
        bids=tuple([(100_000,100)] for _ in t),
        asks=tuple([(100_200,120)] for _ in t)
    )


def fake_public(*, inject_periodic=False, late_empty=False):
    trades=[]
    for t in range(0,480 if not late_empty else 240):
        trades.append(PublicExecution(BEGIN_NS+t*NS,100_100,1,
                                      "BUY" if t%2==0 else "SELL"))
    if inject_periodic:
        # All 45s lattice points in 8 minutes. Two extra public prints
        # at each fixed grid timestamp. Same-timestamp split fills are
        # allowed in a PUBLIC tape, but not called independent owners.
        for j in range(12):
            t=ANCHOR+j*45*NS
            if BEGIN_NS<=t<END_NS and (not late_empty or t<SPLIT_NS):
                trades.extend([
                    PublicExecution(t,100_100,1,"BUY"),
                    PublicExecution(t,100_100,2,"BUY")
                ])
    return tuple(sorted(trades,key=lambda x:x.time_ns))


def case(s,c,base_result):
    x=deepcopy(base_result)
    target=c=="twap_45s_positive"
    dec=x["new_split_half_decision"]
    x.update({
        "seed":s,"cohort":c,
        "posthoc_injected_target_present":target,
        "posthoc_controlled_twap_execution_count":8 if target else 0,
        "new_source_false_alarm":dec=="TARGET_PATTERN" and not target,
        "new_source_target_missed":dec=="NO_TARGET_PATTERN" and target,
        "new_source_target_abstained":dec=="ABSTAIN" and target
    })
    assert set(x)==CASE_FIELDS
    return x


class FrozenSplitHalfPublicNegatives(unittest.TestCase):
    def test_precommit_is_explicitly_postprior_and_source_seeds_are_reserved(self):
        p=frozen_plan()
        self.assertEqual(p["new_locally_unused_seed_candidates"],list(SEEDS))
        self.assertEqual(p["original_matching_engine_cases_planned"],16)
        self.assertEqual(p["original_previous_source_run_inspected"],44936592641)
        self.assertEqual(p["half_open_intervals_exchange_local"],
                         [["09:30:00","09:34:00"],["09:34:00","09:38:00"]])
        self.assertEqual(p["cohorts"],list(COHORTS))
        self.assertEqual((HALF_MIN_PRINTS,HALF_MIN_HITS20,HALF_MIN_ELIGIBLE_LAG),
                         (100,4,2))
        self.assertEqual(RATIO_THRESHOLD,0.6)
        self.assertFalse(p["globally_blind_unseen_seed_claim"])
        self.assertTrue(p["synthetic_oracle_agent_ids_only_accessible_after_all_public_feature_scoring"])
        check_seeds()

    def test_two_half_clocks_remain_public_and_no_prepost_L2_lookahead(self):
        source=public_half_stability(fake_public(),fake_book())
        self.assertEqual(len(source["per_half_public_only"]),2)
        self.assertEqual(source["public_executed_prints"],480)
        self.assertEqual([h["half"] for h in source["per_half_public_only"]],
                         ["early","late"])
        self.assertEqual([h["public_execution_prints"] for h in
                          source["per_half_public_only"]],[240,240])
        self.assertEqual(source["new_split_half_decision"],"NO_TARGET_PATTERN")
        self.assertIsNone(source["new_split_half_abstain_reason"])
        self.assertFalse(source["public_feature_touched_private_agent_IDs"])
        self.assertFalse(source["real_market_owner_FDR_or_accuracy_calibrated"])
        self.assertFalse(source["source_complete_exchange_feed_proven"])
        for half in source["per_half_public_only"]:
            self.assertTrue(half["passes_minimum_observability"])
            self.assertFalse(half["private_agent_IDs_used"])
            self.assertGreaterEqual(half["eligible_completed_previous_30s_l2_bins"],2)

    def test_public_periodic_injection_stably_raises_both_ratios_without_oracle(self):
        source=public_half_stability(fake_public(inject_periodic=True),fake_book())
        self.assertEqual(source["new_split_half_decision"],"TARGET_PATTERN")
        for half in source["per_half_public_only"]:
            self.assertGreaterEqual(half["observed_hit_ratio_45_over_20"],0.6)
            self.assertTrue(half["passes_minimum_observability"])
        self.assertFalse(source["public_feature_touched_private_agent_IDs"])
        self.assertIsNone(source["new_split_half_abstain_reason"])

    def test_second_half_empty_abstains_not_a_negative_class(self):
        source=public_half_stability(fake_public(late_empty=True),fake_book())
        self.assertEqual(source["new_split_half_decision"],"ABSTAIN")
        self.assertEqual(source["per_half_public_only"][0]["public_execution_prints"],240)
        self.assertEqual(source["per_half_public_only"][1]["public_execution_prints"],0)
        self.assertEqual(source["per_half_public_only"][1]["abstain_reason"],"NO_PUBLIC_PRINTS")
        self.assertEqual(source["new_split_half_abstain_reason"],"late:NO_PUBLIC_PRINTS")

    def test_timestamp_exact_split_boundary_enters_only_second_half(self):
        single=PublicExecution(SPLIT_NS,100_100,1,"BUY")
        public=fake_public()+(single,)
        sorted_public=tuple(sorted(public,key=lambda x:x.time_ns))
        source=public_half_stability(sorted_public,fake_book())
        self.assertEqual([h["public_execution_prints"] for h in
                          source["per_half_public_only"]],[240,241])
        self.assertEqual(sum(h["public_execution_prints"] for h in
                             source["per_half_public_only"]),481)

    def test_invalid_source_time_and_private_type_rejected(self):
        for invalid in (
            (PublicExecution(BEGIN_NS-1,100_000,1,"BUY"),),
            (PublicExecution(END_NS,100_000,1,"BUY"),),
            ({"private_agent_id":7,"time_ns":BEGIN_NS},),
            (PublicExecution(BEGIN_NS,100_000,1,"BUY"),)*0
        ):
            with self.subTest(value=str(invalid)[:25]),self.assertRaises(ValueError):
                public_half_stability(invalid,fake_book())
        with self.assertRaises(ValueError):
            public_half_stability(fake_public(),None)
        with self.assertRaises(ValueError):
            public_half_stability(list(fake_public()),fake_book())

    def test_full_synthetic_sixteen_reconciliation_retains_hard_negative(self):
        positive=public_half_stability(fake_public(inject_periodic=True),fake_book())
        negative=public_half_stability(fake_public(),fake_book())
        rows=[]
        for seed in SEEDS:
            for cohort in COHORTS:
                # A no-target fixed background may have a public periodic
                # print pattern identical to an injected synthetic target.
                x=positive if cohort in ("fixed_20s_noise_hard_negative",
                                          "twap_45s_positive") else negative
                rows.append(case(seed,cohort,x))
        out=validate_source_cases(rows)
        self.assertEqual(out["original_matching_engine_cases"],16)
        self.assertEqual(out["cohort_results"]["fixed_20s_noise_hard_negative"][
            "false_positive_background"],4)
        self.assertEqual(out["cohort_results"]["twap_45s_positive"][
            "new_positive_alarms"],4)
        self.assertEqual(out["cohort_results"]["twap_45s_positive"][
            "posthoc_controlled_fills"],32)
        self.assertEqual(out["cohort_results"]["poisson_noise_null"][
            "new_positive_alarms"],0)
        self.assertFalse(out["source_complete_exchange_order_sequence_certified"])
        self.assertFalse(out["injected_agent_or_account_IDs_in_public_data"])

    def test_missing_or_fabricated_cases_cannot_pass_reconciliation(self):
        base=public_half_stability(fake_public(),fake_book())
        rows=[case(seed,cohort,base) for seed in SEEDS for cohort in COHORTS]
        for broken in (rows[:15],rows+rows[:1]):
            with self.assertRaises(ValueError):
                validate_source_cases(broken)
        for key,badval in (
            ("private_owner_id","PRIVATE"),
            ("posthoc_injected_target_present",True),
            ("original_source_raw_print_or_l2_rows_exported",True),
            ("real_market_owner_FDR_or_accuracy_calibrated",True),
            ("source_complete_exchange_feed_proven",True)
        ):
            altered=deepcopy(rows)
            altered[0][key]=badval
            with self.subTest(key=key),self.assertRaises(ValueError):
                validate_source_cases(altered)
        altered=deepcopy(rows)
        altered[0]["per_half_public_only"][1]["observed_hit_ratio_45_over_20"]=0.99
        with self.assertRaises(ValueError):
            validate_source_cases(altered)

    def test_protocol_drift_rejected_before_new_independent_engine_samples(self):
        p=frozen_plan()
        for key,value in (
            ("new_locally_unused_seed_candidates",[3001,3002]),
            ("original_matching_engine_cases_planned",15),
            ("fixed_split_clock_exchange_local","09:35:00"),
            ("globally_blind_unseen_seed_claim",True)
        ):
            bad=deepcopy(p)
            bad[key]=value
            with patch.object(Path,"read_text",return_value=json.dumps(bad)):
                with self.assertRaises(ValueError):
                    frozen_plan()
        bad=deepcopy(p)
        bad["public_only_feature"]["half_minimum_public_20s_hits"]=0
        with patch.object(Path,"read_text",return_value=json.dumps(bad)):
            with self.assertRaises(ValueError):
                frozen_plan()

if __name__=="__main__":
    unittest.main(verbosity=2)
