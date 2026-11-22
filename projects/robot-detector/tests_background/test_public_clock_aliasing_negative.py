"""Mathematical, source-free negative controls against false TWAP inference."""
from pathlib import Path
import json
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from public_clock_aliasing_negative import (
    NS,ANCHOR,TOL_NS,aliasing_lattice,report_frozen_aliasing_negative
)

ROOT=Path(__file__).resolve().parents[1]


class PublicLatticeAliasingNegatives(unittest.TestCase):
    def test_twenty_second_background_exactly_aliases_fortyfive_second_grid(self):
        x=aliasing_lattice(20,45,n_source_events=90)
        self.assertEqual(x["gcd_of_periods_seconds"],5)
        self.assertEqual(x["lcm_of_periods_seconds"],180)
        self.assertEqual(x["complete_periodic_source_cycle_events"],9)
        self.assertEqual(x["observed_public_grid_hits"],10)
        self.assertAlmostEqual(x["descriptive_fraction_on_grid"],1/9,places=7)
        self.assertFalse(x["public_clock_pattern_implies_injected_target"])
        self.assertFalse(x["real_market_owner_accuracy_or_FDR_measured"])
        self.assertFalse(x["oracle_agent_labels_used"])
        self.assertFalse(x["raw_event_timestamps_exported"])

    def test_one_second_phase_shift_breaks_exact_20s_45s_intersections(self):
        aligned=aliasing_lattice(20,45,n_source_events=90)
        shifted=aliasing_lattice(20,45,source_phase_ns=NS,n_source_events=90)
        self.assertEqual(shifted["observed_public_grid_hits"],0)
        self.assertEqual(shifted["descriptive_fraction_on_grid"],0)
        self.assertEqual(shifted["lcm_of_periods_seconds"],
                         aligned["lcm_of_periods_seconds"])
        self.assertEqual(shifted["source_events_tested"],90)
        self.assertFalse(shifted["public_clock_pattern_implies_injected_target"])

    def test_tolerance_is_inclusive_but_does_not_modify_source_identity(self):
        edge=aliasing_lattice(20,45,source_phase_ns=TOL_NS,n_source_events=90)
        beyond=aliasing_lattice(20,45,source_phase_ns=TOL_NS+1,n_source_events=90)
        self.assertEqual(edge["observed_public_grid_hits"],10)
        self.assertEqual(beyond["observed_public_grid_hits"],0)
        all_tens=aliasing_lattice(20,10,n_source_events=90)
        self.assertEqual(all_tens["observed_public_grid_hits"],90)
        # Full 9-source-event period has exactly 1 hit at fixed origin.
        period=aliasing_lattice(20,45,n_source_events=9)
        self.assertEqual(period["observed_public_grid_hits"],1)

    def test_preregistered_source_observation_remains_negative_control(self):
        r=report_frozen_aliasing_negative()
        self.assertEqual(r["frozen_prior_source_run"],44935340284)
        self.assertEqual(r["schema_version"],
                         "predeclared-public-20s-vs-45s-aliasing-control-v1")
        self.assertEqual(r["fixed_20s_no_twap_periodic_background"][
            "observed_public_grid_hits"],10)
        self.assertEqual(r["one_second_shifted_20s_background"][
            "observed_public_grid_hits"],0)
        self.assertGreater(r["45s_original_ABIDES_hard_negative_mean_fraction"],
                           r["45s_original_ABIDES_positive_mean_fraction"])
        self.assertTrue(r["no_original_market_event_rows_or_agent_ids_used"])
        self.assertTrue(r["not_a_posthoc_optimized_classification_threshold"])
        self.assertTrue(r["neither_true_owner_identity_nor_market_FDR_established"])

    def test_original_source_fixture_records_all_12_cases_and_no_owners(self):
        p=ROOT/"fixtures"/"abides_multiscale_public_l2_observed_20261121.json"
        r=json.loads(p.read_text(encoding="utf-8"))
        self.assertEqual(r["original_research_run_id"],44935340284)
        self.assertEqual(r["original_compact_aggregate_artifact"],14719426242)
        self.assertEqual(r["original_independent_simulation_runs"],12)
        self.assertEqual(len(r["original_case_descriptive_aggregates"]),12)
        self.assertEqual(r["source_aggregate_executed_prints"],12568)
        self.assertEqual(r["source_aggregate_l2_snapshots"],21675)
        self.assertEqual(r["source_aggregate_posthoc_controlled_twap_fills"],67)
        self.assertEqual(r["legacy_10s_fixed_negative_false_alarms"],3)
        self.assertEqual(r["legacy_10s_twap_positive_misses"],3)
        self.assertFalse(r["real_market_FDR_or_owner_identity_calibrated"])
        self.assertFalse(r["oracle_owner_IDs_exported"])
        self.assertTrue(r["source_results_were_not_used_to_fit_thresholds"])
        self.assertTrue(r["fixed_noise_45sec_grid_fraction_exceeds_twap_fraction"])
        for x in r["original_case_descriptive_aggregates"]:
            self.assertEqual(set(x["grid_fractions"]),{"10","20","45","90"})
            self.assertEqual(x["controlled_fills_posthoc"]>0,
                             x["cohort"]=="twap_45s_positive")
            self.assertFalse(x["real_owner_truth_known"])

    def test_source_free_bounds_reject_invalid_integer_or_large_input(self):
        for kw in (
            {"source_period_seconds":0,"observed_grid_seconds":45},
            {"source_period_seconds":20.0,"observed_grid_seconds":45},
            {"source_period_seconds":20,"observed_grid_seconds":0},
            {"source_period_seconds":20,"observed_grid_seconds":45,
             "n_source_events":10001},
            {"source_period_seconds":20,"observed_grid_seconds":45,
             "source_phase_ns":45*NS},
            {"source_period_seconds":20,"observed_grid_seconds":45,
             "source_phase_ns":True},
            {"source_period_seconds":20,"observed_grid_seconds":45,
             "tolerance_ns":-1},
        ):
            with self.subTest(kw=kw),self.assertRaises(ValueError):
                aliasing_lattice(**kw)


if __name__=="__main__":
    unittest.main(verbosity=2)
