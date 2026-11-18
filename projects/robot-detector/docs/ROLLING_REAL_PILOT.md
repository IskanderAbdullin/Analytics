# Prospectively evaluated cadence-screen signals on two unseen SBER dates

**Protocol registered 2026-11-18 before reading these dates.** Stage 2 read-only research. This uses the newly implemented rolling forecast against historical anonymized prints; the forecast maker sees only prints at or before each cutoff.

## Predeclared evaluation

- Instrument SBER_TQBR, public T-Invest anonymized trade history.
- **Evaluation dates: 2026-11-12 and 2026-11-13**, which were not used to choose the detector's previous November 16/17 null-control statistics.
- Same .NET revision, parameters and public archive schema on both dates. No interactive tuning or cherry-picking outcomes after the first run.
- Settings: MinMatches=6, 60-minute detector windows, max 5,000 same-size prints per chunk; warmupMinutes=60, strideMinutes=30, maximumCutoffsPerSession=12.
- Immutable one-day compressed archive per date, SHA-256; source/session/trading mode separately grouped; never request account, portfolio or order/trading endpoints.
- For each cutoff, only earlier trades can create period/phase/quantity hypotheses. Score the next window in later prints. Compare against a T/2-shifted window with the same q, side, source and tolerance.
- Only score a hypothesis if both original and placebo target windows occur before the end of the captured file. Deduplicate repeated target slots; no double use of actual future print IDs.
- Full CSV/GZip import must have zero rejected rows to consider a successful technical run. Data stream completeness is NOT verified by this condition.
- Print aggregate counts only: number of prints, examined cutoffs, forecasts, observed hits, placebo hits, observed and placebo observed hit rates; original file hash. No individual prints, account identifiers, trading orders or secrets in logs/artifacts.
- All raw files removed at workflow end. Official Russian Trusted Root CA certificate downloaded over normally validated HTTPS, subject- and fingerprint-checked, then applied only to this runner process. TLS verification never disabled.

## Expected interpretation

A higher realized hit rate than the phase-shift placebo would indicate **some forward predictability of selected periodic prints under this one test**. It would not prove that those prints belong to the same participant, nor establish profitable trading or statistically calibrated confidence. A lower hit rate or no predictions is also an important result and must not be concealed.

The half-period placebo is a rudimentary comparator. Because multiple hypotheses are screened and the venue may have a common clock and feed gaps, its difference from actual hits cannot be called a p-value, FDR, precision at identifying bots, or validated win rate. Results cannot on their own pass the full Stage 2 scientific gate. See ROLLING_FORECAST.md and STAGE_02_VALIDATION.md.

## Follow-ups

- A later distinct time window and several other instruments with frozen parameters and stronger conditional nulls.
- Direct ABIDES/NASDAQ-like known-agent blind truth for event-level attribution, including variable TWAP clips and partial fills.
- Session calendar corrections, source completeness/latency checks, per-pattern dedup and nonstationary regime analysis.
- Only after credible calibration should online alerts or trade-bot integrations be considered.

**Observed results:** deliberately blank before the CI run.
