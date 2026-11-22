"""Adversarial source-free tests for preregistered 500ms candidate C."""
import unittest
from collections import Counter

from public_intensity_conditioned_null import (
    intensity_conditioned_cluster_sample as sample, subcell_occupancy,
)
from public_burst_null_falsification import within_cell_short_gap_count


class TestIntensityNull(unittest.TestCase):
    def test_subcell_and_cluster_invariants(self):
        tape = sorted([1, 1, 2, 498, 499, 500, 500, 999, 4999, 5000, 5001])
        for rep in range(64):
            out = sample(tape, seed=404, replicate=rep)
            self.assertEqual(subcell_occupancy(tape), subcell_occupancy(out))
            self.assertEqual(Counter(tape).total(), Counter(out).total())
            for sub in subcell_occupancy(tape):
                old = sorted(Counter(tape)[t] for t in set(tape) if t // 500 == sub)
                new = sorted(Counter(out)[t] for t in set(out) if t // 500 == sub)
                self.assertEqual(old, new)

    def test_reproducible(self):
        tape = [100, 100, 101, 150, 500, 600]
        self.assertEqual(sample(tape, seed=404, replicate=2), sample(tape, seed=404, replicate=2))

    def test_rejects_bad_inputs(self):
        for tape in ([2, 1], [-1], [True], [1.5], ["1"]):
            with self.subTest(tape=tape), self.assertRaises(ValueError):
                sample(tape, seed=404)
        for kwargs in ({"seed": True}, {"seed": 1.2}, {"seed": 404, "replicate": True},
                       {"seed": 404, "replicate": -1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                sample([1], **kwargs)

    def test_empty_and_boundary(self):
        self.assertEqual(sample([], seed=404), [])
        self.assertEqual(subcell_occupancy(sample([499, 500, 4999, 5000], seed=404)),
                         {0: 1, 1: 1, 9: 1, 10: 1})

    def test_burst_negative_not_calibrated(self):
        tape = sorted(t for c in range(6) for t in [c * 5000 + 1000 + i for i in range(8)])
        observed = within_cell_short_gap_count(tape)
        sampled = [within_cell_short_gap_count(sample(tape, seed=404, replicate=r))
                   for r in range(64)]
        self.assertEqual(observed, 42)
        # This is a diagnostic: it does not demand a chosen statistical outcome.
        self.assertEqual(len(sampled), 64)
        self.assertTrue(all(0 <= x <= 42 for x in sampled))


if __name__ == "__main__":
    unittest.main()
