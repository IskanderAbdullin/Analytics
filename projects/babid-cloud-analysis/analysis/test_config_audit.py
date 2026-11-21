"""Synthetic Babid configuration analysis: no tokens, broker or live files."""
import csv
import json
import tempfile
import unittest
from pathlib import Path

from config_audit import analyze, identity, run


class ConfigAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def save(self, filename, ticker, state, logs, *, mode="live", account="SECRET", check=30):
        value = {
            "mode": mode, "accountId": account,
            "tokenFile": "SECRET-PATH-DO-NOT-EXPORT",
            "instrument": {"ticker": ticker},
            "stateDir": state, "logDir": logs,
            "risk": {"positionCheckIntervalSec": check}
        }
        (self.root / filename).write_text(json.dumps(value), encoding="utf-8")

    def test_detects_shared_directories_and_duplicate_instrument(self):
        self.save("config.nbis-live.json", "NBISperpA", "state/nbis", "logs/nbis")
        self.save("config.nbis-iis-live.json", "NBISperpA", "state/nbis", "logs/nbis")
        configs, issues = analyze(self.root)
        self.assertEqual(len(configs), 2)
        names = {i["category"] for i in issues}
        self.assertIn("shared_state_dir", names)
        self.assertIn("shared_log_dir", names)
        self.assertIn("same_account_instrument", names)

    def test_flags_misleading_filename_and_disabled_position_check(self):
        self.save("config.nbis-live.json", "ANTperpA", "state-ANT", "logs-ANT", check=0)
        configs, issues = analyze(self.root)
        names = {i["category"] for i in issues}
        self.assertIn("filename_ticker_mismatch", names)
        self.assertIn("position_check_disabled", names)

    def test_ignores_templates_for_state_collisions(self):
        self.save("config.example.json", "SBER", "state", "logs", account="")
        self.save("config.sber-live.json", "SBER", "state", "logs", account="")
        _, issues = analyze(self.root)
        self.assertNotIn("shared_state_dir", {i["category"] for i in issues})

    def test_reports_never_expose_account_or_tokenfile(self):
        self.save("config.nbis-live.json", "NBISperpA",
                  "C:/Users/private-user/state-NBIS", "C:/Users/private-user/log-NBIS")
        result = run(self.root, self.root / "reports" / "config-audit")
        self.assertEqual(result["configs"], 1)
        body = (self.root / "reports" / "config-audit" / "config_inventory.csv").read_text()
        self.assertNotIn("SECRET-PATH", body)
        self.assertNotIn("private-user", body)
        self.assertNotIn("SECRET", body)
        with self.assertRaises(ValueError):
            run(self.root, self.root / "reports" / "config-audit")

    def test_handles_invalid_and_windows_paths(self):
        (self.root / "config.bad.json").write_text('{ "mode": ', encoding="utf-8")
        configs, issues = analyze(self.root)
        self.assertEqual(configs, [])
        self.assertEqual(issues[0]["category"], "invalid_config")
        self.assertEqual(identity(self.root, "C:\\Users\\foo\\state").lower(),
                         "c:/users/foo/state")

    def test_relative_paths_normalize(self):
        self.assertEqual(identity(self.root, "./state/../state"), identity(self.root, "state"))


if __name__ == "__main__":
    unittest.main()
