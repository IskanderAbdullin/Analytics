#!/usr/bin/env python3
"""Offline, read-only validation of the long-running research checkpoint.

No background daemon is started by this script. The metadata encodes
which active agent run should resume next, not a promise that one exists.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "research" / "autonomy_state.json"
TZ = ROOT / "docs" / "AUTONOMOUS_RESEARCH_TZ.md"
OWNER = "IskanderAbdullin/Analytics"
BRANCH = "agent/robot-detector-l2-binphase-20261121"
MASTER_ISSUE = "https://github.com/IskanderAbdullin/Analytics/issues/72"
STATES = {"ACTIVE_RESEARCH_NOT_RELEASED", "BLOCKED_WITH_RESUMABLE_WORK",
          "RELEASE_GATE_AUDITED"}
STAGE_STATES = {"READY_TO_IMPLEMENT", "IN_PROGRESS", "BLOCKED",
                "DONE_PENDING_FOLLOW_ON"}
REQUIRED_TRUE = (
    "continue_to_next_stage_without_intermediate_reply_within_active_run",
    "do_not_promise_execution_between_chats_without_scheduler",
    "no_force_push", "no_live_broker_orders",
    "no_github_actions_in_private_repositories",
    "only_small_bounded_one_time_real_market_data_workflows",
    "no_raw_proprietary_market_archives_in_repo",
    "pc_agent_only_with_explicit_user_approval",
    "do_not_close_master_issue_after_single_stage",
)


def unique_object(pairs: list[tuple[str, Any]]) -> dict:
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("Ambiguous duplicate JSON checkpoint key")
        obj[key] = value
    return obj


def load_checkpoint(path: Path = STATE) -> dict:
    if path.stat().st_size > 30_000:
        raise ValueError("Checkpoint must be small: not a raw data dump")
    result = json.loads(path.read_text(encoding="utf-8"),
                        object_pairs_hook=unique_object,
                        parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    if type(result) is not dict:
        raise ValueError("Checkpoint is not a JSON object")
    return result


def valid_nonempty_text(value: object) -> bool:
    return type(value) is str and bool(value.strip()) and len(value) < 5000


def validate_state(s: dict) -> dict:
    if type(s) is not dict:
        raise ValueError("Expected checkpoint object")
    expected = {
        "schema_version": "robot-detector-autonomous-state-v1",
        "repository": OWNER,
        "project_root": "projects/robot-detector",
        "branch": BRANCH,
        "master_issue": MASTER_ISSUE,
        "research_contract": "docs/AUTONOMOUS_RESEARCH_TZ.md",
    }
    for key, value in expected.items():
        if s.get(key) != value:
            raise ValueError(f"Autonomous project identity/protocol changed: {key}")
    if s.get("status") not in STATES:
        raise ValueError("Unknown overall research status")
    if not re.fullmatch(r"20\d\d-\d\d-\d\d", str(s.get("updated_utc_date", ""))):
        raise ValueError("Missing calendar date for checkpoint")
    head = s.get("last_verified_base_commit")
    if type(head) is not str or not re.fullmatch(r"[0-9a-f]{40}", head):
        raise ValueError("No traceable base SHA: cannot safely resume")
    active = s.get("current_stage")
    if type(active) is not dict or not re.fullmatch(
        r"RD-[A-Z0-9-]+", str(active.get("id", ""))
    ):
        raise ValueError("Current stage is missing or invalid")
    if active.get("status") not in STAGE_STATES:
        raise ValueError("Current stage is not actionable")
    if not all(valid_nonempty_text(active.get(k))
               for k in ("title", "why_next")):
        raise ValueError("Current work missing scientific purpose")
    for key in ("inputs", "deliverables", "acceptance"):
        items = active.get(key)
        if (type(items) is not list or len(items) == 0
                or not all(valid_nonempty_text(x) for x in items)):
            raise ValueError(f"Actionable stage lacks {key}")
    backlog = s.get("backlog")
    if type(backlog) is not list or not backlog:
        raise ValueError("Need concrete additional unblocked steps")
    ids = {active["id"]}
    for task in backlog:
        if (type(task) is not dict
                or not re.fullmatch(r"RD-[A-Z0-9-]+",str(task.get("id","")))
                or task["id"] in ids
                or task.get("status") not in {"QUEUED", "BLOCKED", "DONE"}
                or type(task.get("priority")) is not int
                or not 1 <= task["priority"] <= 5
                or not valid_nonempty_text(task.get("title"))):
            raise ValueError("Invalid, ambiguous or duplicate next stage")
        ids.add(task["id"])
    results = s.get("last_known_verified_results")
    if type(results) is not list or not results:
        raise ValueError("No source-grounded verified research evidence")
    for record in results:
        if (type(record) is not dict
                or not all(valid_nonempty_text(record.get(k)) for k in
                           ("stage_id", "evidence_url", "result", "status"))
                or not record["evidence_url"].startswith("https://github.com/")):
            raise ValueError("Missing independently inspectable evidence")
    block = s.get("blockers")
    if type(block) is not list:
        raise ValueError("Unknown missing-data/truth blockers")
    for item in block:
        if (type(item) is not dict
                or not all(valid_nonempty_text(item.get(k))
                           for k in ("scope", "status", "safe_workaround"))):
            raise ValueError("Blockers require explicit independent alternative")
    controls = s.get("operational_constraints")
    if type(controls) is not dict or any(
        controls.get(name) is not True for name in REQUIRED_TRUE
    ):
        raise ValueError("Research autonomy guardrail was removed")
    if not valid_nonempty_text(s.get("resume_instruction")):
        raise ValueError("No precise recovery procedure")
    if not valid_nonempty_text(s.get("last_session_result")):
        raise ValueError("No prior verified progress summary")
    if s["status"] == "ACTIVE_RESEARCH_NOT_RELEASED" and (
        active["status"] == "DONE_PENDING_FOLLOW_ON"
        and not any(x["status"] == "QUEUED" for x in backlog)
    ):
        raise ValueError("All current tasks done but future step not selected")
    if not TZ.is_file():
        raise ValueError("Operational research TZ missing from repository")
    return {
        "status": s["status"],
        "current_stage_id": active["id"],
        "current_stage_title": active["title"],
        "current_stage_status": active["status"],
        "available_queued_followups": sum(x["status"]=="QUEUED" for x in backlog),
        "master_issue": MASTER_ISSUE,
        "base_sha": head,
        "can_resume_from_checkpoint": True,
        "is_background_daemon_running": False,
        "scientific_final_goal_already_verified":
            s["status"] == "RELEASE_GATE_AUDITED",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state",type=Path,default=STATE)
    args=parser.parse_args()
    summary=validate_state(load_checkpoint(args.state))
    print("AUTONOMOUS_RESEARCH_CHECKPOINT_VALIDATED",
          json.dumps(summary,sort_keys=True))


if __name__ == "__main__":
    main()
