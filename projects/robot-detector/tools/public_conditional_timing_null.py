"""Uncalibrated source-free conditional timestamp sampler.

This module deliberately returns no p-values. The 5-second within-cell
exchangeability assumption is NOT validated for market event times.
"""
from __future__ import annotations

from collections import Counter
from random import Random
from typing import Sequence

CELL_MS = 5000


def conditional_sample(
    timestamp_ms: Sequence[int], *, seed: int, replicate: int = 0
) -> list[int]:
    """Return sampled unique event times, preserving each 5s cell's occupancy.

    Input timestamps are public exchange milliseconds; duplicates denote
    split-fill prints, not independent events. Repeated sampled timestamps
    are prevented within a cell. This is a falsification tool, not a null
    distribution with demonstrated exchangeability.
    """
    if not isinstance(seed, int) or not isinstance(replicate, int) or replicate < 0:
        raise ValueError("seed must be integer and replicate nonnegative integer")
    if any(type(t) is not int or t < 0 for t in timestamp_ms):
        raise ValueError("timestamps must be nonnegative integer milliseconds")
    if list(timestamp_ms) != sorted(timestamp_ms):
        raise ValueError("timestamps must be sorted")
    unique = sorted(set(timestamp_ms))
    counts = Counter(t // CELL_MS for t in unique)
    if any(n > CELL_MS for n in counts.values()):
        raise ValueError("more unique events than millisecond slots in cell")
    rng = Random(f"rd-conditional-v1:{seed}:{replicate}")
    out = []
    for cell in sorted(counts):
        offsets = rng.sample(range(CELL_MS), counts[cell])
        out.extend(cell * CELL_MS + x for x in sorted(offsets))
    return out


def cell_occupancy(timestamp_ms: Sequence[int]) -> dict[int, int]:
    """Number of unique public timestamps per fixed five-second cell."""
    return dict(sorted(Counter(t // CELL_MS for t in set(timestamp_ms)).items()))


def conditional_cluster_sample(
    timestamp_ms: Sequence[int], *, seed: int, replicate: int = 0
) -> list[int]:
    """Resample timestamps while preserving simultaneous print multiplicities.

    Each original exact-time print cluster remains intact and in its original
    five-second cell. Cluster sizes follow the within-cell event rank.
    This is an uncalibrated sensitivity diagnostic, NOT a market null p-value.
    """
    sampled_unique = conditional_sample(timestamp_ms, seed=seed, replicate=replicate)
    original_unique = sorted(set(timestamp_ms))
    multiplicity = Counter(timestamp_ms)
    if len(sampled_unique) != len(original_unique):
        raise AssertionError("unique event count changed")
    if any(a // CELL_MS != b // CELL_MS
           for a, b in zip(original_unique, sampled_unique)):
        raise AssertionError("event crossed a fixed cell")
    return [
        t for t, original in zip(sampled_unique, original_unique)
        for _ in range(multiplicity[original])
    ]
