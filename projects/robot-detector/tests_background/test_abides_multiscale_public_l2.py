"""Deterministic, source-free negatives for preregistered ABIDES multiscale/L2.

No ABIDES engine, broker access, data download or private owner oracle.
The tiny source-shaped synthetic book is deliberately NOT a real sample.
"""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from l2_trade_context import PublicExecution
from abides_multiscale_public_l2 import (
    SEEDS,COHORTS,PERIODS,LAGGED_BIN_WIDTHS,ANCHOR_NS,TOLERANCE_NS,
    CASE_ALLOWED_FIELDS,frozen_protocol,_clock_grid_features,
    public_multiscale_l2_summary,validate_results
)


def source_trades():
    base=34_200_000_000_000
    return tuple(PublicExecution(
        base+(30*k+10)*1_000_000_000,
        100_000+k,1+k%3,"BUY" if k%2==0 else "SELL"
    ) for k in range(7))


def source_book():
    base=34_200_000_000_000
    t=tuple(base+(30*k+5)*1_000_000_000 for k in range(8))
    return SimpleNamespace(
        times_ns=t,
        bids=tuple([(100000-k,110+k)] for k in range(len(t))),
        asks=tuple([(100200+k,90+k)] for k in range(len(t)))
    )


def synthetic_case(seed,cohort):
    p=source_trades()
    measured=public_multiscale_l2_summary(p,source_book())
    target=cohort=="twap_45s_positive"
    return {
        "seed":seed,"cohort":cohort,**measured,
        "injected_target_present_only_after_public_inference":target,
        "controlled_twap_fills_posthoc":2 if target else 0,
        "true_owner_IDs_exposed":False,
        "real_market_bot_FDR_known":False,
    }


class PublicMultiscaleSourceContract(unittest.TestCase):
    def test_frozen_config_matches_original_12_case_protocol(self):
        p=frozen_protocol()
        self.assertEqual(p["cohorts"],list(COHORTS))
        self.assertEqual(p["local_ledger_unused_seed_candidates"],[2901,2902,2903])
        self.assertEqual(p["original_matching_engine_runs"],12)
        self.assertEqual(tuple(p["public_only_multiscale_features"][
            "grid_periods_seconds"]),PERIODS)
        self.assertEqual(tuple(p["public_only_multiscale_features"][
            "l2_lagged_bin_seconds"]),LAGGED_BIN_WIDTHS)
        self.assertEqual(p["public_only_multiscale_features"][
            "fixed_anchor_exchange_local_seconds_after_midnight"],34260)
        self.assertTrue(p["no_oracle_agent_id_in_public_feature"])
        self.assertTrue(p["negative_cases_must_never_be_filtered"])
        self.assertTrue(p["not_real_market_accuracy_or_FDR"])

    def test_exact_fixed_grids_have_no_best_phase_optimization(self):
        public=tuple(PublicExecution(t,100000,1,"BUY") for t in (
            ANCHOR_NS,
            ANCHOR_NS+10_000_000_000,
            ANCHOR_NS+45_000_000_000,
            ANCHOR_NS+90_000_000_000
        ))
        r=_clock_grid_features(public)
        self.assertEqual(r["public_prints"],4)
        self.assertEqual(r["grid_hit_counts"],{
            "10":3,"20":1,"45":3,"90":2
        })
        self.assertEqual(r["grid_fractions"]["45"],0.75)
        self.assertAlmostEqual(r["descriptive_grid_lifts_not_probability_or_significance"]["45"],67.5)
        self.assertEqual(r["original_legacy_10s_rule_fraction"],0.75)
        self.assertTrue(r["original_legacy_10s_rule_alarm"])
        self.assertFalse(r["actual_private_agent_ids_accessed"])
        self.assertFalse(r["real_market_owner_accuracy_calibrated"])

    def test_predeclared_tolerance_edges_and_rejected_private_source(self):
        public=tuple(PublicExecution(t,100000,1,"BUY") for t in (
            ANCHOR_NS,ANCHOR_NS+TOLERANCE_NS,
            ANCHOR_NS+TOLERANCE_NS+1,
            ANCHOR_NS+20_000_000_000
        ))
        z=_clock_grid_features(public)
        self.assertEqual(z["grid_hit_counts"]["20"],3)
        self.assertEqual(z["grid_fractions"]["20"],0.75)
        self.assertEqual(z["grid_hit_counts"]["45"],2)
        for broken in (
            (),
            (replace(public[0],quantity=0),),
            (replace(public[0],time_ns=True),),
            (replace(public[0],price_cents=0),),
            (replace(public[0],reported_aggressor_side="OTHER"),),
            ({"agent_id":123,"timestamp":ANCHOR_NS},),
            public[::-1],
        ):
            with self.subTest(broken=str(broken)[:50]),self.assertRaises(ValueError):
                _clock_grid_features(broken)

    def test_lagged_book_30_60_uses_previous_completed_bin_and_abstention(self):
        r=public_multiscale_l2_summary(source_trades(),source_book())
        self.assertEqual(r["public_prints"],7)
        self.assertEqual(r["public_l2_snapshots"],8)
        self.assertEqual(len(r["public_tape_sha256"]),64)
        self.assertEqual(set(r["l2_binned_lagged"]),{"30","60"})
        for width in ("30","60"):
            x=r["l2_binned_lagged"][width]
            self.assertEqual(
                x["populated_trade_bins"],
                x["eligible_previous_completed_book_bins"]+
                sum(x["abstained_bins_by_reason"].values()))
            self.assertFalse(x["calibrated_p_value_or_actor_accuracy_available"])
            self.assertTrue(x["terminal_bin_may_be_partial"])
        self.assertFalse(r["source_complete_exchange_sequence_proven"])
        self.assertFalse(r["private_id_leakage_from_L2_features"])
        self.assertFalse(r["raw_quote_rows_or_l2_observations_exported"])

    def test_actual_twelve_case_completeness_validator_preserves_all_controls(self):
        rows=[synthetic_case(seed,cohort) for seed in SEEDS for cohort in COHORTS]
        self.assertTrue(all(set(x)==CASE_ALLOWED_FIELDS for x in rows))
        r=validate_results(rows)
        self.assertEqual(r["completed_independent_source_engine_runs"],12)
        self.assertEqual(set(r["cohort_aggregates"]),set(COHORTS))
        self.assertEqual(r["cohort_aggregates"]["twap_45s_positive"][
            "total_posthoc_controlled_twap_fills"],6)
        self.assertFalse(r["market_user_identity_or_real_FDR_established"])
        self.assertFalse(r["thresholds_selected_from_new_results"])
        self.assertFalse(r["source_global_seed_novelty_certified"])
        self.assertTrue(r["no_raw_source_market_trades_or_agent_ids_uploaded"])

    def test_missing_negative_or_oracle_leaks_fail_closed(self):
        original=[synthetic_case(seed,cohort)
                  for seed in SEEDS for cohort in COHORTS]
        for mutated in (original[:-1],original+[original[0]],
                        [dict(x,private_agent_id=8) if i==0 else x
                         for i,x in enumerate(original)]):
            with self.assertRaises(ValueError):
                validate_results(mutated)
        for key,value in (
            ("actual_private_agent_ids_accessed",True),
            ("real_market_bot_FDR_known",True),
            ("source_complete_exchange_sequence_proven",True),
            ("public_tape_sha256","bad"),
            ("grid_fractions",{"10":0.4}),
            ("controlled_twap_fills_posthoc",4),
        ):
            broken=deepcopy(original)
            broken[0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                validate_results(broken)

    def test_reject_protocol_drift_before_engine_simulation(self):
        orig=frozen_protocol()
        for field,val in (
            ("local_ledger_unused_seed_candidates",[2801,2802]),
            ("original_matching_engine_runs",6),
            ("no_oracle_agent_id_in_public_feature",False),
            ("start","09:40:00"),
            ("cohorts",["only positive"]),
        ):
            cfg=deepcopy(orig)
            cfg[field]=val
            with self.subTest(field=field),patch.object(
                Path,"read_text",return_value=json.dumps(cfg)
            ),self.assertRaises(ValueError):
                frozen_protocol()


if __name__=="__main__":
    unittest.main(verbosity=2)
