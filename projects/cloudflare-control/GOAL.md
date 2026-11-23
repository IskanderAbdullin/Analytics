# GOAL

G-001: действующий, проверяемый канал ChatGPT -> публичный GitHub Actions
Analytics -> Cloudflare API без BabitVpsAgent, без дополнительных инструментов
Computer Use/PC Agent и без публикации секретов.

Первый критерий: реальный Actions runner в публичном Analytics,
подключение к Cloudflare API по отдельным GitHub Secrets,
GET текущих настроек и развёртываний двух воркеров, безопасный отчёт.

Позднее: согласованное обновление / rollback воркеров с защищённой
политикой изменений и явными approvals. Текущий релиз read-only.
