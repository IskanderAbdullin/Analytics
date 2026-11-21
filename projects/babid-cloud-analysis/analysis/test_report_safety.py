import tempfile
import unittest
from pathlib import Path
from report_safety import validate_report_output, reserve_report_output


class ReportPathTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'archive'
        self.root.mkdir()
        (self.root / 'state-live').mkdir()
        (self.root / 'logs-live').mkdir()

    def test_rejects_live_dirs_and_project_files(self):
        for path in ['state-live/audit', 'logs-live/audit', 'analysis/audit', 'app/audit',
                     'src/audit', 'recordings/audit', 'reports']:
            with self.subTest(path=path), self.assertRaises(ValueError):
                validate_report_output(self.root, self.root / path)

    def test_rejects_parent_escape_and_existing(self):
        with self.assertRaises(ValueError):
            validate_report_output(self.root, self.root.parent / 'reports' / 'audit')
        dest = self.root / 'reports' / 'audit-1'
        self.assertEqual(reserve_report_output(self.root, dest), dest)
        with self.assertRaises(ValueError):
            reserve_report_output(self.root, dest)

    def test_nested_reports_are_allowed_once(self):
        target = self.root / 'reports' / '2026' / 'nvda'
        reserve_report_output(self.root, target)
        self.assertTrue(target.is_dir())

    def test_symlink_redirect_is_rejected(self):
        try:
            (self.root / 'reports').symlink_to(self.root / 'state-live', target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks are unavailable on this host')
        with self.assertRaises(ValueError):
            validate_report_output(self.root, self.root / 'reports' / 'bad')

    def test_symlink_inside_reports_pointing_to_state_is_rejected(self):
        (self.root / 'reports').mkdir()
        try:
            (self.root / 'reports' / 'redirect').symlink_to(self.root / 'state-live', target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks are unavailable on this host')
        with self.assertRaises(ValueError):
            validate_report_output(self.root, self.root / 'reports' / 'redirect' / 'bad')


if __name__ == '__main__':
    unittest.main()
