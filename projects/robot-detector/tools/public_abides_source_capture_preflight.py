"""Source-free ABIDES public capture-profile preflight; NEVER an execution grant.

Previously frozen docs/ABIDES_SOURCE_CAPTURE_PREFLIGHT_PREREG_20261122.md
Source-family typed metadata, not an authenticated original matching-engine job.
"""
from datetime import datetime
import re

from tools.public_intensity_rescaling import Abstain
from tools.public_abides_epoch_ns_clock import PINNED_REVISION,SOURCE_UNIT

PROFILE_FIELDS=frozenset((
    "original_source_run_label","source_family","pinned_revision",
    "configured_simulation_date","simulator_clock_unit",
    "configured_start_HHMMSS","configured_end_HHMMSS",
    "requested_result_profiles","public_l2_capture_mode",
    "requested_l2_depth_per_side","original_source_role",
    "source_coverage_attestation","source_artifact_checksum_attestation",
    "external_license_rights_attestation",
    "independent_source_world_provenance_attestation",
))
ATTESTATION_FIELDS=(
    "source_coverage_attestation","source_artifact_checksum_attestation",
    "external_license_rights_attestation",
    "independent_source_world_provenance_attestation",
)
ATTESTATION_STATUSES=frozenset(("UNKNOWN","EXTERNALLY_DOCUMENTED","FAILED"))


def audit_abides_source_capture_profile_preflight(record):
    """Check a prospective public source manifest; never authorize workflow."""
    if type(record) is not dict or set(record)!=PROFILE_FIELDS:
        raise Abstain("PRIVATE_OR_INCOMPLETE_ABIDES_SOURCE_CAPTURE_PROFILE")
    rid=record["original_source_run_label"]
    if type(rid) is not str or re.fullmatch(r"[A-Za-z0-9_.-]{1,128}",rid) is None:
        raise Abstain("INVALID_OR_SENSITIVE_ORIGINAL_SOURCE_LABEL")
    if (type(record["source_family"]) is not str or record["source_family"]!="ABIDES_SIMULATOR" or
        type(record["pinned_revision"]) is not str or record["pinned_revision"]!=PINNED_REVISION or
        type(record["simulator_clock_unit"]) is not str or record["simulator_clock_unit"]!=SOURCE_UNIT):
        raise Abstain("UNPINNED_OR_MIXED_ABIDES_SOURCE_FAMILY_CLOCK")
    day=record["configured_simulation_date"]
    if type(day) is not str or re.fullmatch(r"[0-9]{8}",day) is None:
        raise Abstain("MISSING_UNTYPED_SIMULATED_UTC_DAY")
    try:
        date=datetime.strptime(day,"%Y%m%d").date()
    except ValueError as exc:
        raise Abstain("INVALID_SIMULATED_UTC_DAY") from exc
    if date.strftime("%Y%m%d")!=day or not 1970<=date.year<=2262:
        raise Abstain("UNSUPPORTED_SOURCE_UTC_DAY")
    if (type(record["configured_start_HHMMSS"]) is not str or
        type(record["configured_end_HHMMSS"]) is not str or
        record["configured_start_HHMMSS"]!="09:30:00" or
        record["configured_end_HHMMSS"]!="09:38:00"):
        raise Abstain("UNMATCHED_FROZEN_SOURCE_FREE_ABIDES_SESSION")
    profiles=record["requested_result_profiles"]
    if (type(profiles) not in (list,tuple) or len(profiles)!=2 or
        any(type(p) is not str for p in profiles) or
        set(profiles)!={"TRADE_ATTRIBUTION","L2_SERIES"}):
        raise Abstain("MISSING_PUBLIC_EXEC_L2_OR_PRIVATE_PROFILE_REQUESTED")
    if (type(record["public_l2_capture_mode"]) is not str or record["public_l2_capture_mode"]!="sparse_l2" or
        type(record["requested_l2_depth_per_side"]) is not int or record["requested_l2_depth_per_side"]!=5):
        raise Abstain("INVALID_ABIDES_PUBLIC_SPARSE_BOOK_CAPTURE_CONFIGURATION")
    role=record["original_source_role"]
    if type(role) is not str or role not in ("train","calibration","evaluation"):
        raise Abstain("MISSING_OR_UNDEFINED_ORIGINAL_SOURCE_ROLE")
    for key in ATTESTATION_FIELDS:
        if type(record[key]) is not str or record[key] not in ATTESTATION_STATUSES:
            raise Abstain("INVALID_OR_SELF_AUTHORIZING_EXTERNAL_EVIDENCE_STATUS")
    blockers=tuple(k for k in ATTESTATION_FIELDS if record[k]!="EXTERNALLY_DOCUMENTED")
    failed=tuple(k for k in ATTESTATION_FIELDS if record[k]=="FAILED")
    return {
        "status":"STRUCTURAL_PUBLIC_ABIDES_SOURCE_PROFILE_ONLY_NO_SOURCE_AUTHORIZATION",
        "source_family":"ABIDES_SIMULATOR",
        "simulator_public_clock_unit":SOURCE_UNIT,
        "source_profile_requests_matched_EXEC_and_sparse_L2":True,
        "metadata_profile_structurally_valid":True,
        "configured_UTC_day_externally_authenticated":False,
        "original_world_provenance_externally_verified_by_this_checker":False,
        "external_attestation_claim_count":len(ATTESTATION_FIELDS)-len(blockers),
        "missing_or_failed_external_attestation_fields":blockers,
        "explicitly_failed_external_attestation_fields":failed,
        "original_source_role_structure_only":role,
        "original_source_experiment_authorized":False,
        "original_independent_source_study_ready":False,
        "sample_size_and_power_verified":False,
        "real_market_fdr_known":False,
        "physical_owner_identity_known":False,
        "original_simulator_runs_created":0,
        "raw_source_event_or_private_ids_exported":False,
    }
