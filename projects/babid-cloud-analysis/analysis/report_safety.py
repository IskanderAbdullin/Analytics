"""Keep read-only Babid offline audit artifacts out of live trading directories."""
from __future__ import annotations

from pathlib import Path


def validate_report_output(root: Path, output: Path) -> tuple[Path, Path]:
    """Verify a fresh destination under <root>/reports, never a trading input.

    Resolves symlinks before comparing roots, including a symlinked reports
    directory. Do not use a preexisting output: forensic evidence must be
    immutable across repeated runs. Reserve with mkdir(exist_ok=False) next.
    """
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("audit root must be a directory")
    report_root = root / "reports"
    if report_root.is_symlink():
        raise ValueError("reports directory must not be a symlink")
    report_root_resolved = report_root.resolve(strict=False)
    if not report_root_resolved.is_relative_to(root):
        raise ValueError("reports directory escapes the source copy")
    output = Path(output).resolve(strict=False)
    if not output.is_relative_to(report_root_resolved) or output == report_root_resolved:
        raise ValueError("audit outputs must be in a new subdirectory of reports/")
    if output.exists() or output.is_symlink():
        raise ValueError("refusing to overwrite an existing report directory")
    return root, output


def reserve_report_output(root: Path, output: Path) -> Path:
    """Atomically create a new output directory after validating containment."""
    _, destination = validate_report_output(root, output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.mkdir(exist_ok=False)
    return destination
