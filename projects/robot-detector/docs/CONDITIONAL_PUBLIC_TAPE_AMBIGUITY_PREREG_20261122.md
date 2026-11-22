# Cross-model public-tape ambiguity / short-window L2 coverage stress (2026-11-22)

**SOURCE-FREE PRETEST DESIGN FREEZE**, new unit/invariance analysis, not an empirical market experiment or modification to earlier frozen ABIDES, M0, M1, M1-v2 or M2 protocols. The prior 3301–3340 remain inspected. No new source seeds.

## Scientific falsification question

Can the new M0 (constant cluster rate), M1-v2 (training-only spread-conditioned lagged L2), and M2 (predictable self-excitation) distinguish different private generating stories when **all of their observable public print timestamps and L2 snapshots are identical**? It must be impossible: equality of all public inputs must imply equality of all public-only deterministic outputs, regardless of hidden owner/robot story. Do not claim this proves particular real-world ownership configurations, only a formal public observability limit.

## Entire toy input frozen before scoring

Use two distinct *hypothetical* stories ("unrelated periodic background" vs "controlled schedule") with the **same exact public timestamp clusters** `(20100, 21000, 21900, 22800) ms`, no private story/owner/agent labels passed to inference. Test an additional constructed non-target momentum burst `(20100,20101,20102,22800)` and irregular public clusters `(20100,20710,21930,22850)`. All are 4 unique events within the same complete (source-asserted, *not independently verified*) evaluation window `[20000,23000)` ms.

Freeze source-free training independent of the named toy worlds:
- M0 constant hazard training window [0,5000] with events `(100,500,2000,3000,4500)`.
- M2 same training events as a separate declared original-run identifier, fixed precommitted 3x3 grid and 1.0s decay; no retuning.
- M1-v2 training as exactly two **different** declared source runs: [2000,5000] with public BBO (0,100,102), (3000,100,104), cluster times (2500,4200), and [10000,13000] with BBO (8000,100,104), (10500,100,102), events (11000,12000).
- All constructed evaluation public L2: [20000,23000] with BBO snapshots `(18500,bid=100,ask=102)` and `(20500,bid=100,ask=104)`, both complete, asserted gap-free 1ms source precision, M1-v2 fixed lag=1000ms and max age=10000ms. Evaluation run IDs disjoint from training IDs.

Compute exact **public-only** M0 rescaled event gaps, M1-v2 piecewise public intensity rescaled gaps, M2 exact rescaled event gaps and held-out log likelihood. Return aggregate sizes/min/mean/max and optional state-of-coverage only; do not publish source raw L2, oracle ids or owner labels. Train M0/M1-v2/M2 on the frozen training sets before evaluating toy outcomes; no evaluation data fitting.

## Hard negatives and coverage criteria

- Publicly identical periodic stories MUST yield exactly matching outputs for all models, even when their invented private explanations differ; any discrepancy is a leakage bug.
- Momentum/irregular tapes must be retained with all metrics, **never** claimed to identify a robot based on rescaled spacing alone. No fitted-on-evaluation KS p-values or market FDR.
- Under same 3-second changing-BBO evaluation window, old **M1 stable single prior book** (age allowed <=1000ms) should ABSTAIN for quote age >1000ms; M1-v2 can emit two segments **only** if asserted source continuity holds. This is synthetic engineering coverage improvement and does not prove real L2 quality or exchange completeness.
- Unknown continuity, missing BBO history, unverified clock precision or private fields -> ABSTAIN, not false negative/absence of robot.
- Determinism, split-fill invariance, no future data/lag leaks, all 3 non-target backgrounds are distinct analytic cases not additional original seed worlds.

**Acceptance:** exact public Python CI test of these frozen cases, produce a compact source-free aggregate report and preserve any false confidence/coverage mistakes; before any new ABIDES source design, perform independent data-rights and source-completeness review.