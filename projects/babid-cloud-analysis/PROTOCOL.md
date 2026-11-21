# PROTOCOL — сохранение и точное возобновление исследования

1. Прочитать GOAL.md, STATE.json, NEXT_ACTION.json, EVIDENCE.md, BACKLOG.md.
2. Запустить: python analysis/research_state.py validate
3. Получить точку продолжения: python analysis/research_state.py next
4. Выполнить наиболее значимую разрешённую задачу, проверяя качество
   и происхождение исходных данных. Не угадывать пропущенные файлы.
5. Перед КАЖДЫМ коммитом обновить EVIDENCE.md и гипотезы, STATE.json,
   BACKLOG.md и NEXT_ACTION.json; зафиксировать следующий конкретный шаг.
6. Закоммитить всё вместе, push без force, проверить CI и сразу
   перейти к следующей доступной задаче, а не остановиться на PR.
7. При блокере записать blocked_external с конкретным отсутствующим
   вводом/разрешением и командой для разрешённого возобновления.

Инварианты: STATE.current_action_id = NEXT_ACTION.action_id.
Evidence refs должны существовать. Подтверждённые гипотезы требуют
реальных доказательств. При unresolved нельзя установить completed.
Blocked action требует blockers и next_command.

Плановое GitHub Actions проверяет эти инварианты и печатает следующую
задачу, но НЕ является агентом ChatGPT Work и не подключается к
локальным файлам или брокеру.
