#!/usr/bin/env python3
"""Frozen ABIDES TWAP contrast matrix and no-agent source-only negative tests."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from abides_l2_twap_phase_contrast import (
    SEEDS,SCENARIOS,PHASES_SECONDS,frozen_plan,aggregate,run_case
)

def sample():
    rows=[]
    for seed in SEEDS:
        for scenario in SCENARIOS:
            for phase in PHASES_SECONDS:
                rows.append({
                    "seed":seed,"scenario":scenario,"phase_seconds":phase,
                    "full_public_tape_sha256":("a" if scenario=="background_only" else "b")*64,
                    "public_prints":80,"public_lots":90,"l2_snapshots":100,
                    "eligible_lagged_bins":8,"populated_trade_bins":10,
                    "abstained_bins":2,"rho":{0:-0.3,10:-0.1,20:0.2}[phase],
                    "posthoc_controlled_prints":0 if scenario=="background_only" else 5,
                    "private_identity_used_for_feature":False,
                    "best_phase_selected":False,
                    "real_market_calibrated":False})
    return rows

class FrozenControlledContrast(unittest.TestCase):
    def test_exact_precommitted_synthetic_design_is_not_blind(self):
        plan=frozen_plan()
        self.assertEqual(plan["development_seeds_local_only"],[2401,2402])
        self.assertEqual(plan["phases_seconds"],[0,10,20])
        self.assertEqual(plan["scenarios"],["background_only","twap_injected"])
        self.assertEqual(plan["genuine_matching_runs"],4)
        self.assertEqual(plan["correlated_public_phase_views"],12)
        self.assertFalse(plan["globally_unused_seeds_certified"])
        self.assertTrue(plan["internal_truth_is_posthoc_count_only"])
        self.assertTrue(plan["no_phase_or_threshold_selection"])

    def test_aggregate_counts_four_runs_not_twelve_independent_samples(self):
        result=aggregate(sample())
        self.assertEqual(result["genuine_matching_runs"],4)
        self.assertEqual(result["non_independent_analytical_views"],12)
        self.assertEqual(len(result["cohorts"]),6)
        self.assertEqual(len(result["cases"]),12)
        self.assertTrue(all(x["original_runs"]==2 for x in result["cohorts"]))
        self.assertFalse(result["private_truth_used_for_feature"])
        self.assertFalse(result["physical_bot_count_known"])
        self.assertFalse(result["real_market_significance_established"])
        self.assertFalse(result["trade_execution_enabled"])

    def test_missing_duplicates_and_tape_digest_drift_are_rejected(self):
        cases=sample()
        for candidate in (cases[:-1],cases+[cases[0]]):
            with self.assertRaises(ValueError):
                aggregate(candidate)
        changed=[dict(x) for x in cases]
        changed[0]["full_public_tape_sha256"]="z"*64
        with self.assertRaises(ValueError):
            aggregate(changed)
        changed=[dict(x) for x in cases]
        changed[0]["full_public_tape_sha256"]="c"*64
        with self.assertRaises(ValueError):
            aggregate(changed)
        changed=[dict(x) for x in cases]
        changed[0]["seed"]=1901
        with self.assertRaises(ValueError):
            aggregate(changed)

    def test_private_truth_counts_must_be_reconciled_and_not_in_features(self):
        for change in (
            {"posthoc_controlled_prints":-1},
            {"posthoc_controlled_prints":1},
            {"private_identity_used_for_feature":True},
            {"best_phase_selected":True},
            {"real_market_calibrated":True},
        ):
            with self.subTest(change=change),self.assertRaises(ValueError):
                cases=[dict(r) for r in sample()]
                cases[0].update(change)
                aggregate(cases)
        cases=[dict(r) for r in sample()]
        injected=next(x for x in cases if x["scenario"]=="twap_injected")
        injected["posthoc_controlled_prints"]=0
        with self.assertRaises(ValueError):
            aggregate(cases)

    def test_invalid_numeric_rho_and_inconsistent_counts_fail_closed(self):
        for change in (
            {"rho":float("nan")},{"rho":float("inf")},{"rho":True},
            {"rho":1.1},{"rho":"-0.2"},
            {"public_prints":True},{"public_lots":-1},
            {"l2_snapshots":2},{"eligible_lagged_bins":-1},
            {"eligible_lagged_bins":4},{"abstained_bins":3},
            {"posthoc_controlled_prints":100},
        ):
            with self.subTest(change=change),self.assertRaises(ValueError):
                cases=[dict(r) for r in sample()]
                cases[0].update(change)
                aggregate(cases)
        cases=[dict(r) for r in sample()]
        cases[0]["rho"]=None
        self.assertIsNone(next(x for x in aggregate(cases)["cases"]
                               if x["seed"]==cases[0]["seed"] and
                               x["scenario"]==cases[0]["scenario"] and
                               x["phase_seconds"]==cases[0]["phase_seconds"])["rho"])

    def test_original_genuine_matching_aggregate_fixture_matches_plan(self):
        import json
        path=(Path(__file__).resolve().parents[1] / "fixtures"
              / "abides_l2_twap_phase_observed_20261121.json")
        record=json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(record["source_workflow_run_id"],44915375635)
        self.assertEqual(record["original_aggregate_sha256"],
                         "2391c9f223b6841f8346502282b7e099856e6feee7726cd4769967dcbcd97fa8")
        self.assertFalse(record["source_content_authenticated_by_external_provider"])
        self.assertFalse(record["raw_event_archive_included"])
        report=aggregate(record["cases"])
        self.assertEqual(report["genuine_matching_runs"],4)
        self.assertEqual(report["non_independent_analytical_views"],12)
        expected={
            ("background_only",0):-0.22622645896303184,
            ("background_only",10):-0.061293054771315636,
            ("background_only",20):-0.47556791035051904,
            ("twap_injected",0):-0.07113534825205306,
            ("twap_injected",10):0.00005812601720530091,
            ("twap_injected",20):0.10044991576826279,
        }
        for row in report["cohorts"]:
            self.assertAlmostEqual(
                row["median_descriptive_rho"],
                expected[(row["scenario"],row["phase_seconds"])],places=12)
        inversions=0
        for seed in SEEDS:
            for scenario in SCENARIOS:
                rows=[r for r in report["cases"] if r["seed"]==seed
                      and r["scenario"]==scenario]
                coeff=[r["rho"] for r in rows]
                inversions+=int(min(coeff)<0<max(coeff))
                self.assertEqual(len({r["full_public_tape_sha256"] for r in rows}),1)
                self.assertEqual(
                    rows[0]["posthoc_controlled_prints"],
                    22 if scenario=="twap_injected" else 0)
        self.assertEqual(inversions,2)

    def test_illegal_scenarios_frozen_before_simulator_import(self):
        for args in ((2400,"background_only"),(2401,"twap"),(2402,"poisson")):
            with self.assertRaises(ValueError):
                run_case(*args)

if __name__=="__main__":
    unittest.main(verbosity=2)
