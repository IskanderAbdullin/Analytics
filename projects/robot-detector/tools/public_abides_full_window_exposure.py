"""ABIDES source-free sparse L2 full observation-window exposure quality.

Unlike an event-only quote join, this checks ALL time including no-trade gaps.
Precommitted: docs/ABIDES_FULL_WINDOW_SPARSE_EXPOSURE_PREREG_20261122.md.
Not a source completeness attestation or real-market classifier.
"""
from bisect import bisect_right
from dataclasses import dataclass

from tools.public_intensity_rescaling import Abstain
from tools.public_abides_epoch_ns_clock import UNIT
from tools.public_abides_sparse_l2_screen import (
    PublicABIDESSparseL2Eligibility, LAG_NS, MAX_QUOTE_AGE_NS,
)


@dataclass(frozen=True)
class ABIDESPublicFullWindowSegment:
    start_ns: int
    end_ns: int
    relative_spread_numerator: int
    relative_spread_denominator: int


@dataclass(frozen=True)
class ABIDESPublicFullWindowExposure:
    unit: str
    segments: tuple
    safe_aggregate: dict


def qualify_abides_full_window_l2_exposure(
    eligibility, *, start_ns, end_ns,
    source_family="ABIDES_SIMULATOR",
    window_unit=UNIT,
    source_trade_capture_asserted=True,
    source_l2_capture_asserted=True,
):
    """Strict source-free whole-interval source-time quality, never an oracle."""
    if type(eligibility) is not PublicABIDESSparseL2Eligibility or eligibility.unit!=UNIT:
        raise Abstain("WRONG_ABIDES_SOURCE_FAMILY_OR_UNTYPED_EXECUTION_SCREEN")
    if type(source_family) is not str or source_family!="ABIDES_SIMULATOR" or type(window_unit) is not str or window_unit!=UNIT:
        raise Abstain("WRONG_SOURCE_FAMILY_OR_SIMULATED_UTC_CLOCK_UNIT")
    if (type(source_trade_capture_asserted) is not bool or not source_trade_capture_asserted or
        type(source_l2_capture_asserted) is not bool or not source_l2_capture_asserted):
        raise Abstain("SOURCE_EVENTS_OR_L2_NOT_EXTERNALLY_ASSERTED_COMPLETE")
    if (type(start_ns) is not int or type(end_ns) is not int or
        not 34200*LAG_NS <= start_ns < end_ns <= 57600*LAG_NS):
        raise Abstain("INVALID_SIMULATED_UTC_OBSERVATION_INTERVAL")
    meta=eligibility.safe_aggregate
    if (type(meta) is not dict or meta.get("source_family")!="ABIDES_SIMULATOR" or
        meta.get("whole_trade_window_eligible_under_assertions_only") is not True or
        meta.get("full_window_L2_exposure_coverage_independently_proven") is not False or
        meta.get("public_source_trade_capture_independently_proven") is not False or
        meta.get("public_sparse_l2_distinct_exact_ns_quote_times")!=len(eligibility.public_post_event_l2_quotes) or
        meta.get("trade_rows_with_strict_prior_lagged_BBO")!=len(eligibility.public_trade_times_ns)):
        raise Abstain("UNVERIFIED_OR_UNRECONCILED_ABIDES_SOURCE_QUALIFICATION")
    if any(type(t) is not int or not start_ns<t<end_ns for t in eligibility.public_trade_times_ns):
        raise Abstain("ABIDES_PUBLIC_EXECUTIONS_OUTSIDE_OBSERVATION_WINDOW")
    quotes=eligibility.public_post_event_l2_quotes
    if type(quotes) is not tuple or not quotes or len(quotes)>100000:
        raise Abstain("MISSING_OR_UNBOUNDED_ABIDES_SPARSE_QUOTE_TAPE")
    ticks=[]
    for q in quotes:
        if (type(q) is not tuple or len(q)!=3 or
            any(type(v) is not int for v in q) or
            not 34200*LAG_NS<=q[0]<end_ns or
            not 0<q[1]<q[2] or
            (ticks and q[0]<=ticks[-1])):
            raise Abstain("INVALID_ABIDES_PUBLIC_SPARSE_QUOTE_SOURCE_STATE")
        ticks.append(q[0])
    eff=[t+LAG_NS for t in ticks]
    if bisect_right(eff,start_ns)==0:
        raise Abstain("NO_PREVIOUS_CAUSAL_LAGGED_ABIDES_BBO_AT_INTERVAL_START")
    breaks=[start_ns]+[t for t in eff if start_ns<t<end_ns]+[end_ns]
    segments=[]
    for left,right in zip(breaks,breaks[1:]):
        idx=bisect_right(eff,left)-1
        if idx<0 or left>=right or right-quotes[idx][0]>MAX_QUOTE_AGE_NS:
            raise Abstain("INCOMPLETE_OR_STALE_FULL_WINDOW_L2_TIME_EXPOSURE")
        _,bid,ask=quotes[idx]
        segments.append(ABIDESPublicFullWindowSegment(left,right,ask-bid,ask+bid))
    if sum(x.end_ns-x.start_ns for x in segments)!=end_ns-start_ns:
        raise Abstain("ABIDES_FULL_WINDOW_PUBLIC_EXPOSURE_NOT_TILED")
    return ABIDESPublicFullWindowExposure(
        UNIT,tuple(segments),{
            "status":"SOURCE_FREE_ABIDES_FULL_WINDOW_L2_EXPOSURE_NOT_SOURCE_CERTIFIED",
            "source_family":"ABIDES_SIMULATOR",
            "unit":UNIT,
            "public_exposure_segment_count":len(segments),
            "public_exposure_duration_ns":end_ns-start_ns,
            "exact_nanosecond_window_tiling_valid":True,
            "quote_lag_ns":LAG_NS,
            "max_quote_age_at_segment_right_ns":MAX_QUOTE_AGE_NS,
            "source_asserted_event_and_quote_coverage":True,
            "original_market_source_event_completeness_independently_verified":False,
            "source_clock_and_exchange_latency_externally_attested":False,
            "market_executions_represent_LOBSTER_visible_type4":False,
            "source_is_independent_blind_original_world":False,
            "physical_owner_identity_known":False,
            "real_market_fdr_known":False,
            "raw_trade_or_L2_rows_exported":False,
        })
