"""Source-free causal piecewise-constant intensity rescaling. Not calibrated inference."""
from dataclasses import dataclass
from math import isfinite

class Abstain(ValueError):
    pass

@dataclass(frozen=True)
class Exposure:
    start_ms: int
    end_ms: int
    rate_per_second: float
    complete: bool = True
    causal: bool = True

def rescaled_cluster_gaps(print_times_ms, exposure):
    """Integrate externally fixed predictable rates across distinct public clusters."""
    if not isinstance(print_times_ms,(list,tuple)) or len(print_times_ms)<2:
        raise Abstain("INSUFFICIENT_PUBLIC_PRINTS")
    if any(type(t) is not int or t<0 for t in print_times_ms):
        raise Abstain("INVALID_TIMESTAMP")
    if list(print_times_ms)!=sorted(print_times_ms):
        raise Abstain("UNSORTED_TIMESTAMPS")
    unique=sorted(set(print_times_ms))
    if len(unique)<2:
        raise Abstain("INSUFFICIENT_UNIQUE_CLUSTERS")
    if not exposure:
        raise Abstain("MISSING_EXPOSURE")
    segments=sorted(exposure,key=lambda s:s.start_ms)
    for s in segments:
        if (type(s.start_ms) is not int or type(s.end_ms) is not int or
            s.start_ms>=s.end_ms or not isfinite(s.rate_per_second) or
            s.rate_per_second<0 or not s.complete or not s.causal):
            raise Abstain("INVALID_OR_NONCAUSAL_EXPOSURE")
    if any(a.end_ms>b.start_ms for a,b in zip(segments,segments[1:])):
        raise Abstain("OVERLAPPING_EXPOSURE")
    out=[]
    for left,right in zip(unique,unique[1:]):
        cursor=left
        integral=0.0
        for s in segments:
            if s.end_ms<=cursor: continue
            if s.start_ms>cursor: break
            upto=min(right,s.end_ms)
            if upto>cursor:
                integral+=(upto-cursor)*s.rate_per_second/1000.
                cursor=upto
            if cursor==right: break
        if cursor!=right: raise Abstain("INCOMPLETE_EXPOSURE")
        if integral<=0 or not isfinite(integral):
            raise Abstain("ZERO_OR_INVALID_INTEGRATED_INTENSITY")
        out.append(integral)
    return tuple(out)
