"""Source-free adversarial regression of preregistered descriptive scan."""
import unittest
from tools.public_period_scan import PERIODS_MS, scan_public_timestamps


class PublicPeriodScanTests(unittest.TestCase):
    def test_all_periods_reported(self):
        r = scan_public_timestamps([0, 20000, 40000])
        self.assertEqual(tuple(p["period_ms"] for p in r["periods"]), PERIODS_MS)

    def test_split_fills_do_not_change_timing(self):
        a = scan_public_timestamps([0, 20000, 40000])
        b = scan_public_timestamps([0] * 100 + [20000, 40000])
        self.assertEqual(a["periods"], b["periods"])
        self.assertNotEqual(a["cluster_multiplicity_histogram"], b["cluster_multiplicity_histogram"])

    def test_unrelated_fixed_cadence_is_not_owner_truth(self):
        r = scan_public_timestamps([i * 20000 for i in range(10)])
        self.assertEqual(r["periods"][3]["fraction"], 1.0)
        self.assertEqual(r["inference"], "NO_PVALUE_NO_OWNER_ID_NO_MARKET_FDR")

    def test_no_gap_abstention(self):
        r = scan_public_timestamps([123, 123])
        self.assertEqual(r["status"], "ABSTAIN_NO_GAPS")
        self.assertTrue(all(p["fraction"] is None for p in r["periods"]))

    def test_tolerance_boundary(self):
        r = scan_public_timestamps([0, 20050, 40101])
        self.assertEqual(r["periods"][3]["hits"], 1)

    def test_invalid_input(self):
        for value in (-1, 1.5, True, "agent_id"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                scan_public_timestamps([0, value])

    def test_minute_occupancy_counts_clusters(self):
        r = scan_public_timestamps([0, 0, 60000, 60000, 60001])
        self.assertEqual(r["utc_minute_occupancy"], {0: 1, 1: 2})


if __name__ == "__main__":
    unittest.main()
