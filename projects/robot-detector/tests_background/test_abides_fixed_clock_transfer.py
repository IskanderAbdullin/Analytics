#!/usr/bin/env python3
"""Synthetic-only source-public ABIDES fixed-grid transfer contract tests."""
from dataclasses import replace
from pathlib import Path
import sys
import unittest
from copy import deepcopy

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from abides_fixed_clock_transfer import (
    SEEDS,COHORTS,THRESHOLD,GRID_TOLERANCE_NS,
    GRID_PERIOD_NS,ALLOWED_CASE_FIELDS,
    frozen_plan, score_abides_public_only,audit_result
)
from l2_trade_context import PublicExecution
from research_seed_registry import read_ledger


def trade(offset:int,side:str="BUY")->PublicExecution:
    return PublicExecution(
        34_200_000_000_000+offset,10000,2,side
    )


def fake_cases():
    cases=[]
    for seed in SEEDS:
        for cohort in COHORTS:
            alarm=cohort!="poisson_noise_null"
            target=cohort=="twap_injected_positive"
            count=160
            hit=100 if alarm else 0
            cases.append({
                "seed":seed,"cohort":cohort,
                "original_public_prints":count,
                "original_public_l2_snapshots":170,
                "public_tape_sha256":"a"*64,
                "public_prints_within_frozen_10s_grid":hit,
                "public_fraction_within_frozen_grid":round(hit/count,8),
                "fixed_threshold_0_22_alarm":alarm,
                "posthoc_injected_target_present":target,
                "posthoc_source_controlled_trade_count":5 if target else 0,
                "correct_synthetic_target_classification":alarm==target,
                "false_alarm_on_background":alarm and not target,
                "public_feature_accessed_private_agent_identifiers":False,
                "private_agent_identifiers_exported":False,
                "original_market_actor_truth_known":False,
                "genuine_ABIDES_matching_engine_simulation":True,
                "real_market_FDR_calibrated":False,
            })
    return cases


class FrozenGenuineABIDESFixedGridTests(unittest.TestCase):
    def test_exact_new_sources_book_scope_and_grid_precommitted_before_running(self):
        p=frozen_plan()
        self.assertEqual(p["new_locally_uninspected_seeds"],[2801,2802])
        self.assertEqual(p["simulation_start_exchange_time"],"09:30:00")
        self.assertEqual(p["simulation_end_exchange_time"],"09:38:00")
        self.assertEqual(p["source_matching_engine_runs"],6)
        self.assertEqual(p["frozen_grid_tolerance_ns"],250000000)
        self.assertEqual(p["frozen_fraction_threshold"],0.22)
        self.assertTrue(p["private_simulated_owner_ids_only_accessible_posthoc_after_public_feature_computed"])
        ledger=read_ledger()
        # Register these new seeds before any source simulation attempt.
        known={s for study in ledger["studies"] for s in study["seeds"]}
        self.assertTrue(set(SEEDS).issubset(known))
        self.assertEqual(GRID_PERIOD_NS,10_000_000_000)

    def test_precise_grid_edge_and_source_public_only_schema(self):
        samples=tuple(trade(x) for x in (
            0,GRID_TOLERANCE_NS,GRID_TOLERANCE_NS+1,
            GRID_PERIOD_NS-GRID_TOLERANCE_NS
        ))
        r=score_abides_public_only(samples)
        self.assertEqual(r["public_prints"],4)
        self.assertEqual(r["fixed_clock_hit_count"],3)
        self.assertEqual(r["fixed_clock_fraction"],0.75)
        self.assertTrue(r["fixed_clock_alarm"])
        self.assertEqual(len(r["public_tape_sha256"]),64)
        self.assertFalse(r["actual_private_oracle_data_accessed"])
        self.assertFalse(r["physical_owner_count_identified"])

    def test_market_event_public_order_and_source_labels_fail_closed(self):
        for bad in ((), (trade(0),{"owner_id":"PRIVATE"}),
                    (trade(GRID_PERIOD_NS),trade(0)),
                    (replace(trade(0),reported_aggressor_side="UNKNOWN"),),
                    (replace(trade(0),quantity=0),),
                    (replace(trade(0),price_cents=0),),
                    (replace(trade(0),time_ns=True),)):
            with self.subTest(sample=str(bad)[:25]),self.assertRaises(ValueError):
                score_abides_public_only(bad)
        with self.assertRaises(ValueError):
            score_abides_public_only([trade(0)])

    def test_frozen_synthetic_outputs_reconcile_false_positive_and_negative(self):
        report=audit_result(fake_cases())
        self.assertEqual(report["independent_matching_engine_runs"],6)
        self.assertEqual([x["cohort"] for x in report["source_public_tape_cases"][:3]],
                         list(COHORTS))
        self.assertEqual(report["cohort_results"]["fixed_cadence_noise_hard_negative"][
            "false_alarms_on_background"],2)
        self.assertEqual(report["cohort_results"]["twap_injected_positive"][
            "posthoc_controlled_prints"],10)
        self.assertEqual(report["cohort_results"]["twap_injected_positive"][
            "false_negative_real_TWAP_count"],0)
        self.assertFalse(report["real_market_robot_precision_or_FDR_calibrated"])
        self.assertFalse(report["threshold_or_phase_selected_after_results"])
        self.assertTrue(report["private_agent_identifiers_read_only_after_public_feature"])
        self.assertFalse(report["raw_source_trade_or_l2_book_rows_exported"])
        self.assertEqual(set(report["source_public_tape_cases"][0]),ALLOWED_CASE_FIELDS)

    def test_missing_or_extra_source_run_and_private_leak_rejected(self):
        for rows in (fake_cases()[:-1],fake_cases()+fake_cases()[:1]):
            with self.assertRaises(ValueError):
                audit_result(rows)
        for scope,field,value in (
            ("case","public_fraction_within_frozen_grid",1),
            ("case","fixed_threshold_0_22_alarm",False),
            ("case","real_market_FDR_calibrated",True),
            ("case","private_agent_identifiers_exported",True),
            ("case","public_tape_sha256","0"),
            ("case","original_public_prints",-1),
            ("case","posthoc_source_controlled_trade_count",2),
            ("case","owner_id","PRIVATE"),
        ):
            rows=fake_cases()
            rows[1][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                audit_result(rows)

    def test_frozen_plan_rejects_uncommitted_new_simulator_inputs(self):
        import json
        from unittest.mock import patch
        cfg=frozen_plan()
        for field,value in (
            ("new_locally_uninspected_seeds",[2801]),
            ("frozen_period_seconds",15),
            ("frozen_fraction_threshold",0.5),
            ("simulation_start_exchange_time","09:31:00"),
            ("source_matching_engine_runs",4),
            ("no_best_phase_model_threshold_or_seed_selection",False),
            ("abides_upstream_git_commit","OTHER"),
        ):
            wrong=deepcopy(cfg)
            wrong[field]=value
            with self.subTest(field=field), patch.object(
                Path,"read_text",return_value=json.dumps(wrong)
            ),self.assertRaises(ValueError):
                frozen_plan()

if __name__=="__main__":
    unittest.main(verbosity=2)
