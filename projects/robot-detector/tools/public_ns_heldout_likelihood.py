"""Exact nanosecond full-window predictive fixed public intensity score.

Precommitted: docs/CONDITIONAL_NS_HELDOUT_LL_PREREG_20261122.md
For train-frozen ns causal exposure only, NOT market FDR or actor owners.
"""
from bisect import bisect_right
from dataclasses import dataclass
from math import fsum, isfinite, log

from tools.public_intensity_rescaling import Abstain
from tools.public_m1_v3_ns_l2 import NsExposure, _valid_ns
from tools.public_lobster_ns_time import UNIT, NS_PER_SECOND

MAX_EVENTS=100000
MAX_SEGMENTS=100000


@dataclass(frozen=True)
class NsPublicEventWindow:
    unit: str
    start_ns: int
    end_ns: int
    cluster_times_ns: tuple
    interval_complete: bool = True


def _rate_ok(value):
    if type(value) not in (int,float):
        return False
    try:
        return isfinite(value) and value>0
    except (OverflowError,TypeError,ValueError):
        return False


def heldout_ns_fixed_intensity_log_likelihood(observed, exposure):
    """No future learning or hidden actor input; expose aggregate scores only."""
    if type(observed) is not NsPublicEventWindow or observed.unit != UNIT or type(observed.unit) is not str:
        raise Abstain("INVALID_OR_UNTAGGED_NS_EVENT_WINDOW")
    start,end=observed.start_ns,observed.end_ns
    if not _valid_ns(start) or not _valid_ns(end) or start>=end:
        raise Abstain("INVALID_NANOS_OBSERVATION_INTERVAL")
    if type(observed.interval_complete) is not bool or not observed.interval_complete:
        raise Abstain("UNVERIFIED_NS_PUBLIC_EVENT_COVERAGE")
    times=observed.cluster_times_ns
    if type(times) not in (tuple,list) or len(times)>MAX_EVENTS:
        raise Abstain("INVALID_OR_EXCESSIVE_NS_PUBLIC_CLUSTERS")
    if any(not _valid_ns(t) for t in times) or list(times)!=sorted(times):
        raise Abstain("INVALID_OR_UNSORTED_NS_EVENT_TIMES")
    if any(not start<t<end for t in times):
        raise Abstain("PUBLIC_NS_EVENT_OUTSIDE_EXPOSURE")
    if type(exposure) not in (tuple,list) or not 1<=len(exposure)<=MAX_SEGMENTS:
        raise Abstain("NO_OR_EXCESSIVE_NS_EXPOSURE")
    cursor=start
    begins=[]
    rates=[]
    integral_terms=[]
    for e in exposure:
        if type(e) is not NsExposure or not _valid_ns(e.start_ns) or not _valid_ns(e.end_ns):
            raise Abstain("INVALID_NS_EXPOSURE_RECORD")
        if e.start_ns!=cursor or e.end_ns<=e.start_ns or e.end_ns>end:
            raise Abstain("GAPPED_OVERLAPPING_OR_OUT_OF_ORDER_NS_EXPOSURE")
        if (type(e.source_complete_asserted) is not bool or not e.source_complete_asserted or
            type(e.causal_lagged) is not bool or not e.causal_lagged or not _rate_ok(e.rate_per_second)):
            raise Abstain("INVALID_NONCAUSAL_OR_NONFINITE_NS_RATE")
        duration=e.end_ns-e.start_ns
        expected=e.rate_per_second*(duration/NS_PER_SECOND)
        if not isfinite(expected) or expected<=0:
            raise Abstain("NONFINITE_NS_EXPOSURE_COMPENSATOR")
        begins.append(e.start_ns)
        rates.append(e.rate_per_second)
        integral_terms.append(expected)
        cursor=e.end_ns
    if cursor!=end:
        raise Abstain("INCOMPLETE_NS_PUBLIC_EXPOSURE_END")
    integral=fsum(integral_terms)
    if not isfinite(integral) or integral<=0:
        raise Abstain("NONFINITE_NS_FULL_WINDOW_COMPENSATOR")
    unique=tuple(dict.fromkeys(times))
    logs=[]
    for t in unique:
        idx=bisect_right(begins,t)-1
        if idx<0 or t>=exposure[idx].end_ns:
            raise Abstain("NS_EVENT_LACKS_PAST_EXPOSURE")
        logs.append(log(rates[idx]))
    ll=fsum(logs)-integral
    if not isfinite(ll):
        raise Abstain("NONFINITE_NS_HELDOUT_LL")
    return {
        "status":"SOURCE_FREE_NS_HELDOUT_NOT_CALIBRATED",
        "source_clock_unit":UNIT,
        "unique_public_clusters":len(unique),
        "exposure_segments":len(exposure),
        "integrated_intensity":integral,
        "heldout_log_likelihood":ll,
        "heldout_log_likelihood_per_second":ll/((end-start)/NS_PER_SECOND),
        "source_completeness_independently_verified":False,
        "real_market_fdr_known":False,
        "physical_owner_identity_known":False,
    }
