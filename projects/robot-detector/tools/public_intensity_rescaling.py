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

# Public-source input contract: this is a provenance/eligibility gate, not a
# statistical calibration or a proof of real-world source completeness.
PUBLIC_FIELDS = frozenset({"timestamp_ms", "side", "quantity", "price"})
L2_FIELDS = frozenset({"timestamp_ms", "bid_price", "ask_price", "complete"})

def validate_public_inputs(prints, l2_snapshots, *, timestamp_resolution_ms):
    """Fail closed on hidden fields, coarse clocks and non-previous L2.

    Returns the sorted public print times. Does not fit an intensity model.
    A timestamp is eligible only if a strictly earlier complete L2 snapshot
    exists; no forward fill from simultaneous/future book states.
    """
    if type(timestamp_resolution_ms) is not int or not (0 < timestamp_resolution_ms <= 1):
        raise Abstain("UNVERIFIED_OR_COARSE_CLOCK_PRECISION")
    if not isinstance(prints, (tuple, list)) or not isinstance(l2_snapshots, (tuple, list)):
        raise Abstain("INVALID_PUBLIC_RECORDS")
    def checked(record, allowed, required):
        if not isinstance(record, dict) or not required.issubset(record) or set(record) - allowed:
            raise Abstain("FORBIDDEN_OR_MISSING_PUBLIC_FIELD")
        t = record["timestamp_ms"]
        if type(t) is not int or t < 0 or t % timestamp_resolution_ms:
            raise Abstain("INVALID_PUBLIC_TIMESTAMP")
        return t
    times = [checked(p, PUBLIC_FIELDS, {"timestamp_ms"}) for p in prints]
    books = [checked(b, L2_FIELDS, {"timestamp_ms", "complete"}) for b in l2_snapshots]
    if times != sorted(times) or books != sorted(books):
        raise Abstain("UNSORTED_PUBLIC_EVENTS")
    if len(set(times)) < 2:
        raise Abstain("INSUFFICIENT_UNIQUE_CLUSTERS")
    if not books:
        raise Abstain("NO_PRIOR_L2")
    j = 0
    prior = None
    for t in sorted(set(times)):
        while j < len(books) and books[j] < t:
            if type(l2_snapshots[j]["complete"]) is not bool:
                raise Abstain("INVALID_L2_COMPLETENESS")
            prior = l2_snapshots[j]
            j += 1
        if prior is None or not prior["complete"]:
            raise Abstain("NO_COMPLETE_STRICTLY_PRIOR_L2")
    return tuple(times)
