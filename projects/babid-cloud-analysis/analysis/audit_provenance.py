"""Post-run file stability checks for offline evidence analysis.

Detects changes in source files between inventory and report completion using
size and mtime, without reading source files a second time or following links
outside the selected copy. This is not an atomic filesystem snapshot.
"""
from __future__ import annotations

from pathlib import Path

SOURCE_PATTERNS = ("config*.json", "state*/journal.json", "state*/risk.json",
                   "state*/fills.csv", "state*/pnl-curve.csv",
                   "logs*/*.log", "recordings/*/*.tsv", "recordings/*/*.tsv.gz")


def changes_since_inventory(root: Path, inventory: list[dict]) -> list[dict]:
    root = Path(root).resolve(strict=True)
    changes = []
    known = {str(item.get("path", "")).replace("\\", "/") for item in inventory}
    for entry in inventory:
        name = entry.get("path", "")
        if not name:
            continue
        path = (root / name).resolve(strict=False)
        if not path.is_relative_to(root):
            changes.append({"path": name, "reason": "input_escaped_archive"})
            continue
        if "error" in entry:
            changes.append({"path": name, "reason": "input_unreadable_at_inventory"})
            continue
        try:
            st = path.stat()
        except OSError:
            changes.append({"path": name, "reason": "missing_after_scan"})
            continue
        if "mtime_ns_after" not in entry or "size_after" not in entry:
            changes.append({"path": name, "reason": "inventory_missing_stat"})
            continue
        if st.st_size != entry["size_after"] or st.st_mtime_ns != entry["mtime_ns_after"]:
            changes.append({"path": name, "reason": "changed_after_inventory",
                            "size_before": entry["size_after"], "size_after": st.st_size})
    # The files seen when the audit began are not the whole story. Live log
    # rotation or a newly created recording can add previously unseen sources.
    added = set()
    for pattern in SOURCE_PATTERNS:
        for path in root.glob(pattern):
            if not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            if relative in known or relative in added:
                continue
            added.add(relative)
            if not path.resolve().is_relative_to(root):
                changes.append({"path": relative, "reason": "new_input_escaped_archive"})
            else:
                changes.append({"path": relative, "reason": "added_after_inventory"})
    return changes
