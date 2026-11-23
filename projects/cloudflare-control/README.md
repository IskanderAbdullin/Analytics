# Cloudflare API Control (GitHub Actions)

Отдельный мини-проект в публичном IskanderAbdullin/Analytics для доступа
ChatGPT к официальному Cloudflare API через GitHub Actions, даже когда
BabitVpsAgent на Ubuntu теряет WebSocket.

Схема:
  ChatGPT -> GitHub connector -> commit request.json -> GitHub Actions
  -> Cloudflare API (фиксированные GET) -> очищенный результат CI/status.

## Настройка Secrets

Два существующих GitHub Secrets из другого репозитория НЕ наследуются.
Их нужно добавить отдельно в Analytics / Settings / Secrets and variables /
Actions / Repository secrets:

1. CLOUDFLARE_API_TOKEN — желательно отдельный токен Cloudflare только на
   чтение Workers (минимум Workers Scripts Read для этого account).
2. CLOUDFLARE_ACCOUNT_ID — идентификатор аккаунта из Cloudflare, тоже
   храним как Secret, а не в исходниках.

Ни одного значения токена, учётных данных, VPS-паролей или брокерских
ключей в этот публичный репозиторий добавлять нельзя.

## Запуск и получение результата

Файл .github/workflows/cloudflare-api-bridge.yml срабатывает на
push в main или chatgpt/cloudflare-control-20261123 при изменении
этого проекта (и на ручной workflow_dispatch после размещения на main).

Для очередного запуска ChatGPT через GitHub обновляет
projects/cloudflare-control/request.json, увеличивая целое поле nonce.
Поле operation может быть только "inventory". Никакие shell-команды,
URL или JSON-аргументы Cloudflare через этот файл передать нельзя.

Отчёт виден в журнале Actions и безопасном commit status с контекстом
cloudflare-readonly-audit. Код публикует только имя одного из двух
заранее фиксированных Worker, наличие одного заранее известного binding
и факт наличия деплоймента. Он не выводит полный ответ Cloudflare.

Локально: cd projects/cloudflare-control && python3 -m unittest discover
-p 'test_*.py' -v

Если нет Secrets в Analytics, появится secrets_unavailable. Рабочий
GitHub workflow не означает автоматически доступности Cloudflare API.

## Ограничения

- Только GET settings/deployments для babit-vps-bridge и t-invest-mcp-proxy.
- Нет кода или прав на deploy, delete, reboot, shell и торговые операции.
- Логи GitHub публичны. Никаких raw API ответов (Cloudflare может вернуть
  секретные значения в settings).
- Независимость от BabitVpsAgent касается доступа к API Cloudflare,
  а не исполнения команд внутри Ubuntu.
- Для API Serverspace через babit-vps-bridge требуется отдельное
  развёртывание PR #18 в приватном MCP-proxi; этот workflow — лишь
  независимый контроллер Cloudflare и начальный диагностический канал.
