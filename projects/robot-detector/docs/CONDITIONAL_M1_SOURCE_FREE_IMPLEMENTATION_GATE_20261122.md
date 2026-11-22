# M1 implementation gate — source-free conservative first slice (2026-11-22)

**PRE-IMPLEMENTATION / PRE-TEST ADDENDUM.** The [original M1 design](CONDITIONAL_M1_LAGGED_L2_PREREG_20261122.md) remains frozen, unchanged and authoritative. This addendum specifies an intentionally narrow first implementation, without new source experiments, p-values, tuning or holdout seeds.

## Decision before implementation

Test only **single locally stable quoted-BBO windows**; a training/evaluation run supplies one fully declared *prior* public BBO observation. Any additional within-window book transition, uncertain continuity, missing coverage or staleness causes **ABSTAIN** rather than assuming a valid continuous exposure. This narrow subset cannot establish utility on fast-changing real L2 and is not the full M1 research release.

- Fixed conservative source quality gates: integer event/book times, declared exact 1ms precision, previous BBO with `snapshot_time_ms + 1 < window_start_ms`, maximal quote age measured at window end **1000ms**, positive finite non-crossed bid/ask, `snapshot.complete is True`, `run.interval_complete is True`. A lone snapshot does not prove exchange completeness: `interval_complete` is a required **external asserted coverage condition**; science must report that limitation, never silently infer it from data.
- Input: each training run has nonempty non-secret original-run identifier `run_id`, `[start_ms,end_ms)`, sorted public timestamp-cluster times within the open window, a single allowlisted strictly prior book record, and a bool interval coverage assertion. Exact duplicates at timestamp are **one** cluster.
- Freeze one median spread observation **per eligible training run**; median computed from training ONLY. `spread=(ask-bid)/((ask+bid)/2)`, deterministic tie `<=median` low, greater high; counts and exposure pool by assigned stratum, `lambda=count*1000/exposure_ms`. Require positive exposure and at least one cluster in **both** strata. No arbitrary smoothing, no evaluation-derived parameters.
- Evaluation receives ONLY run identifier, exposure window, a prior source BBO and coverage assertion — **no evaluation prints, oracle or labels**. Reject evaluation run IDs already used for fitting. M1 outputs externally fixed `Exposure` for the existing rescaling diagnostic, not a detector/decision or calibrated p-value.
- Fresh original ABIDES runs/seeds remain BLOCKED pending complete causal segmentation and an independent run-disjoint M0/M1/M2 train/calibration/assessment protocol. No retrospective rebranding of seeds 3301–3340.

## Predeclared adversarial controls

Positive technical: two non-overlapping training windows, one in each spread stratum, and stable evaluation exposure. Negative fail-closed cases: same-time/future L2; coarse/imprecise and stale quotes; missing/false/nonboolean coverage; crossed, zero, NaN or forbidden private fields; unsorted or outside-window events; no clusters/one-stratum/one-sided counts; duplicate run identifiers and evaluation identity overlap. Split fills must not change cluster rates. Evaluation cannot change fitted median or rates. Unrelated periodic and momentum public tapes may share the same M1 exposures: **never infer actors from that coincidence**.

## Acceptance and limits

Cheap deterministic source-free Python tests on exact code; CI log must enumerate M1 methods before declaring verified. If tests fail, log and fix without altering this precommitted gate silently. Even a pass does not validate exchange completeness, spread conditioning, null exchangeability, market FDR, physical owner count, or M1 superiority over M0. Expand only in a new explicitly numbered design and separate independent evaluation.
