# Stage 2/3 — Genuine ABIDES-NG exchange-execution blinded evaluation

## Scientific objective

Run **the actual ABIDES-NG discrete-event matching-engine simulator**, not our earlier toy generator. Save one *public exchange tape* (what detectors are allowed to observe) and a completely separate *private per-execution agent attribution manifest* (only the scorer can read). Measure event-level precision/recall for fixed-q and variable-q detectors without tuning thresholds on these outcomes.

**Upstream pinned source:** [GabrieleDiCorato/abides-ng at ac7a2a7](https://github.com/GabrieleDiCorato/abides-ng/tree/ac7a2a7bf6e406cd2bbed887e22c5a5a790bb242), BSD-3-Clause. ABIDES-NG modules `abides_core` and `abides_markets`; `SimulationBuilder`, `TWAPExecutionAgentConfig`, `run_simulation` and `ResultProfile.TRADE_ATTRIBUTION`. Upstream's [typed extraction guide](https://github.com/GabrieleDiCorato/abides-ng/blob/main/docs/reference/data-extraction.md) defines `TradeAttribution` as a *single exchange fill*, with maker/taker IDs, passive order side, integer price cents and quantity shares.

## Contract and separation

`tools/abides_export.py` performs the simulation. Two modes: `--mode twap` (one exchange-executed TWAP plus background agents) and `--mode null` (same family of independent background agents, without any controlled TWAP). Both use a 30-minute simulated session, a real ABIDES matching engine, an agent-populated order book, deterministic seeds, and a low-overhead trade-attribution result profile.

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

The CI must compare event conservation and null recall semantics across all eight cases. Do not cite batch results until the batch actually runs successfully.

## Scientific limits and release gates

ABIDES-NG is a synthetic exchange simulator, not a calibrated representation of MOEX/SPB, nor an independent prediction trial on untouched real instruments/dates. One seeded scenario with an ABIDES execution agent does not prove precision, recall or model advantage on a real market. Exchange per-fill truth identifies synthetic agent participants, **not** independent physical real-world owners. The private truth is an evaluator input; tampering SHA mismatches or event records fails closed, but the scorer cannot cryptographically prove that an external manifest really originated from ABIDES unless the environment/source is independently audited.

**Stage 2 scientific gate: CLOSED** until: more than one agent strategy (TWAP/VWAP/POV), multiple liquidity regimes, exact full-coverage exported fills, independently frozen holdout seeds/instruments and predeclared controls, confidence bounds and multiple-testing procedures, validation of actual T-Invest public semantics, and prospective real-market edge vs placebo.

The simulator uses its own exchange and simulated execution orders only. **No real broker API calls, no user account requests, no OS Engine changes and no live order placement.**
