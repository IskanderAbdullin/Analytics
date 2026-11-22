"""Synthetic regression: exchange time and robot log time must not be merged."""
import csv
from pathlib import Path
import tempfile
import unittest

from position_forensics import run


class ClockDomainTests(unittest.TestCase):
    def test_nonmonotonic_ledger_records_not_causally_resorted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / "synthetic-state"
            logs = root / "synthetic-logs"
            state.mkdir()
            logs.mkdir()
            (state / "fills.csv").write_text(
                "time_msk;order;exchange_id;trade_id;side;kind;price;lots;net_lots;realized\n"
                "2026-11-21 13:07:56.501;41;ex-a;t-a;Buy;open;99;2;36;0\n"
                "2026-11-21 13:07:30.881;42;ex-b;t-b;Sell;open;99;2;34;0\n",
                encoding="utf-8",
            )
            (logs / "run.log").write_text(
                "2026-11-21 13:07:35.907 INF Order 42: Active -> Cancel; filled=0/40; source=Query\n"
                "2026-11-21 13:08:14.192 TRD FILL Sell 2 @ 99; order=42 (open)\n",
                encoding="utf-8",
            )
            summary = run(
                root, "synthetic-state", "synthetic-logs",
                "2026-11-21 13:07:20", "2026-11-21 13:08:30",
                root / "reports" / "synthetic-incident",
            )
            with (root / "reports" / "synthetic-incident" / "incident_evidence.csv").open(
                encoding="utf-8", newline=""
            ) as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 4)
            fills = [r for r in rows if r["source"] == "fills.csv"]
            observed = [r for r in rows if r["source"] == "run.log"]
            self.assertEqual([r["source_sequence"] for r in fills], ["2", "3"])
            self.assertEqual(
                [r["timestamp"] for r in fills],
                ["2026-11-21 13:07:56.501", "2026-11-21 13:07:30.881"],
            )
            self.assertEqual([r["source_sequence"] for r in observed], ["1", "2"])
            self.assertTrue(all(r["clock_domain"] == "broker_reported_execution" for r in fills))
            self.assertTrue(all(r["clock_domain"] == "robot_log_observation" for r in observed))
            self.assertEqual(summary["cross_clock_temporal_causality"], "not_inferred")
            self.assertTrue(summary["source_native_order_preserved"])


if __name__ == "__main__":
    unittest.main()
