#!/usr/bin/env python3
"""Research provenance must fail closed on spent seeds and source drift."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from research_seed_registry import (
    LEDGER, ROOT, read_ledger, audit_sources, assess_proposed_seeds
)


class ResearchSeedLedgerTests(unittest.TestCase):
    def setUp(self):
        self.registry = read_ledger()

    def _bad_registry(self, modify):
        data = json.loads(json.dumps(self.registry))
        modify(data)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "registry.json"
            p.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                read_ledger(p)

    def test_actual_frozen_scripts_match_historical_registry(self):
        r = audit_sources(self.registry, ROOT)
        self.assertGreaterEqual(r["canonical_studies"], 11)
        self.assertGreaterEqual(r["canonical_spent_seeds"], 25)
        self.assertEqual(len(r["source_constant_checks"]), 5)
        self.assertEqual(r["non_independent_replay_groups"], 1)
        self.assertFalse(r["globally_unused_seeds_verified"])
        self.assertFalse(r["blind_evaluation_reuse_allowed"])
        self.assertTrue(r["no_private_data_accessed"])

    def test_all_prior_development_and_toy_seeds_are_blocked_for_blind_claim(self):
        for seed in (41, 61, 71, 901, 1101, 1301, 1401, 1501,
                     1701, 1801, 1901, 2101):
            with self.subTest(seed=seed):
                r = assess_proposed_seeds(self.registry, [seed])
                self.assertTrue(r["known_spent_overlap"])
                self.assertFalse(r["eligible_for_claim_of_fresh_blind_test"])
                self.assertFalse(r["globally_unused_or_unseen_elsewhere_verified"])

    def test_unknown_seed_is_not_proven_globally_new(self):
        r = assess_proposed_seeds(self.registry, [2101, 2102])
        self.assertTrue(r["not_previously_listed_in_project_ledger"])
        self.assertFalse(r["known_spent_overlap"])
        self.assertFalse(r["eligible_for_claim_of_fresh_blind_test"])
        self.assertFalse(r["globally_unused_or_unseen_elsewhere_verified"])

    def test_registry_rejects_duplicate_canonical_seed_or_duplicate_id(self):
        self._bad_registry(lambda x: x["studies"][1]["seeds"].append(
            x["studies"][0]["seeds"][0]))
        self._bad_registry(lambda x: x["studies"][1].update(
            id=x["studies"][0]["id"]))
        self._bad_registry(lambda x: x["studies"][1].update(seeds=[61, 61]))
        self._bad_registry(lambda x: x["studies"][1].update(seeds=[True, 62]))

    def test_replay_must_be_explicit_and_non_independent(self):
        self.assertEqual(self.registry["replays"][0]["seeds"], [1501])
        self._bad_registry(lambda x: x["replays"][0].update(
            classification="independent_frozen_holdout"))
        self._bad_registry(lambda x: x["replays"][0].update(seeds=[1901]))
        self._bad_registry(lambda x: x["replays"][0].update(
            canonical_study_id="not_real"))

    def test_modified_source_seed_literal_cannot_silently_pass(self):
        data = {
            "studies": [{
                "id": "mock_study", "kind": "genuine_abides",
                "phase": "evaluated", "seeds": [11, 12],
                "source_file": "tools/frozen.py", "source_constant": "SEEDS",
            }],
            "replays": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tools").mkdir()
            source = root / "tools" / "frozen.py"
            source.write_text("SEEDS = (11, 12)\n", encoding="utf-8")
            result = audit_sources(data, root)
            self.assertEqual(result["source_constant_checks"], ["mock_study"])
            source.write_text("SEEDS = (11, 13)\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                audit_sources(data, root)
            source.write_text("SEEDS = tuple(range(11, 13))\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                audit_sources(data, root)

    def test_invalid_candidate_inputs_fail_closed(self):
        for seeds in ([], [1901, 1901], [-1], [True], [1.5]):
            with self.subTest(seeds=seeds), self.assertRaises(ValueError):
                assess_proposed_seeds(self.registry, seeds)


if __name__ == "__main__":
    unittest.main(verbosity=2)
