import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from directional_shift_frozen_replication import (
    FROZEN_REPLICATION_SEEDS, LOCKED_PARAMETERS, preregister
)


class FrozenShiftProtocolTests(unittest.TestCase):
    def test_fixed_design_prevents_later_relabeling(self):
        result = preregister([1101, 1102, 1103, 1104])
        self.assertEqual(tuple(result["seeds"]), FROZEN_REPLICATION_SEEDS)
        self.assertEqual(result["modes"], ["null", "vwap", "pov"])
        self.assertEqual(result["parameters"], LOCKED_PARAMETERS)
        self.assertFalse(result["private_truth_access"])
        self.assertFalse(result["market_false_alarm_calibrated"])
        self.assertFalse(result["physical_owner_count_known"])

    def test_no_seed_or_order_substitution(self):
        for seeds in (
            [1101, 1102, 1103],
            [1101, 1103, 1102, 1104],
            [901, 902, 903, 904],
            [1101, 1102, 1103, 1111]
        ):
            with self.subTest(seeds=seeds), self.assertRaises(ValueError):
                preregister(seeds)


if __name__ == "__main__":
    unittest.main(verbosity=2)
