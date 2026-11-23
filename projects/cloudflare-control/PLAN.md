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
