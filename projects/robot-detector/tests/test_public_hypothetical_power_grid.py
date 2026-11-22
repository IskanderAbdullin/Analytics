"""Prospectively fixed source-free power grid; not empirical source inference."""
import unittest

from tools.public_evaluation_bounds import upper_one_sided, lower_one_sided
from tools.public_hypothetical_power_grid import (
    N_GRID, P_POS_GRID, P_NEG_GRID, PER_COMPARISON_ALPHA,
    frozen_cutoffs, binomial_tail_probability,
    preregistered_hypothetical_power_panel,
)


class HypotheticalPowerGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.panel = preregistered_hypothetical_power_panel()

    def test_all_precommitted_sample_sizes_and_grid_cross_product(self):
        cases = self.panel["cases"]
        self.assertEqual(len(cases), 6*3*4)
        self.assertEqual({x["n_original_seed_worlds"] for x in cases}, set(N_GRID))
        self.assertEqual({x["hypothetical_positive_success_probability"] for x in cases},set(P_POS_GRID))
        self.assertEqual({x["hypothetical_per_negative_worst_case_error_probability"] for x in cases},set(P_NEG_GRID))
        self.assertFalse(self.panel["source_independence_verified"])
        self.assertFalse(self.panel["real_market_fdr_known"])
        self.assertFalse(self.panel["within_world_cross_cohort_independence_assumed"])

    def test_integer_cutoffs_strict_thresholds_not_retuned(self):
        for n in N_GRID:
            pos,neg=frozen_cutoffs(n)
            with self.subTest(n=n):
                self.assertIsNotNone(pos)
                self.assertIsNotNone(neg)
                self.assertGreater(lower_one_sided(pos,n,PER_COMPARISON_ALPHA), .8)
                self.assertLessEqual(lower_one_sided(pos-1,n,PER_COMPARISON_ALPHA), .8)
                self.assertLess(upper_one_sided(neg,n,PER_COMPARISON_ALPHA), .05)
                self.assertGreaterEqual(upper_one_sided(neg+1,n,PER_COMPARISON_ALPHA), .05)

    def test_tail_probabilities_exact_simple_cases(self):
        self.assertAlmostEqual(binomial_tail_probability(3,.5,3,upper=True),.125)
        self.assertAlmostEqual(binomial_tail_probability(3,.5,1,upper=False),.5)
        self.assertEqual(binomial_tail_probability(100,0.,0,upper=False),1.)
        self.assertEqual(binomial_tail_probability(100,0.,1,upper=True),0.)
        self.assertEqual(binomial_tail_probability(100,1.,100,upper=True),1.)

    def test_all_joint_probability_bounds_are_valid(self):
        for row in self.panel["cases"]:
            low=row["joint_power_lower_union_bound"]
            high=row["joint_power_upper_marginal_bound"]
            with self.subTest(n=row["n_original_seed_worlds"],
                              p_pos=row["hypothetical_positive_success_probability"],
                              p_neg=row["hypothetical_per_negative_worst_case_error_probability"]):
                self.assertGreaterEqual(low,0)
                self.assertLessEqual(low,high+1e-10)
                self.assertLessEqual(high,1.)
                self.assertLessEqual(low,row["marginal_positive_gate_power"]+1e-10)
                self.assertLessEqual(high,row["marginal_single_negative_gate_power"]+1e-10)

    def test_zero_hundred_still_has_positive_upper_error_bound(self):
        self.assertGreater(upper_one_sided(0,100,PER_COMPARISON_ALPHA),0.0295)
        self.assertLess(upper_one_sided(0,100,PER_COMPARISON_ALPHA),0.05)

    def test_hypothetical_one_hundred_worlds_can_be_inconclusive(self):
        rows=[z for z in self.panel["cases"] if z["n_original_seed_worlds"]==100 and
              z["hypothetical_positive_success_probability"]==0.9 and
              z["hypothetical_per_negative_worst_case_error_probability"]==0.02]
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["joint_power_lower_union_bound"],0)

    def test_invalid_n_and_forged_probs_fail_not_truncated(self):
        for n in (1,1001,10**500,True):
            with self.subTest(n=str(n)[:20]),self.assertRaises(ValueError):
                frozen_cutoffs(n)
        for p in (-1,1.1,True,"0.5",float("nan")):
            with self.subTest(p=repr(p)),self.assertRaises(ValueError):
                binomial_tail_probability(100,p,5,upper=True)

    def test_grid_has_no_source_or_oracle_identifiers(self):
        as_text=str(self.panel).lower()
        self.assertNotIn("agent_id",as_text)
        self.assertNotIn("private_truth",as_text)
        self.assertNotIn("owner_id",as_text)


if __name__=="__main__":
    unittest.main()
