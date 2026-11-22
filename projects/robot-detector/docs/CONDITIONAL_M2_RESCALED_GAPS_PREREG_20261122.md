# M2 strictly predictable time-rescaled event gaps — prospective source-free prereg (2026-11-22)

**DESIGN FREEZE BEFORE IMPLEMENTATION / NEW TOY TESTS.** A next method iteration, not a rewrite of the frozen [M2 exponential-likelihood training protocol](CONDITIONAL_M2_PREDICTABLE_HISTORY_PREREG_20261122.md). No new ABIDES seeds, no real source data and no p-values/owner/FDR claims. The M0 and M1 trained models remain immutable.

## Hypothesis and exact deterministic quantity

For a *separate evaluation run* of distinct public timestamp clusters `t_1 < t_2 < ...`, and an already trained M2 model `lambda(t|H_(t-)) = mu + a Σ_{t_j<t} exp(-(t-t_j)/tau)`, compute `z_i = ∫_{t_i}^{t_(i+1)} lambda(u|H_(u-)) du` with **strictly preceding** histories. Let `S_i = Σ_{j<i} exp(-(t_i-t_j)/tau)`. Then after cluster i, for the open interval to the next cluster, `z_i = mu Δ_i + a*tau*(S_i+1)*(1-exp(-Δ_i/tau))` where seconds are used. At a print's own timestamp its own jump is not included in `lambda(t_i-)`; it only contributes to **later** integrals. Duplicates at exact timestamp are a single cluster, not many independent arrivals.

## Engineering / source-quality gates frozen

- Reuse the exact M2 `M2Run` and `M2Model` validation and `TRAIN_EVALUATION_SOURCE_RUN_OVERLAP` guard. No evaluation events may be used in model fitting or future-history contribution. Unknown/coarse timestamp precision, missing or unverified coverage, huge unsafe timestamps, unbounded size, invalid model parameters or zero/negative compensator must raise explicit `Abstain`.
- Require **at least two unique clusters**; empty or one cluster is `ABSTAIN`, not "no robot". The same externally asserted full-event source coverage and 1ms time-precision limitations apply. No hidden simulation agent IDs or real owner truth.
- No estimated-parameter time-rescaling p-values, naive KS significance or claims of independent exponential residuals. This is **a deterministic predictive diagnostic** only. Always report M0 constant-baseline gaps beside M2; never treat M2 fit to non-target momentum as a robot classifier.
- Predeclare adversarial tests: exact two-event integral for `mu=2,a=.2,tau=1` at 0.2s and 0.8s; split-fill invariant; future append does not alter old gaps; constant-rate `a=0` matches M0; train/eval run overlap aborts; incomplete/coarse coverage, bad rates and single unique event abstain; two toy **non-target** backgrounds (unrelated 20s periodic, closely spaced momentum bursts) reported without owner inference.
- Time-rescaling caution: in-sample parameter fitting biases nominal residual-calibration tests; independent evaluation and explicit source identities needed before any formal p-values. Ogata 1988 and contemporary time-rescaling critique: https://doi.org/10.1080/01621459.1988.10478560 and https://pmc.ncbi.nlm.nih.gov/articles/PMC12416029/

**NEXT_ACTION:** implement fixed analytic integration and source-free negative tests only after this doc is committed; verify exact CI and save all failures. No change to original frozen M2 `tau`/grid or prior holdouts.