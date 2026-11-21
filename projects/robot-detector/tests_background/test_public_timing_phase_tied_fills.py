"""Adversarial source-free phase shift, timestamp-tie and owner-limit tests."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from l2_trade_context import PublicExecution
from public_timing_phase_tied_fills import (
    FIXED_SHIFTS_MS,THRESHOLD,PERIODS,
    frozen_plan,build_synthetic_public,phase_counts,original_counterexample
)


class FixedPhaseSplitFillNegatives(unittest.TestCase):
    def test_protocol_original_constraints_frozen_before_synthetic_counterexample(self):
        d=frozen_plan()
        self.assertEqual(d["triggering_original_source_runs"],
                         [44936592641,44937478576])
        self.assertEqual(d["grid_periods_seconds"],[20,45])
        self.assertEqual(d["phase_anchor_exchange_local_seconds_after_midnight"],34260)
        self.assertEqual(d["clock_tolerance_nanoseconds"],250_000_000)
        self.assertEqual(d["diagnostic_shifts_milliseconds"],[-300,-250,0,250,300])
        self.assertEqual(THRESHOLD,.60)
        self.assertTrue(d["source_public_baseline"]["all_synthetic_events_are_non_target_background"])
        self.assertTrue(d["synthetic_ties_not_identification_of_parent_order"])
        self.assertFalse(d["real_market_owner_FDR_p_value_or_classifier_accuracy_unavailable"] is False)

    def test_single_print_no_false_alarm_split_one_event_many_fills_false_alarm(self):
        source=build_synthetic_public(split_fills=1)
        split=build_synthetic_public(split_fills=100)
        one=phase_counts(source,shift_ms=0,collapse_same_timestamp=False)
        many=phase_counts(split,shift_ms=0,collapse_same_timestamp=False)
        collapsed=phase_counts(split,shift_ms=0,collapse_same_timestamp=True)
        self.assertEqual((len(source),len(split)),(13,112))
        self.assertEqual(one["hit_counts"],{"20":12,"45":2})
        self.assertEqual(many["hit_counts"],{"20":12,"45":101})
        self.assertEqual(collapsed["hit_counts"],one["hit_counts"])
        self.assertFalse(one["fixed_ratio_0_60_alarm"])
        self.assertTrue(many["fixed_ratio_0_60_alarm"])
        self.assertFalse(collapsed["fixed_ratio_0_60_alarm"])
        self.assertAlmostEqual(many["observed_ratio_45s_over_20s"],101/12)
        self.assertEqual(many["equal_timestamp_repeated_prints"],99)
        self.assertEqual(collapsed["counted_public_observations"],13)
        for row in (one,many,collapsed):
            self.assertFalse(row["physical_order_owner_identity_estimated"])

    def test_all_fixed_shift_boundaries_and_denominator_abstention(self):
        split=build_synthetic_public(split_fills=100)
        scores={ms:phase_counts(split,shift_ms=ms,collapse_same_timestamp=False)
                for ms in FIXED_SHIFTS_MS}
        self.assertEqual(set(scores),{-300,-250,0,250,300})
        for shift in (-250,0,250):
            self.assertTrue(scores[shift]["fixed_ratio_0_60_alarm"])
            self.assertFalse(scores[shift]["abstained_zero_20s_denominator"])
            self.assertEqual(scores[shift]["hit_counts"],{"20":12,"45":101})
        for shift in (-300,300):
            self.assertFalse(scores[shift]["fixed_ratio_0_60_alarm"])
            self.assertTrue(scores[shift]["abstained_zero_20s_denominator"])
            self.assertIsNone(scores[shift]["observed_ratio_45s_over_20s"])
            self.assertEqual(scores[shift]["hit_counts"],{"20":0,"45":0})

    def test_raw_public_input_cannot_accept_an_oracle_or_extra_field(self):
        source=build_synthetic_public(split_fills=1)
        for bad in (
            (),[source[0]],
            ({"time_ns":source[0].time_ns,"owner_id":"PRIVATE"},),
            (PublicExecution(-1,100000,1,"BUY"),),
            (PublicExecution(source[0].time_ns,0,1,"BUY"),),
            (PublicExecution(source[0].time_ns,100000,0,"BUY"),),
            (PublicExecution(source[0].time_ns,100000,1,"UNKNOWN"),),
            source[::-1]
        ):
            with self.subTest(bad=str(bad)[:25]),self.assertRaises(ValueError):
                phase_counts(bad,shift_ms=0,collapse_same_timestamp=False)
        for bad in (1.0,False,300,1000):
            with self.subTest(shift=bad),self.assertRaises(ValueError):
                phase_counts(source,shift_ms=bad,collapse_same_timestamp=False)
        with self.assertRaises(ValueError):
            phase_counts(source,shift_ms=0,collapse_same_timestamp=1)
        with self.assertRaises(ValueError):
            build_synthetic_public(split_fills=3)

    def test_same_observed_session_with_absolute_day_shift_has_same_counts(self):
        from public_timing_phase_tied_fills import DAY_NS
        rows=build_synthetic_public(split_fills=100)
        shifted=tuple(PublicExecution(x.time_ns+19_000*DAY_NS,x.price_cents,
                    x.quantity,x.reported_aggressor_side) for x in rows)
        self.assertEqual(phase_counts(rows,shift_ms=0,
                                      collapse_same_timestamp=False),
                         phase_counts(shifted,shift_ms=0,
                                      collapse_same_timestamp=False))

    def test_original_compact_aggregate_preserves_every_predeclared_shift(self):
        out=original_counterexample()
        self.assertEqual(out["schema_version"],
                         "public-clock-phase-tied-fill-negative-observed-v1")
        self.assertEqual(out["original_fixed_clock_shift_matrix_ms"],
                         list(FIXED_SHIFTS_MS))
        self.assertTrue(out["synthetic_100_split_prints_are_not_100_independent_orders"])
        self.assertTrue(out["same_timestamp_grouping_cannot_prove_single_parent_order"])
        self.assertTrue(out["phase_results_are_descriptive_not_selected_best_phase"])
        self.assertFalse(out["real_market_order_owner_FDR_or_p_value_calibrated"])
        self.assertFalse(out["source_original_exchange_or_ABIDES_data_used"])
        self.assertFalse(out["raw_event_timestamps_or_private_agent_IDs_exported"])
        for x in out["constructions"].values():
            self.assertEqual(len(x["all_predeclared_phase_results"]),10)
            self.assertTrue(x["synthetic_non_target_background_only"])
            for row in x["all_predeclared_phase_results"]:
                self.assertIn(row["shift_milliseconds"],FIXED_SHIFTS_MS)
                self.assertIn(row["unit"],
                              ("public_execution_prints","unique_execution_timestamps"))
                self.assertNotIn("time_ns",row)
                self.assertNotIn("owner_id",row)

    def test_frozen_protocol_drift_is_detected_before_counterexample(self):
        d=frozen_plan()
        for key,val in (
            ("grid_periods_seconds",[15,45]),
            ("clock_tolerance_nanoseconds",100),
            ("diagnostic_shifts_milliseconds",[-300,0,300]),
            ("fixed_descriptive_alarm_ratio_threshold",0.9),
            ("source_type","genuine source"),
            ("synthetic_ties_not_identification_of_parent_order",False)
        ):
            x=deepcopy(d)
            x[key]=val
            with self.subTest(key=key),patch.object(
                Path,"read_text",return_value=json.dumps(x)
            ),self.assertRaises(ValueError):
                frozen_plan()

if __name__=="__main__":
    unittest.main(verbosity=2)
