# M2 predictable-history candidate — prospective freeze (2026-11-22)

**DESIGN-ONLY PREREGISTRATION BEFORE ANY M2 TEST OR DATA.** Stage RD-PUBLIC-CONDITIONAL-NULL-16. This is a separate candidate from M0 constant cluster rate and M1 conservative lagged-BBO spread strata. Existing frozen 160 ABIDES cases and all prior timing A/B/C/D panels are spent/development evidence, **not** independent M2 evaluation.

## Scientific question and theoretical caveat

Does a strictly predictable history-dependent intensity explain *observable unique-timestamp cluster arrivals* better than M0 and M1 on independent source-run units **without attributing physical owners or declaring real-market FDR**?

Proposed univariate exponential Hawkes-like conditional intensity, time in seconds:

`lambda(t | H_(t-)) = mu + a * sum_{t_i < t} exp(-(t-t_i)/tau)`

- Each distinct public timestamp is ONE arrival regardless of split-fill multiplicity. Only strictly earlier arrivals contribute: no event can increase its **own** predicted intensity; no future observations, oracle labels, private IDs or real order attribution.
- Fix **tau=1.0 second** prospectively as a source-free stress-test scale, NOT a measured market optimum. Candidate training grid: `mu = c*(N_train/T_train)`, `c ∈ {0.5, 1.0, 2.0}`; `a ∈ {0.0, 0.2, 0.4} sec^-1`. The grid includes the non-self-exciting M0-like `a=0` corner. Use all candidates; never choose only favorable source periods.
- To guard nonexplosive kernels, require `mu > 0, a >= 0, a*tau < 1`, strict source window/clock quality, and no cross-run event history. No candidate is fitted on held-out calibration/evaluation runs.
- For a training run `[0,T]`, unique public clusters `t_i` yield exactly the predeclared log-likelihood score:
  `LL = sum_i log(mu + a*sum_{j<i} exp(-(t_i-t_j)/tau)) - mu*T - a*tau*sum_i(1-exp(-(T-t_i)/tau))`.
  Compute a pooled sum of **independent original training-run** log likelihoods. Choose the maximum, deterministic ties lowest `a`, then lowest `c`. If no observed training clusters, unknown coverage/precision, missing time denominators or invalid horizon, **ABSTAIN**. No per-window reinitialisation that falsely treats phases of one tape as independent source runs.
- Evaluation: frozen `mu,a,tau` from training and strictly prior-only history within each independent evaluation run. Predictive integrated intensity and negative log likelihood per original run; coverage and quality abstentions reported alongside scores. No "robot" threshold or p-value in this stage.

## Prespecified controls and mandatory falsifiers

1. **Strict causality:** a cluster must not count itself or future/simultaneous fills in lambda(t_i); perturbed future suffix cannot alter earlier predicted intensities.
2. **Cluster invariance:** duplicating prints at existing timestamp leaves M2 fit/score unchanged.
3. **Negative backgrounds:** source-free Poisson-like, unrelated fixed-20s and momentum bursts always reported, even when M2 fits them better than M0. "Strong pattern" is not a ground-truth robot label.
4. **Source gates:** declared clock precision <=1ms is an *asserted source property*, not proof of actual exchange clock fidelity; unknown/coarse timestamp precision and incomplete/missing event history fail closed. M1's stable-window asserted coverage is a separate limitation.
5. **Split identity:** original market-run is statistical unit; three analytical phases are dependent views, never three independent runs. No 3301–3340 rebranding.
6. **Integrity:** no private oracle/agent fields, no raw vendor archives, no licensed-data redistribution, no posthoc seed/threshold/period changes. Always preserve negative findings.

## Evaluation/release restrictions

Time rescaling based on the *estimated in-sample parameters* can yield biased goodness-of-fit calibration. Do **NOT** equate nominal KS bands/p-values with valid model checks without assessing fitting uncertainty and independence. The first M2 stage produces deterministic algorithmic diagnostics, and independent run-disjoint train/calibration/evaluation allocation must be frozen before any fresh ABIDES simulation or source evaluation. No real-market FDR or owner identification.

**External methodological references (checked 2026-11-22; they do not validate this detector):**
- Annual Reviews, *Hawkes Models and Their Applications* (2025): https://doi.org/10.1146/annurev-statistics-112723-034304 — self-exciting model family and event-process context.
- *On the use and misuse of time-rescaling to assess the goodness-of-fit of self-exciting temporal point processes* (2025): https://pmc.ncbi.nlm.nih.gov/articles/PMC12416029/ — estimated-parameter time-rescaling bias and predictive checking caveats.
- Ogata (1988), *Statistical Models for Earthquake Occurrences and Residual Analysis for Point Processes*: https://doi.org/10.1080/01621459.1988.10478560 — classical point-process residual framework.

**NEXT_ACTION:** implement a source-free deterministic M2 training log-likelihood scorer + strict-causal test fixture from this frozen grid, then run relevant cheap tests; do not execute new source experiments until original-run-level allocation and source rights are audited.