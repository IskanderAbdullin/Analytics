# Stage 2/3 — Genuine ABIDES-NG exchange-execution blinded evaluation

## Scientific objective

Run **the actual ABIDES-NG discrete-event matching-engine simulator**, not our earlier toy generator. Save one *public exchange tape* (what detectors are allowed to observe) and a completely separate *private per-execution agent attribution manifest* (only the scorer can read). Measure event-level precision/recall for fixed-q and variable-q detectors without tuning thresholds on these outcomes.

**Upstream pinned source:** [GabrieleDiCorato/abides-ng at ac7a2a7](https://github.com/GabrieleDiCorato/abides-ng/tree/ac7a2a7bf6e406cd2bbed887e22c5a5a790bb242), BSD-3-Clause. ABIDES-NG modules `abides_core` and `abides_markets`; `SimulationBuilder`, `TWAPExecutionAgentConfig`, `run_simulation` and `ResultProfile.TRADE_ATTRIBUTION`. Upstream's [typed extraction guide](https://github.com/GabrieleDiCorato/abides-ng/blob/main/docs/reference/data-extraction.md) defines `TradeAttribution` as a *single exchange fill*, with maker/taker IDs, passive order side, integer price cents and quantity shares.

## Contract and separation

`tools/abides_export.py` performs the simulation. Two modes: `--mode twap` (one exchange-executed TWAP plus background agents) and `--mode null` (same family of independent background agents, without any controlled TWAP). Both use a 30-minute simulated session, a real ABIDES matching engine, an agent-populated order book, deterministic seeds, and a low-overhead trade-attribution result profile.

The exporter supports four ABIDES strategies: `twap` (fixed-ish slices), `vwap` (volume-profile-weighted slices), `pov` (participation-of-volume), and `null` (independent background). The source implementation uses genuine ABIDES matching execution records, not scheduled parent order requests. Each controlled strategy's private agent name is identified only by its simulation-registered prefix, never by public event IDs.

A deterministic projector builds `public.csv`, containing strictly:
`TRADE_TS,INSTRUMENT_UID,DIRECTION,PRICE,QUANTITY,TRADE_SOURCE,EVENT_ID,TICKER,TRADING_MODE,SESSION_ID,DATA_KIND`.

The CSV uses:
- only **SHA-256-derived opaque event IDs** without producer IDs in the payload;
- UTC microsecond time (ABIDES internal nanoseconds are rounded *down* to 1µs for .NET compatibility; co-timed events remain separate by EventId);
- positive quantity in **simulated shares treated as 1-lot units**, not an assumed MOEX contract lot multiplier;
- positive decimal dollar prices (ABIDES integer cents divided by 100);
- `DIRECTION` set to the *aggressor direction*, derived as the opposite of ABIDES's **passive** order side, not inferred from a real T-Invest feed;
- `TRADE_SOURCE=EXCHANGE`, `DATA_KIND=SIMULATED_ABIDES_NG`.

The private `truth.json`, **never supplied to the detector**, records upstream revision, seed, controlled agent IDs, the public CSV SHA-256 and exact event-level passive/aggressive agent IDs. Identical timestamps and equal quantities do **not** combine fills and do **not** imply shared parent ownership.

`AbidesBlindEvaluation.Score(public.csv,truth.json)` validates exact SHA-256, unique IDs, one-to-one event coverage, complete attribution, source and schema, then runs **both existing detectors on the public CSV only**. After detection it scores labels as controlled if at least one exchange-side participant belongs to the predeclared TWAP agent list. Zero-control null cases produce `EventRecall=null`; all attributions on null are false positives. It exposes no real-world owner count and no trading API.

## Reproduce

From `projects/robot-detector` with Python 3.12 and .NET SDK 10, in an isolated research environment:

```bash
git clone https://github.com/GabrieleDiCorato/abides-ng.git /tmp/abides-ng
git -C /tmp/abides-ng checkout --detach ac7a2a7bf6e406cd2bbed887e22c5a5a790bb242
python -m pip install -e /tmp/abides-ng/abides-core -e /tmp/abides-ng/abides-markets
python -m unittest discover -s tests_python -p 'test_*.py' -v

python tools/abides_export.py --mode twap --seed 41 --public /tmp/abides_twap.csv --truth /tmp/abides_twap_private.json
python tools/abides_export.py --mode null --seed 42 --public /tmp/abides_null.csv --truth /tmp/abides_null_private.json
dotnet run --project src/RobotDetector.Cli -- benchmark-abides-blind --public /tmp/abides_twap.csv --truth /tmp/abides_twap_private.json --output /tmp/twap_score.json
dotnet run --project src/RobotDetector.Cli -- benchmark-abides-blind --public /tmp/abides_null.csv --truth /tmp/abides_null_private.json --output /tmp/null_score.json
```

`--public`/`--truth` must be **different, previously nonexistent paths**. Never add private truth or market archives to the repository. The upstream project is pinned by exact SHA because its config API has had breaking changes. The dedicated CI workflow `.github/workflows/robot-detector-abides-real.yml` runs Python unit tests, installs this exact upstream source, simulates positive and negative scenarios, runs C# self-tests, scores the real ABIDES matching-execution projection, checks print conservation and asserts that controlled prints actually executed in the positive run.

## First executed genuine ABIDES result (2026-11-21)

**[Successful GitHub Actions #44890531080](https://github.com/IskanderAbdullin/Analytics/actions/runs/44890531080)** installed the pinned upstream ABIDES source and ran the matching engine, exported its executed fills and privately scored the two C# detectors. Local Windows and standard .NET CI also passed **123/123** offline checks.

| ABIDES case | Public exchange fills | Privately controlled fills | Fixed-q model | Variable-q model |
|---|---:|---:|---|---|
| TWAP agent, seed 41 | 3,923 | 44 | TP 30, FP 0, FN 14 | TP 0, FP 0, FN 44 |
| No controlled agent, seed 42 | 3,060 | 0 | No attributed prints; recall undefined | No attributed prints; recall undefined |

The fixed-q screen's **30/44 = 68.18% controlled-print recall** in the one observed TWAP run reflects this *particular* ABIDES scenario only. Precision=30/30 for these attributed prints is likewise an in-sample synthetic observation, **not** a measured real-market precision bound. One null seed with no detections establishes no real exchange false discovery rate.

## Frozen-seed replication (separate from tuning)

After the initial smoke, the next protocol freezes untouched synthetic seeds **901, 902, 903, 904**. `tools/abides_batch.py` runs both a TWAP and matched agent-free null for each seed (8 full ABIDES simulations). It serialises only the public CSV fingerprints and aggregate detector scores; the private maker/taker manifest stays in an ephemeral temporary directory and is deleted after scoring. All default detector thresholds remain unchanged. This is a *synthetic held-out seed* study, not truly held-out real market data or a statistically calibrated release gate.

```bash
python tools/abides_batch.py --holdout-seeds 901 902 903 904 \
  --cli-dll src/RobotDetector.Cli/bin/Release/net10.0/RobotDetector.Cli.dll \
  --output /tmp/abides_holdout_4seeds.json
```

The [executed frozen-seed CI #44890937246](https://github.com/IskanderAbdullin/Analytics/actions/runs/44890937246) confirmed exactly eight cases with 123/123 C# self-tests, Python projector tests and complete source/truth reconciliation:

| Frozen simulation (4 seeds, 901–904) | Public exchange fills | Executed controlled prints | Fixed-q detector | Variable-q detector |
|---|---:|---:|---|---|
| TWAP execution | 14,761 | 197 | TP 101, FP 0, missed 96 (51.27% controlled-print recall) | TP 0, FP 0, missed 197 |
| Background-only null | 14,639 | 0 | No attributions; recall undefined | No attributions; recall undefined |

**Additional genuine execution strategies (development probes, NOT in the frozen TWAP cohort):**

| Strategy and seed | Public exchange fills | Controlled prints | Fixed-q model | Variable-q model |
|---|---:|---:|---|---|
| VWAP, 43 | 3,788 | 50 | 0 controlled prints recovered | 0 controlled prints recovered |
| POV, 44 | 3,702 | 14 | 0 controlled prints recovered | 0 controlled prints recovered |

Both VWAP and POV controlled execution fills **actually occurred**, verified through matching-engine private maker/taker attribution. Their complete missed detection is a limitation of the present detector models on these synthetic examples, NOT evidence that these market executions are non-algorithmic. Zero false positive attributions in four toy null runs establishes no real-market specificity and cannot be extrapolated to MOEX/SPB.

A second report version, `abides-blind-score-v2`, adds `postHocControlledDiagnostics`: distinct quantities, unique timestamps, collisions, median positive/nonpositive interprint intervals, all calculated using hidden controlled-truth labels strictly **after** both detectors finish. Do not feed these post-hoc statistics into the detector or reuse the same seeds as a fresh holdout after tuning new algorithms.

## New independent executed-fill baseline (pre-registered 2026-11-21)

The initial ABIDES TWAP/fixed-q 4-seed cohort (901–904), and individual VWAP/POV examples (43,44), have already been inspected and therefore **cannot** be treated as unused evaluation data. Public volume-response development seeds (61–63), directional-share development seeds (71–73) and independent share-shift replication (1101–1104) are likewise spent. The [direction-share replication](DIRECTIONAL_REGIME_SHIFT.md) found null 1 / VWAP 0 / POV 1 public shift windows at fixed settings, so **that feature does not provide reliable program recognition**.

For the **original unchanged existing C# fixed-/variable-quantity screens**, the next execution-level test pre-registers **entirely new** ABIDES seeds `1301,1302,1303,1304`, four simulator modes `null,twap,vwap,pov`, and both existing detector default configurations. See `tools/abides_execution_baseline_holdout.py`.

The protocol runs **16 genuine matching-engine simulations** with complete maker/taker per-fill attribution. Each detector sees **only public CSV prints**. The existing `benchmark-abides-blind` C# scorer reads private labels **only after the candidate detection outputs are produced**, verifies a SHA-256-linked one-to-one event mapping, and writes aggregate-only synthetic event counts TP/FP/missed by model and mode. Every private manifest and detailed public tape is stored only in an ephemeral CI directory, not in artifacts or the repository. Report metrics:

- `pooled_event_recall = controlled synthetic prints detected / all controlled synthetic prints` for positive modes, **null** for zero-controlled null scenarios.
- `pooled_event_precision = controlled prints detected / all publicly attributed prints` if any attribution, else **null**.
- `false_positive_prints`: publicly attributed print IDs belonging to **uncontrolled synthetic agent participation**; this is not a calibrated real-market FDR.
- `cases_with_any_attribution`: descriptive number of four simulator runs in which the screen emitted at least one public print attribution.

**No detector coefficients, periods, sizes or cutoffs are changed** and no frozen-run labels are used in training. A locked seed/mode/config contract and a Python accounting-unit test are committed **before** the results. If a positive strategy fails to execute actual exchange fills, the experiment fails instead of misleadingly counting it as zero recall. The separate aggregate-only workflow artifact has 14-day retention.

This test cannot establish physical traders, actual MOEX/SPB precision, a market opportunity or independent physical bots. The 1301–1304 cohort becomes **spent immediately after evaluation**; no further model tuning against it is permitted. Any future new strategy requires a new unrelated hidden evaluation set.

## Scientific limits and release gates

ABIDES-NG is a synthetic exchange simulator, not a calibrated representation of MOEX/SPB, nor an independent prediction trial on untouched real instruments/dates. One seeded scenario with an ABIDES execution agent does not prove precision, recall or model advantage on a real market. Exchange per-fill truth identifies synthetic agent participants, **not** independent physical real-world owners. The private truth is an evaluator input; tampering SHA mismatches or event records fails closed, but the scorer cannot cryptographically prove that an external manifest really originated from ABIDES unless the environment/source is independently audited.

**Stage 2 scientific gate: CLOSED** until: more than one agent strategy (TWAP/VWAP/POV), multiple liquidity regimes, exact full-coverage exported fills, independently frozen holdout seeds/instruments and predeclared controls, confidence bounds and multiple-testing procedures, validation of actual T-Invest public semantics, and prospective real-market edge vs placebo.

The simulator uses its own exchange and simulated execution orders only. **No real broker API calls, no user account requests, no OS Engine changes and no live order placement.**
