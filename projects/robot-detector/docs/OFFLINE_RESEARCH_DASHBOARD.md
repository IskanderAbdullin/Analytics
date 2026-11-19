# Local offline research dashboard — Stage 3 (read-only, no broker account)

**Created:** 2026-11-19. **Purpose:** make existing, independently tested *observational* market-data methods accessible in a standalone HTML report without a server, JavaScript, browser connector, cloud session, or OsEngine install.

## One command

Requires .NET SDK 10. From `projects/robot-detector/`, on Windows PowerShell:

```powershell
dotnet run --project src/RobotDetector.Cli -- dashboard `
  --input fixtures/synthetic_activity_episode.csv `
  --html data/results/research.html `
  --json data/results/research.json
start data/results/research.html
```

For a downloaded public T-Invest CSV/GZip or ZIP archive, replace `--input` with its local path. Do not upload non-public broker/account information. Options: `--window-minutes 5` (1–1440), `--max-visible-windows 240` (1–5000), `--max-rows 1000000`. Both HTML and JSON outputs are **new files only**: the CLI refuses to overwrite existing results.

**Read-only operations:** no gRPC connection, API token, portfolio, account, order endpoint, market order placement, webhook, remote UI server or internet access. The report's Content-Security-Policy denies all external resources and scripting; only inline CSS is allowed. The HTML can be opened locally in the default browser without an extension or plugin.

## What it shows (and what it does not)

- **Public print count, observed lots, instruments and populated windows**. All underlying events are counted once across instrument UID, source, trading mode and session; missing intervals are not invented as zero-activity windows.
- **Reported BUY/SELL imbalance** (provider definition, **not** the passive order side); 1-second print-count Fano factor; share of public prints near a whole second.
- **High-activity historical episodes**. Only preceding, contiguous 5-minute windows in the same instrument/source/mode/session are compared; candidate windows are `unvalidated_observed_activity`, never a physical bot.
- **Timestamp collision share** from the independent `TimestampQualityAudit`; prints sharing timestamps are **never deduplicated**.
- **Standalone HTML visualization**: summary metrics, source comparison table and up to N busiest populated windows. All report windows remain in optional JSON, independent of what HTML displays.
- **SHA-256 provenance** of the original source and importer rejected-row count. A successful CSV import does not verify full exchange coverage.
- Explicit **`actualBotCountKnown=false`** and **`statisticalSignificanceEstablished=false`**. No "99% confirmed bot" claims, no profitable trading signals and no new predictions.

Unlike the fixed-clip and variable-clip period screen, the dashboard does **not** rely on selecting periodic candidates. It prioritizes robust, reproducible, explainable **market flow**. Existing periodic detectors remain available as research commands.

## Data contracts

New module `src/RobotDetector.Core/ResearchDashboard.cs` has `ResearchDashboard.Build(TradeImportResult, windowMinutes)` and `ResearchDashboard.ToStandaloneHtml(ResearchDashboardReport, maximumVisibleWindows)`. No external packages; only .NET 10 BCL. It reuses, without changing their implementation:

- `FlowFootprint.Describe` for temporal windows, lots and Fano statistics;
- `FlowActivityEpisodes.Find` for past-only elevated-activity observations;
- `TimestampQualityAudit.Describe` for duplicate-clock timestamp diagnostics.

The module **fails closed** if these independent calculations disagree on input print totals, source groups, elevated activity counts or the summarized HTML report's cardinality. The HTML renderer encodes all untrusted ticker/UID/source/session/filename strings with `WebUtility.HtmlEncode`. It includes **no individual trade event IDs or source rows**.

## Validation checklist

- Synthetic: conservation of all original prints and lots, direction/source isolation, equal-timestamp preservation, activity-episode status, empty inputs and configured 10-minute window width;
- Security: escaped untrusted HTML labels, no script tags/remote requests, restrictive CSP, deterministic HTML contents;
- Data integrity: tampered source/window counts and fabricated activity labels are rejected;
- CI: .NET 10 Core, CLI, SelfTests, synthetic dashboard export, JSON/HTML smoke and no order API dependency;
- Empirical trial: a read-only one-day SBER archive should produce report summaries; no raw archive or standalone report stored as build artifact without explicit data rights.

## Scientific status

**Engineering UI gate:** requires green CI and one reproducible authentic public-archive smoke run.

**Scientific/forecasting gate:** still **NOT PASSED**, and this dashboard does not change that. Fixed-clip future predictions matched the phase-shift placebo on two independent SBER days; source clocks and common-activity effects are confounded; identities are unobservable.

**Next independent work:** multi-instrument dashboard batch support; offline replay toward optional read-only T-Invest MarketDataStream and OsEngine adapter. Live API access needs explicit token/config from the user and separate source/coverage validation; it must never automatically place orders.

References: [T-Invest public market-data stream definition](https://developer.tbank.ru/invest/services/quotes/marketdata), [ABIDES-NG open-agent simulator](https://github.com/GabrieleDiCorato/abides-ng), [Stage 3 requirements](STAGE_03_REALTIME.md).
