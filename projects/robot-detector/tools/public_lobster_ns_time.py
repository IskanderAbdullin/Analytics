"""Typed lossless source-time Decimal seconds to integer nanoseconds.

Frozen prereg: docs/LOBSTER_LOSSLESS_NS_TIME_PREREG_20261122.md
Never pass a returned ns tape as millisecond M1-v2 or M2 input.
Source-free only; no vendor original time series is exported.
"""
from dataclasses import dataclass
from decimal import Decimal
from tools.public_intensity_rescaling import Abstain

NS_PER_SECOND = 1000000000
NS_PER_MILLISECOND = 1000000
MAX_SAFE_TICK = (1 << 53) - 1
MAX_TOY_ROWS = 100000
SESSION_START = Decimal("34200")
SESSION_END = Decimal("57600")
UNIT = "nanoseconds_since_exchange_local_midnight"


@dataclass(frozen=True)
class SourceNanosecondTimeTape:
    unit: str
    ticks: tuple
    safe_aggregate: dict


def exact_decimal_to_ns(value):
    """Exact bounded coefficient/exponent arithmetic without binary floats."""
    if type(value) is not Decimal or not value.is_finite():
        raise Abstain("UNVERIFIED_OR_INVALID_DECIMAL_TIME")
    if not SESSION_START <= value <= SESSION_END:
        raise Abstain("SOURCE_TIME_OUTSIDE_EXCHANGE_LOCAL_SESSION")
    sign, digits, exponent = value.as_tuple()
    if sign or not digits or len(digits) > 48 or not -48 <= exponent <= 48:
        raise Abstain("UNSAFE_DECIMAL_TIME_REPRESENTATION")
    coefficient = int("".join(map(str, digits)))
    power = exponent + 9
    if power >= 0:
        if power > 24:
            raise Abstain("UNSAFE_DECIMAL_TIME_EXPONENT")
        ticks = coefficient * (10 ** power)
    else:
        divisor = 10 ** (-power)
        if coefficient % divisor:
            raise Abstain("SUB_NANOSECOND_SOURCE_PRECISION_NOT_LOSSLESS")
        ticks = coefficient // divisor
    if not 0 <= ticks <= MAX_SAFE_TICK:
        raise Abstain("SOURCE_TIME_TICK_EXCEEDS_EXACT_INTEGER_RANGE")
    if Decimal(ticks) / NS_PER_SECOND != value:
        raise Abstain("NONEXACT_SOURCE_TIME_ROUNDTRIP")
    return ticks


def lossless_decimal_time_tape(source_times):
    """Internal typed bounded toy input; safe_aggregate excludes timestamps."""
    if type(source_times) not in (tuple, list) or not 1 <= len(source_times) <= MAX_TOY_ROWS:
        raise Abstain("INVALID_OR_UNBOUNDED_SOURCE_FREE_TAPE")
    ticks = []
    exact_ties = off_ms = coarsening = distinct = 0
    prior = prior_bucket = None
    for t in source_times:
        n = exact_decimal_to_ns(t)
        if prior is not None and n < prior:
            raise Abstain("UNSORTED_EXCHANGE_LOCAL_SOURCE_TIME")
        if n % NS_PER_MILLISECOND:
            off_ms += 1
        bucket = n // NS_PER_MILLISECOND
        if prior is None or n > prior:
            distinct += 1
            if prior_bucket is not None and bucket == prior_bucket:
                coarsening += 1
        else:
            exact_ties += 1
        ticks.append(n)
        prior, prior_bucket = n, bucket
    if len(ticks) != distinct + exact_ties:
        raise Abstain("UNRECONCILED_DECIMAL_SOURCE_CLUSTERS")
    return SourceNanosecondTimeTape(UNIT, tuple(ticks), {
        "status": "SOURCE_FREE_EXACT_NS_CLOCK_NOT_MARKET_VALIDATION",
        "unit": UNIT,
        "source_rows": len(ticks),
        "distinct_exact_source_timestamps": distinct,
        "exact_source_timestamp_ties": exact_ties,
        "rows_with_submillisecond_component": off_ms,
        "distinct_source_groups_merged_if_floored_to_ms": coarsening,
        "nanosecond_encoding_exact": True,
        "source_completeness_independently_verified": False,
        "real_market_fdr_known": False,
        "physical_owner_identity_known": False,
        "vendor_source_rows_exported": False,
    })
