"""Synthetic research checkpoint validator tests; no user files/broker access."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from research_state import REQUIRED_FILES, check, next_action


class ResearchStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        original = Path(__file__).resolve().parents[1]
        for name in REQUIRED_FILES:
            (self.root / name).write_text(
                (original / name).read_text(encoding="utf-8"), encoding="utf-8")

    def change(self, filename, change):
        path = self.root / filename
        data = json.loads(path.read_text(encoding="utf-8"))
        change(data)
        path.write_text(json.dumps(data), encoding="utf-8")

    def test_committed_checkpoint_is_valid(self):
        self.assertEqual(check(self.root), [])

    def test_next_command_does_not_execute_or_mutate(self):
        before = (self.root / "STATE.json").read_bytes()
        line = next_action(self.root)
        self.assertIn("A-001 [blocked_external]", line)
        self.assertIn(json.loads((self.root / "NEXT_ACTION.json").read_text())["next_command"], line)
        self.assertEqual(before, (self.root / "STATE.json").read_bytes())

    def test_mismatched_action_pointer_fails(self):
        self.change("STATE.json", lambda x: x.update(current_action_id="A-999"))
        self.assertTrue(any("current_action_id" in e for e in check(self.root)))

    def test_unverified_evidence_reference_fails(self):
        self.change("STATE.json", lambda x: x["evidence_refs"].append("E-999"))
        self.assertTrue(any("unknown state evidence" in e for e in check(self.root)))

    def test_unproven_hypothesis_cannot_be_confirmed(self):
        self.change("STATE.json", lambda x: x["hypotheses"][0].update(status="confirmed"))
        self.assertTrue(any("needs evidence" in e for e in check(self.root)))

    def test_unresolved_goal_cannot_be_marked_completed(self):
        self.change("STATE.json", lambda x: x.update(goal_status="completed"))
        self.assertTrue(any("completed" in e for e in check(self.root)))

    def test_blocked_external_must_name_its_blocker(self):
        self.change("NEXT_ACTION.json", lambda x: x.update(blockers=[]))
        self.assertTrue(any("requires documented blockers" in e for e in check(self.root)))

    def test_no_ci_permission_for_private_data_action(self):
        self.change("NEXT_ACTION.json", lambda x: x.update(public_ci_allowed=True))
        self.assertTrue(any("public CI" in e for e in check(self.root)))

    def test_missing_file_is_reported(self):
        (self.root / "BACKLOG.md").unlink()
        self.assertTrue(any("BACKLOG.md" in e for e in check(self.root)))


if __name__ == "__main__":
    unittest.main()
