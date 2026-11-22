"""Source-free falsification of uniform-within-cell timing exchangeability.

Constructed burst is NOT a fitted Hawkes process or real-market evidence.
No inferential p-values, ownership inference, or source seeds are used.
"""
from __future__ import annotations

from collections import Counter
from random import Random

from public_conditional_timing_null import CELL_MS, conditional_cluster_sample


def within_cell_short_gap_count(timestamps, *, tolerance_ms=10):
    """Count adjacent unique timestamps at most tolerance_ms apart in a cell."""
    unique = sorted(set(timestamps))
    return sum(
        a // CELL_MS == b // CELL_MS and b - a <= tolerance_ms
        for a, b in zip(unique, unique[1:])
    )


def offset_preserving_sample(timestamps, *, seed, replicate=0):
    """Translate each cell's entire cluster pattern without changing its gaps.

    This retains all within-cell short-gap structure and multiplicities, but
    has severely restricted support and is NOT a calibrated randomization null.
    """
    if type(seed) is not int or type(replicate) is not int or replicate < 0:
        raise ValueError("seed and nonnegative replicate must be integers")
    from public_conditional_timing_null import conditional_cluster_sample
    # Reuse the validated input constraints without using its sampled values.
    conditional_cluster_sample(timestamps, seed=seed, replicate=replicate)
    counts = Counter(timestamps)
    cells = {}
    for t in sorted(counts):
        cells.setdefault(t // CELL_MS, []).append(t)
    rng = Random(f"rd-offset-preserving-v1:{seed}:{replicate}")
    result = []
    for cell, times in sorted(cells.items()):
        offsets = [t - cell * CELL_MS for t in times]
        shift = rng.randint(-offsets[0], CELL_MS - 1 - offsets[-1])
        for t in times:
            result.extend([t + shift] * counts[t])
    return result


def constructed_burst_falsification(*, replicates=64):
    """Return deterministic diagnostics, not a market p-value."""
    if type(replicates) is not int or replicates < 2:
        raise ValueError("at least two replicates required")
    # Six independent constructed cells, eight clustered events per cell,
    # and split fills at each cell's first timestamp.
    tape = []
    for cell in range(6):
        start = cell * CELL_MS + 1000
        tape.extend(start + i for i in range(8))
        tape.extend([start] * 3)
    observed = within_cell_short_gap_count(tape)
    uniform = [
        within_cell_short_gap_count(
            conditional_cluster_sample(tape, seed=404, replicate=i))
        for i in range(replicates)
    ]
    offset = [
        within_cell_short_gap_count(
            offset_preserving_sample(tape, seed=404, replicate=i))
        for i in range(replicates)
    ]
    return {
        "source": "constructed_source_free_bursts_only",
        "replicates": replicates,
        "observed_short_gaps": observed,
        "uniform_min_short_gaps": min(uniform),
        "uniform_max_short_gaps": max(uniform),
        "offset_min_short_gaps": min(offset),
        "offset_max_short_gaps": max(offset),
        "uniform_exchangeability_falsified_on_constructed_burst": max(uniform) < observed,
        "offset_preserves_within_cell_gaps": all(x == observed for x in offset),
        "no_calibrated_p_values_or_real_market_FDR": True,
    }
