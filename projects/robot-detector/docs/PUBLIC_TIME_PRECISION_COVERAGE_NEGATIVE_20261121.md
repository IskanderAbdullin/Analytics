# RD-PUBLIC-CONDITIONAL-NULL-16 / subtask #98 — timestamp precision and lagged L2 abstention

**Source-free negative evidence**; no additional market data, simulator seeds, real owner IDs, FDR or p-values. The public toy protocols were frozen **before executing this toy matrix** at [`public_time_precision_coverage_precommit_20261121.json`](../research/public_time_precision_coverage_precommit_20261121.json) (commit `e0e28ae`). This retrospective controlled toy **does not** rewrite any earlier ABIDES 40-seed frozen source or reverse the 7/40 grouped TWAP misses.

## Tests and exact experiment

- [GitHub source-free provenance CI #44945044597](https://github.com/IskanderAbdullin/Analytics/actions/runs/44945044597) **SUCCESS**: all **8 new adversarial tests** and the full previously configured seed/provenance suite passed; [implementation](../tools/public_time_precision_coverage_null.py), [negative tests](../tests_background/test_public_time_precision_coverage_null.py).
- Four *constructed public-only* source tapes (no private agent or parent-order field), 240 public prints in paired-noise baseline, plus an explicitly pre-specified 100-print same-timestamp 45s-only split cluster, 9 near ±250ms tolerance edge prints, or 9 positive-cadence public events. They are NOT real market tapes or four genuine ABIDES simulations.
- Four nested timestamp resolutions: **1ns, 1ms, 10ms, 100ms**. For each, synthetic previous completed 30s L2-bin counts **4, 5, 10**. An additional variant with **unknown precision** is included for each of four constructed tapes. Exactly **52 dependent technical views**, NOT 52 independent source observations.
- Frozen clock scoring uses anchor **09:31:00** local session, 20s/45s grid, ±250ms match, ratio threshold **≥0.60**, at least 200 prints, 8 unique/print 20s hits and **5 prior-only** L2 bins. *Conservative demonstrated toy quality rule* returns **ABSTAIN** for unverified precision and for known resolution coarser than 1ms; it must be validated against any actual feed semantics before operational use. No future L2 is imported.

## All source-free outcomes

| Toy tape | Eligible views, q = 1ns or 1ms and L2 prior bins ≥5 | Per-print | Grouped timestamp | Specific negative result |
|---|---:|---|---|---|
| Paired background without target | 4 | NO TARGET | NO TARGET | Tied prints are not independent physical actors |
| 100 simultaneous fills on an unrelated 45s-only timestamp, **without target** | 4 | **False TARGET** | NO TARGET | Cluster weighting reverses a print inflation artifact |
| Nine near ±250ms grid-boundary public events, no target | 4 | NO TARGET | NO TARGET | Numeric score can change under quantization; precision gate suppresses false certainty |
| Nine sparse 45s-cadence synthetic public events | 4 | **NO TARGET (miss)** | **NO TARGET (miss)** | Real cadence alone need not cross fixed ratio in noise; do not hide this negative |

Each of the four tapes also produces exactly **4 low-L2 abstentions** (coverage=4), **4 too-coarse-precision abstentions** (10/100ms with coverage≥5), and **1 unknown-precision abstention**. Therefore total **16 eligible views** + **16 low-coverage abstentions** + **16 coarse-precision abstentions** + **4 unknown-precision abstentions** = **52 views**. Repeated coverage/precision variants share the same four underlying source tapes and are not pseudo-independent trials.

**Conservation invariants** were checked across every time quantization: all public-print counts, lot sums, BUY/SELL fields and chronological order preserved; rounded timestamps never gain distinct groups as precision becomes coarser; malformed/private-ID-bearing input rejected. No raw vendor archives or identifiers were published.

## Scientific interpretation

The same general fixed 20s/45s public pattern rule admits both failure directions under deterministic source-free controls: a massive non-target split-fill burst can **create a spurious per-print positive**, while a sparse target-like rhythm can be **missed** by both methods. Grouping can fix this particular toy split-fill artifact but did **not** improve genuine frozen ABIDES 160-case inference: [#96 original source report](ABIDES_160_ORIGINAL_SOURCE_AUDIT_20261121.md) found 7 additional grouped TWAP misses and remaining Poisson/momentum false alarms. No claim of statistical specificity or real-market owner attribution follows.

**Next action** under current main [issue #97](https://github.com/IskanderAbdullin/Analytics/issues/97): integrate these conservative precision/coverage controls into the **already pre-registered period-agnostic public conditional-null family**; do not tune fixed 0.60 on inspected seeds 3301–3340; add negative tests for an independent exchange timestamp semantics / quote-availability model, then seek prospective lawful observational data. Focused [subissue #98](https://github.com/IskanderAbdullin/Analytics/issues/98) tracks precision and coverage separately. Master [#72](https://github.com/IskanderAbdullin/Analytics/issues/72) stays OPEN pending independent scientific release audit.
