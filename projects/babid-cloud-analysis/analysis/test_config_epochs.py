"""Historical setting timeline fixtures from the documented logger format."""
from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from config_epochs import extract, reconstruct, run


class ConfigEpochTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.logs = self.root / "logs-nvda"
        self.logs.mkdir()
        self.log = self.logs / "babid01-20261121.log"

    def write(self):
        self.log.write_text(
            "2026-11-21 14:00:00.000 INF Engine started: regime=On; refreshMs=auto; depthTimeoutMs=0; maxPositionLots=80; buy=40@level>=120; sell=40@level>=120\n"
            "2026-11-21 14:00:00.001 INF Risk: maxDailyLoss=1000; maxDailyLossPercent=0; action=Halt; autoResumeNextDay=False; maxRejectsPerHour=20; positionCheck=30s/Halt\n"
            "2026-11-21 14:20:00.000 INF Config applied: regime=On; maxPositionLots=80; buy=40@level>=100; sell=40@level>=100 | maxDailyLoss=1000; positionCheck=30s/Halt | commission estimate=0.05% | requote by ReplaceOrder\n"
            "2026-11-21 14:30:00.000 INF Schedule 14:30 MSK: regime CloseOnly, position limit 40 and orders 20/20 lot(s) (x0.5 of 80 and 40/40).\n"
            "2026-11-21 14:31:00.000 ERR Config reload failed, the previous settings stay in force: malformed JSON\n"
            "2026-11-21 14:32:00.000 INF Schedule: the regime was changed by hand to On; it holds until the next item of the schedule.\n",
            encoding="utf-8")

    def test_derive_only_logged_settings_and_timeline(self):
        self.write()
        rows, issues = reconstruct(self.logs)
        self.assertEqual(len(rows), 5)
        self.assertEqual(len(issues), 1)
        self.assertEqual(rows[0]["event_kind"], "engine_started")
        self.assertEqual(rows[0]["max_position_lots"], "80")
        self.assertEqual(rows[0]["end_msk"], "2026-11-21 14:00:00.001")
        self.assertEqual(rows[1]["position_check_sec"], "30")
        self.assertEqual(rows[2]["buy_min_level_lots"], "100")
        self.assertEqual(rows[2]["replace_order"], "true")
        self.assertEqual(rows[2]["end_msk"], "2026-11-21 14:30:00.000")
        self.assertEqual(rows[3]["regime"], "CloseOnly")
        self.assertEqual(rows[3]["max_position_lots"], "40")
        self.assertEqual(rows[4]["regime"], "On")
        self.assertEqual(rows[4]["confidence"], "schedule_partial")

    def test_ignore_identity_change_warnings_and_no_secret_export(self):
        self.write()
        with self.log.open("a", encoding="utf-8") as log:
            log.write("2026-11-21 14:33:00.000 WRN Config: mode, account and instrument changes need a restart and were ignored.\n")
        output = self.root / "reports" / "epochs"
        result = run(self.root, output)
        self.assertEqual(result["observed_epochs"], 5)
        self.assertEqual(result["warning_events"], 2)
        file = (output / "settings_epochs.csv").read_text()
        self.assertNotIn("malformed JSON", file)
        with self.assertRaises(ValueError):
            run(self.root, output)

    def test_short_schedules_and_startup_restart_do_not_invent_values(self):
        self.log.write_text(
            "2026-11-21 14:00:00.000 INF Schedule 14:00 MSK: regime On.\n"
            "2026-11-21 14:01:00.000 INF Engine started: regime=On; maxPositionLots=1; buy=1@level>=1; sell=1@level>=1\n",
            encoding="utf-8")
        rows, _ = reconstruct(self.logs)
        self.assertEqual(rows[0]["regime"], "On")
        self.assertEqual(rows[0]["max_position_lots"], "")
        self.assertEqual(rows[1]["max_position_lots"], "1")
        self.assertEqual(rows[1]["position_check_sec"], "")

    def test_close_no_loss_and_without_short_detection(self):
        part = extract("regime=On; buy=2@level>=4; sell=2@level>=5; closing@level>=20 when not at a loss",
                       "config_applied")
        self.assertEqual(part["close_no_loss"], "true")
        self.assertEqual(part["closing_level_lots"], "20")


if __name__ == "__main__":
    unittest.main()
