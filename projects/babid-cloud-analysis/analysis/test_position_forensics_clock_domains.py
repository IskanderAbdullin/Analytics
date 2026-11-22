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


    def test_bounded_execution_lookback_does_not_claim_arrival_time(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state, logs = root / "synthetic-state", root / "synthetic-logs"
            state.mkdir()
            logs.mkdir()
            (state / "fills.csv").write_text(
                "time_msk;order;exchange_id;trade_id;side;kind;price;lots;net_lots;realized\n"
                "2026-01-01 10:00:30.000;7;fiction;demo;Sell;open;99;2;8;0\n",
                encoding="utf-8",
            )
            (logs / "robot.log").write_text(
                "2026-01-01 10:01:10.000 TRD FILL Sell 2 @ 99; order=7 (open)\n",
                encoding="utf-8",
            )
            common = (root, "synthetic-state", "synthetic-logs",
                      "2026-01-01 10:01:00", "2026-01-01 10:01:30")
            without = run(*common, root / "reports" / "without")
            self.assertEqual(without["fill_rows"], 0)
            self.assertEqual(without["log_events"], 1)
            with_lookback = run(
                *common, root / "reports" / "with",
                execution_lookback_sec=60,
            )
            self.assertEqual(with_lookback["fill_rows"], 1)
            self.assertEqual(with_lookback["selected_prior_execution_rows"], 1)
            self.assertEqual(with_lookback["execution_lookback_seconds"], 60)
            self.assertEqual(with_lookback["cross_clock_temporal_causality"], "not_inferred")
            with (root / "reports" / "with" / "incident_evidence.csv").open(
                newline="", encoding="utf-8"
            ) as stream:
                rows = list(csv.DictReader(stream))
            early = next(row for row in rows if row["source"] == "fills.csv")
            self.assertEqual(early["execution_lookback"], "True")
            self.assertEqual(early["clock_domain"], "broker_reported_execution")
            with self.assertRaises(ValueError):
                run(*common, root / "reports" / "invalid",
                    execution_lookback_sec=-1)
            self.assertFalse((root / "reports" / "invalid").exists())

if __name__ == "__main__":
    unittest.main()
