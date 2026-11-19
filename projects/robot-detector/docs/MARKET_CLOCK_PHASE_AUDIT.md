# Independent market-clock synchronization audit

**Stage:** research-only observation / confounder control. **Date:** 19 November 2026. **Status:** C# implementation plus offline tests (CI evidence to be appended after verified run).

## Why this matters

A highly regular sequence of public trade prints can arise because **many trading programs independently react to the exchange clock**. This may create a peak exactly at the start of a second or minute even when there is no single hidden parent order spanning the observations. Therefore neither an FFT peak nor a collection of equal-size public prints can prove the physical number of active bots.

The relevant primary research includes:

- D. Muravyev and J. Picard, *Does trade clustering reduce trading costs? Evidence from periodicity in algorithmic trading*, Financial Management (2022), https://doi.org/10.1111/fima.12405 — marked concentration of trade and quote events in the first 100 ms after a whole second.
- *Periodicity of trading activity in foreign exchange markets*, Journal of Financial Research (2022), https://doi.org/10.1111/jfir.12280 — common clock-time surges near minute boundaries in 25 FX pairs.
- *Intraday periodicity in algorithmic trading*, Journal of Financial Markets (2014), https://www.sciencedirect.com/science/article/pii/S1042443114000274 — round clock-time marks as a potential behavioural/algorithmic common cause.
- Code examples for downstream tick features (different data model, not directly ported): https://github.com/axiomying/tickflow ; https://github.com/Mattbusel/fin-stream ; https://github.com/jonathancornelissen/highfrequency . Read licenses before copying any code; this .NET implementation is independent.

## Design and source separation

Code: `src/RobotDetector.Core/ClockPhaseAudit.cs`. CLI command: `clock-phase-audit`. Input: anonymized public prints from the existing strict T-Invest CSV/GZip reader, without a trading token.

Group **separately** by instrument UID, `TradeSource` (EXCHANGE vs DEALER), `TradingMode` and `SessionId`. All provider-reported trade directions are considered together because the subject is **market clock activity**, not aggressor or passive-order ownership. Never combine two instruments to infer an individual program.

Per group, use the exact original UTC timestamps and count observations in ten [0,100), [100,200), ..., [900,1000) millisecond bins within each second. Default "near clock" window is [0,100)ms. The 10-bin histogram is additive and can be checked against the full group count. We do not re-round source timestamps before calculating the phase.

**Weak but cluster-aware control:** for every UTC minute within a group, apply one shared random 1–999ms phase shift to all events in the minute, modulo 1,000ms. This preserves the number of trades per minute and almost all **relative subsecond timing and bursts within each minute**, while removing their shared alignment with the absolute 1-second boundary. It avoids the worse alternative of uniformly relocating *each* print independently. At the minute boundary, circular wrapping changes cross-minute relationships; that limitation is explicit.

Controls are reproducible by a fixed seed and deterministic group ordering. Default `NullTrials=99`, `MinPrintsPerGroup=100` and at least 2 distinct UTC minute blocks. Small/one-minute groups are marked **ineligible**, not zero evidence.

## Outputs

- Group source identifiers; print count, number of minute blocks, 10×100ms histogram and near-clock share.
- For eligible groups, rotated control counts, mean share and descriptive 95th percentile of rotated shares.
- Descriptive **global** exceedance frequency `(1 + #{rotated_count >= observed_count}) / (B + 1)`. This is a simulation diagnostic only. Do **not** label it a statistical p-value or evidence that a bot exists.
- `OwnerCountKnown=false` and `StatisticalSignificanceEstablished=false` regardless of detected phase peaks.
- Raw file SHA and `FeedCoverageVerified` flag from the source. A historical archive's coverage is not automatically verified.

## CLI

```powershell
cd projects/robot-detector

dotnet run --project src/RobotDetector.Cli -- clock-phase-audit \
 --input fixtures/synthetic_long_cadence_5min.csv \
 --first-ms 100 --min-prints 8 --trials 99 \
 --seed 20261119 --output data/results/synthetic-clock.json

# Example with an actual downloaded archive:
dotnet run --project src/RobotDetector.Cli -- clock-phase-audit \
 --input data/raw/sber_2026-11-17.csv \
 --first-ms 100 --min-prints 100 --trials 99 \
 --output data/results/clock.json
```

No account, broker or order permissions are used.

## Acceptance and critical limitations

1. A synthetic 5-minute clock-aligned sequence maps all prints to first 100ms and is distinguishable descriptively from rotated controls.
2. Synthetic events evenly spaced across all ten 100ms phase bins remain exactly uniform under any common minute rotation.
3. EXCHANGE/DEALER, instrument, mode and session must not be pooled.
4. If there are fewer than 100 prints or fewer than 2 minutes in a group, control metrics must be `null`, never fabricated.
5. Reproducibility by seed, correct subsecond boundaries, no account/trading access, no claim of owner count.
6. Real prints may be bundled, delayed or timestamp-rounded by the data provider; multiple exchange executions may share timestamps. The detector cannot separate provider artefacts without direct venue source auditing.
7. Despite preserving intra-minute bursts, this null does not preserve **cross-minute execution scheduling, queue events, microstructure causality, order IDs or trading halts**. It is not a valid per-pattern FDR without extra evidence.
8. An instrument with a clock peak shows an observable **market-wide rhythm**, not an identified count of algorithms; even consistent behaviour across instruments cannot prove shared ownership.

## Frozen real-data comparison (planned)

After passing synthetic CI, run **SBER_TQBR** and **MOEX_TQBR** on the same existing public archive day (2026-11-17) under identical frozen settings (100ms, 100 prints minimum, 99 rotations, seed 20261119). Record only source SHA, group counts, observed phase shares and control summary. If a specified archive is not available, report `BLOCKED_BY_DATA` and do not quietly choose an alternative.

This first independent cross-instrument comparison is **descriptive**, not an unseen validation of prior optimized parameters and not a release gate. Neither method is allowed to label its findings confirmed bots or profitable signals.


## First empirical cross-instrument result — 2026-11-19

**Completed successfully:** [GitHub Actions run 44549763665](https://github.com/IskanderAbdullin/Analytics/actions/runs/44549763665), same code revision and predeclared settings for SBER_TQBR and MOEX_TQBR on **2026-11-17**. No raw exchange tapes committed or uploaded; source archive and local CA deleted from the runner. [Separate .NET CI](https://github.com/IskanderAbdullin/Analytics/actions/runs/44549763988) passed **69/69** deterministic self-tests, and all CLI smoke checks.

| Measure | SBER_TQBR | MOEX_TQBR |
|---|---:|---:|
| Anonymized public prints | **121,920** | **15,208** |
| Source / trading mode / session | EXCHANGE / UNSPECIFIED / 2026-11-17 | EXCHANGE / UNSPECIFIED / 2026-11-17 |
| Source-specific UTC minute blocks | 1009 | 975 |
| Prints in the first 100ms after whole second | 13,213 | 1,548 |
| Observed first-100ms print share | **10.8374%** | **10.1789%** |
| Mean randomized shared-minute phase share (99 controls) | **10.0540%** | **10.0500%** |
| 95th percentile of control share | **10.5167%** | **10.9613%** |
| Descriptive add-one global-tail fraction | **0.02** | **0.41** |
| Public feed completeness independently verified | No | No |
| Physical owner/bot count known | **No** | **No** |

Compressed archive SHA-256:
- SBER_TQBR: `0af872b1c9c861e7af40a1c40e5bbdf565f9161dd997337c08da584c4dafc782`
- MOEX_TQBR: `81bbb5270ca7b78efcd7ed353e8ab803ba00f212ee50f623e05e3fa884b44948`

The exact 100ms phase-bin histograms are logged in the CI run. **MOEX has its largest bin at 700–800ms (2,030 prints, approximately 13.35%)**, rather than at the predeclared start-of-second bin. It would be **selection bias** to compare this post-hoc peak to the first-100ms control distribution and declare significance. A separate maximum-over-all-10-bins null, with controls using the *same max* functional, is the appropriate next exploratory diagnostic.

### Interpretation

SBER shows a modest excess in the *predeclared* first-100ms window versus within-minute shared-rotation controls; MOEX does not show this excess under the same first-100ms test. These are **observed aggregate clock-phase features**, not identified bots or a transferable forecasting rule. The 0.02 value is a **descriptive Monte Carlo frequency under an imperfect null**, **not** a calibrated p-value or FDR.

The instruments have different volumes, market activity regimes and potential provider timestamp/venue clock artefacts. A day of public prints from each does not prove completeness, independent observations, exact participant counts, or statistical market microstructure causation.

**Decision:** independent code/runtime/data import gates PASSED; inference/owner identification and live trading release gate NOT PASSED. Next: max-over-10 phase-bin control, source timestamp-precision diagnostics and cross-day robustness.
