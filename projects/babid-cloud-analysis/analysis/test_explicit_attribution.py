"""Coordinator explicit attribution is opt-in, never inferred from latest config."""
from __future__ import annotations

import csv
import gzip
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from run_offline_audit import run

MSK = timezone(timedelta(hours=3))


class OptInAttributionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_partial_identity_arguments_refused_before_output(self):
        folder = self.root / "reports" / "partial"
        with self.assertRaises(ValueError):
            run(self.root, folder, False, epoch_state="state-fake")
        with self.assertRaises(ValueError):
            run(self.root, folder, False, markout_state="state-fake", markout_day="2026-11-21")
        self.assertFalse(folder.exists())

    def test_opt_in_is_analyzed_but_not_certified(self):
        state = self.root / "state-fake"
        logs = self.root / "logs-fake"
        tape_dir = self.root / "recordings" / "FAKE"
        for folder in (state, logs, tape_dir):
            folder.mkdir(parents=True)
        day = "2026-11-21"
        at = datetime(2026, 11, 21, 14, 0, tzinfo=MSK)
        ms = int(at.timestamp() * 1000)
        (state / "fills.csv").write_text(
            "time_msk;order;exchange_id;trade_id;side;kind;lots;price;synthetic;realized;fee_estimate\n"
            "2026-11-21 14:00:01.000;1;ex;t1;Buy;open;1;100;0;0;0.1\n",
            encoding="utf-8")
        (logs / "day.log").write_text(
            "2026-11-21 14:00:00.000 INF Engine started: regime=On; maxPositionLots=1; buy=1@level>=1; sell=1@level>=1\n"
            "2026-11-21 14:00:10.000 INF P&L at start: total=0\n",
            encoding="utf-8")
        with gzip.open(tape_dir / f"FAKE_{day}.tsv.gz", "wt") as out:
            out.write('I\t{"Ticker":"FAKE","PriceStep":1}\n')
            out.write(f"B\t{ms}\t{ms}\t100@2\t102@2\t\t\n")
            out.write(f"T\t{ms + 7000}\t{ms + 7000}\t101\t1\tB\n")
        output = self.root / "reports" / "all"
        result = run(self.root, output, with_market=False,
                     epoch_state="state-fake", epoch_logs="logs-fake",
                     markout_state="state-fake", markout_instrument="FAKE",
                     markout_day=day)
        self.assertIn("epoch_attribution", result["reports"])
        self.assertIn("markout", result["reports"])
        with (output / "epoch-attribution" / "booked_fills_by_epoch.csv").open(newline="") as f:
            self.assertEqual(sum(int(r["fills"]) for r in csv.DictReader(f)), 1)
        report = json.loads((output / "quality_gate.json").read_text())
        self.assertFalse(report["safe_for_automatic_live_tuning"])
        self.assertEqual((state / "fills.csv").read_text().count("t1"), 1)


if __name__ == "__main__":
    unittest.main()
