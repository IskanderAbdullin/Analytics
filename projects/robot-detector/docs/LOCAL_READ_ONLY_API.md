# Local-only snapshot API — Robot Detector (read-only)

**Created:** 2026-11-19. **Milestone:** safe local server shell for historical data. This is **not** a live T-Invest streaming client, not a financial trading signal, and cannot identify a physical bot.

## Quick start (Windows PowerShell)

Requires .NET SDK 10. From `projects/robot-detector/`:

```powershell
dotnet run --project src/RobotDetector.Server -- `
  --input fixtures/synthetic_activity_episode.csv --port 8765
```

Then open in a browser: `http://127.0.0.1:8765/`.

The service loads one CSV/GZip/ZIP archive at startup, builds an immutable aggregated snapshot using `ResearchDashboard.Build`, and serves it locally. It does not require a T-Invest token or a running OsEngine instance. Restart the service to load an updated input file. Stop it using Ctrl+C.

Supported arguments are restricted to `--input`, `--port` (1024–65535, default 8765), `--window-minutes` (default 5), `--max-rows` (default 1,000,000), and `--max-visible-windows` (default 240). Unknown options and invalid values fail rather than silently altering network exposure. There is **no** option to bind to all interfaces.

## Routes (aggregated data only)

| Method | URL | Content |
|---|---|---|
| `GET` | `/` | Fully self-contained, script-free, HTML/CSS market observation dashboard |
| `GET` | `/api/v1/health` | `status=offline_snapshot`, `mode=read_only`, source SHA-256, source public-print count, `tradingEnabled=false`, `liveMarketDataConnected=false`, `actualBotCountKnown=false` |
| `GET` | `/api/v1/summary` | Aggregated `ResearchDashboardReport` JSON, same schema as the standalone dashboard CLI |
| Other routes | any | `404 Not Found` |
| `POST`/`PUT`/`DELETE`/etc. | any | `405 Method Not Allowed` |

The response is **not** a stream of raw prints, nor a participant/order history. No account, broker token, trading, mutation, subscriptions, jobs or external file-write endpoint is implemented. For script-free offline sharing without a running server, prefer the `dashboard --html report.html` CLI command.

## HTTP security envelope

1. The Kestrel listener binds **only IPv4 loopback `127.0.0.1`**. No port forwarding, Internet exposure, or configurable `0.0.0.0` listener. Other machines cannot use the service through the ordinary interface.
2. Requests are rejected unless their remote IP is loopback, `Host` is exactly `127.0.0.1`, and any explicit browser `Origin` is `http://127.0.0.1:<configured port>`. This helps prevent DNS rebinding and cross-origin probing. The server **does not** grant CORS to remote origins.
3. Only GET/HEAD requests are eligible; other methods are explicitly rejected. Unknown read-only routes return 404, not a wildcard action.
4. Headers: no-store caching, no-sniff, frame deny, no-referrer, restrictive Content-Security-Policy without scripts, remote assets or external form submissions.
5. HTML names from imported data are HTML-escaped and includes no raw EventId, account or individual trade print rows. Local imported raw data still resides on the user's disk and should be protected.
6. This is a **loopback-only convenience snapshot server, not a fully authenticated multi-user web service**. Do not expose it through reverse proxies, tunnel providers or public network interfaces; that would require a new security review. Data shown in localhost can still be accessed by local processes with access to the host.
7. File ingestion occurs **before** binding the port, so a failed parse does not expose an incorrect or partial dashboard.
8. The service is read-only, so even a compromised local browser route cannot submit market orders through this app.

## Tests required before release

- .NET 10 standalone server project compiles without NuGet trading dependencies.
- Start the process on loopback with the 40-print synthetic activity fixture. Verify `/api/v1/health`, `/api/v1/summary` and `/`, and that all aggregated output has `actualBotCountKnown=false`.
- Verify POST=>405, unknown route=>404, malicious Host=>403, malicious Origin=>403, CSP + frame protection and no raw trade IDs in HTML.
- Existing `RobotDetector.SelfTests` remain green; original IPO CI unaffected.
- The service must not access private T-Invest accounts or bind a public interface.

## Scientific and architectural limitations

The data displayed are **historic static snapshots** with source-completeness `unverified`. A local health check only confirms the service process, **not** live connectivity, a complete market-data feed, or evidence of a trading robot. Stage 2 prospective tests did **not** establish predictive advantage of the fixed-size cadence detector over placebo. Do not emit execution alerts or statistically calibrated confidence from these routes.

**Next stages:** genuinely incremental, read-only MarketDataStream ingestion with subscription ACK, reconnect/heartbeat, data-quality watermark and network receive timestamps. Then optional read-only OsEngine UI adapter and client-facing replay/diff API. Implementation of a legitimate live data source requires current protocol validation and a user-provided scoped market-data access method. Trade submission remains out of scope.

See [Stage 3 requirements](STAGE_03_REALTIME.md), [Offline research dashboard](OFFLINE_RESEARCH_DASHBOARD.md) and [Bounded replay](BOUNDED_EVENT_REPLAY.md).
