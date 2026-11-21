# ABIDES L2: preregistered background versus controlled TWAP, clock-origin sensitivity

**Protocol committed before observing outcomes:** 2026-11-21.
**Scope:** genuine synthetic ABIDES matching engine, public depth-five L2 and
executed prints, **development only**. Not real-market inference, not a
certified fresh blind holdout, and not a detector of physical participants.

## Research question

The earlier background-only ABIDES study found public previous-bin book
imbalance versus next-bin BUY-share `rho` changed appreciably when the
30-second clock *origin* changed. Does adding one known TWAP execution
program to the same background configuration change the public feature,
and is any resulting descriptive difference sensitive to the same
clock-origin choice?

This is **not a controlled causal effect of adding one execution print**:
inserting an agent can alter the entire simulated order book and background
behavior. No selection of a best width, phase, rho threshold or agent count.

## Frozen design and provenance

- Pinned genuine exchange simulator at
  `ac7a2a7bf6e406cd2bbed887e22c5a5a790bb242`.
- New project-locally registered **development-only** seeds `2401,2402`,
  added to `research/seed_registry.json` and AST-checked against the
  source `SEEDS` constant **before first run**. Their global novelty
  is not independently established; they are spent for future blinded
  evaluation on first inspection.
- 2 seeds × 2 scenarios = exactly **4 actual market simulations**.
  Scenarios: 60 Poisson NoiseAgents (20-second mean wake-up), with or
  without one TWAPExecutionAgent. Session 09:30–09:42, ABM ticker, L2
  capture depth five. TWAP parameters: buy-side market orders, 1200 lots,
  45-second schedule, start/end offsets one minute.
- Every original public tape is reprocessed at exactly three 30-second
  clock origins: **0s / 10s / 20s**. Exactly **12 dependent analytical
  rows**, not 12 new simulations.
- Last L2 snapshot of the previous completed bin's imbalance compared
  with next populated trade bin's reported BUY lot share, tie-aware
  Spearman. No individual order or owner identification.
- Combined SHA-256 commits every ordered L2 snapshot and anonymous
  print, with exact clock-shift normalization and strict public input
  validation. Same-tape consistency is checked between all three
  origin views of each simulation.
- **Private** ABIDES agent IDs are used **after** public book/print
  feature computation only to check a controlled strategy produced
  some real matched executions. No IDs are passed to the feature,
  persisted in the JSON or uploaded as an artifact.
- No real archive completeness attestation and no independent
  certification that the ABIDES background matches MOEX/SPB.

## Predeclared acceptance and stopping criteria

The source tests must pass before installing ABIDES. A missing public
book, no fills for the injected TWAP, invalid mixed case matrix,
failing source totals, non-finite coefficients or changed original
tape hashes is a **failed study**, not a success or missing-zero
substitution. Complete aggregate contains 6 separate cohort rows
(`scenario × origin`) and all 12 anonymized case summaries.

**No statistical or trading release gate can be opened** by either
a high or low rho in this study. The private truth count is only a
post-hoc simulation manipulation check. Samples may be dependent across
background modes by seed; there are only four genuinely simulated
market sessions and no independent out-of-sample market labels.

## Reproduction

```bash
cd projects/robot-detector
python -m unittest discover -s tests_background -p 'test_abides_l2_twap_phase_contrast.py' -v
python -m unittest discover -s tests_background -p 'test_public_tape_fingerprint.py' -v
# Only after installing the pinned ABIDES upstream:
python tools/abides_l2_twap_phase_contrast.py --output /tmp/abides-l2-twap-phase-contrast.json
```

A single explicitly source-triggered GitHub workflow performs the
original frozen developmental experiment and saves an **aggregate-only**
7-day artifact. After execution the workflow should become manual-only
to avoid repeated expensive runs of already spent synthetic seeds.

No user accounts, broker APIs, live orders, secrets or raw market files
are created or modified.

## Executed genuine simulation (2026-11-21)

[Successful pinned ABIDES CI #44915375635](https://github.com/IskanderAbdullin/Analytics/actions/runs/44915375635)
ran all source-only preregistration tests, installed the exact pinned
matching-engine revision, generated **four real synthetic exchange market
simulations** and examined exactly **12 dependent public time-origin
views**. The aggregate-only result artifact is
`abides-public-l2-twap-phase-contrast` (artifact ID
`14711182500`), full original JSON SHA-256:

```text
2391c9f223b6841f8346502282b7e099856e6feee7726cd4769967dcbcd97fa8
```

The compact source-controlled
`fixtures/abides_l2_twap_phase_observed_20261121.json` records all
twelve resulting case summaries, exact full-public-tape hashes and
post-hoc counts, not the raw events or private agent IDs.

| Scenario | Seed | rho 0s | rho 10s | rho 20s | TWAP controlled execution prints |
|---|---:|---:|---:|---:|---:|
| Background only | 2401 | +0.3123 | −0.0583 | −0.3687 | 0 |
| Background only | 2402 | −0.7647 | −0.0643 | −0.5824 | 0 |
| Injected TWAP | 2401 | +0.3981 | +0.0148 | +0.1937 | 22 |
| Injected TWAP | 2402 | −0.5404 | −0.0147 | +0.0072 | 22 |

| Cohort median (two original runs per mode) | rho 0s | rho 10s | rho 20s |
|---|---:|---:|---:|
| Background only | −0.2262 | −0.0613 | −0.4756 |
| With TWAP | −0.0711 | +0.000058 | +0.1004 |

**Interpretation and limits:** two of four original simulations reverse
the sign of the descriptive rho between the three fixed clock phases:
one background-only, one with injected TWAP. All four original
simulations have phase-dependent eligible-bin counts. Both backgrounds
and injected scenarios show large shifts in rho without selecting a
best phase. In the TWAP cohort at 10s, the near-zero median comes from
individual values +0.014822 and −0.014706, not a stable zero across
seeds. Likewise changing the market by adding a TWAP changes overall
prices, quantities, book snapshots and executed prints; seed-level
comparison is not a matched-print causal estimate.

This confirms the programmatic manipulation check and **fails to
validate rho as a phase-invariant individual-robot identifier**.
The original seed pair (2401/2402) is now spent in this project,
not an untouched future holdout. Neither the synthetic controlled
execution count nor a correlation coefficient can establish
the number of real-world parent orders, owner identities, predictive
market signal value, or the true market false-alarm rate.

After the successful original run, the expensive workflow is
**manual-dispatch only**. Lightweight CI continues to validate
preregistration, the frozen observed scalar fixture and source tests.

## Follow-up: the clock-phase separation trap

The source-only `abides_l2_twap_separability.py` reads all **twelve
already executed** public L2 coefficients, with strict case and
provenance validation. This checks a mathematically simple **in-sample
range ordering**: is the lowest injected-TWAP rho above the *highest*
background-only rho at the same origin? It is a warning about data
snooping, **not** a fitted model, a tuned threshold or out-of-sample
detection probability.

| Pre-registered 30-second origin | Strict observed rho range separation? | TWAP minimum rho − background maximum rho |
|---|---|---:|
| 0 seconds | **No** | −0.8526 |
| 10 seconds | **Yes** | +0.0436 |
| 20 seconds | **Yes** | +0.3759 |
| All three origins considered together | **No** | Negative |

These are *two* development background runs versus *two* injected
development runs at each origin, not a statistically powered train/test
benchmark. Changing nothing except the analytical clock origin can
turn apparent perfect separation **on or off** in this tiny sample.
Precommitting a single preferred origin from these results would
be post-hoc model selection; no such choice is made.

On the same nominal seeds, injected-TWAP rho was higher than the
background-only rho at all three origins; those are six **descriptive**
seed-aligned scenario differences, not six independent causal effects.
Injected TWAP changes the market endogenously and all views share
few original simulations. Without new truly blinded market validation,
neither this observation nor the positive at 10s/20s licenses a
physical bot count, market false-positive claim or live trading.

The cheap research-ledger CI now verifies this counterexample
with the immutable observed fixture and explicit null/undefined
negative tests. No additional ABIDES simulations are run.
