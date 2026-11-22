"""Prospectively fixed source-free ns M1-v3 causal L2 / negative controls."""
from dataclasses import replace
from decimal import Decimal as D
import unittest
from tools.public_intensity_rescaling import Abstain
from tools.public_lobster_ns_time import exact_decimal_to_ns, UNIT
from tools.public_m1_v3_ns_l2 import (
    NsTrainingRun, NsEvaluationWindow, fit_ns_m1_v3_train_only,
    predict_ns_m1_v3_exposure, LAG_NS, MAX_AGE_NS,
)


def t(seconds):
    return exact_decimal_to_ns(D(str(seconds)))


def book(seconds,ask=102,bid=100,**extras):
    return dict(timestamp_ns=t(seconds),bid_price=bid,ask_price=ask,complete=True,**extras)


def training():
    return [
        NsTrainingRun("low-world",t("34202"),t("34206"),
                      (t("34202.5"),t("34203.5"),t("34204.25")),
                      (book("34200"),book("34203",ask=104))),
        NsTrainingRun("high-world",t("34212"),t("34216"),
                      (t("34212.5"),t("34214.25")),
                      (book("34210",ask=104),book("34213"))),
    ]


def evaluation():
    return NsEvaluationWindow("evaluation-world",t("34222"),t("34226"),
                              (book("34220"),book("34223",ask=104)))


class NanosCausalBookIntensityTests(unittest.TestCase):
    def test_frozen_training_two_regimes_exact_counts_and_ns_durations(self):
        m=fit_ns_m1_v3_train_only(training())
        self.assertAlmostEqual(m.training_weighted_median_relative_spread,2/101)
        self.assertEqual((m.low_cluster_count,m.high_cluster_count),(3,2))
        self.assertEqual((m.low_exposure_ns,m.high_exposure_ns),(4*10**9,4*10**9))
        self.assertEqual((m.low_rate_per_second,m.high_rate_per_second),(.75,.5))

    def test_frozen_prediction_two_segments_one_second_lag(self):
        m=fit_ns_m1_v3_train_only(training())
        e=predict_ns_m1_v3_exposure(m,evaluation())
        self.assertEqual([(x.start_ns,x.end_ns) for x in e],
                         [(t("34222"),t("34224")),(t("34224"),t("34226"))])
        self.assertEqual([x.rate_per_second for x in e],[.75,.5])
        self.assertEqual(LAG_NS,10**9)
        self.assertEqual(MAX_AGE_NS,10**10)

    def test_one_nanosecond_separated_clusters_are_distinct(self):
        a=training()
        a[0]=replace(a[0],cluster_times_ns=(t("34202.5"),t("34202.500000001"),t("34204.25")))
        m=fit_ns_m1_v3_train_only(a)
        self.assertEqual(m.low_cluster_count,3)
        self.assertEqual(t("34202.500000001")-t("34202.5"),1)

    def test_split_fills_not_double_counted(self):
        a=training()
        a[0]=replace(a[0],cluster_times_ns=(t("34202.5"),t("34202.5"),t("34203.5"),t("34204.25"),t("34204.25")))
        self.assertEqual(fit_ns_m1_v3_train_only(a),fit_ns_m1_v3_train_only(training()))

    def test_same_time_raw_post_event_quote_does_not_affect_current_rate(self):
        m=fit_ns_m1_v3_train_only(training())
        w=evaluation()
        w2=replace(w,post_event_bbo=w.post_event_bbo+(book("34225.5",ask=106),))
        self.assertEqual(predict_ns_m1_v3_exposure(m,w2),
                         predict_ns_m1_v3_exposure(m,w))
        self.assertEqual(predict_ns_m1_v3_exposure(m,w)[0].rate_per_second,.75)

    def test_wrong_ns_unit_or_millisecond_magnitude_abstains(self):
        a=training()
        for unit in ("milliseconds",None,1,"nanoseconds_since_UTC_epoch"):
            with self.subTest(unit=unit),self.assertRaises(Abstain):
                fit_ns_m1_v3_train_only([replace(a[0],unit=unit),a[1]])
        w=replace(evaluation(),start_ns=34222*1000,end_ns=34226*1000)
        with self.assertRaises(Abstain):
            predict_ns_m1_v3_exposure(fit_ns_m1_v3_train_only(a),w)

    def test_absent_initial_quote_or_stale_book_abstains(self):
        m=fit_ns_m1_v3_train_only(training())
        for b in ((book("34221.5"),),(book("34200"),),(book("34215"),)):
            with self.subTest(b=b),self.assertRaises(Abstain):
                predict_ns_m1_v3_exposure(m,replace(evaluation(),post_event_bbo=b))

    def test_valid_single_prior_post_event_bbo_under_ten_seconds_is_eligible(self):
        model=fit_ns_m1_v3_train_only(training())
        one=replace(evaluation(),post_event_bbo=(book("34220"),))
        pred=predict_ns_m1_v3_exposure(model,one)
        self.assertEqual(len(pred),1)
        self.assertEqual((pred[0].start_ns,pred[0].end_ns),
                         (t("34222"),t("34226")))
        self.assertEqual(pred[0].rate_per_second,.75)

    def test_future_tied_unsorted_post_event_bbo_abstains(self):
        m=fit_ns_m1_v3_train_only(training())
        for b in ((book("34223"),book("34220")),
                  (book("34220"),book("34220")),
                  (book("34220"),book("34226"))):
            with self.subTest(b=b),self.assertRaises(Abstain):
                predict_ns_m1_v3_exposure(m,replace(evaluation(),post_event_bbo=b))

    def test_invalid_extreme_or_crossed_book_abstains(self):
        m=fit_ns_m1_v3_train_only(training())
        for x in (book("34220",ask=0),book("34220",bid=105,ask=104),
                  book("34220",ask=float("nan")),book("34220",ask=10**500),
                  dict(book("34220"),complete=False),dict(book("34220"),complete=1),
                  dict(book("34220"),agent_id=333)):
            with self.subTest(x=str(x)[:50]),self.assertRaises(Abstain):
                predict_ns_m1_v3_exposure(m,replace(evaluation(),post_event_bbo=(x,book("34223",ask=104))))

    def test_unknown_completeness_or_coarse_precision_abstains(self):
        m=fit_ns_m1_v3_train_only(training())
        for w in (replace(evaluation(),interval_complete=False),
                  replace(evaluation(),interval_complete=1),
                  replace(evaluation(),declared_precision_ns=1000000),
                  replace(evaluation(),declared_precision_ns=True)):
            with self.subTest(w=w),self.assertRaises(Abstain):
                predict_ns_m1_v3_exposure(m,w)

    def test_event_outside_or_unsorted_or_boolean_abstains(self):
        for seq in ((t("34204"),t("34202")),(t("34202"),t("34206")),(t("34202"),True)):
            a=training();a[0]=replace(a[0],cluster_times_ns=seq)
            with self.subTest(seq=seq),self.assertRaises(Abstain):
                fit_ns_m1_v3_train_only(a)

    def test_training_evaluation_overlap_abstains(self):
        m=fit_ns_m1_v3_train_only(training())
        with self.assertRaises(Abstain):
            predict_ns_m1_v3_exposure(m,replace(evaluation(),run_id="low-world"))

    def test_duplicate_training_source_ids_abstains(self):
        a=training();a[1]=replace(a[1],run_id="low-world")
        with self.assertRaisesRegex(Abstain,"DUPLICATE"):
            fit_ns_m1_v3_train_only(a)

    def test_zero_stratum_or_zero_events_abstains(self):
        a=training();a[0]=replace(a[0],cluster_times_ns=(t("34202.5"),))
        a[1]=replace(a[1],cluster_times_ns=(t("34214.25"),))
        with self.assertRaises(Abstain):
            fit_ns_m1_v3_train_only(a)
        a=training();a[0]=replace(a[0],cluster_times_ns=())
        a[1]=replace(a[1],cluster_times_ns=(t("34212.5"),))
        with self.assertRaises(Abstain):
            fit_ns_m1_v3_train_only(a)

    def test_public_prediction_has_no_private_actors_or_eval_prints(self):
        m=fit_ns_m1_v3_train_only(training())
        e=predict_ns_m1_v3_exposure(m,evaluation())
        self.assertEqual(len(e),2)
        self.assertNotIn("cluster_times_ns",evaluation().__dict__)
        self.assertTrue(all(not hasattr(x,"owner_id") and x.causal_lagged for x in e))
        self.assertEqual(UNIT,"nanoseconds_since_exchange_local_midnight")


if __name__=="__main__":
    unittest.main()
