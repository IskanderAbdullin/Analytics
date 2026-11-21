"""Offline tests for the read-only audit; no broker, live config or network."""
import csv
import gzip
import json
import tempfile
import unittest
from pathlib import Path

from audit_history import read_jsonc, run


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "state-foo").mkdir()
        (self.root / "logs-foo").mkdir()
        (self.root / "recordings" / "FOO").mkdir(parents=True)
        (self.root / "config.foo.json").write_text(
            '{ // comment\n "mode":"live","tokenFile":"C://not-a-token",'
            '"accountId":"SECRET","instrument":{"ticker":"FOO"},'
            '"stateDir":"state-foo","logDir":"logs-foo",'
            '"strategy":{"buyMinLevelLots":3},}', encoding="utf-8"
        )
        (self.root / "state-foo" / "journal.json").write_text(json.dumps({
            "Mode": "live", "AccountId": "SECRET", "ExternalLots": -2,
            "Pnl": {"NetLots": 33, "Realized": 12, "FillCount": 2, "Day": "2026-11-21"}
        }), encoding="utf-8")
        (self.root / "state-foo" / "fills.csv").write_text(
            "time_msk;order;exchange_id;trade_id;side;kind;price;lots;fee_estimate;realized;net_lots;synthetic\n"
            "2026-11-21 14:51:00.001;1;a;t1;Buy;open;50;1;0;0;1;0\n"
            "2026-11-21 14:52:00.001;1;a;t1;Buy;open;50;1;0;0;1;0\n"
            "2026-11-21 14:54:00.001;2;b;t2;Sell;close;51;1;0;1;0;1\n",
            encoding="utf-8")
        msk = "2026-11-21 14:55:00"
        (self.root / "logs-foo" / "day.log").write_text(
            f"{msk}.000 WRN Position check: position outside the robot changed from 0 to -2 lots\n"
            "2026-11-21 15:01:47.000 ERR RISK: Halted — position outside the robot changed from -2 to 0 lots\n"
            "2026-11-21 15:02:10.000 ERR 30049 Replace failed\n",
            encoding="utf-8")
        rows = [(1795260000000, 12), (1795260010000, 10),
                (1795260020000, 14)]
        (self.root / "state-foo" / "pnl-curve.csv").write_text(
            "".join(f"{ts};{value}\n" for ts, value in rows), encoding="utf-8")
        with gzip.open(self.root / "recordings" / "FOO" / "FOO_2026-11-21.tsv.gz", "wt") as out:
            out.write("B\t2026-11-21T14:55\nG\t2026-11-21T14:56\n")

    def test_jsonc_keeps_strings_and_trailing_comma(self):
        # Literal C:// must not be accidentally removed as a comment.
        conf = read_jsonc(self.root / "config.foo.json")
        self.assertEqual(conf["tokenFile"], "C://not-a-token")

    def test_reports_fills_errors_and_privacy(self):
        output = self.root / "reports" / "audit-1"
        result = run(self.root, output, "2026-11-21T14:40:00", "2026-11-21T15:10:00")
        self.assertEqual(result["states"], 1)
        self.assertEqual(result["days_with_fills"], 1)
        with (output / "fills_daily.csv").open(newline="", encoding="utf-8") as f:
            row = next(csv.DictReader(f))
        self.assertEqual(row["fills"], "3")
        self.assertEqual(row["duplicate_trade_ids"], "1")
        self.assertEqual(row["synthetic"], "1")
        with (output / "incident_timeline.csv").open(newline="", encoding="utf-8") as f:
            incident = list(csv.DictReader(f))
        self.assertEqual(len(incident), 3)
        self.assertEqual(result["recordings"], 1)
        self.assertNotIn("SECRET", (output / "configs.csv").read_text())
        self.assertNotIn("C://not-a-token", (output / "configs.csv").read_text())

    def test_output_is_never_replaced(self):
        output = self.root / "reports" / "audit-1"
        run(self.root, output, "2026-11-21T14:40:00", "2026-11-21T15:10:00")
        with self.assertRaises(ValueError):
            run(self.root, output, "2026-11-21T14:40:00", "2026-11-21T15:10:00")

    def test_refuses_outside_source(self):
        with self.assertRaises(ValueError):
            run(self.root, self.root.parent / "outside", "", "")


if __name__ == "__main__":
    unittest.main()
