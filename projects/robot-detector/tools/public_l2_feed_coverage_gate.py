#!/usr/bin/env python3
"""Research read-only abstention gate for incomplete or stale public L2.

A monotonically increasing order reference is NOT a source event sequence.
An archive with perfect row alignment is NOT automatically exchange-complete.
Only a named synthetic oracle can attest the full expected sequence range
in this module. Without that evidence, output is UNKNOWN, not PASS.
"""
from __future__ import annotations

from dataclasses import dataclass


MAX_FRAMES=200000
SESSION_START_US=34_200_000_000
SESSION_END_US=57_600_000_000
MAX_QUOTE_AGE_US=30_000_000
REASONS=frozenset((
    "MISSING_EVENT_SEQUENCE","PARTIAL_EVENT_SEQUENCE","DUPLICATE_EVENT_SEQUENCE",
    "REVERSED_EVENT_SEQUENCE","GAP_IN_OBSERVED_EVENT_SEQUENCE",
    "EVENT_TIMESTAMP_REGRESSION","BOOK_ROW_MISSING",
    "EVENT_AND_BOOK_TIMESTAMP_DIFFER","TOP_OF_BOOK_UNAVAILABLE",
    "LOCKED_OR_CROSSED_BOOK","QUOTE_HOLD_EXCEEDS_30_SECONDS",
    "TRUSTED_SOURCE_BOUNDARY_MISMATCH"
))


@dataclass(frozen=True)
class PublicFrame:
    event_time_us: int
    book_time_us: int|None
    source_event_sequence: int|None
    best_ask_price_x10000: int|None
    best_bid_price_x10000: int|None


def analyze_coverage(
    frames: tuple[PublicFrame,...],
    *,
    trusted_synthetic_expected_sequence_range: tuple[int,int]|None=None
) -> dict:
    """Return only coverage summary/abstention reason, never source rows.

    trusted_synthetic_expected_sequence_range is a known simulated
    oracle boundary. It MUST NOT be populated from a vendor order ref,
    observed min/max, or a source WITHOUT external true sequence proof.
    """
    if type(frames) is not tuple or not 0<len(frames)<=MAX_FRAMES:
        raise ValueError("Expected bounded collection of public L2 frames")
    expected=trusted_synthetic_expected_sequence_range
    if expected is not None and (
        type(expected) is not tuple or len(expected)!=2
        or any(type(x) is not int or x<0 for x in expected)
        or expected[0]>expected[1]
        or expected[1]-expected[0]>MAX_FRAMES
    ):
        raise ValueError("Trusted synthetic sequence range must be bounded integers")
    reasons=set()
    prev_time=None
    prev_seq=None
    present_count=0
    seen_sequences=set()
    internal_gaps=0
    valid_book_count=0
    equal_time_count=0
    long_gap_count=0
    missing_sequence_count=0
    for frame in frames:
        if type(frame) is not PublicFrame:
            raise ValueError("Expected typed public observation without extra fields")
        ts=frame.event_time_us
        if (type(ts) is not int
                or not SESSION_START_US<=ts<=SESSION_END_US):
            raise ValueError("Invalid exchange-local microsecond clock")
        seq=frame.source_event_sequence
        if seq is None:
            missing_sequence_count+=1
        elif type(seq) is not int or seq<0:
            raise ValueError("Invalid source event sequence ID")
        else:
            if seq in seen_sequences:
                reasons.add("DUPLICATE_EVENT_SEQUENCE")
            if prev_seq is not None:
                if seq<prev_seq:
                    reasons.add("REVERSED_EVENT_SEQUENCE")
                elif seq>prev_seq+1:
                    reasons.add("GAP_IN_OBSERVED_EVENT_SEQUENCE")
                    internal_gaps+=seq-prev_seq-1
            seen_sequences.add(seq)
            prev_seq=seq
        if prev_time is not None:
            if ts<prev_time:
                reasons.add("EVENT_TIMESTAMP_REGRESSION")
            elif ts==prev_time:
                equal_time_count+=1
            elif ts-prev_time>MAX_QUOTE_AGE_US:
                long_gap_count+=1
                reasons.add("QUOTE_HOLD_EXCEEDS_30_SECONDS")
        prev_time=ts
        bts=frame.book_time_us
        if bts is None:
            reasons.add("BOOK_ROW_MISSING")
        else:
            if type(bts) is not int or bts<SESSION_START_US or bts>SESSION_END_US:
                raise ValueError("Invalid book event timestamp")
            if bts!=ts:
                reasons.add("EVENT_AND_BOOK_TIMESTAMP_DIFFER")
            else:
                present_count+=1
        ask,bid=frame.best_ask_price_x10000,frame.best_bid_price_x10000
        if ask is None or bid is None:
            reasons.add("TOP_OF_BOOK_UNAVAILABLE")
        else:
            if type(ask) is not int or type(bid) is not int or ask<=0 or bid<=0:
                raise ValueError("Invalid top quote")
            if ask<=bid:
                reasons.add("LOCKED_OR_CROSSED_BOOK")
            else:
                valid_book_count+=1
    if missing_sequence_count==len(frames):
        reasons.add("MISSING_EVENT_SEQUENCE")
    elif missing_sequence_count:
        reasons.add("PARTIAL_EVENT_SEQUENCE")
    if expected is not None:
        if (missing_sequence_count or len(seen_sequences)!=expected[1]-expected[0]+1
                or min(seen_sequences,default=None)!=expected[0]
                or max(seen_sequences,default=None)!=expected[1]):
            reasons.add("TRUSTED_SOURCE_BOUNDARY_MISMATCH")

    fully_attested=(expected is not None and not reasons)
    # Only a synthetic oracle expected range can produce an 'eligible'
    # result. Full exchange completeness is NEVER inferred here.
    state=(
        "SYNTHETIC_COVERAGE_ELIGIBLE_ONLY" if fully_attested else
        "ABSTAIN_SOURCE_OR_BOOK_INTEGRITY" if reasons else
        "UNKNOWN_SOURCE_COMPLETENESS"
    )
    coverage=(len(seen_sequences)/(expected[1]-expected[0]+1)
              if expected is not None else None)
    return {
        "schema_version":"public-l2-research-source-coverage-abstention-v1",
        "status":state,
        "observed_frame_count":len(frames),
        "event_book_timestamp_aligned_count":present_count,
        "two_sided_noncrossed_book_count":valid_book_count,
        "distinct_observed_sequence_ids":len(seen_sequences),
        "missing_sequence_ids_in_observed_range":internal_gaps,
        "same_exchange_time_adjacent_event_pairs":equal_time_count,
        "observed_previous_quote_holds_over_30s":long_gap_count,
        "source_expected_total_events_if_oracle_attested":(
            expected[1]-expected[0]+1 if expected else None),
        "source_sequence_coverage_fraction_if_oracle_attested":coverage,
        "reason_codes":sorted(reasons),
        "synthetic_oracle_source_boundary_used":expected is not None,
        "unattested_real_source_completeness_declared":False,
        "source_missing_events_proven_absent_from_unattested_data":False,
        "physical_robot_owner_accuracy_or_market_FDR_calibrated":False,
        "real_trading_or_order_placement_authorized":False,
        "raw_market_frames_or_order_ids_exported":False,
        "limitations":[
            "A public order reference is not a monotonic exchange EVENT sequence.",
            "Without authenticated source event numbering and expected endpoints, completeness remains unknown.",
            "Synthetic oracle sequence coverage says nothing about actual NASDAQ/Binance source completeness.",
            "Thirty seconds is a conservative research quote-hold threshold, not a universal feed outage definition.",
            "A synthetic coverage gate cannot calibrate physical market bot FDR or identify hidden owners.",
        ]
    }


def main()->None:
    frames=tuple(
        PublicFrame(SESSION_START_US+i*1000,SESSION_START_US+i*1000,
                    200+i,1186000,1185000)
        for i in range(5)
    )
    result=analyze_coverage(frames,
        trusted_synthetic_expected_sequence_range=(200,204))
    if result["status"]!="SYNTHETIC_COVERAGE_ELIGIBLE_ONLY":
        raise AssertionError("Known contiguous source-free synthetic case failed")
    import json
    print("SYNTHETIC_L2_COVERAGE_GATE",json.dumps(result,sort_keys=True))


if __name__=="__main__":
    main()
