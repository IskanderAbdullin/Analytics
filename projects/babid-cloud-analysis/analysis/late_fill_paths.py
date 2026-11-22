"""Offline synthetic-only predicate model for the competing late-fill hypotheses.

Mirrors the inspected PruneOrders / Filled / FillsSynchronized predicates.
NOT an execution of the C# trading engine or proof of historical flags.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class OrderSnapshot:
    """Fields required by PruneOrders, without account or trade IDs."""
    terminal: bool
    filled_by_state: int
    filled_by_fills: int
    updated_ms: int
    now_ms: int
    needs_check: bool = False
    resync_needed: bool = False
    query_in_flight: bool = False

    @property
    def filled(self) -> int:
        return max(self.filled_by_state, self.filled_by_fills)

    @property
    def fills_synchronized(self) -> bool:
        return self.filled_by_fills >= self.filled_by_state


def source_prune_predicate(s: OrderSnapshot, grace_ms: int = 5000) -> bool:
    """Inspected PruneOrders predicate only; does not show it was called.

    Actual removal also requires list membership and a housekeeping/prune call
    before a later fill or status update.
    """
    if grace_ms < 0:
        raise ValueError("negative grace")
    if min(s.filled_by_state, s.filled_by_fills) < 0:
        raise ValueError("negative lots")
    return (
        s.terminal
        and s.filled == 0
        and s.fills_synchronized
        and not s.needs_check
        and not s.resync_needed
        and not s.query_in_flight
        and s.now_ms - s.updated_ms >= grace_ms
    )


def after_fill_synthetic_paths(initial_journal: int, lots: int = 2) -> dict[str, dict[str, int]]:
    """Two distinct synthetic paths to unchanged Journal at late fill.

    Detached: order no longer contributes to journal, but fill changes PnL.
    Precredited: tracked order already counted status lots, fill cannot double
    count Journal. Neither path is historically confirmed.
    """
    if lots <= 0:
        raise ValueError("fill lots must be positive")
    return {
        "detached": {
            "journal_before_fill": initial_journal,
            "journal_after_fill": initial_journal,
            "pnl_delta_at_fill": -lots,
        },
        "precredited": {
            "journal_before_fill": initial_journal - lots,
            "journal_after_fill": initial_journal - lots,
            "pnl_delta_at_fill": -lots,
        },
    }


def precredit_prior_baseline(observed_flat_journal: int, lots: int = 2) -> int:
    """Required earlier journal if precredit alone precedes flat observation.

    Existence of that baseline is not implied by this calculation.
    """
    if lots <= 0:
        raise ValueError("fill lots must be positive")
    return observed_flat_journal + lots


def window_ms(cancel_ms: int, fill_processed_ms: int, grace_ms: int = 5000) -> int:
    """Maximum possible prune opportunity, not evidence of actual removal."""
    if grace_ms < 0:
        raise ValueError("negative grace")
    return max(0, fill_processed_ms - (cancel_ms + grace_ms))
