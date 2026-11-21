#!/usr/bin/env python3
"""Run all read-only Babid C Cloud forensic studies against one source copy.

Creates a new report directory. No broker connection, order placement,
trading-state mutation or Windows desktop control is possible from this tool.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from report_safety import validate_report_output

import audit_history
import market_study
import position_forensics
import reconcile_fills
import opportunity_validation
import audit_provenance
import config_audit
import tape_integrity
import time_weighted_books
import config_epochs
import audit_quality
import fills_by_epoch
import execution_markout


def checksum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for part in iter(lambda: source.read(1 << 20), b""):
            h.update(part)
    return h.hexdigest()


def inventory(root: Path) -> list[dict]:
    """Hash inputs before a scan, with before/after sizes for live-file detection."""
    root = root.resolve(strict=True)
    names = set()
    for pattern in audit_provenance.SOURCE_PATTERNS:
        names.update(root.glob(pattern))
    records = []
    for p in sorted(names):
        if not p.is_file() or not p.resolve().is_relative_to(root):
            continue
        try:
            before = p.stat()
            digest = checksum(p)
            after = p.stat()
            records.append(dict(path=p.relative_to(root).as_posix(), sha256=digest,
                                size_before=before.st_size, size_after=after.st_size,
                                mtime_ns_after=after.st_mtime_ns,
                                stable_during_hash=(before.st_size == after.st_size and
                                    before.st_mtime_ns == after.st_mtime_ns)))
        except OSError as error:
            records.append(dict(path=p.relative_to(root).as_posix(),
                                error=str(error)[:150]))
    return records


def run(root: Path, output: Path, with_market: bool = True, *,
        epoch_state: str | None = None, epoch_logs: str | None = None,
        markout_state: str | None = None, markout_instrument: str | None = None,
        markout_day: str | None = None) -> dict:
    if bool(epoch_state) != bool(epoch_logs):
        raise ValueError("epoch_state and epoch_logs must be supplied together")
    if any((markout_state, markout_instrument, markout_day)) and not all(
            (markout_state, markout_instrument, markout_day)):
        raise ValueError("markout_state, markout_instrument and markout_day must all be supplied")
    root, output = validate_report_output(root, output)
    # First take file-level checksums; no source changes. If inputs are changing,
    # the report explicitly says it is not an atomic snapshot.
    files = inventory(root)
    output.mkdir(parents=True, exist_ok=False)
    manifest = dict(created_utc=datetime.now(UTC).isoformat(),
                    root=str(root), files=files, reports={},
                    limitations=["Input folders are not an atomic filesystem snapshot",
                                 "No independent broker-side executed-trade reconciliation",
                                 "Historical config epochs may be unavailable",
                                 "No auto-application of optimized settings"])
    try:
        manifest["reports"]["history"] = audit_history.run(
            root, output / "history", "2026-11-21T14:40:00",
            "2026-11-21T15:10:00")
    except (OSError, ValueError) as error:
        manifest["reports"]["history_error"] = str(error)[:300]
    try:
        manifest["reports"]["reconciliation"] = reconcile_fills.run(
            root, output / "reconciliation")
    except (OSError, ValueError) as error:
        manifest["reports"]["reconciliation_error"] = str(error)[:300]
    try:
        manifest["reports"]["configs"] = config_audit.run(
            root, output / "config-audit")
    except (OSError, ValueError) as error:
        manifest["reports"]["configs_error"] = str(error)[:300]
    try:
        manifest["reports"]["config_epochs"] = config_epochs.run(
            root, output / "config-epochs")
    except (OSError, ValueError) as error:
        manifest["reports"]["config_epochs_error"] = str(error)[:300]
    if with_market and (root / "recordings").is_dir():
        try:
            manifest["reports"]["time_weighted"] = time_weighted_books.run(
                root, output / "time-weighted", 2000)
        except (OSError, ValueError) as error:
            manifest["reports"]["time_weighted_error"] = str(error)[:300]
        try:
            manifest["reports"]["tape_integrity"] = tape_integrity.run(
                root, output / "tape-integrity")
        except (OSError, ValueError) as error:
            manifest["reports"]["tape_integrity_error"] = str(error)[:300]
        try:
            manifest["reports"]["market"] = market_study.run(
                root, output / "market", market_study.DEFAULT_LEVELS, None)
        except (OSError, ValueError) as error:
            manifest["reports"]["market_error"] = str(error)[:300]
    if with_market and (output / "market" / "opportunities.csv").is_file():
        try:
            manifest["reports"]["opportunity_validation"] = opportunity_validation.run(
                root, output / "market" / "opportunities.csv",
                output / "opportunity_validation")
        except (OSError, ValueError) as error:
            manifest["reports"]["opportunity_validation_error"] = str(error)[:300]
    if (root / "state-nvda-iis-live" / "fills.csv").is_file():
        try:
            manifest["reports"]["nvda"] = position_forensics.run(
                root, "state-nvda-iis-live", "logs-nvda-iis-live",
                "2026-11-21 14:40:00", "2026-11-21 15:10:00",
                output / "nvda")
        except (OSError, ValueError) as error:
            manifest["reports"]["nvda_error"] = str(error)[:300]
    if epoch_state and epoch_logs:
        try:
            manifest["reports"]["epoch_attribution"] = fills_by_epoch.run(
                root, output / "epoch-attribution", epoch_state, epoch_logs)
        except (OSError, ValueError) as error:
            manifest["reports"]["epoch_attribution_error"] = str(error)[:300]
    if markout_state and markout_instrument and markout_day:
        try:
            manifest["reports"]["markout"] = execution_markout.run(
                root, output / "markout", markout_state, markout_instrument, markout_day)
        except (OSError, ValueError) as error:
            manifest["reports"]["markout_error"] = str(error)[:300]
    manifest["unstable_input_files"] = sum(
        1 for f in files if not f.get("stable_during_hash", False))
    manifest["changed_inputs_across_scan"] = audit_provenance.changes_since_inventory(root, files)
    manifest["input_files_appear_stable"] = (
        manifest["unstable_input_files"] == 0 and not manifest["changed_inputs_across_scan"])
    manifest["quality_gate"] = audit_quality.evaluate(manifest)
    (output / "quality_gate.json").write_text(
        json.dumps(manifest["quality_gate"], ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return dict(output=str(output), files=len(files),
                unstable_input_files=manifest["unstable_input_files"],
                audit_status=manifest["quality_gate"]["status"],
                reports=list(manifest["reports"]))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--output", type=Path)
    p.add_argument("--skip-market", action="store_true",
                   help="skip potentially lengthy scans of market recordings")
    p.add_argument("--epoch-state", help="explicit state folder for per-setting booked fills")
    p.add_argument("--epoch-logs", help="explicit logs folder for per-setting booked fills")
    p.add_argument("--markout-state", help="explicit state folder for markouts")
    p.add_argument("--markout-instrument", help="explicit tape ticker for markouts")
    p.add_argument("--markout-day", help="MSK day YYYY-MM-DD for markouts")
    args = p.parse_args()
    root = args.root.resolve()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output = args.output or (root / "reports" / ("complete-audit-" + stamp))
    try:
        result = run(root, output, not args.skip_market,
                     epoch_state=args.epoch_state, epoch_logs=args.epoch_logs,
                     markout_state=args.markout_state,
                     markout_instrument=args.markout_instrument,
                     markout_day=args.markout_day)
    except (OSError, ValueError) as error:
        print("Offline audit refused:", error, file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result["audit_status"] == "incomplete" else 0


if __name__ == "__main__":
    raise SystemExit(main())
