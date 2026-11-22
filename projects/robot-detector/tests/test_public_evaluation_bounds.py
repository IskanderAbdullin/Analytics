"""Adversarial source-free checks, no real data or source jobs."""
import math
import unittest
from tools.public_evaluation_bounds import upper_one_sided, lower_one_sided, conservative_outcome_bounds


class ExactBoundsTests(unittest.TestCase):
    def test_zero_false_alarms_not_zero_risk(self):
        self.assertAlmostEqual(upper_one_sided(0, 100), 0.029513049607039932, places=10)

    def test_all_successes_and_zero_successes(self):
        self.assertEqual(upper_one_sided(100, 100), 1)
        self.assertEqual(lower_one_sided(0, 100), 0)
        self.assertAlmostEqual(lower_one_sided(100, 100), 0.05 ** .01)

    def test_monotone_bounds(self):
        self.assertLess(upper_one_sided(3, 100), upper_one_sided(4, 100))
        self.assertLess(lower_one_sided(90, 100), lower_one_sided(91, 100))
        self.assertLess(lower_one_sided(90, 100), upper_one_sided(90, 100))

    def test_invalid_and_nonfinite_inputs_fail(self):
        for k, n, a in [(True, 100, .05), (0, True, .05), (-1, 100, .05),
                         (101, 100, .05), (0, 0, .05), (0, 100, float('nan')),
                         (0, 100, 0), (0, 100, 1)]:
            with self.subTest(k=k, n=n, a=a), self.assertRaises(ValueError):
                upper_one_sided(k, n, a)

    def test_missing_coverage_not_relabelled_as_success(self):
        r = conservative_outcome_bounds(90, 90, 100)
        self.assertEqual(r['abstentions'], 10)
        self.assertLess(r['lower_alarm_all'], 0.9)
        self.assertEqual(conservative_outcome_bounds(0, 0, 10)['status'], 'ABSTAIN')
        for args in [(0, 0, 0), (3, 2, 4), (0, 5, 4), (0, 0, -1)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                conservative_outcome_bounds(*args)


if __name__ == '__main__':
    unittest.main()
