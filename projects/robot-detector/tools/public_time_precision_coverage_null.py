#!/usr/bin/env python3
"""Source-free deterministic clock precision / lagged L2 negative controls.

All 52 summaries derive from four precommitted constructed public-print toys
on nested timestamp precisions, never from additional ABIDES seeds or real
vendor source data. Equal timestamps and deterministic cadence do not identify
physical owners or parent orders; coverage is a synthetic integer stand-in.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT/"research"/"public_time_precision_coverage_precommit_20261121.json"
BILLION = 1_000_000_000
Q = (1,1_000_000,10_000_000,100_000_000)
COHORTS = (
    "paired_background_null","split_100_at_45sec_only_null",
    "near_boundary_45sec_null","sparse_public_45sec_positive"
)
L2_COVERAGE = (4,5,10)
ANCHOR = 34260*BILLION
TOLERANCE = 250_000_000
SESS_START = 34200*BILLION
SESS_END = 34680*BILLION
STATUSES = ("ABSTAIN","TARGET_PATTERN","NO_TARGET_PATTERN")


@dataclass(frozen=True, slots=True)
class PublicPrint:
    time_ns:int
    lots:int
    side:str

    def __post_init__(self):
        if (type(self.time_ns) is not int
            or not SESS_START <= self.time_ns < SESS_END
            or type(self.lots) is not int or self.lots <= 0
            or self.side not in ("BUY","SELL")):
            raise ValueError("Invalid public-only synthetic print")


def frozen_protocol()->dict:
    p=json.loads(PLAN.read_text(encoding="utf-8"))
    g=p.get("fixed_source_generation",{})
    s=p.get("fixed_public_scoring",{})
    if (p.get("schema_version") !=
            "public-time-precision-and-lagged-l2-adversarial-precommit-v1"
        or p.get("scientific_stage")!="RD-PUBLIC-CONDITIONAL-NULL-16"
        or p.get("focused_subissue")!=98
        or p.get("primary_stage_issue")!=97
        or p.get("source_mode")!=
            "SOURCE_FREE_DETERMINISTIC_PUBLIC_ONLY_TOY_NO_NEW_ENGINE_OR_MARKET_DATA"
        or p.get("origin_original_source_run")!=44944144915
        or p.get("new_source_seed_values")!=[]
        or p.get("original_inspected_source_seed_range")!=[3301,3340]
        or p.get("precision_grid_ns")!=list(Q)
        or p.get("precision_transformation")!=
            "floor each non-negative UTC nanosecond timestamp to multiple of quantum, never modify side/lots/print multiplicity; all source variants and all precision values must be reported"
        or p.get("no_real_trading_or_external_data") is not True
        or p.get("frozen_after_source_3301_3340_inspection") is not True
        or p.get("do_not_use_as_independent_real_market_or_new_ABIDES_evidence") is not True
        or g.get("exchange_session_start_second_local")!=34200
        or g.get("exchange_session_end_second_local_exclusive")!=34680
        or g.get("public_prints_base")!=240
        or g.get("base_timestamp_centers")!=120
        or g.get("base_center_step_ns")!=4*BILLION
        or g.get("base_center_jitter_formula")!=
            "(7*i % 100) * 1000000 nanoseconds for i=0..119"
        or g.get("within_center_print_offsets_ns")!=[0,200000]
        or g.get("base_lots_by_j")!=[5,7]
        or g.get("base_reported_sides_by_j")!=["BUY","SELL"]
        or g.get("variants")!=list(COHORTS)
        or g.get("split_variant_added_print_count")!=100
        or g.get("split_variant_timestamp_second_local")!=34305
        or g.get("split_variant_print_lots")!=1
        or g.get("near_boundary_added_count")!=9
        or g.get("near_boundary_timestamp_formula")!=
            "34260+45*i seconds + 255000000 nanoseconds, i=0..8"
        or g.get("near_boundary_print_lots")!=1
        or g.get("sparse_positive_added_count")!=9
        or g.get("sparse_positive_timestamp_formula")!=
            "34260+45*i seconds, i=0..8"
        or g.get("sparse_positive_print_lots")!=1
        or g.get("allow_private_parent_or_agent_ids_in_input") is not False
        or s.get("clock_anchor_second_local")!=34260
        or s.get("grid_periods_seconds")!=[20,45]
        or s.get("grid_tolerance_ns")!=TOLERANCE
        or s.get("ratio_threshold_greater_equal")!=.60
        or s.get("min_public_prints")!=200
        or s.get("min_public_20sec_clock_hits")!=8
        or s.get("min_unique_timestamp_20sec_hits")!=8
        or s.get("min_prior_completed_30sec_l2_bins")!=5
        or s.get("prior_l2_bins_test_values")!=list(L2_COVERAGE)
        or s.get("proven_source_timestamp_resolution_ceiling_ns")!=1_000_000
        or s.get("unknown_or_coarser_precision_status")!="ABSTAIN"
        or s.get("no_oracle_in_public_features") is not True):
        raise ValueError("Precommitted public-only precision/coverage design drift")
    return p


def constructed_public_tape(cohort:str)->tuple[PublicPrint,...]:
    if cohort not in COHORTS:raise ValueError("Unknown precommitted toy cohort")
    tape=[]
    for i in range(120):
        base=SESS_START+4*i*BILLION+((7*i)%100)*1_000_000
        tape.extend((
            PublicPrint(base,5,"BUY"),
            PublicPrint(base+200_000,7,"SELL")
        ))
    if cohort=="split_100_at_45sec_only_null":
        tape.extend(PublicPrint(34305*BILLION,1,"BUY") for _ in range(100))
    elif cohort=="near_boundary_45sec_null":
        tape.extend(PublicPrint((34260+45*i)*BILLION+255_000_000,1,"BUY")
                    for i in range(9))
    elif cohort=="sparse_public_45sec_positive":
        tape.extend(PublicPrint((34260+45*i)*BILLION,1,"BUY")
                    for i in range(9))
    tape.sort(key=lambda x:x.time_ns)
    n=240+(100 if cohort=="split_100_at_45sec_only_null"
           else 0 if cohort=="paired_background_null" else 9)
    if len(tape)!=n:raise AssertionError("Public toy source print count changed")
    return tuple(tape)


def _source_fingerprint(tape:tuple[PublicPrint,...])->str:
    h=hashlib.sha256()
    for p in tape:
        h.update(f"{p.time_ns}|{p.lots}|{p.side}\n".encode("ascii"))
    return h.hexdigest()


def precision_view(tape:tuple[PublicPrint,...],quantum_ns:int)->tuple[PublicPrint,...]:
    if quantum_ns not in Q or type(quantum_ns) is not int:
        raise ValueError("Only precommitted nested precision values allowed")
    if type(tape) is not tuple or not tape or any(type(x) is not PublicPrint for x in tape):
        raise ValueError("Source-free public tape only, never agent truth")
    if tuple(sorted(tape,key=lambda x:x.time_ns))!=tape:
        raise ValueError("Public input must be source-time monotonic")
    result=tuple(PublicPrint((x.time_ns//quantum_ns)*quantum_ns,x.lots,x.side)
                 for x in tape)
    if (len(result)!=len(tape)
        or sum(x.lots for x in result)!=sum(x.lots for x in tape)
        or any(a.lots!=b.lots or a.side!=b.side for a,b in zip(tape,result))
        or tuple(sorted(result,key=lambda x:x.time_ns))!=result):
        raise AssertionError("Precision view lost public events, quantities or sequence")
    return result


def _hits(times:tuple[int,...],period:int)->int:
    interval=period*BILLION
    return sum(min(rem,interval-rem)<=TOLERANCE
               for t in times for rem in ((t-ANCHOR)%interval,))


def public_clock_score(tape:tuple[PublicPrint,...], *,
                       quantum_ns:int,prior_completed_l2_bins:int,
                       precision_certified:bool)->dict:
    if quantum_ns not in Q or type(quantum_ns) is not int:
        raise ValueError("Unfrozen timestamp precision")
    if type(prior_completed_l2_bins) is not int or prior_completed_l2_bins not in L2_COVERAGE:
        raise ValueError("Unfrozen synthetic prior-only L2 coverage")
    if type(precision_certified) is not bool:
        raise ValueError("Public precision must be explicitly certified/unknown")
    if type(tape) is not tuple or any(type(x) is not PublicPrint for x in tape):
        raise ValueError("Private source IDs or unknown print fields prohibited")
    times=tuple(x.time_ns for x in tape)
    unique=tuple(sorted(set(times)))
    p20,p45=_hits(times,20),_hits(times,45)
    g20,g45=_hits(unique,20),_hits(unique,45)
    if len(times)<200:
        why="TOO_FEW_PUBLIC_PRINTS"
    elif p20<8 or g20<8:
        why="TOO_FEW_20S_GRID_HITS"
    elif prior_completed_l2_bins<5:
        why="TOO_FEW_PRIOR_COMPLETED_L2_BINS"
    elif not precision_certified:
        why="UNKNOWN_SOURCE_TIMESTAMP_PRECISION"
    elif quantum_ns>1_000_000:
        why="SOURCE_TIMESTAMP_PRECISION_TOO_COARSE"
    else:
        why=None
    rp=round(p45/p20,8) if p20 else None
    rg=round(g45/g20,8) if g20 else None
    status_p=("ABSTAIN" if why else
              "TARGET_PATTERN" if rp>=.60 else "NO_TARGET_PATTERN")
    status_g=("ABSTAIN" if why else
              "TARGET_PATTERN" if rg>=.60 else "NO_TARGET_PATTERN")
    return {
        "public_print_count":len(tape),
        "public_lots_total":sum(x.lots for x in tape),
        "unique_public_timestamps":len(unique),
        "dependent_same_timestamp_extra_prints":len(times)-len(unique),
        "largest_exact_timestamp_print_cluster":max(Counter(times).values()),
        "public_print_hits20":p20,"public_print_hits45":p45,
        "public_timestamp_hits20":g20,"public_timestamp_hits45":g45,
        "per_print_ratio":rp,"per_timestamp_ratio":rg,
        "per_print_decision":status_p,"per_timestamp_decision":status_g,
        "coverage_or_precision_abstain_reason":why,
        "previous_only_L2_bin_count":prior_completed_l2_bins,
        "certified_public_time_precision":precision_certified,
        "quantization_ns":quantum_ns,
        "public_fingerprint_sha256":_source_fingerprint(tape),
        "real_market_owner_identity_or_FDR_known":False,
        "parent_orders_inferred_from_same_timestamp":False,
        "synthetic_coverage_number_not_actual_L2":True,
    }


def full_matrix()->dict:
    frozen_protocol()
    rows=[]
    for cohort in COHORTS:
        base=constructed_public_tape(cohort)
        uniq_by_quant=[]
        for q in Q:
            v=precision_view(base,q)
            uniq_by_quant.append(len(set(x.time_ns for x in v)))
            for prior in L2_COVERAGE:
                r=public_clock_score(
                    v,quantum_ns=q,
                    prior_completed_l2_bins=prior,
                    precision_certified=True
                )
                rows.append({"cohort":cohort,**r})
        if uniq_by_quant!=sorted(uniq_by_quant,reverse=True):
            raise AssertionError("Nested time rounding increased unique timestamps")
        unknown=public_clock_score(
            precision_view(base,Q[0]),quantum_ns=Q[0],
            prior_completed_l2_bins=10,precision_certified=False
        )
        if (unknown["per_print_decision"]!="ABSTAIN"
            or unknown["per_timestamp_decision"]!="ABSTAIN"
            or unknown["coverage_or_precision_abstain_reason"]!=
               "UNKNOWN_SOURCE_TIMESTAMP_PRECISION"):
            raise AssertionError("Uncertified source precision bypassed abstention")
        rows.append({"cohort":cohort,**unknown})
    if len(rows)!=52:
        raise AssertionError("One or more negative/positive source views excluded")
    return {
        "schema_version":"source-free-precision-coverage-negative-52views-v1",
        "frozen_protocol":"research/public_time_precision_coverage_precommit_20261121.json",
        "source_free_dependent_views":len(rows),
        "independent_market_or_ABIDES_source_runs":0,
        "corresponding_physical_agent_ID_or_market_FDR_known":False,
        "all_precommitted_negative_control_views_retained":True,
        "same_tape_precision_and_coverage_views_not_independent_observations":True,
        "source_no_private_agent_identifiers_or_raw_vendor_data":True,
        "rows":rows
    }


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    if args.output.exists():
        p.error("Do not overwrite frozen source-free negative matrix output")
    result=full_matrix()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x",encoding="utf-8") as fh:
        json.dump(result,fh,indent=2,sort_keys=True,allow_nan=False)
        fh.write("\n")
    summary=Counter((r["cohort"],r["per_print_decision"],
                     r["per_timestamp_decision"],
                     r["coverage_or_precision_abstain_reason"]) for r in result["rows"])
    print("PUBLIC_PRECISION_L2_SOURCE_FREE_52VIEWS",json.dumps(
        {str(k):v for k,v in summary.items()},sort_keys=True))
    print("PUBLIC_PRECISION_L2_SOURCE_FREE_SCOPE",
          json.dumps({"dependent_views":52,
                      "independent_market_source_runs":0,
                      "actual_owners_or_market_FDR_known":False}))


if __name__=="__main__":
    main()
