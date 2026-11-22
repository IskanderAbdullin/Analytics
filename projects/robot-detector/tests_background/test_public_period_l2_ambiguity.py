"""Precommitted source-free causal L2 ambiguity and tied-snapshot negatives.

See issue #97 comment 7075629666. No market source or oracle truth.
"""
import unittest
from itertools import product
from tools.public_period_l2_gate import scan_with_prior_l2


def s(t, covered=True, precision=1):
    return {"timestamp_ms": t, "covered": covered, "source_precision_ms": precision}


class PriorL2AmbiguityTests(unittest.TestCase):
    def test_newer_precision_overlap_blocks_older_prior_fallback(self):
        r = scan_with_prior_l2([1000, 2000], [s(900), s(999, precision=2),
                                                s(1900), s(1999, precision=2)])
        self.assertEqual(r["status"], "ABSTAIN_L2_QUALITY")
        self.assertEqual(r["l2_quality"]["reasons"], {"AMBIGUOUS_NEWER_L2_ORDER": 2})
        self.assertEqual(r["l2_quality"]["exchange_completeness"], "UNKNOWN")
        self.assertTrue(all(row["hits"] is None and row["fraction"] is None
                            for row in r["periods"]))

    def test_conflicting_covered_ties_abstain_irrespective_of_input_order(self):
        for order1, order2 in product((False, True), repeat=2):
            first = [s(900, False), s(900, True)]
            second = [s(1900, False), s(1900, True)]
            if order1: first.reverse()
            if order2: second.reverse()
            with self.subTest(order1=order1, order2=order2):
                r = scan_with_prior_l2([1000, 2000], first + second)
                self.assertEqual(r["status"], "ABSTAIN_L2_QUALITY")
                self.assertEqual(r["l2_quality"]["reasons"],
                                 {"CONFLICTING_TIED_L2_SNAPSHOTS": 2})

    def test_identical_duplicate_snapshots_and_future_do_not_change_eligibility(self):
        one = scan_with_prior_l2([1000, 2000], [s(900), s(1900)])
        duplicate = scan_with_prior_l2([1000, 2000],
                                       [s(900), s(900), s(1900), s(1900), s(5000)])
        self.assertEqual(one["l2_quality"]["status"], "ELIGIBLE_LOCAL_OBSERVATION_ONLY")
        self.assertEqual(duplicate["l2_quality"]["status"], "ELIGIBLE_LOCAL_OBSERVATION_ONLY")
        self.assertEqual(one["periods"], duplicate["periods"])
        self.assertEqual(duplicate["l2_quality"]["exchange_completeness"], "UNKNOWN")

    def test_uncovered_latest_and_private_field_fail_closed(self):
        r = scan_with_prior_l2([1000, 2000], [s(900), s(990, covered=False), s(1900)])
        self.assertEqual(r["l2_quality"]["reasons"], {"PRIOR_L2_COVERAGE_MISSING": 1})
        with self.assertRaises(ValueError):
            scan_with_prior_l2([1000, 2000], [dict(s(900), private_oracle_id="x")])


if __name__ == '__main__':
    unittest.main()
