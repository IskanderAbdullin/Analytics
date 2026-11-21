#!/usr/bin/env python3
"""Bounded no-network public trade source/integrity/license regression fixtures."""
import io
import json
from hashlib import sha256
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from binance_public_trade_archive import (
    analyze_verified_zip, frozen_source, verify_checksum, PROTOCOL
)

DAY="2026-11-18"
SYMBOL="LTCUSDT"
START_US=1794960000000000
ZIP_NAME=f"{SYMBOL}-trades-{DAY}.zip"
CSV_NAME=ZIP_NAME[:-4]+".csv"
HEADER="id,price,qty,quoteQty,time,isBuyerMaker,isBestMatch"
ROWS=[
    f"51,100.00,1.5,150.00,{START_US+1},True,True",
    f"52,100.10,2.0,200.20,{START_US+2},False,True",
    f"54,100.20,0.25,25.05,{START_US+120_000_000},True,True",
]

def archive(rows=ROWS, *, filename=CSV_NAME, header=True, extras=()):
    with io.BytesIO() as out:
        with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr(filename,
                       ("\n".join(([HEADER] if header else [])+list(rows))+"\n").encode())
            for name, content in extras:
                z.writestr(name,content)
        blob=out.getvalue()
    digest=sha256(blob).hexdigest()
    return blob, f"{digest}  {ZIP_NAME}\n"

class RealTradeArchiveTests(unittest.TestCase):
    def test_source_is_exact_public_utc_day(self):
        name,date,url,checksum=frozen_source(SYMBOL,DAY)
        self.assertEqual(name,ZIP_NAME)
        self.assertEqual(date.isoformat(),DAY)
        self.assertEqual(url,"https://data.binance.vision/data/spot/daily/trades/"
                              f"{SYMBOL}/{ZIP_NAME}")
        self.assertEqual(checksum,url+".CHECKSUM")

    def test_synthetic_bounded_exchange_prints_and_aggressor_directions(self):
        raw,check=archive()
        result=analyze_verified_zip(raw,check,symbol=SYMBOL,day=DAY)
        self.assertEqual(result["schema_version"],PROTOCOL)
        self.assertEqual(result["public_trade_count"],3)
        self.assertEqual(result["first_trade_id"],51)
        self.assertEqual(result["last_trade_id"],54)
        self.assertEqual(result["missing_ids_inside_observed_range"],1)
        self.assertEqual(result["aggressive_buy_prints"],1)
        self.assertEqual(result["aggressive_sell_prints"],2)
        self.assertEqual(result["aggressive_buy_base_quantity"],"2.0")
        self.assertEqual(result["aggressive_sell_base_quantity"],"1.75")
        self.assertEqual(result["minute_bins_with_observed_trades"],2)
        self.assertEqual(result["median_trades_per_nonempty_minute"],1.5)
        self.assertTrue(result["provider_published_checksum_matched"])
        self.assertFalse(result["l2_orderbook_present"])
        self.assertFalse(result["real_world_owner_count_known"])
        self.assertFalse(result["market_specific_false_alarm_rate_estimated"])
        self.assertFalse(result["commercial_use_allowed_without_license"])
        self.assertFalse(result["raw_trades_or_ids_exported"])
        self.assertEqual(result["source_zip_sha256"],sha256(raw).hexdigest())

    def test_header_optional_no_misinterpretation(self):
        raw,check=archive(header=False)
        self.assertEqual(analyze_verified_zip(raw,check,symbol=SYMBOL,day=DAY)[
            "public_trade_count"],3)

    def test_refuses_wrong_checksum_malicious_filename_and_tampered_zip(self):
        blob,check=archive()
        for candidate in ("a"*64+"  "+ZIP_NAME+"\n",
                          check.replace(ZIP_NAME,"OTHER.zip"),
                          "wrong\n", ""):
            with self.subTest(candidate=candidate[:30]),self.assertRaises(ValueError):
                analyze_verified_zip(blob,candidate,symbol=SYMBOL,day=DAY)
        with self.assertRaises(ValueError):
            verify_checksum(b"",check,ZIP_NAME)
        with self.assertRaises(ValueError):
            analyze_verified_zip(blob+b"zero",check,symbol=SYMBOL,day=DAY)

    def test_rejects_wrong_archive_members_and_decompression_limit(self):
        for kw in ({"filename":"../../../oops.csv"},
                   {"extras":[("more.csv","other")]}):
            blob,check=archive(**kw)
            with self.assertRaises(ValueError):
                analyze_verified_zip(blob,check,symbol=SYMBOL,day=DAY)
        blob,check=archive()
        with patch("binance_public_trade_archive.MAX_CSV_BYTES",20):
            with self.assertRaises(ValueError):
                analyze_verified_zip(blob,check,symbol=SYMBOL,day=DAY)

    def test_nonmonotone_ids_invalid_size_date_timestamp_and_flags_rejected(self):
        malformed=(
            [ROWS[0],ROWS[0]],
            [ROWS[1],ROWS[0]],
            [ROWS[0],ROWS[1].replace(",2.0,",",0.0,")],
            [ROWS[0].replace(str(START_US+1),str(START_US-1))],
            [ROWS[0].replace("True,True","UNKNOWN,True")],
            [ROWS[0].replace("100.00","-100.00")],
            [ROWS[0].replace("100.00","NaN")],
            [ROWS[0].replace(str(START_US+1),"1794960000000")],
            [ROWS[0],ROWS[1].replace(str(START_US+2),str(START_US))],
            [ROWS[0].replace("150.00","0,00")],
        )
        for rows in malformed:
            with self.subTest(rows=rows),self.assertRaises(ValueError):
                blob,check=archive(rows)
                analyze_verified_zip(blob,check,symbol=SYMBOL,day=DAY)

    def test_frozen_three_origin_public_trade_phase_and_conservation(self):
        raw,check=archive()
        result=analyze_verified_zip(raw,check,symbol=SYMBOL,day=DAY,
                                    clock_origin_study=True)
        study=result["clock_origin_descriptive_v1"]
        self.assertEqual(study["predeclared_origin_seconds"],[0,10,20])
        self.assertEqual(study["source_event_count"],3)
        self.assertTrue(study["all_source_prints_accounted_for_each_phase"])
        self.assertFalse(study["threshold_or_best_phase_selected"])
        self.assertFalse(study["real_world_bot_calibration_claimed"])
        self.assertEqual(len(study["variants"]),3)
        by_phase={x["origin_seconds"]:x for x in study["variants"]}
        self.assertEqual([by_phase[p]["fully_contained_utc_day_bins"] for p in (0,10,20)],
                         [2880,2879,2879])
        self.assertEqual([by_phase[p]["public_prints_in_full_bins"] for p in (0,10,20)],
                         [3,1,1])
        self.assertEqual([by_phase[p]["boundary_trades_excluded"] for p in (0,10,20)],
                         [0,2,2])
        self.assertEqual(by_phase[0]["equal_buy_sell_print_count_bins"],1)
        self.assertEqual(by_phase[0]["strictly_buy_one_sided_bins_or_sell_one_sided_bins"],1)
        self.assertTrue(all(not x["has_public_orderbook_l2"] for x in study["variants"]))

    def test_utc_last_partial_bin_is_discarded_for_shifted_origins(self):
        last=f"55,101.00,1.0,101.0,{START_US+86_400_000_000-1},False,True"
        raw,check=archive(ROWS+[last])
        result=analyze_verified_zip(raw,check,symbol=SYMBOL,day=DAY,
                                    clock_origin_study=True)
        phases=result["clock_origin_descriptive_v1"]["variants"]
        self.assertEqual([v["public_prints_in_full_bins"] for v in phases],[4,1,1])
        self.assertEqual([v["boundary_trades_excluded"] for v in phases],[0,3,3])
        self.assertEqual([v["eligible_nonempty_bins"] for v in phases],[3,1,1])

    def test_real_source_decoder_preserves_phase_and_null_evidence(self):
        raw,check=archive()
        report=analyze_verified_zip(
            raw,check,symbol=SYMBOL,day=DAY,
            clock_origin_study=True,direction_null_study=True)
        null=report["public_within_minute_weak_direction_null_v1"]
        phase=report["clock_origin_descriptive_v1"]
        self.assertEqual(null["source_event_count"],report["public_trade_count"])
        self.assertEqual(null["clock_phases_seconds"],[0,10,20])
        for value,original in zip(null["variants"],phase["variants"]):
            self.assertEqual(value["origin_seconds"],original["origin_seconds"])
            self.assertEqual(value["observed_one_sided_bins"],
                             original["strictly_buy_one_sided_bins_or_sell_one_sided_bins"])
            self.assertEqual(value["observed_prints_in_full_bins"],
                             original["public_prints_in_full_bins"])
            self.assertEqual(value["excluded_utc_edge_prints"],
                             original["boundary_trades_excluded"])
        self.assertFalse(null["physical_robot_identification_validated"])
        self.assertFalse(null["commercial_or_live_trading_allowed"])
        self.assertFalse(null["raw_print_timestamps_or_labels_exported"])

    def test_stronger_source_null_preserves_observed_exact_30s_counts(self):
        raw,checksum=archive()
        report=analyze_verified_zip(
            raw,checksum,symbol=SYMBOL,day=DAY,
            clock_origin_study=True,cluster_preserving_null_study=True)
        strong=report["public_within_minute_cluster_direction_null_v1"]
        original=report["clock_origin_descriptive_v1"]
        self.assertTrue(strong["same_timestamp_side_vector_clusters_preserved"])
        self.assertEqual(strong["source_event_count"],3)
        for a,b in zip(strong["variants"],original["variants"]):
            self.assertEqual(a["observed_one_sided_bins"],
                             b["strictly_buy_one_sided_bins_or_sell_one_sided_bins"])
            self.assertEqual(a["excluded_utc_edge_prints"],
                             b["boundary_trades_excluded"])
        self.assertFalse(strong["real_world_owner_count_known"]
                         if "real_world_owner_count_known" in strong else
                         strong["physical_robot_identification_validated"])

    def test_rejects_nonboolean_null_flag(self):
        raw,check=archive()
        for value in (1,0,"yes",None):
            with self.assertRaises(ValueError):
                analyze_verified_zip(raw,check,symbol=SYMBOL,day=DAY,
                                     direction_null_study=value)

    def test_rejects_nonboolean_phase_switch(self):
        raw,check=archive()
        for bad in (0,1,"yes",None):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                analyze_verified_zip(raw,check,symbol=SYMBOL,day=DAY,
                                     clock_origin_study=bad)

    def test_invalid_dates_and_paths_are_not_network_targets(self):
        for symbol,day in (
            ("../../etc",DAY),("ltcusdt",DAY),("LTCUSDT","2026-11-31"),
            ("LTCUSDT","2026-11-18/extra"),
            ("LTCUSDT","2099-01-01"),("LTCUSDT","2026-11-21"),
        ):
            with self.subTest(symbol=symbol,day=day),self.assertRaises(ValueError):
                frozen_source(symbol,day)

if __name__=="__main__":
    unittest.main(verbosity=2)
