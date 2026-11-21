#!/usr/bin/env python3
"""Retrospective exact small-N synthetic ABIDES matched-pair uncertainty audit.

NOT a new matching-engine run, source market p-value, or robot-owner estimate.
The original 3201–3204 source labels were already known when this audit was
designed. Report nominal Clopper-Pearson bounds only under a hypothetical IID
ABIDES seed-trial assumption, which deterministic local seed choice does not
certify. Use same 16 source tapes for both classification methods, not 32
independent market observations. Print-level fills are never IID seed trials.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from math import comb, isfinite
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PLAN=ROOT/"research"/"abides_matched_uncertainty_audit_protocol_20261121.json"
SOURCE=ROOT/"fixtures"/"abides_clustered_grid_original_20261121.json"
SEEDS=(3201,3202,3203,3204)
COHORTS=("poisson_noise_null","fixed_20s_noise_hard_negative",
         "momentum_noise_hard_negative","twap_45s_positive")
ALPHA=.05
CONFIDENCE=.95
METHODS=("naive","grouped")
STATUSES=("TARGET_PATTERN","NO_TARGET_PATTERN","ABSTAIN")
EXPECTED_SOURCE_SHA="e75c089f023a12bddd19c2f4cf33a64470a29aeb79125024877fb4a9997885e2"


ROOT_FIELDS = frozenset((
    "schema_version", "scientific_scope", "original_genuine_matching_engine_ci_run",
    "source_commit", "original_source_artifact_id", "original_source_artifact_name",
    "original_artifact_uncompressed_json_sha256", "source_precommit",
    "engine_revision", "local_seeds", "cohort_names", "independent_simulations",
    "totals", "original_cohort_aggregates", "original_all_16_case_public_summary",
    "source_only_public_negative_outcomes_preserved",
    "real_market_fdr_or_owner_accuracy_known",
    "original_raw_print_tapes_l2_or_agent_IDs_in_repo",
    "timestamp_grouping_does_not_identify_parent_order",
    "no_posthoc_threshold_or_phase_change"
))
CASE_FIELDS = frozenset((
    "cohort", "grouped_classification", "grouped_ratio",
    "max_same_timestamp_cluster", "naive_classification",
    "naive_per_print_ratio", "posthoc_TWAP_fills", "prints",
    "real_market_FDR_known", "seed", "source_L2", "unique_time_groups"
))
COHORT_FIELDS = frozenset((
    "extra_same_timestamp_prints_total", "grouped_timestamp_abstentions",
    "grouped_timestamp_false_alarms", "grouped_timestamp_missed_TWAP",
    "grouped_timestamp_positive_alarms",
    "independent_original_matching_engine_runs",
    "original_print_based_abstentions", "original_print_based_false_alarms",
    "original_print_based_missed_TWAP", "original_print_based_positive_alarms",
    "posthoc_controlled_TWAP_fills", "public_prints_total",
    "unique_event_timestamp_clusters_total"
))
TOTAL_FIELDS = frozenset((
    "public_execution_prints", "public_L2_snapshots",
    "unique_exchange_timestamps", "oracle_controlled_TWAP_executions"
))


def _exact_fields(value: dict, expected: frozenset, scope: str) -> None:
    """Fail closed on extra fields, including private IDs and raw source rows."""
    if type(value) is not dict or set(value) != expected:
        raise ValueError(f"Unexpected or missing source-only aggregate keys in {scope}")


def frozen_protocol()->dict:
    p=json.loads(PLAN.read_text(encoding="utf-8"))
    interval=p.get("exact_nominal_binomial_interval",{})
    if (
        p.get("schema_version")!="abides-exact-synthetic-four-seed-retrospective-uncertainty-v1"
        or p.get("stage")!="RD-MATCHED-UNCERTAINTY-14"
        or p.get("design_origin")!="RETROSPECTIVE_UNCERTAINTY_AUDIT_AFTER_ALL_3201_3204_OUTCOMES_OBSERVED"
        or p.get("new_source_replay")!="NONE"
        or p.get("original_source_run")!=44938991772
        or p.get("original_source_artifact_id")!=14720831681
        or p.get("original_source_uncompressed_json_sha256")!=EXPECTED_SOURCE_SHA
        or p.get("source_fixture")!="fixtures/abides_clustered_grid_original_20261121.json"
        or p.get("cohorts")!=list(COHORTS)
        or p.get("source_seed_values")!=list(SEEDS)
        or p.get("per_cohort_independent_engine_runs")!=4
        or interval.get("family")!="two-sided Clopper-Pearson"
        or interval.get("confidence_level")!=CONFIDENCE
        or interval.get("alpha")!=ALPHA
        or interval.get("bounds")!=[0,1]
        or interval.get("interpretation")!="nominal mathematical sensitivity only; not empirical real-market coverage"
        or p.get("method_pairing_key")!="same seed plus same cohort plus same original source tape"
        or p.get("source_snapshot_and_print_rows_not_independent_experimental_units") is not True
        or p.get("printed_100_fill_cluster_not_100_independent_owners") is not True
        or p.get("no_pvalue_or_bayesian_posterior_claim") is not True
        or p.get("no_real_market_FDR_precision_or_owner_identity_claim") is not True
        or p.get("no_threshold_selection_on_inspected_data") is not True
        or p.get("all_negative_source_cases_must_be_preserved") is not True
        or p.get("output_compact_aggregates_without_public_event_rows") is not True
    ):
        raise ValueError("Retrospective interval/matched source protocol drift")
    return p


def _binomial_cdf(k:int,n:int,p:float)->float:
    """P(X<=k); only tiny exact integer seed trial counts used here."""
    return sum(comb(n,i)*p**i*(1-p)**(n-i) for i in range(k+1))


def _binomial_tail(k:int,n:int,p:float)->float:
    """P(X>=k) for the same exact Bernoulli-trial mathematical assumption."""
    return sum(comb(n,i)*p**i*(1-p)**(n-i) for i in range(k,n+1))


def clopper_pearson(successes:int,trials:int,confidence:float=CONFIDENCE)->dict:
    if (type(successes) is not int or type(trials) is not int
        or trials!=4 or not 0<=successes<=trials
        or type(confidence) is not float or confidence!=CONFIDENCE):
        raise ValueError("Only frozen 4 source seed trials and nominal 95% level")
    a=(1-confidence)/2
    if successes==0: lower=0.0
    else:
        lo,hi=0.0,1.0
        for _ in range(90):
            mid=(lo+hi)/2
            if _binomial_tail(successes,trials,mid)<a:lo=mid
            else:hi=mid
        lower=(lo+hi)/2
    if successes==trials: upper=1.0
    else:
        lo,hi=0.0,1.0
        for _ in range(90):
            mid=(lo+hi)/2
            if _binomial_cdf(successes,trials,mid)>a:lo=mid
            else:hi=mid
        upper=(lo+hi)/2
    if not 0<=lower<=successes/trials<=upper<=1:
        raise AssertionError("Exact nominal binomial bounds inconsistent")
    return {
        "source_seed_trials":trials,
        "successes":successes,
        "observed_synthetic_fraction":round(successes/trials,8),
        "nominal_two_sided_confidence":confidence,
        "nominal_exact_CP_lower":round(lower,8),
        "nominal_exact_CP_upper":round(upper,8),
        "iid_simulation_seed_sampling_assumption_confirmed":False,
        "real_market_population_confidence_interval":False
    }


def validate_original_source_fixture(raw:dict)->list[dict]:
    _exact_fields(raw, ROOT_FIELDS, 'root')
    _exact_fields(raw.get('totals'), TOTAL_FIELDS, 'totals')
    if (type(raw) is not dict
        or raw.get("schema_version")!="genuine-abides-public-cluster-source-reconciled-v1"
        or raw.get("original_genuine_matching_engine_ci_run")!=44938991772
        or raw.get("source_commit")!="902fdeb30e1548ab3722aa97718947cd9a9468fd"
        or raw.get("engine_revision")!="ac7a2a7bf6e406cd2bbed887e22c5a5a790bb242"
        or raw.get("original_source_artifact_name")!="robot-detector-genuine-abides-16-timestamp-grouping-source-only"
        or raw.get("original_source_artifact_id")!=14720831681
        or raw.get("original_artifact_uncompressed_json_sha256")!=EXPECTED_SOURCE_SHA
        or raw.get("source_precommit")!="research/abides_clustered_grid_source_precommit_20261121.json"
        or raw.get("local_seeds")!=list(SEEDS)
        or raw.get("cohort_names")!=list(COHORTS)
        or raw.get("independent_simulations")!=16
        or raw.get("source_only_public_negative_outcomes_preserved") is not True
        or raw.get("real_market_fdr_or_owner_accuracy_known") is not False
        or raw.get("original_raw_print_tapes_l2_or_agent_IDs_in_repo") is not False
        or raw.get("timestamp_grouping_does_not_identify_parent_order") is not True
        or raw.get("no_posthoc_threshold_or_phase_change") is not True):
        raise ValueError("Original source identity/limitations are not verifiable")
    cases=raw.get("original_all_16_case_public_summary")
    if (type(cases) is not list or len(cases)!=16 or
        any(type(x) is not dict for x in cases) or
        {(x.get("seed"),x.get("cohort")) for x in cases}!=
        {(seed,cohort) for seed in SEEDS for cohort in COHORTS}):
        raise ValueError("Original source case list missing/duplicated/unexpected")
    totals=Counter()
    cohort_aggregates=raw.get("original_cohort_aggregates")
    if type(cohort_aggregates) is not dict or set(cohort_aggregates)!=set(COHORTS):
        raise ValueError("Source original cohort aggregates missing")
    for x in cases:
        _exact_fields(x, CASE_FIELDS, "per-seed source case")
        s,c=x["seed"],x["cohort"]
        label=c=="twap_45s_positive"
        n=x.get("prints")
        uniq=x.get("unique_time_groups")
        l2=x.get("source_L2")
        fills=x.get("posthoc_TWAP_fills")
        group=x.get("grouped_ratio")
        naive=x.get("naive_per_print_ratio")
        if (type(s) is not int or type(n) is not int or type(uniq) is not int
            or type(l2) is not int or type(fills) is not int
            or not 0<uniq<=n<=200_000 or not 0<l2<=250_000
            or (fills>0)!=label
            or type(group) not in (float,int) or type(naive) not in (float,int)
            or not all(isfinite(v) and v>=0 for v in (group,naive))
            or x.get("real_market_FDR_known") is not False
            or x.get("grouped_classification") not in STATUSES
            or x.get("naive_classification") not in STATUSES
            or x.get("max_same_timestamp_cluster",0)>n
            or type(x.get("max_same_timestamp_cluster")) is not int
            or x.get("max_same_timestamp_cluster")<1):
            raise ValueError("An original source public/label/coverage field is invalid")
        # Frozen 0.60 whole-session source decisions, no abstentions in source.
        if x["grouped_classification"]!=(
                "TARGET_PATTERN" if group>=.6 else "NO_TARGET_PATTERN"):
            raise ValueError("Original grouped source decision drifted")
        if x["naive_classification"]!=(
                "TARGET_PATTERN" if naive>=.6 else "NO_TARGET_PATTERN"):
            raise ValueError("Original per-print source decision drifted")
        totals["public_execution_prints"]+=n
        totals["public_L2_snapshots"]+=l2
        totals["unique_exchange_timestamps"]+=uniq
        totals["oracle_controlled_TWAP_executions"]+=fills
    if dict(totals)!=raw.get("totals"):
        raise ValueError("Original source case totals do not conserve")
    for c in COHORTS:
        rows=[x for x in cases if x["cohort"]==c]
        q=cohort_aggregates[c]
        _exact_fields(q, COHORT_FIELDS, "cohort aggregate")
        if (
            q.get("independent_original_matching_engine_runs")!=4
            or q.get("public_prints_total")!=sum(x["prints"] for x in rows)
            or q.get("unique_event_timestamp_clusters_total")!=
               sum(x["unique_time_groups"] for x in rows)
            or q.get("extra_same_timestamp_prints_total")!=
               sum(x["prints"]-x["unique_time_groups"] for x in rows)
            or q.get("posthoc_controlled_TWAP_fills")!=sum(x["posthoc_TWAP_fills"] for x in rows)
            or q.get("original_print_based_positive_alarms")!=
               sum(x["naive_classification"]=="TARGET_PATTERN" for x in rows)
            or q.get("grouped_timestamp_positive_alarms")!=
               sum(x["grouped_classification"]=="TARGET_PATTERN" for x in rows)
            or q.get("original_print_based_abstentions")!=
               sum(x["naive_classification"]=="ABSTAIN" for x in rows)
            or q.get("grouped_timestamp_abstentions")!=
               sum(x["grouped_classification"]=="ABSTAIN" for x in rows)
            or q.get("original_print_based_false_alarms") !=
               sum(c!="twap_45s_positive" and x["naive_classification"]=="TARGET_PATTERN" for x in rows)
            or q.get("grouped_timestamp_false_alarms") !=
               sum(c!="twap_45s_positive" and x["grouped_classification"]=="TARGET_PATTERN" for x in rows)
            or q.get("original_print_based_missed_TWAP") !=
               sum(c=="twap_45s_positive" and x["naive_classification"]=="NO_TARGET_PATTERN" for x in rows)
            or q.get("grouped_timestamp_missed_TWAP") !=
               sum(c=="twap_45s_positive" and x["grouped_classification"]=="NO_TARGET_PATTERN" for x in rows)):
            raise ValueError("Cohort original outcome/count conservation failed")
    return cases


def audit_matched_uncertainty(raw:dict)->dict:
    frozen_protocol()
    cases=validate_original_source_fixture(raw)
    result={}
    for cohort in COHORTS:
        rows=[x for x in cases if x["cohort"]==cohort]
        yes_both=sum(x["naive_classification"]=="TARGET_PATTERN" and
                     x["grouped_classification"]=="TARGET_PATTERN" for x in rows)
        print_only=sum(x["naive_classification"]=="TARGET_PATTERN" and
                       x["grouped_classification"]=="NO_TARGET_PATTERN" for x in rows)
        group_only=sum(x["naive_classification"]=="NO_TARGET_PATTERN" and
                       x["grouped_classification"]=="TARGET_PATTERN" for x in rows)
        neither=sum(x["naive_classification"]=="NO_TARGET_PATTERN" and
                    x["grouped_classification"]=="NO_TARGET_PATTERN" for x in rows)
        abstain=sum("ABSTAIN" in (x["naive_classification"],
                                  x["grouped_classification"]) for x in rows)
        if yes_both+print_only+group_only+neither+abstain!=4:
            raise AssertionError("Paired original source tapes cannot be unpaired")
        print_hits=yes_both+print_only
        group_hits=yes_both+group_only
        result[cohort]={
            "same_original_source_tape_trial_count":4,
            "posthoc_injected_TWAP_present":cohort=="twap_45s_positive",
            "naive_print_positive_alarm":clopper_pearson(print_hits,4),
            "grouped_timestamp_positive_alarm":clopper_pearson(group_hits,4),
            "paired_decisions":{
                "both_positive":yes_both,
                "print_only_positive":print_only,
                "grouped_only_positive":group_only,
                "both_negative":neither,
                "at_least_one_abstain":abstain
            },
            "source_oracle_controlled_TWAP_fills":sum(x["posthoc_TWAP_fills"] for x in rows)
        }
    combined_false_alarms={
        "original_negative_source_cases":12,
        "print_based_false_alarms_descriptive_only":sum(
            x["naive_classification"]=="TARGET_PATTERN"
            for x in cases if x["cohort"]!="twap_45s_positive"
        ),
        "grouped_false_alarms_descriptive_only":sum(
            x["grouped_classification"]=="TARGET_PATTERN"
            for x in cases if x["cohort"]!="twap_45s_positive"
        ),
        "pooling_three_different_backgrounds_as_one_iid_cohort_prohibited":True,
        "real_market_FDR_available":False
    }
    # The same single Poisson FALSE alarm persists; grouped loses the 3204
    # target. No method was calibrated on the new source response.
    if (
        combined_false_alarms["print_based_false_alarms_descriptive_only"]!=1
        or combined_false_alarms["grouped_false_alarms_descriptive_only"]!=1
        or result["twap_45s_positive"]["paired_decisions"]["print_only_positive"]!=1
        or result["twap_45s_positive"]["paired_decisions"]["grouped_only_positive"]!=0
    ):
        raise AssertionError("Original negative outcomes changed or were hidden")
    return {
        "schema_version":"abides-genuine-paired-small-n-retrospective-audit-v1",
        "audit_protocol":"research/abides_matched_uncertainty_audit_protocol_20261121.json",
        "original_genuine_simulator_source_run":44938991772,
        "original_source_artifact_id":14720831681,
        "original_source_uncompressed_json_sha256":EXPECTED_SOURCE_SHA,
        "already_inspected_same_synthetic_source_tapes":True,
        "new_independent_matching_engine_runs":0,
        "experiment_unit":"one ABIDES seed/cohort matching engine tape, NOT prints or L2 events",
        "each_cohort":result,
        "descriptive_background_sum_not_a_real_market_FDR":combined_false_alarms,
        "nominal_interval_method":"Clopper-Pearson exact two-sided 95% if IID Bernoulli trials",
        "IID_simulation_seed_sampling_certified":False,
        "market_population_confidence_claim":False,
        "true_owner_robotalgorithm_identity_inferred":False,
        "p_values_or_significant_winner_claimed":False,
        "real_market_FDR_calibrated":False,
        "no_event_timestamps_private_agent_IDs_or_source_tapes_exported":True,
        "paired_decision_risk_not_an_independent_32_source_sample":True,
        "conclusion":"In 4 new-source TWAP simulations grouping lost 1 positive; background Poisson 1 false alarm in both; nominal 4-trial 95% intervals necessarily wide. No demonstrated gain in specificity, no reliable real-market FDR."
    }


def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        parser.error("Refuse overwriting original retrospective audit output")
    raw=json.loads(SOURCE.read_text(encoding="utf-8"))
    result=audit_matched_uncertainty(raw)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x",encoding="utf-8") as f:
        json.dump(result,f,sort_keys=True,indent=2,allow_nan=False)
        f.write("\n")
    print("ABIDES_GENUINE_SMALL_N_PAIRED_AUDIT",json.dumps({
        "synthetic_original_source_seed_tapes":16,
        "new_engine_runs":0,
        "TWAP_source_paired_decisions":result["each_cohort"]["twap_45s_positive"]["paired_decisions"],
        "Poisson_source_paired_decisions":result["each_cohort"]["poisson_noise_null"]["paired_decisions"],
        "0_of_4_exact_upper_bound":clopper_pearson(0,4)["nominal_exact_CP_upper"],
        "4_of_4_exact_lower_bound":clopper_pearson(4,4)["nominal_exact_CP_lower"],
        "real_market_owner_FDR_known":False
    },sort_keys=True))


if __name__=="__main__":
    main()
