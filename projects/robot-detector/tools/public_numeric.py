#!/usr/bin/env python3
"""Lossless coercion guard for public exchange nanoseconds, prices and lots.

Do not convert floats/booleans/decimals to integer ticks or quantities using
int(), since this silently truncates or invents exchange observations.
operator.index accepts exact Python and compatible NumPy integer scalars.
"""
from __future__ import annotations

from operator import index


def exact_nonnegative_integer(value: object, name: str, *, positive: bool = False) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{name}: boolean is not a valid exchange integer")
    try:
        integer = index(value)
    except (TypeError, OverflowError) as exc:
        raise ValueError(f"{name}: expected exact integer scalar, not float/text") from exc
    if integer < (1 if positive else 0):
        raise ValueError(f"{name}: out-of-range exchange integer")
    return int(integer)
