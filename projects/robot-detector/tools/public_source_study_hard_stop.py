"""Source study planning NO-GO; NEVER authorizes data access or execution.

Precommitted: docs/NS_SOURCE_STUDY_HARD_STOP_PREREG_20261122.md.
Self-declared external evidence does not establish source authenticity/license.
"""
from tools.public_intensity_rescaling import Abstain

SOURCE_FAMILIES = frozenset({
    "ABIDES_SIMULATOR", "LOBSTER_PUBLIC_DEMO", "BINANCE_TRADE_ONLY",
    "COINBASE_MARKET_DATA", "MOEX_ISS_HISTORY",
})
PHASES = frozenset({"INDEPENDENT_SOURCE_STUDY", "REAL_MARKET_RELEASE"})
EVIDENCE_FIELDS = (
    "provider_research_rights",
    "immutable_source_revision",
    "unit_safe_source_clock",
    "trade_event_definition",
    "exchange_event_completeness",
    "causal_l2_coverage",
    "original_world_train_cal_eval_split",
    "power_and_resource_adequacy",
    "frozen_models_and_thresholds",
)
EVIDENCE_STATES = frozenset({"UNKNOWN", "FAILED", "DOCUMENTED_EXTERNAL"})
SOURCE_RESTRICTIONS = {
    "LOBSTER_PUBLIC_DEMO": "HISTORICAL_DEMO_TRADE_ONLY_CLOCK_AND_COMPLETENESS_NOT_ATTESTED",
    "BINANCE_TRADE_ONLY": "NO_SYNCHRONIZED_HISTORICAL_L2_FOR_THIS_SOURCE",
    "COINBASE_MARKET_DATA": "EXPRESS_WRITTEN_PERMISSION_FOR_AI_ALGORITHM_RESEARCH_NOT_ESTABLISHED",
    "MOEX_ISS_HISTORY": "FULL_L2_AND_NON_DISPLAY_MARKET_DATA_RIGHTS_NOT_ESTABLISHED",
}


def source_study_planning_hard_stop(manifest):
    """Read only exactly specified planning flags, NEVER grant execution."""
    if type(manifest) is not dict or set(manifest) != {"source_family","study_phase","evidence"}:
        raise Abstain("INVALID_OR_PRIVILEGED_SOURCE_STUDY_MANIFEST")
    family, phase, evidence = (manifest["source_family"],manifest["study_phase"],
                               manifest["evidence"])
    if type(family) is not str or family not in SOURCE_FAMILIES:
        raise Abstain("UNKNOWN_OR_FORBIDDEN_SOURCE_FAMILY")
    if type(phase) is not str or phase not in PHASES:
        raise Abstain("UNKNOWN_OR_FORBIDDEN_STUDY_PHASE")
    if type(evidence) is not dict or set(evidence) != set(EVIDENCE_FIELDS):
        raise Abstain("MISSING_OR_FORBIDDEN_EXTERNAL_SOURCE_EVIDENCE")
    for field in EVIDENCE_FIELDS:
        if type(evidence[field]) is not str or evidence[field] not in EVIDENCE_STATES:
            raise Abstain("INVALID_OR_SELF_AUTHORIZING_SOURCE_EVIDENCE_STATUS")

    outstanding = tuple(k for k in EVIDENCE_FIELDS if evidence[k] != "DOCUMENTED_EXTERNAL")
    failed = tuple(k for k in EVIDENCE_FIELDS if evidence[k] == "FAILED")
    provider_condition = SOURCE_RESTRICTIONS.get(family)
    if phase == "REAL_MARKET_RELEASE":
        provider_condition = "NO_INDEPENDENT_REAL_MARKET_PHYSICAL_OWNER_TRUTH_OR_FDR"
    if outstanding or provider_condition:
        study_state = "BLOCKED_EVIDENCE"
    else:
        study_state = "STRUCTURAL_EVIDENCE_DOCUMENTED_EXTERNAL_REVIEW_STILL_REQUIRED"
    return {
        "status": study_state,
        "execution_authorization": "NOT_AUTHORIZED_FOR_SOURCE_EXECUTION",
        "source_family": family,
        "study_phase": phase,
        "prerequisite_count": len(EVIDENCE_FIELDS),
        "externally_documented_claim_count": len(EVIDENCE_FIELDS)-len(outstanding),
        "missing_or_failed_evidence_fields": outstanding,
        "explicitly_failed_evidence_fields": failed,
        "source_or_release_specific_blocker": provider_condition,
        "all_documentation_claims_source_authenticated_by_tool": False,
        "original_source_worlds_generated": 0,
        "real_market_fdr_known": False,
        "physical_owner_identity_known": False,
        "provider_data_rights_granted_by_tool": False,
    }


def current_project_ns_study_no_go():
    """Frozen evidence-only snapshot: prior toy CI is not source attestation."""
    evidence = {key:"UNKNOWN" for key in EVIDENCE_FIELDS}
    return source_study_planning_hard_stop({
        "source_family":"ABIDES_SIMULATOR",
        "study_phase":"INDEPENDENT_SOURCE_STUDY",
        "evidence":evidence,
    })
