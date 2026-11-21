#!/usr/bin/env python3
"""Synthetic-only precommitted real-source occupancy audit regression tests."""
from datetime import datetime,timezone
from hashlib import sha256
import io
from pathlib import Path
import sys
import unittest
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from binance_public_trade_archive import analyze_verified_zip
from real_spot_occupancy_review import PRECOMMIT, load_json, validate_precommit, analyze

DAY="2026-11-17"
START=int(datetime(2026,11,17,tzinfo=timezone.utc).timestamp()*1_000_000)


def fake(symbol,first_id):
    text=["id,price,qty,quoteQty,time,isBuyerMaker,isBestMatch"]
    index=0
    for i,qty in enumerate([1,2,3,4,5,10]):
        for j in range(qty):
            stamp=START+(i*31+1)*1_000_000+(j//2)
            maker="True" if j%2==0 else "False"
            text.append(f"{first_id+index},100.0,1.25,125.0,{stamp},{maker},True")
            index+=1
    name=f"{symbol}-trades-{DAY}.zip"
    with io.BytesIO() as out:
        with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(name[:-4]+".csv","\n".join(text)+"\n")
        payload=out.getvalue()
    chk=f"{sha256(payload).hexdigest()}  {name}\n"
    return analyze_verified_zip(payload,chk,symbol=symbol,day=DAY,
                                clock_origin_study=True,
                                cluster_preserving_null_study=True)


def fake_pair():
    return [fake("LTCUSDT",100),fake("BCHUSDT",300)]


class RealSpotOccupancyReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=load_json(PRECOMMIT,max_bytes=12000)

    def test_protocol_frozen_prior_to_new_source_download(self):
        validate_precommit(self.cfg)
        pairs=self.cfg["new_source_pairs_frozen_before_any_download"]
        self.assertEqual([(x["symbol"],x["day"]) for x in pairs],
                         [("LTCUSDT",DAY),("BCHUSDT",DAY)])
        self.assertEqual(self.cfg["occupancy_mutually_exclusive_classes"],
                         ["1","2","3-4","5-9","10+"])
        self.assertEqual(self.cfg["primary_occupancy_filter_min_prints_per_bin"],5)
        self.assertEqual(self.cfg["primary_origin_seconds"],0)
        self.assertTrue(self.cfg["not_prospective_forward_time_holdout"])
        self.assertTrue(self.cfg["not_a_real_market_robot_FDR_or_physical_owner_detector"])

    def test_synthetic_real_archive_shape_and_occupancy_reconcile(self):
        result=analyze(self.cfg,fake_pair())
        self.assertEqual(result["distinct_instruments"],2)
        self.assertEqual(result["distinct_market_utc_days"],1)
        self.assertEqual(result["source_public_trades_total"],50)
        self.assertEqual(result["occupancy_primary_min_trades_per_30s_bin"],5)
        self.assertFalse(result["statistically_calibrated_p_value_or_false_discovery_rate"])
        self.assertFalse(result["physical_market_actor_count_known"])
        self.assertFalse(result["has_full_exchange_l2_book"])
        self.assertFalse(result["commercial_use_permitted_without_provider_license"])
        self.assertFalse(result["original_public_tape_or_event_vectors_exported"])
        for case in result["cases"]:
            self.assertEqual(case["public_trade_count"],25)
            self.assertEqual([p["origin_seconds"] for p in case["phases"]],[0,10,20])
            phase=case["phases"][0]
            self.assertEqual(phase["complete_nonempty_bins"],6)
            self.assertEqual(phase["qualifying_bins_with_5_or_more_prints"],2)
            self.assertEqual([s["eligible_bins"] for s in phase["strata"]],
                             [1,1,2,1,1])
            self.assertEqual(phase["strata"][0]["observed_one_sided"],1)
            self.assertEqual(phase["strata"][0]["null_min"],1)
            self.assertEqual(phase["strata"][0]["null_max"],1)

    def test_wrong_license_day_source_identity_or_bogus_truth_rejected(self):
        for key,value in (
            ("symbol","BTCUSDT"),("utc_date","2026-11-20"),
            ("dataset_license","commercial use"),
            ("source_zip_sha256","0"),
            ("provider_published_checksum_matched",False),
            ("l2_orderbook_present",True),
            ("all_exchange_trades_independently_verified",True),
            ("market_specific_false_alarm_rate_estimated",True),
            ("real_world_owner_count_known",True),
            ("raw_trades_or_ids_exported",True),
            ("public_trade_count",999),
            ("aggressive_buy_prints",500),
            ("first_public_timestamp_us",START-1),
            ("first_trade_id",0.1)
        ):
            reports=fake_pair()
            reports[0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                analyze(self.cfg,reports)

    def test_corrupted_occupancy_denominators_and_null_variants_rejected(self):
        for scope,key,value in (
            ("null","bin_occupancy_classes",["1","2"]),
            ("null","same_timestamp_side_vector_clusters_preserved",False),
            ("null","primary_conditioned_bin_occupancy_minimum",10),
            ("null","market_false_discovery_rate_calibrated",True),
            ("phase","qualifying_bins_with_at_least_five_prints",1),
            ("phase","null_ge5_one_sided_max",999),
            ("phase","observed_ge5_one_sided_above_all_eight_nulls",True),
            ("stratum","eligible_complete_bins",777),
            ("stratum","observed_one_sided_bins",0),
            ("stratum","null_one_sided_min",0)
        ):
            reports=fake_pair()
            strong=reports[1]["public_within_minute_cluster_direction_null_v1"]
            if scope=="null":
                strong[key]=value
            elif scope=="phase":
                strong["variants"][0][key]=value
            else:
                strong["variants"][0]["one_sided_bins_by_public_print_occupancy"][0][key]=value
            with self.subTest(scope=scope,key=key),self.assertRaises(ValueError):
                analyze(self.cfg,reports)

    def test_no_missing_or_posthoc_replacement_sources(self):
        source=fake_pair()
        for reports in ([],source[:1],source[::-1],[None,None],(source[0],source[1])):
            with self.assertRaises(ValueError):
                analyze(self.cfg,reports)

    def test_changed_protocol_fails_before_inspecting_new_data(self):
        import json
        for field,value in (
            ("predeclared_phase_origins_seconds",[20,10,0]),
            ("primary_origin_seconds",20),
            ("bin_width_seconds",60),
            ("occupancy_mutually_exclusive_classes",["1","2","10+"]),
            ("primary_occupancy_filter_min_prints_per_bin",1),
            ("fixed_eight_null_seeds",[1]*8),
            ("new_source_pairs_frozen_before_any_download",[]),
            ("not_for_live_or_commercial_trading",False),
            ("primary_metric","any pretty signal")
        ):
            cfg=json.loads(json.dumps(self.cfg))
            cfg[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                validate_precommit(cfg)


if __name__=="__main__":
    unittest.main(verbosity=2)
