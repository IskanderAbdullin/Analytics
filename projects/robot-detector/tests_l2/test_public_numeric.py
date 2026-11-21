#!/usr/bin/env python3
"""Reject silent numeric truncation in the public-only market data pipeline."""
import sys
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from public_numeric import exact_nonnegative_integer
from l2_probe import audit_l2_public
from l2_trade_context import PublicExecution, public_projection, audit_public_join
from lagged_l2_bin import summarize_lagged_book


def book(timestamp=100,price=100,qty=5):
    return SimpleNamespace(times_ns=[timestamp],bids=[[(price,qty)]],
                           asks=[[(102,7)]])


class IndexScalar:
    """Models integer-like scalars with an exact __index__ protocol."""
    def __index__(self):
        return 11


class StrictPublicScalarTests(unittest.TestCase):
    def test_index_protocol_accepts_integer_like_without_rounding(self):
        self.assertEqual(exact_nonnegative_integer(IndexScalar(),"test"),11)
        self.assertEqual(exact_nonnegative_integer(10**26,"big exchange ns"),10**26)
        self.assertEqual(exact_nonnegative_integer(0,"timestamp"),0)
        with self.assertRaises(ValueError):
            exact_nonnegative_integer(0,"positive qty",positive=True)

    def test_no_float_bool_decimal_string_or_negative_coercion(self):
        for bad in (100.0,100.9,True,False,Decimal("100"),"100",-1):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                exact_nonnegative_integer(bad,"exchange integer")

    def test_l2_timestamps_reject_truncation(self):
        for bad in (100.1,100.0,True,"100",Decimal("100")):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                audit_l2_public(book(timestamp=bad),max_depth=5)

    def test_l2_price_lots_depth_reject_truncation(self):
        for field in ("price","qty"):
            for bad in (100.1,100.0,True,"100",Decimal("100")):
                with self.subTest(field=field,bad=bad),self.assertRaises(ValueError):
                    kwargs={field:bad}
                    audit_l2_public(book(**kwargs),max_depth=5)
        for bad in (5.0,True,"5"):
            with self.subTest(depth=bad),self.assertRaises(ValueError):
                audit_l2_public(book(),max_depth=bad)

    def test_raw_public_execution_projection_refuses_cast(self):
        original=dict(time_ns=101,price_cents=102,quantity=3,side="SELL")
        for field in ("time_ns","price_cents","quantity"):
            for bad in (3.9,3.0,True,"3",Decimal("3")):
                with self.subTest(field=field,bad=bad),self.assertRaises(ValueError):
                    row=dict(original)
                    row[field]=bad
                    public_projection([SimpleNamespace(**row)])
        valid=public_projection([SimpleNamespace(**original)])
        self.assertEqual(valid,(PublicExecution(101,102,3,"BUY"),))

    def test_public_join_and_lagged_reject_noninteger_prints(self):
        snap=book()
        for bad in (101.9,101.0,True,Decimal("101")):
            with self.subTest(time=bad),self.assertRaises(ValueError):
                audit_public_join(snap,[PublicExecution(bad,102,4,"BUY")])
            with self.subTest(time_lag=bad),self.assertRaises(ValueError):
                summarize_lagged_book(
                    snap,[PublicExecution(bad,102,4,"BUY")],bin_seconds=10)
        for bad in (4.5,4.0,True):
            with self.subTest(qty=bad),self.assertRaises(ValueError):
                audit_public_join(snap,[PublicExecution(101,102,bad,"BUY")])
            with self.subTest(qty_lag=bad),self.assertRaises(ValueError):
                summarize_lagged_book(
                    snap,[PublicExecution(101,102,bad,"BUY")],bin_seconds=10)

    def test_input_configurations_reject_float_declaration(self):
        snap=book()
        tape=[PublicExecution(101,102,3,"BUY")]
        for age in (1.0,1.4,True,"1"):
            with self.subTest(max_age=age),self.assertRaises(ValueError):
                audit_public_join(snap,tape,max_age_ns=age)
        for bin_s in (10.0,10.5,True,"10"):
            with self.subTest(bin_s=bin_s),self.assertRaises(ValueError):
                summarize_lagged_book(snap,tape,bin_seconds=bin_s)
        for depth in (5.0,True):
            with self.subTest(depth=depth),self.assertRaises(ValueError):
                summarize_lagged_book(snap,tape,maximum_depth=depth)

    def test_valid_integer_fixture_keeps_quote_accounting_unchanged(self):
        snap=SimpleNamespace(
            times_ns=[100,100,120],
            bids=[[(100,5)],[(100,4)],[(101,5)]],
            asks=[[(102,4)],[(102,5)],[(103,6)]])
        report=audit_l2_public(snap,max_depth=5)
        self.assertEqual(report["l2_snapshot_events"],3)
        self.assertEqual(report["same_timestamp_repeated_snapshots"],1)
        trades=[PublicExecution(101,102,3,"BUY"),PublicExecution(121,101,2,"SELL")]
        joined=audit_public_join(snap,trades,max_age_ns=50)
        self.assertEqual(joined["public_fill_count"],2)
        self.assertEqual(joined["public_total_lots"],5)
        self.assertEqual(joined["categories"]["at_or_through_prior_opposite_best"],2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
