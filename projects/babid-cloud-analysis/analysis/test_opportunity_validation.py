"""Synthetic descriptive walk-forward checks with no execution or P&L model."""
import csv
import tempfile
import unittest
from pathlib import Path
from opportunity_validation import run

HEADER = 'ticker,date_msk,hour_msk,min_level_lots,books,buy_share,sell_share,spread_ticks,buy_edge_ticks,sell_edge_ticks\n'


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root = Path(self.t.name)
        folder = self.root / 'reports' / 'market-study'
        folder.mkdir(parents=True)
        self.source = folder / 'opportunities.csv'
        self.output = self.root / 'reports' / 'validation-1'

    def data(self, days=3):
        rows = []
        for i, v in enumerate(['0.25', '0.50', '0.75'][:days], 19):
            rows.append(f'NVDA,2026-11-{i},12,120,100,{v},0.5,3,1,1\n')
        self.source.write_text(HEADER + ''.join(rows))

    def test_held_out_last_day_and_weighted_training(self):
        self.data()
        result = run(self.root, self.source, self.output)
        self.assertEqual(result['comparable_groups'], 1)
        with (self.output / 'out_of_sample_feasibility.csv').open(newline='') as f:
            row = next(csv.DictReader(f))
        self.assertEqual(row['held_out_day'], '2026-11-21')
        self.assertEqual(row['train_buy_share'], '0.375')
        self.assertEqual(row['test_buy_share'], '0.75')
        self.assertEqual(row['worst_daily_buy_share'], '0.25')
        self.assertEqual(row['ready_for_comparison'], 'True')
        with self.assertRaises(ValueError):
            run(self.root, self.source, self.output)

    def test_insufficient_days_not_optimization(self):
        self.data(2)
        result = run(self.root, self.source, self.output)
        self.assertEqual(result['comparable_groups'], 0)

    def test_untrusted_external_input_rejected(self):
        self.data()
        outside = self.root / 'outside.csv'
        outside.write_text(self.source.read_text())
        with self.assertRaises(ValueError):
            run(self.root, outside, self.output)

    def test_invalid_record_is_reported_not_counted(self):
        self.data()
        with self.source.open('a') as f:
            f.write('NVDA,2026-11-22,12,120,100,NaN,0.1,1,1,1\n')
            f.write('NVDA,2026-11-99,12,120,100,0.2,0.1,1,1,1\n')
        result = run(self.root, self.source, self.output)
        self.assertEqual(result['warnings_total'], 2)

    def test_bad_source_quality_prevents_eligible_comparison(self):
        self.data()
        result = run(self.root, self.source, self.output, source_quality_unverified=True)
        self.assertEqual(result["comparable_groups"], 0)
        self.assertTrue(result["source_market_quality_unverified"])
        with (self.output / "out_of_sample_feasibility.csv").open(newline="") as f:
            row = next(csv.DictReader(f))
        self.assertEqual(row["ready_for_comparison"], "False")
        self.assertIn("source_market_quality_unverified", row["qualifications"])

    def test_invalid_csv_rows_block_success_even_with_many_valid_days(self):
        self.data()
        with self.source.open("a") as file:
            file.write("NVDA,2026-11-22,13,120,100,NaN,0.1,1,1,1\n")
        result = run(self.root, self.source, self.output)
        self.assertEqual(result["warnings_total"], 1)
        self.assertEqual(result["comparable_groups"], 0)
        with (self.output / "out_of_sample_feasibility.csv").open(newline="") as f:
            row = next(csv.DictReader(f))
        self.assertIn("invalid_or_duplicate_opportunity_rows", row["qualifications"])

    def test_duplicate_hour_not_allowed_to_inflate_training(self):
        self.data()
        with self.source.open("a") as file:
            file.write("NVDA,2026-11-19,12,120,100,0.9,0.9,3,1,1\n")
        result = run(self.root, self.source, self.output)
        self.assertEqual(result["duplicate_hour_rows"], 1)
        self.assertEqual(result["comparable_groups"], 0)
        with (self.output / "out_of_sample_feasibility.csv").open(newline="") as f:
            row = next(csv.DictReader(f))
        self.assertEqual(row["train_books"], "200")
        self.assertIn("invalid_or_duplicate_opportunity_rows", row["qualifications"])

    def test_error_examples_are_bounded_without_losing_error_total(self):
        self.data()
        with self.source.open("a") as file:
            file.write("NVDA,2026-11-99,13,120,100,NaN,0.1,1,1,1\n" * 120)
        result = run(self.root, self.source, self.output)
        self.assertEqual(result["warnings_total"], 120)
        self.assertEqual(len(result["warnings"]), 100)
        self.assertEqual(result["comparable_groups"], 0)


if __name__ == '__main__':
    unittest.main()
