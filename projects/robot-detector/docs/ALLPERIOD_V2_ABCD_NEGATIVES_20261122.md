# All-period A/B/C/D positive-harmonic source-free negatives (2026-11-22)

**Pre-analysis frozen:** [issue #97 comment 7075711877](https://github.com/IskanderAbdullin/Analytics/issues/97#issuecomment-7075711877).
All three tapes are PREVIOUSLY INSPECTED constructed negatives, not
fresh market/ABIDES trials. All 7 periods, 4 candidates, 3 scenarios and
64 deterministic replicates (seed 404) are included without best-only selection.
Metric: v2 positive harmonics k>=1, tolerance ±50ms.

| No-target constructed stream | Observed 5s hits | Observed 20s hits | A 5s min..max / mean | B 5s min..max / mean | C 5s min..max / mean | D 5s min..max / mean |
|---|---:|---:|---|---|---|---|
| Quantized Poisson-like | 0 | 0 | 0..0 / 0 | 0..0 / 0 | 0..0 / 0 | 0..0 / 0 |
| Momentum-like 24×8-event bursts | 23 | 0 | 0..0 / 0 | 0..2 / 0.5 | 0..0 / 0 | 0..3 / 0.421875 |
| Unrelated 20s periodic stream | 5 | 5 | 0..1 / 0.109375 | 0..2 / 0.125 | 0..4 / 0.796875 | 0..1 / 0.078125 |

The unrelated 20s non-target has **5/5** observed hits at
**5s, 10s and 20s**. Momentum-like non-target has **23/191**
observed 5s hits due to regular 5s burst starts. Both are
**hard-negative counterexamples** to owner/target-specific claims.
A/B/C/D samples can dilute these clock patterns without a
market-exchangeability proof. This cannot license significance p-values
or an actual robot owner ID: none of the three tapes has a target.

D's 10ms gap statistic is fixed by construction; B/D also have
no extra relative-offset degrees of freedom on one-event-per-cell
periodic tapes, though their deterministic random replicates differ.
All-period v2 removes v1's zero-harmonic artifact, NOT its
residual positive-harmonic alias or the owner-identifiability limit.

New aggregate-only reporter retains original denominators and
all 64 replicate hit counts for each of 7 periods × 4 models × 3
constructed scenarios, plus min/max/mean and hardcoded
p-value/owner/FDR false flags. Only small aggregate JSON
is uploaded to 3-day-retention GitHub Actions artifacts;
no raw vendor archives or private IDs.

Three report-integrity tests passed locally on source-equivalent
transcribed code **3/3**. Commit b1dbd166 initially FAILED provenance CI #44996834864 and #44996830341 after all three report tests PASSED: the direct CLI lacked project-root import path and raised ModuleNotFoundError for tools.public_period_positive_harmonics_v2. A follow-up importer-only fix adds project ROOT to sys.path; verified the direct CLI locally without PYTHONPATH; corrected exact-HEAD CI pending. No scientific results, threshold, seed or frozen protocol altered.
The previous version's five v2 tests independently passed in
[provenance CI #44996649423](https://github.com/IskanderAbdullin/Analytics/actions/runs/44996649423).

NEXT_ACTION: verify exact-HEAD aggregate CI and artifact,
then develop explicit *testable* exchangeability conditions
or an independently preregistered synthetic source with new
untouched seeds; no thresholds optimized on this panel.
Master #72 remains open.
