#!/usr/bin/env python3
"""Read-only provenance gate for already-spent synthetic research seeds.

A "not in this project ledger" result is NOT evidence that a seed is globally
unseen, nor permission to claim a fresh blind evaluation. This script does
not run a simulator, inspect accounts, change frozen results or place orders.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "research" / "seed_registry.json"


def _seed_sequence(values: Any, *, label: str) -> tuple[int, ...]:
    if (not isinstance(values, list) or not values or
        any(type(x) is not int or x < 0 for x in values) or
        len(values) != len(set(values))):
        raise ValueError(f"{label}: require distinct nonnegative integer seeds")
    return tuple(values)


def read_ledger(path: Path = LEDGER) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if data.get("schema_version") != "market-robot-detector-seed-ledger-v1":
        raise ValueError("Unsupported or unknown seed provenance schema")
    studies = data.get("studies")
    if not isinstance(studies, list) or not studies:
        raise ValueError("Missing list of canonical synthetic studies")
    seen: dict[int, str] = {}
    ids: set[str] = set()
    canon: dict[str, tuple[int, ...]] = {}
    for study in studies:
        sid = study.get("id")
        if not isinstance(sid, str) or not sid or sid in ids:
            raise ValueError("Study ID is missing or repeated")
        if study.get("kind") not in ("genuine_abides", "constructed_toy"):
            raise ValueError(f"{sid}: unsupported research source kind")
        if study.get("phase") not in ("development", "evaluated", "illustrative"):
            raise ValueError(f"{sid}: unsupported spent-seed study phase")
        seeds = _seed_sequence(study.get("seeds"), label=sid)
        for seed in seeds:
            if seed in seen:
                raise ValueError(
                    f"Seed {seed} improperly duplicated between "
                    f"canonical studies {seen[seed]} and {sid}")
            seen[seed] = sid
        ids.add(sid)
        canon[sid] = seeds
        if ("source_file" in study) != ("source_constant" in study):
            raise ValueError(f"{sid}: source file and constant must be paired")

    replays = data.get("replays", [])
    if not isinstance(replays, list):
        raise ValueError("Replay declaration is not a list")
    replay_ids: set[str] = set()
    for replay in replays:
        sid = replay.get("study_id")
        parent = replay.get("canonical_study_id")
        if (not isinstance(sid, str) or not sid or sid in ids
            or sid in replay_ids or parent not in canon
            or replay.get("classification") != "non_independent_development_replay"):
            raise ValueError("Untracked, duplicated, or falsely independent replay")
        replay_ids.add(sid)
        if _seed_sequence(replay.get("seeds"), label=sid) != canon[parent]:
            raise ValueError(f"{sid}: replay must use the entire canonical spent seed set")
    return data


def _literal_assignment(source_file: Path, name: str) -> tuple[int, ...]:
    if not name.isidentifier():
        raise ValueError("Invalid Python constant name")
    tree = ast.parse(source_file.read_text(encoding="utf-8"), filename=str(source_file))
    candidates = []
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == name for t in stmt.targets):
                candidates.append(stmt.value)
        elif isinstance(stmt, ast.AnnAssign):
            if isinstance(stmt.target, ast.Name) and stmt.target.id == name:
                candidates.append(stmt.value)
    if len(candidates) != 1:
        raise ValueError(f"{source_file.name}: exactly one frozen {name} assignment required")
    try:
        value = ast.literal_eval(candidates[0])
    except (ValueError, TypeError, SyntaxError, MemoryError) as exc:
        raise ValueError(f"{source_file.name}: frozen {name} must be a literal") from exc
    if not isinstance(value, (tuple, list)):
        raise ValueError("Frozen seed constant must be tuple/list")
    return _seed_sequence(list(value), label=f"{source_file.name}.{name}")


def audit_sources(ledger: dict[str, Any], root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    checked = []
    for study in ledger["studies"]:
        if "source_file" not in study:
            continue
        sid = study["id"]
        relative = Path(study["source_file"])
        file = (root / relative).resolve()
        if relative.is_absolute() or not file.is_relative_to(root) or not file.is_file():
            raise ValueError(f"{sid}: source path missing or outside project root")
        literal = _literal_assignment(file, study["source_constant"])
        expected = _seed_sequence(study["seeds"], label=sid)
        if literal != expected:
            raise ValueError(f"{sid}: source constant drifted from historical seed ledger")
        checked.append(sid)
    used = sum(len(x["seeds"]) for x in ledger["studies"])
    return {
        "schema_version": "market-robot-detector-seed-audit-v1",
        "canonical_studies": len(ledger["studies"]),
        "canonical_spent_seeds": used,
        "source_constant_checks": checked,
        "non_independent_replay_groups": len(ledger.get("replays", [])),
        "globally_unused_seeds_verified": False,
        "blind_evaluation_reuse_allowed": False,
        "no_private_data_accessed": True,
    }


def assess_proposed_seeds(ledger: dict[str, Any], proposed: list[int]) -> dict[str, Any]:
    candidates = _seed_sequence(proposed, label="proposed")
    already = {int(seed): x["id"] for x in ledger["studies"] for seed in x["seeds"]}
    overlaps = [{"seed": seed, "spent_study": already[seed]}
                for seed in candidates if seed in already]
    return {
        "requested_seeds": list(candidates),
        "known_spent_overlap": overlaps,
        "eligible_for_claim_of_fresh_blind_test": False,
        "not_previously_listed_in_project_ledger": not overlaps,
        "globally_unused_or_unseen_elsewhere_verified": False,
        "interpretation": (
            "No local ledger collision is only a preliminary check; "
            "freshness needs separate preregistration and evidence."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-seeds", nargs="+", type=int, default=None)
    args = parser.parse_args()
    registry = read_ledger()
    report = audit_sources(registry)
    print("SEED_PROVENANCE_AUDIT", json.dumps(report, sort_keys=True))
    if args.candidate_seeds is not None:
        result = assess_proposed_seeds(registry, args.candidate_seeds)
        print("SEED_CANDIDATE_REVIEW", json.dumps(result, sort_keys=True))
        if result["known_spent_overlap"]:
            raise SystemExit(2)


if __name__ == "__main__":
    main()
