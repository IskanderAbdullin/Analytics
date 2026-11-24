# PLAN

1. Отдельный Python (stdlib) API-клиент и автономные тесты, без реальных ключей.
2. Самостоятельный GitHub Actions workflow с push + manual workflow_dispatch.
3. Проверка первого запуска в публичном Analytics без Secrets.
4. Хранение read-only токена Cloudflare и account ID в Actions Secrets Analytics.
5. Проверка настоящих GET settings и deployments; результат редактируется
   строго по белому списку.
6. Отдельное расширение до управляемого deploy только после проверки
   версии живых Worker, сохранения rollback и согласования прав.

## Post-G-001 active Serverspace stages (2026-11-23)
- DONE: authenticated fixed private Serverspace GET from Cloudflare named entrypoint, via Cron diagnostic Worker; original diagnostic schedule disabled after success.
- DONE: direct production OAuth Worker injection + private Service Binding using code-only and settings-only official Cloudflare API; all original 25 bindings inherited and verified.
- NEXT: registered ChatGPT MCP connector must discover `serverspace_list_servers` and invoke it with owner OAuth; check live allowlisted output. Current session tool catalogue is stale/does not expose it.
- FUTURE: explicitly scoped provider VPS control operations and independent Ubuntu command channel. Trading automation and power changes remain untouched.

## Active continuation update 2026-11-23 22:04 UTC
1. Read-only aggregate-only `summary_v1` result from the existing diagnostic KV after scheduled Cron propagation; record only totals and disable schedule after verified success. Do not mutate the production VPS.
2. Restore Linux WSS device connectivity through existing dedicated route: active admin export has been repaired, bindings and workers.dev are enabled, but `vps_status` still gives HTTP 503. Next diagnosis needs device session / Linux agent environment, not more Cloudflare export uploads.
3. Resolve OAuth MCP tool discovery; no direct ChatGPT `serverspace_list_servers` call confirmed though provider Service binding and code live.
4. Review and test staged draft MCP-proxi PR #20 privately, with control flags disabled and separate targeted owner authorization, before any power API deploy. Real Linux root shell is a distinct channel from Serverspace provider power endpoints.

## 2026-11-24 05:16 UTC — re-prioritized based on real SSH-equivalent root command success
**Proven**: owner OAuth `vps_status` and `vps_exec` can reach live Ubuntu 26.04 as `babit-admin` and `sudo root`. The goal of basic Linux shell access is achieved; **the reliability objective remains open** (579 agent WSS disconnects since 00:00Z against four connects by 05:11Z).
1. Build and review [private PR #21](https://github.com/IskanderAbdullin/MCP-proxi/pull/21) redacted phase/error telemetry without secrets; do not deploy uncompiled C# or restart trading.
2. Controlled and reversible administration-agent-only deployment, followed by bounded classification of real reconnect failures. Correct evidenced cause, not speculative Cloudflare worker fixes.
3. Refresh owner ChatGPT connector tool schema to expose existing server-side `serverspace_list_servers`, or an officially supported tool-discovery mechanism. No extra plugin/worker duplicates.
4. Keep separately staged [provider-power PR #20](https://github.com/IskanderAbdullin/MCP-proxi/pull/20) disabled; only a targeted owner-approved command may ever enable mutation. The actual Serverspace project has one powered-on VPS.

## 2026-11-24 05:24 UTC
- Existing t-invest_IIS **private plugin manifest** updated in place to v1.0.1 with the same App binding. Tool catalogue in the current session remained unchanged (18 tools, no serverspace_list_servers). Do not duplicate or repeatedly republish the plugin; prioritize actually supported re-discovery at a new session boundary.
- Linux root shell proven but WSS stability not achieved; next actionable fix requires compiling and deploying source-only categorized WSS logging in private [PR #21](https://github.com/IskanderAbdullin/MCP-proxi/pull/21). Separate provider-control [PR #20](https://github.com/IskanderAbdullin/MCP-proxi/pull/20) remains disabled and unshipped.
