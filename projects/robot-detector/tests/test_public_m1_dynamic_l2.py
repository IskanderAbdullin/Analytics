"""Source-free M1-v2 lagged-L2 changing-book cases; no owner or market FDR."""
import math
import unittest
from dataclasses import replace

from tools.public_intensity_rescaling import Abstain, rescaled_cluster_gaps
from tools.public_m1_dynamic_l2 import (
    M1DynamicTrainingRun, M1DynamicEvaluationWindow,
    fit_m1_dynamic_train_only, predict_m1_dynamic_exposure,
)


def book(t,bid=100.,ask=102.,**kwargs):
    return {"timestamp_ms":t,"bid_price":bid,"ask_price":ask,"complete":True,**kwargs}


def training():
    return [
        M1DynamicTrainingRun("low-world",2000,5000,(2500,4200),
                             (book(0),book(3000,ask=104.))),
        M1DynamicTrainingRun("high-world",10000,13000,(11000,12000),
                             (book(8000,ask=104.),book(10500))),
    ]


def eval_window():
    return M1DynamicEvaluationWindow("fresh-eval",20000,23000,
                                     (book(18500),book(20500,ask=104.)))


class DynamicLaggedL2Tests(unittest.TestCase):
    def test_known_train_weighted_median_and_two_rates(self):
        m=fit_m1_dynamic_train_only(training())
        self.assertAlmostEqual(m.median_relative_spread,2/101)
        self.assertEqual((m.low_cluster_count,m.high_cluster_count),(2,2))
        self.assertEqual((m.low_exposure_ms,m.high_exposure_ms),(3500,2500))
        self.assertAlmostEqual(m.low_rate_per_second,2000/3500)
        self.assertAlmostEqual(m.high_rate_per_second,2000/2500)

    def test_predict_complete_two_segment_exposure_without_evaluation_prints(self):
        m=fit_m1_dynamic_train_only(training())
        exp=predict_m1_dynamic_exposure(m,eval_window())
        self.assertEqual([(e.start_ms,e.end_ms) for e in exp],[(20000,21500),(21500,23000)])
        self.assertEqual([e.rate_per_second for e in exp],[m.low_rate_per_second,m.high_rate_per_second])
        self.assertAlmostEqual(rescaled_cluster_gaps((21000,22000),exp)[0],
                               .5*m.low_rate_per_second+.5*m.high_rate_per_second)

    def test_current_time_book_update_is_not_used_until_lag(self):
        m=fit_m1_dynamic_train_only(training())
        w=eval_window()
        no_future=predict_m1_dynamic_exposure(m,w)
        # Quote at 22000 is still NOT effective at any instant <23000.
        extra=replace(w,snapshots=w.snapshots+(book(22000,ask=106.),))
        self.assertEqual(predict_m1_dynamic_exposure(m,extra),no_future)

    def test_event_exact_transition_uses_preknown_one_second_prior_quote(self):
        rr=training()
        rr[0]=replace(rr[0],cluster_times_ms=(2500,4000))
        m=fit_m1_dynamic_train_only(rr)
        self.assertEqual((m.low_cluster_count,m.high_cluster_count),(2,2))

    def test_duplicate_split_fills_do_not_change_trained_rates(self):
        rr=training()
        rr[0]=replace(rr[0],cluster_times_ms=(2500,2500,4200,4200))
        self.assertEqual(fit_m1_dynamic_train_only(rr),fit_m1_dynamic_train_only(training()))

    def test_redundant_quote_update_same_public_bbo_no_rate_change(self):
        rr=training()
        rr[0]=replace(rr[0],snapshots=(book(0),book(2000),book(3000,ask=104.)))
        self.assertEqual(fit_m1_dynamic_train_only(rr),fit_m1_dynamic_train_only(training()))

    def test_eval_source_run_id_overlap_and_invalid_type_abstain(self):
        m=fit_m1_dynamic_train_only(training())
        with self.assertRaisesRegex(Abstain,"OVERLAP"):
            predict_m1_dynamic_exposure(m,replace(eval_window(),run_id="low-world"))
        with self.assertRaises(Abstain):
            predict_m1_dynamic_exposure(m,object())

    def test_missing_initial_prior_or_stale_quote_abstain(self):
        m=fit_m1_dynamic_train_only(training())
        for w in (replace(eval_window(),snapshots=(book(19500),)),
                  replace(eval_window(),snapshots=(book(1000),)),
                  replace(eval_window(),snapshots=(book(18500),))):
            with self.subTest(w=w),self.assertRaises(Abstain):
                predict_m1_dynamic_exposure(m,w)

    def test_source_precision_completeness_and_bbo_fail_closed(self):
        m=fit_m1_dynamic_train_only(training())
        w=eval_window()
        for x in (replace(w,source_precision_ms=10),replace(w,source_precision_ms=True),
                  replace(w,interval_complete=False),replace(w,interval_complete=1),
                  replace(w,snapshots=(book(18500),book(20500,ask=104.,agent_id=9))),
                  replace(w,snapshots=(book(18500),book(20500,bid=105,ask=104))),
                  replace(w,snapshots=(book(18500),book(20500,ask=float("nan")))),
                  replace(w,snapshots=(book(18500),dict(book(20500),complete=1)))):
            with self.subTest(x=x),self.assertRaises(Abstain):
                predict_m1_dynamic_exposure(m,x)

    def test_duplicate_or_unsorted_book_timestamp_abstain(self):
        m=fit_m1_dynamic_train_only(training())
        w=eval_window()
        for b in ((book(20500),book(18500)),(book(18500),book(18500)),
                  (book(18500),book(23000))):
            with self.subTest(b=b),self.assertRaises(Abstain):
                predict_m1_dynamic_exposure(m,replace(w,snapshots=b))

    def test_invalid_training_event_times_and_duplicate_world_ids_abstain(self):
        for timestamps in ((4200,2500),(2000,2500),(2500,5000),(2500,True),(2500,2500.5)):
            rr=training()
            rr[0]=replace(rr[0],cluster_times_ms=timestamps)
            with self.subTest(t=timestamps),self.assertRaises(Abstain):
                fit_m1_dynamic_train_only(rr)
        rr=training();rr[1]=replace(rr[1],run_id="low-world")
        with self.assertRaisesRegex(Abstain,"DUPLICATE"):
            fit_m1_dynamic_train_only(rr)

    def test_all_one_stratum_and_missing_training_cluster_abstain(self):
        rr=training()
        rr[0]=replace(rr[0],snapshots=(book(0),),cluster_times_ms=(2500,))
        rr[1]=replace(rr[1],snapshots=(book(8000),),cluster_times_ms=(11000,))
        with self.assertRaisesRegex(Abstain,"STRATUM"):
            fit_m1_dynamic_train_only(rr)
        rr=training();rr[0]=replace(rr[0],cluster_times_ms=())
        with self.assertRaisesRegex(Abstain,"STRATUM"):
            fit_m1_dynamic_train_only(rr)

    def test_invalid_large_timestamp_and_nonpositive_quotes_abstain(self):
        m=fit_m1_dynamic_train_only(training())
        w=eval_window()
        for b in (book(18500,bid=0),book(18500,bid=True),book(18500,ask=10**500)):
            with self.subTest(b=str(b)[:40]),self.assertRaises(Abstain):
                predict_m1_dynamic_exposure(m,replace(w,snapshots=(b,book(20500,ask=104.))))
        with self.assertRaises(Abstain):
            predict_m1_dynamic_exposure(m,replace(w,end_ms=10**500))

    def test_periodic_and_momentum_hard_negatives_do_not_become_owner_labels(self):
        m=fit_m1_dynamic_train_only(training())
        periods=(20500,21000,21500,22000)
        momentum=(20500,20501,20502,22000)
        prediction=predict_m1_dynamic_exposure(m,eval_window())
        self.assertNotEqual(periods,momentum)
        self.assertEqual(prediction,predict_m1_dynamic_exposure(m,eval_window()))
        self.assertFalse(any(hasattr(e,"owner_id") for e in prediction))


if __name__=="__main__": unittest.main()
