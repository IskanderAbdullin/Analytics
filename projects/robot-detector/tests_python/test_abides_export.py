#!/usr/bin/env python3
"""Dependency-free deterministic tests of the ABIDES public/private projector."""
from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from abides_export import project_executions  # noqa: E402


def execution(time_ns: int, price: int = 10050, quantity: int = 100,
              passive: int = 7, aggressive: int = 99,
              side: str = "SELL") -> SimpleNamespace:
    return SimpleNamespace(time_ns=time_ns, price_cents=price, quantity=quantity,
                           passive_agent_id=passive, aggressive_agent_id=aggressive,
                           side=side)


class AbidesProjectionTests(unittest.TestCase):
    def test_public_projection_contains_no_owners_and_is_deterministic(self) -> None:
        t = [execution(1_632_000_000_000_000_101),
             execution(1_632_000_000_000_000_101, passive=55, aggressive=7),
             execution(1_632_000_000_000_000_330, side="BUY")]
        public, private = project_executions(t, seed=42, ticker="ABM",
                                             controlled_agent_ids=[7])
        again, same_truth = project_executions(t, seed=42, ticker="ABM",
                                               controlled_agent_ids=[7])
        self.assertEqual((public, private), (again, same_truth))
        self.assertEqual(hashlib.sha256(public).hexdigest(), private["public_sha256"])
        self.assertEqual(len(private["events"]), 3)
        self.assertNotIn(b"agent_id", public)
        self.assertNotIn(b"controlled", public)
        self.assertNotIn(b"TWAP", public)
        lines = public.decode().splitlines()
        self.assertEqual(len(lines), 4)
        self.assertEqual(len({item["event_id"] for item in private["events"]}), 3)
        self.assertEqual(public.count(b"SIMULATED_ABIDES_NG"), 3)
        self.assertIn("BUY,100.5,100,EXCHANGE", public.decode())
        self.assertIn("SELL,100.5,100,EXCHANGE", public.decode())

    def test_private_relabel_does_not_change_public_tape(self) -> None:
        data = [execution(1_632_000_000_000_000_101),
                execution(1_632_000_000_000_000_330)]
        public_a, truth_a = project_executions(data, seed=19, ticker="ABM",
                                               controlled_agent_ids=[7])
        public_b, truth_b = project_executions(data, seed=19, ticker="ABM",
                                               controlled_agent_ids=[55])
        self.assertEqual(public_a, public_b)
        self.assertEqual(truth_a["events"], truth_b["events"])
        self.assertNotEqual(truth_a["controlled_agent_ids"], truth_b["controlled_agent_ids"])

    def test_distinct_fills_even_at_identical_timestamp(self) -> None:
        t = [execution(1_632_000_000_000_000_101, quantity=50),
             execution(1_632_000_000_000_000_101, quantity=50)]
        public, truth = project_executions(t, seed=1, ticker="ABM",
                                           controlled_agent_ids=[7])
        self.assertEqual(len(truth["events"]), 2)
        self.assertEqual(len({e["event_id"] for e in truth["events"]}), 2)
        self.assertEqual(public.count(b",50,EXCHANGE"), 2)

    def test_negative_truth_and_validation(self) -> None:
        data = [execution(1_632_000_000_000_000_000)]
        _, truth = project_executions(data, seed=0, ticker="ABM",
                                      controlled_agent_ids=[])
        self.assertFalse(truth["controlled_agent_ids"])
        with self.assertRaises(ValueError):
            project_executions(data, seed=-1, ticker="ABM", controlled_agent_ids=[])
        with self.assertRaises(ValueError):
            project_executions(data, seed=0, ticker="ABM", controlled_agent_ids=[7, 7])
        with self.assertRaises(ValueError):
            project_executions([execution(1_632_000_000_000_000_101, quantity=-1)],
                               seed=0, ticker="ABM", controlled_agent_ids=[])
        with self.assertRaises(ValueError):
            project_executions([execution(1_632_000_000_000_000_101, side="UNKNOWN")],
                               seed=0, ticker="ABM", controlled_agent_ids=[])


if __name__ == "__main__":
    unittest.main(verbosity=2)
