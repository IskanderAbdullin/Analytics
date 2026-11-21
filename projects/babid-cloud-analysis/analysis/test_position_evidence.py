"""Two-lot position discrepancy synthetic evidence, no live broker data."""
from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from position_evidence import reconcile, run


class PositionEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.state = self.root / "state-nvda"
        self.logs = self.root / "logs-nvda"
        self.state.mkdir()
        self.logs.mkdir()

    def fixture(self):
        (self.logs / "babid01.log").write_text(
            "2026-11-21 14:55:00.000 ERR Position check: position outside the robot changed from 0 to -2 lots (broker +31, journal +33): check\n"
            "2026-11-21 15:01:47.000 ERR RISK: Halted — position outside the robot changed from -2 to 0 lots (broker 0, journal 0)\n",
            encoding="utf-8")
        (self.state / "fills.csv").write_text(
            "time_msk;exchange_id;trade_id;side;lots;synthetic\n"
            "2026-11-21 14:56:00.000;ex;trade1;Sell;20;0\n"
            "2026-11-21 14:57:00.000;ex;trade2;Sell;13;0\n",
            encoding="utf-8")

    def test_position_arithmetic_and_local_fill_delta(self):
        self.fixture()
        positions, intervals, summary = reconcile(self.root, "state-nvda", "logs-nvda")
        self.assertEqual(summary["observations"], 2)
        self.assertEqual(summary["external_changes"], 1)
        self.assertEqual(summary["journal_fill_mismatches"], 0)
        self.assertEqual(str(intervals[0]["broker_delta_lots"]), "-31")
        self.assertEqual(str(intervals[0]["journal_delta_lots"]), "-33")
        self.assertEqual(str(intervals[0]["external_delta_lots"]), "2")
        self.assertEqual(str(intervals[0]["fill_net_lots_in_window"]), "-33")
        self.assertEqual(positions[0]["reported_consistent"], True)
        self.assertEqual(positions[1]["reported_consistent"], True)

    def test_flag_unexplained_local_fill_gap_and_duplicate(self):
        self.fixture()
        file = self.state / "fills.csv"
        with file.open("a", encoding="utf-8") as output:
            output.write("2026-11-21 14:58:00.000;ex;trade2;Sell;13;0\n")
        text = file.read_text().replace("Sell;13;0", "Sell;12;0", 1)
        file.write_text(text)
        _, intervals, summary = reconcile(self.root, "state-nvda", "logs-nvda")
        self.assertEqual(summary["duplicate_fill_ids"], 1)
        self.assertEqual(summary["journal_fill_mismatches"], 1)
        self.assertEqual(str(intervals[0]["fill_net_lots_in_window"]), "-32")

    def test_report_is_read_only_and_opt_in_paths(self):
        self.fixture()
        output = self.root / "reports" / "evidence"
        result = run(self.root, output, "state-nvda", "logs-nvda")
        self.assertEqual(result["comparison_intervals"], 1)
        with (output / "position_deltas.csv").open(newline="", encoding="utf-8") as f:
            self.assertEqual(len(list(csv.DictReader(f))), 1)
        with self.assertRaises(ValueError):
            run(self.root, output, "state-nvda", "logs-nvda")
        with self.assertRaises(ValueError):
            reconcile(self.root, "../state-nvda", "logs-nvda")

    def test_first_observation_transition_is_not_lost(self):
        self.fixture()
        positions, _, summary = reconcile(self.root, "state-nvda", "logs-nvda")
        self.assertEqual(summary["external_changes"], 1)  # only paired endpoints
        self.assertEqual(summary["reported_external_transitions"], 2)
        self.assertTrue(summary["first_observation_transition_unanchored"])
        self.assertEqual(summary["reported_prior_position_disagreements"], 0)
        self.assertEqual(str(positions[0]["reported_transition_lots"]), "-2")
        self.assertEqual(str(positions[1]["reported_transition_lots"]), "2")

    def test_single_reported_transition_is_counted_without_any_pair(self):
        self.fixture()
        source = self.logs / "babid01.log"
        source.write_text(source.read_text().splitlines(keepends=True)[0], encoding="utf-8")
        _, intervals, summary = reconcile(self.root, "state-nvda", "logs-nvda")
        self.assertEqual(intervals, [])
        self.assertEqual(summary["external_changes"], 0)
        self.assertEqual(summary["reported_external_transitions"], 1)
        self.assertTrue(summary["first_observation_transition_unanchored"])


if __name__ == "__main__":
    unittest.main()
