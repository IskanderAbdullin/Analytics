#!/usr/bin/env python3
"""Reconstruct ONLY observable strategy-configuration epochs from Babid01 logs.

The terminal JSON config is not historical evidence. Engine-start, Risk,
Config-applied and Schedule log markers have varying completeness; missing
fields stay unknown instead of being invented or backfilled.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

from report_safety import validate_report_output

LINE = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d(?:\.\d+)?)\s+[A-Z]{3}\s+(.*)$")
FIELDS = (
    "log_dir", "start_msk", "end_msk", "event_kind", "confidence",
    "known_fields", "settings_digest", "regime", "max_position_lots",
    "buy_quote_lots", "buy_min_level_lots", "sell_quote_lots",
    "sell_min_level_lots", "closing_level_lots", "close_no_loss",
    "max_daily_loss", "position_check_sec", "position_mismatch_action",
    "replace_order", "commission_percent", "source_file", "source_line",
)
ISSUE_FIELDS = ("log_dir", "at_msk", "kind", "source_file", "line")

RULES = {
    "regime": r"\bregime=(Off|On|CloseOnly)\b",
    "max_position_lots": r"\bmaxPositionLots=(\d+)\b",
    "buy_quote_lots": r"\bbuy=(\d+)@level>=",
    "buy_min_level_lots": r"\bbuy=\d+@level>=(\d+)\b",
    "sell_quote_lots": r"\bsell=(\d+)@level>=",
    "sell_min_level_lots": r"\bsell=\d+@level>=(\d+)\b",
    "closing_level_lots": r"\bclosing@level>=(\d+)\b",
    "max_daily_loss": r"\bmaxDailyLoss=([0-9.]+)\b",
    "position_check_sec": r"\bpositionCheck=(\d+)s/",
    "position_mismatch_action": r"\bpositionCheck=\d+s/(Warn|Halt|CloseOnly)\b",
    "commission_percent": r"commission estimate=([0-9.]+)%",
}


def extract(message: str, kind: str) -> dict:
    result = {}
    for field, pattern in RULES.items():
        match = re.search(pattern, message)
        if match:
            result[field] = match.group(1)
    if "closing@level>=" in message:
        result["close_no_loss"] = "true" if " when not at a loss" in message else "false"
    if kind == "config_applied":
        result["replace_order"] = "true" if "requote by ReplaceOrder" in message else "false"
    if kind == "schedule":
        match = re.search(r"Schedule \d\d?:\d\d MSK: regime (Off|On|CloseOnly)\b", message)
        if match:
            result["regime"] = match.group(1)
        scaled = re.search(r"position limit (\d+) and orders (\d+)/(\d+) lot\(s\)", message)
        if scaled:
            result.update(max_position_lots=scaled.group(1),
                          buy_quote_lots=scaled.group(2),
                          sell_quote_lots=scaled.group(3))
    if kind == "hand_regime":
        match = re.search(r"changed by hand to (Off|On|CloseOnly)", message)
        if match:
            result["regime"] = match.group(1)
    return result


def classify(message: str):
    if message.startswith("Config applied: "):
        return "config_applied", message[len("Config applied: "):]
    if message.startswith("Engine started: "):
        return "engine_started", message[len("Engine started: "):]
    if message.startswith("Risk: "):
        return "risk", message[len("Risk: "):]
    if message.startswith("P&L at stop: "):
        return "engine_stopped", ""
    if message.startswith("Schedule ") and " MSK: regime " in message:
        return "schedule", message
    if message.startswith("Schedule: the regime was changed by hand to "):
        return "hand_regime", message
    if message.startswith("Config reload failed"):
        return "config_reload_failed", ""
    if message.startswith("Config: mode, account and instrument changes need a restart"):
        return "ignored_identity_change", ""
    return None, ""


def log_events(folder: Path) -> list[dict]:
    selected = []
    for file in sorted(folder.glob("*.log")):
        if not file.is_file():
            continue
        with file.open("r", encoding="utf-8-sig", errors="replace") as stream:
            for lineno, line in enumerate(stream, 1):
                match = LINE.match(line.rstrip("\r\n"))
                if not match:
                    continue
                at, message = match.groups()
                kind, payload = classify(message)
                if kind is None:
                    continue
                selected.append(dict(at=at, kind=kind, values=extract(payload, kind),
                                     file=file.name, line=lineno))
                if len(selected) > 200000:
                    raise ValueError("too many config events: split the log archive")
    selected.sort(key=lambda v: (v["at"], v["file"], v["line"]))
    return selected


def reconstruct(folder: Path) -> tuple[list[dict], list[dict]]:
    events = log_events(folder)
    state = {}
    epochs, issues = [], []
    log_dir = folder.name
    for item in events:
        kind, changes = item["kind"], item["values"]
        if kind == "engine_stopped":
            if epochs:
                epochs[-1]["end_msk"] = item["at"]
            state = {}  # Nothing may be attributed after an observed stop.
            issues.append(dict(log_dir=log_dir, at_msk=item["at"], kind="observed_stop",
                               source_file=item["file"], line=item["line"]))
            continue
        if kind in ("config_reload_failed", "ignored_identity_change"):
            issues.append(dict(log_dir=log_dir, at_msk=item["at"], kind=kind,
                               source_file=item["file"], line=item["line"]))
            continue
        if kind == "engine_started":
            state = {}  # Do not carry settings across process restarts.
        state.update(changes)
        # Config-applied log has Strategy.Describe + Risk.Describe + fees.
        # It omits many connection options; it is NOT a complete config snapshot.
        confidence = (
            "descriptor_partial" if kind == "config_applied" else
            "startup_strategy_only" if kind == "engine_started" else
            "risk_only" if kind == "risk" else "schedule_partial"
        )
        digest = hashlib.sha256(
            json.dumps(state, sort_keys=True, ensure_ascii=True).encode()
        ).hexdigest()[:16] if state else ""
        record = {key: "" for key in FIELDS}
        record.update(log_dir=log_dir, start_msk=item["at"],
                      event_kind=kind, confidence=confidence,
                      known_fields=",".join(sorted(state)), settings_digest=digest,
                      source_file=item["file"], source_line=item["line"])
        record.update(state)
        if epochs:
            epochs[-1]["end_msk"] = item["at"]
        epochs.append(record)
    return epochs, issues


def run(root: Path, output: Path) -> dict:
    root, output = validate_report_output(root, output)
    epochs, issues = [], []
    directories = 0
    for folder in sorted(root.glob("logs*")):
        if not folder.is_dir() or not folder.resolve().is_relative_to(root):
            continue
        directories += 1
        e, i = reconstruct(folder)
        epochs.extend(e)
        issues.extend(i)
    output.mkdir(parents=True, exist_ok=False)
    with (output / "settings_epochs.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(epochs)
    with (output / "config_events.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=ISSUE_FIELDS)
        writer.writeheader()
        writer.writerows(issues)
    summary = dict(log_directories=directories, observed_epochs=len(epochs),
                   warning_events=len(issues), by_kind={kind: sum(e["event_kind"] == kind for e in epochs)
                                                         for kind in sorted({e["event_kind"] for e in epochs})},
                   limits=[
                       "No settings can be inferred before the first logged event.",
                       "Engine startup descriptors omit connection fields and risk is logged separately.",
                       "Schedule updates are partial and do not prove all effective parameters.",
                       "Log directories may be shared; an epoch is not proven to belong to a single instrument.",
                       "Financial results must not be attributed to these epochs without a verified mapping.",
                   ])
    (output / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    root = a.root.resolve()
    try:
        result = run(root, a.output or root / "reports" / "config-epochs")
    except (OSError, ValueError) as error:
        print("Config epoch scan refused:", error, file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
