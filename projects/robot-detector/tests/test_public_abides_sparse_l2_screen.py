"""ABIDES public-only EXEC versus sparse L2 post-event causal negatives."""
from datetime import date
from dataclasses import replace
import unittest

from tools.public_intensity_rescaling import Abstain
from tools.public_abides_epoch_ns_clock import NS,ORIGIN,UNIT,SOURCE_UNIT
from tools.public_abides_sparse_l2_screen import screen_abides_public_execution_sparse_l2 as screen


ORIGIN_NS=(date(2021,2,5)-ORIGIN).days*86400*NS

def ts(x):return ORIGIN_NS+int(round(float(str(x))*NS))

def fill(x,side="BUY",price=101,qty=2,**extras):
    return dict(epoch_ns=ts(x),price_cents=price,quantity=qty,aggressor_side=side,**extras)

def book(x,bid=100,ask=102,**extras):
    return dict(epoch_ns=ts(x),bid_cents=bid,ask_cents=ask,depth_complete=True,**extras)

def trades():
    return (fill("34222.5"),fill("34222.5",side="SELL"),
            fill("34223.5"),fill("34224.5"))

def quotes():
    return (book("34220"),book("34222.5",ask=104),book("34223",ask=102))

def qualify(t=None,q=None,**kw):
    return screen(trades() if t is None else t,quotes() if q is None else q,
                  source_run_id=kw.pop("source_run_id","toy-public-ABIDES"),
                  simulation_date=kw.pop("simulation_date","20210205"),
                  window_start_ns=kw.pop("window_start_ns",34222*NS),
                  window_end_ns=kw.pop("window_end_ns",34226*NS),**kw)


class ABIDESPublicSparseL2SourceFreeTests(unittest.TestCase):
    def test_bbo_at_raw_event_time_cannot_be_current_event_prestate(self):
        r=qualify()
        self.assertEqual(r.unit,UNIT)
        self.assertEqual(r.selected_lagged_public_ask_cents,(102,102,104,102))
        self.assertEqual((r.safe_aggregate["public_exec_rows"],
                          r.safe_aggregate["distinct_exact_ns_public_exec_timestamp_clusters"]),(4,3))
        self.assertEqual(r.safe_aggregate["trade_rows_with_strict_prior_lagged_BBO"],4)
        self.assertTrue(r.safe_aggregate["whole_trade_window_eligible_under_assertions_only"])

    def test_exact_same_time_quotes_use_last_only_after_one_second(self):
        r=qualify(q=(book("34220"),book("34222.5",ask=103),
                     book("34222.5",ask=104),book("34223",ask=102)))
        self.assertEqual(r.selected_lagged_public_ask_cents,(102,102,104,102))
        self.assertEqual(r.safe_aggregate["same_time_l2_extra_rows_last_used_only_after_lag"],1)

    def test_one_nanosecond_distinct_execution_cluster_kept(self):
        a=list(trades())
        a[1]=dict(a[1],epoch_ns=a[0]["epoch_ns"]+1)
        r=qualify(t=a)
        self.assertEqual(r.public_trade_times_ns[1]-r.public_trade_times_ns[0],1)
        self.assertEqual(r.safe_aggregate["distinct_exact_ns_public_exec_timestamp_clusters"],4)

    def test_future_quote_inside_window_not_backdated(self):
        original=qualify()
        future=qualify(q=quotes()+(book("34225",ask=106),))
        self.assertEqual(future.selected_lagged_public_ask_cents,original.selected_lagged_public_ask_cents)

    def test_no_previous_lag_eligible_book_abstains_event(self):
        x=qualify(q=(book("34222.4"),))
        self.assertEqual(x.safe_aggregate["trade_rows_abstain_no_prior_lagged_BBO"],2)
        self.assertEqual(x.selected_lagged_public_ask_cents[:2],(None,None))
        self.assertFalse(x.safe_aggregate["whole_trade_window_eligible_under_assertions_only"])

    def test_stale_prior_l2_not_silent_negative(self):
        x=qualify(q=(book("34211"),))
        self.assertEqual(x.safe_aggregate["trade_rows_abstain_stale_prior_BBO"],4)
        self.assertFalse(x.safe_aggregate["whole_trade_window_eligible_under_assertions_only"])

    def test_unknown_or_false_source_completeness_flags_rejected(self):
        for k in ("trade_capture_complete","book_capture_complete"):
            for v in (False,None,1,0):
                with self.subTest(k=k,v=v),self.assertRaises(Abstain):
                    qualify(**{k:v})

    def test_wrong_family_or_clock_unit_or_date_and_revision_rejected(self):
        for opts in ({"source_family":"LOBSTER_VISIBLE_TYPE4"},
                     {"source_clock_unit":"nanoseconds_since_exchange_local_midnight"},
                     {"window_unit":"nanoseconds_since_exchange_local_midnight"},
                     {"simulation_date":"20210206"},
                     {"pinned_revision":"unverified"}):
            with self.subTest(opts=opts),self.assertRaises(Abstain):
                qualify(**opts)

    def test_private_hidden_actor_fields_forbidden(self):
        for key in ("agent_id","passive_agent_id","aggressive_agent_id","order_id","private_truth"):
            with self.subTest(key=key),self.assertRaises(Abstain):
                qualify(t=[dict(trades()[0],**{key:17})])
        with self.assertRaises(Abstain):
            qualify(q=[dict(quotes()[0],private_agent_id=1)])

    def test_invalid_trade_price_quantity_side_or_time_rejected(self):
        for row in (fill("34222.5",price=0),fill("34222.5",price=True),
                    fill("34222.5",qty=0),fill("34222.5",side="ASK"),
                    dict(fill("34222.5"),epoch_ns=34222*NS),
                    dict(fill("34222.5"),epoch_ns=False)):
            with self.subTest(row=str(row)[:50]),self.assertRaises(Abstain):
                qualify(t=(row,))

    def test_crossed_empty_invalid_or_bool_l2_rejected(self):
        for row in (book("34220",bid=105,ask=104),book("34220",bid=0),
                    book("34220",ask=True),
                    dict(book("34220"),depth_complete=False),
                    dict(book("34220"),depth_complete=1)):
            with self.subTest(row=str(row)[:50]),self.assertRaises(Abstain):
                qualify(q=(row,))

    def test_source_sorting_and_future_book_rejected(self):
        for t,q in ((tuple(reversed(trades())),quotes()),
                    (trades(),tuple(reversed(quotes()))),
                    (trades(),quotes()+(book("34226"),))):
            with self.subTest(t=t,q=q),self.assertRaises(Abstain):
                qualify(t=t,q=q)

    def test_out_of_window_trade_and_malformed_run_labels_rejected(self):
        with self.assertRaises(Abstain):
            qualify(t=trades()+(fill("34226"),))
        for label in (None,"","123/private","agent account"):
            with self.subTest(label=label),self.assertRaises(Abstain):
                qualify(source_run_id=label)

    def test_aggregate_only_unknown_owners_and_not_lobster_equivalent(self):
        a=qualify().safe_aggregate
        for key in ("epoch_ns","ask_cents","bid_cents","order_id","agent_id","trade_rows"):
            self.assertNotIn(key,a)
        self.assertFalse(a["private_agent_ids_used"])
        self.assertFalse(a["LOBSTER_visible_type4_equivalence_claimed"])
        self.assertFalse(a["public_source_trade_capture_independently_proven"])
        self.assertFalse(a["real_market_fdr_known"])


if __name__=="__main__":
    unittest.main()
