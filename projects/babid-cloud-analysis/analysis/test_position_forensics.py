"""Synthetic regression tests; never call the broker."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from position_forensics import run


class PositionForensicTests(unittest.TestCase):
    def test_two_lot_mismatch_and_recovery_without_automatic_reset(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "state-nvda-iis-live").mkdir()
            (root / "logs-nvda-iis-live").mkdir()
            state = root / "state-nvda-iis-live"
            (state / "fills.csv").write_text(
                "time_msk;order;exchange_id;trade_id;side;kind;price;lots;net_lots;realized\n"
                "2026-11-21 14:49:00.001;41;ex41;t41;Buy;open;100;2;33;0\n"
                "2026-11-21 15:00:00.001;42;ex42;t42;Sell;close;101;2;31;2\n")
            (state / "risk.json").write_text(json.dumps(
                {"Level":"Halted","SinceUtc":"2026-11-21T12:01:47Z",
                 "Reason":"position outside changed from -2 to 0"}))
            (root / "logs-nvda-iis-live" / "run.log").write_text(
                "2026-11-21 14:55:00.001 ERR RISK: Halted — position outside the robot changed from 0 to -2 lots (broker +31, journal +33)\n"
                "2026-11-21 14:55:14.001 INF Risk manager: stop lifted from the window\n"
                "2026-11-21 15:01:47.001 ERR RISK: Halted — position outside the robot changed from -2 to 0 lots (broker 0, journal 0)\n")
            result = run(root, "state-nvda-iis-live", "logs-nvda-iis-live",
                         "2026-11-21 14:40:00", "2026-11-21 15:10:00",
                         root / "reports" / "nvda")
            self.assertEqual(result["fill_rows"], 2)
            self.assertEqual(result["position_check_events"], 2)
            self.assertEqual(result["risk_snapshot"]["level"], "Halted")
            with (root / "reports" / "nvda" / "broker_journal_checks.csv").open(newline="") as f:
                checks = list(csv.DictReader(f))
            self.assertEqual(checks[0]["broker_lots"], "+31")
            self.assertEqual(checks[0]["journal_lots"], "+33")
            self.assertEqual(checks[1]["new_external"], "0")
            with self.assertRaises(ValueError):
                run(root, "state-nvda-iis-live", "logs-nvda-iis-live",
                    "2026-11-21 14:40:00", "2026-11-21 15:10:00",
                    root / "reports" / "nvda")


if __name__ == "__main__":
    unittest.main()
