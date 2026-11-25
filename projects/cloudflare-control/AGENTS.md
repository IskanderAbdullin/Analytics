# Cloudflare Control instructions

- Никогда не выводить или копировать в публичные файлы Cloudflare
  account ID, токены, произвольные variable/secret values, raw API JSON,
  сетевые идентификаторы серверов и брокерские данные.
- Разрешены только фиксированные GET: settings и deployments для двух
  закреплённых Worker; в D177 для диагностики согласованного владельцем резервного
  Cloudflare Tunnel дополнительно один фиксированный GET списка с фильтром
  имени уже существующего PC tunnel. Вывод только status/boolean или HTTP code,
  без token endpoint, IDs, IP, raw JSON и без изменений ресурсов.
  Никакие произвольные URL или команды через inputs.
- Никаких Cloudflare deployment / mutation / VPS / PC Agent / реальных
  торговых операций в рамках первого read-only этапа.
- Не менять остальные проекты Analytics и приватный MCP-proxi.
- Стандарт журнала OsEngine Lab v2 из корневого AGENTS, commit+push без force.
- Перед каждым действием сверять HEAD и checkpoint.

- D179: владелец отдельно разрешил одноразовый временный Worker только для проверки TCP 22 своего хоста. Адрес только из закрытого Actions Secret PC_SSH_PROBE_HOST; порт фиксирован, без SSH-аутентификации, команд или проксирования. Отдельный случайный Worker, одноразовый авторизованный вызов с коротким сроком, удаление в finally; не менять существующие Worker. Без закрытого адреса не создавать ресурсы. Это исключение не расширяет обычный read-only bridge.

- D180: одноразовый TCP 22 probe разрешён также через штатную Cloudflare Queue + временный KV для результата, без публичного HTTP и изменения Access. Одна фиксированная команда проверки доступности (не SSH-команда), случайные отдельные ресурсы, короткое истечение, cleanup; никаких пользовательских команд, проксирования или чужих ресурсов.

- D181: read-only readiness audit of existing exact named PC tunnel: GET filtered list, then GET connections/configurations for the uniquely matched UUID; output status, config source and booleans only. No token endpoint, no route/config changes, no raw values.

- D181 follow-up: fixed read-only GET connectivity/directory/services filtered to HTTP, summarize only exact existing pc-agent-loopback service using booleans. No service modification, raw identifiers or values.

- D183: fixed one-message diagnostic via existing exact HTTP VPC service only. Unsigned POST /v1/status (expected 401 if origin is live), record HTTP status only; no authentication bypass, commands, body retention, new network route, public endpoint or shared Worker changes. Temporary Worker/Queue/KV cleanup as in D180.

- D184: one fixed TCP22 connectivity probe via a temporary VPC Network binding to the unique existing named pc-agent-private tunnel only, NOT Mesh or default network. Target literal 127.0.0.1:22, no SSH bytes written/read, no credentials, no general execution or proxy, no public endpoint, no changes to tunnel routes or other services. One queue event and cleanup as D180. This is not an SSH client or new persistent access mechanism.

- D185: fixed read-only Log Explorer SQL query (POST query endpoint, no mutation). Only aggregated close reasons for D183/D184 temporary Worker name prefixes and exact historical time window. No raw log records, IDs, source/destination addresses, token, dataset creation or paid enablement. No new connection tests.

- D186: owner supplied fresh evidence of established QUIC and local TCP22 listener; one repeat of D184 fixed connectivity diagnostic authorized under same scope. Separate sanitized categories for API shape, timeout, proxy error; no raw exception text, SSH data, credentials, new routes or other targets. No HTTP origin repeat (8765 absent).

- D189: public CI synthetic SSH compatibility fixture only: ephemeral loopback server, generated disposable fixture keys, pinned ssh2 library, no real host address, actual credentials, Cloudflare deployment, commands, forwarding or secrets. Test host-key rejection and public-key authentication through standard Node/Web streams.

- D190: local Miniflare/workerd compatibility fixture, Wrangler dry-run bundling only. No actual cloud deployment, secrets, live tunnel/SSH, remote host, commands or production bindings. Generated in-memory fixture key only.
