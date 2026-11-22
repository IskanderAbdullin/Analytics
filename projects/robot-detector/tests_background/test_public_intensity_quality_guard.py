"""Predeclared toy precision/prior-L2 abstention controls; not source validation."""
import unittest
from tools.public_intensity_quality_guard import quality_gated_intensity_sample as gate
from tools.public_intensity_conditioned_null import subcell_occupancy


def s(t, covered=True, precision=1):
    return {"timestamp_ms": t, "covered": covered, "source_precision_ms": precision}


class TestIntensityQualityGate(unittest.TestCase):
    def test_one_ms_good_prior_observation_and_all_frozen_replicates(self):
        tape = [1000, 2000]
        for r in range(64):
            with self.subTest(replicate=r):
                a = gate(tape, [s(900), s(1900)], source_precision_ms=1, replicate=r)
                b = gate(tape, [s(900), s(1900)], source_precision_ms=1, replicate=r)
                self.assertEqual(a, b)
                self.assertEqual(a["status"], "DESCRIPTIVE_SOURCE_FREE_ONLY")
                self.assertEqual(subcell_occupancy(tape), subcell_occupancy(a["sampled_timestamps_ms"]))
                self.assertEqual(a["exchange_completeness"], "UNKNOWN")
                self.assertEqual(a["inference"], "NO_PVALUE_NO_OWNER_ID_NO_MARKET_FDR")

    def test_coarse_unknown_invalid_precision_abstains_without_sample(self):
        for precision in (None, 10, 100, 0, True, 1.5, "1"):
            with self.subTest(precision=precision):
                r = gate([1000, 2000], [s(900), s(1900)], source_precision_ms=precision)
                self.assertEqual(r["reason"], "UNSUPPORTED_OR_UNKNOWN_PRINT_PRECISION")
                self.assertIsNone(r["sampled_timestamps_ms"])

    def test_missing_and_ambiguous_prior_l2_do_not_license_sampling(self):
        cases = ([], [s(900), s(1900), s(999, precision=2), s(1999, precision=2)])
        for snaps in cases:
            with self.subTest(snapshots=snaps):
                r = gate([1000, 2000], snaps, source_precision_ms=1)
                self.assertEqual(r["reason"], "PRIOR_L2_QUALITY")
                self.assertEqual(r["status"], "ABSTAIN")
                self.assertIsNone(r["sampled_timestamps_ms"])
        with self.assertRaises(ValueError):
            gate([1000, 2000], [dict(s(900), agent_id="private")], source_precision_ms=1)

    def test_single_timestamp_and_boolean_replicate_fail_closed(self):
        r = gate([1000, 1000], [s(900)], source_precision_ms=1)
        self.assertEqual(r["reason"], "ABSTAIN_NO_GAPS")
        self.assertIsNone(r["sampled_timestamps_ms"])
        with self.assertRaises(ValueError):
            gate([1000, 2000], [s(900), s(1900)], source_precision_ms=1, replicate=True)


if __name__ == '__main__':
    unittest.main()
