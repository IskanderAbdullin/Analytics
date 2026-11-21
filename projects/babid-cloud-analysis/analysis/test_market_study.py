"""Synthetic offline tests for market_study; no network or live broker."""
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

    def test_duplicate_tsv_variants_cannot_create_opportunity(self):
        import csv
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / "recordings" / "FAKE"
            folder.mkdir(parents=True)
            raw = folder / "FAKE_2026-11-21.tsv"
            body = ('I\t{"Ticker":"FAKE","PriceStep":1}\n'
                    'B\t1795167000000\t1795167000000\t100@5\t102@5\t\t\n')
            raw.write_text(body, encoding="utf-8")
            with gzip.open(folder / (raw.name + ".gz"), "wt") as zipped:
                zipped.write(body)
            result = run(root, root / "reports" / "market", (5,), None)
            self.assertEqual(result["files"], 0)
            self.assertEqual(result["rejected_recordings"], 2)
            with (root / "reports" / "market" / "opportunities.csv").open(newline="") as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 0)

    def test_invalid_book_and_feed_outage_do_not_become_opportunities(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "recordings" / "FAKE"
            folder.mkdir(parents=True)
            path = folder / "FAKE_2026-11-21.tsv"
            path.write_text(
                'I\t{"Ticker":"FAKE","PriceStep":1}\n'
                'B\t1795167000000\t1795167000000\t100@5\t103@5\t\t\n'
                'B\t1795167000100\t1795167000100\t100@5;101@5\t103@5\t\t\n'
                'D\t1795167000500\tdown\n'
                'B\t1795167000600\t1795167000600\t100@5\t103@5\t\t\n'
                'U\t1795167002000\n'
                'B\t1795167002100\t1795167002100\tnan@5\t103@5\t\t\n',
                encoding="utf-8")
            rows, quality = scan(path, (5,))
            self.assertEqual(quality["books"], 4)
            self.assertEqual(quality["valid_books"], 1)
            self.assertEqual(quality["invalid_books"], 3)
            self.assertIn("malformed or crossed order book", quality["issues"])
            self.assertIn("book during known feed outage", quality["issues"])
            self.assertEqual(rows[0]["books"], 1)

    def test_nonfinite_price_step_blocks_all_book_opportunities(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "recordings" / "FAKE"
            folder.mkdir(parents=True)
            path = folder / "FAKE_2026-11-21.tsv"
            path.write_text(
                'I\t{"Ticker":"FAKE","PriceStep":"NaN"}\n'
                'B\t1795167000000\t1795167000000\t100@5\t103@5\t\t\n',
                encoding="utf-8")
            rows, quality = scan(path, (5,))
            self.assertEqual(rows, [])
            self.assertEqual(quality["valid_books"], 0)
            self.assertIn("nonfinite or missing price step", quality["issues"])


if __name__ == "__main__":
    unittest.main()
