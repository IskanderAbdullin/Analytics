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
