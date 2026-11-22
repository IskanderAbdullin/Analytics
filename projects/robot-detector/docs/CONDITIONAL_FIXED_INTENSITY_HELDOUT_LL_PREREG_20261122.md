# Fixed public intensity held-out log likelihood — prospective source-free prereg (2026-11-22)

**PRETEST / PREIMPLEMENTATION.** New scoring module for the already frozen M0 constant hazard and M1-v2 changing lagged BBO models, to compare with independently pre-registered M2 exponential-history `evaluate_m2_run`. This does not alter any model-fitting protocol, select posthoc seeds, use real source, or infer real owners/FDR.

## Scientific quantity

Given a **fixed** public-only piecewise-rate exposure tiling a whole evaluation window `[start_ms,end_ms)`, and an independent public evaluation print tape of unique timestamp clusters `t_i`, score

`LL = Σ_(distinct t_i in window) log λ(t_i-) - Σ_(segments s) λ_s * (end_s-start_s)/1000`.

Rates are pre-trained on independent training runs. The held-out print counts must NOT enter M0/M1-v2 fitting, parameter selection, lag, median or boundary. Model M1-v2 only changes at raw L2 timestamp+1000ms, so a print *exactly at* that delayed effective transition may use the new regime: it became predictable 1000ms earlier; raw co-timestamp L2 must not influence its own event. Rate units events/second; exposure in integer milliseconds. All observations at the same exact timestamp comprise ONE event; split fills never increase likelihood counts. No print is taken to be a known physical parent/owner.

## Strict numerical, data-quality and causal gates

- Input is sorted Python list/tuple of exact nonnegative integer public timestamps, not raw records or oracle labels; observation window exact ints `0 <= start < end <= 2^53-1`. Require every unique timestamp strictly *inside* the window; zero-event window is a legitimate count outcome with `LL=-integral`, NOT evidence of no robot.
- Fixed public Exposure segments must be exact `Exposure` dataclass, chronological, nonoverlapping and gap-free, their first start and last end exactly matching the declared full window. Rates are finite positive real numbers (no bool, huge malformed ints, NaN or zero), and `complete` and `causal` exactly True. Overlaps, uncovered ends, unsorted or backwards durations -> explicit `Abstain`, never synthetic silent fill.
- Max **100000 public print records** and **100000 exposure segments** per evaluation run as a bounded engineering guard; higher source counts require separately documented scalable implementation. No estimates on M2/source independence or true FDR from this scorer.
- Return only source-free metadata (`unique_clusters, integral_intensity, heldout_log_likelihood, log_likelihood_per_second, exposure_segments, status=SOURCE_FREE_FIXED_RATE_SCORE_NOT_CALIBRATED`), not event rows or private identifiers.

## Prespecified adversarial tests

1. Constant rate 2/s, [0,1000] and 3 distinct events -> `3 log(2)-2`, invariant to splitting events into duplicate fills.
2. Two complete half-second segments λ=1,3; event at 250ms and exactly 500ms -> `log(3)-2`; no future book leakage assumption beyond upstream asserted causality.
3. Empty window -> `LL=-integral`; no invented positive or owner inference.
4. Full exposure tiling mandatory (missing first/last, middle gap, overlap, out-of-order and missing/false/nonbool source flags) -> ABSTAIN.
5. Missing, invalid, nonfinite, boolean, negative, zero, extreme `10**500` rate and unsafe timestamp -> ABSTAIN, not unbounded runtime/OverflowError.
6. Raw additional fields/oracle, unsorted/outside/boolean/fractional timestamps -> ABSTAIN.
7. Exact M2 `a=0` constant-history trained model log likelihood matches M0 fixed-rate scorer on identical holdout; any discrepancy is a mathematical integrity bug.
8. Score all **three previously frozen constructed** public tapes from the prior cross-model ambiguity prereg; identical public tapes remain identical under all three predictive models regardless of invented hidden story. M1-v2 may abstain if prior L2 coverage is unknown; DO NOT call that a model miss/negative class.

**Acceptance:** source-free Python negative tests on committed SHA, original frozen 160 results untouched, master/state/issue updated. No ABIDES source generation or market p-values. NEXT_ACTION: compare frozen constructed hard negatives with M0/M1-v2/M2 predictive LL, then independent source-quality and train/eval manifest audit before new seeds.