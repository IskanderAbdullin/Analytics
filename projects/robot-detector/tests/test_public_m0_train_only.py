"""Source-free adversarial tests for prospective train-only M0."""
import unittest

from tools.public_intensity_rescaling import Abstain, rescaled_cluster_gaps
from tools.public_m0_train_only import TrainingRun, fit_m0_train_only, predict_m0_exposure


class M0TrainOnlyTests(unittest.TestCase):
    def test_unique_cluster_count_and_rate(self):
        m = fit_m0_train_only([TrainingRun(0, 5000, (1000, 1000, 3000))])
        self.assertEqual(m.training_cluster_count, 2)
        self.assertEqual(m.training_exposure_ms, 5000)
        self.assertAlmostEqual(m.rate_per_second, 0.4)
        self.assertEqual(rescaled_cluster_gaps([11000, 13000], predict_m0_exposure(m, 10000, 15000)), (0.8,))

    def test_multiple_training_runs_pooled_by_exposure_not_run_average(self):
        m = fit_m0_train_only([TrainingRun(0, 1000, (500,)),
                              TrainingRun(10000, 19000, (11000, 12000))])
        self.assertEqual(m.training_run_count, 2)
        self.assertAlmostEqual(m.rate_per_second, 0.3)

    def test_evaluation_window_cannot_change_fitted_rate(self):
        m = fit_m0_train_only([TrainingRun(0, 5000, (1000, 2000))])
        self.assertEqual(predict_m0_exposure(m, 10000, 20000)[0].rate_per_second,
                         predict_m0_exposure(m, 30000, 60000)[0].rate_per_second)

    def test_empty_and_zero_count_training_abstains(self):
        for runs in ([], [TrainingRun(0, 1000, ())]):
            with self.subTest(runs=runs), self.assertRaises(Abstain):
                fit_m0_train_only(runs)

    def test_invalid_windows_abstain(self):
        for run in (TrainingRun(0, 0, ()), TrainingRun(True, 1000, (500,)),
                    TrainingRun(0, 1000.5, (500,))):
            with self.subTest(run=run), self.assertRaises(Abstain):
                fit_m0_train_only([run])

    def test_unsorted_and_outside_abstain(self):
        for times in ((800, 200), (0, 200), (200, 1000), (200, -1)):
            with self.subTest(times=times), self.assertRaises(Abstain):
                fit_m0_train_only([TrainingRun(0, 1000, times)])

    def test_boolean_and_fractional_event_times_abstain(self):
        for times in ((True, 500), (100.5, 500)):
            with self.subTest(times=times), self.assertRaises(Abstain):
                fit_m0_train_only([TrainingRun(0, 1000, times)])

    def test_evaluation_window_invalid_abstains(self):
        m = fit_m0_train_only([TrainingRun(0, 1000, (500,))])
        for start, end in ((1000, 1000), (True, 2000), (1000, 1000.5)):
            with self.subTest(start=start, end=end), self.assertRaises(Abstain):
                predict_m0_exposure(m, start, end)

    def test_invalid_model_abstains(self):
        with self.assertRaises(Abstain):
            predict_m0_exposure(object(), 1000, 2000)


if __name__ == "__main__":
    unittest.main()
