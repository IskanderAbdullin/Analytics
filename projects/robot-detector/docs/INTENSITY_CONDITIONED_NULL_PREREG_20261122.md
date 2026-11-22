# RD-PUBLIC-CONDITIONAL-NULL-16 — intensity-conditioned falsification protocol v0 (pre-implementation)

Date: 2026-11-22. Status: **source-free preregistration / exploratory model development, not calibrated inference**.

## Motivation and non-negotiable negative result

The frozen 160 genuine ABIDES seed×cohort cases (3301–3340, 40 seeds × four cohorts) already showed 6/40 Poisson and 7/40 momentum false alarms after grouping by exact public timestamp, with seven extra missed TWAP cases. These seeds are spent and are **not** an independent holdout. A constructed six-cell burst case has 42 observed within-cell gaps <=10ms, while uniform-within-5s-cell resampling of 64 deterministic replicates yielded 0..2 gaps and rigid offset-preserving resampling yielded 42..42. Neither null is justified as a market p-value.

## Frozen source-free comparison design

1. Use public millisecond exchange timestamps only; identical timestamps form **observable** clusters, never assumed to be one physical parent. Strictly sorted, nonnegative integer input; reject booleans, future L2 and private/oracle fields.
2. Fix 5,000ms UTC-aligned cells and report all candidate periods {5,10,15,20,30,45,60}s at ±50ms tolerance. Do not choose a period/phase or threshold from the outcome.
3. Compare three *descriptive* constructions: (A) uniform unique timestamps within each fixed cell, preserving per-cell count and original cluster-size vector; (B) rigid translation of each cell's ordered within-cell offsets, preserving every gap; (C) **candidate intensity-stratified construction**, conditioning additionally on counts in ten consecutive 500ms subcells of each 5s cell, with complete split-fill clusters intact. Each candidate is a sensitivity diagnostic, not a validated randomization distribution.
4. For C, resample unique millisecond slots without replacement *within each 500ms subcell*; attach original split-fill multiplicities in chronological rank order within the same subcell. No event may cross its 500ms subcell or 5s cell. Use deterministic Python `Random` string seed namespace `rd-intensity-500ms-v1:{seed}:{replicate}`. Fixed diagnostic seed 404, replicates 0..63. This seed is a constructed randomization seed, not an ABIDES source seed.
5. Construct negatives **before evaluation**: homogeneous Poisson-like source-free timestamps, inhomogeneous rate-burst (self-exciting-like) clusters, momentum-like concentrated activity, unrelated deterministic periodic background, split-fill duplication, and identical public tapes with distinct private owner configurations. Include positive injected cadence only as a constructed sensitivity check. Compare within-cell <=10ms adjacent unique gaps, occupancy and period scan, with all abstentions and all candidates reported.
6. Fail closed on missing/unknown precision or L2 coverage; L2 gate uses only strictly prior snapshots. Do not silently reinterpret missing events as absence of a pattern.

## Decision criteria and interpretation

Technical acceptance: all 500ms and 5s occupancy invariants, timestamp multiplicity vectors, deterministic replay, validation failures and no-lookahead gates pass adversarial tests. Scientific falsification: if C erases burst gap structure or alarms on periodic non-target/momentum/Poisson negatives, record failure without retuning the 500ms width or seed. If C preserves structure but loses power against constructed target, record the validity/power tradeoff. Any width adjustment requires a new version and prospective test; no posthoc selection of the best candidate. **No p-values, owner identities, real-market FDR, or new ABIDES claims** from these constructed tests.

NEXT_ACTION: implement candidate C and adversarial source-free tests, execute exact committed tests and cheap CI; only then design an independently registered new source cohort with separate frozen seeds and honest oracle/public separation.
