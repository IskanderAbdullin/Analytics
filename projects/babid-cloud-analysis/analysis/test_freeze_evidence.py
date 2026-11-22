"""Synthetic-only smoke/regression tests; no broker data or user paths."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from freeze_evidence import UnstableInput, freeze_inputs


class FreezeEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.src = self.base / "source"
        self.src.mkdir()
        self.private = self.base / "analysis" / "reports" / "private"
        self.items = ("logs-synthetic/fictional.log", "state-synthetic/fills.csv")
        for n, content in zip(self.items, (b"SYNTHETIC order events\n", b"synthetic;2;99\n"), strict=True):
            path = self.src / n
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)

    def test_successful_freeze_hashes_and_disclaims_atomicity(self):
        manifest = freeze_inputs(self.src, self.private, "fixture-01", self.items)
        self.assertFalse(manifest["atomic_across_files"])
        self.assertFalse(manifest["independent_broker_evidence"])
        self.assertEqual(manifest["completeness_of_order_stream"], "not_verified")
        self.assertEqual(len(manifest["files"]), 2)
        self.assertEqual(json.loads((self.private / "fixture-01/manifest.json").read_text()), manifest)
        for item in manifest["files"]:
            expected = (self.src / item["path"]).read_bytes()
            self.assertEqual((self.private / "fixture-01" / item["path"]).read_bytes(), expected)
            self.assertEqual(item["sha256"], hashlib.sha256(expected).hexdigest())
        self.assertEqual((self.private / "fixture-01/.gitignore").read_text(), "*\n")

    def test_input_path_traversal_denied(self):
        for path in ("../outside", "/etc/shadow", "x/../y", "x\\..\\z", "./foo", ""):
            with self.subTest(path=path), self.assertRaises(ValueError):
                freeze_inputs(self.src, self.private, "bad-" + str(len(path)), (path,))

    def test_no_overwrite_existing_snapshot(self):
        freeze_inputs(self.src, self.private, "frozen", self.items)
        with self.assertRaises(FileExistsError):
            freeze_inputs(self.src, self.private, "frozen", self.items)

    def test_detects_source_changed_during_copy_and_cleans_output(self):
        from freeze_evidence import _copy_stream

        def racing_copy(source, target):
            result = _copy_stream(source, target)
            source.write_bytes(source.read_bytes() + b"modified by synthetic test")
            return result

        with mock.patch("freeze_evidence._copy_stream", side_effect=racing_copy):
            with self.assertRaises(UnstableInput):
                freeze_inputs(self.src, self.private, "racing", self.items)
        self.assertFalse((self.private / "racing").exists())

    def test_missing_input_rolls_back(self):
        with self.assertRaises(FileNotFoundError):
            freeze_inputs(self.src, self.private, "missing", ("missing.bin",))
        self.assertFalse((self.private / "missing").exists())

    def test_public_directory_denied(self):
        with self.assertRaises(ValueError):
            freeze_inputs(self.src, self.base / "output" / "public", "bad", self.items)

    def test_source_nested_output_denied(self):
        with self.assertRaises(ValueError):
            freeze_inputs(self.src, self.src / "reports" / "private", "bad", self.items)

    def test_symlinked_input_denied(self):
        alias = self.src / "alias.bin"
        try:
            alias.symlink_to(self.src / self.items[0])
        except (OSError, NotImplementedError):
            self.skipTest("symbolic links unavailable")
        with self.assertRaises(ValueError):
            freeze_inputs(self.src, self.private, "link", ("alias.bin",))


if __name__ == "__main__":
    unittest.main()
