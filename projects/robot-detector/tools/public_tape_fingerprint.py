#!/usr/bin/env python3
"""Exact, anonymous ordered public book+trade hashes; no source attestation."""
from __future__ import annotations
from hashlib import sha256
from typing import Any, Iterable
from l2_probe import audit_l2_public
from l2_trade_context import PublicExecution, MAX_FILLS, MAX_SNAPSHOTS
from public_numeric import exact_nonnegative_integer as exact_int


def _line(h: Any, *parts: str | int) -> None:
    h.update(("|".join(map(str, parts)) + "\n").encode("ascii"))


def fingerprint_public_tape(
    snapshots: Any, public_executions: Iterable[PublicExecution],
    *, restore_clock_ns: int = 0, maximum_depth: int = 5
) -> dict:
    """Preserve every public L2 event and print, including equal-time order.

    Restoring a known uniform shift creates a phase-invariant fingerprint.
    Source authenticity and exchange completeness are never inferred.
    """
    restore = exact_int(restore_clock_ns, "clock restore ns")
    depth = exact_int(maximum_depth, "depth", positive=True)
    if depth > 20 or snapshots is None or len(snapshots.times_ns) > MAX_SNAPSHOTS:
        raise ValueError("Invalid bounded L2 source")
    audit_l2_public(snapshots, max_depth=depth)
    prints = tuple(public_executions)
    if len(prints) > MAX_FILLS:
        raise ValueError("Too many public prints")

    book = sha256(b"robot-detector:public-l2:v1\n")
    _line(book, "depth", depth)
    for time_ns, bids, asks in zip(snapshots.times_ns, snapshots.bids, snapshots.asks):
        _line(book, "snapshot", exact_int(time_ns, "L2 ns") + restore,
              len(bids), len(asks))
        for side, levels in (("B", bids), ("A", asks)):
            for price, lots in levels:
                _line(book, side, exact_int(price, "book price", positive=True),
                      exact_int(lots, "book lots", positive=True))

    trades = sha256(b"robot-detector:public-trades:v1\n")
    for p in prints:
        if p.reported_aggressor_side not in ("BUY", "SELL"):
            raise ValueError("Invalid public side")
        _line(trades, "execution",
              exact_int(p.time_ns, "trade ns") + restore,
              exact_int(p.price_cents, "trade price", positive=True),
              exact_int(p.quantity, "trade lots", positive=True),
              p.reported_aggressor_side)
    combined = sha256(b"robot-detector:public-tape:v1\n"
                      + book.digest() + trades.digest())
    return {
        "schema_version": "public-tape-fingerprint-v1",
        "l2_sha256": book.hexdigest(),
        "prints_sha256": trades.hexdigest(),
        "public_tape_sha256": combined.hexdigest(),
        "source_book_events": len(snapshots.times_ns),
        "source_public_prints": len(prints),
        "source_authenticity_verified": False,
    }
