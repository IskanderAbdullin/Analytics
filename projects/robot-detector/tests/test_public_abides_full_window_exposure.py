"""Source-free ABIDES whole-time quote exposure vs misleading event-only check."""
from dataclasses import replace
from datetime import date
import unittest

from tools.public_intensity_rescaling import Abstain
from tools.public_abides_epoch_ns_clock import NS,ORIGIN,UNIT
from tools.public_abides_sparse_l2_screen import screen_abides_public_execution_sparse_l2 as screen
from tools.public_abides_full_window_exposure import (
    ABIDESPublicFullWindowExposure,ABIDESPublicFullWindowSegment,
    qualify_abides_full_window_l2_exposure as qualify,
)

BASE=(date(2021,2,5)-ORIGIN).days*86400*NS

def tick(sec):return BASE+int(sec*NS)

def fill(sec):
    return {"epoch_ns":tick(sec),"price_cents":101,"quantity":1,"aggressor_side":"BUY"}

def book(sec,ask=102):
    return {"epoch_ns":tick(sec),"bid_cents":100,"ask_cents":ask,"depth_complete":True}

def source(trades=None,books=None,end=34226):
    return screen(
        (fill(34222.5),fill(34223.5),fill(34224.5)) if trades is None else trades,
        (book(34220),book(34222.5,104),book(34223)) if books is None else books,
        source_run_id="source-free-original", simulation_date="20210205",
        window_start_ns=34222*NS,window_end_ns=int(end*NS))

def full(tape=None,end=34226,**kw):
    return qualify(source() if tape is None else tape,
                   start_ns=kw.pop("start_ns",34222*NS),
                   end_ns=kw.pop("end_ns",int(end*NS)),**kw)


class ABIDESFullWindowExposureTests(unittest.TestCase):
    def test_three_complete_precommitted_segments_and_exact_duration(self):
        x=full()
        self.assertEqual(x.unit,UNIT)
        self.assertEqual([(s.start_ns,s.end_ns,s.relative_spread_numerator,s.relative_spread_denominator)
                          for s in x.segments],
                         [(34222*NS,int(34223.5*NS),2,202),
                          (int(34223.5*NS),34224*NS,4,204),
                          (34224*NS,34226*NS,2,202)])
        self.assertEqual(x.safe_aggregate["public_exposure_duration_ns"],4*NS)
        self.assertEqual(x.safe_aggregate["public_exposure_segment_count"],3)

    def test_trade_only_eligibility_can_pass_while_full_window_is_stale(self):
        tape=source((fill(34222.5),),(book(34220),),end=34232)
        self.assertTrue(tape.safe_aggregate["whole_trade_window_eligible_under_assertions_only"])
        self.assertEqual(tape.safe_aggregate["trade_rows_with_strict_prior_lagged_BBO"],1)
        with self.assertRaisesRegex(Abstain,"STALE_FULL_WINDOW"):
            full(tape=tape,end=34232)

    def test_one_earlier_quote_complete_short_window(self):
        s=source((fill(34222.5),),(book(34220),),end=34226)
        q=full(tape=s)
        self.assertEqual(len(q.segments),1)
        self.assertEqual((q.segments[0].start_ns,q.segments[0].end_ns),(34222*NS,34226*NS))

    def test_tied_same_ns_quote_last_used_only_after_lag(self):
        s=source(books=(book(34220),book(34222.5,103),book(34222.5,104),book(34223)))
        x=full(tape=s)
        self.assertEqual(x.segments[0].relative_spread_numerator,2)
        self.assertEqual(x.segments[1].relative_spread_numerator,4)

    def test_one_nanosecond_boundary_preserved_exact(self):
        s=source(books=(book(34220),book(34222.5,104),book(34223)))
        x=full(tape=s,start_ns=34222*NS+1,end_ns=34226*NS)
        self.assertEqual(x.segments[0].start_ns,34222*NS+1)
        self.assertEqual(x.segments[0].end_ns,int(34223.5*NS))

    def test_no_initial_lagged_quote_abstains_before_segment(self):
        s=source((fill(34223.5),),(book(34222.5,104),),end=34226)
        with self.assertRaisesRegex(Abstain,"NO_PREVIOUS_CAUSAL"):
            full(tape=s)

    def test_incorrect_window_or_source_unit_abstains(self):
        s=source()
        for opts in ({"window_unit":"nanoseconds_since_exchange_local_midnight"},
                     {"source_family":"LOBSTER_PUBLIC_DEMO"},
                     {"start_ns":True},
                     {"end_ns":False},
                     {"end_ns":34222*NS},
                     {"start_ns":34225*NS}):
            with self.subTest(opts=opts),self.assertRaises(Abstain):
                full(s,**opts)

    def test_nonexternal_caller_capture_flags_must_stay_assertions(self):
        for k in ("source_trade_capture_asserted","source_l2_capture_asserted"):
            for v in (False,1,None):
                with self.subTest(k=k,v=v),self.assertRaises(Abstain):
                    full(**{k:v})

    def test_forged_earlier_screen_source_proof_is_rejected(self):
        t=source()
        forged=replace(t,safe_aggregate={
            **t.safe_aggregate,"full_window_L2_exposure_coverage_independently_proven":True})
        with self.assertRaises(Abstain):
            full(tape=forged)

    def test_forged_sparse_book_quote_state_rejected(self):
        t=source()
        for quotes in ((int(34220*NS),),(("abc",100,102),),
                       ((34220*NS,105,104),),
                       ((34220*NS,100,102),(34220*NS,100,102))):
            forged=replace(t,public_post_event_l2_quotes=quotes,
                           safe_aggregate={**t.safe_aggregate,
                                           "public_sparse_l2_distinct_exact_ns_quote_times":len(quotes)})
            with self.subTest(quotes=quotes),self.assertRaises(Abstain):
                full(tape=forged)

    def test_event_outside_new_observation_window_abstains(self):
        t=source()
        with self.assertRaises(Abstain):
            full(tape=t,end_ns=34224*NS)

    def test_aggregate_never_exports_book_or_physical_owners(self):
        x=full()
        a=x.safe_aggregate
        self.assertTrue(a["exact_nanosecond_window_tiling_valid"])
        self.assertFalse(a["original_market_source_event_completeness_independently_verified"])
        self.assertFalse(a["real_market_fdr_known"])
        self.assertFalse(a["source_is_independent_blind_original_world"])
        for key in ("timestamp_ns","epoch_ns","bid_cents","ask_cents","price_cents",
                    "agent_id","trades","execution_owner","raw_event_rows"):
            self.assertNotIn(key,a)


if __name__=="__main__":
    unittest.main()
