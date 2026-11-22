"""Source-free public original-run structural identity for ns message/book scoring.

Prospective: docs/CONDITIONAL_NS_PUBLIC_SOURCE_FINGERPRINT_PREREG_20261122.md
SHA equality is NOT a provider-signed or globally independent source proof.
No raw vendor rows, account, order or agent identifiers are exported.
"""
from dataclasses import dataclass
from hashlib import sha256
import json
import re

from tools.public_intensity_rescaling import Abstain
from tools.public_lobster_ns_time import UNIT
from tools.public_ns_visible_exec_projector import (
    NsVisibleExecutionAndPostEventBBO, project_public_ns_visible_executions,
)
from tools.public_m1_v3_ns_l2 import NsEvaluationWindow
from tools.public_ns_visible_integrated_ll import score_same_source_visible_exec_ns

_HASH_RE=re.compile(r"[0-9a-f]{64}")
_RUN_RE=re.compile(r"[A-Za-z0-9_.-]{1,128}")
_SCHEMA=b"robot-detector-public-ns-message-book-v1\n"
_PROJECTION_SCHEMA=b"robot-detector-projected-visible-ns-v1\n"
MAX_REGISTRY_RUNS=1000


@dataclass(frozen=True)
class BoundPublicNsSource:
    original_run_label: str
    source_public_sha256: str
    projected_public_sha256: str
    projection: NsVisibleExecutionAndPostEventBBO


@dataclass(frozen=True)
class BoundNsEvaluation:
    original_run_label: str
    expected_source_public_sha256: str
    evaluation_window: NsEvaluationWindow


def _canonical_digest(prefix, records):
    h=sha256(prefix)
    for record in records:
        h.update(json.dumps(record,sort_keys=True,separators=(",",":"),
                            ensure_ascii=True,allow_nan=False).encode("ascii"))
        h.update(b"\n")
    return h.hexdigest()


def _projected_digest(projection):
    if type(projection) is not NsVisibleExecutionAndPostEventBBO:
        raise Abstain("INVALID_BOUND_PROJECTION")
    return _canonical_digest(_PROJECTION_SCHEMA,(
        {"unit":projection.unit},
        {"visible_timestamp_clusters_ns":projection.visible_type4_trade_cluster_times_ns},
        {"post_event_bbo":projection.post_event_bbo_snapshots},
        {"safe_aggregate":projection.safe_aggregate},
    ))


def bind_public_ns_source(
    paired_rows, *, original_run_label, source_time_unit=UNIT,
    source_precision_ns=1, interval_complete=True,
):
    """Bind exact PUBLIC message events to their POST-event books internally."""
    if type(original_run_label) is not str or _RUN_RE.fullmatch(original_run_label) is None:
        raise Abstain("INVALID_OR_SENSITIVE_ORIGINAL_SOURCE_LABEL")
    projection=project_public_ns_visible_executions(
        paired_rows,source_time_unit=source_time_unit,
        source_precision_ns=source_precision_ns,interval_complete=interval_complete,
    )
    canonical_sha=_canonical_digest(_SCHEMA,paired_rows)
    return BoundPublicNsSource(
        original_run_label,canonical_sha,_projected_digest(projection),projection,
    )


def score_bound_public_ns_source(bound_source, trained_model, bound_evaluation):
    """Structural tape/quote consistency; never a source authenticity claim."""
    if type(bound_source) is not BoundPublicNsSource or type(bound_evaluation) is not BoundNsEvaluation:
        raise Abstain("MISSING_BOUND_PUBLIC_SOURCE_OR_EVALUATION")
    if (type(bound_source.original_run_label) is not str or
        _RUN_RE.fullmatch(bound_source.original_run_label) is None or
        type(bound_evaluation.original_run_label) is not str or
        bound_evaluation.original_run_label != bound_source.original_run_label or
        type(bound_source.source_public_sha256) is not str or
        _HASH_RE.fullmatch(bound_source.source_public_sha256) is None or
        bound_evaluation.expected_source_public_sha256 != bound_source.source_public_sha256):
        raise Abstain("ORIGINAL_SOURCE_RUN_OR_PUBLIC_TAPE_DIGEST_MISMATCH")
    if (type(bound_source.projected_public_sha256) is not str or
        _HASH_RE.fullmatch(bound_source.projected_public_sha256) is None or
        _projected_digest(bound_source.projection) != bound_source.projected_public_sha256):
        raise Abstain("PUBLIC_SOURCE_PROJECTION_MUTATED_AFTER_BINDING")
    window=bound_evaluation.evaluation_window
    if type(window) is not NsEvaluationWindow or window.run_id != bound_source.original_run_label:
        raise Abstain("EVAL_WINDOW_SOURCE_ID_DOES_NOT_MATCH_BOUND_ORIGINAL_RUN")
    actual=score_same_source_visible_exec_ns(
        bound_source.projection,trained_model,window,
    )
    return {
        **actual,
        "source_binding_status":"STRUCTURAL_PUBLIC_DIGEST_MATCH_NOT_ORIGIN_AUTHENTICATED",
        "source_globally_independent_verified":False,
        "original_market_feed_completeness_verified":False,
    }


def audit_structural_unique_bound_sources(sources):
    """Catch replay aliases; not a generator or validator of globally fresh seeds."""
    if type(sources) not in (list,tuple) or not 1<=len(sources)<=MAX_REGISTRY_RUNS:
        raise Abstain("INVALID_OR_EXCESSIVE_SOURCE_REGISTRY")
    ids=set()
    hashes=set()
    for s in sources:
        if type(s) is not BoundPublicNsSource:
            raise Abstain("INVALID_SOURCE_REGISTRY_ENTRY")
        if (type(s.original_run_label) is not str or _RUN_RE.fullmatch(s.original_run_label) is None or
            type(s.source_public_sha256) is not str or
            _HASH_RE.fullmatch(s.source_public_sha256) is None or
            type(s.projected_public_sha256) is not str or
            _projected_digest(s.projection) != s.projected_public_sha256):
            raise Abstain("INVALID_OR_MUTATED_SOURCE_REGISTRY_PROVENANCE")
        if s.original_run_label in ids or s.source_public_sha256 in hashes:
            raise Abstain("DEPENDENT_REPLAY_ID_OR_PUBLIC_TAPE_ALIAS")
        ids.add(s.original_run_label)
        hashes.add(s.source_public_sha256)
    return {
        "status":"STRUCTURAL_PUBLIC_ONLY_PROVENANCE_NOT_AUTHENTICATED",
        "source_labels":len(ids),
        "distinct_public_source_fingerprints":len(hashes),
        "real_market_fdr_known":False,
        "globally_independent_source_worlds_verified":False,
        "physical_owner_identity_known":False,
    }
