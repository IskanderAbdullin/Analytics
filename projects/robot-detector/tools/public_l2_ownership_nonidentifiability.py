#!/usr/bin/env python3
"""Synthetic constructive limit: identical public L2, different oracle owners.

A LOBSTER-style public order reference is not an account identifier.
Two distinct assignments of hidden owner IDs to exactly the SAME public
messages and 10-level post-event orderbook states can be observationally
equivalent. This does not prevent detecting observable execution rhythms.
No brokerage data, real hidden owners, raw vendor data or trading.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any

if __package__:
    from .lobster_public_sample_format_audit import _validate_book
else:
    from lobster_public_sample_format_audit import _validate_book

PUBLIC_EVENT_KEYS=frozenset((
    "exchange_local_microseconds","event_type","public_order_reference",
    "size_shares","limit_price_x10000","resting_limit_side",
    "post_event_book_10levels"
))
MAX_PUBLIC_EVENTS=10000


@dataclass(frozen=True)
class OracleWorld:
    """Private truth exists only for synthetic evaluation, not the detector."""
    public_events: tuple[dict[str,Any], ...]
    private_owner_of_order_reference: tuple[tuple[int,str],...]


def validate_public_events(events: tuple[dict[str,Any],...]) -> tuple:
    if type(events) is not tuple or not 0<len(events)<=MAX_PUBLIC_EVENTS:
        raise ValueError("Expected bounded tuple of synthetic public observations")
    previous=None
    order_refs=set()
    for item in events:
        if type(item) is not dict or set(item)!=PUBLIC_EVENT_KEYS:
            raise ValueError("Public projection may not include extra private owner fields")
        for key in PUBLIC_EVENT_KEYS-{"post_event_book_10levels"}:
            if type(item[key]) is not int:
                raise ValueError("Strict integer public event field required: "+key)
        ts=item["exchange_local_microseconds"]
        if not 34200000000<=ts<=57600000000 or (previous is not None and ts<previous):
            raise ValueError("Non-monotone or out-of-session public event time")
        previous=ts
        if (item["event_type"] not in (1,2,3,4,5,6)
                or item["public_order_reference"]<1
                or item["size_shares"]<1 or item["limit_price_x10000"]<1
                or item["resting_limit_side"] not in (-1,1)):
            raise ValueError("Malformed LOBSTER-style event")
        book=item["post_event_book_10levels"]
        if type(book) is not tuple or len(book)!=40:
            raise ValueError("Expected full 10-level post-event quote tuple")
        if any(type(n) is not int for n in book):
            raise ValueError("Book contains noninteger values")
        _validate_book([str(n) for n in book])
        order_refs.add(item["public_order_reference"])
    return tuple(sorted(order_refs))


def make_public_demo_case() -> tuple[dict[str,Any],...]:
    """Original tiny synthetic event tape; NOT sampled from vendor records."""
    def book(ask, bid):
        result=[]
        for i in range(10):
            result.extend((ask+100*i,100+10*i,
                           bid-100*i,100+5*i))
        return tuple(result)
    times=(34200001000,34200002000,34200002000,34200003000,
           34200004000,34200005000)
    kinds=(1,1,4,1,4,3)
    refs=(10,11,10,12,11,12)
    sides=(-1,1,-1,-1,1,-1)
    books=(book(1186000,1185000),
           book(1186000,1185000),
           book(1186100,1185000),
           book(1186100,1185000),
           book(1186100,1184900),
           book(1186100,1184900))
    events=tuple({
        "exchange_local_microseconds":times[i],
        "event_type":kinds[i],
        "public_order_reference":refs[i],
        "size_shares":10 if kinds[i] in (4,3) else 100,
        "limit_price_x10000":1186000 if sides[i]==-1 else 1185000,
        "resting_limit_side":sides[i],
        "post_event_book_10levels":books[i],
    } for i in range(len(kinds)))
    validate_public_events(events)
    return events


def make_oracle_world(events: tuple[dict[str,Any],...],
                      owners_by_order_ref: dict[int,str]) -> OracleWorld:
    visible_refs=validate_public_events(events)
    if (type(owners_by_order_ref) is not dict
            or set(owners_by_order_ref)!=set(visible_refs)):
        raise ValueError("Private oracle must assign each observed ORDER reference")
    for ref,owner in owners_by_order_ref.items():
        if type(ref) is not int or type(owner) is not str or not owner:
            raise ValueError("Invalid private oracle ID mapping")
    # Freeze a copy so altering the caller's map cannot change this world.
    truth=tuple(sorted(owners_by_order_ref.items()))
    return OracleWorld(tuple(dict(item) for item in events),truth)


def public_projection(world: OracleWorld) -> tuple[dict[str,Any],...]:
    if type(world) is not OracleWorld:
        raise ValueError("Private oracle world required")
    # STRICT public-side whitelist. No private ownership map is accessed.
    observed=tuple({k:item[k] for k in sorted(PUBLIC_EVENT_KEYS)}
                   for item in world.public_events)
    validate_public_events(observed)
    return observed


def source_visible_fingerprint(public_events: tuple[dict[str,Any],...]) -> str:
    validate_public_events(public_events)
    payload=json.dumps(public_events,sort_keys=True,separators=(",",":"),
                       ensure_ascii=True).encode("utf-8")
    return sha256(payload).hexdigest()


def public_only_descriptor(public_events: tuple[dict[str,Any],...]) -> dict:
    """Simple public-only observer; never consumes private oracle truth."""
    refs=validate_public_events(public_events)
    visible_trades=sum(e["event_type"]==4 for e in public_events)
    return {
        "public_projection_sha256":source_visible_fingerprint(public_events),
        "public_messages":len(public_events),
        "distinct_exchange_order_references":len(refs),
        "visible_execution_events":visible_trades,
        "physical_owner_count_identifiable":False,
        "real_robot_detection_FDR_calibrated":False,
    }


def private_oracle_owner_count(world: OracleWorld) -> int:
    """Only evaluation code can use this; never pass to a detector."""
    if type(world) is not OracleWorld:
        raise ValueError("Oracle owner truth requires an oracle world")
    return len({owner for _,owner in world.private_owner_of_order_reference})


def demonstrate_owner_nonidentifiability() -> dict:
    public=make_public_demo_case()
    one=make_oracle_world(public,{10:"synthetic_owner_A",
                                 11:"synthetic_owner_A",
                                 12:"synthetic_owner_A"})
    many=make_oracle_world(public,{10:"synthetic_owner_A",
                                  11:"synthetic_owner_B",
                                  12:"synthetic_owner_C"})
    left,right=public_projection(one),public_projection(many)
    if left!=right:
        raise AssertionError("Constructive public equivalence must be exact")
    a=public_only_descriptor(left)
    b=public_only_descriptor(right)
    if a!=b:
        raise AssertionError("Public-only estimator leaked latent truth")
    truth_a=private_oracle_owner_count(one)
    truth_b=private_oracle_owner_count(many)
    if truth_a==truth_b:
        raise AssertionError("Expected observationally equivalent different owners")
    return {
        "schema_version":"synthetic-public-l2-owner-nonidentifiability-v1",
        "synthetic_public_messages":len(left),
        "synthetic_unique_order_references":a["distinct_exchange_order_references"],
        "identical_full_10level_post_event_public_tapes":True,
        "identical_public_sha256":a["public_projection_sha256"],
        "identical_public_only_estimator_result":True,
        "synthetic_private_owner_count_world_a":truth_a,
        "synthetic_private_owner_count_world_b":truth_b,
        "true_owner_count_recoverable_in_both_worlds_from_public_view":False,
        "different_owner_assignments_may_produce_same_public_orders":True,
        "public_order_reference_is_not_an_owner_identifier":True,
        "not_a_claim_that_observable_algorithmic_patterns_cannot_be_detected":True,
        "synthetic_private_owner_labels_exported":False,
        "real_market_actor_identification_or_FDR_calibrated":False,
        "real_vendor_event_rows_used":False,
        "actual_live_trading_enabled":False,
        "caveats":[
            "This is a synthetic constructive identifiability counterexample, not a real exchange validation.",
            "Worlds differ only by private ownership assignment while public order actions are fixed.",
            "Distinct order references do not imply distinct physical people or bots.",
            "Public-only algorithmic execution pattern recognition remains a distinct, investigable goal.",
        ]
    }


def main() -> None:
    print("PUBLIC_OWNER_COUNT_NONIDENTIFIABLE",
          json.dumps(demonstrate_owner_nonidentifiability(),sort_keys=True))


if __name__=="__main__":
    main()
