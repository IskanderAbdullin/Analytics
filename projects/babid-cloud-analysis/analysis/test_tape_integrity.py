"""Synthetic recorder-integrity tests: no broker, repository or real trading data."""
from __future__ import annotations

import csv
import gzip
import tempfile
import unittest
from pathlib import Path

from tape_integrity import good_book, run, summarize


class TapeIntegrityTests(unittest.TestCase):
    def test_book_validation(self):
        self.assertTrue(good_book("100@2;99@20", "101@3;102@2"))
        self.assertFalse(good_book("100@2;101@20", "102@1"))
        self.assertFalse(good_book("100@2", "100@3"))
        self.assertFalse(good_book("100@2", "99@3"))
        self.assertFalse(good_book("100@-1", "101@1"))
        self.assertFalse(good_book("nan@1", "101@1"))
        self.assertFalse(good_book("", "101@1"))

    def test_received_vs_exchange_clock_and_gap_quality(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / "recordings" / "FAKE"
            folder.mkdir(parents=True)
            p = folder / "FAKE_2026-11-21.tsv.gz"
            with gzip.open(p, "wt", encoding="utf-8") as target:
                target.write("# babid01 market recording v1\n")
                target.write('I\t{"Ticker":"FAKE","PriceStep":1}\n')
                target.write("S\t100000\tNormalTrading\t1\t1\n")
                target.write("B\t100000\t99900\t100@1\t102@2\t\t\n")
                target.write("B\t100100\t99700\t101@2\t103@2\t\t\n")
                target.write("D\t101000\tstream down\n")
                target.write("G\t101050\t98000\t101\t1\tB\n")
                target.write("U\t104000\n")
                target.write("B\t104050\t104075\t99@2\t103@2\t\t\n")  # clock skew
                target.write("B\t104060\t104050\t105@2\t103@2\t\t\n")  # crossed
                target.write("T\t104070\t104065\t103\t2\tS\n")
            stats = summarize(p)
            self.assertEqual(stats["books"], 4)
            self.assertEqual(stats["invalid_books"], 1)
            self.assertEqual(stats["trades"], 1)
            self.assertEqual(stats["gap_trades"], 1)
            self.assertEqual(stats["known_outage_seconds"], 3)
            self.assertEqual(stats["negative_exchange_age"], 1)
            self.assertEqual(stats["exchange_age_gt_500ms"], 0)
            self.assertFalse(stats["open_outage"])
            report = run(root, root / "reports" / "quality")
            self.assertEqual(report["recordings"], 1)
            with (root / "reports" / "quality" / "tape_quality.csv").open(newline="") as infile:
                self.assertEqual(len(list(csv.DictReader(infile))), 1)
            with self.assertRaises(ValueError):
                run(root, root / "reports" / "quality")

    def test_missing_timestamp_open_outage_and_reversal(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "raw.tsv"
            path.write_text("B\t100000\t0\t100@1\t101@1\n"
                            "B\t99500\t99400\t100@1\t101@1\n"
                            "D\t102000\tbad\n"
                            "D\t103000\trepeated\n", encoding="utf-8")
            result = summarize(path)
            self.assertTrue(result["open_outage"])
            self.assertEqual(result["non_monotonic_receipt"], 1)
            self.assertIn("exchange_timestamp_missing:1", result["error_kinds"])
            self.assertIn("repeated_disconnect:1", result["error_kinds"])

    def test_corrupt_tail_is_recorded_not_interpreted(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "raw.tsv"
            path.write_text("B\t100000\t99900\t100@1\t101@1\n"
                            "B\t100001\t99901\tCORRUPT\t101@1\n"
                            "T\t100002\t99903\t101\tbad\tB\n", encoding="utf-8")
            result = summarize(path)
            self.assertEqual(result["books"], 2)
            self.assertEqual(result["recording_errors"], 1)
            self.assertEqual(result["invalid_books"], 1)


if __name__ == "__main__":
    unittest.main()
