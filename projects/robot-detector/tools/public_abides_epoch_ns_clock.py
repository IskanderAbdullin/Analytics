"""Source-free ABIDES Unix epoch ns -> explicitly simulated UTC midnight ns.

Pinned design: docs/ABIDES_EPOCH_NS_PRECISION_PREREG_20261122.md.
Never cast simulated UTC time directly to LOBSTER exchange-local M1-v3.
"""
from dataclasses import dataclass
from datetime import date, datetime
import re
from tools.public_intensity_rescaling import Abstain

NS = 1_000_000_000
MAX_INT64_NS = (1 << 63) - 1
MAX_SAFE_NORMALIZED_NS = (1 << 53) - 1
MAX_TOY = 100000
SESSION_START_NS = 34200 * NS
SESSION_END_NS = 57600 * NS
SOURCE_UNIT = "unix_epoch_nanoseconds"
UNIT = "ns_since_simulated_utc_midnight"
PINNED_REVISION = "ac7a2a7bf6e406cd2bbed887e22c5a5a790bb242"
ORIGIN = date(1970, 1, 1)


@dataclass(frozen=True)
class ABIDESSimulatedUTCClockTape:
    unit: str
    ticks: tuple
    safe_aggregate: dict


def _utc_midnight_epoch_ns(simulation_date):
    if type(simulation_date) is not str or re.fullmatch(r"[0-9]{8}",simulation_date) is None:
        raise Abstain("UNKNOWN_OR_UNTYPED_SIMULATION_UTC_DATE")
    try:
        d=datetime.strptime(simulation_date,"%Y%m%d").date()
    except ValueError as exc:
        raise Abstain("INVALID_SIMULATION_UTC_CALENDAR_DATE") from exc
    if not 1970 <= d.year <= 2262 or d.strftime("%Y%m%d") != simulation_date:
        raise Abstain("UNSUPPORTED_SIMULATION_UTC_DATE")
    return (d - ORIGIN).days * 86400 * NS


def _normalization_config(simulation_date, source_unit, pinned_revision):
    if type(source_unit) is not str or source_unit != SOURCE_UNIT:
        raise Abstain("ABIDES_CLOCK_NOT_PINNED_UNIX_EPOCH_NS")
    if type(pinned_revision) is not str or pinned_revision != PINNED_REVISION:
        raise Abstain("WRONG_OR_UNVERIFIED_ABIDES_SOURCE_REVISION")
    return _utc_midnight_epoch_ns(simulation_date)


def abides_epoch_ns_to_utc_simulated_ns(
    raw_epoch_ns, *, simulation_date, source_unit=SOURCE_UNIT,
    pinned_revision=PINNED_REVISION,
):
    """Int64 time minus explicit UTC day origin; exact arithmetic, no floats."""
    origin_ns=_normalization_config(simulation_date,source_unit,pinned_revision)
    if type(raw_epoch_ns) is not int or not 0 <= raw_epoch_ns <= MAX_INT64_NS:
        raise Abstain("INVALID_ABIDES_EPOCH_NS_INT64_TIME")
    n=raw_epoch_ns-origin_ns
    if not SESSION_START_NS <= n <= SESSION_END_NS or n > MAX_SAFE_NORMALIZED_NS:
        raise Abstain("ABIDES_TIME_NOT_IN_DECLARED_UTC_SIMULATED_SESSION")
    return n


def qualify_abides_utc_ns_tape(
    raw_epoch_times, *, simulation_date, source_unit=SOURCE_UNIT,
    pinned_revision=PINNED_REVISION,
):
    """Toy full-ns time checker, explicitly NOT real ABIDES feed attestation."""
    origin_ns=_normalization_config(simulation_date,source_unit,pinned_revision)
    if type(raw_epoch_times) not in (list,tuple) or not 1 <= len(raw_epoch_times) <= MAX_TOY:
        raise Abstain("EMPTY_OR_UNBOUNDED_SOURCE_FREE_ABIDES_TAPE")
    normalized=[]
    tied=distinct=micro_collision=submicro=0
    previous=previous_micro=None
    for value in raw_epoch_times:
        if type(value) is not int or not 0 <= value <= MAX_INT64_NS:
            raise Abstain("INVALID_ABIDES_EPOCH_NS_INT64_TIME")
        n=value-origin_ns
        if not SESSION_START_NS <= n <= SESSION_END_NS or n > MAX_SAFE_NORMALIZED_NS:
            raise Abstain("ABIDES_TIME_NOT_IN_DECLARED_UTC_SIMULATED_SESSION")
        if previous is not None and n < previous:
            raise Abstain("ABIDES_SOURCE_EVENT_CLOCK_NOT_SORTED")
        if n % 1000:
            submicro+=1
        micro=n//1000
        if previous is None or n > previous:
            distinct+=1
            if previous_micro is not None and previous_micro==micro:
                micro_collision+=1
        else:
            tied+=1
        normalized.append(n)
        previous,previous_micro=n,micro
    if distinct+tied!=len(normalized):
        raise Abstain("ABIDES_SOURCE_ORIGINAL_NS_CLOCK_ACCOUNTING_FAILURE")
    return ABIDESSimulatedUTCClockTape(
        UNIT,tuple(normalized),
        {
            "status":"SOURCE_FREE_ABIDES_UNIX_NS_CONVERSION_NOT_SOURCE_VALIDATION",
            "source_unit":SOURCE_UNIT,
            "converted_unit":UNIT,
            "source_rows":len(normalized),
            "distinct_original_nanosecond_timestamps":distinct,
            "exact_original_nanosecond_ties":tied,
            "rows_with_submicrosecond_component":submicro,
            "distinct_ns_groups_merged_by_microsecond_floor":micro_collision,
            "normalization_arithmetic_lossless":True,
            "source_runtime_date_attested_externally":False,
            "source_publisher_authenticated":False,
            "full_public_execution_and_L2_coverage_proven":False,
            "actual_ABIDES_csv_microsecond_collisions_measured":False,
            "real_market_fdr_known":False,
            "physical_owner_identity_known":False,
            "raw_source_event_times_exported":False,
        },
    )
