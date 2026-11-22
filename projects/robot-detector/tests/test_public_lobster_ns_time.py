"""Predeclared source-free Decimal/nanosecond precision negative controls."""
from decimal import Decimal as D
import unittest
from tools.public_intensity_rescaling import Abstain
from tools.public_lobster_ns_time import (
    UNIT, NS_PER_SECOND, SourceNanosecondTimeTape,
    exact_decimal_to_ns, lossless_decimal_time_tape as tape,
)
from tools.public_m1_dynamic_l2 import (
    M1DynamicRateModel, fit_m1_dynamic_train_only, predict_m1_dynamic_exposure,
)


class LosslessNanosecondTimeGateTests(unittest.TestCase):
    def test_one_nanosecond_exact_encoding(self):
        self.assertEqual(exact_decimal_to_ns(D("34200.000000001")),34200000000001)
        self.assertEqual(exact_decimal_to_ns(D("34200.0000000010")),34200000000001)
        self.assertEqual(exact_decimal_to_ns(D("57600")),57600*NS_PER_SECOND)

    def test_submillisecond_distinct_events_not_merged(self):
        x=tape((D("34200.0001"),D("34200.0009")))
        self.assertEqual(x.unit,UNIT)
        self.assertEqual(x.ticks,(34200000100000,34200000900000))
        self.assertEqual(x.safe_aggregate["distinct_source_groups_merged_if_floored_to_ms"],1)
        self.assertEqual(x.safe_aggregate["rows_with_submillisecond_component"],2)

    def test_exact_duplicate_timestamps_remain_ties(self):
        x=tape((D("34200.000000001"),D("34200.000000001"),D("34200.000000002")))
        self.assertEqual(x.safe_aggregate["exact_source_timestamp_ties"],1)
        self.assertEqual(x.safe_aggregate["distinct_exact_source_timestamps"],2)
        self.assertEqual(x.ticks[:2],(34200000000001,)*2)

    def test_subnanosecond_never_rounded(self):
        for s in ("34200.0000000001","34200.00000000101","57600.0000000001"):
            with self.subTest(s=s),self.assertRaises(Abstain):
                exact_decimal_to_ns(D(s))

    def test_invalid_types_and_nonfinite_fail_closed(self):
        for v in (34200.0,True,"34200",None,D("NaN"),D("Infinity"),D("-Infinity")):
            with self.subTest(v=repr(v)),self.assertRaises(Abstain):
                exact_decimal_to_ns(v)

    def test_unsafe_or_outside_session_rejected(self):
        for v in (D("-1"),D("0"),D("34199.999999999"),D("57600.000000001"),
                  D("1E+9999"),D("34200."+"0"*70+"1")):
            with self.subTest(v=str(v)[:40]),self.assertRaises(Abstain):
                exact_decimal_to_ns(v)

    def test_exact_order_and_distinctions_preserved(self):
        seq=(D("34200.001"),D("34200.001000001"),D("34200.001000001"),
             D("34200.001000002"),D("34200.002"))
        x=tape(seq)
        self.assertEqual(x.ticks,tuple(exact_decimal_to_ns(t) for t in seq))
        self.assertEqual(len(set(x.ticks)),len(set(seq)))
        self.assertTrue(all(D(n)/NS_PER_SECOND==t for n,t in zip(x.ticks,seq)))

    def test_unsorted_empty_and_oversized_tape_abstains(self):
        for seq in ((),[],[D("34200.0001"),D("34200.000099999")],
                    [D("34200")]*100001,None):
            with self.subTest(length=-1 if seq is None else len(seq)),self.assertRaises(Abstain):
                tape(seq)

    def test_typed_ns_not_accepted_by_ms_m1v2(self):
        x=tape((D("34200"),D("34200.000000001")))
        m=M1DynamicRateModel(.02,1.,2.,("train",),1,1,1000,1000)
        with self.assertRaises(Abstain):
            predict_m1_dynamic_exposure(m,x)
        with self.assertRaises(Abstain):
            fit_m1_dynamic_train_only([x])
        self.assertIs(type(x),SourceNanosecondTimeTape)

    def test_safe_aggregate_no_raw_timestamps_or_ids(self):
        x=tape((D("34200.001"),D("34200.001000001")))
        self.assertTrue(x.safe_aggregate["nanosecond_encoding_exact"])
        self.assertFalse(x.safe_aggregate["vendor_source_rows_exported"])
        for key in ("ticks","timestamp_ms","order_id","agent_id","book_rows","event_times"):
            self.assertNotIn(key,x.safe_aggregate)
        self.assertFalse(x.safe_aggregate["physical_owner_identity_known"])


if __name__=="__main__":
    unittest.main()
