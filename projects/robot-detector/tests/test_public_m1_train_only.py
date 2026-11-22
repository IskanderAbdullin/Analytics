"""Source-free adversarial M1 tests; no source, p-values or owner truth."""
import unittest
from dataclasses import replace

from tools.public_intensity_rescaling import Abstain
from tools.public_m1_train_only import (
    M1EvaluationWindow, M1TrainingRun, fit_m1_train_only, predict_m1_exposure,
)


def book(ts=0, bid=100., ask=102., **extras):
    return dict(timestamp_ms=ts, bid_price=bid, ask_price=ask,
                complete=True, source_precision_ms=1, **extras)


def runs():
    return [M1TrainingRun("training-low", 100, 500, (150, 150, 350), book(), True),
            M1TrainingRun("training-high", 200, 600, (250,), book(10, 100., 104.), True)]


class M1ConservativeTrainOnlyTests(unittest.TestCase):
    def test_two_training_strata_rates_and_fixed_prediction(self):
        m = fit_m1_train_only(runs())
        self.assertAlmostEqual(m.low_rate_per_second, 5.)
        self.assertAlmostEqual(m.high_rate_per_second, 2.5)
        self.assertEqual((m.low_cluster_count, m.high_cluster_count), (2, 1))
        predicted = predict_m1_exposure(m, M1EvaluationWindow("eval", 700, 900, book(400), True))
        self.assertEqual(predicted[0].rate_per_second, 5.)
        self.assertTrue(predicted[0].causal and predicted[0].complete)

    def test_split_fills_do_not_change_rate_or_training_median(self):
        orig = fit_m1_train_only(runs())
        alt = runs()
        alt[0] = replace(alt[0], cluster_times_ms=(150, 150, 150, 350, 350))
        self.assertEqual(fit_m1_train_only(alt), orig)

    def test_training_not_affected_by_evaluation_window(self):
        m = fit_m1_train_only(runs())
        for ts, start, end in ((300, 700, 900), (400, 600, 950)):
            w = M1EvaluationWindow("independent-eval", start, end, book(ts), True)
            predict_m1_exposure(m, w)
        self.assertEqual(m, fit_m1_train_only(runs()))

    def test_same_time_or_future_book_fails(self):
        m = fit_m1_train_only(runs())
        for ts in (700, 701, 699):
            with self.subTest(ts=ts), self.assertRaisesRegex(Abstain, "SAME_TIME"):
                predict_m1_exposure(m, M1EvaluationWindow("eval", 700, 800, book(ts), True))

    def test_stale_book_fails(self):
        m = fit_m1_train_only(runs())
        with self.assertRaisesRegex(Abstain, "STALE"):
            predict_m1_exposure(m, M1EvaluationWindow("eval", 1000, 2000, book(1), True))

    def test_coarse_precision_and_false_coverage_fail(self):
        m = fit_m1_train_only(runs())
        w = M1EvaluationWindow("eval", 700, 900, book(400), True)
        for b in (dict(book(400), source_precision_ms=10), dict(book(400), complete=False),
                  dict(book(400), complete=1), dict(book(400), source_precision_ms=True)):
            with self.subTest(book=b), self.assertRaisesRegex(Abstain, "CLOCK_OR_INCOMPLETE"):
                predict_m1_exposure(m, replace(w, book_snapshot=b))
        for coverage in (False, "yes", 1, None):
            with self.subTest(coverage=coverage), self.assertRaisesRegex(Abstain, "COMPLETE_EXPOSURE"):
                predict_m1_exposure(m, replace(w, interval_complete=coverage))

    def test_invalid_bbo_and_private_oracle_field_fail(self):
        m = fit_m1_train_only(runs())
        w = M1EvaluationWindow("eval", 700, 900, book(400), True)
        for b in (book(400, 105, 104), book(400, 0, 105), book(400, 100, float("nan")),
                  book(400, True, 105), dict(book(400), agent_id=7),
                  dict(book(400), private_truth="robot")):
            with self.subTest(book=b), self.assertRaises(Abstain):
                predict_m1_exposure(m, replace(w, book_snapshot=b))

    def test_zero_training_cases_and_one_stratum_abstain(self):
        for candidate in ([], [runs()[0]],
                          [runs()[0], replace(runs()[1], book_snapshot=book(10))],
                          [runs()[0], replace(runs()[1], cluster_times_ms=())]):
            with self.subTest(candidate=candidate), self.assertRaises(Abstain):
                fit_m1_train_only(candidate)

    def test_duplicate_run_id_and_train_eval_overlap_fail(self):
        items = runs()
        with self.assertRaisesRegex(Abstain, "DUPLICATE"):
            fit_m1_train_only([items[0], replace(items[1], run_id=items[0].run_id)])
        m = fit_m1_train_only(items)
        with self.assertRaisesRegex(Abstain, "OVERLAP"):
            predict_m1_exposure(m, M1EvaluationWindow("training-low", 700, 900, book(400), True))

    def test_invalid_and_unsorted_cluster_times_fail(self):
        for t in ((350, 150), (100, 150), (150, 500), (150, True), (150, 151.5)):
            rr = runs()
            rr[0] = replace(rr[0], cluster_times_ms=t)
            with self.subTest(t=t), self.assertRaises(Abstain):
                fit_m1_train_only(rr)

    def test_invalid_exposure_and_private_run_types_fail(self):
        for bad in (replace(runs()[0], run_id=""),
                    replace(runs()[0], start_ms=True),
                    replace(runs()[0], end_ms=100),
                    replace(runs()[0], interval_complete=1),
                    replace(runs()[0], book_snapshot=dict(book(), hidden_agent="x"))):
            with self.subTest(bad=bad), self.assertRaises(Abstain):
                fit_m1_train_only([bad, runs()[1]])

    def test_non_target_periodic_tapes_are_not_owner_predictions(self):
        # Evaluated print timestamps are not accepted by M1 inference at all.
        m = fit_m1_train_only(runs())
        w = M1EvaluationWindow("eval", 700, 900, book(400), True)
        unrelated_periodic = (710, 730, 750)
        momentum_burst = (710, 711, 712)
        self.assertNotEqual(unrelated_periodic, momentum_burst)
        self.assertEqual(predict_m1_exposure(m, w), predict_m1_exposure(m, w))


if __name__ == "__main__":
    unittest.main()
