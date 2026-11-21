#!/usr/bin/env python3
"""No-lookahead, finite-state quote-time-weighted L2 summaries.

LOBSTER orderbook snapshot for message i describes the state AFTER i.
The most recent post-event state is held right-continuously until
the NEXT event. Nothing before first or after last event is assumed.
Same-timestamp snapshots contribute ZERO wall-clock quote duration.
Only compact summaries are allowed to leave this accumulator.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation


STALE_INTERVAL_SECONDS = Decimal(30)
MAX_OBSERVATION_SECONDS = Decimal(23400)  # 09:30..16:00 local session, 6.5h


class DurationWeightedBBO:
    __slots__=(
        "_previous_time","_previous_quote","_seen",
        "_observed","_valid","_missing","_locked_crossed",
        "_sum_spread","_sum_depth","_sum_imbalance",
        "_zero_durations","_positive_durations","_large_intervals",
        "_large_time","_max_interval"
    )

    def __init__(self) -> None:
        self._previous_time=None
        self._previous_quote=None
        self._seen=0
        self._observed=Decimal(0)
        self._valid=Decimal(0)
        self._missing=Decimal(0)
        self._locked_crossed=Decimal(0)
        self._sum_spread=Decimal(0)
        self._sum_depth=Decimal(0)
        self._sum_imbalance=Decimal(0)
        self._zero_durations=0
        self._positive_durations=0
        self._large_intervals=0
        self._large_time=Decimal(0)
        self._max_interval=Decimal(0)

    @staticmethod
    def _quote(ask: int|None,bid: int|None,
               ask_size: int,bid_size: int) -> tuple:
        for name,val in (("ask",ask),("bid",bid)):
            if val is not None and (type(val) is not int or val <= 0):
                raise ValueError(f"Invalid {name} quote price")
        if (type(ask_size) is not int or type(bid_size) is not int
                or not 0<=ask_size<=10**12 or not 0<=bid_size<=10**12):
            raise ValueError("Invalid bounded top-of-book quote depth")
        if ask is not None and ask_size==0:
            raise ValueError("Occupied best ask must have strictly positive size")
        if bid is not None and bid_size==0:
            raise ValueError("Occupied best bid must have strictly positive size")
        return (ask,bid,ask_size,bid_size)

    def observe_post_event(self, stamp: Decimal, ask: int|None, bid: int|None,
                           ask_size: int, bid_size: int) -> None:
        if (type(stamp) is not Decimal or not stamp.is_finite()
                or not Decimal(34200)<=stamp<=Decimal(57600)):
            raise ValueError("Expected strict finite exchange-local session timestamp")
        current=self._quote(ask,bid,ask_size,bid_size)
        if self._previous_time is not None:
            dt=stamp-self._previous_time
            if dt<0:
                raise ValueError("Market event timestamp regression")
            if dt==0:
                self._zero_durations+=1
            else:
                self._positive_durations+=1
                self._observed+=dt
                self._max_interval=max(self._max_interval,dt)
                if dt>STALE_INTERVAL_SECONDS:
                    self._large_intervals+=1
                    self._large_time+=dt
                prev_ask,prev_bid,prev_ask_size,prev_bid_size=self._previous_quote
                if prev_ask is None or prev_bid is None:
                    self._missing+=dt
                elif prev_ask<=prev_bid:
                    self._locked_crossed+=dt
                else:
                    self._valid+=dt
                    self._sum_spread+=Decimal(prev_ask-prev_bid)*dt
                    self._sum_depth+=Decimal(prev_ask_size+prev_bid_size)*dt
                    total=prev_bid_size+prev_ask_size
                    if total==0:
                        raise AssertionError("Validated quote cannot have empty top")
                    self._sum_imbalance+=(
                        Decimal(prev_bid_size-prev_ask_size)/Decimal(total)*dt)
        self._seen+=1
        if self._seen>750000 or self._observed>MAX_OBSERVATION_SECONDS:
            raise ValueError("Session quote-time exposure outside source bounds")
        self._previous_time=stamp
        self._previous_quote=current

    def summary(self) -> dict:
        if self._seen<=0:
            raise ValueError("No market snapshots")
        if (self._valid+self._missing+self._locked_crossed!=self._observed
                or self._positive_durations+self._zero_durations!=self._seen-1
                or self._large_time>self._observed):
            raise AssertionError("Durations failed exact accounting")
        def decimal_rounded(num:Decimal,denom:Decimal) -> float|None:
            return round(float(num/denom),8) if denom else None
        return {
            "schema_version":"l2-post-event-right-continuous-clock-weight-v1",
            "input_post_event_snapshots":self._seen,
            "observation_clock_interval_seconds":str(self._observed),
            "valid_two_sided_non_crossed_quote_seconds":str(self._valid),
            "missing_quote_seconds":str(self._missing),
            "locked_or_crossed_quote_seconds":str(self._locked_crossed),
            "max_positive_quote_hold_seconds":str(self._max_interval),
            "positive_time_intervals":self._positive_durations,
            "zero_duration_same_timestamp_intervals":self._zero_durations,
            "intervals_exceeding_30_seconds":self._large_intervals,
            "total_duration_in_over_30s_intervals":str(self._large_time),
            "time_weighted_spread_x10000":decimal_rounded(self._sum_spread,self._valid),
            "time_weighted_top_depth_shares":decimal_rounded(self._sum_depth,self._valid),
            "time_weighted_top_depth_imbalance":decimal_rounded(self._sum_imbalance,self._valid),
            "previous_post_event_snapshot_used_without_future_lookahead":True,
            "no_pre_first_event_or_post_last_event_extrapolation":True,
            "same_timestamp_zero_time_weight":True,
            "event_count_weights_not_used":True,
            "raw_market_event_snapshots_or_timestamps_exported":False,
            "real_robot_identity_or_FDR_calibrated":False,
        }
