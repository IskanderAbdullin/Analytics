# PLAN

1. Отдельный Python (stdlib) API-клиент и автономные тесты, без реальных ключей.
2. Самостоятельный GitHub Actions workflow с push + manual workflow_dispatch.
3. Проверка первого запуска в публичном Analytics без Secrets.
4. Хранение read-only токена Cloudflare и account ID в Actions Secrets Analytics.
5. Проверка настоящих GET settings и deployments; результат редактируется
   строго по белому списку.
6. Отдельное расширение до управляемого deploy только после проверки
   версии живых Worker, сохранения rollback и согласования прав.
