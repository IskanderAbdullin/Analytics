# Standalone multi-archive market comparison

**Status:** implementation on development branch, empirical validation pending (2026-11-19). Entirely read-only; no trading tokens or account endpoints.

## Goal

Avoid tuning a single fixed-size cadence detector to one equity. Compare **observable** trade flow and timestamp quality from 2–20 **independent source files** under the same time-window configuration. A higher Fano factor, near-second timestamp concentration or activity episode rate does not identify the physical owner of a trade or a robot.

Reuses only already-tested `ResearchDashboard.Build` results, which in turn use `FlowFootprint`, `FlowActivityEpisodes`, and `TimestampQualityAudit`. This comparison does not run a trader classifier, perform machine learning, infer parent orders, or place/modify/cancel orders.

## How to run on Windows

From `projects/robot-detector/` with .NET SDK 10:

```powershell
dotnet run --project src/RobotDetector.Cli -- compare-archives `
  --inputs "data/raw/SBER_2026-11-17.csv;data/raw/MOEX_2026-11-17.csv" `
  --window-minutes 5 `
  --html data/results/market-comparison.html `
  --json data/results/market-comparison.json
start data/results/market-comparison.html
```

The `--inputs` argument is a quoted semicolon-separated list of **2..20** files. The CLI refuses duplicate canonical file paths; the core comparator rejects duplicate raw source SHA-256 values, mismatched UTC window widths and corrupted aggregate totals. A different file SHA alone **does not prove** that two files have disjoint public market data, so overlapping sources remain a caveat. `--max-rows` defaults to 1 million per file. HTML and JSON outputs must not exist already.

## Report

One row per input archive: instrument tickers, source/trading mode, input print count, observed lots, populated windows, observed high-activity windows, timestamp collision share, percentage of prints in the first 100ms of a UTC second, and median of within-window Fano factors (one-second bins). Other source grouping/session distinctions remain in the source's single-file dashboard.

The rendered HTML is fully static: no scripts, external assets, JavaScript or HTTP connections; source-supplied labels are escaped before interpolation. No raw per-trade IDs, participant/account data, tokens, orders or individual exchange executions are written to the HTML.

The JSON includes source SHA-256 and flags `actualBotCountKnown=false`, `statisticalSignificanceEstablished=false`, `sourceCoverageVerified=false` for isolated public archives. `ComparableDataKinds` is false if someone attempts to compare synthetic and historical trades as interchangeable market samples.

## Tests and empirical protocol

Synthetic regression checks: 7 + 40 separately loaded public-like prints add up to 47; no cross-file deduplication, duplicate SHA refusal, mismatched window width rejection, malicious ticker/filename HTML escaping, mixed provenance warning, empty-source handling, deterministic output and corrupted summary rejection. Complete project CI must pass.

**Predeclared public check (no model fitting):** SBER_TQBR and MOEX_TQBR on the **same 2026-11-17 date**, available from the read-only historical T-Invest endpoint. Exactly two public archives, same 5-minute window width, 1-second Fano bins and 100ms first-clock cutoff. Print source hashes and aggregate metrics only. Delete downloaded tapes and temporary official pinned root CA at the end. No raw trade tape or HTML artifact is published as a CI artifact.

Do not interpret cross-instrument difference as a test of independent robots: liquidity, tick size, sessions, dealer mixing, auctions, timestamp formation and source completeness can differ. There is no null-calibrated significance, live prediction or true owner identity.

**Observed results:** only to be added after an actual successful CI run. A failure or missing day must remain visible as `BLOCKED_BY_DATA`, not a zero-robot result.

## Research next steps

- Add formal stratification by trade intensity, instrument/day/session instead of directly treating higher collision/Fano ratios as a stronger signal.
- Construct a **controlled known-agent** ABIDES market tape with hidden agent IDs projected out of the observations, to measure precision and recall without attributing real public prints to identities.
- Feed truly incremental market receipts through a local read-only source adapter; archived row order must never be used as a latency estimate.
- Gate any live alerts and external OsEngine UI until statistical validation produces independent predictive evidence.

References: [T-Invest anonymized trade history](https://developer.tbank.ru/invest/services/history-md/head-history-md), [ABIDES-NG](https://github.com/GabrieleDiCorato/abides-ng), [existing single-file dashboard](OFFLINE_RESEARCH_DASHBOARD.md), [Stage 2 validation](STAGE_02_VALIDATION.md).
