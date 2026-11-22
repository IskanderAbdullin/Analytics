#!/usr/bin/env python3
"""Aggregate-only full 64-replicate A/B/C/D positive-harmonic constructed panel.

Previously inspected constructed negatives; NOT new ABIDES/market source,
independent market trials, calibrated probabilities or owner attribution.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
# A direct 'python tools/...' invocation has tools/, not project root, on sys.path.
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(ROOT/'tests_background'))
from test_public_abc_constructed_controls import constructed_controls
from public_conditional_timing_null import conditional_cluster_sample as a
from public_burst_null_falsification import offset_preserving_sample as b
from public_intensity_conditioned_null import intensity_conditioned_cluster_sample as c
from public_microburst_block_null import microburst_block_sample as d
from public_period_positive_harmonics_v2 import scan_positive_harmonics_v2 as scan

SAMPLERS={"A_uniform_5s":a,"B_rigid_offset_5s":b,
          "C_stratified_500ms":c,"D_microburst_blocks_10ms":d}
SEED=404
REPLICATES=64


def report():
    output={"schema_version":"rd-positive-harmonics-allperiod-abcd-sourcefree-v1",
            "source_kind":"previously_inspected_constructed_non_target_controls",
            "randomization_seed":SEED,"randomization_replicates":REPLICATES,
            "fresh_market_or_ABIDES_sources":0,
            "periods_ms":[5000,10000,15000,20000,30000,45000,60000],
            "tolerance_ms":50,"calibrated_p_values":False,
            "physical_owner_id_known":False,"real_market_fdr_known":False,
            "scenarios":{}}
    for name,tape in constructed_controls().items():
        observed=scan(tape)
        row={"public_print_count":len(tape),"unique_timestamp_count":len(set(tape)),
             "observed":{str(x["period_ms"]):{"hits":x["hits"],"denominator":x["denominator"]}
                         for x in observed["periods"]},
             "candidates":{}}
        for label,sampler in SAMPLERS.items():
            per_period={p:[] for p in output["periods_ms"]}
            for replicate in range(REPLICATES):
                sampled=sampler(tape,seed=SEED,replicate=replicate)
                for s in scan(sampled)["periods"]:
                    per_period[s["period_ms"]].append(s["hits"])
            row["candidates"][label]={str(p):{
                "min_hits":min(hits),"max_hits":max(hits),
                "mean_hits":sum(hits)/REPLICATES,
                "all_replicate_hits":hits} for p,hits in per_period.items()}
        output["scenarios"][name]=row
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    raw=json.dumps(report(),sort_keys=True,indent=2)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(raw,encoding='utf-8')
        print("SOURCEFREE_ALLPERIOD_ABCD_REPORT_CREATED",args.output)
    else:print(raw,end='')


if __name__=='__main__':main()
