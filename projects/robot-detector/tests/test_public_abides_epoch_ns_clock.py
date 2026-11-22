"""Pinned source-free ABIDES epoch-ns and microsecond coarsening negatives."""
from datetime import date
from dataclasses import replace
import unittest

from tools.public_intensity_rescaling import Abstain
from tools.public_abides_epoch_ns_clock import (
    NS, SOURCE_UNIT, UNIT, PINNED_REVISION, MAX_INT64_NS, ORIGIN,
    ABIDESSimulatedUTCClockTape, abides_epoch_ns_to_utc_simulated_ns as convert,
    qualify_abides_utc_ns_tape as qualify,
)
from tools.abides_export import _date_utc
from tools.public_m1_v3_ns_l2 import fit_ns_m1_v3_train_only, predict_ns_m1_v3_exposure


def origin(day="20210205"):
    d=date(int(day[:4]),int(day[4:6]),int(day[6:]))
    return (d-ORIGIN).days*86400*NS


def sample(*offsets):
    return tuple(origin()+34200*NS+x for x in offsets)


DEFAULT_TAPE=object()

def tape(times=DEFAULT_TAPE,**kw):
    return qualify(sample(1,2,2) if times is DEFAULT_TAPE else times,
                   simulation_date=kw.pop("simulation_date","20210205"),**kw)


class ABIDESUnixNsClockNegativeTests(unittest.TestCase):
    def test_one_nanosecond_epoch_to_simulated_utc_exact(self):
        self.assertEqual(convert(sample(1)[0],simulation_date="20210205"),34200*NS+1)
        self.assertEqual(convert(sample(2)[0],simulation_date="20210205"),34200*NS+2)
        self.assertEqual(tape().ticks,(34200*NS+1,34200*NS+2,34200*NS+2))

    def test_original_ns_distinct_but_legacy_csv_microseconds_identical(self):
        first,second=sample(1,2)
        self.assertNotEqual(first,second)
        self.assertEqual(_date_utc(first),_date_utc(second))
        self.assertTrue(_date_utc(first).endswith(".000000Z"))
        d=tape((first,second)).safe_aggregate
        self.assertEqual(d["distinct_original_nanosecond_timestamps"],2)
        self.assertEqual(d["distinct_ns_groups_merged_by_microsecond_floor"],1)
        self.assertFalse(d["actual_ABIDES_csv_microsecond_collisions_measured"])

    def test_same_nanosecond_split_fills_remain_tied_not_owner_identification(self):
        d=tape().safe_aggregate
        self.assertEqual((d["source_rows"],d["distinct_original_nanosecond_timestamps"],
                          d["exact_original_nanosecond_ties"]),(3,2,1))
        self.assertFalse(d["physical_owner_identity_known"])

    def test_preserves_one_microsecond_without_collision(self):
        d=tape(sample(1000,2000)).safe_aggregate
        self.assertEqual(d["rows_with_submicrosecond_component"],0)
        self.assertEqual(d["distinct_ns_groups_merged_by_microsecond_floor"],0)

    def test_other_declared_session_day_is_lossless_but_not_auto_matched(self):
        leap="20200229"
        first=origin(leap)+34200*NS+1
        self.assertEqual(convert(first,simulation_date=leap),34200*NS+1)
        with self.assertRaises(Abstain):
            convert(first,simulation_date="20210205")

    def test_wrong_unit_or_unpinned_revision_abstains(self):
        for kw in ({"source_unit":"nanoseconds_since_exchange_local_midnight"},
                   {"source_unit":"unix_epoch_microseconds"},
                   {"pinned_revision":"unverified"},
                   {"pinned_revision":None},
                   {"source_unit":None}):
            with self.subTest(kw=kw),self.assertRaises(Abstain):
                tape(**kw)

    def test_invalid_dates_and_nonexplicit_source_day_fail_closed(self):
        for x in (None,True,20210205,"20210229","20211301","2021-02-05",
                  "19691231","22630101","20210001",""):
            with self.subTest(date=repr(x)),self.assertRaises(Abstain):
                tape(simulation_date=x)

    def test_wrong_epoch_type_bool_float_string_negative_and_giant(self):
        for value in (True,False,float(sample(1)[0]),str(sample(1)[0]),
                      -1,MAX_INT64_NS+1,None):
            with self.subTest(value=repr(value)),self.assertRaises(Abstain):
                tape((value,))

    def test_wrong_date_or_outside_market_window_fail_closed(self):
        for ts in (origin()-1,origin()+34200*NS-1,
                   origin()+57600*NS+1,origin()+86400*NS):
            with self.subTest(ts=ts),self.assertRaises(Abstain):
                tape((ts,))

    def test_unsorted_and_unbounded_source_rows_abstain(self):
        for x in ([],(),[sample(2)[0],sample(1)[0]],
                  [sample(1)[0]]*100001,None):
            with self.subTest(size=-1 if x is None else len(x)),self.assertRaises(Abstain):
                tape(x)

    def test_typed_abides_clock_rejected_by_lobster_only_m1v3(self):
        t=tape()
        self.assertIs(type(t),ABIDESSimulatedUTCClockTape)
        self.assertNotEqual(t.unit,"nanoseconds_since_exchange_local_midnight")
        with self.assertRaises(Abstain):
            fit_ns_m1_v3_train_only([t])
        with self.assertRaises(Abstain):
            predict_ns_m1_v3_exposure(None,t)

    def test_aggregates_only_no_raw_market_data_or_owner_id(self):
        r=tape().safe_aggregate
        for forbidden in ("ticks","timestamp_ns","order_id","agent_id","trades",
                          "raw_source_rows","price_cents","passive_agent_id"):
            self.assertNotIn(forbidden,r)
        self.assertTrue(r["normalization_arithmetic_lossless"])
        self.assertFalse(r["source_publisher_authenticated"])
        self.assertFalse(r["raw_source_event_times_exported"])
        self.assertFalse(r["real_market_fdr_known"])


if __name__=="__main__":
    unittest.main()
