"""Existing genuine ABIDES 160-case COMPACT aggregate cannot re-score M1-v4.

Prereg: docs/ABIDES_COMPACT_160_REANALYSIS_IMPOSSIBILITY_PREREG_20261122.md
Read only committed source metadata, never download original engine tapes.
"""
import json
from pathlib import Path
import re

from tools.public_intensity_rescaling import Abstain

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/"fixtures"/"abides_grid_160_source_aggregate_reconciled_20261121.json"
REVISION="ac7a2a7bf6e406cd2bbed887e22c5a5a790bb242"
SOURCE_SHA="55394e5dfda274613cb081ee4ad44e9b2b8e051eb2e0f0c361e4ee8016431d62"
COHORTS=(
    "poisson_noise_null","fixed_20s_noise_hard_negative",
    "momentum_noise_hard_negative","twap_45s_positive",
)
ROOT_KEYS=frozenset((
    "schema_version","classification","source_engine","engine_revision",
    "precommitted_protocol","precommitted_protocol_blob_sha",
    "pre_source_zero_fill_addendum","original_source_run","original_source_commit",
    "original_artifact_id","repeat_same_seeds_source_run",
    "repeat_same_seeds_artifact_id","original_uncompressed_full_source_json_sha256",
    "repeat_uncompressed_full_source_json_sha256","source_full_case_count",
    "seeds","default_source_classification","source_cohorts","totals",
    "interpretation_flags","notes",
))
COHORT_KEYS=frozenset((
    "public_prints","unique_execution_timestamps","l2_snapshots",
    "posthoc_twap_fills","naive_positive_seeds","grouped_positive_seeds",
    "naive_abstain_seeds","grouped_abstain_seeds","type",
))
TWAP_KEYS=COHORT_KEYS|frozenset(("grouped_missed_twap_seeds",))


def _seed_mask(xs,spent):
    if type(xs) is not list or any(type(z) is not int or z not in spent for z in xs):
        raise Abstain("MALFORMED_SPENT_ABIDES_SOURCE_CASE_SEED_MASK")
    if len(set(xs))!=len(xs):
        raise Abstain("DUPLICATE_ABIDES_SOURCE_CASE_SEED_MASK")
    return len(xs)


def audit_compact_160_source_reanalysis_possible(aggregate):
    """Negative source-information sufficiency check; no model evaluation."""
    if type(aggregate) is not dict or set(aggregate)!=ROOT_KEYS:
        raise Abstain("MALFORMED_OR_UNEXPECTED_RAW_ABIDES_AGGREGATE_FIELD")
    if (aggregate["schema_version"]!="genuine-abides-160-original-compact-reconciled-v1" or
        aggregate["engine_revision"]!=REVISION or
        type(aggregate["source_full_case_count"]) is not int or
        aggregate["source_full_case_count"]!=160 or
        aggregate["original_source_run"]!=44944144915 or
        aggregate["repeat_same_seeds_source_run"]!=44944168231):
        raise Abstain("UNPINNED_OR_INCONSISTENT_ORIGINAL_ABIDES_SOURCE")
    if (aggregate["original_uncompressed_full_source_json_sha256"]!=SOURCE_SHA or
        aggregate["repeat_uncompressed_full_source_json_sha256"]!=SOURCE_SHA):
        raise Abstain("ORIGINAL_AND_REPLAY_ABIDES_SOURCE_PROVENANCE_NOT_EQUAL")
    seeds=aggregate["seeds"]
    if type(seeds) is not list or seeds!=list(range(3301,3341)):
        raise Abstain("SPENT_ABIDES_SOURCE_SEED_LEDGER_DRIFT")
    required_flags=aggregate["interpretation_flags"]
    expected_flags=(
        "not_real_market_data","real_market_FDR_unknown",
        "physical_owner_identity_unknown",
        "repeat_is_not_160_additional_independent_cases",
        "method_threshold_phase_and_seed_selection_unchanged",
        "source_positive_eligibility_and_abstentions_explicit",
        "original_raw_events_and_private_agent_ids_not_in_fixture",
    )
    if type(required_flags) is not dict or any(required_flags.get(k) is not True for k in expected_flags):
        raise Abstain("ABIDES_HISTORICAL_SOURCE_LIMITATIONS_LOST")
    totals=aggregate["totals"]
    expected_totals={
        "source_public_prints":156234,
        "source_unique_execution_timestamps":144908,
        "source_L2_snapshots":253386,
        "source_posthoc_controlled_TWAP_fills":617,
    }
    if type(totals) is not dict or totals!=expected_totals:
        raise Abstain("ORIGINAL_ABIDES_PUBLIC_SOURCE_AGGREGATE_TOTALS_DRIFT")
    cohort=aggregate["source_cohorts"]
    if type(cohort) is not dict or set(cohort)!=set(COHORTS):
        raise Abstain("ORIGINAL_ABIDES_PUBLIC_BACKGROUND_COHORTS_MISSING")
    counts=[]
    sums=[0,0,0]
    for name in COHORTS:
        record=cohort[name]
        if type(record) is not dict or set(record)!=(TWAP_KEYS if name==COHORTS[3] else COHORT_KEYS):
            raise Abstain("MALFORMED_OR_UNEXPECTED_ABIDES_COHORT_RAW_EVENT_DATA")
        if record["l2_snapshots"] is not None:
            raise Abstain("NEW_ABIDES_UNPREGISTERED_SOURCE_L2_SERIES_IN_COMPACT_FILE")
        if record["type"]!=("injected_positive" if name==COHORTS[3] else "negative"):
            raise Abstain("HISTORICAL_ABIDES_SOURCE_COHORT_LABEL_CHANGED")
        for i,k in enumerate(("public_prints","unique_execution_timestamps","posthoc_twap_fills")):
            if type(record[k]) is not int or record[k]<0:
                raise Abstain("ABIDES_SOURCE_COHORT_COUNT_NOT_A_POSITIVE_INT")
            sums[i]+=record[k]
        masks={k:_seed_mask(record[k],seeds) for k in (
            "naive_positive_seeds","grouped_positive_seeds",
            "naive_abstain_seeds","grouped_abstain_seeds")}
        counts.append(masks)
        if name==COHORTS[3]:
            if _seed_mask(record["grouped_missed_twap_seeds"],seeds)!=7:
                raise Abstain("ORIGINAL_TWAP_MISSES_NOT_PRESERVED")
        elif record["posthoc_twap_fills"]!=0:
            raise Abstain("HARD_NEGATIVE_ORACLE_FILLS_ARE_NONZERO")
    if sums != [156234,144908,617] or [
        (x["naive_positive_seeds"],x["grouped_positive_seeds"],
         x["naive_abstain_seeds"],x["grouped_abstain_seeds"])
        for x in counts
    ] != [(7,6,0,0),(0,0,1,1),(7,7,0,0),(39,32,1,1)]:
        raise Abstain("ORIGINAL_ABIDES_NEGATIVE_OUTCOMES_OR_COHORT_SUMS_DRIFT")
    return {
        "status":"ORIGINAL_ABIDES_160_COMPACT_NOT_REANALYZABLE_FOR_M1V4",
        "original_synthetic_matching_engine_case_count":160,
        "original_seed_world_count":40,
        "independent_worlds_added_by_repeat":0,
        "previous_public_execution_rows":156234,
        "previous_unique_public_execution_timestamps":144908,
        "previous_L2_snapshot_count_aggregate_only":253386,
        "previous_grouped_poisson_false_alarms_of_40":6,
        "previous_grouped_momentum_false_alarms_of_40":7,
        "previous_grouped_fixed_false_alarms_of_40":0,
        "previous_grouped_TWAP_positive_of_40":32,
        "previous_grouped_TWAP_missed_cases":7,
        "previous_grouped_TWAP_abstentions":1,
        "public_exact_execution_timestamp_vector_stored":False,
        "source_aligned_L2_quote_timestamp_and_price_vectors_stored":False,
        "new_M1v4_original_source_LL_reconstructable":False,
        "source_original_case_replay_is_independent":False,
        "new_original_engine_source_cases_executed":0,
        "physical_owner_identity_known":False,
        "real_market_fdr_known":False,
        "raw_public_market_rows_or_private_agent_IDs_exported":False,
    }


def read_existing_compact_160_source_only(path=FIXTURE):
    try:
        obj=json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError,ValueError,TypeError,UnicodeError) as exc:
        raise Abstain("MISSING_OR_INVALID_LOCAL_ORIGINAL_SOURCE_COMPACT_FIXTURE") from exc
    return audit_compact_160_source_reanalysis_possible(obj)


if __name__=="__main__":
    print(json.dumps(read_existing_compact_160_source_only(),sort_keys=True))
