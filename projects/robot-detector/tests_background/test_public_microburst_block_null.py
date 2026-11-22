"""Frozen candidate D 10ms microburst-block relocation adversarial controls.

Pretest issue #97 comment 7075675938. Not calibrated market inference.
"""
import unittest
from collections import Counter
from tools.public_microburst_block_null import microburst_block_sample as d
from tools.public_burst_null_falsification import (
    within_cell_short_gap_count, offset_preserving_sample as b,
)


class TestMicroburstBlockNull(unittest.TestCase):
    def test_occupancy_and_tied_split_fills_all_64(self):
        tape = sorted([1000, 1000, 1000, 1001, 1002, 1003, 3000, 3000, 3001, 3002,
                       5100, 5101, 5102, 5500, 5500])
        for r in range(64):
            with self.subTest(replicate=r):
                x = d(tape, replicate=r)
                self.assertEqual(len(x), len(tape))
                self.assertEqual(within_cell_short_gap_count(x), within_cell_short_gap_count(tape))
                self.assertEqual(Counter(t // 5000 for t in set(x)),
                                 Counter(t // 5000 for t in set(tape)))
                for cell in (0, 1):
                    self.assertEqual(
                        sorted(Counter(x)[t] for t in set(x) if t // 5000 == cell),
                        sorted(Counter(tape)[t] for t in set(tape) if t // 5000 == cell),
                    )

    def test_two_bursts_vary_between_block_gap_while_b_does_not(self):
        tape = list(range(1000, 1008)) + list(range(3000, 3008))
        self.assertEqual(within_cell_short_gap_count(tape), 14)
        d_gaps, b_gaps = set(), set()
        for r in range(64):
            xx = d(tape, replicate=r)
            yy = b(tape, seed=404, replicate=r)
            self.assertEqual(within_cell_short_gap_count(xx), 14)
            self.assertEqual(within_cell_short_gap_count(yy), 14)
            d_gaps.add(xx[8] - xx[7])
            b_gaps.add(yy[8] - yy[7])
        self.assertGreater(len(d_gaps), 1)
        self.assertEqual(b_gaps, {1993})

    def test_unrelated_periodic_background_not_a_target_label(self):
        tape = [1000 + 20000 * j for j in range(6)]
        for r in range(64):
            sample = d(tape, replicate=r)
            self.assertEqual(len(sample), 6)
            self.assertEqual(within_cell_short_gap_count(sample), 0)
        self.assertEqual(d(tape, replicate=4), d(tape, replicate=4))

    def test_validation_and_empty_tape(self):
        self.assertEqual(d([], seed=404), [])
        for tape in ([2, 1], [-1], [True], [1.5], ['1']):
            with self.subTest(tape=tape), self.assertRaises(ValueError):
                d(tape)
        for kwargs in ({'seed': True}, {'seed': 1.2}, {'replicate': True}, {'replicate': -1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                d([1000], **kwargs)


if __name__ == '__main__':
    unittest.main()
