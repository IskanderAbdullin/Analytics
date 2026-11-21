"""Synthetic provenance checks do not touch a user's running trade files."""
import tempfile
import unittest
from pathlib import Path
from audit_provenance import changes_since_inventory


class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "state-nvda" / "fills.csv"
        self.path.parent.mkdir()
        self.path.write_text("abc")
        s = self.path.stat()
        self.entry = {"path": "state-nvda/fills.csv", "size_after": s.st_size,
                      "mtime_ns_after": s.st_mtime_ns}

    def test_stable_input(self):
        self.assertEqual(changes_since_inventory(self.root, [self.entry]), [])

    def test_same_size_rewrite_is_detected(self):
        self.path.write_text("xyz")
        s = self.path.stat()
        import os
        os.utime(self.path, ns=(s.st_atime_ns, self.entry["mtime_ns_after"] + 1000000000))
        changes = changes_since_inventory(self.root, [self.entry])
        self.assertEqual(changes[0]["reason"], "changed_after_inventory")

    def test_removed_input(self):
        self.path.unlink()
        self.assertEqual(changes_since_inventory(self.root, [self.entry])[0]["reason"], "missing_after_scan")

    def test_unknown_inventory_is_not_marked_stable(self):
        self.assertEqual(changes_since_inventory(self.root, [{"path": "state-nvda/fills.csv"}])[0]["reason"],
                         "inventory_missing_stat")

    def test_new_log_file_is_detected(self):
        folder = self.root / "logs-nvda"
        folder.mkdir()
        (folder / "babid01-20261121.log").write_text("new data")
        changes = changes_since_inventory(self.root, [self.entry])
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["reason"], "added_after_inventory")

    def test_new_recording_detected(self):
        folder = self.root / "recordings" / "NVDAperpA"
        folder.mkdir(parents=True)
        (folder / "NVDAperpA_2026-11-21.tsv").write_text("B\t123")
        changes = changes_since_inventory(self.root, [self.entry])
        self.assertEqual(changes[0]["reason"], "added_after_inventory")

    def test_symlink_escape_rejected(self):
        outside = self.root.parent / (self.root.name + "-secret")
        outside.mkdir()
        self.addCleanup(lambda: outside.rmdir())
        try:
            (self.root / "redirect").symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable on this host")
        self.assertEqual(changes_since_inventory(self.root, [{"path": "redirect/file"}])[0]["reason"],
                         "input_escaped_archive")


if __name__ == "__main__":
    unittest.main()
