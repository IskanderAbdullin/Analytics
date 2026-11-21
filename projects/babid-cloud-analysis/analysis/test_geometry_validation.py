"""Synthetic time-weighted held-out-day validations, no user trading files."""
import csv
import tempfile
import unittest
from pathlib import Path

from geometry_validation import run


class GeometryValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        folder = self.root / "reports" / "time-weighted"
        folder.mkdir(parents=True)
        self.source = folder / "time_weighted_geometry.csv"
        self.output = self.root / "reports" / "validation"

    def write(self, days=4, extra=""):
        header = ("instrument,day_msk,hour_msk,min_level_lots,observed_ms,"
                  "covered_ms,uncovered_ms,buy_geometry_ms,sell_geometry_ms,"
                  "coverage_share,buy_share_of_covered,sell_share_of_covered\n")
        rows = "".join(
            f"FAKE,2026-11-{18+i},14,120,1000000,800000,200000,"
            f"{200000 if i == 3 else 400000},600000,0.8,0.5,0.75\n"
            for i in range(days))
        self.source.write_text(header + rows + extra, encoding="utf-8")

    def test_holdout_not_in_training_metrics(self):
        self.write()
        result = run(self.root, self.source, self.output, min_daily_covered_ms=500000)
        self.assertEqual(result["eligible_for_descriptive_comparison"], 1)
        with (self.output / "held_out_book_geometry.csv").open(newline="") as file:
            row = next(csv.DictReader(file))
        self.assertEqual(row["train_buy_share"], "0.5")
        self.assertEqual(row["test_buy_share"], "0.25")
        self.assertEqual(row["held_out_day"], "2026-11-21")
        with self.assertRaises(ValueError):
            run(self.root, self.source, self.output, min_daily_covered_ms=500000)

    def test_two_days_are_not_sufficient(self):
        self.write(days=2)
        result = run(self.root, self.source, self.output, min_daily_covered_ms=500000)
        self.assertEqual(result["eligible_for_descriptive_comparison"], 0)

    def test_nan_input_blocks_all_comparisons(self):
        self.write(extra="FAKE,2026-11-22,14,120,1000000,800000,200000,NaN,600000,0.8,0.5,0.75\n")
        result = run(self.root, self.source, self.output, min_daily_covered_ms=500000)
        self.assertEqual(result["invalid_source_rows"], 1)
        self.assertEqual(result["eligible_for_descriptive_comparison"], 0)

    def test_overlap_warning_blocks_result(self):
        self.write(extra="FAKE,2026-11-21,14,120,2800000,2200000,600000,1000000,1000000,0.8,0.5,0.5\n")
        result = run(self.root, self.source, self.output, min_daily_covered_ms=500000)
        self.assertEqual(result["possible_overlapping_groups"], 1)
        self.assertEqual(result["eligible_for_descriptive_comparison"], 0)

    def test_source_outside_reports_refused(self):
        self.write()
        foreign = self.root / "untrusted.csv"
        foreign.write_text(self.source.read_text())
        with self.assertRaises(ValueError):
            run(self.root, foreign, self.output)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
