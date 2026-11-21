"""Only invented strategy histories and invented fills, never user trading data."""
from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from fills_by_epoch import run, run_analysis


class BookedEpochTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / "state-fake"
        self.logs = self.root / "logs-fake"
        self.state.mkdir()
        self.logs.mkdir()

    def setup_data(self):
        (self.logs / "babid01-20261121.log").write_text(
            "2026-11-21 14:00:00.000 INF Engine started: regime=On; maxPositionLots=4; buy=1@level>=10; sell=1@level>=10\n"
            "2026-11-21 14:00:00.100 INF Risk: maxDailyLoss=1000; positionCheck=30s/Halt\n"
            "2026-11-21 14:10:00.000 INF Config applied: regime=On; maxPositionLots=4; buy=1@level>=20; sell=1@level>=20 | maxDailyLoss=1000; positionCheck=30s/Halt | commission estimate=0.05%\n"
            "2026-11-21 14:20:00.000 INF P&L at stop: total=5\n"
            "2026-11-21 15:00:00.000 INF Engine started: regime=On; maxPositionLots=8; buy=2@level>=40; sell=2@level>=40\n"
            "2026-11-21 15:01:00.000 INF P&L at start: total=10\n",
            encoding="utf-8")
        header = "time_msk;exchange_id;trade_id;side;kind;lots;realized;fee_estimate;synthetic\n"
        trades = [
            ("14:05:00.000", "Buy", "open", 0, "0.10"),
            ("14:15:00.000", "Sell", "close", 5, "0.10"),
            ("14:30:00.000", "Buy", "open", 0, "0"),
            ("15:00:00.000", "Buy", "open", 0, "0"),
            ("15:00:30.000", "Sell", "close", 2, "0.10"),
            ("16:00:00.000", "Sell", "close", 3, "0.10"),
        ]
        (self.state / "fills.csv").write_text(header + "".join(
            f"2026-11-21 {t};exchange;trade{i};{side};{kind};1;{realized};{fee};0\n"
            for i, (t, side, kind, realized, fee) in enumerate(trades)), encoding="utf-8")

    def test_conservative_attribution_and_unknown_gaps(self):
        self.setup_data()
        rows, summary = run_analysis(self.root, "state-fake", "logs-fake")
        self.assertEqual(summary["total_fills"], 6)
        self.assertEqual(summary["unknown_fills"], 3)
        groups = {row["group_id"]: row for row in rows}
        config = next(row for row in rows if row["event_kind"] == "config_applied")
        self.assertEqual(config["gross_realized"], "5")
        self.assertEqual(config["net_realized_after_estimated_fees"], "4.90")
        self.assertEqual(groups["unknown_after_observed_stop"]["fills"], 2)
        self.assertEqual(groups["unknown_after_last_log_event"]["fills"], 1)
        self.assertNotIn("unknown_before_first_setting", groups)
        self.assertEqual(groups["epoch_3"]["gross_realized"], "2")

    def test_report_does_not_overwrite_source(self):
        self.setup_data()
        out = self.root / "reports" / "epoch-study"
        summary = run(self.root, out, "state-fake", "logs-fake")
        self.assertEqual(summary["setting_epochs"], 4)
        with (out / "booked_fills_by_epoch.csv").open(newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(sum(int(row["fills"]) for row in rows), 6)
        with self.assertRaises(ValueError):
            run(self.root, out, "state-fake", "logs-fake")
        self.assertIn("14:20:00.000", (self.logs / "babid01-20261121.log").read_text())

    def test_strict_scoped_paths(self):
        self.setup_data()
        with self.assertRaises(ValueError):
            run_analysis(self.root, "../state-fake", "logs-fake")
        with self.assertRaises(ValueError):
            run_analysis(self.root, "state-fake", "../../logs-fake")


if __name__ == "__main__":
    unittest.main()
