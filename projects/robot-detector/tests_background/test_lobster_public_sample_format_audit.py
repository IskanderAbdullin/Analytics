#!/usr/bin/env python3
"""Synthetic-only official LOBSTER demonstration structure/coverage QA tests."""
from hashlib import sha256
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from lobster_public_sample_format_audit import (
    audit_sample_zip,_integer,_bounded_decimal,_validate_message,
    _validate_book,download_exact_demo,DUMMY_ASK,DUMMY_BID,SOURCE_URL
)

BASE="AMZN_2012-06-21_34200000_57600000"
MESSAGE=BASE+"_message_10.csv"
BOOK=BASE+"_orderbook_10.csv"

MSG=[
    "34200.001,1,123,100,1186000,-1",
    "34200.002,4,123,10,1186000,-1",
    "34200.002,4,124,5,1185000,1",
    "34200.003,5,0,3,1186000,-1",
    "34200.004,7,0,0,-1,-1",
]

def book_row(*,bid=1185000,ask=1186000,empty=False):
    result=[]
    for i in range(10):
        if empty and i>1:
            result.extend([DUMMY_ASK,0,DUMMY_BID,0])
        else:
            result.extend([ask+(i*100),100,bid-(i*100),90])
    return ",".join(str(x) for x in result)

def archive(messages=MSG,books=None,*,name_message=MESSAGE,name_book=BOOK,additional=()):
    if books is None:
        books=[book_row() for _ in messages]
    with io.BytesIO() as buffer:
        with zipfile.ZipFile(buffer,"w",compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr(name_message,"\n".join(messages)+"\n")
            z.writestr(name_book,"\n".join(books)+"\n")
            z.writestr("README.txt","Vendor noncommercial demonstration only")
            for p,v in additional:
                z.writestr(p,v)
        return buffer.getvalue()


class LobsterPublicSampleQATests(unittest.TestCase):
    def test_exact_official_sample_source_and_no_redistribution(self):
        self.assertEqual(SOURCE_URL,
            "https://php.lobsterdata.com/info/sample/LOBSTER_SampleFile_AMZN_2012-06-21_10.zip")
        report=audit_sample_zip(archive())
        self.assertEqual(report["sample_date"],"2012-06-21")
        self.assertEqual(report["sample_symbol"],"AMZN")
        self.assertEqual(report["levels_per_side"],10)
        self.assertEqual(report["paired_event_and_book_rows"],5)
        self.assertEqual(report["event_counts_by_type"]["4"],2)
        self.assertEqual(report["event_counts_by_type"]["5"],1)
        self.assertEqual(report["event_counts_by_type"]["7"],1)
        self.assertEqual(report["visible_exec_resting_sell_implies_buy_aggressor"],1)
        self.assertEqual(report["visible_exec_resting_buy_implies_sell_aggressor"],1)
        self.assertEqual(report["same_exact_timestamp_adjacent_message_pairs"],1)
        self.assertEqual(report["book_states_with_valid_both_best_quotes"],5)
        self.assertEqual(report["book_states_with_locked_or_crossed_best_quotes"],0)
        self.assertEqual(report["max_best_spread_price_x10000"],1000)
        self.assertEqual(report["raw_vendor_zip_sha256_observed_by_this_client"],
                         sha256(archive()).hexdigest())
        for forbidden in (
            "provider_published_SHA256_checksum_matched",
            "permission_to_train_ml_robot_classifier_confirmed",
            "commercial_data_use_or_trading_authorized",
            "independent_real_market_bot_labels_available",
            "market_false_discovery_rate_calibrated",
            "full_depth_market_orderbook_claimed",
            "raw_market_messages_or_book_states_exported",
            "event_order_reference_ids_exported",
        ):
            self.assertIs(report[forbidden],False,forbidden)
        self.assertTrue(report["paired_L2_source_format_qa_only"])

    def test_empty_levels_dummy_bid_ask_and_locked_market_counted_not_silent(self):
        sample=[book_row(empty=True),book_row(bid=1187000,ask=1186000,empty=True)]
        report=audit_sample_zip(archive(messages=MSG[:2],books=sample))
        self.assertEqual(report["book_ask_bid_empty_level_slots"],32)
        self.assertEqual(report["book_states_with_locked_or_crossed_best_quotes"],1)
        self.assertEqual(report["best_quote_changes_vs_previous_event"],1)
        self.assertFalse(report["full_depth_market_orderbook_claimed"])

    def test_bad_member_paths_duplicate_or_missing_csv_rejected(self):
        for kwargs in (
            {"name_message":"../../etc/_message_10.csv"},
            {"name_book":"other_2012-06-21_34200000_57600000_orderbook_10.csv"},
            {"additional":[(MESSAGE,"duplicate")]},
            {"additional":[("random.bin","test")]},
        ):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):
                audit_sample_zip(archive(**kwargs))
        with self.assertRaises(ValueError):
            audit_sample_zip(b"not really a zip")
        with self.assertRaises(ValueError):
            audit_sample_zip(b"")

    def test_event_book_row_count_and_column_mismatch_rejected(self):
        for messages,books in (
            (MSG, [book_row()]),
            (MSG[:1], [book_row(),book_row()]),
            (["34200.0,4,1,2,-1"],[book_row()]),
            (MSG[:1], ["1,2,3"]),
        ):
            with self.subTest(rows=(len(messages),len(books))),self.assertRaises(ValueError):
                audit_sample_zip(archive(messages,books))

    def test_halt_and_resting_side_semantics_restricted(self):
        good=[["34200.0","7","0","0","-1","-1"],
              ["57600.0","7","0","0","0","-1"],
              ["40000.0","7","0","0","1","-1"]]
        for row in good:
            stamp,typ,n,side=_validate_message(row,None)
            self.assertEqual((typ,n,side),(7,0,-1))
        for row in (
            ["34200.0","7","0","100","-1","-1"],
            ["34200.0","7","0","0","999","-1"],
            ["34200.0","4","13","1","100000","0"],
            ["34200.0","4","13","0","100000","-1"],
            ["34200.0","8","13","10","100000","-1"],
            ["34200.0","4","13","10","-1","1"],
            ["34200.0","4","13","10","100000","2"],
        ):
            with self.subTest(row=row),self.assertRaises(ValueError):
                _validate_message(row,None)

    def test_time_reversal_outside_session_and_nonfinite_number_rejected(self):
        for row in (
            ["34199.999","1","4","10","100000","-1"],
            ["57600.001","1","4","10","100000","-1"],
            ["34200.0","1","4","10","100000","-1"],
            ["nan","1","4","10","100000","-1"],
        ):
            previous=__import__("decimal").Decimal("34200.001") if row[0]=="34200.0" else None
            with self.subTest(row=row),self.assertRaises(ValueError):
                _validate_message(row,previous)
        for val in ("NaN","inf","-Infinity"):
            with self.assertRaises(ValueError):
                _bounded_decimal(val,"time")

    def test_bad_book_price_or_size_ordering_rejected(self):
        valid=book_row().split(",")
        for col,value in (
            (0,"0"),(1,"-1"),(2,"0"),(3,"-1"),
            (4,valid[0]),(6,valid[2]),(0,"NaN"),
            (1,"notint")
        ):
            bad=valid.copy()
            bad[col]=value
            with self.subTest(col=col,value=value),self.assertRaises(ValueError):
                _validate_book(bad)

    def test_archive_bounded_and_download_disabled_in_unit_suite(self):
        data=archive()
        with patch("lobster_public_sample_format_audit.MAX_UNCOMPRESSED_BYTES",40):
            with self.assertRaises(ValueError):
                audit_sample_zip(data)
        with patch("lobster_public_sample_format_audit.MAX_ZIP_BYTES",30):
            with self.assertRaises(ValueError):
                audit_sample_zip(data)
        with patch("lobster_public_sample_format_audit.urlopen") as url:
            self.assertEqual(audit_sample_zip(data)["paired_event_and_book_rows"],5)
            url.assert_not_called()


if __name__=="__main__":
    unittest.main(verbosity=2)
