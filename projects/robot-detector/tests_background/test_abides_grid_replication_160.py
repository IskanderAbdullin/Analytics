"""No-network integrity tests: 40 locally new seeds x four ABIDES cohorts."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from abides_grid_replication_160 import SEEDS,COHORTS,CASE_FIELDS,frozen_protocol,check_ledger,_decode_decision,validate_source_report

def fake_case(seed,cohort):
    target=cohort=="twap_45s_positive"
    old,owhy=_decode_decision(220,12,9,6,grouped=False)
    new,nwhy=_decode_decision(220,10,7,6,grouped=True)
    d={
        "source_seed":seed,"source_cohort":cohort,
        "synthetic_target_present_posthoc":target,
        "public_prints":220,"unique_execution_timestamps":205,
        "same_timestamp_extra_prints":15,"largest_timestamp_cluster_prints":16,
        "public_L2_snapshot_events":200,"eligible_previous_completed_30s_L2_bins":6,
        "public_tape_sha256":"a"*64,
        "per_print_hits20":12,"per_print_hits45":9,
        "per_unique_timestamp_hits20":10,"per_unique_timestamp_hits45":7,
        "per_print_ratio_45_over_20":0.75,"per_unique_ratio_45_over_20":0.7,
        "per_print_decision":old,"per_unique_decision":new,
        "per_print_abstain_reason":owhy,"per_unique_abstain_reason":nwhy,
        "posthoc_controlled_TWAP_fills":3 if target else 0,
        "per_print_false_alarm":not target and old=="TARGET_PATTERN",
        "per_unique_false_alarm":not target and new=="TARGET_PATTERN",
        "per_print_missed_TWAP":target and old=="NO_TARGET_PATTERN",
        "per_unique_missed_TWAP":target and new=="NO_TARGET_PATTERN",
        "private_oracle_agent_IDs_entered_public_features":False,
        "actual_market_owner_identity_or_FDR_known":False,
        "source_complete_real_exchange_feed_proven":False,
        "raw_prints_or_L2_snapshots_exported":False
    }
    assert set(d)==CASE_FIELDS
    return d

class Frozen160SourceTests(unittest.TestCase):
    def test_original_precommit_local_seeds_and_engine_provenance(self):
        p=frozen_protocol()
        self.assertEqual((len(SEEDS),min(SEEDS),max(SEEDS)),(40,3301,3340))
        self.assertEqual(p["fixed_new_seed_values"],list(SEEDS))
        self.assertEqual(p["planned_engine_cases"],160)
        self.assertEqual(p["cohorts"],list(COHORTS))
        self.assertEqual(p["source_status_at_design"],"NOT_RUN")
        self.assertEqual(p["frozen_baseline"]["per_print_ratio_threshold_greater_equal"],.6)
        self.assertEqual(p["frozen_baseline"]["per_unique_timestamp_ratio_threshold_greater_equal"],.6)
        self.assertTrue(p["no_real_market_FDR_or_owner_accuracy_claim"])
        self.assertTrue(p["no_raw_trades_L2_rows_private_agent_or_order_ids_in_artifact"])
        check_ledger()

    def test_coverage_abstention_not_zero_denominator_fabrication(self):
        for n,h20,h45,lag,grouped,code in [
            (199,0,0,0,False,"TOO_FEW_PUBLIC_PRINTS"),
            (220,7,3,6,False,"TOO_FEW_20S_CLOCK_HITS"),
            (220,7,3,6,True,"TOO_FEW_DISTINCT_20S_HITS"),
            (220,10,2,4,True,"TOO_FEW_ELIGIBLE_COMPLETED_L2_BINS")
        ]:
            with self.subTest(code=code):
                self.assertEqual(_decode_decision(n,h20,h45,lag,grouped=grouped),
                                 ("ABSTAIN",code))
        self.assertEqual(_decode_decision(220,10,6,5,grouped=True),("TARGET_PATTERN",None))
        self.assertEqual(_decode_decision(220,10,5,5,grouped=False),("NO_TARGET_PATTERN",None))
        for n,h20,h45,lag in [(True,2,3,4),(100,101,3,6),(1,1,-1,4),(1,1,1,-1)]:
            with self.assertRaises(ValueError):
                _decode_decision(n,h20,h45,lag,grouped=False)

    def test_all_160_cases_reconcile_and_keep_synthetic_negative_outcomes(self):
        rows=[fake_case(s,c) for s in SEEDS for c in COHORTS]
        x=validate_source_report(rows)
        self.assertEqual(x["original_matching_engine_source_case_count"],160)
        self.assertEqual(len(x["all_original_160_anonymous_case_aggregates"]),160)
        self.assertEqual(x["local_new_source_seeds_not_certified_globally_blind"],list(SEEDS))
        self.assertTrue(x["oracle_used_only_after_public_feature"])
        self.assertFalse(x["physical_owner_or_real_market_FDR_calibrated"])
        for c in COHORTS:
            s=x["source_cohorts"][c]
            self.assertEqual(s["independent_local_seed_engine_runs"],40)
            self.assertEqual(s["source_executions"],8800)
            self.assertEqual(s["source_unique_timestamps"],8200)
            self.assertEqual(s["paired_both_positive"],40)
            self.assertEqual(s["paired_any_abstention"],0)
        self.assertEqual(x["source_cohorts"]["twap_45s_positive"]["posthoc_controlled_TWAP_fills"],120)
        self.assertEqual(x["source_cohorts"]["poisson_noise_null"]["per_print_false_alarms"],40)

    def test_missing_duplicates_wrong_inference_or_oracle_leak_fail_closed(self):
        rows=[fake_case(s,c) for s in SEEDS for c in COHORTS]
        for broken in (rows[:-1],rows+rows[:1]):
            with self.assertRaises(ValueError):
                validate_source_report(broken)
        for k,v in [
            ("private_agent_id",3),("public_prints",100),
            ("same_timestamp_extra_prints",0),("per_print_ratio_45_over_20",.99),
            ("per_print_decision","NO_TARGET_PATTERN"),
            ("per_print_false_alarm",False),
            ("synthetic_target_present_posthoc",True),
            ("actual_market_owner_identity_or_FDR_known",True),
            ("raw_prints_or_L2_snapshots_exported",True)
        ]:
            mutated=deepcopy(rows)
            mutated[0][k]=v
            with self.subTest(field=k),self.assertRaises(ValueError):
                validate_source_report(mutated)

    def test_original_source_precommit_rejects_posthoc_edit(self):
        p=frozen_protocol()
        for k,v in [
            ("planned_engine_cases",40),("source_status_at_design","SUCCESS"),
            ("fixed_new_seed_values",[3301]),("source_engine_revision","mutable"),
            ("local_seed_novelty_only_not_globally_blind",False)
        ]:
            modified=deepcopy(p)
            modified[k]=v
            with self.subTest(field=k),patch.object(
                Path,"read_text",return_value=json.dumps(modified)
            ),self.assertRaises(ValueError):
                frozen_protocol()
        changed=deepcopy(p)
        changed["frozen_baseline"]["per_unique_timestamp_ratio_threshold_greater_equal"]=.8
        with patch.object(Path,"read_text",return_value=json.dumps(changed)):
            with self.assertRaises(ValueError):
                frozen_protocol()

if __name__=="__main__":
    unittest.main(verbosity=2)
