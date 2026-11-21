"""Time-weighted recorder geometry tests use fabricated streams."""
from __future__ import annotations

import csv
import gzip
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from time_weighted_books import run, scan


class WeightedBooksTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = self.root / "recordings" / "FAKE"
        self.folder.mkdir(parents=True)
        tz = timezone(timedelta(hours=3))
        self.t = int(datetime(2026, 11, 21, 14, 0, 0, tzinfo=tz).timestamp() * 1000)

    def tape(self, *rows):
        p = self.folder / "FAKE_2026-11-21.tsv.gz"
        with gzip.open(p, "wt", encoding="utf-8") as f:
            f.write('I\t{"Ticker":"FAKE","PriceStep":1}\n')
            f.writelines(rows)
        return p

    def b(self, offset, bid=100, ask=102):
        ts = self.t + offset
        return f"B\t{ts}\t{ts}\t{bid}@10\t{ask}@10\t\t\n"

    def tline(self, offset):
        ts = self.t + offset
        return f"T\t{ts}\t{ts}\t101\t1\tB\n"

    def test_ttl_capping_sparse_books_and_resets(self):
        file = self.tape(
            self.b(0), self.tline(1000), self.tline(3000),
            f"D\t{self.t + 4000}\tdown\n",
            f"U\t{self.t + 6000}\n",
            self.b(6100), self.tline(7100))
        rows, quality = scan(file, (10, 20), ttl_ms=2000)
        a = next(x for x in rows if x["min_level_lots"] == 10)
        b = next(x for x in rows if x["min_level_lots"] == 20)
        self.assertEqual(a["observed_ms"], 7100)
        self.assertEqual(a["covered_ms"], 3000)  # first 2s, then 1s
        self.assertEqual(a["buy_geometry_ms"], 3000)
        self.assertEqual(a["sell_geometry_ms"], 3000)
        self.assertEqual(b["covered_ms"], 3000)
        self.assertEqual(b["buy_geometry_ms"], 0)
        self.assertEqual(quality["resets"], 2)

    def test_book_count_is_not_duration_and_no_forward_extrapolation(self):
        path = self.tape(self.b(0), self.tline(10000))
        rows, _ = scan(path, (10,), ttl_ms=2000)
        self.assertEqual(rows[0]["observed_ms"], 10000)
        self.assertEqual(rows[0]["covered_ms"], 2000)
        self.assertEqual(rows[0]["coverage_share"], 0.2)

    def test_hour_boundary_split(self):
        t = self.t + 3599000
        path = self.tape(f"B\t{t}\t{t}\t100@10\t102@10\t\t\n",
                         f"T\t{t + 2000}\t{t + 2000}\t101\t1\tB\n")
        rows, _ = scan(path, (10,), ttl_ms=2000)
        self.assertEqual(len(rows), 2)
        self.assertEqual(sum(x["covered_ms"] for x in rows), 2000)
        self.assertEqual({x["hour_msk"] for x in rows}, {"14", "15"})

    def test_reject_backward_time_and_no_overwrite(self):
        path = self.tape(self.b(5000), self.b(1000))
        with self.assertRaises(ValueError):
            scan(path, (10,))
        result = run(self.root, self.root / "reports" / "scan", 2000, (10,))
        self.assertEqual(result["rejected_recordings"], 1)
        with (self.root / "reports" / "scan" / "time_weighted_geometry.csv").open(newline="") as f:
            self.assertEqual(len(list(csv.DictReader(f))), 0)
        with self.assertRaises(ValueError):
            run(self.root, self.root / "reports" / "scan", 2000, (10,))


if __name__ == "__main__":
    unittest.main()
