#!/usr/bin/env python3
"""Causal-order and censoring counterexamples for read-only quote-time summaries."""
from decimal import Decimal
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from l2_duration_weighting import DurationWeightedBBO
from lobster_event_time_features import event_time_features
from test_lobster_public_sample_format_audit import archive,MSG,book_row


D=Decimal


def observe(times,spreads):
    counter=DurationWeightedBBO()
    for t,sp in zip(times,spreads):
        counter.observe_post_event(D(str(t)),100000+sp,100000,200,100)
    return counter.summary()


class ClockTimeWeightedBBOTests(unittest.TestCase):
    def test_same_event_weighted_spreads_can_have_opposite_duration_means(self):
        a=observe([34200,34209,34210],[1000,3000,1000])
        b=observe([34200,34201,34210],[1000,3000,1000])
        # Same event multiset; all EVENT weighted metrics would be equal.
        self.assertAlmostEqual(sum([1000,3000,1000])/3,1666.6666666666667)
        self.assertEqual(a["time_weighted_spread_x10000"],1200)
        self.assertEqual(b["time_weighted_spread_x10000"],2800)
        self.assertEqual(a["observation_clock_interval_seconds"],"10")
        self.assertEqual(b["observation_clock_interval_seconds"],"10")
        self.assertEqual(a["valid_two_sided_non_crossed_quote_seconds"],"10")
        self.assertEqual(b["valid_two_sided_non_crossed_quote_seconds"],"10")
        self.assertEqual(a["positive_time_intervals"],2)
        self.assertEqual(a["zero_duration_same_timestamp_intervals"],0)
        self.assertTrue(a["no_pre_first_event_or_post_last_event_extrapolation"])
        self.assertTrue(b["previous_post_event_snapshot_used_without_future_lookahead"])
        self.assertFalse(a["raw_market_event_snapshots_or_timestamps_exported"])

    def test_exact_same_timestamp_earlier_state_has_zero_duration(self):
        got=observe([34200,34200,34210],[1000,3000,1000])
        self.assertEqual(got["time_weighted_spread_x10000"],3000)
        self.assertEqual(got["observation_clock_interval_seconds"],"10")
        self.assertEqual(got["zero_duration_same_timestamp_intervals"],1)
        self.assertEqual(got["positive_time_intervals"],1)
        self.assertTrue(got["same_timestamp_zero_time_weight"])

    def test_first_last_events_are_censored_not_extended_to_session_boundaries(self):
        one=DurationWeightedBBO()
        one.observe_post_event(D("40000"),11000,10000,100,200)
        state=one.summary()
        self.assertEqual(state["observation_clock_interval_seconds"],"0")
        self.assertIsNone(state["time_weighted_spread_x10000"])
        self.assertEqual(state["input_post_event_snapshots"],1)
        two=observe([40000,40001],[1000,3000])
        self.assertEqual(two["time_weighted_spread_x10000"],1000)
        self.assertEqual(two["observation_clock_interval_seconds"],"1")
        self.assertTrue(two["no_pre_first_event_or_post_last_event_extrapolation"])

    def test_missing_and_locked_book_quote_time_is_separately_counted(self):
        w=DurationWeightedBBO()
        w.observe_post_event(D("34200"),None,None,0,0)
        w.observe_post_event(D("34205"),10000,10000,100,100)
        w.observe_post_event(D("34210"),11000,10000,100,100)
        w.observe_post_event(D("34220"),12000,11000,100,100)
        r=w.summary()
        self.assertEqual(r["observation_clock_interval_seconds"],"20")
        self.assertEqual(r["missing_quote_seconds"],"5")
        self.assertEqual(r["locked_or_crossed_quote_seconds"],"5")
        self.assertEqual(r["valid_two_sided_non_crossed_quote_seconds"],"10")
        self.assertEqual(r["time_weighted_spread_x10000"],1000)
        self.assertEqual(r["time_weighted_top_depth_shares"],200)
        self.assertEqual(r["time_weighted_top_depth_imbalance"],0)

    def test_nonzero_stale_hold_exposure_reported_not_silently_discarded(self):
        w=DurationWeightedBBO()
        w.observe_post_event(D("34200"),11000,10000,100,100)
        w.observe_post_event(D("34300"),11000,10000,100,100)
        r=w.summary()
        self.assertEqual(r["intervals_exceeding_30_seconds"],1)
        self.assertEqual(r["total_duration_in_over_30s_intervals"],"100")
        self.assertEqual(r["max_positive_quote_hold_seconds"],"100")
        self.assertEqual(r["valid_two_sided_non_crossed_quote_seconds"],"100")
        self.assertEqual(r["time_weighted_spread_x10000"],1000)

    def test_failure_on_nonfinite_negative_or_out_of_order_times_and_sizes(self):
        for bad in (
            D("nan"),D("Infinity"),D("-Infinity"),D("34199"),
            D("57601"),float(34200),True,"34200"
        ):
            with self.subTest(bad=str(bad)),self.assertRaises(ValueError):
                DurationWeightedBBO().observe_post_event(bad,11000,10000,100,100)
        for ask,bid,asksize,bidsize in (
            (10000,11000,False,10),
            (10000,11000,-1,10),
            (10000,11000,0,10),
            (None,11000,0,-1),
            (10000,False,10,10),
            (10000,11000,1000000000001,10)
        ):
            with self.subTest(ask=ask,bid=bid),self.assertRaises(ValueError):
                DurationWeightedBBO().observe_post_event(
                    D("34200"),ask,bid,asksize,bidsize)
        state=DurationWeightedBBO()
        state.observe_post_event(D("34201"),11000,10000,10,10)
        with self.assertRaises(ValueError):
            state.observe_post_event(D("34200"),11000,10000,10,10)
        with self.assertRaises(ValueError):
            DurationWeightedBBO().summary()

    def test_post_event_hold_integrated_into_source_decoder_and_not_invented(self):
        raw=archive()
        s=event_time_features(raw)
        d=s["post_event_clock_weighted_bbo"]
        self.assertEqual(d["schema_version"],"l2-post-event-right-continuous-clock-weight-v1")
        self.assertEqual(d["input_post_event_snapshots"],s["event_count"])
        self.assertEqual(d["zero_duration_same_timestamp_intervals"],1)
        self.assertEqual(d["positive_time_intervals"],3)
        self.assertEqual(d["observation_clock_interval_seconds"],"0.003")
        self.assertEqual(d["valid_two_sided_non_crossed_quote_seconds"],"0.003")
        self.assertEqual(d["time_weighted_spread_x10000"],1000)
        self.assertEqual(d["time_weighted_top_depth_shares"],190)
        self.assertAlmostEqual(d["time_weighted_top_depth_imbalance"],-10/190)
        self.assertTrue(d["same_timestamp_zero_time_weight"])
        self.assertFalse(d["real_robot_identity_or_FDR_calibrated"])

    def test_timestamp_sequence_cannot_overflow_SIX_AND_HALF_HOURS(self):
        w=DurationWeightedBBO()
        w.observe_post_event(D("34200"),11000,10000,10,10)
        w.observe_post_event(D("57600"),11000,10000,10,10)
        self.assertEqual(w.summary()["observation_clock_interval_seconds"],"23400")

if __name__=="__main__":
    unittest.main(verbosity=2)
