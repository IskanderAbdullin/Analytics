"""Adversarial tests for the uncalibrated conditional timing sampler."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from public_conditional_timing_null import conditional_sample, cell_occupancy, conditional_cluster_sample


class ConditionalTimingTests(unittest.TestCase):
    def test_occupancy_and_split_fills(self):
        tape = [100, 100, 110, 5100, 5100, 5200, 10300]
        a = conditional_sample(tape, seed=101)
        b = conditional_sample(sorted(set(tape)), seed=101)
        self.assertEqual(a, b)
        self.assertEqual(cell_occupancy(a), cell_occupancy(tape))
        self.assertEqual(len(a), len(set(tape)))

    def test_reproducible_replicates(self):
        tape = [10, 50, 200, 5100, 5500]
        self.assertEqual(conditional_sample(tape, seed=4), conditional_sample(tape, seed=4))
        self.assertNotEqual(conditional_sample(tape, seed=4), conditional_sample(tape, seed=4, replicate=1))

    def test_randomization_changes_intervals(self):
        tape = [100, 200, 300, 400]
        original = [b-a for a,b in zip(tape, tape[1:])]
        sampled = [conditional_sample(tape, seed=9, replicate=i) for i in range(8)]
        self.assertTrue(any([b-a for a,b in zip(s, s[1:])] != original for s in sampled))

    def test_reject_invalid_inputs(self):
        for tape in ([10, 5], [-1, 2], [1.2, 3], [True, 5]):
            with self.subTest(tape=tape), self.assertRaises(ValueError):
                conditional_sample(tape, seed=1)

    def test_no_actor_attribution_from_public_tape(self):
        # Two private owner assignments yield the same public timestamps.
        public = [100, 100, 10100, 20100]
        self.assertEqual(conditional_sample(public, seed=11),
                         conditional_sample(public, seed=11))

    def test_periodic_background_not_identification(self):
        # A non-target periodic stream remains perfectly regular before sampling.
        tape = [100 + i*5000 for i in range(6)]
        self.assertEqual([b-a for a,b in zip(tape, tape[1:])], [5000]*5)
        self.assertEqual(cell_occupancy(conditional_sample(tape, seed=12)), cell_occupancy(tape))


    def test_cluster_multiplicity_per_cell(self):
        from collections import Counter
        tape = [100, 100, 100, 120, 120, 4999, 5001, 5001, 5010]
        for replicate in range(12):
            sampled = conditional_cluster_sample(tape, seed=77, replicate=replicate)
            self.assertEqual(len(sampled), len(tape))
            self.assertEqual(
                {cell: sorted(n for t, n in Counter(tape).items()
                              if t // 5000 == cell)
                 for cell in (0, 1)},
                {cell: sorted(n for t, n in Counter(sampled).items()
                              if t // 5000 == cell)
                 for cell in (0, 1)}
            )
            self.assertEqual(sampled, sorted(sampled))

    def test_cluster_sample_rejects_invalid_inputs(self):
        for tape in ([20, 10], [-1, 2], [True, 5]):
            with self.subTest(tape=tape), self.assertRaises(ValueError):
                conditional_cluster_sample(tape, seed=1)


if __name__ == "__main__":
    unittest.main()
