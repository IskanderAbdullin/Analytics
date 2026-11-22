"""Prospective, deterministic M2 hard negatives; no oracle or market FDR."""
import math
import unittest
from dataclasses import replace
from tools.public_intensity_rescaling import Abstain
from tools.public_m2_train_only import (M2Run, M2Model, fit_m2_train_only,
                                         evaluate_m2_run, _strictly_previous_score)


def train():
    return [M2Run("A", 0, 3000, (100, 100, 150, 500, 1100)),
            M2Run("B", 6000, 10000, (6200, 7100, 8400, 9100))]


class M2PredictabilityTests(unittest.TestCase):
    def test_all_nine_predeclared_candidates_are_scored(self):
        m = fit_m2_train_only(train())
        self.assertEqual(len(m.full_grid_train_log_likelihood), 9)
        self.assertEqual(m.training_unique_clusters, 8)
        self.assertEqual(m.training_exposure_ms, 7000)
        self.assertTrue(all(math.isfinite(c[2]) for c in m.full_grid_train_log_likelihood))

    def test_split_fill_multiplicity_does_not_change_fit(self):
        a = train()
        m = fit_m2_train_only(a)
        a[0] = replace(a[0], cluster_times_ms=(100, 100, 100, 150, 500, 1100, 1100))
        self.assertEqual(fit_m2_train_only(a), m)

    def test_first_event_has_no_self_excitation_and_future_suffix_does_not_change_past(self):
        m = fit_m2_train_only(train())
        w = M2Run("eval", 0, 1000, (100, 101, 300))
        v = evaluate_m2_run(m, w)
        self.assertEqual(v.pre_event_intensities[0], m.mu_per_second)
        suffix = evaluate_m2_run(m, replace(w, cluster_times_ms=(100, 101, 300, 990)))
        self.assertEqual(v.pre_event_intensities, suffix.pre_event_intensities[:3])

    def test_exact_integral_for_one_event(self):
        w = M2Run("eval", 0, 1000, (200,))
        score, intensities, integral = _strictly_previous_score(w, (200,), 2.0, 0.2, 1.0)
        self.assertEqual(intensities, (2.,))
        self.assertAlmostEqual(integral, 2.0+0.2*(1-math.exp(-0.8)))
        self.assertAlmostEqual(score, math.log(2.0)-integral)

    def test_offset_translation_same_train_fit(self):
        orig=fit_m2_train_only(train())
        shifted=[replace(r, start_ms=r.start_ms+100000,end_ms=r.end_ms+100000,
                         cluster_times_ms=tuple(t+100000 for t in r.cluster_times_ms)) for r in train()]
        self.assertEqual(fit_m2_train_only(shifted),orig)

    def test_training_run_overlap_rejected_on_evaluation(self):
        m=fit_m2_train_only(train())
        with self.assertRaisesRegex(Abstain,"OVERLAP"):
            evaluate_m2_run(m,M2Run("A",0,1000,(200,)))

    def test_duplicate_source_run_id_rejected(self):
        rr=train()
        rr[1]=replace(rr[1],run_id="A")
        with self.assertRaisesRegex(Abstain,"DUPLICATE"):
            fit_m2_train_only(rr)

    def test_coarse_clock_and_incomplete_coverage_abstain(self):
        m=fit_m2_train_only(train())
        for r in (M2Run("eval",0,1000,(200,),source_precision_ms=10),
                  M2Run("eval",0,1000,(200,),interval_complete=False),
                  M2Run("eval",0,1000,(200,),interval_complete=1),
                  M2Run("eval",0,1000,(200,),source_precision_ms=True)):
            with self.subTest(r=r),self.assertRaises(Abstain):
                evaluate_m2_run(m,r)

    def test_reject_invalid_times_boolean_and_unsorted(self):
        for times in ((200,100),(True,200),(100.,200),(0,500),(500,1000),(-10,50)):
            rr=train();rr[0]=replace(rr[0],cluster_times_ms=times,start_ms=0,end_ms=1000)
            with self.subTest(t=times),self.assertRaises(Abstain):
                fit_m2_train_only(rr)

    def test_reject_empty_training_and_forged_parameters(self):
        with self.assertRaises(Abstain): fit_m2_train_only([])
        with self.assertRaises(Abstain): fit_m2_train_only([M2Run("empty",0,1000,())])
        m=fit_m2_train_only(train())
        for val in (True, float("nan"), -1.0):
            with self.subTest(value=val),self.assertRaises(Abstain):
                evaluate_m2_run(replace(m,mu_per_second=val),M2Run("eval",0,1000,(200,)))

    def test_known_unrelated_periodic_and_momentum_are_not_labeled(self):
        m=fit_m2_train_only(train())
        cases=(M2Run("fixed20",0,100000,(20000,40000,60000,80000)),
               M2Run("momentum",0,100000,(20000,20001,20002,80000)),
               M2Run("poisson_like",0,100000,(1000,14400,57000,92100)))
        scored=[evaluate_m2_run(m,r) for r in cases]
        self.assertTrue(all(math.isfinite(s.log_likelihood) for s in scored))
        self.assertEqual([s.run_id for s in scored],["fixed20","momentum","poisson_like"])
        self.assertFalse(hasattr(scored[0],"owner_id"))

    def test_extreme_timestamp_exposure_and_event_abstain_not_overflow(self):
        with self.assertRaisesRegex(Abstain, "SAFE_EXACT_RANGE"):
            fit_m2_train_only([M2Run("large", 0, 10**500, (100,))])
        m = fit_m2_train_only(train())
        with self.assertRaisesRegex(Abstain, "SAFE_EXACT_RANGE"):
            evaluate_m2_run(m, M2Run("eval", 0, 10**500, (100,)))
        with self.assertRaisesRegex(Abstain, "SAFE_EXACT_RANGE"):
            evaluate_m2_run(m, M2Run("eval", 0, 10**500 + 200, (10**500,)))

    def test_extreme_forged_rate_abstains_not_overflow(self):
        m = fit_m2_train_only(train())
        for field in ("mu_per_second", "amplitude_per_second", "tau_seconds"):
            with self.subTest(field=field), self.assertRaisesRegex(Abstain, "INVALID_M2_PARAMETERS"):
                evaluate_m2_run(replace(m, **{field: 10**500}), M2Run("eval", 0, 1000, (300,)))

    def test_no_observed_eval_events_is_scored_not_fabricated_as_owners(self):
        m=fit_m2_train_only(train())
        result=evaluate_m2_run(m,M2Run("empty_eval",0,1000,()))
        self.assertEqual(result.unique_clusters,0)
        self.assertEqual(result.pre_event_intensities,())
        self.assertAlmostEqual(result.log_likelihood,-m.mu_per_second)


if __name__=="__main__": unittest.main()
