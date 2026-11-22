import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from real_public_trade_pair_review import ROOT,FROZEN,review

def fixtures():
    return [
        json.loads((ROOT/"fixtures"/f"binance_spot_ltcusdt_real_observed_{day.replace('-','')}.json")
                   .read_text(encoding="utf-8"))
        for day,_ in FROZEN
    ]

class PairAuditTests(unittest.TestCase):
    def test_real_observed_two_utc_days_and_contiguous_ids(self):
        out=review(fixtures())
        self.assertEqual(out["real_exchange_daily_archives"],2)
        self.assertEqual(out["observed_source_trade_count"],278403)
        self.assertEqual(out["public_aggressive_buy_prints"],131444)
        self.assertEqual(out["public_aggressive_sell_prints"],146959)
        self.assertEqual(out["utc_days"],["2026-11-18","2026-11-19"])
        self.assertTrue(out["adjacent_day_observed_public_trade_ids_consecutive"])
        self.assertAlmostEqual(out["overall_buy_print_fraction"],131444/278403)
        for key in ("original_raw_files_reverified_by_this_review",
                    "provider_exchange_completeness_independently_proven",
                    "public_spot_l2_available",
                    "real_market_bot_identification_proven",
                    "independent_blind_detector_holdout_established",
                    "commercial_or_live_trading_authorized"):
            self.assertFalse(out[key])

    def test_rejects_duplicate_missing_or_forged_cross_day_sources(self):
        tests=(
            (0,"source_zip_sha256","0"*64),
            (0,"utc_date","2026-11-17"),
            (1,"first_trade_id",608302705),
            (1,"last_trade_id",608464661),
            (1,"first_public_timestamp_us",1794960000000000),
            (0,"public_trade_count",116445),
            (1,"aggressive_buy_prints",71850),
            (1,"orderbook_l2_in_archive",True),
            (0,"market_bot_detection_accuracy_established",True),
            (0,"provider_checksum_verified",False),
            (1,"data_license","commercial granted"),
        )
        for idx,key,value in tests:
            cases=fixtures()
            cases[idx][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                review(cases)

    def test_declared_phase_bin_membership_is_conserved(self):
        for field,value in (
            ("fully_contained_utc_day_bins",2880),
            ("eligible_nonempty_bins",3000),
            ("public_prints_in_full_bins",161938),
            ("boundary_trades_excluded",0),
            ("buy_dominant_bins",-1),
            ("equal_buy_sell_print_count_bins",2),
        ):
            cases=fixtures()
            cases[1]["clock_origin_descriptive_v1"]["variants"][1][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                review(cases)
        cases=fixtures()
        cases[1]["clock_origin_descriptive_v1"]["threshold_or_best_phase_selected"]=True
        with self.assertRaises(ValueError):
            review(cases)

    def test_wrong_matrix_missing_or_bad_type_rejected(self):
        for cases in ([],[fixtures()[0]],[None,None],fixtures()[::-1]):
            with self.assertRaises(ValueError):
                review(cases)
        cases=fixtures()
        cases[0]["first_trade_id"]=True
        with self.assertRaises(ValueError):
            review(cases)

if __name__=="__main__":
    unittest.main(verbosity=2)
