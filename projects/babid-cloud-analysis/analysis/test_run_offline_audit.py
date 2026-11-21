"""Synthetic safety and provenance tests for the audit coordinator."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from run_offline_audit import checksum, inventory, run


class CoordinatorTests(unittest.TestCase):
    def test_checksum_and_safe_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "state-test").mkdir()
            (root / "config.test.json").write_text('{"mode":"paper","stateDir":"state-test"}')
            (root / "state-test" / "journal.json").write_text('{"Mode":"paper"}')
            c = checksum(root / "config.test.json")
            self.assertEqual(len(c), 64)
            self.assertEqual(len(inventory(root)), 2)
            output = root / "reports" / "once"
            result = run(root, output, with_market=False)
            self.assertIn("history", result["reports"])
            self.assertTrue((output / "manifest.json").is_file())
            with self.assertRaises(ValueError):
                run(root, output, with_market=False)
            with self.assertRaises(ValueError):
                run(root, root / "state-test" / "reports", with_market=False)


if __name__ == "__main__":
    unittest.main()
