"""Exact predetermined heldout point-process likelihood negatives."""
import math
import unittest

from tools.public_intensity_rescaling import Abstain, Exposure
from tools.public_fixed_intensity_likelihood import heldout_fixed_intensity_log_likelihood as score
from tools.public_m2_train_only import M2Model,M2Run,evaluate_m2_run


class FixedPredictiveLikelihoodTests(unittest.TestCase):
    def test_m0_constant_rate_full_window_known_log_likelihood(self):
        r=score([100,200,300],[Exposure(0,1000,2)],start_ms=0,end_ms=1000)
        self.assertAlmostEqual(r["heldout_log_likelihood"],3*math.log(2)-2)
        self.assertEqual(r["unique_public_clusters"],3)
        self.assertAlmostEqual(r["integrated_intensity"],2.)

    def test_split_fills_cannot_increase_score(self):
        e=[Exposure(0,1000,2)]
        self.assertEqual(score((100,200,300),e,start_ms=0,end_ms=1000),
                         score((100,100,200,200,300),e,start_ms=0,end_ms=1000))

    def test_same_delayed_transition_boundary_uses_new_known_rate(self):
        e=[Exposure(0,500,1),Exposure(500,1000,3)]
        r=score((250,500),e,start_ms=0,end_ms=1000)
        self.assertAlmostEqual(r["heldout_log_likelihood"],math.log(3)-2)
        self.assertEqual(r["exposure_segments"],2)

    def test_empty_source_complete_window_is_rate_integral_not_no_robot(self):
        r=score((),[Exposure(0,1000,2)],start_ms=0,end_ms=1000)
        self.assertEqual(r["unique_public_clusters"],0)
        self.assertEqual(r["heldout_log_likelihood"],-2)
        self.assertFalse(r["real_market_fdr_known"])

    def test_incomplete_overlapping_or_out_of_order_exposure_abstains(self):
        for exposure in (
            [Exposure(100,1000,1)],
            [Exposure(0,500,1),Exposure(600,1000,1)],
            [Exposure(0,600,1),Exposure(500,1000,1)],
            [Exposure(500,1000,1),Exposure(0,500,1)],
            [Exposure(0,900,1)],
        ):
            with self.subTest(exposure=exposure),self.assertRaises(Abstain):
                score((250,700),exposure,start_ms=0,end_ms=1000)

    def test_invalid_noncausal_exposure_and_broken_rates_abstain(self):
        for bad in ("1.0",0,-1,True,float("nan"),float("inf"),10**500):
            with self.subTest(rate=repr(bad)),self.assertRaises(Abstain):
                score([250,700],[Exposure(0,1000,bad)],start_ms=0,end_ms=1000)
        for flag in ("complete","causal"):
            for bad in (False,1,"yes",None):
                x={"complete":True,"causal":True};x[flag]=bad
                with self.subTest(flag=flag,bad=repr(bad)),self.assertRaises(Abstain):
                    score((250,700),[Exposure(0,1000,1,**x)],start_ms=0,end_ms=1000)

    def test_invalid_or_outside_event_time_cannot_be_silently_clipped(self):
        for times in ((500,200),(0,250),(250,1000),(True,250),(250,250.5),
                      (250,10**500),(250,{"agent_id":1})):
            with self.subTest(times=str(times)[:40]),self.assertRaises(Abstain):
                score(times,[Exposure(0,1000,1)],start_ms=0,end_ms=1000)

    def test_outside_bounded_window_is_abstention(self):
        with self.assertRaises(Abstain):
            score((100,200),[Exposure(0,10**500,1)],start_ms=0,end_ms=10**500)
        with self.assertRaises(Abstain):
            score((100,200),[Exposure(0,1000,1)],start_ms=True,end_ms=1000)

    def test_m2_amplitude_zero_matches_fixed_m0_log_likelihood_exactly(self):
        model=M2Model(2.,0.,1.,("training",),3,1000,())
        run=M2Run("eval",0,1000,(100,200,300))
        m2=evaluate_m2_run(model,run).log_likelihood
        m0=score((100,200,300),[Exposure(0,1000,2.)],start_ms=0,end_ms=1000)
        self.assertAlmostEqual(m2,m0["heldout_log_likelihood"],places=12)

    def test_non_target_periodic_and_momentum_score_without_actor_labels(self):
        exposure=[Exposure(20000,23000,2.)]
        for tape in ((20100,21000,21900,22800),(20100,20101,20102,22800),
                     (20100,20710,21930,22850)):
            r=score(tape,exposure,start_ms=20000,end_ms=23000)
            self.assertEqual(r["unique_public_clusters"],4)
            self.assertFalse(r["source_independence_verified"])
            self.assertNotIn("owner_id",r)


if __name__=="__main__": unittest.main()
