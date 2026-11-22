"""In-memory public post-event BBO projector; never export vendor rows.

Precommitted: docs/POST_EVENT_BBO_CAUSAL_PROJECTOR_PREREG_20261122.md
Book row k is AFTER message row k; frozen M1-v2 applies 1000ms lag.
"""
from dataclasses import dataclass
from math import isfinite

from tools.public_intensity_rescaling import Abstain
from tools.public_m1_dynamic_l2 import LAG_MS, MAX_SAFE_MS

ALLOWED_FIELDS = frozenset({"timestamp_ms", "bid_price", "ask_price", "complete"})
MAX_ROWS = 100000


@dataclass(frozen=True)
class PublicPostEventProjection:
    snapshots: tuple  # in-memory only; do not export vendor records
    safe_aggregate: dict


def _valid_price(x):
    if type(x) not in (int, float):
        return False
    try:
        return isfinite(x) and x > 0
    except (OverflowError, TypeError, ValueError):
        return False


def project_paired_post_event_bbo(
    rows, *, source_precision_ms, interval_complete,
    declared_message_rows, declared_book_rows,
):
    """Choose final post-event BBO for each public timestamp; not pre-event.

    The caller's precision, continuity and pairing assertions cannot prove
    source exchange completeness or actual provider timestamp fidelity.
    """
    if type(source_precision_ms) is not int or source_precision_ms != 1:
        raise Abstain("UNVERIFIED_OR_COARSE_SOURCE_PRECISION")
    if type(interval_complete) is not bool or not interval_complete:
        raise Abstain("UNVERIFIED_SOURCE_EVENT_CONTINUITY")
    if type(rows) not in (list, tuple) or not 1 <= len(rows) <= MAX_ROWS:
        raise Abstain("EMPTY_OR_EXCESSIVE_POST_EVENT_PAIRS")
    if (type(declared_message_rows) is not int or
        type(declared_book_rows) is not int or
        declared_message_rows != declared_book_rows or
        declared_message_rows != len(rows)):
        raise Abstain("UNALIGNED_POST_EVENT_MESSAGE_BOOK_ROWS")
    projection = []
    tied = 0
    for row in rows:
        if type(row) is not dict or set(row) != ALLOWED_FIELDS:
            raise Abstain("FORBIDDEN_OR_MISSING_POST_EVENT_PUBLIC_FIELD")
        t = row["timestamp_ms"]
        if type(t) is not int or not 0 <= t <= MAX_SAFE_MS-LAG_MS:
            raise Abstain("INVALID_OR_UNSAFE_SOURCE_TIMESTAMP")
        if type(row["complete"]) is not bool or not row["complete"]:
            raise Abstain("MISSING_POST_EVENT_BBO_COVERAGE")
        bid, ask = row["bid_price"], row["ask_price"]
        if not _valid_price(bid) or not _valid_price(ask) or bid > ask:
            raise Abstain("INVALID_POST_EVENT_PUBLIC_BBO")
        clean = {"timestamp_ms": t, "bid_price": bid, "ask_price": ask, "complete": True}
        if projection and t < projection[-1]["timestamp_ms"]:
            raise Abstain("UNSORTED_SOURCE_POST_EVENT_TIME")
        if projection and t == projection[-1]["timestamp_ms"]:
            projection[-1] = clean
            tied += 1
        else:
            projection.append(clean)
    return PublicPostEventProjection(
        tuple(projection),
        {
            "status": "ASSERTED_SOURCE_ONLY_POST_EVENT_NOT_PRE_EVENT_PROOF",
            "post_event_rows": len(rows),
            "unique_public_timestamps": len(projection),
            "tied_post_event_rows": tied,
            "effective_book_lag_ms": LAG_MS,
            "source_clock_independently_verified": False,
            "exchange_event_completeness_independently_verified": False,
            "vendor_raw_rows_exported": False,
            "real_market_fdr_known": False,
            "physical_owner_identity_known": False,
        },
    )
