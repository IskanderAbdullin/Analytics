# Frozen three public non-target tapes — held-out LL negative result (2026-11-22)

**Classification:** constructed source-free toy *negative methodological result*. Training, input tapes and metrics were frozen **before** this run in [preregistration](CONDITIONAL_CROSSMODEL_HELDOUT_LL_PREREG_20261122.md) commit `58a9ca51`. Model code at `8bfa4ec0`; exact checked-out [GitHub public Python job #45039673176](https://github.com/IskanderAbdullin/Analytics/actions/runs/45039673176) printed every aggregate from all three tapes and passed **149/149 tests**. CLI: `cd projects/robot-detector && python -m tools.public_crossmodel_heldout_ll`. This is **not** original ABIDES or real-market data, calibrated p-values, owners or real-market FDR.

## Complete unselected result

All three previously inspected source-free public tapes have **four unique clusters** each, same asserted complete 3-second [20000,23000) window and two lagged-BBO M1-v2 segments. The constructed training set and M0/M1v2/M2 hyperparameters were fixed beforehand.

| Constructed tape (all are non-targets) | M0 LL | M1-v2 LL | M2 LL | M1-v2 minus M0 | M2 minus M0 |
|---|---:|---:|---:|---:|---:|
| Unrelated periodic cadence | -3.000000 | -3.622661535642122 | -3.000000 | **-0.622661535642122** | 0 |
| Momentum burst | -3.000000 | -3.959133772263335 | -3.000000 | **-0.959133772263335** | 0 |
| Irregular public control | -3.000000 | -3.622661535642122 | -3.000000 | **-0.622661535642122** | 0 |

**M2 training actually selected `mu=1.0 / sec`, `a=0.0 / sec`, `tau=1.0 sec` on the prospectively frozen constructed training data.** Thus it collapses **exactly** to M0 here; no M2 predictive improvement can be claimed, even on deliberately bursty non-target observations. M1-v2 yields **lower** (worse) heldout LL than M0 on **all three** frozen non-target tapes; this is a valuable negative result and cannot be hidden by selecting only a favorable constructed tape.

The M1-v2 negative differences reflect the particular frozen training spread strata and constructed evaluation book; not a general rejection of causal L2 conditioning. M2 choosing a=0 is a valid outcome of its previously frozen 3×3 training grid, not a reason to retune training or evaluate a different convenient toy. No source-level exchangeability, calibrated statistical significance or real market detection performance is established. The three tapes are *dependent constructed methodological cases*, not three independent source worlds.

## Scientific and operational implications

- **Prediction != provenance.** Even if a different model were to score a periodic or momentum non-target better, it could not prove a physical algorithmic owner. The same public tape can have different hidden stories and identical model output.
- M1-v2's two eligible public-L2 segments require caller-asserted complete source event history, not proof of exchange completeness. Stable M1 abstains on older quotes; widening the gate only based on toy data would hide uncertainty.
- No new ABIDES source run, research seed, raw vendor archive, hidden private agent ID, real-market FDR or owner count has been produced.
- Continuing the *scientific goal* requires a genuine independent train/calibration/evaluation source protocol and disjoint original market-world units, a source-rights review, explicit coverage/abstention thresholds and power/cost feasibility **before** spending new seeds. The separate [power feasibility audit](INDEPENDENT_POWER_FEASIBILITY_AUDIT_20261122.md) already found n=100 insufficient for strict simultaneous gates under optimistic p_neg≥1%.

**NEXT_ACTION:** verify real-public source L2 capabilities and provenance legality, and decide whether honest ABSTAIN/identifiability limits are the meaningful scientific result rather than forcing a positive classifier.
