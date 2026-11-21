#!/usr/bin/env python3
"""No external network: preregistered transfer audit adversarial fixtures."""
from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
from pathlib import Path
import sys
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))

from binance_public_trade_archive import analyze_verified_zip
from real_spot_transfer_review import (
    PROTOCOL, SCHEMA, load_json, analyze, validate_precommit, strict_pairs
)

DATE="2026-11-20"
ORIGIN=int(datetime(2026,11,20,tzinfo=timezone.utc).timestamp()*1_000_000)


def make_source(symbol, *, seed=500, count=10):
    rows=["id,price,qty,quoteQty,time,isBuyerMaker,isBestMatch"]
    for i in range(count):
        ts=ORIGIN + (i//2)*31_000_000 + i%2
        is_maker="True" if i%3 == 0 else "False"
        rows.append(f"{seed+i},100.0,1.25,125.0,{ts},{is_maker},True")
    name=f"{symbol}-trades-{DATE}.zip"
    with io.BytesIO() as out:
        with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(name[:-4]+".csv","\n".join(rows)+"\n")
        raw=out.getvalue()
    chk=f"{sha256(raw).hexdigest()}  {name}\n"
    return analyze_verified_zip(
        raw,chk,symbol=symbol,day=DATE,
        clock_origin_study=True,
        direction_null_study=True,
        cluster_preserving_null_study=True
    )


def fake_reports():
    return [make_source("LTCUSDT"),make_source("BCHUSDT",seed=700)]


class TransferPrecommittedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=load_json(PROTOCOL,max_bytes=12000)

    def test_precommit_frozen_before_new_market_sources(self):
        validate_precommit(self.config)
        self.assertEqual(
            [c["symbol"] for c in self.config["frozen_new_sources_before_any_archive_download"]],
            ["LTCUSDT","BCHUSDT"])
        self.assertEqual(
            [c["day"] for c in self.config["frozen_new_sources_before_any_archive_download"]],
            [DATE,DATE])
        self.assertEqual(self.config["clock_offsets_seconds"],[0,10,20])
        self.assertEqual(self.config["fixed_rng_seeds"],
                         [32001,32003,32009,32027,32029,32051,32057,32063])
        self.assertTrue(self.config["no_hypothesis_or_threshold_fitting_on_new_sources"])
        self.assertEqual(self.config["complete_bin_width_seconds"],30)

    def test_synthetic_verified_input_two_symbols_but_only_one_date(self):
        reports=fake_reports()
        result=analyze(self.config,reports)
        self.assertEqual(result["schema_version"],SCHEMA)
        self.assertEqual(result["true_distinct_market_sessions"],2)
        self.assertEqual(result["distinct_utc_dates"],1)
        self.assertEqual(result["source_count_total"],20)
        self.assertEqual([x["symbol"] for x in result["reports"]],
                         ["LTCUSDT","BCHUSDT"])
        self.assertEqual([x["utc_day"] for x in result["reports"]],[DATE,DATE])
        self.assertEqual(len(result["reports"][0]["clock_bin_comparisons"]),3)
        self.assertFalse(result["no_l2_or_known_physical_owner_truth"] is False)
        self.assertTrue(result["no_fdr_or_statistical_significance_claimed"])
        self.assertTrue(result["not_licensed_for_live_or_commercial_trading"])
        self.assertTrue(result["no_source_raw_tapes_or_print_ids_exported"])
        for row in result["reports"]:
            self.assertEqual(len(row["source_zip_sha256"]),64)
            for phase in row["clock_bin_comparisons"]:
                self.assertEqual(len(phase["null_controls"]),2)
                self.assertEqual(phase["null_controls"][0]["controls"],8)
                self.assertEqual(phase["null_controls"][1]["controls"],8)
                self.assertTrue(phase["null_controls"][1][
                    "descriptive_control_comparison_not_p_value"])
                self.assertIsInstance(phase["null_controls"][1][
                    "observed_above_all_eight_controls"],bool)

    def test_malicious_prospective_source_and_license_changes_rejected(self):
        for field,value in (
            ("symbol","DOGEUSDT"),("utc_date","2026-11-19"),
            ("source_zip_sha256","not_a_sha"),
            ("provider_published_checksum_matched",False),
            ("dataset_license","unlimited commercial"),
            ("commercial_use_allowed_without_license",True),
            ("l2_orderbook_present",True),
            ("tuned_detector_or_threshold",True),
            ("all_exchange_trades_independently_verified",True),
            ("raw_trades_or_ids_exported",True),
            ("market_specific_false_alarm_rate_estimated",True),
            ("first_public_timestamp_us",ORIGIN-1),
            ("first_trade_id",500.0),
            ("public_trade_count",0),
            ("aggressive_buy_prints",500),
        ):
            reports=fake_reports()
            reports[0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                analyze(self.config,reports)

    def test_null_and_bin_tampering_cannot_pass_as_source_evidence(self):
        mutations=(
            ("strong_model","same_timestamp_side_vector_clusters_preserved",False),
            ("strong_model","source_event_count",3),
            ("strong_model","clock_phases_seconds",[20,10,0]),
            ("strong_model","market_false_discovery_rate_calibrated",True),
            ("strong_phase","predeclared_null_seeds",[12345]*8),
            ("strong_phase","observed_one_sided_bins",999),
            ("strong_phase","null_one_sided_bin_count_max",999),
            ("strong_phase","null_one_sided_bin_count_median",-1),
            ("observed_phase","boundary_trades_excluded",7),
            ("observed_phase","strictly_buy_one_sided_bins_or_sell_one_sided_bins",999),
        )
        for typ,key,value in mutations:
            reports=fake_reports()
            item=reports[0]
            if typ=="strong_model":
                item["public_within_minute_cluster_direction_null_v1"][key]=value
            elif typ=="strong_phase":
                item["public_within_minute_cluster_direction_null_v1"]["variants"][0][key]=value
            else:
                item["clock_origin_descriptive_v1"]["variants"][0][key]=value
            with self.subTest(typ=typ,key=key),self.assertRaises(ValueError):
                analyze(self.config,reports)

    def test_must_include_both_precommitted_reports(self):
        reports=fake_reports()
        for bad in ([],reports[:1],reports[::-1],(reports[0],reports[1]),[None,None]):
            with self.subTest(bad=str(bad)[:20]),self.assertRaises(ValueError):
                analyze(self.config,bad)

    def test_corrupted_precommit_rejected(self):
        for key,value in (
            ("clock_offsets_seconds",[20,0,10]),
            ("complete_bin_width_seconds",60),
            ("fixed_rng_seeds",[1,2,3,4,5,6,7,8]),
            ("no_data_dependent_phase_selection",False),
            ("no_hypothesis_or_threshold_fitting_on_new_sources",False),
            ("primary_endpoint","select best posthoc"),
            ("noncommercial_license","no restrictions"),
            ("frozen_new_sources_before_any_archive_download",[]),
            ("nulls",[]),
        ):
            altered=json.loads(json.dumps(self.config))
            altered[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                validate_precommit(altered)

    def test_duplicate_json_fields_fail_closed(self):
        with self.assertRaises(ValueError):
            json.loads('{"x": 1, "x": 2}',object_pairs_hook=strict_pairs)


if __name__=="__main__":
    unittest.main(verbosity=2)
