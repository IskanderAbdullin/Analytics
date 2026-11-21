"""No-lookahead markout tests use only invented trades and order books."""
from __future__ import annotations

import csv
import gzip
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from execution_markout import analyze, run

MSK = timezone(timedelta(hours=3))
DAY = "2026-11-21"


def stamp(ms):
    return datetime.fromtimestamp(ms / 1000, MSK).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


class MarkoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / "state-fake"
        self.state.mkdir()
        self.folder = self.root / "recordings" / "FAKE"
        self.folder.mkdir(parents=True)
        self.start = int(datetime(2026, 11, 21, 14, tzinfo=MSK).timestamp() * 1000)
        self.fill = self.start + 1000

    def fills(self, rows):
        header = "time_msk;order;exchange_id;trade_id;side;price;lots;synthetic\n"
        data = "".join(f"{stamp(ms)};{i};ex;trade{i};{side};{price};1;{synthetic}\n"
                       for i, (ms, side, price, synthetic) in enumerate(rows, 1))
        (self.state / "fills.csv").write_text(header + data, encoding="utf-8")

    def tape(self, *items):
        path = self.folder / f"FAKE_{DAY}.tsv.gz"
        with gzip.open(path, "wt", encoding="utf-8") as f:
            f.write('I\t{"Ticker":"FAKE","PriceStep":1}\n')
            f.writelines(items)

    def book(self, ms, bid, ask):
        return f"B\t{ms}\t{ms}\t{bid}@5\t{ask}@5\t\t\n"

    def test_markouts_and_stale_horizon(self):
        self.fills([(self.fill, "Buy", "100", "0"),
                    (self.fill + 100, "Sell", "102", "0")])
        self.tape(self.book(self.start, 100, 102),
                  self.book(self.start + 5001, 101, 103),
                  self.book(self.start + 6100, 102, 104),
                  self.book(self.start + 32000, 98, 100))
        rows, s = analyze(self.root, "state-fake", "FAKE", DAY)
        self.assertEqual(s["fills"], 2)
        self.assertEqual(s["entry_valid"], 2)
        self.assertEqual(rows[0]["entry_edge_ticks"], "1")
        self.assertEqual(rows[0]["markout_5s_ticks"], "2")
        self.assertEqual(rows[1]["markout_5s_ticks"], "0")
        self.assertEqual(rows[0]["h30_status"], "stale_or_same_millisecond")
        self.assertEqual(s["h30_valid"], 0)

    def test_equal_timestamp_cannot_use_future_book(self):
        self.fills([(self.fill, "Buy", "100", "0")])
        self.tape(self.book(self.start, 100, 102),
                  self.book(self.fill, 110, 112),
                  self.book(self.fill + 5100, 112, 114))
        rows, _ = analyze(self.root, "state-fake", "FAKE", DAY, max_book_age_ms=7000)
        self.assertEqual(rows[0]["entry_edge_ticks"], "1")
        self.assertEqual(rows[0]["markout_5s_ticks"], "11")

    def test_gap_blocks_future_markout(self):
        self.fills([(self.fill, "Buy", "100", "0")])
        self.tape(self.book(self.start, 100, 102),
                  f"D\t{self.start + 2000}\tdown\n",
                  f"U\t{self.start + 4000}\n",
                  self.book(self.start + 4500, 100, 102),
                  self.book(self.start + 9000, 100, 102))
        rows, _ = analyze(self.root, "state-fake", "FAKE", DAY, max_book_age_ms=7000)
        self.assertEqual(rows[0]["h5_status"], "stream_reset")

    def test_duplicate_fill_and_output_exclusive(self):
        self.fills([(self.fill, "Buy", "100", "0")])
        with (self.state / "fills.csv").open("a", encoding="utf-8") as f:
            f.write(f"{stamp(self.fill)};1;ex;trade1;Buy;100;1;0\n")
        self.tape(self.book(self.start, 100, 102),
                  self.book(self.start + 4000, 100, 102))
        output = self.root / "reports" / "markouts"
        s = run(self.root, output, "state-fake", "FAKE", DAY)
        self.assertEqual(s["invalid_or_duplicate_fills"], 1)
        with (output / "fill_markouts.csv").open(newline="", encoding="utf-8") as f:
            self.assertEqual(len(list(csv.DictReader(f))), 1)
        with self.assertRaises(ValueError):
            run(self.root, output, "state-fake", "FAKE", DAY)

    def test_invalid_state_or_missing_tape(self):
        self.fills([(self.fill, "Buy", "100", "0")])
        self.tape(self.book(self.start, 100, 102))
        with self.assertRaises(ValueError):
            analyze(self.root, "../state-fake", "FAKE", DAY)
        with self.assertRaises(ValueError):
            analyze(self.root, "state-fake", "NVDA", DAY)


if __name__ == "__main__":
    unittest.main()
