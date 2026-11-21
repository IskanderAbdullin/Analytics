"""End-to-end test: the coordinator must run on a fabricated archive only."""
from __future__ import annotations

import csv
import gzip
import json
import tempfile
import unittest
from pathlib import Path

from run_offline_audit import run


class FullPipelineTests(unittest.TestCase):
    def test_all_studies_on_synthetic_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = root / "state-nvda-iis-live"
            logs = root / "logs-nvda-iis-live"
            recordings = root / "recordings" / "FAKE"
            state.mkdir()
            logs.mkdir()
            recordings.mkdir(parents=True)

            # Artificial identifiers and executions, not real user data.
            (root / "config.fake-live.json").write_text(json.dumps({
                "mode": "paper", "accountId": "FAKE-ACCOUNT",
                "instrument": {"ticker": "FAKE", "classCode": "TEST"},
                "stateDir": "state-nvda-iis-live",
                "logDir": "logs-nvda-iis-live",
                "strategy": {"regime": "Off"},
                "risk": {"positionCheckIntervalSec": 30}
            }), encoding="utf-8")
            (state / "journal.json").write_text(json.dumps({
                "Mode": "paper",
                "AccountId": "FAKE-ACCOUNT",
                "ExternalLots": 0,
                "Pnl": {
                    "Realized": 2, "Fees": 0, "FillCount": 2,
                    "LotsTraded": 2, "NetLots": 0, "Day": "2026-11-21"
                }
            }), encoding="utf-8")
            (state / "risk.json").write_text(json.dumps({"Level": "Normal"}), encoding="utf-8")
            (state / "fills.csv").write_text(
                "time_msk;order;exchange_id;trade_id;side;kind;price;lots;fee_estimate;realized;"
                "net_lots;avg_price;realized_total;fees_total;synthetic\n"
                "2026-11-21 14:50:00;1;exchange;trade1;Buy;open;100;1;0;0;1;100;0;0;0\n"
                "2026-11-21 14:52:00;2;exchange;trade2;Sell;close;102;1;0;2;0;0;2;0;0\n",
                encoding="utf-8")
            (state / "pnl-curve.csv").write_text(
                "1795260000000;0\n1795260060000;2\n", encoding="utf-8")
            (logs / "babid01-20261121.log").write_text(
                "2026-11-21 14:50:00.000 INF State: ready=True\n"
                "2026-11-21 14:52:00.000 INF FILL trade2, 1 lot\n",
                encoding="utf-8")
            with gzip.open(recordings / "FAKE_2026-11-21.tsv.gz", "wt", encoding="utf-8") as out:
                out.write('I\t{"Ticker":"FAKE","PriceStep":1}\n')
                out.write("B\t1795260000000\t1795260000000\t100@5;99@20\t104@5;105@20\t\t\n")
                out.write("T\t1795260000050\t1795260000050\t101\t1\tB\n")

            output = root / "reports" / "complete-audit-synthetic"
            result = run(root, output, with_market=True)
            for section in ("history", "reconciliation", "configs", "market",
                            "opportunity_validation", "nvda"):
                self.assertIn(section, result["reports"], msg=str(result))
                self.assertNotIn(section + "_error", result["reports"])
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertTrue(manifest["input_files_appear_stable"], msg=str(manifest))
            self.assertFalse(manifest["changed_inputs_across_scan"])
            self.assertEqual(manifest["reports"]["reconciliation"]["local_journal_matches"], 1)
            self.assertEqual(manifest["reports"]["market"]["files"], 1)
            self.assertEqual(manifest["reports"]["configs"]["configs"], 1)
            self.assertEqual(manifest["reports"]["nvda"]["fill_rows"], 2)

            # Sensitive configuration and journal identifiers must not leak to
            # the synthesized config inventory.
            inventory = (output / "config-audit" / "config_inventory.csv").read_text()
            self.assertNotIn("FAKE-ACCOUNT", inventory)

            # Original synthetic source data is unchanged by all six passes.
            self.assertEqual(json.loads((state / "journal.json").read_text())["Pnl"]["NetLots"], 0)
            self.assertEqual((logs / "babid01-20261121.log").read_text().count("FILL"), 1)

            # Source archival reports are immutable: never overwrite a prior run.
            with self.assertRaises(ValueError):
                run(root, output, with_market=True)


if __name__ == "__main__":
    unittest.main()
