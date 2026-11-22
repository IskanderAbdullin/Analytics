"""Adversarial causal/coverage tests; constructed public-only fixtures."""
import unittest
from tools.public_period_l2_gate import scan_with_prior_l2

def s(t, covered=True, precision=1):
    return {"timestamp_ms": t, "covered": covered, "source_precision_ms": precision}

class PriorL2GateTests(unittest.TestCase):
    def test_prior_only_passes(self):
        r = scan_with_prior_l2([100, 20100, 40100], [s(90), s(20090), s(40090)])
        self.assertEqual(r["l2_quality"]["status"], "ELIGIBLE_LOCAL_OBSERVATION_ONLY")
        self.assertEqual(r["l2_quality"]["exchange_completeness"], "UNKNOWN")
    def test_same_time_and_future_abstain(self):
        for t in (100, 101, 102):
            with self.subTest(t=t):
                r = scan_with_prior_l2([100, 20100], [s(t), s(20090)])
                self.assertEqual(r["status"], "ABSTAIN_L2_QUALITY")
                self.assertIsNone(r["periods"][0]["fraction"])
    def test_precision_overlap_abstains(self):
        r = scan_with_prior_l2([100, 20100], [s(90, precision=10), s(20090)])
        self.assertEqual(r["status"], "ABSTAIN_L2_QUALITY")
    def test_missing_latest_prior_coverage_abstains(self):
        r = scan_with_prior_l2([100, 20100], [s(80), s(90, False), s(20090)])
        self.assertEqual(r["l2_quality"]["reasons"], {"PRIOR_L2_COVERAGE_MISSING": 1})
    def test_stale_prior_abstains(self):
        r = scan_with_prior_l2([2000, 22000], [s(0), s(21990)])
        self.assertEqual(r["status"], "ABSTAIN_L2_QUALITY")
    def test_unknown_precision_and_private_field_rejected(self):
        for sample in ({"timestamp_ms": 90, "covered": True},
                       dict(s(90), agent_id=7), s(90, precision=0)):
            with self.subTest(sample=sample), self.assertRaises(ValueError):
                scan_with_prior_l2([100, 20100], [sample])
    def test_split_fills_do_not_change_eligibility(self):
        a = scan_with_prior_l2([100, 20100], [s(90), s(20090)])
        b = scan_with_prior_l2([100] * 50 + [20100], [s(90), s(20090)])
        self.assertEqual(a["periods"], b["periods"])
        self.assertEqual(a["l2_quality"], b["l2_quality"])
    def test_no_gaps_abstains(self):
        self.assertEqual(scan_with_prior_l2([100, 100], [s(90)])["status"], "ABSTAIN_L2_QUALITY")

if __name__ == "__main__":
    unittest.main()
