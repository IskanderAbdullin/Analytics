#!/usr/bin/env python3
"""Offline two-stream *declared* public coverage; not verified provider truth.

A quote feed and trade feed each need an independent coverage interval and
gap log. The raw ABIDES L2/print objects do not carry verified provider
provenance. This metadata is caller-asserted and NEVER proves complete real
market coverage or a real-time trading signal.
"""
from __future__ import annotations

from dataclasses import dataclass


def _ns(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label}: require nonnegative integer nanoseconds")
    return value


@dataclass(frozen=True, slots=True)
class PublicStreamClaim:
    stream_kind: str
    venue: str
    instrument: str
    session: str
    source: str
    starts_ns: int
    complete_through_ns: int
    gaps: tuple[tuple[int, int], ...] = ()

    def __post_init__(self) -> None:
        if self.stream_kind not in ("book", "trades"):
            raise ValueError("Expected public book or public trades stream")
        for name in ("venue", "instrument", "session", "source"):
            val = getattr(self, name)
            if not isinstance(val, str) or not val.strip() or len(val) > 128:
                raise ValueError(f"{name} must be an explicit nonblank identifier")
        start = _ns(self.starts_ns, "starts_ns")
        end = _ns(self.complete_through_ns, "complete_through_ns")
        if end <= start:
            raise ValueError("Exclusive complete-through must follow coverage start")
        if not isinstance(self.gaps, tuple):
            raise ValueError("Gaps must be a sorted tuple of timestamp pairs")
        previous = start
        for item in self.gaps:
            if not isinstance(item, tuple) or len(item) != 2:
                raise ValueError("Gap must be an exclusive [start,end) pair")
            lo, hi = (_ns(item[0], "gap start"), _ns(item[1], "gap end"))
            if lo < previous or hi <= lo or hi > end:
                raise ValueError("Gaps must be nonoverlapping, sorted, bounded, nonempty")
            previous = hi

    def covers(self, begin_ns: int, end_ns: int) -> bool:
        begin = _ns(begin_ns, "bin start")
        end = _ns(end_ns, "bin end")
        if end <= begin:
            raise ValueError("Bin interval must be nonempty")
        if begin < self.starts_ns or end > self.complete_through_ns:
            return False
        return not any(a < end and b > begin for a, b in self.gaps)


@dataclass(frozen=True, slots=True)
class DualPublicStreamClaim:
    book: PublicStreamClaim
    trades: PublicStreamClaim

    def __post_init__(self) -> None:
        if (not isinstance(self.book, PublicStreamClaim) or
            not isinstance(self.trades, PublicStreamClaim)):
            raise ValueError("Both independent public stream claims are required")
        if self.book.stream_kind != "book" or self.trades.stream_kind != "trades":
            raise ValueError("Book and trade streams must not be swapped")
        for name in ("venue", "instrument", "session"):
            if getattr(self.book, name) != getattr(self.trades, name):
                raise ValueError(f"Cross-source public {name} mismatch")

    def is_pair_covered(self, prev_start_ns: int, current_start_ns: int,
                        current_end_ns: int) -> tuple[bool, bool]:
        """Return separately declared previous BOOK and current TRADES coverage."""
        if not (prev_start_ns < current_start_ns < current_end_ns):
            raise ValueError("Previous book bin must strictly precede current trade bin")
        return (self.book.covers(prev_start_ns, current_start_ns),
                self.trades.covers(current_start_ns, current_end_ns))


def disclose_claim(claim: DualPublicStreamClaim) -> dict:
    """Use only meta identifiers and counts, not quote/trade records or IDs."""
    if not isinstance(claim, DualPublicStreamClaim):
        raise ValueError("A validated dual public feed claim is required")
    return {
        "claim_venue": claim.book.venue,
        "claim_instrument": claim.book.instrument,
        "claim_session": claim.book.session,
        "book_source": claim.book.source,
        "trades_source": claim.trades.source,
        "book_gap_count": len(claim.book.gaps),
        "trades_gap_count": len(claim.trades.gaps),
        "cross_stream_instrument_session_match": True,
        "coverage_is_caller_declared_not_provider_verified": True,
        "raw_tape_labels_independently_verified": False,
        "market_completeness_certified": False,
    }
