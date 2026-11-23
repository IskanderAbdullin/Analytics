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
