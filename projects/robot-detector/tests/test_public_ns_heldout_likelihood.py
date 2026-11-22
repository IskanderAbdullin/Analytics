"""Precommitted ns causal heldout point-process LL and negatives."""
from dataclasses import replace
from decimal import Decimal as D
import math
import unittest

from tools.public_intensity_rescaling import Abstain, Exposure
from tools.public_fixed_intensity_likelihood import heldout_fixed_intensity_log_likelihood
from tools.public_lobster_ns_time import exact_decimal_to_ns, UNIT
from tools.public_m1_v3_ns_l2 import (
    NsTrainingRun, NsEvaluationWindow, NsExposure,
    fit_ns_m1_v3_train_only, predict_ns_m1_v3_exposure,
)
from tools.public_ns_heldout_likelihood import (
    NsPublicEventWindow, heldout_ns_fixed_intensity_log_likelihood as score,
)


def t(sec): return exact_decimal_to_ns(D(str(sec)))


def book(sec,ask=102):
    return {"timestamp_ns":t(sec),"bid_price":100,"ask_price":ask,"complete":True}


def fixtures():
    runs=[
        NsTrainingRun("low-world",t("34202"),t("34206"),(t("34202.5"),t("34203.5"),t("34204.25")),
                      (book("34200"),book("34203",104))),
        NsTrainingRun("high-world",t("34212"),t("34216"),(t("34212.5"),t("34214.25")),
                      (book("34210",104),book("34213"))),
    ]
    model=fit_ns_m1_v3_train_only(runs)
    window=NsEvaluationWindow("eval",t("34222"),t("34226"),
                              (book("34220"),book("34223",104)))
    return predict_ns_m1_v3_exposure(model,window)


def events(seq=("34222.5","34224","34225.5")):
    return NsPublicEventWindow(UNIT,t("34222"),t("34226"),tuple(t(s) for s in seq))


class NanosecondHeldoutLikelihoodNegatives(unittest.TestCase):
    def test_known_three_cluster_analytic_LL_and_integral(self):
        r=score(events(),fixtures())
        self.assertAlmostEqual(r["integrated_intensity"],2.5)
        self.assertAlmostEqual(r["heldout_log_likelihood"],
                               math.log(.75)+2*math.log(.5)-2.5,places=12)
        self.assertEqual(r["unique_public_clusters"],3)

    def test_ns_vs_legacy_ms_exactly_aligned_toys_agree(self):
        n=score(events(),fixtures())
        ms_exposure=(Exposure(t("34222")//1000000,t("34224")//1000000,.75),
                     Exposure(t("34224")//1000000,t("34226")//1000000,.5))
        s=heldout_fixed_intensity_log_likelihood(
            tuple(x//1000000 for x in events().cluster_times_ns),ms_exposure,
            start_ms=t("34222")//1000000,end_ms=t("34226")//1000000)
        self.assertAlmostEqual(s["integrated_intensity"],n["integrated_intensity"],places=12)
        self.assertAlmostEqual(s["heldout_log_likelihood"],n["heldout_log_likelihood"],places=12)

    def test_distinct_one_nanosecond_cluster_adds_log_low_rate(self):
        a=score(events(),fixtures())
        added=score(events(("34222.5","34222.500000001","34224","34225.5")),fixtures())
        self.assertEqual(added["unique_public_clusters"],4)
        self.assertAlmostEqual(added["heldout_log_likelihood"]-a["heldout_log_likelihood"],
                               math.log(.75),places=12)

    def test_split_fill_same_exact_ns_does_not_increase_score(self):
        self.assertEqual(score(events(),fixtures()),
                         score(events(("34222.5","34222.5","34224","34225.5","34225.5")),fixtures()))

    def test_boundary_rate_uses_lagged_known_high_book(self):
        a=score(events(("34224",)),fixtures())
        b=score(events(("34223.999999999",)),fixtures())
        self.assertAlmostEqual(a["heldout_log_likelihood"]-b["heldout_log_likelihood"],
                               math.log(.5/.75),places=12)

    def test_empty_asserted_complete_event_window_not_owner_absence(self):
        r=score(events(()),fixtures())
        self.assertEqual(r["unique_public_clusters"],0)
        self.assertEqual(r["heldout_log_likelihood"],-2.5)
        self.assertFalse(r["real_market_fdr_known"])

    def test_missing_initial_middle_or_last_exposure_abstains(self):
        e=fixtures()
        for p in ((e[1],),(e[0],),
                  (replace(e[0],end_ns=t("34223.999999999")),e[1]),
                  (e[0],replace(e[1],start_ns=t("34223.999999999"))),
                  (e[1],e[0])):
            with self.subTest(p=p),self.assertRaises(Abstain):
                score(events(),p)

    def test_bad_rate_noncausal_and_incomplete_flags_abstain(self):
        a,b=fixtures()
        for v in (-1,0,True,None,".5",float("nan"),float("inf"),10**500):
            with self.subTest(v=repr(v)),self.assertRaises(Abstain):
                score(events(),(replace(a,rate_per_second=v),b))
        for flag in ("causal_lagged","source_complete_asserted"):
            for v in (False,1,None):
                with self.subTest(flag=flag,v=v),self.assertRaises(Abstain):
                    score(events(),(replace(a,**{flag:v}),b))

    def test_unknown_or_millisecond_unit_abstains(self):
        for unit in ("milliseconds",None,"nanoseconds_since_epoch",1):
            with self.subTest(unit=repr(unit)),self.assertRaises(Abstain):
                score(replace(events(),unit=unit),fixtures())
        with self.assertRaises(Abstain):
            score(replace(events(),interval_complete=False),fixtures())

    def test_outside_boolean_unsorted_or_unbounded_times_abstain(self):
        for seq in ((t("34225"),t("34224")),(t("34222"),),(t("34226"),),
                    (True,t("34224")),(t("34222.5"),10**500)):
            with self.subTest(seq=str(seq)[:40]),self.assertRaises(Abstain):
                score(replace(events(),cluster_times_ns=seq),fixtures())
        with self.assertRaises(Abstain):
            score(replace(events(),start_ns=34222*1000,end_ns=34226*1000),fixtures())

    def test_private_oracle_rows_invalid_not_actor_guess(self):
        with self.assertRaises(Abstain):
            score({"agent_id":9,"events":events()},fixtures())
        r=score(events(),fixtures())
        for field in ("agent_id","owner_id","private_truth","physical_bot_count"):
            self.assertNotIn(field,r)
        self.assertFalse(r["source_completeness_independently_verified"])

    def test_non_target_momentum_and_regular_inputs_not_classified(self):
        for seq in (("34222.5","34223.5","34224.5","34225.5"),
                    ("34222.500000001","34222.500000002","34222.500000003","34225.5")):
            r=score(events(seq),fixtures())
            self.assertTrue(math.isfinite(r["heldout_log_likelihood"]))
            self.assertEqual(r["status"],"SOURCE_FREE_NS_HELDOUT_NOT_CALIBRATED")
            self.assertFalse(r["physical_owner_identity_known"])


if __name__=="__main__":
    unittest.main()
