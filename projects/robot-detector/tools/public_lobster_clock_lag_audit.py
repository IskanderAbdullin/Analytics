"""Bounded source-only LOBSTER decimal-clock and post-event-lag feasibility QA.

FROZEN: docs/LOBSTER_PUBLIC_CLOCK_LAG_ELIGIBILITY_PREREG_20261122.md
Only aggregate counts; no source trades, book rows, order IDs or agent truth.
"""
import argparse
from collections import deque
import csv
from decimal import Decimal
from hashlib import sha256
from io import BytesIO, TextIOWrapper
from itertools import zip_longest
import json
from pathlib import Path
from zipfile import ZipFile

from tools.lobster_public_sample_format_audit import (
    SOURCE_URL, MAX_ROWS, MAX_ZIP_BYTES, _members, _validate_message,
    _validate_book, audit_sample_zip, download_exact_demo,
)
from tools.lobster_event_time_features import LOCALLY_PINNED_SAMPLE_SHA256

ONE_SECOND=Decimal("1")
TEN_SECONDS=Decimal("10")
MILLISECONDS=Decimal("1000")
SAMPLE_EXPECTED_ROWS=269748
SAMPLE_EXPECTED_VISIBLE_EXECUTIONS=8974


def source_free_timing_eligibility(rows):
    """Exact Decimal event clocks and one-second lag on POST-event BBO rows.

    Iterator items are (time_seconds_after_midnight, public_event_type, valid_bbo).
    The tuple is an ephemeral in-memory public fixture only, never exported.
    """
    n=0
    last=None
    last_bucket=None
    waiting=deque()
    eligible_quote=None
    visible=hidden=0
    visible_eligible=visible_no_lag=visible_stale=visible_bad_quote=0
    same_exact=off_ms=coarsening=distinct=big_gaps=0
    for value in rows:
        if type(value) not in (list,tuple) or len(value)!=3:
            raise ValueError("INVALID_PAIRED_PUBLIC_SOURCE_EVENT")
        t,typ,quote_valid=value
        if (type(t) is not Decimal or not t.is_finite() or t<0 or
            type(typ) is not int or not 1<=typ<=7 or
            type(quote_valid) is not bool):
            raise ValueError("INVALID_PUBLIC_DECIMAL_EVENT_OR_COVERAGE")
        if last is not None and t<last:
            raise ValueError("UNSORTED_PUBLIC_SOURCE_TIME")
        n+=1
        if n>MAX_ROWS:
            raise ValueError("OVERSIZED_SOURCE_EVENT_HISTORY")
        ms=t*MILLISECONDS
        bucket=int(ms)
        if ms!=ms.to_integral_value():
            off_ms+=1
        if last is None or t>last:
            distinct+=1
            if last_bucket is not None and bucket==last_bucket:
                coarsening+=1
            if last is not None and t-last>TEN_SECONDS:
                big_gaps+=1
        else:
            same_exact+=1
        # ONLY previously visited post-event rows may become eligible.
        # Source row current event is enqueued strictly AFTER its evaluation.
        while waiting and waiting[0][0]+ONE_SECOND<=t:
            eligible_quote=waiting.popleft()
        if typ==4:
            visible+=1
            if eligible_quote is None:
                visible_no_lag+=1
            elif t-eligible_quote[0]>TEN_SECONDS:
                visible_stale+=1
            elif not eligible_quote[1]:
                visible_bad_quote+=1
            else:
                visible_eligible+=1
        elif typ==5:
            hidden+=1
        waiting.append((t,quote_valid))
        last=t
        last_bucket=bucket
    if not n or sum((visible_eligible,visible_no_lag,visible_stale,visible_bad_quote))!=visible:
        raise ValueError("EMPTY_OR_UNRECONCILED_SOURCE_ELIGIBILITY")
    return {
        "status":"RETROSPECTIVE_SOURCE_ONLY_COVERAGE_NOT_REAL_ROBOT_VALIDATION",
        "paired_source_event_book_rows":n,
        "distinct_exact_exchange_event_timestamps":distinct,
        "exact_same_timestamp_adjacent_event_pairs":same_exact,
        "raw_source_rows_with_submillisecond_decimal_remainder":off_ms,
        "adjacent_distinct_exact_times_merged_by_millisecond_floor":coarsening,
        "original_event_gaps_strictly_over_10_seconds":big_gaps,
        "visible_type4_executions":visible,
        "hidden_type5_executions":hidden,
        "visible_executions_locally_eligible_lagged_bbo":visible_eligible,
        "visible_executions_abstain_no_lagged_bbo":visible_no_lag,
        "visible_executions_abstain_stale_over_10s":visible_stale,
        "visible_executions_abstain_invalid_post_event_bbo":visible_bad_quote,
        "post_event_book_used_as_same_event_prestatement":False,
        "integer_millisecond_normalization_automatically_approved":False,
        "publisher_signed_zip_checksum_available":False,
        "source_event_completeness_independently_certified":False,
        "physical_owner_identity_known":False,
        "real_market_fdr_known":False,
        "raw_vendor_rows_or_order_references_exported":False,
    }


def audit_pinned_public_demo(raw):
    """Re-read only official previously observed demo; never export vendor data."""
    if type(raw) is not bytes or not 0<len(raw)<=MAX_ZIP_BYTES:
        raise ValueError("INVALID_BOUNDED_SOURCE_ZIP")
    digest=sha256(raw).hexdigest()
    if digest!=LOCALLY_PINNED_SAMPLE_SHA256:
        raise ValueError("LOCAL_PINNED_DEMO_SOURCE_SHA_MISMATCH")
    qa=audit_sample_zip(raw)
    def original_rows():
        with ZipFile(BytesIO(raw)) as z:
            members=_members(z)
            with z.open(members["messages"]) as m, z.open(members["books"]) as b:
                messages=csv.reader(TextIOWrapper(m,encoding="utf-8-sig",newline=""))
                books=csv.reader(TextIOWrapper(b,encoding="utf-8-sig",newline=""))
                prev=None
                for msg,book in zip_longest(messages,books):
                    if msg is None or book is None:
                        raise ValueError("MISSING_PAIRED_PUBLIC_VENDOR_ROWS")
                    t,typ,shares,resting_side=_validate_message(msg,prev)
                    ask,bid,empties,crossed,top_depth=_validate_book(book)
                    prev=t
                    yield (t,typ,ask is not None and bid is not None and not crossed)
    summary=source_free_timing_eligibility(original_rows())
    if (summary["paired_source_event_book_rows"]!=qa["paired_event_and_book_rows"] or
        summary["paired_source_event_book_rows"]!=SAMPLE_EXPECTED_ROWS or
        summary["visible_type4_executions"]!=SAMPLE_EXPECTED_VISIBLE_EXECUTIONS or
        summary["hidden_type5_executions"]!=qa["hidden_order_executions"] or
        summary["exact_same_timestamp_adjacent_event_pairs"]!=qa["same_exact_timestamp_adjacent_message_pairs"]):
        raise ValueError("ORIGINAL_PUBLIC_SOURCE_QA_RECONCILIATION_FAILED")
    return {
        **summary,
        "official_demo_source_url":SOURCE_URL,
        "local_unsigned_source_zip_sha256":digest,
        "original_sample_row_count_crosschecked":True,
        "frozen_design_before_reanalysis":True,
        "new_original_ABIDES_or_exchange_source_runs":0,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    if args.output.exists():
        p.error("Refuse to overwrite previous source-only audit")
    payload=download_exact_demo()  # bounded single official source, RAM only
    result=audit_pinned_public_demo(payload)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x",encoding="utf-8") as fd:
        json.dump(result,fd,sort_keys=True,indent=2,allow_nan=False)
        fd.write("\n")
    print("LOBSTER_PUBLIC_CLOCK_LAG_AGGREGATE_ONLY",json.dumps(result,sort_keys=True))


if __name__=="__main__":
    main()
