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

## Actual results — 2026-11-18

**Completed successfully.** [GitHub Actions run 44298537864](https://github.com/IskanderAbdullin/Analytics/actions/runs/44298537864). The runner built the .NET project and passed **32/32 self-tests**, downloaded only two public GZip archives, evaluated all forecasts, printed aggregate results and deleted the downloaded tapes and temporary root certificate. This is a prospective historical *replay* of prints after frozen cutoffs, not a live trading prediction made before the actual November dates.

| Measure | 2026-11-12 | 2026-11-13 |
|---|---:|---:|
| Public prints read | 139,600 | 106,127 |
| Distinct source/session groups | 1 | 2 |
| UTC cutoffs evaluated | 12 | 12 |
| Scorable candidate forecast windows | **489** | **494** |
| Matches at the candidate target | **8** | **6** |
| Matches at the T/2-shifted placebo target | **8** | **6** |
| Observed target hit rate | **1.636%** | **1.215%** |
| Placebo hit rate | **1.636%** | **1.215%** |
| Feed completeness independently verified | No | No |
| Actual independent bot owners identified | Unknown | Unknown |

Source compressed file SHA-256:
- 2026-11-12: 8239d0cb6a65799fbb6e14fc60c9c2ab8dddd671e3e54ab19f17c378b7b2dc16
- 2026-11-13: 1a82aecb3225cfbd1ce93654dc87a8e161e9c7b3484878bd12808a8fc92b2ce2

**Combined:** 245,727 public trade prints, 983 scorable forecast windows, **14 matched future target prints**, **14 matched phase-shift placebo prints**, 1.424% observed target hit rate and the same 1.424% placebo hit rate. Source data completeness was not verified.

### Decision

**Stage-2 prospective forecasting gate: NOT PASSED.** The fixed-quantity cadence screen shows no observed advantage over its simple T/2-shifted placebo on these two previously unused dates under the predeclared settings. Historical candidate counts and dual size-null excesses from 16/17 November **cannot** be translated into predictive power or evidence of actual robot identities.

This does not show that all algorithmic flow is unpredictable: the tested detector imposes exact clip sizes, cannot model changing execution schedules, partial fills or latent parent orders, and its current session/market completeness representation is limited. The placebo itself is a simple heuristic baseline. However, **it is unsafe to claim a reliable next-print signal** without further independent validation.

### Required corrective experiments (without tuning on this held-out result)

1. **Document model failure modes:** quantify whether patterns stop, drift in phase, change child volume, or are spurious common-clock bursts. Diagnostics must use a new development set rather than optimizing on Nov 12/13.
2. Separate **detection** and **prediction**: require an independent, strictly historical training holdout before declaring a candidate ready to forecast; a count of 6 historical prints is not statistical validation.
3. Compare periods/harmonics after source precision correction; detect changes in q with separately validated variable-size TWAP models.
4. Study multi-execution splits and liquidity/auction regimes. Do not reinterpret provider direction as the passive order side.
5. Establish better placebos preserving clock-time bursts and conditional q distribution, with multiplicity correction and confidence intervals; use synthetic ABIDES ground truth.
6. Run final **untouched** held-out dates/instruments, frozen in advance. Never promote to live algorithmic signals until forecast improvement survives these tests and a feed-completeness audit.

The project remains valuable as a **research-oriented, read-only historical pattern screener**, not a validated forecasting/robot-counting system.

