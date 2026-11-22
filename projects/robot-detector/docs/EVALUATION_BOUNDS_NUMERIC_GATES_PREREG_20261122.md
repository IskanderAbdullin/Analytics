# Prospective fail-closed numeric guards for binomial bounds (2026-11-22)

**PRETEST / PREIMPLEMENTATION** addendum. The current source-free exact-binomial functions and historical 160-case results remain unchanged until a later separate implementation commit. No statistical source inference or simulation is authorised.

## Known code-inspection hypotheses
1. `conservative_outcome_bounds(0, 0, 10, alpha=0)` currently takes its no-eligible branch without validating alpha. Any invalid/nonnumeric/nonfinite/boolean alpha must reject even when observed coverage is zero.
2. `upper_one_sided(0, 10**500)` may overflow/allocate excessively without a fixed input budget. The exact-binomial test design needs a bounded explicit denominator before any numeric iteration.

## Engineering controls frozen before tests
- Exact `k,n` Python integers only, `0 <= k <= n`; numerical study guard **1 <= n <= 1000**. This is a bounded computation guard for source-free methodological checks; datasets with >1000 original worlds require a separately reviewed scalable method and MUST NOT be silently truncated to 1000.
- `alpha` must be exact float or exact int and strictly finite and `0 < alpha < 1`. Reject bool, NaN, infinities, malformed types and extreme-precision integers, including no-coverage outcomes.
- In `conservative_outcome_bounds`, validate alpha **first**, before abstaining for `eligible == 0`. Preserve original coverage meanings; no invented event counts; no silent fallback or best-phase selection.
- Keep old exact Clopper-Pearson formula/one-sided conventions unchanged. Negative tests: malformed alpha at 0 eligible; astronomically large counts (both zero- and positive-alarm paths); endpoint n=1000 still accepted; boolean/nonnumeric alpha; ordinary 0/100 unchanged.
- No claim that 0/100 means zero risk, and no use of per-fill binomial independence, market FDR or owner truth.

Acceptance: source-free tests must execute on exact committed code with documented CI run. Any failure preserved, no source experiments/seeds.