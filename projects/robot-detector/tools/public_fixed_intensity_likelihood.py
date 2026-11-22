"""Full-window heldout fixed public intensity log likelihood; no calibrated inference.

Precommitted: docs/CONDITIONAL_FIXED_INTENSITY_HELDOUT_LL_PREREG_20261122.md
All rates must be trained independently of the evaluation public events.
"""
from bisect import bisect_right
from math import fsum, isfinite, log

from tools.public_intensity_rescaling import Abstain, Exposure

MAX_SAFE_MS=2**53-1
MAX_OBSERVATIONS=100000


def _ms(value):
    return type(value) is int and 0 <= value <= MAX_SAFE_MS


def _valid_rate(value):
    if type(value) not in (int,float):
        return False
    try:
        return isfinite(value) and value > 0
    except (OverflowError, TypeError, ValueError):
        return False


def heldout_fixed_intensity_log_likelihood(print_times_ms, exposures, *, start_ms, end_ms):
    """Sum log predictable λ at unique clusters minus full-window compensator."""
    if not _ms(start_ms) or not _ms(end_ms) or start_ms >= end_ms:
        raise Abstain("INVALID_EVALUATION_OBSERVATION_WINDOW")
    if type(print_times_ms) not in (list,tuple) or len(print_times_ms)>MAX_OBSERVATIONS:
        raise Abstain("INVALID_OR_EXCESSIVE_PUBLIC_EVENTS")
    if any(not _ms(t) for t in print_times_ms) or list(print_times_ms)!=sorted(print_times_ms):
        raise Abstain("INVALID_OR_UNSORTED_PUBLIC_TIMESTAMPS")
    if any(not (start_ms<t<end_ms) for t in print_times_ms):
        raise Abstain("EVENT_OUTSIDE_EVALUATION_WINDOW")
    if type(exposures) not in (list,tuple) or not 1<=len(exposures)<=MAX_OBSERVATIONS:
        raise Abstain("INVALID_OR_EXCESSIVE_FIXED_EXPOSURE")
    cursor=start_ms
    rates=[]
    begins=[]
    integrals=[]
    for s in exposures:
        if type(s) is not Exposure:
            raise Abstain("INVALID_EXPOSURE_RECORD")
        if (not _ms(s.start_ms) or not _ms(s.end_ms) or
            s.start_ms != cursor or s.end_ms <= s.start_ms or s.end_ms > end_ms):
            raise Abstain("GAP_OVERLAP_OR_OUT_OF_ORDER_EXPOSURE")
        if (not _valid_rate(s.rate_per_second) or
            type(s.complete) is not bool or type(s.causal) is not bool or
            not s.complete or not s.causal):
            raise Abstain("INVALID_OR_NONCAUSAL_EXPOSURE_RATE")
        part = (s.end_ms-s.start_ms)*s.rate_per_second/1000.0
        if not isfinite(part) or part <= 0:
            raise Abstain("NONFINITE_OR_ZERO_COMPENSATOR")
        begins.append(s.start_ms)
        rates.append(s.rate_per_second)
        integrals.append(part)
        cursor=s.end_ms
    if cursor != end_ms:
        raise Abstain("INCOMPLETE_EVALUATION_EXPOSURE")
    integral=fsum(integrals)
    if integral<=0 or not isfinite(integral):
        raise Abstain("NONFINITE_OR_ZERO_COMPENSATOR")
    unique=tuple(dict.fromkeys(print_times_ms))
    event_terms=[]
    for t in unique:
        idx=bisect_right(begins,t)-1
        if idx<0 or t>=exposures[idx].end_ms:
            raise Abstain("UNCOVERED_PUBLIC_EVENT")
        event_terms.append(log(rates[idx]))
    ll=fsum(event_terms)-integral
    if not isfinite(ll):
        raise Abstain("NONFINITE_HELDOUT_LOG_LIKELIHOOD")
    return {
        "status": "SOURCE_FREE_FIXED_RATE_SCORE_NOT_CALIBRATED",
        "unique_public_clusters": len(unique),
        "exposure_segments": len(exposures),
        "integrated_intensity": integral,
        "heldout_log_likelihood": ll,
        "heldout_log_likelihood_per_second": ll/((end_ms-start_ms)/1000.0),
        "real_market_fdr_known": False,
        "source_independence_verified": False,
    }
