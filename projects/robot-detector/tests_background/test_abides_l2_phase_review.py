#!/usr/bin/env python3
"""Offline phase review: original summaries, parser, no-simulator guards."""
import json
import statistics
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from abides_l2_binphase_sensitivity import aggregate, SEEDS, BACKGROUNDS, PHASES_SECONDS
from abides_l2_phase_review import MAX_INPUT_BYTES, parse_input, reanalyse_saved_result, main


def saved_report():
    cases=[]
    for seed in SEEDS:
        for mode in BACKGROUNDS:
            for phase, rho in ((0,-0.6),(10,-0.2),(20,0.3)):
                cases.append({
                    "seed":seed, "background":mode, "phase_seconds":phase,
                    "public_sha256":("a" if seed==2101 else "b")*64,
                    "public_prints":80, "public_lots":120, "l2_snapshots":90,
                    "populated_trade_bins":10, "eligible_lagged_bins":8,
                    "abstained_bins":2, "descriptive_rho":rho,
                    "claimed_real_feed_completeness":False,
                    "private_identity_accessed":False, "model_selected":False,
                })
    return aggregate(cases)


class OfflineReviewTests(unittest.TestCase):
    def test_existing_frozen_cases_produce_four_paired_contrasts(self):
        r=reanalyse_saved_result(saved_report())
        self.assertEqual(r["additional_simulations_run"],0)
        self.assertEqual(len(r["paired_cohort_contrasts"]),4)
        self.assertTrue(all(x["simulations_with_defined_paired_rho"]==2
                            for x in r["paired_cohort_contrasts"]))
        self.assertFalse(r["source_file_authenticity_verified"])

    def test_legacy_sensitivity_keys_are_accepted(self):
        report=saved_report()
        for item in report["per_simulation_sensitivity"]:
            for key in ("rho_sign_reversal_between_defined_phases",
                        "signed_rho_delta_from_zero_second_origin",
                        "max_abs_rho_delta_from_zero_second_origin",
                        "eligible_bin_count_range_across_phases"):
                del item[key]
        r=reanalyse_saved_result(report)
        self.assertTrue(all(x["rho_sign_reversal_between_defined_phases"]
                            for x in r["per_simulation_sensitivity"]))

    def test_forged_claims_and_cohort_drift_fail_closed(self):
        for key, value in (
            ("schema_version","wrong"),
            ("actual_matching_engine_simulations",12),
            ("non_independent_analytical_views",True),
            ("private_truth_used",True),
            ("real_market_accuracy_calibrated",0),
            ("cohorts",[]),
            ("per_simulation_sensitivity",[]),
        ):
            with self.subTest(key=key),self.assertRaises(ValueError):
                data=saved_report()
                data[key]=value
                reanalyse_saved_result(data)

    def test_changed_case_wrong_order_or_old_summary_rejected(self):
        for mutation in ("case","order","summary","source"):
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                data=saved_report()
                if mutation=="case":
                    data["cases"][0]["descriptive_rho"]=0.8
                elif mutation=="order":
                    data["cases"].reverse()
                elif mutation=="summary":
                    data["per_simulation_sensitivity"][0]["rho_range"]=0.1
                else:
                    data["cases"][0]["public_sha256"]="c"*64
                reanalyse_saved_result(data)

    def test_strict_json_loader(self):
        for raw in (b'{"a":1,"a":2}',b'{"rho":NaN}',
                    b'{"rho":Infinity}',b"not json",b"\xff",
                    b"x"*(MAX_INPUT_BYTES+1),b"[]"):
            with self.subTest(raw=raw[:20]),self.assertRaises(ValueError):
                parse_input(raw)
        self.assertEqual(len(parse_input(json.dumps(saved_report()).encode())["cases"]),12)

    def test_pinned_original_public_scalar_fixture_and_paired_changes(self):
        fixture_path=(Path(__file__).resolve().parents[1] / "fixtures"
                      / "abides_l2_phase_observed_scalars_20261121.json")
        evidence=json.loads(fixture_path.read_text(encoding="utf-8"))
        self.assertEqual(evidence["source_simulations"],4)
        self.assertEqual(evidence["correlated_analytic_views"],12)
        self.assertEqual(evidence["full_original_json_sha256"],
                         "8db020efd034eb3870aa772785320ada62ac25a7392ffd158284b55af1eb1009")
        self.assertFalse(evidence["source_authenticity_independently_verified"])
        self.assertEqual(len(evidence["cases"]),12)
        expected={
            ("poisson",10):-0.14711531793911659,
            ("poisson",20):-0.16724964585376484,
            ("fixed_cadence",10):0.02319187296304001,
            ("fixed_cadence",20):-0.2746995948368946,
        }
        sign_reversals=0
        for mode in BACKGROUNDS:
            for seed in SEEDS:
                by_phase={r["phase_seconds"]:r for r in evidence["cases"]
                          if r["background"]==mode and r["seed"]==seed}
                self.assertEqual(set(by_phase),set(PHASES_SECONDS))
                sign_reversals += (min(r["descriptive_rho"] for r in by_phase.values())<0
                                   <max(r["descriptive_rho"] for r in by_phase.values()))
                self.assertTrue(all(r["eligible_lagged_bins"]<=r["populated_trade_bins"]
                                    for r in by_phase.values()))
            for phase in PHASES_SECONDS[1:]:
                deltas=[]
                for seed in SEEDS:
                    by_phase={r["phase_seconds"]:r for r in evidence["cases"]
                              if r["background"]==mode and r["seed"]==seed}
                    deltas.append(by_phase[phase]["descriptive_rho"]
                                  -by_phase[0]["descriptive_rho"])
                self.assertAlmostEqual(statistics.median(deltas),
                                       expected[(mode,phase)],places=12)
        self.assertEqual(sign_reversals,1)

    def test_cli_no_market_run_and_atomic_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            inp=Path(d)/"saved.json"
            out=Path(d)/"review.json"
            inp.write_text(json.dumps(saved_report()),encoding="utf-8")
            with patch("sys.argv",["review","--input",str(inp),"--output",str(out)]):
                with patch("abides_l2_binphase_sensitivity.run_case",
                           side_effect=AssertionError("Unexpected simulator")):
                    main()
            self.assertEqual(json.loads(out.read_text())["additional_simulations_run"],0)
            original=out.read_bytes()
            with patch("sys.argv",["review","--input",str(inp),"--output",str(out)]):
                with self.assertRaises(FileExistsError):
                    main()
            self.assertEqual(out.read_bytes(),original)


if __name__=="__main__":
    unittest.main(verbosity=2)
