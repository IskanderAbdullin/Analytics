"""Synthetic offline tests for market_study; no network or live broker."""
import csv
import gzip
import tempfile
import unittest
from pathlib import Path
from market_study import levels, quote, run, scan


class MarketStudyTests(unittest.TestCase):
    def test_quote_feasibility(self):
        bids, asks = levels("100@2;99@20"), levels("104@3;105@30")
        self.assertEqual(quote(bids, asks, 1.0, 10), (True, True, 4.0, 4.0))
        self.assertEqual(quote(bids, asks, 1.0, 100), (False, False, 0.0, 0.0))
        self.assertEqual(quote(levels("100@20"), levels("101@20"), 1, 10),
                         (False, False, 0.0, 0.0))

    def test_gzip_gap_accounting(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / "recordings" / "FAKE"
            folder.mkdir(parents=True)
            file = folder / "FAKE_2026-11-21.tsv.gz"
            with gzip.open(file, "wt") as out:
                out.write('# babid01 market recording v1\n')
                out.write('I\t{"Ticker":"FAKE","PriceStep":1}\n')
                out.write('B\t1795167000000\t1795167000000\t100@5;99@50\t104@5;105@50\t\t\n')
                out.write('T\t1795167000100\t1795167000100\t103\t3\tB\n')
                out.write('D\t1795167001000\tdown\n')
                out.write('G\t1795167001500\t1795167001500\t101\t2\tS\n')
                out.write('U\t1795167004000\n')
            rows, quality = scan(file, (5, 50))
            self.assertEqual(quality["known_outage_seconds"], 3)
            self.assertEqual(quality["gap_trades"], 1)
            self.assertEqual(len(rows), 2)
            report = run(root, root / "reports" / "market", (5, 50), None)
            self.assertEqual(report["books"], 1)
            with self.assertRaises(ValueError):
                run(root, root / "reports" / "market", (5, 50), None)


if __name__ == "__main__":
    unittest.main()
