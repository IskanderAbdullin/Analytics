"""Candidate D: fixed 10ms microburst-block relocation, exploratory only.

Maintains within-block gaps and exact-time print clusters while redistributing
free space among blocks inside the same 5s cell. This cannot calibrate p-values,
physical owners or real-market FDR; short gaps are fixed by construction.
"""
from __future__ import annotations

from collections import Counter
from random import Random
from typing import Sequence

CELL_MS = 5000
LINK_GAP_MS = 10


def microburst_block_sample(timestamp_ms: Sequence[int], *, seed: int = 404,
                            replicate: int = 0) -> list[int]:
    """Sample nonnegative slack composition, preserving complete burst blocks."""
    if type(seed) is not int or type(replicate) is not int or replicate < 0:
        raise ValueError("seed and nonnegative replicate must be integers")
    stamps = list(timestamp_ms)
    if any(type(t) is not int or t < 0 for t in stamps):
        raise ValueError("timestamps must be nonnegative integer milliseconds")
    if stamps != sorted(stamps):
        raise ValueError("timestamps must be chronologically sorted")
    sizes = Counter(stamps)
    cells: dict[int, list[int]] = {}
    for t in sorted(sizes):
        cells.setdefault(t // CELL_MS, []).append(t)
    rng = Random(f"rd-microburst-block-v1:{seed}:{replicate}")
    out = []
    for cell, times in sorted(cells.items()):
        blocks: list[list[int]] = []
        for t in times:
            if not blocks or t - blocks[-1][-1] > LINK_GAP_MS:
                blocks.append([t])
            else:
                blocks[-1].append(t)
        k = len(blocks)
        spans = [b[-1] - b[0] + 1 for b in blocks]
        available = CELL_MS - sum(spans) - LINK_GAP_MS * (k - 1)
        if available < 0:
            raise ValueError("microburst blocks cannot be packed within cell")
        # Stars-and-bars: sample k ordered bar positions out of slack+k slots.
        bars = sorted(rng.sample(range(available + k), k))
        gaps = ([bars[0]] + [bars[i] - bars[i - 1] - 1 for i in range(1, k)]
                + [available + k - 1 - bars[-1]])
        pos = gaps[0]
        for i, block in enumerate(blocks):
            for t in block:
                out.extend([cell * CELL_MS + pos + t - block[0]] * sizes[t])
            pos += spans[i]
            if i < k - 1:
                pos += LINK_GAP_MS + gaps[i + 1]
    return out
