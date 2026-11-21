#!/usr/bin/env python3
"""Deterministic validation/resumption for the Babid Cloud research checkpoint.

This never reads user trade logs, calls brokers, mutates state, or executes
the next command. It is safe for public, synthetic-only GitHub Actions.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

REQUIRED_FILES = (
    "GOAL.md", "STATE.json", "NEXT_ACTION.json", "EVIDENCE.md",
    "BACKLOG.md", "PROTOCOL.md",
)
PROJECT_ID = "babid-cloud-analysis"
HYPOTHESIS_STATUSES = {"untested", "supported", "rejected", "confirmed"}
ACTION_STATUSES = {"ready", "in_progress", "blocked_external", "done"}
EVIDENCE_RE = re.compile(r"^\|\s*(E-\d{3,})\s*\|", re.MULTILINE)


def read_documents(root: Path) -> tuple[dict, dict, dict]:
    """Load local research metadata only; no private folders are searched."""
    missing = [name for name in REQUIRED_FILES if not (root / name).is_file()]
    if missing:
        raise ValueError("missing required research files: " + ", ".join(missing))
    return (
        json.loads((root / "STATE.json").read_text(encoding="utf-8")),
        json.loads((root / "NEXT_ACTION.json").read_text(encoding="utf-8")),
        {
            "goal": (root / "GOAL.md").read_text(encoding="utf-8"),
            "evidence": (root / "EVIDENCE.md").read_text(encoding="utf-8"),
            "backlog": (root / "BACKLOG.md").read_text(encoding="utf-8"),
            "protocol": (root / "PROTOCOL.md").read_text(encoding="utf-8"),
        },
    )


def check(root: Path) -> list[str]:
    """Pure read-only validation. Errors never auto-repair or advance state."""
    errors: list[str] = []
    try:
        state, action, text = read_documents(root)
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError) as error:
        return [str(error)]
    if not isinstance(state, dict) or not isinstance(action, dict):
        return ["STATE.json and NEXT_ACTION.json must be objects"]
    for label, doc in (("state", state), ("next", action)):
        if doc.get("schema_version") != 1:
            errors.append(label + ": unsupported schema_version")
        if doc.get("project") != PROJECT_ID:
            errors.append(label + ": project must be babid-cloud-analysis")
        if doc.get("goal_id") != "G-001":
            errors.append(label + ": goal must be G-001")
    if "G-001" not in text["goal"]:
        errors.append("GOAL.md does not identify G-001")
    if state.get("current_action_id") != action.get("action_id"):
        errors.append("current_action_id does not match NEXT_ACTION.action_id")
    action_id = action.get("action_id")
    if not isinstance(action_id, str) or not re.fullmatch(r"A-\d{3,}", action_id):
        errors.append("NEXT_ACTION.action_id is invalid")
    elif not re.search(r"\b" + re.escape(action_id) + r"\b", text["backlog"]):
        errors.append("NEXT_ACTION.action_id not present in BACKLOG.md")
    if action.get("status") not in ACTION_STATUSES:
        errors.append("NEXT_ACTION.status is invalid")
    if not isinstance(action.get("title"), str) or not action["title"].strip():
        errors.append("NEXT_ACTION.title must be nonempty")
    if not isinstance(action.get("next_command"), str) or not action["next_command"].strip():
        errors.append("NEXT_ACTION.next_command must be nonempty")
    if not isinstance(action.get("completion_criteria"), list) or not action["completion_criteria"]:
        errors.append("NEXT_ACTION must define completion_criteria")
    if action.get("status") == "blocked_external" and not action.get("blockers"):
        errors.append("blocked_external requires documented blockers")
    if action.get("public_ci_allowed") is not False:
        errors.append("private-data research action must not run in public CI")
    if state.get("goal_status") not in ("in_progress", "completed"):
        errors.append("invalid goal_status")
    if state.get("incident_status") not in ("unresolved", "confirmed", "evidence_limited"):
        errors.append("invalid incident_status")
    if state.get("goal_status") == "completed":
        if state.get("incident_status") != "confirmed":
            errors.append("completed cannot have unresolved/unconfirmed incident")
        required = {"root_cause", "fix_specification", "real_history", "strategy_assessment"}
        if not required.issubset(set(state.get("verified_deliverables", []))):
            errors.append("completed requires all four evidence-backed deliverables")
        if action.get("status") == "blocked_external":
            errors.append("completed cannot be blocked_external")
    if state.get("incident_status") != "confirmed" and state.get("goal_status") == "completed":
        errors.append("research goal cannot be closed on synthetic evidence alone")
    try:
        date.fromisoformat(state["checkpoint_date"])
    except (KeyError, TypeError, ValueError):
        errors.append("invalid checkpoint_date")
    evidence_rows = EVIDENCE_RE.findall(text["evidence"])
    evidence_ids = set(evidence_rows)
    if not evidence_ids:
        errors.append("EVIDENCE.md must contain an evidence register")
    if len(evidence_ids) != len(evidence_rows):
        errors.append("duplicate evidence ID in EVIDENCE.md")
    state_refs = state.get("evidence_refs", [])
    if not isinstance(state_refs, list):
        errors.append("state evidence_refs must be a list")
        state_refs = []
    if len(set(state_refs)) != len(state_refs):
        errors.append("duplicate state evidence reference")
    hypothesis_ids: set[str] = set()
    for hypothesis in state.get("hypotheses", []):
        if not isinstance(hypothesis, dict):
            errors.append("invalid hypothesis entry")
            continue
        hid = hypothesis.get("id")
        if hid in hypothesis_ids:
            errors.append("duplicate hypothesis ID")
        hypothesis_ids.add(hid)
        if hypothesis.get("status") not in HYPOTHESIS_STATUSES:
            errors.append("invalid hypothesis status")
        refs = hypothesis.get("evidence_refs", [])
        if not isinstance(refs, list):
            errors.append("hypothesis evidence_refs must be a list")
            refs = []
        if hypothesis.get("status") in ("confirmed", "rejected") and not refs:
            errors.append("confirmed/rejected hypothesis needs evidence refs")
        for ref in refs:
            if ref not in evidence_ids:
                errors.append("unknown hypothesis evidence: " + str(ref))
    for ref in state_refs:
        if ref not in evidence_ids:
            errors.append("unknown state evidence: " + str(ref))
    milestone_ids: set[str] = set()
    for milestone in state.get("verified_progress", []):
        if not isinstance(milestone, dict) or not milestone.get("evidence_refs"):
            errors.append("milestone lacks cited evidence")
            continue
        mid = milestone.get("id")
        if not isinstance(mid, str) or not re.fullmatch(r"M-\d{3,}", mid):
            errors.append("invalid milestone ID")
        elif mid in milestone_ids:
            errors.append("duplicate milestone ID")
        else:
            milestone_ids.add(mid)
        for ref in milestone["evidence_refs"]:
            if ref not in evidence_ids:
                errors.append("unknown milestone evidence: " + str(ref))
    return errors


def next_action(root: Path) -> str:
    state, action, _ = read_documents(root)
    blockers = action.get("blockers") or []
    parts = [
        "Goal: " + state["goal_id"] + " / " + state["goal_status"],
        "Incident: " + state["incident_status"],
        "Next: " + action["action_id"] + " [" + action["status"] + "]",
        "Priority: " + action.get("priority", "unspecified"),
        "Task: " + action["title"],
        "Resume command (not executed): " + action["next_command"],
    ]
    if blockers:
        parts.append("External blockers:")
        parts += ["- " + block["id"] + ": " + block["description"] for block in blockers]
    parts.append("This heartbeat cannot access private/local data or start a ChatGPT agent.")
    return "\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "next"))
    parser.add_argument("--project-root", type=Path,
                        default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors = check(args.project_root)
    if errors:
        for error in errors:
            print("Research checkpoint invalid: " + error, file=sys.stderr)
        return 2
    if args.command == "validate":
        print("Research checkpoint valid; no claim about live investigation.")
    else:
        print(next_action(args.project_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
