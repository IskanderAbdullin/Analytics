#!/usr/bin/env python3
"""Frozen public-L2 origin offsets are correlated views of the same tape."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from abides_l2_binphase_sensitivity import (
    SEEDS, BACKGROUNDS, PHASES_SECONDS,
    frozen_plan, shift_public_clock, aggregate
)
from l2_trade_context import PublicExecution

NS=1_000_000_000


def fake(seed,mode,phase,rho):
    return {
        "seed":seed,"background":mode,"phase_seconds":phase,
        "public_sha256":f"{seed}{mode}".encode().hex().ljust(64,"0"),
        "public_prints":600,"public_lots":1300,"l2_snapshots":950,
        "eligible_lagged_bins":12,"populated_trade_bins":15,
        "abstained_bins":3,"descriptive_rho":rho,
        "claimed_real_feed_completeness":False,
        "private_identity_accessed":False,"model_selected":False
    }


def matrix(rhos=None):
    rhos=rhos or {0:-0.6,10:-0.2,20:0.3}
    return [fake(seed,mode,phase,rhos[phase])
            for seed in SEEDS for mode in BACKGROUNDS
            for phase in PHASES_SECONDS]


class FrozenClockPhaseTests(unittest.TestCase):
    def test_protocol_frozen_without_selection_or_actor_claim(self):
        p=frozen_plan()
        self.assertEqual(p["seeds"],[2101,2102])
        self.assertEqual(p["phases_seconds"],[0,10,20])
        self.assertEqual(p["bin_width_seconds"],30)
        self.assertEqual(p["actual_simulations"],4)
        self.assertEqual(p["analytic_views_of_same_public_tape"],12)
        self.assertFalse(p["source_completion_attested"])
        self.assertTrue(p["no_model_selection_or_best_phase"])
        self.assertTrue(p["public_features_only"])

    def test_shift_same_public_events_preserves_time_differences_and_book_levels(self):
        book=SimpleNamespace(
            times_ns=[25*NS,30*NS,30*NS,65*NS],
            bids=[[(100,3)],[(100,5)],[(101,6)],[(100,4)]],
            asks=[[(102,3)],[(102,2)],[(103,2)],[(102,5)]])
        tape=(PublicExecution(31*NS,102,7,"BUY"),
              PublicExecution(66*NS,100,8,"SELL"))
        shifted,prints=shift_public_clock(book,tape,20)
        self.assertEqual(shifted.times_ns,[5*NS,10*NS,10*NS,45*NS])
        self.assertEqual([x.time_ns for x in prints],[11*NS,46*NS])
        self.assertEqual(book.bids,shifted.bids)
        self.assertEqual(book.asks,shifted.asks)
        self.assertEqual([(p.price_cents,p.quantity,p.reported_aggressor_side)
                          for p in tape],
                         [(p.price_cents,p.quantity,p.reported_aggressor_side)
                          for p in prints])
        self.assertEqual(book.times_ns[2]-book.times_ns[1],
                         shifted.times_ns[2]-shifted.times_ns[1])

    def test_unsupported_phase_or_noninteger_source_rejected(self):
        book=SimpleNamespace(times_ns=[25*NS],bids=[[(100,2)]],asks=[[(102,2)]])
        tape=(PublicExecution(31*NS,102,2,"BUY"),)
        with self.assertRaises(ValueError):
            shift_public_clock(book,tape,7)
        with self.assertRaises(ValueError):
            shift_public_clock(
                SimpleNamespace(times_ns=[5*NS],bids=book.bids,asks=book.asks),
                tape,20)
        with self.assertRaises(ValueError):
            shift_public_clock(
                SimpleNamespace(times_ns=[25.0*NS],bids=book.bids,asks=book.asks),
                tape,10)

    def test_aggregate_counts_four_not_twelve_independent_simulations(self):
        report=aggregate(matrix())
        self.assertEqual(report["actual_matching_engine_simulations"],4)
        self.assertEqual(report["non_independent_analytical_views"],12)
        self.assertEqual(len(report["cohorts"]),6)
        self.assertEqual(len(report["per_simulation_sensitivity"]),4)
        self.assertTrue(all(x["simulations"]==2 for x in report["cohorts"]))
        self.assertTrue(all(abs(x["rho_range"]-0.9)<1e-9
                            for x in report["per_simulation_sensitivity"]))
        self.assertFalse(report["private_truth_used"])
        self.assertFalse(report["real_market_accuracy_calibrated"])
        self.assertFalse(report["physical_owner_count_known"])
        self.assertFalse(report["independent_provider_completeness_verified"])

    def test_missing_duplicate_or_drifted_public_tape_rejected(self):
        raw=matrix()
        with self.assertRaises(ValueError):
            aggregate(raw[:-1])
        with self.assertRaises(ValueError):
            aggregate(raw+[raw[0]])
        changed=[dict(x) for x in raw]
        changed[0]["public_sha256"]="f"*64
        with self.assertRaises(ValueError):
            aggregate(changed)
        bad=[dict(x) for x in raw]
        bad[0]["seed"]=1901
        with self.assertRaises(ValueError):
            aggregate(bad)

    def test_fails_closed_on_nan_infinite_or_non_numeric_rho(self):
        for bad_rho in (float("nan"), float("inf"), -float("inf"),
                        True, "0.1", [], 0j):
            with self.subTest(bad_rho=repr(bad_rho)), self.assertRaises(ValueError):
                cases=[dict(x) for x in matrix()]
                cases[0]["descriptive_rho"]=bad_rho
                aggregate(cases)

    def test_counts_must_be_exact_and_physically_consistent(self):
        for key, value in (
            ("seed", True), ("phase_seconds", False),
            ("public_prints", 600.0), ("public_lots", True),
            ("l2_snapshots", "950"), ("eligible_lagged_bins", 12.0),
            ("populated_trade_bins", 0), ("abstained_bins", -1),
            ("public_lots", 599), ("public_prints", 14),
            ("eligible_lagged_bins", 951),
        ):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                cases=[dict(x) for x in matrix()]
                cases[0][key]=value
                aggregate(cases)
        cases=[dict(x) for x in matrix()]
        cases[0].update(eligible_lagged_bins=1, abstained_bins=14,
                        descriptive_rho=0.5)
        with self.assertRaises(ValueError):
            aggregate(cases)

    def test_digest_and_flags_require_canonical_exact_types(self):
        for key, value in (
            ("public_sha256", "x"*64),
            ("public_sha256", "A"*64),
            ("public_sha256", "0"*63),
            ("public_sha256", 123),
            ("claimed_real_feed_completeness", 0),
            ("private_identity_accessed", None),
            ("model_selected", "false"),
        ):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                cases=[dict(x) for x in matrix()]
                cases[0][key]=value
                aggregate(cases)
        for bad_matrix in (None, {}, [None], [dict(x) for x in matrix()]):
            if isinstance(bad_matrix, list) and bad_matrix and type(bad_matrix[0]) is dict:
                del bad_matrix[0]["background"]
            with self.assertRaises(ValueError):
                aggregate(bad_matrix)

    def test_undefined_rho_and_false_evidence_claims_fail_closed(self):
        r=aggregate(matrix({0:None,10:-0.1,20:None}))
        self.assertEqual(len(r["cohorts"]),6)
        self.assertTrue(all(c["median_descriptive_rho"] is None
                            for c in r["cohorts"] if c["phase_seconds"] in (0,20)))
        for patch in (
            {"claimed_real_feed_completeness":True},
            {"private_identity_accessed":True},
            {"model_selected":True},
            {"abstained_bins":5},
            {"descriptive_rho":1.2}
        ):
            with self.subTest(patch=patch),self.assertRaises(ValueError):
                case=[dict(x) for x in matrix()]
                case[0].update(patch)
                aggregate(case)


if __name__=="__main__":
    unittest.main(verbosity=2)
