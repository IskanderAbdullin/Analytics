#!/usr/bin/env python3
"""Freeze a bounded NVDA forensic input set into a local-only directory.

This is NOT an atomic filesystem snapshot and cannot certify broker-side facts.
Never run with a public artifact/output directory or upload the output to CI.
The script reads source files only; it never talks to the broker or robot.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
from typing import Iterable

# Explicit bounded P0 input set. No config, credentials, tokens, or network files.
NVDA_INPUTS = (
    "logs-nvda-iis-live/babid01-20261121.log",
    "state-nvda-iis-live/fills.csv",
    "state-nvda-iis-live/journal.json",
    "state-nvda-iis-live/journal.wal",
    "state-nvda-iis-live/risk.json",
)
CHUNK = 1024 * 1024


class UnstableInput(RuntimeError):
    """A source was modified or replaced during the freeze operation."""


def _reject_linked_components(path: Path) -> None:
    # Prevent following junctions/reparse points as well as regular symlinks.
    for part in (path, *path.parents):
        if not part.exists() and not part.is_symlink():
            continue
        if part.is_symlink():
            raise ValueError("linked filesystem component is not allowed")
        try:
            attrs = part.lstat().st_file_attributes
        except AttributeError:  # POSIX st_file_attributes is absent.
            attrs = 0
        if attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
            raise ValueError("reparse-point component is not allowed")


def _safe_relative(name: str) -> Path:
    if not name or "\\" in name or name.startswith("/"):
        raise ValueError("input must be a relative POSIX-style path")
    p = Path(name)
    if p.is_absolute() or any(part in ("", ".", "..") for part in name.split("/")):
        raise ValueError("unsafe relative input path")
    return p


def _signature(info: os.stat_result) -> tuple[int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def _read_hash(path: Path) -> tuple[str, os.stat_result]:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("source must be a regular file")
        sha = hashlib.sha256()
        while True:
            buf = stream.read(CHUNK)
            if not buf:
                break
            sha.update(buf)
    return sha.hexdigest(), info


def _copy_stream(src: Path, target: Path) -> tuple[str, int, os.stat_result]:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(src, flags)
    h = hashlib.sha256()
    length = 0
    with os.fdopen(fd, "rb") as source, target.open("xb") as destination:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("source must be a regular file")
        while True:
            buf = source.read(CHUNK)
            if not buf:
                break
            destination.write(buf)
            h.update(buf)
            length += len(buf)
        destination.flush()
        os.fsync(destination.fileno())
    return h.hexdigest(), length, info


def freeze_inputs(source_root: Path, private_root: Path, label: str,
                  inputs: Iterable[str] = NVDA_INPUTS) -> dict:
    """Make one self-contained copy; raise and remove it on instability.

    Per-file SHA stability is checked before and after the copy. It does not
    mean simultaneous, cross-file atomicity, historical completeness, or a
    broker-authoritative statement.
    """
    source_root = Path(source_root)
    private_root = Path(private_root)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", label):
        raise ValueError("invalid snapshot label")
    # Require the intentional private output subtree even for the CLI.
    if [p.lower() for p in private_root.parts[-2:]] != ["reports", "private"]:
        raise ValueError("output must be a reports/private directory")
    _reject_linked_components(source_root)
    _reject_linked_components(private_root)
    if not source_root.is_dir():
        raise FileNotFoundError("source root is missing")
    relative = [_safe_relative(name) for name in inputs]
    if len(relative) != len(set(relative)):
        raise ValueError("duplicate input")
    # Prevent snapshot being placed inside the source tree, which is unsafe
    # to include in future audits and can accidentally feed the robot.
    if private_root.resolve() == source_root.resolve() or source_root.resolve() in private_root.resolve().parents:
        raise ValueError("private output must be outside the source tree")
    private_root.mkdir(parents=True, exist_ok=True)
    target_root = private_root / label
    target_root.mkdir(exist_ok=False)
    entries = []
    try:
        for rel in relative:
            source = source_root / rel
            _reject_linked_components(source)
            if not source.is_file():
                raise FileNotFoundError("required forensic input missing: " + rel.as_posix())
            before_hash, before_stat = _read_hash(source)
            target = target_root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            copy_hash, length, copy_stat = _copy_stream(source, target)
            after_hash, after_stat = _read_hash(source)
            saved_hash, saved_stat = _read_hash(target)
            if (len({before_hash, copy_hash, after_hash, saved_hash}) != 1 or
                    _signature(before_stat) != _signature(copy_stat) or
                    _signature(before_stat) != _signature(after_stat) or
                    length != before_stat.st_size or saved_stat.st_size != length):
                raise UnstableInput("forensic input changed during freeze: " + rel.as_posix())
            entries.append({
                "path": rel.as_posix(),
                "sha256": saved_hash,
                "size": length,
                "source_stable_during_copy": True,
                "copied_file_verified": True,
            })
        created = datetime.now(timezone.utc).isoformat()
        manifest = {
            "schema_version": 1,
            "created_utc": created,
            "purpose": "NVDA 2026-11-21 offline causal audit only",
            "files": entries,
            "verified_each_file_before_and_after_copy": True,
            "atomic_across_files": False,
            "independent_broker_evidence": False,
            "completeness_of_order_stream": "not_verified",
            "limitations": [
                "Individual files may represent different moments; NOT an atomic snapshot",
                "A copied source that was stable while copied can still have changed at other times",
                "No broker-side execution confirmation or order-state request/response chronology",
                "Keep all copied files and this manifest private; never upload to public CI or GitHub",
            ],
        }
        (target_root / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        (target_root / ".gitignore").write_text("*\n", encoding="utf-8")
        return manifest
    except BaseException:
        shutil.rmtree(target_root)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path,
                        help="Local workspace copy of Babid01-TInvest; never a broker endpoint")
    parser.add_argument("--private-root", required=True, type=Path,
                        help="Local ANALYSIS reports/private directory, outside source root")
    parser.add_argument("--label", help="New name without slashes; defaults to an UTC label")
    args = parser.parse_args()
    label = args.label or "nvda-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    manifest = freeze_inputs(args.source_root, args.private_root, label)
    print("Private bounded freeze succeeded: %d inputs; per-file hashes verified; cross-file atomicity NOT claimed." % len(manifest["files"]))
    print("Keep frozen output in local reports/private; do NOT upload to public CI/GitHub.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
