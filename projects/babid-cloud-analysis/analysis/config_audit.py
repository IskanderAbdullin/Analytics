#!/usr/bin/env python3
"""Read-only audit of Babid Cloud configuration copies.

Finds potential conflicting state/log paths and filenames inconsistent with
selected instruments. Does not load tokenFile, contact a broker or edit config.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from audit_history import read_jsonc
from report_safety import validate_report_output

CONFIG_FIELDS = (
    "config", "template", "mode", "ticker", "class_code", "account_hash",
    "state_label", "log_label", "regime", "max_position_lots",
    "buy_quote_lots", "sell_quote_lots", "position_check_interval_sec",
    "position_mismatch_action", "use_replace_order", "schedule_enabled"
)
ISSUE_FIELDS = ("category", "severity", "files", "description")


def identity(directory: Path, raw: str) -> str:
    """Canonical identity for comparison, including Windows drive paths.

    A foreign-platform Windows absolute path is not made relative to the
    Linux scanner. Paths are compared in memory only, never published in CSV.
    """
    raw = str(raw).strip()
    if not raw:
        return ""
    normalized = raw.replace("\\", "/")
    if re.match(r"^[a-zA-Z]:/", normalized) or normalized.startswith("//"):
        return normalized.casefold().rstrip("/")
    return str((directory / normalized).resolve(strict=False)).casefold()


def safe_label(raw: str) -> str:
    """Output only the final directory name, never the full path or username."""
    return str(raw or "").replace("\\", "/").rstrip("/").split("/")[-1][:100]


def config_filename_hint(name: str) -> str | None:
    # Only conventionally instrument-tagged *live* configs are compared.
    # 'config.abc-live.json' / 'config.abc-iis-live.json'.
    found = re.match(r"^config[._-]([A-Za-z][A-Za-z0-9]*)(?:[-_][\w]+)*[-_]live(?:\b|[ ._-])",
                     name, flags=re.IGNORECASE)
    return found.group(1) if found else None


def analyze(root: Path) -> tuple[list[dict], list[dict]]:
    root = root.resolve(strict=True)
    configs: list[dict] = []
    issues: list[dict] = []
    by_state = defaultdict(list)
    by_logs = defaultdict(list)
    by_account_instrument = defaultdict(list)

    for file in sorted(root.glob("config*.json")):
        if not file.is_file() or not file.resolve().is_relative_to(root):
            continue
        template = "example" in file.name.lower() or "sample" in file.name.lower()
        try:
            raw = read_jsonc(file)
            if not isinstance(raw, dict):
                raise ValueError("configuration must be an object")
            instrument = raw.get("instrument") or {}
            strategy = raw.get("strategy") or {}
            risk = raw.get("risk") or {}
            connection = raw.get("connection") or {}
            schedule = raw.get("schedule") or {}
            if any(not isinstance(section, dict) for section in (instrument, strategy, risk, connection, schedule)):
                raise ValueError("invalid configuration section type")
            ticker = str(instrument.get("ticker") or "")
            mode = str(raw.get("mode") or "")
            account = str(raw.get("accountId") or "")
            account_hash = hashlib.sha256(account.encode("utf-8")).hexdigest()[:12] if account else ""
            state = str(raw.get("stateDir") or "state")
            logs = str(raw.get("logDir") or "logs")
            row = dict(
                config=file.name, template=template, mode=mode, ticker=ticker,
                class_code=str(instrument.get("classCode") or ""),
                account_hash=account_hash,
                state_label=safe_label(state), log_label=safe_label(logs),
                regime=strategy.get("regime", "Off"),
                max_position_lots=strategy.get("maxPositionLots", ""),
                buy_quote_lots=strategy.get("buyQuoteLots", ""),
                sell_quote_lots=strategy.get("sellQuoteLots", ""),
                position_check_interval_sec=risk.get("positionCheckIntervalSec", ""),
                position_mismatch_action=risk.get("positionMismatchAction", ""),
                use_replace_order=connection.get("useReplaceOrder", ""),
                schedule_enabled=schedule.get("enabled", False),
            )
            configs.append(row)
            if template:
                continue
            key_state = identity(root, state)
            key_logs = identity(root, logs)
            if key_state:
                by_state[key_state].append(file.name)
            if key_logs:
                by_logs[key_logs].append(file.name)
            if account_hash and ticker:
                by_account_instrument[(account_hash, ticker.casefold(), mode.casefold())].append(file.name)
            hint = config_filename_hint(file.name)
            if hint and ticker and not ticker.casefold().startswith(hint.casefold()):
                issues.append(dict(
                    category="filename_ticker_mismatch", severity="warning",
                    files=file.name,
                    description=f"filename suggests {hint}; parsed instrument ticker is {ticker}"
                ))
            if mode.casefold() == "live" and risk.get("positionCheckIntervalSec") == 0:
                issues.append(dict(
                    category="position_check_disabled", severity="review",
                    files=file.name, description="live mode with positionCheckIntervalSec=0"
                ))
        except (OSError, ValueError, TypeError) as error:
            issues.append(dict(
                category="invalid_config", severity="error", files=file.name,
                description=str(error)[:180]
            ))
    for files in by_state.values():
        if len(files) > 1:
            issues.append(dict(category="shared_state_dir", severity="warning",
                               files=" | ".join(files),
                               description="Multiple config files refer to one state directory; simultaneous runs would collide"))
    for files in by_logs.values():
        if len(files) > 1:
            issues.append(dict(category="shared_log_dir", severity="review",
                               files=" | ".join(files),
                               description="Multiple config files refer to one log directory; histories can be mixed"))
    for files in by_account_instrument.values():
        if len(files) > 1:
            issues.append(dict(category="same_account_instrument", severity="review",
                               files=" | ".join(files),
                               description="Multiple config files use the same account, ticker and mode; this does not prove simultaneous trading"))
    return configs, issues


def run(root: Path, output: Path) -> dict:
    root, output = validate_report_output(root, output)
    configs, issues = analyze(root)
    output.mkdir(parents=True, exist_ok=False)
    with (output / "config_inventory.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CONFIG_FIELDS)
        writer.writeheader()
        writer.writerows(configs)
    with (output / "config_issues.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=ISSUE_FIELDS)
        writer.writeheader()
        writer.writerows(issues)
    counts = {kind: sum(issue["category"] == kind for issue in issues)
              for kind in sorted({issue["category"] for issue in issues})}
    summary = dict(configs=len(configs), issues=len(issues), counts=counts,
                   note="Potential configuration conflicts are not evidence of concurrent robots.")
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        root = args.root.resolve()
        result = run(root, args.output or root / "reports" / "config-audit")
    except (OSError, ValueError) as error:
        print("Config audit refused:", error, file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
