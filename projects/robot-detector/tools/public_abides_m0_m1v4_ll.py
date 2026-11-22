"""Source-free ABIDES public EXEC M0/M1-v4 train-only LL, not bot detection.

Precommit: docs/ABIDES_M0_M1V4_SOURCEFREE_LL_PREREG_20261122.md
ABIDES simulated-UTC public EXEC, never LOBSTER visible type4 or owners.
No original simulator jobs, independent source calibration or market FDR.
"""
from bisect import bisect_right
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
from math import isfinite, fsum, log
import re

from tools.public_intensity_rescaling import Abstain
from tools.public_abides_epoch_ns_clock import UNIT, NS
from tools.public_abides_sparse_l2_screen import PublicABIDESSparseL2Eligibility
from tools.public_abides_full_window_exposure import (
    ABIDESPublicFullWindowExposure, qualify_abides_full_window_l2_exposure,
)


@dataclass(frozen=True)
class ABIDESPublicOriginalCase:
    source_run_label: str
    start_ns: int
    end_ns: int
    public_execution_quote_screen: PublicABIDESSparseL2Eligibility
    full_window_exposure: ABIDESPublicFullWindowExposure


@dataclass(frozen=True)
class ABIDESPublicTrainOnlyIntensity:
    unit: str
    m0_rate_per_second: float
    m1_low_rate_per_second: float
    m1_high_rate_per_second: float
    median_spread_numerator: int
    median_spread_denominator: int
    train_original_run_labels: tuple
    train_internal_public_fingerprints: tuple
    train_low_unique_clusters: int
    train_high_unique_clusters: int
    train_low_exposure_ns: int
    train_high_exposure_ns: int


def _source_fingerprint(case):
    # Protected structural public projection; no private identity/provenance.
    x=(case.public_execution_quote_screen.public_trade_times_ns,
       case.public_execution_quote_screen.public_post_event_l2_quotes)
    return sha256(repr(x).encode("utf-8")).hexdigest()


def _case_segments_and_events(case):
    if type(case) is not ABIDESPublicOriginalCase:
        raise Abstain("MISSING_TYPED_PUBLIC_ABIDES_ORIGINAL_SOURCE_CASE")
    if type(case.source_run_label) is not str or re.fullmatch(r"[A-Za-z0-9_.-]{1,128}",case.source_run_label) is None:
        raise Abstain("INVALID_OR_SENSITIVE_ABIDES_SOURCE_LABEL")
    screen=case.public_execution_quote_screen
    exposure=case.full_window_exposure
    if (type(screen) is not PublicABIDESSparseL2Eligibility or
        type(exposure) is not ABIDESPublicFullWindowExposure or
        screen.unit!=UNIT or exposure.unit!=UNIT):
        raise Abstain("MIXED_SOURCE_CLOCK_OR_SOURCE_FAMILY_EXPOSURE")
    regenerated=qualify_abides_full_window_l2_exposure(
        screen,start_ns=case.start_ns,end_ns=case.end_ns,
    )
    if regenerated!=exposure:
        raise Abstain("ABIDES_SOURCE_QUOTE_EXPOSURE_MISMATCH")
    times=screen.public_trade_times_ns
    if type(times) is not tuple or not times or len(times)>100000:
        raise Abstain("INVALID_PUBLIC_ABIDES_TRADE_SOURCE_TIMES")
    if any(type(t) is not int or not case.start_ns<t<case.end_ns for t in times):
        raise Abstain("OUT_OF_WINDOW_OR_INVALID_ABIDES_PUBLIC_TRADE")
    return exposure.segments, tuple(dict.fromkeys(times))


def _spread(seg):
    return Fraction(seg.relative_spread_numerator,seg.relative_spread_denominator)


def _regime_at(segments, t, *, median):
    begins=tuple(s.start_ns for s in segments)
    idx=bisect_right(begins,t)-1
    if idx<0 or t>=segments[idx].end_ns:
        raise Abstain("ABIDES_PUBLIC_EXECUTION_NOT_COVERED_BY_SOURCE_EXPOSURE")
    return 0 if _spread(segments[idx])<=median else 1


def fit_abides_public_m0_m1v4_train_only(cases):
    """Fit from PUBLIC source-free original-run structures, no eval prints."""
    if type(cases) not in (list,tuple) or not 1<=len(cases)<=1000:
        raise Abstain("MISSING_OR_EXCESSIVE_ORIGINAL_ABIDES_TRAINING_CASES")
    records=[]
    ids=set()
    fps=set()
    weighted=[]
    total_count=total_exposure=0
    for case in cases:
        segs,times=_case_segments_and_events(case)
        fingerprint=_source_fingerprint(case)
        if case.source_run_label in ids or fingerprint in fps:
            raise Abstain("REPLAY_OR_DEPENDENT_ABIDES_ORIGINAL_TRAINING_SOURCE")
        ids.add(case.source_run_label)
        fps.add(fingerprint)
        for seg in segs:
            weighted.append((_spread(seg),seg.end_ns-seg.start_ns))
        records.append((segs,times))
        total_count+=len(times)
        total_exposure+=case.end_ns-case.start_ns
    if not weighted or total_count<=0 or total_exposure<=0:
        raise Abstain("MISSING_ABIDES_PUBLIC_TRAINING_EXPOSURE")
    weighted.sort(key=lambda x:x[0])
    cumulative=0
    median=None
    total=sum(w for _,w in weighted)
    for value,w in weighted:
        cumulative+=w
        if 2*cumulative>=total:
            median=value
            break
    if median is None:
        raise Abstain("NO_ABIDES_PUBLIC_TRAINING_MEDIAN")
    duration=[0,0]
    counts=[0,0]
    for segs,times in records:
        for s in segs:
            duration[0 if _spread(s)<=median else 1]+=s.end_ns-s.start_ns
        for t in times:
            counts[_regime_at(segs,t,median=median)]+=1
    if min(counts)<=0 or min(duration)<=0:
        raise Abstain("M1V4_ABIDES_TRAINING_SPREAD_STRATUM_UNOBSERVED")
    rates=[c*NS/w for c,w in zip(counts,duration)]
    baseline=total_count*NS/total_exposure
    if any(not isfinite(r) or r<=0 for r in (baseline,*rates)):
        raise Abstain("INVALID_ABIDES_PUBLIC_RATE_OR_PRECISION")
    return ABIDESPublicTrainOnlyIntensity(
        UNIT,baseline,rates[0],rates[1],
        median.numerator,median.denominator,
        tuple(sorted(ids)),tuple(sorted(fps)),
        counts[0],counts[1],duration[0],duration[1],
    )


def evaluate_abides_public_fixed_m0_m1v4(model, heldout):
    """Full-window LL; output source-free aggregates not algorithm-owner claims."""
    if type(model) is not ABIDESPublicTrainOnlyIntensity or model.unit!=UNIT:
        raise Abstain("INVALID_OR_UNTYPED_ABIDES_PUBLIC_TRAINED_MODEL")
    if any(type(r) not in (int,float) or not isfinite(r) or r<=0
           for r in (model.m0_rate_per_second,model.m1_low_rate_per_second,
                     model.m1_high_rate_per_second)):
        raise Abstain("INVALID_ABIDES_PUBLIC_TRAINED_RATES")
    median=Fraction(model.median_spread_numerator,model.median_spread_denominator)
    segs,clusters=_case_segments_and_events(heldout)
    if (heldout.source_run_label in model.train_original_run_labels or
        _source_fingerprint(heldout) in model.train_internal_public_fingerprints):
        raise Abstain("TRAIN_EVALUATION_SOURCE_OR_REPLAY_OVERLAP")
    m0=model.m0_rate_per_second
    m1rates=(model.m1_low_rate_per_second,model.m1_high_rate_per_second)
    m0int=m0*(heldout.end_ns-heldout.start_ns)/NS
    m1int=fsum(m1rates[0 if _spread(s)<=median else 1]*(s.end_ns-s.start_ns)/NS for s in segs)
    ll0=len(clusters)*log(m0)-m0int
    ll1=fsum(log(m1rates[_regime_at(segs,t,median=median)]) for t in clusters)-m1int
    if any(not isfinite(v) for v in (m0int,m1int,ll0,ll1)):
        raise Abstain("NONFINITE_ABIDES_PUBLIC_SOURCE_FREE_LL")
    return {
        "status":"SOURCE_FREE_ABIDES_M0_M1V4_DESCRIPTIVE_NOT_ROBOT_CALIBRATION",
        "family":"ABIDES_SIMULATOR_PUBLIC_EXEC_NOT_LOBSTER_TYPE4",
        "unit":UNIT,
        "train_source_label_count":len(model.train_original_run_labels),
        "train_low_cluster_count":model.train_low_unique_clusters,
        "train_high_cluster_count":model.train_high_unique_clusters,
        "train_low_duration_ns":model.train_low_exposure_ns,
        "train_high_duration_ns":model.train_high_exposure_ns,
        "m0_rate_per_second":m0,
        "m1_low_rate_per_second":m1rates[0],
        "m1_high_rate_per_second":m1rates[1],
        "heldout_unique_exact_ns_exec_clusters":len(clusters),
        "m0_full_window_integral":m0int,
        "m1_full_window_integral":m1int,
        "m0_full_window_LL":ll0,
        "m1_full_window_LL":ll1,
        "m1_minus_m0_LL":ll1-ll0,
        "independent_original_source_worlds_verified":False,
        "source_event_and_book_completeness_verified":False,
        "real_market_fdr_known":False,
        "physical_owner_identity_known":False,
        "real_trades_or_order_placement_enabled":False,
        "raw_source_rows_or_private_oracle_IDs_exported":False,
    }
