"""Adversarial constructed burst tests; no real market inference."""
import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from public_burst_null_falsification import (
    constructed_burst_falsification, offset_preserving_sample,
    within_cell_short_gap_count,
)


class BurstNullFalsificationTests(unittest.TestCase):
    def test_constructed_burst_rejects_uniform_exchangeability(self):
        result = constructed_burst_falsification(replicates=64)
        self.assertTrue(result["uniform_exchangeability_falsified_on_constructed_burst"])
        self.assertEqual(result["observed_short_gaps"], 42)
        self.assertTrue(result["offset_preserves_within_cell_gaps"])
        self.assertTrue(result["no_calibrated_p_values_or_real_market_FDR"])

    def test_offsets_preserve_cluster_sizes_and_short_gaps(self):
        tape = [100, 100, 101, 102, 5100, 5100, 5101, 5102]
        for i in range(20):
            sampled = offset_preserving_sample(tape, seed=9, replicate=i)
            self.assertEqual(within_cell_short_gap_count(sampled),
                             within_cell_short_gap_count(tape))
            self.assertEqual(sorted(Counter(sampled).values()),
                             sorted(Counter(tape).values()))
            self.assertEqual([x // 5000 for x in sampled],
                             [x // 5000 for x in tape])

    def test_offset_is_not_an_independent_market_null(self):
        tape = [100, 101, 102, 103]
        for i in range(20):
            sampled = offset_preserving_sample(tape, seed=17, replicate=i)
            self.assertEqual([b-a for a, b in zip(sorted(set(sampled)),
                                                   sorted(set(sampled))[1:])],
                             [1, 1, 1])

    def test_invalid_inputs_fail_closed(self):
        for tape in ([20, 10], [-1, 2], [True, 5]):
            with self.assertRaises(ValueError):
                offset_preserving_sample(tape, seed=1)
        with self.assertRaises(ValueError):
            constructed_burst_falsification(replicates=1)


if __name__ == "__main__":
    unittest.main()
