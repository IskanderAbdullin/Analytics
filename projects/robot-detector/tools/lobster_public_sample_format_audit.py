#!/usr/bin/env python3
"""Strict read-only format/QA validator for one official LOBSTER demo ZIP.

Source rights are NOT an open ML/trading license. This code performs only
noncommercial format and data-integrity demonstration and emits metadata,
NEVER raw message IDs, orders, book snapshots, private identities, ML
features or trading signals. No provider-authenticated SHA256 is available.
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import io
import json
from pathlib import Path, PurePosixPath
import re
from urllib.request import Request,urlopen
from zipfile import ZipFile,BadZipFile,is_zipfile

SOURCE_URL = "https://php.lobsterdata.com/info/sample/LOBSTER_SampleFile_AMZN_2012-06-21_10.zip"
LANDING_URL = "https://php.lobsterdata.com/info/DataSamples.php"
TERMS_URL = "https://php.lobsterdata.com/termsAndConditions.php"
MAX_ZIP_BYTES = 40_000_000
MAX_UNCOMPRESSED_BYTES = 300_000_000
MAX_ROWS = 750_000
NUM_LEVELS = 10
N_BOOK_COLUMNS = 4*NUM_LEVELS
VALID_EVENTS = set(range(1,8))
DUMMY_ASK = 9_999_999_999
DUMMY_BID = -9_999_999_999
N_MSG_COLS = 6


def _bounded_decimal(value: str, label: str) -> Decimal:
    try:
        number = Decimal(value.strip())
    except (InvalidOperation,AttributeError) as exc:
        raise ValueError(f"Invalid decimal field: {label}") from exc
    if not number.is_finite():
        raise ValueError(f"Nonfinite decimal field: {label}")
    return number


def _integer(value: str, label: str, *, allow_negative: bool = False) -> int:
    if type(value) is not str:
        raise ValueError(f"Invalid {label} type")
    value = value.strip()
    pattern = r"-?[0-9]+" if allow_negative else r"[0-9]+"
    if not re.fullmatch(pattern,value):
        raise ValueError(f"Noninteger {label}")
    result=int(value)
    if len(value)>17 or abs(result)>10**15:
        raise ValueError(f"Unbounded integer {label}")
    return result


def _safe_member(name: str) -> tuple[str,str]:
    """No extraction is performed, but reject traversal/ambiguous names."""
    if not name or "\\" in name or name.startswith("/") or "\x00" in name:
        raise ValueError("Unsafe LOBSTER ZIP member")
    p=PurePosixPath(name)
    if any(part in (".","..") for part in name.split("/")) or p.is_absolute():
        raise ValueError("LOBSTER archive path traversal")
    if len(p.parts)>3 or len(name)>250:
        raise ValueError("LOBSTER archive path not bounded")
    return name, p.name


def _members(z: ZipFile) -> dict[str,str]:
    result={}
    info=z.infolist()
    if not 2<=len(info)<=7:
        raise ValueError("Unexpected LOBSTER demo ZIP entry count")
    total=0
    for member in info:
        name, base=_safe_member(member.filename)
        if member.is_dir():
            continue
        total+=member.file_size
        if (member.flag_bits & 1 or member.file_size<=0
                or member.file_size>MAX_UNCOMPRESSED_BYTES):
            raise ValueError("Encrypted/empty/oversized vendor demo member")
        if total>MAX_UNCOMPRESSED_BYTES:
            raise ValueError("Oversized decompressed sample archive")
        if re.fullmatch(r"AMZN_2012-06-21_[0-9]+_[0-9]+_message_10.csv",base):
            key="messages"
        elif re.fullmatch(r"AMZN_2012-06-21_[0-9]+_[0-9]+_orderbook_10.csv",base):
            key="books"
        elif (base.lower().endswith(".txt") or base.lower().endswith(".md")
              or base.lower().endswith(".pdf")) and ("readme" in base.lower() or "info" in base.lower()):
            continue  # Ignored third-party prose; not returned nor parsed
        else:
            raise ValueError("Unexpected archive member format")
        if key in result:
            raise ValueError("Duplicate market CSV in LOBSTER sample")
        result[key]=name
    if set(result)!={"messages","books"}:
        raise ValueError("LOBSTER demo must have one message and one L2 book CSV")
    if (re.sub(r"_message_10\.csv$","",PurePosixPath(result["messages"]).name)
            !=re.sub(r"_orderbook_10\.csv$","",PurePosixPath(result["books"]).name)):
        raise ValueError("Message/book sources have mismatched session")
    return result


def _validate_message(record: list[str], prev_time: Decimal | None) -> tuple[Decimal,int,int,int]:
    if len(record)!=N_MSG_COLS:
        raise ValueError("Expected exactly 6 CSV columns in LOBSTER event")
    time_sec=_bounded_decimal(record[0],"exchange seconds after midnight")
    if not Decimal(34200)<=time_sec<=Decimal(57600):
        raise ValueError("Vendor sample event outside 09:30-16:00 session")
    if prev_time is not None and time_sec<prev_time:
        raise ValueError("Out-of-order original market event timestamp")
    typ=_integer(record[1],"event_type")
    if typ not in VALID_EVENTS:
        raise ValueError("Unsupported original LOBSTER message event type")
    _integer(record[2],"order reference")
    size=_integer(record[3],"shares")
    price=_integer(record[4],"x10000 price",allow_negative=True)
    side=_integer(record[5],"resting order side",allow_negative=True)
    if side not in (-1,1):
        raise ValueError("Resting order side must be -1 sell or 1 buy")
    if typ==7:
        if size!=0 or price not in (-1,0,1):
            raise ValueError("Malformed trading halt sentinel")
    elif price<=0 or size<=0:
        raise ValueError("Nonpositive shares/price in non-halt market event")
    # Crucial: side=-1 is the resting SELL limit order, not
    # the aggressor! Visible type 4 execute sell implies BUY initiator.
    return time_sec,typ,size,side


def _validate_book(record: list[str]) -> tuple[int | None,int | None,int,bool,int]:
    if len(record)!=N_BOOK_COLUMNS:
        raise ValueError("LOBSTER 10-level book must have 40 columns")
    bid_prices,ask_prices=[],[]
    bid_size=ask_size=0
    empty_pairs=0
    for i in range(NUM_LEVELS):
        values=record[4*i:4*i+4]
        ask_p=_integer(values[0],f"ask price L{i+1}",allow_negative=True)
        ask_v=_integer(values[1],f"ask size L{i+1}")
        bid_p=_integer(values[2],f"bid price L{i+1}",allow_negative=True)
        bid_v=_integer(values[3],f"bid size L{i+1}")
        if ask_v:
            if ask_p<=0 or ask_p==DUMMY_ASK:
                raise ValueError("Invalid occupied ask quote price")
            ask_prices.append(ask_p)
        else:
            empty_pairs+=1
            if ask_p not in (DUMMY_ASK,0):
                raise ValueError("Unexpected empty ask quote sentinel")
        if bid_v:
            if bid_p<=0 or bid_p==DUMMY_BID:
                raise ValueError("Invalid occupied bid quote price")
            bid_prices.append(bid_p)
        else:
            empty_pairs+=1
            if bid_p not in (DUMMY_BID,0):
                raise ValueError("Unexpected empty bid quote sentinel")
        if i==0:
            ask_size,bid_size=ask_v,bid_v
    if ask_prices!=sorted(ask_prices) or len(set(ask_prices))!=len(ask_prices):
        raise ValueError("Ask quotes not strictly increasing across occupied book levels")
    if bid_prices!=sorted(bid_prices,reverse=True) or len(set(bid_prices))!=len(bid_prices):
        raise ValueError("Bid quotes not strictly decreasing across occupied book levels")
    ask_best=ask_prices[0] if ask_prices else None
    bid_best=bid_prices[0] if bid_prices else None
    if ask_best is not None and bid_best is not None:
        if (ask_prices[0]!=_integer(record[0],"best ask",allow_negative=True)
                or bid_prices[0]!=_integer(record[2],"best bid",allow_negative=True)):
            raise ValueError("Missing best quote in occupied level 1")
    locked_crossed=(ask_best is not None and bid_best is not None
                    and ask_best<=bid_best)
    return ask_best,bid_best,empty_pairs,locked_crossed,ask_size+bid_size


def audit_sample_zip(raw: bytes) -> dict:
    if type(raw) is not bytes or not 0<len(raw)<=MAX_ZIP_BYTES:
        raise ValueError("Invalid/oversized vendor sample ZIP")
    if not is_zipfile(io.BytesIO(raw)):
        raise ValueError("Source is not a valid ZIP archive")
    digest=sha256(raw).hexdigest()
    with ZipFile(io.BytesIO(raw)) as z:
        members=_members(z)
        counts=Counter()
        event_count=0
        prior_time=None
        first_time=last_time=None
        visible_aggressive_buy=visible_aggressive_sell=0
        hidden_execution_count=0
        crossed_or_locked=0
        no_quote_states=0
        empty_level_pairs=0
        orderbook_best_changes=0
        consecutive_same_time_events=0
        prior_best=None
        first_best=None
        max_spread=None
        observed_spread_sum=0
        valid_spread_states=0
        with (z.open(members["messages"]) as m,
              z.open(members["books"]) as b):
            msgs=csv.reader(io.TextIOWrapper(m,encoding="utf-8-sig",newline=""))
            books=csv.reader(io.TextIOWrapper(b,encoding="utf-8-sig",newline=""))
            from itertools import zip_longest
            for message,book in zip_longest(msgs,books):
                if message is None or book is None:
                    raise ValueError("Event row count != paired 10-level L2 snapshot count")
                event_count+=1
                if event_count>MAX_ROWS:
                    raise ValueError("Vendor demo sample exceeds bounded event row cap")
                stamp,event_type,shares,resting_side=_validate_message(message,prior_time)
                best_ask,best_bid,empties,crossed,top_depth=_validate_book(book)
                if prior_time==stamp:
                    consecutive_same_time_events+=1
                if event_count==1:
                    first_time=stamp
                last_time=stamp
                prior_time=stamp
                counts[event_type]+=1
                if event_type==4:
                    if resting_side==-1:
                        visible_aggressive_buy+=1
                    else:
                        visible_aggressive_sell+=1
                if event_type==5:
                    hidden_execution_count+=1
                if crossed:
                    crossed_or_locked+=1
                if best_ask is None or best_bid is None:
                    no_quote_states+=1
                else:
                    spread=best_ask-best_bid
                    if max_spread is None or spread>max_spread:
                        max_spread=spread
                    observed_spread_sum+=spread
                    valid_spread_states+=1
                empty_level_pairs+=empties
                if prior_best is not None and (best_ask,best_bid)!=prior_best:
                    orderbook_best_changes+=1
                if event_count==1:
                    first_best=(best_ask,best_bid)
                prior_best=(best_ask,best_bid)
    if not event_count or visible_aggressive_buy+visible_aggressive_sell!=counts[4]:
        raise ValueError("Sample empty or visible execution side accounting failed")
    return {
        "schema_version":"lobster-public-vendor-demo-paired-l2-format-audit-v1",
        "vendor":"LOBSTER DATA TECHNOLOGY & SCIENCE LTD",
        "source_url":SOURCE_URL,"source_page":LANDING_URL,
        "sample_symbol":"AMZN","sample_date":"2012-06-21",
        "sample_market":"NASDAQ Historical TotalView-ITCH, vendor reconstructed",
        "market_event_clock":"seconds after exchange-local midnight, NOT UTC unix epoch",
        "first_event_time_seconds_after_midnight":str(first_time),
        "last_event_time_seconds_after_midnight":str(last_time),
        "levels_per_side":NUM_LEVELS,
        "max_available_levels_claimed":NUM_LEVELS,
        "full_depth_market_orderbook_claimed":False,
        "raw_vendor_zip_sha256_observed_by_this_client":digest,
        "provider_signed_sha256_available":False,
        "provider_published_SHA256_checksum_matched":False,
        "compressed_zip_bytes":len(raw),
        "paired_event_and_book_rows":event_count,
        "message_columns":N_MSG_COLS,
        "book_columns":N_BOOK_COLUMNS,
        "all_message_book_rows_aligned":True,
        "event_counts_by_type":{str(i):counts[i] for i in sorted(VALID_EVENTS)},
        "visible_exec_resting_sell_implies_buy_aggressor":visible_aggressive_buy,
        "visible_exec_resting_buy_implies_sell_aggressor":visible_aggressive_sell,
        "hidden_order_executions":hidden_execution_count,
        "same_exact_timestamp_adjacent_message_pairs":consecutive_same_time_events,
        "book_states_with_locked_or_crossed_best_quotes":crossed_or_locked,
        "book_states_missing_ask_or_bid":no_quote_states,
        "book_ask_bid_empty_level_slots":empty_level_pairs,
        "best_quote_changes_vs_previous_event":orderbook_best_changes,
        "book_states_with_valid_both_best_quotes":valid_spread_states,
        "mean_event_weighted_best_spread_price_x10000":(
            observed_spread_sum/valid_spread_states if valid_spread_states else None),
        "max_best_spread_price_x10000":max_spread,
        "actual_last_quote_not_exported":True,
        "raw_market_messages_or_book_states_exported":False,
        "event_order_reference_ids_exported":False,
        "paired_L2_source_format_qa_only":True,
        "permission_to_train_ml_robot_classifier_confirmed":False,
        "commercial_data_use_or_trading_authorized":False,
        "independent_real_market_bot_labels_available":False,
        "market_false_discovery_rate_calibrated":False,
        "source_contract_terms_not_publicly_standalone":True,
        "source_terms_url":TERMS_URL,
        "limitations":[
            "The public download is an official historical DEMONSTRATION, not a research/trading license.",
            "Sample is 2012-06-21, not present-day live market or comprehensive modern validation.",
            "A published vendor checksum or independent exchange-completeness attestation was not supplied.",
            "Exactly 10 occupied levels per side are shown, not complete market-by-order depth.",
            "Reconstructed L2 quote book is event-aligned to vendor message event, not a physical market actor label.",
            "Event type 4 direction is resting side; inferred trade aggressor is opposite.",
            "Real historical crossed or locked books are counted, not scrubbed.",
            "No training, robot identification, raw redistribution, proprietary trading or paid signals authorized.",
        ]
    }


def download_exact_demo() -> bytes:
    request=Request(SOURCE_URL,headers={"User-Agent":"RobotDetector-format-qa/1.0"})
    with urlopen(request,timeout=30) as resp:
        payload=resp.read(MAX_ZIP_BYTES+1)
    if not payload or len(payload)>MAX_ZIP_BYTES:
        raise ValueError("Absent or oversized publicly offered sample")
    return payload


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    if a.output.exists():
        p.error("Do not overwrite previous source format audit")
    payload=download_exact_demo()
    summary=audit_sample_zip(payload)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("x",encoding="utf-8") as f:
        json.dump(summary,f,indent=2,sort_keys=True,allow_nan=False)
        f.write("\n")
    print("LOBSTER_PUBLIC_AMZN_L2_FORMAT_QA",json.dumps({
        "symbol":summary["sample_symbol"],
        "date":summary["sample_date"],
        "actual_event_aligned_ten_level_books":summary["paired_event_and_book_rows"],
        "source_sha256_observed":summary["raw_vendor_zip_sha256_observed_by_this_client"],
        "provider_published_checksum_available":False,
        "ML_data_license_granted":False,
        "real_bot_accuracy_inferred":False
    },sort_keys=True))


if __name__=="__main__":
    main()
