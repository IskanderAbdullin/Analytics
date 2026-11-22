"""Frozen source-free 7-period phase-shift and tied-fill negative checks."""
import json
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from l2_trade_context import PublicExecution
from public_interarrival_period_scan_negative import (
    PERIODS,SHIFTS_NS,TOLERANCE_NS,frozen_protocol,
    make_public,audit_public,original_negative_matrix
)

class PrecommittedPeriodScanNegatives(unittest.TestCase):
    def test_frozen_protocol_seven_periods_two_shifts(self):
        p=frozen_protocol()
        self.assertEqual(PERIODS,(10,15,20,30,45,60,90))
        self.assertEqual(SHIFTS_NS,(0,1_000_000_000))
        self.assertEqual(TOLERANCE_NS,250_000_000)
        self.assertEqual(p["source_unique_event_count"],90)
        self.assertEqual(p["source_equal_timestamp_extra_prints_in_split_variant"],99)
        self.assertTrue(p["no_market_FDR_p_value_or_owner_identity_claim"])

    def test_phase_shift_erases_anchored_hits_but_not_unrelated_interarrival(self):
        original=audit_public(make_public(global_shift_ns=0,add_split_fills=False))
        shifted=audit_public(make_public(global_shift_ns=1_000_000_000,add_split_fills=False))
        self.assertEqual(original["source_prints"],90)
        self.assertEqual(shifted["source_unique_times"],90)
        a=original["period_grid_all_frozen_candidates"]["20"]
        b=shifted["period_grid_all_frozen_candidates"]["20"]
        self.assertEqual(a["absolute_grid_print_hits"],90)
        self.assertEqual(b["absolute_grid_print_hits"],0)
        self.assertEqual(a["consecutive_unique_interarrival_hits"],89)
        self.assertEqual(b["consecutive_unique_interarrival_hits"],89)
        for k in map(str,PERIODS):
            x=original["period_grid_all_frozen_candidates"][k]
            y=shifted["period_grid_all_frozen_candidates"][k]
            self.assertEqual(y["absolute_grid_print_hits"],0)
            self.assertEqual(y["consecutive_unique_interarrival_hits"],
                             x["consecutive_unique_interarrival_hits"])

    def test_one_hundred_split_fills_create_false_clock_concentration(self):
        x=audit_public(make_public(global_shift_ns=0,add_split_fills=True))
        self.assertEqual((x["source_prints"],x["source_unique_times"]),(190,91))
        self.assertEqual(x["same_timestamp_extra_prints"],99)
        self.assertEqual(x["zero_length_print_interarrival_count"],99)
        self.assertEqual(x["period_grid_all_frozen_candidates"]["45"][
            "absolute_grid_print_hits"],110)
        self.assertEqual(x["period_grid_all_frozen_candidates"]["45"][
            "absolute_grid_unique_time_hits"],11)
        self.assertEqual(x["period_grid_all_frozen_candidates"]["20"][
            "consecutive_unique_interarrival_hits"],88)
        self.assertFalse(x["calibrated_market_significance_or_FDR"])

    def test_all_four_cases_all_frozen_periods_not_cherry_picked(self):
        r=original_negative_matrix()
        cases=r["four_precommitted_public_source_cases"]
        self.assertEqual(len(cases),4)
        for row in cases:
            self.assertEqual(set(row["period_grid_all_frozen_candidates"]),
                             set(map(str,PERIODS)))
            self.assertFalse(row["calibrated_market_significance_or_FDR"])
        self.assertTrue(r["no_source_injected_45s_agent_in_any_case"])
        self.assertTrue(r["posthoc_best_period_or_phase_was_not_selected"])
        self.assertFalse(r["real_market_pvalues_FDR_or_actor_labels_calibrated"])
        self.assertFalse(r["actual_exchange_or_ABIDES_source_accessed"])

    def test_reject_private_type_unsorted_and_bogus_phase(self):
        data=make_public(global_shift_ns=0,add_split_fills=False)
        for wrong in (
            list(data),data[::-1],data[:3],
            ({"owner_id":5,"time_ns":data[0].time_ns},),
            (PublicExecution(-1,100100,1,"BUY"),)*12,
            (PublicExecution(data[0].time_ns,100100,0,"BUY"),)*12
        ):
            with self.assertRaises(ValueError):
                audit_public(wrong)
        for shift in (-1,True,2_000_000_000,0.0):
            with self.assertRaises(ValueError):
                make_public(global_shift_ns=shift,add_split_fills=False)
        with self.assertRaises(ValueError):
            make_public(global_shift_ns=0,add_split_fills=1)

    def test_saved_four_by_seven_original_negative_aggregates_match_source_code(self):
        f=Path(__file__).resolve().parents[1]/"fixtures"/"public_interarrival_period_scan_observed_20261121.json"
        saved=json.loads(f.read_text(encoding="utf-8"))
        computed=original_negative_matrix()
        self.assertEqual(saved["source_free_verification_ci_run"],44945259589)
        self.assertEqual(
            {k:v for k,v in saved.items() if k!="source_free_verification_ci_run"},
            computed
        )
        self.assertEqual(len(saved["four_precommitted_public_source_cases"]),4)
        self.assertEqual(sum(len(c["period_grid_all_frozen_candidates"])
                             for c in saved["four_precommitted_public_source_cases"]),28)
        self.assertTrue(saved["timestamp_split_fills_not_independent_parent_orders"])
        self.assertFalse(saved["actual_exchange_or_ABIDES_source_accessed"])

    def test_refuse_protocol_edits_after_frozen_design(self):
        p=frozen_protocol()
        for k,value in (
            ("scan_periods_seconds",[20,45]),
            ("grid_tolerance_ns",500_000_000),
            ("source_global_clock_shifts_ns",[0]),
            ("no_market_FDR_p_value_or_owner_identity_claim",False)
        ):
            changed=deepcopy(p)
            changed[k]=value
            with patch.object(Path,"read_text",return_value=json.dumps(changed)):
                with self.assertRaises(ValueError):
                    frozen_protocol()

if __name__=="__main__":
    unittest.main(verbosity=2)
