"""Synthetic lossless accounting checks. No brokerage API or live robot."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from reconcile_fills import run

HEADER = ("time_msk;order;exchange_id;trade_id;side;kind;price;lots;fee_estimate;"
          "realized;net_lots;avg_price;realized_total;fees_total;synthetic\n")


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root = Path(self.t.name)
        self.state = self.root / "state-nvda"
        self.state.mkdir()
        self.journal = self.state / "journal.json"
        self.fills = self.state / "fills.csv"

    def write(self, rows, **pnl):
        self.fills.write_text(HEADER + "".join(rows), encoding="utf-8")
        defaults = dict(Realized=2.5, Fees=0, FillCount=2, LotsTraded=2,
                        NetLots=0, Day="2026-11-21")
        defaults.update(pnl)
        self.journal.write_text(json.dumps(dict(Mode="live",AccountId="SECRET-123",Pnl=defaults)), encoding="utf-8")

    def rows(self):
        return [
            "2026-11-21 14:50:00;1;ex1;tr1;Buy;open;100;1;0;0;1;100;0;0;0\n",
            "2026-11-21 14:51:00;2;ex2;tr2;Sell;close;102.5;1;0;2.5;0;0;2.5;0;0\n",
        ]

    def report(self):
        result = run(self.root, self.root / "reports" / "one")
        with (self.root / "reports" / "one" / "reconciliation.csv").open(newline="", encoding="utf-8") as f:
            record = next(csv.DictReader(f))
        return result, record

    def test_consistent_snapshots_and_redaction(self):
        self.write(self.rows())
        summary, row = self.report()
        self.assertEqual(summary["local_journal_matches"], 1)
        self.assertEqual(row["status"], "matches_local_journal")
        self.assertNotIn("SECRET-123", str(row))
        with self.assertRaises(ValueError):
            run(self.root, self.root / "reports" / "one")

    def test_duplicate_and_two_lot_discontinuity(self):
        rows = self.rows()
        rows[1] = rows[1].replace("ex2;tr2", "ex1;tr1").replace(";0;0;2.5;0;0", ";-2;0;2.5;0;0")
        self.write(rows, NetLots=-2)
        summary, row = self.report()
        self.assertEqual(summary["needs_review"], 1)
        self.assertIn("duplicates", row["flags"])
        self.assertIn("continuity_gaps", row["flags"])

    def test_journal_mismatch_and_decimal_precision(self):
        self.write(self.rows(), Realized="2.5000000001", FillCount=3)
        summary, row = self.report()
        self.assertEqual(summary["needs_review"], 1)
        self.assertIn("journal_diff_realized", row["flags"])
        self.assertIn("journal_diff_fill_count", row["flags"])

    def test_empty_fills_cannot_claim_local_match(self):
        self.write([], FillCount=0, LotsTraded=0, NetLots=0, Realized=0)
        summary, row = self.report()
        self.assertEqual(summary["needs_review"], 1)
        self.assertIn("empty_fills", row["flags"])

    def test_missing_pnl_object_is_incomplete(self):
        self.fills.write_text(HEADER + "".join(self.rows()))
        self.journal.write_text(json.dumps({"Mode": "live"}))
        summary, row = self.report()
        self.assertEqual(summary["incomplete_or_unverified"], 1)
        self.assertEqual(row["status"], "incomplete")
        self.assertIn("missing required Pnl", row["flags"])

    def test_rejects_writing_inside_live_state(self):
        self.write(self.rows())
        with self.assertRaises(ValueError):
            run(self.root, self.state / "reports")

    def test_missing_fills_report_incomplete(self):
        self.journal.write_text('{}', encoding='utf-8')
        summary, row = self.report()
        self.assertEqual(summary["incomplete_or_unverified"], 1)
        self.assertEqual(row["status"], "incomplete")


if __name__ == '__main__':
    unittest.main()
