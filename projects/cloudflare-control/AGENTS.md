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
