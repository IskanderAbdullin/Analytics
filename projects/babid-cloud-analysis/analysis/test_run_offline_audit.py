"""Synthetic safety and provenance tests for the audit coordinator."""
import tempfile
import unittest
from pathlib import Path
from run_offline_audit import checksum, inventory, run


class CoordinatorTests(unittest.TestCase):
    def test_checksum_and_safe_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "state-test").mkdir()
            (root / "config.test.json").write_text('{"mode":"paper","stateDir":"state-test"}')
            (root / "state-test" / "journal.json").write_text('{"Mode":"paper"}')
            c = checksum(root / "config.test.json")
            self.assertEqual(len(c), 64)
            self.assertEqual(len(inventory(root)), 2)
            output = root / "reports" / "once"
            result = run(root, output, with_market=False)
            self.assertIn("history", result["reports"])
            self.assertTrue((output / "manifest.json").is_file())
            with self.assertRaises(ValueError):
                run(root, output, with_market=False)
            with self.assertRaises(ValueError):
                run(root, root / "state-test" / "reports", with_market=False)

    def test_entire_history_is_default_and_incident_is_opt_in(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "logs-foo").mkdir()
            (root / "logs-foo" / "day.log").write_text(
                "2025-04-03 12:00:00.000 ERR RISK: Halted test old incident\n"
                "2026-11-21 14:55:00.000 ERR RISK: Halted test recent incident\n",
                encoding="utf-8",
            )
            output = root / "reports" / "all"
            result = run(root, output, with_market=False)
            self.assertNotIn("incident", result["reports"])
            import json
            import csv
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["history_scope"]["mode"], "all")
            with (output / "history" / "incident_timeline.csv").open(
                    encoding="utf-8", newline="") as f:
                events = list(csv.DictReader(f))
            self.assertEqual(len(events), 2)
            self.assertEqual([row["at_msk"][:4] for row in events], ["2025", "2026"])

    def test_invalid_partial_focus_and_incident_are_rejected_before_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "reports" / "invalid"
            with self.assertRaises(ValueError):
                run(root, output, False, focus_start="2026-11-21T00:00:00")
            with self.assertRaises(ValueError):
                run(root, output, False, focus_start="2026-11-22T00:00:00",
                    focus_end="2026-11-21T00:00:00")
            with self.assertRaises(ValueError):
                run(root, output, False, incident_state="state-foo")
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
