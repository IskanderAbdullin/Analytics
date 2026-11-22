"""Synthetic hypothetical world rows; NOT independent ABIDES source results."""
import unittest
from tools.public_paired_seed_inference import (
    SCENARIOS, NEGATIVES, POSITIVE, paired_seed_world_diagnostic,
)
from tools.public_evaluation_bounds import upper_one_sided


def fake(n, positive="ALARM", negative="NO_ALARM"):
    return [
        {"seed": 91000 + i,
         "outcomes": {key: (positive if key == POSITIVE else negative) for key in SCENARIOS}}
        for i in range(n)
    ]


class PairedSeedWorldNegatives(unittest.TestCase):
    def test_strict_paired_directional_three_favorable(self):
        r = paired_seed_world_diagnostic(fake(3))
        self.assertEqual((r["paired_discordant_favorable"], r["paired_discordant_unfavorable"]), (3, 0))
        self.assertEqual(r["paired_conditional_one_sided_sign_p"], .125)
        self.assertFalse(r["real_market_fdr_known"])
        self.assertFalse(r["independence_established_by_this_checker"])

    def test_symmetry_one_favorable_one_unfavorable(self):
        a = fake(2)
        a[1]["outcomes"][POSITIVE] = "NO_ALARM"
        a[1]["outcomes"][NEGATIVES[0]] = "ALARM"
        r = paired_seed_world_diagnostic(a)
        self.assertEqual((r["paired_discordant_favorable"], r["paired_discordant_unfavorable"]), (1, 1))
        self.assertEqual(r["paired_conditional_one_sided_sign_p"], .75)

    def test_no_discordance_not_false_significance(self):
        r = paired_seed_world_diagnostic(fake(3, positive="NO_ALARM", negative="NO_ALARM"))
        self.assertEqual(r["paired_conditional_one_sided_sign_p"], 1.)

    def test_bonferroni_zero_false_alarms_is_not_zero_risk(self):
        r = paired_seed_world_diagnostic(fake(100))
        self.assertGreater(r["negative_upper_simultaneous"][NEGATIVES[0]], upper_one_sided(0, 100))
        self.assertGreater(r["negative_upper_simultaneous"][NEGATIVES[0]], 0.0295)
        self.assertLess(r["negative_upper_simultaneous"][NEGATIVES[0]], .05)
        self.assertGreater(r["contrast_lower_vs_worst_negative"], 0.)

    def test_abstention_conservatively_counts_as_negative_error_and_positive_miss(self):
        rows = fake(3, positive="ABSTAIN", negative="ABSTAIN")
        r = paired_seed_world_diagnostic(rows)
        self.assertEqual(r["status_counts"][POSITIVE]["ABSTAIN"], 3)
        self.assertEqual(r["negative_worst_case_error_counts"][NEGATIVES[0]], 3)
        self.assertEqual(r["positive_alarm_sensitivity_lower"], 0.)
        self.assertEqual(r["paired_discordant_unfavorable"], 3)
        self.assertEqual(r["paired_conditional_one_sided_sign_p"], 1.)

    def test_unrelated_periodic_and_momentum_are_negative(self):
        rows = fake(6)
        rows[0]["outcomes"][NEGATIVES[1]] = "ALARM"
        rows[1]["outcomes"][NEGATIVES[2]] = "ABSTAIN"
        rows[2]["outcomes"][NEGATIVES[0]] = "ALARM"
        r = paired_seed_world_diagnostic(rows)
        self.assertEqual(r["negative_worst_case_error_counts"], {NEGATIVES[0]: 1, NEGATIVES[1]: 1, NEGATIVES[2]: 1})
        self.assertEqual(r["paired_any_negative_error_count"], 3)
        self.assertEqual(r["paired_discordant_favorable"], 3)

    def test_duplicates_or_phase_rows_not_independent_worlds(self):
        r = fake(3)
        r.append(dict(r[0]))
        with self.assertRaisesRegex(ValueError, "DEPENDENT_REPLAY"):
            paired_seed_world_diagnostic(r)
        r = fake(3); r[0]["phase"] = "10s"
        with self.assertRaisesRegex(ValueError, "FORBIDDEN"):
            paired_seed_world_diagnostic(r)

    def test_missing_cohort_unknown_status_or_oracle_field_fails(self):
        a=fake(2); del a[0]["outcomes"][NEGATIVES[0]]
        with self.assertRaisesRegex(ValueError, "INCOMPLETE"):
            paired_seed_world_diagnostic(a)
        b=fake(2); b[0]["outcomes"][NEGATIVES[0]] = "private_robot"
        with self.assertRaisesRegex(ValueError, "STATUS"):
            paired_seed_world_diagnostic(b)
        c=fake(2); c[0]["agent_id"] = 17
        with self.assertRaisesRegex(ValueError, "FORBIDDEN"):
            paired_seed_world_diagnostic(c)

    def test_bad_seed_or_alpha_fails_closed(self):
        for bad in (True, -1, 1.5, None):
            a=fake(2);a[0]["seed"]=bad
            with self.subTest(seed=bad),self.assertRaises(ValueError):
                paired_seed_world_diagnostic(a)
        for alpha in (0, 1, True, None, "0.05", float("nan"), 10**500):
            with self.subTest(alpha=repr(alpha)),self.assertRaises(ValueError):
                paired_seed_world_diagnostic(fake(2),alpha=alpha)

    def test_bounded_world_guard_no_truncation(self):
        with self.assertRaisesRegex(ValueError, "BOUNDED_STUDY"):
            paired_seed_world_diagnostic(fake(1001))
        self.assertEqual(paired_seed_world_diagnostic(fake(1000))["original_world_count"],1000)
