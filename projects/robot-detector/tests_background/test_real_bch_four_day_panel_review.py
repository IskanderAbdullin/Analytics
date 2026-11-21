#!/usr/bin/env python3
"""No-network adverse source report and frozen four-day BCH panel regression."""
from datetime import datetime,timezone
from hashlib import sha256
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from binance_public_trade_archive import analyze_verified_zip
from real_spot_transfer_review import load_json
import real_bch_four_day_panel_review as panel


def source(day, first_id=100):
    origin=int(datetime.fromisoformat(day+"T00:00:00+00:00").timestamp()*1_000_000)
    name=f"BCHUSDT-trades-{day}.zip"
    lines=["id,price,qty,quoteQty,time,isBuyerMaker,isBestMatch"]
    for i in range(20):
        t=origin+(i//3*31+2)*1_000_000+(i%3)
        maker="True" if i%3==0 else "False"
        lines.append(f"{first_id+i},100.0,1.0,100.0,{t},{maker},True")
    with io.BytesIO() as buf:
        with zipfile.ZipFile(buf,"w",compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(name[:-4]+".csv","\n".join(lines)+"\n")
        raw=buf.getvalue()
    return analyze_verified_zip(
        raw,f"{sha256(raw).hexdigest()}  {name}\n",
        symbol="BCHUSDT",day=day,clock_origin_study=True,
        cluster_preserving_null_study=True
    )


class FourDayBchPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=load_json(panel.PROTOCOL)
        cls.earlier=load_json(panel.EARLIER)

    def test_exact_precommit_and_seen_source_provenance(self):
        panel.validate_protocol(self.cfg)
        self.assertEqual([x["day"] for x in self.cfg["new_precommitted_archives"]],
                         ["2026-11-18","2026-11-19"])
        self.assertEqual(self.cfg["frozen_minimum_fills_per_bin"],5)
        self.assertEqual(self.cfg["frozen_primary_origin_seconds"],0)
        self.assertEqual(self.cfg["frozen_null_rng_seeds"],
                         [32001,32003,32009,32027,32029,32051,32057,32063])
        original=panel._read_seen_nov17_fixture(self.earlier)
        self.assertEqual(original["public_trade_count"],42678)
        self.assertFalse(original["phase0_conditioned_primary_met"])
        self.assertEqual(original["observed_first_public_trade_id"],296851413)
        self.assertEqual(original["observed_last_public_trade_id"],296894090)

    def test_frozen_source_checks_count_and_bin_conservation(self):
        for day in ("2026-11-18","2026-11-19","2026-11-20"):
            raw=source(day)
            out=panel._read_source(raw,day,
                 expected_count=raw["public_trade_count"],
                 expected_sha=raw["source_zip_sha256"])
            self.assertEqual(out["public_trade_count"],20)
            self.assertEqual([p["phase_seconds"] for p in out["phases"]],[0,10,20])
            self.assertEqual(out["observed_last_public_trade_id"],119)
            self.assertFalse(out["phase0_conditioned_primary_met"])
            for phase in out["phases"]:
                self.assertGreaterEqual(phase["one_fill_bins"],0)
                self.assertGreaterEqual(phase["five_plus_eligible"],0)

    def test_fake_license_missing_source_or_fabricated_owner_claim_rejected(self):
        for key,value in (
            ("symbol","LTCUSDT"),("utc_date","2026-11-20"),
            ("provider_published_checksum_matched",False),
            ("dataset_license","unlicensed"),
            ("source_zip_sha256","notSHA"),
            ("l2_orderbook_present",True),
            ("all_exchange_trades_independently_verified",True),
            ("market_specific_false_alarm_rate_estimated",True),
            ("commercial_use_allowed_without_license",True),
            ("public_trade_count",999),
            ("first_public_timestamp_us",1)
        ):
            bad=source("2026-11-18")
            bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                panel._read_source(bad,"2026-11-18")

    def test_broken_occupancy_and_study_nulls_rejected(self):
        for scope,key,value in (
            ("model","same_timestamp_side_vector_clusters_preserved",False),
            ("model","primary_conditioned_bin_occupancy_minimum",1),
            ("model","clock_phases_seconds",[20,10,0]),
            ("model","physical_robot_identification_validated",True),
            ("phase","null_ge5_one_sided_max",999),
            ("phase","qualifying_bins_with_at_least_five_prints",1),
            ("phase","observed_ge5_one_sided_above_all_eight_nulls",True),
            ("stratum","eligible_complete_bins",999),
            ("stratum","null_one_sided_min",-1),
        ):
            bad=source("2026-11-18")
            model=bad["public_within_minute_cluster_direction_null_v1"]
            if scope=="model":model[key]=value
            elif scope=="phase":model["variants"][0][key]=value
            else:model["variants"][0]["one_sided_bins_by_public_print_occupancy"][0][key]=value
            with self.subTest(scope=scope,key=key),self.assertRaises(ValueError):
                panel._read_source(bad,"2026-11-18")

    def test_fourday_panel_preserves_seen_v_unseen_role_and_no_fdr_claim(self):
        reports=[source("2026-11-18",100),
                 source("2026-11-19",120),
                 source("2026-11-20",140)]
        original=panel._read_source
        def fake_read(report,day,**ignored):
            # Synthetic Nov20 is deliberately not the original real 73279
            # archive; only bypass its hardcoded REAL source SHA/count
            # for a pure orchestration test. Production enforces both.
            return original(report,day)
        with patch.object(panel,"_read_source",side_effect=fake_read):
            r=panel.analyze(self.cfg,*reports,self.earlier)
        self.assertEqual([x["utc_day"] for x in r["all_cases"]],
                         ["2026-11-17","2026-11-18","2026-11-19","2026-11-20"])
        self.assertEqual(r["sum_original_public_trade_prints"],42678+60)
        self.assertEqual(r["independent_utc_market_dates"],4)
        self.assertEqual(r["uninspected_source_phase0_5plus_cases_total"],2)
        self.assertEqual(r["previously_inspected_dates"],["2026-11-17","2026-11-20"])
        self.assertFalse(r["independent_real_market_actor_labels_available"])
        self.assertFalse(r["calibrated_real_actor_p_values_or_FDR"])
        self.assertFalse(r["commercial_or_live_trading_authorized"])
        self.assertFalse(r["full_depth_exchange_l2_available"])
        self.assertFalse(r["provider_exchange_completeness_independently_verified"])
        self.assertFalse(r["full_bch_observed_ids_contiguous_across_four_utc_days"])

    def test_source20_original_archive_sha_count_must_match_without_mock(self):
        seen=source("2026-11-20")
        with self.assertRaises(ValueError):
            panel._read_source(
                seen,"2026-11-20",expected_count=73279,
                expected_sha=panel.EXPECTED_SEEN_SHA)

    def test_changed_frozen_bch_source_or_posthoc_metric_fails(self):
        import json
        for key,value in (
            ("frozen_minimum_fills_per_bin",1),
            ("frozen_bin_width_seconds",60),
            ("frozen_primary_origin_seconds",20),
            ("frozen_secondary_origins_seconds",[0,10]),
            ("frozen_occupancy_groups",["1","2"]),
            ("frozen_null_rng_seeds",[1]*8),
            ("new_precommitted_archives",[]),
            ("four_day_panel_expected_dates",[]),
            ("not_forward_time_or_labelled_bot_holdout",False),
        ):
            edited=json.loads(json.dumps(self.cfg))
            edited[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                panel.validate_protocol(edited)


if __name__=="__main__":
    unittest.main(verbosity=2)
