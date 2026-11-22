"""Source-free A/B/C descriptive falsification; NOT calibrated market inference.

Frozen development scenarios: Poisson-like exponential gaps, deterministic
momentum-like bursts, unrelated 20s periodic stream. Fixed 64 replicates,
seed 404, <=10ms short-gap metric; report every scenario and candidate.
All source-free constructed controls, not genuine ABIDES or exchange data.
"""
import random
import unittest
from collections import Counter

from public_conditional_timing_null import conditional_cluster_sample
from public_burst_null_falsification import (
    offset_preserving_sample, within_cell_short_gap_count,
)
from public_intensity_conditioned_null import intensity_conditioned_cluster_sample

REPLICATES = 64
SEED = 404
SAMPLERS = {
    "A_uniform_5s": conditional_cluster_sample,
    "B_offset_5s": offset_preserving_sample,
    "C_intensity_500ms": intensity_conditioned_cluster_sample,
}


def constructed_controls():
    rng = random.Random("rd-controls-v1:404")
    poisson = []
    t = 1000.0
    while t < 120000:
        t += rng.expovariate(1 / 75)
        if t < 120000:
            poisson.append(int(t))
    # Timestamp quantization is intentional: ties are public print clusters.
    momentum = sorted(
        c * 5000 + 1000 + j for c in range(24) for j in range(8)
    )
    periodic = [1000 + 20000 * k for k in range(6)]
    return {
        "poisson_like_quantized": sorted(poisson),
        "momentum_like_bursts": momentum,
        "unrelated_periodic_20s": periodic,
    }


def descriptive_panel():
    result = {}
    for scenario, tape in constructed_controls().items():
        observed = within_cell_short_gap_count(tape)
        rows = {}
        for name, sampler in SAMPLERS.items():
            values = [
                within_cell_short_gap_count(sampler(tape, seed=SEED, replicate=r))
                for r in range(REPLICATES)
            ]
            rows[name] = {
                "min": min(values), "max": max(values),
                "mean": sum(values) / REPLICATES,
                "all_replicates": values,
            }
        result[scenario] = {"observed": observed, "candidates": rows}
    return result


class TestConstructedControlPanel(unittest.TestCase):
    def test_all_controls_and_replicates_reported(self):
        panel = descriptive_panel()
        self.assertEqual(set(panel), {
            "poisson_like_quantized", "momentum_like_bursts",
            "unrelated_periodic_20s",
        })
        for row in panel.values():
            self.assertEqual(set(row["candidates"]), set(SAMPLERS))
            for values in row["candidates"].values():
                self.assertEqual(len(values["all_replicates"]), REPLICATES)
                self.assertEqual(values["min"], min(values["all_replicates"]))
                self.assertEqual(values["max"], max(values["all_replicates"]))

    def test_reproducible_and_preserves_public_cluster_counts(self):
        for tape in constructed_controls().values():
            for sampler in SAMPLERS.values():
                a = sampler(tape, seed=SEED, replicate=0)
                b = sampler(tape, seed=SEED, replicate=0)
                self.assertEqual(a, b)
                self.assertEqual(len(a), len(tape))
                self.assertEqual(
                    sorted(Counter(tape).values()),
                    sorted(Counter(a).values()),
                )

    def test_bursts_are_not_interpreted_as_robot_ownership(self):
        panel = descriptive_panel()
        # These are constructed non-target controls, not positive robot labels.
        self.assertEqual(panel["momentum_like_bursts"]["observed"], 24 * 7)
        self.assertEqual(panel["unrelated_periodic_20s"]["observed"], 0)
        self.assertTrue(all(
            x >= 0 for row in panel.values()
            for candidate in row["candidates"].values()
            for x in candidate["all_replicates"]
        ))


if __name__ == "__main__":
    unittest.main()
