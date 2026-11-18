# Stage 2 — historical-only recency gate (development-derived, untouched-date validation)

**Protocol frozen:** 2026-11-18 before running the proposed November 5/6 archives. **Status:** code implemented; independent real-data evaluation pending.

## Motivation and provenance

On the *development-only* SBER archive days 2026-11-09 and 2026-11-10, a post-hoc audit of a preexisting rolling forecast pipeline produced 306 candidate checks; 297 misses, with **291** misses coming from patterns whose last observed confirming print was **more than 8 predicted cycles** old. Across both days, 293/306 candidate checks had last evidence more than 8 cycles in the past. See [FORECAST_FAILURE_DIAGNOSTICS.md](FORECAST_FAILURE_DIAGNOSTICS.md), run 44303630656. These observations motivated a **simple history-only** gate. The 9/10 development data are not a validation sample.

**New rule (predeclared):** `maximumTrainingAgeCycles=2`. Before inspecting the upcoming print, require `(cutoffUtc - lastTrainingEvidenceUtc).TotalMilliseconds / periodMs <= 2`. If not, reject the candidate for a forecast. **No future prints are inspected to establish eligibility.** No threshold tuning on new holdout samples.

The rolling code keeps the original unrestricted mode (`maximumTrainingAgeCycles=null`) as the baseline; an optional C# API and CLI parameter enables the gate. Both versions retain the same fixed-volume detector, timestamp/period matching, source/session isolation, and half-period placebo controls. The result includes the gate's value and warnings, no calibrated confidence or actual owner count.

## Independent evaluation (dates frozen in advance)

- Historical public SBER_TQBR sessions: **2026-11-05 and 2026-11-06**. These dates were not used in the earlier 9/10 development diagnostic, 12/13 sealed replay, or 16/17 candidate-count/null investigations.
- Per date, download exactly one anonymized T-Invest read-only public CSV/GZip archive, compute SHA-256, process with the same code revision.
- Within each file, run **two** forecasts: original *unrestricted* and age-gated `2 cycles`. Use the same `minMatches=6`, `warmupMinutes=60`, `strideMinutes=30`, `maxCutoffs=12`, `AnalysisWindowMinutes=60`, same trade source/mode/session boundaries.
- For each version print the number of evaluated cutoffs, forecast windows, observed hits, T/2-shift placebo hits, observed and placebo hit rates; every log must label `actualBotCountKnown=false`, `calibrated=false` and `feedCoverageVerified=false`.
- Compare **absolute opportunity reduction and hit-minus-placebo difference**. A higher hit percentage caused by filtering nearly all candidates is not sufficient evidence of useful detection or predictive power.
- If fewer than 30 independent-enough gated future windows remain, label the pilot `INSUFFICIENT_SAMPLE` (30 is a reporting warning, not an optimized statistical threshold). Even with more than 30, repeated target windows, common market clocks and non-independent prints prevent simple binomial statistical claims.

The raw exchange tape is deleted from the CI runner and never committed or published. TLS validation uses only the previously pinned official Russian Trusted Root CA inside the isolated process. No broker tokens, portfolio reads or trade/order methods.

## Acceptance and scientific safety

- All .NET 10 builds, offline regression tests and the synthetic `maxTrainingAgeCycles=2` smoke pass before data evaluation.
- A synthetic missing-future/changed-quantity test must prove that **candidate eligibility remains identical when only future prints are modified**.
- A strongly stale historical-only pattern must be filtered, with the unchanged unrestricted baseline still generating a candidate.
- Invalid gate values `<=0` are rejected. No retroactive rewriting of the negative 12/13 November result (14/983 against 14/983 placebo).
- Report actual holdout outcome regardless of whether the recency gate helps or hurts. Do not introduce further changes after seeing Nov 5/6 and call them validation on those same dates.
- No live alert, trading signal or calibrated bot count is authorized by this evaluation.

## Post-evaluation

If fresh windows are too scarce, prefer longer independent development windows and known-agent synthetic ABIDES validation. A valid future release needs separate execution-plan clustering, stationarity tests, better control for common clock triggers, unseen instruments and reliability calibration.

**Observed results:** intentionally not filled until GitHub Actions reports actual metrics.
