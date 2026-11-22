"""Source-free paired post-event BBO projection causality controls."""
import unittest
from dataclasses import replace
from tools.public_intensity_rescaling import Abstain
from tools.public_post_event_bbo_projector import project_paired_post_event_bbo as project
from tools.public_m1_dynamic_l2 import (
    M1DynamicEvaluationWindow, M1DynamicRateModel, predict_m1_dynamic_exposure,
)


def row(t, ask=102., bid=100., **extras):
    return dict(timestamp_ms=t, bid_price=bid, ask_price=ask, complete=True, **extras)


def checked(rows):
    return project(rows, source_precision_ms=1, interval_complete=True,
                   declared_message_rows=len(rows), declared_book_rows=len(rows))


def model():
    return M1DynamicRateModel(.03, .5, 1., ("training-only",), 1, 1, 1000, 1000)


class PostEventCausalityTests(unittest.TestCase):
    def test_aligned_post_event_pairs_are_internal_not_pre_event(self):
        x=checked([row(1000), row(2000,104.), row(3000)])
        self.assertEqual([z["timestamp_ms"] for z in x.snapshots],[1000,2000,3000])
        self.assertEqual(x.safe_aggregate["post_event_rows"],3)
        self.assertFalse(x.safe_aggregate["source_clock_independently_verified"])

    def test_tied_quotes_choose_last_post_event_and_only_future_lag(self):
        x=checked([row(1000),row(2000),row(2000,104.),row(3000)])
        self.assertEqual(len(x.snapshots),3)
        self.assertEqual(x.safe_aggregate["tied_post_event_rows"],1)
        self.assertEqual(x.snapshots[1]["ask_price"],104.)
        w=M1DynamicEvaluationWindow("eval",2500,3500,x.snapshots)
        e=predict_m1_dynamic_exposure(model(),w)
        self.assertEqual([(v.start_ms,v.end_ms) for v in e],[(2500,3000),(3000,3500)])
        self.assertEqual([v.rate_per_second for v in e],[.5,1.])

    def test_future_book_does_not_change_preexisting_predictable_intensity(self):
        x=checked([row(1000),row(2000,104.),row(3000)])
        y=checked([row(1000),row(2000,104.),row(3000),row(4000,106.)])
        w=M1DynamicEvaluationWindow("eval",2500,3500,x.snapshots)
        self.assertEqual(predict_m1_dynamic_exposure(model(),w),
                         predict_m1_dynamic_exposure(model(),replace(w,snapshots=y.snapshots)))

    def test_duplicate_timestamps_not_extra_independent_source_worlds(self):
        x=checked([row(1000),row(2000),row(2000),row(3000)])
        self.assertEqual(x.safe_aggregate["post_event_rows"],4)
        self.assertEqual(x.safe_aggregate["unique_public_timestamps"],3)
        self.assertFalse(x.safe_aggregate["physical_owner_identity_known"])

    def test_unbalanced_source_pair_counts_abstain(self):
        for v in (0,2,True,3.5):
            with self.subTest(count=repr(v)),self.assertRaisesRegex(Abstain,"UNALIGNED"):
                project([row(1000)],source_precision_ms=1,interval_complete=True,
                        declared_message_rows=1,declared_book_rows=v)

    def test_coarse_precision_and_unsupported_coverage_abstain(self):
        for precision in (0,10,None,True):
            with self.subTest(p=precision),self.assertRaises(Abstain):
                project([row(1000)],source_precision_ms=precision,interval_complete=True,
                        declared_message_rows=1,declared_book_rows=1)
        for coverage in (False,"yes",None,1):
            with self.subTest(c=coverage),self.assertRaises(Abstain):
                project([row(1000)],source_precision_ms=1,interval_complete=coverage,
                        declared_message_rows=1,declared_book_rows=1)

    def test_timestamp_unsorted_or_invalid_abstain(self):
        for r in ([row(2000),row(1000)],[row(True)],[row(1.5)],
                  [row(-1)],[row(10**500)]):
            with self.subTest(r=str(r)[:50]),self.assertRaises(Abstain):
                checked(r)

    def test_crossed_missing_or_huge_public_quote_abstain(self):
        for r in ([row(1000,ask=0)],[row(1000,bid=105,ask=104)],
                  [row(1000,ask=float("nan"))],[row(1000,ask=10**500)],
                  [dict(row(1000),complete=1)],[dict(row(1000),complete=False)]):
            with self.subTest(r=str(r)[:50]),self.assertRaises(Abstain):
                checked(r)

    def test_private_oracle_order_account_fields_abstain(self):
        for field in ("agent_id","order_id","private_truth","account_id","metadata"):
            with self.subTest(field=field),self.assertRaisesRegex(Abstain,"FORBIDDEN"):
                checked([dict(row(1000),**{field:"secret"})])

    def test_safe_aggregate_has_no_raw_event_rows_or_prices(self):
        a=checked([row(1000),row(2000,104.)]).safe_aggregate
        self.assertEqual(a["effective_book_lag_ms"],1000)
        for forbidden in ("timestamp_ms","bid_price","ask_price","order_id","agent_id"):
            self.assertNotIn(forbidden,a)
        self.assertFalse(a["vendor_raw_rows_exported"])
        self.assertFalse(a["real_market_fdr_known"])


if __name__ == "__main__":
    unittest.main()
