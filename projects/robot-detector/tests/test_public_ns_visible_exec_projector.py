"""Public-only exact-ns type-4 vs all event/book message controls."""
from dataclasses import replace
from decimal import Decimal as D
import unittest

from tools.public_intensity_rescaling import Abstain
from tools.public_lobster_ns_time import UNIT,exact_decimal_to_ns
from tools.public_ns_visible_exec_projector import project_public_ns_visible_executions as project
from tools.public_m1_v3_ns_l2 import (
    NsM1Model,NsEvaluationWindow,predict_ns_m1_v3_exposure,
)


def t(value): return exact_decimal_to_ns(D(str(value)))


def row(sec,etype=1,side=-1,ask=102,bid=100,**extra):
    return dict(timestamp_ns=t(sec),event_type=etype,resting_side=side,
                bid_price=bid,ask_price=ask,complete=True,**extra)


def checked(rows):
    return project(rows,source_time_unit=UNIT,source_precision_ns=1,interval_complete=True)


def toy_rows():
    return [row("34220",1),row("34222.5",4,-1),row("34222.5",4,1,104),
            row("34222.5",5,1,104),row("34223",2,-1)]


def model():
    return NsM1Model(2/101,.75,.5,("train",),3,2,4*10**9,4*10**9)


class SourceFreeVisibleTradeProjectionNegatives(unittest.TestCase):
    def test_visible_type4_is_not_all_source_messages(self):
        p=checked(toy_rows())
        a=p.safe_aggregate
        self.assertEqual((a["source_message_and_post_event_book_rows"],
                          a["visible_type4_executions"],
                          a["visible_type4_exact_trade_timestamp_clusters"]),(5,2,1))
        self.assertEqual(a["other_source_message_events_not_visible_type4_trades"],2)
        self.assertEqual(a["hidden_type5_executions_not_direction_inferred"],1)
        self.assertFalse(a["true_market_trade_only_ms_collision_rate_known"])

    def test_type4_resting_side_is_opposite_aggressor(self):
        a=checked(toy_rows()).safe_aggregate
        self.assertEqual(a["visible_aggressive_buy_inferred_from_resting_sell"],1)
        self.assertEqual(a["visible_aggressive_sell_inferred_from_resting_buy"],1)
        self.assertEqual(a["hidden_type5_executions_not_direction_inferred"],1)

    def test_last_of_tied_post_event_books_only_for_future_rate(self):
        p=checked(toy_rows())
        self.assertEqual(len(p.post_event_bbo_snapshots),3)
        self.assertEqual(p.post_event_bbo_snapshots[1]["ask_price"],104)
        self.assertEqual(p.visible_type4_trade_cluster_times_ns,(t("34222.5"),))
        w=NsEvaluationWindow("eval",t("34222"),t("34226"),p.post_event_bbo_snapshots)
        pred=predict_ns_m1_v3_exposure(model(),w)
        self.assertEqual([(x.start_ns,x.end_ns) for x in pred],
                         [(t("34222"),t("34223.5")),(t("34223.5"),t("34224")),(t("34224"),t("34226"))])
        self.assertEqual([x.rate_per_second for x in pred],[.75,.5,.75])

    def test_one_ns_apart_visible_trade_clusters_remain_distinct(self):
        p=checked([row("34220"),row("34222.500000001",4),
                   row("34222.500000002",4),row("34222.500000002",2)])
        self.assertEqual(len(p.visible_type4_trade_cluster_times_ns),2)
        self.assertEqual(p.visible_type4_trade_cluster_times_ns[1]-p.visible_type4_trade_cluster_times_ns[0],1)
        self.assertEqual(p.safe_aggregate["visible_type4_tied_additional_fills"],0)
        self.assertFalse(p.safe_aggregate["true_market_trade_only_ms_collision_rate_known"])

    def test_exact_tied_visible_execution_counts_extra_fill_not_owner(self):
        p=checked([row("34220"),row("34222.5",4),row("34222.5",2),row("34222.5",4)])
        self.assertEqual(len(p.visible_type4_trade_cluster_times_ns),1)
        self.assertEqual(p.safe_aggregate["visible_type4_tied_additional_fills"],1)
        self.assertFalse(p.safe_aggregate["physical_owner_identity_known"])

    def test_no_visible_exec_valid_empty_projection_not_automated_absence(self):
        p=checked([row("34220",1),row("34221",5),row("34222",2)])
        self.assertEqual(p.visible_type4_trade_cluster_times_ns,())
        self.assertEqual(p.safe_aggregate["visible_type4_executions"],0)
        self.assertFalse(p.safe_aggregate["real_market_fdr_known"])

    def test_bad_extra_private_oracle_and_order_fields_rejected(self):
        for field in ("agent_id","order_id","account","private_truth","broker_id"):
            with self.subTest(field=field),self.assertRaisesRegex(Abstain,"FORBIDDEN"):
                checked([dict(row("34220"),**{field:3})])

    def test_invalid_bool_or_unknown_event_and_resting_side_rejected(self):
        for bad in (dict(row("34220"),event_type=True),
                    dict(row("34220"),event_type=8),
                    dict(row("34220"),resting_side=True),
                    dict(row("34220"),resting_side=0)):
            with self.subTest(bad=bad),self.assertRaises(Abstain):
                checked([bad])

    def test_bad_book_missing_crossed_nonfinite_extreme_rejected(self):
        for bad in (row("34220",ask=0),row("34220",bid=104,ask=103),
                    row("34220",ask=float("nan")),row("34220",ask=10**500),
                    dict(row("34220"),complete=False),dict(row("34220"),complete=1)):
            with self.subTest(bad=str(bad)[:45]),self.assertRaises(Abstain):
                checked([bad])

    def test_source_unit_precision_continuity_strict_fail_closed(self):
        for u,precision,complete in (("milliseconds",1,True),(UNIT,1000000,True),
                                      (UNIT,True,True),(UNIT,1,False),(UNIT,1,1)):
            with self.subTest(u=u,p=precision,c=complete),self.assertRaises(Abstain):
                project(toy_rows(),source_time_unit=u,source_precision_ns=precision,
                        interval_complete=complete)

    def test_source_out_of_order_or_unsafe_time_rejected(self):
        for r in ([row("34222"),row("34220")],
                  [dict(row("34220"),timestamp_ns=True)],
                  [dict(row("34220"),timestamp_ns=34220*1000)],
                  [dict(row("34220"),timestamp_ns=10**500)]):
            with self.subTest(r=str(r)[:45]),self.assertRaises(Abstain):
                checked(r)

    def test_aggregate_exposes_no_source_event_or_book_rows(self):
        a=checked(toy_rows()).safe_aggregate
        for forbidden in ("timestamp_ns","bid_price","ask_price","order_id","agent_id","source_rows"):
            self.assertNotIn(forbidden,a)
        self.assertFalse(a["raw_vendor_event_order_or_book_rows_exported"])
        self.assertFalse(a["source_completeness_independently_verified"])


if __name__=="__main__":
    unittest.main()
