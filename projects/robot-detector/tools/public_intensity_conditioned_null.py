"""Uncalibrated 500ms intensity-conditioned public timestamp diagnostic.

No exchangeability guarantee, p-values, owner attribution, or market FDR.
"""
from __future__ import annotations

from collections import Counter
from random import Random
from typing import Sequence

CELL_MS = 5000
SUBCELL_MS = 500


def intensity_conditioned_cluster_sample(
    timestamp_ms: Sequence[int], *, seed: int, replicate: int = 0
) -> list[int]:
    """Preserve exact-time multiplicities and unique occupancy per UTC 500ms subcell."""
    if type(seed) is not int or type(replicate) is not int or replicate < 0:
        raise ValueError("seed must be integer and replicate nonnegative integer")
    if any(type(t) is not int or t < 0 for t in timestamp_ms):
        raise ValueError("timestamps must be nonnegative integer milliseconds")
    if list(timestamp_ms) != sorted(timestamp_ms):
        raise ValueError("timestamps must be chronologically sorted")
    counts = Counter(timestamp_ms)
    by_subcell: dict[int, list[int]] = {}
    for t in sorted(counts):
        by_subcell.setdefault(t // SUBCELL_MS, []).append(t)
    rng = Random(f"rd-intensity-500ms-v1:{seed}:{replicate}")
    output: list[int] = []
    for subcell, times in sorted(by_subcell.items()):
        if len(times) > SUBCELL_MS:
            raise ValueError("more unique events than millisecond slots")
        sampled = sorted(rng.sample(range(SUBCELL_MS), len(times)))
        for original, offset in zip(times, sampled):
            output.extend([subcell * SUBCELL_MS + offset] * counts[original])
    return output


def subcell_occupancy(timestamp_ms: Sequence[int]) -> dict[int, int]:
    return dict(sorted(Counter(t // SUBCELL_MS for t in set(timestamp_ms)).items()))
