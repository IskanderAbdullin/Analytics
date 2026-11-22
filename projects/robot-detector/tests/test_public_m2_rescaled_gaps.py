"""Source-free strict past M2 integrated gaps and hard negatives."""
import math
import unittest
from dataclasses import replace

from tools.public_intensity_rescaling import Abstain, Exposure, rescaled_cluster_gaps
from tools.public_m2_train_only import M2Model, M2Run, fit_m2_train_only, evaluate_m2_run
from tools.public_m2_rescaled_gaps import m2_rescaled_cluster_gaps


def fixed_model(mu=2.0, a=.2):
    return M2Model(mu, a, 1.0, ("training-world",), 2, 1000, ())


class M2PredictiveCompensatorTests(unittest.TestCase):
    def test_two_event_exact_analytic_integral(self):
        r=M2Run("eval",0,1000,(200,800))
        z=m2_rescaled_cluster_gaps(fixed_model(),r)
        self.assertEqual(len(z),1)
        self.assertAlmostEqual(z[0],2.0*.6+.2*(1-math.exp(-.6)),places=12)

    def test_no_self_excitation_in_current_event_and_future_suffix_invariant(self):
        m=fixed_model()
        first=M2Run("eval",0,1000,(200,800))
        other=M2Run("eval",0,1000,(200,800,900))
        self.assertEqual(m2_rescaled_cluster_gaps(m,first),
                         m2_rescaled_cluster_gaps(m,other)[:1])
        self.assertEqual(evaluate_m2_run(m,first).pre_event_intensities[0],m.mu_per_second)

    def test_split_fills_are_one_timestamp_cluster(self):
        m=fixed_model()
        plain=M2Run("eval",0,1000,(200,800))
        duplicated=M2Run("eval",0,1000,(200,200,800,800))
        self.assertEqual(m2_rescaled_cluster_gaps(m,plain),
                         m2_rescaled_cluster_gaps(m,duplicated))

    def test_constant_amplitude_zero_matches_m0_rescaling(self):
        m=fixed_model(a=0.)
        r=M2Run("eval",0,1000,(200,800))
        self.assertEqual(m2_rescaled_cluster_gaps(m,r),
                         rescaled_cluster_gaps([200,800],[Exposure(0,1000,2.)]))

    def test_compensator_partition_matches_independent_full_m2_integral(self):
        m=fixed_model()
        r=M2Run("eval",0,2000,(100,150,300,1200))
        z=m2_rescaled_cluster_gaps(m,r)
        full=evaluate_m2_run(m,r)
        prior=m.mu_per_second*(100/1000)
        # Post-last contribution includes the last event and all preceding decay.
        ts=[100,150,300,1200]
        s=sum(math.exp(-(ts[-1]-t)/1000.0) for t in ts)
        tail=(2000-ts[-1])/1000.0
        final=m.mu_per_second*tail+m.amplitude_per_second*s*(1-math.exp(-tail))
        self.assertAlmostEqual(prior+sum(z)+final, full.integrated_intensity,places=11)

    def test_missing_or_coarse_l2_like_event_quality_abstains(self):
        m=fixed_model()
        for r in (M2Run("eval",0,1000,(200,800),source_precision_ms=10),
                  M2Run("eval",0,1000,(200,800),interval_complete=False),
                  M2Run("eval",0,1000,(200,800),interval_complete=1)):
            with self.subTest(r=r),self.assertRaises(Abstain):
                m2_rescaled_cluster_gaps(m,r)

    def test_one_cluster_and_overlap_abstain(self):
        m=fixed_model()
        with self.assertRaisesRegex(Abstain,"INSUFFICIENT_UNIQUE"):
            m2_rescaled_cluster_gaps(m,M2Run("eval",0,1000,(200,200)))
        with self.assertRaisesRegex(Abstain,"OVERLAP"):
            m2_rescaled_cluster_gaps(m,M2Run("training-world",0,1000,(200,800)))

    def test_nonfinite_negative_or_huge_values_abstain(self):
        r=M2Run("eval",0,1000,(200,800))
        for val in (-1, float("nan"), float("inf"), 10**500):
            with self.subTest(v=repr(val)), self.assertRaises(Abstain):
                m2_rescaled_cluster_gaps(replace(fixed_model(),mu_per_second=val),r)
        with self.assertRaises(Abstain):
            m2_rescaled_cluster_gaps(fixed_model(),M2Run("eval",0,10**500,(200,800)))

    def test_unrelated_periodic_and_momentum_toy_gaps_are_not_owners(self):
        m=fit_m2_train_only([M2Run("training-world",0,5000,(100,101,105,3100))])
        for r in (M2Run("fixed20_non_target",0,100000,(10000,30000,50000,70000,90000)),
                  M2Run("momentum_non_target",0,100000,(20000,20001,20002,20005,80000))):
            z=m2_rescaled_cluster_gaps(m,r)
            self.assertEqual(len(z),4)
            self.assertTrue(all(math.isfinite(v) and v>0 for v in z))
            self.assertFalse(hasattr(z, "owner_id"))
            self.assertNotEqual(r.run_id, "identified_robot")


if __name__=="__main__": unittest.main()
