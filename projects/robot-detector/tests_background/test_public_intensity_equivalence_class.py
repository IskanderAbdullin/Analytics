"""Predeclared source-free failure of 500ms-occupancy-only timing identifiability.

Pair fixed in issue #97 before this test was implemented. No synthetic oracle,
market truth, ownership inference, p-values or fitted thresholds.
"""
import unittest
from collections import Counter
from public_intensity_conditioned_null import intensity_conditioned_cluster_sample as model_c
from public_conditional_timing_null import conditional_cluster_sample as model_a
from public_burst_null_falsification import offset_preserving_sample as model_b, within_cell_short_gap_count

BURST = [100, 101, 102, 103, 1000, 1001, 1002, 1003]
DISPERSED = [100, 225, 350, 475, 1000, 1125, 1250, 1375]
SEED = 404
REPLICATES = range(64)


class TestIntensityEquivalenceClass(unittest.TestCase):
    def test_frozen_pair_has_same_subcell_occupancy_but_different_gaps(self):
        self.assertEqual([t // 500 for t in BURST], [t // 500 for t in DISPERSED])
        self.assertEqual(within_cell_short_gap_count(BURST), 6)
        self.assertEqual(within_cell_short_gap_count(DISPERSED), 0)

    def test_abc_behavior_all_frozen_replicates(self):
        for r in REPLICATES:
            with self.subTest(replicate=r):
                # A and C cannot distinguish two inputs in their conditioned equivalence class.
                self.assertEqual(model_a(BURST, seed=SEED, replicate=r),
                                 model_a(DISPERSED, seed=SEED, replicate=r))
                self.assertEqual(model_c(BURST, seed=SEED, replicate=r),
                                 model_c(DISPERSED, seed=SEED, replicate=r))
                # B perfectly retains each gap pattern; this is power loss, not calibration.
                self.assertEqual(within_cell_short_gap_count(model_b(BURST, seed=SEED, replicate=r)), 6)
                self.assertEqual(within_cell_short_gap_count(model_b(DISPERSED, seed=SEED, replicate=r)), 0)

    def test_matching_split_fills_preserved_without_owner_interpretation(self):
        burst = sorted(BURST + [100, 100, 1000, 1000])
        dispersed = sorted(DISPERSED + [100, 100, 1000, 1000])
        for r in REPLICATES:
            with self.subTest(replicate=r):
                sampled_a = model_c(burst, seed=SEED, replicate=r)
                sampled_b = model_c(dispersed, seed=SEED, replicate=r)
                self.assertEqual(sampled_a, sampled_b)
                self.assertEqual(len(sampled_a), 12)
                self.assertEqual(sorted(Counter(sampled_a).values()), [1,1,1,1,1,1,3,3])

    def test_coarse_precision_erases_within_subcell_burst_structure(self):
        quantized_10ms = sorted(10 * (t // 10) for t in BURST)
        self.assertEqual(len(quantized_10ms), len(BURST))
        self.assertEqual(len(set(quantized_10ms)), 2)
        self.assertEqual(within_cell_short_gap_count(quantized_10ms), 0)
        self.assertEqual(within_cell_short_gap_count(BURST), 6)
        # A single public timestamp cluster is NOT evidence of one parent order.


if __name__ == '__main__':
    unittest.main()
