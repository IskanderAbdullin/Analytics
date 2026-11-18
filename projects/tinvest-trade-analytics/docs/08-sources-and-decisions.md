# 08. Источники, открытые реализации, ADR и вопросы

**Дата проверки публичных страниц:** 18.11.2026. Ссылки — точки входа для разработчика; точная форма protobuf DTO и доступность SDK должна заново фиксироваться на момент implementation. Не копировать исходники без проверки лицензии.

## 1. Официальная документация T-Invest (источники требований P0)

| Документ | Что в нём нужно проверить | Ссылка |
|---|---|---|
| API intro / auth / endpoints | prod vs sandbox, официальный API scope | https://developer.tbank.ru/invest/intro/intro |
| OperationsService | методы GetPortfolio/GetPositions/GetBrokerReport/GetOperationsByCursor и stream | https://developer.tbank.ru/invest/services/operations/methods |
| Operations by cursor | pagination, max `limit=1000`, фильтры, `withoutCommissions`, `withoutTrades`, `state`, timestamps UTC | https://developer.tbank.ru/invest/api/operations-service-get-operations-by-cursor |
| Operations service head | рекомендации cursor vs deprecated `GetOperations`, задержки | https://developer.tbank.ru/invest/services/operations/head-operations |
| Особенности истории | operation IDs меняются, trade IDs иногда расходятся, cursor `limit>2` | https://developer.tbank.ru/invest/services/operations/operations_problems |
| Operations FAQ | quantity штуки, нет прямой надёжной связи с order ID, VM daily clearing, broker report | https://developer.tbank.ru/invest/services/operations/faq_operations |
| Operation stream | только часть неторговых событий, повторные комиссии, вариационная маржа per-instrument + aggregate | https://developer.tbank.ru/invest/services/operations/operations_stream |
| Broker report | async task_id, generate/poll/pages | https://developer.tbank.ru/invest/api/operations-service-get-broker-report |
| Instruments FAQ | min_price_increment_amount futures | https://developer.tbank.ru/invest/services/instruments/faq_instruments |
| Market data service | свечи, рынок, фьючерсные котировки, depth/time concerns | https://developer.tbank.ru/invest/services/quotes/head-marketdata |
| Rate limits | dynamic user quotas across accounts/tokens, service budgets; 200 ops/min etc as-of | https://developer.tbank.ru/invest/intro/intro/limits |
| Sandbox | возможности/ограничения операций и отчётов | https://developer.tbank.ru/invest/intro/developer/sandbox |
| Official Swagger | конечные protobuf/REST shapes | https://russianinvestments.github.io/investAPI/swagger-ui/ |

**Подтверждённые ограничения, которые нельзя игнорировать:**
- Старый `GetOperations` ограничен последней 1000 операций; `GetOperationsByCursor` предназначен для пагинации и расширенной фильтрации.
- Operation IDs могут меняться; в ряде случаев trade ID отличается от IDs в сервисе заявок.
- В `OperationsStream` торговые исполнения не представляют полный источник истории, некоторые неторговые комиссии могут дублироваться, VM может иметь агрегатное и инструментальное представления.
- Broker report генерируется асинхронно; reconciliation нельзя свести к получению одной страницы.
- Quantity в OperationsService указан в штуках, нельзя ошибочно масштабировать его размером лота.
- Лимиты T-Invest действуют для пользователя по счетам/токенам; бюджет ingestion не должен мешать живым роботам.
- Сервер может менять контракт и правила; избегать hardcode перечислений и сроков хранения.
- Бесплатность личного доступа к API не означает права коммерческой ретрансляции биржевых данных.

## 2. Открытые SDK и примеры

**Официальные и полезные базы (проверять поддержку и актуальность):**
- https://github.com/Tinkoff/invest-api-csharp-sdk — исходный C# SDK / legacy entrypoint.
- https://github.com/Invest-SDK/invest-csharp — современная ветка C# SDK, проверить официальные ссылки на портале и релизы.
- https://github.com/Tinkoff/invest-python — исторически распространённая Python SDK.
- https://github.com/Invest-SDK/invest-python — альтернативная/развиваемая ветка Python SDK.
- https://russianinvestments.github.io/invest-python/examples/ — демонстрации курсорных операций.
- https://github.com/ya-erm/TTExtension — полезны UI и P&L concepts; осторожно с лицензией.
- https://github.com/softandiron/tinkproject — исторические табличные отчёты, деньги, XIRR; legacy API.
- https://github.com/Relff/t-invest-portfolio-tracker — Excel/Google Sheets аналitika, FIFO/XIRR (требует code audit).
- https://github.com/Plekkkh/OpenInvest.Monitor — разделение интеграций/доходности (требует code audit).
- https://github.com/pvlKryu/Tinkoff_Invest_Analitics — компактный исходный пример.
- https://github.com/nyxandro/t-invest-skill — агентский CLI / аналитические возможности, требует security review.
- https://github.com/earlisreal/eJournal — идеи lot matching, position episodes, short, partial closes.
- https://github.com/Gonzalez8/fintrack — идеи FIFO/LIFO/average accounting.
- https://github.com/Sid-OP-collab/portfolio-analytics — идеи TWR, XIRR, equity.
- https://github.com/krbob/portfolio — идеи журналирования транзакций.
- https://investstats.ru/api — сторонний сервис-аналог по методам P&L, вариационной марже и API, исходники не открыты.

**Статус:** перечень кандидатов для изучения и независимой проверки, а НЕ заявление, что их расчётный код корректен, имеет право на копирование или поддерживает все современные российские деривативы. При реализации составить таблицу `repo, commit, licence, language, algorithms, tests, known bugs, API version, suitability, copied_code? true/false`.

## 3. Методологические источники для research

- Joel Hasbrouck, *Empirical Market Microstructure* — оценка ликвидности, информационного воздействия.
- Robert Almgren / Neil Chriss — алгоритмическое исполнение и market impact, требует осторожности с пассивными и pro-rata стратегиями.
- David H. Bailey / Marcos López de Prado, *The Deflated Sharpe Ratio* — проблема множественного перебора стратегий.
- Halbert White, *A Reality Check for Data Snooping*; Peter R. Hansen, *A Test for Superior Predictive Ability* — корректность сравнений после многочисленных экспериментов.
- Survival analysis — time-to-fill при цензурированных заявках; chronological/block bootstrap для сделок с внутридневной зависимостью.

Для внедрения исследований отдельно подтвердить DOI/издание/лицензию и записать версию данных. Не цитировать нечитанную работу как валидацию собственного метода.

## 4. Открытые ADR / required decisions

| ADR | Вопрос | Предлагаемое решение | Проверка |
|---|---|---|---|
| A001 | SDK | актуальный официальный C# gRPC client / direct proto fallback | release, support, tests |
| A002 | Financial P&L policy | separate realized / unrealized / VM / fees / FX and ledger | independent broker report |
| A003 | Database | SQLite operational + Parquet research, immutable raw | volume, retention, replay |
| A004 | Raw identity | revision links, never external ID as only PK | altered-ID fixtures |
| A005 | UI | WPF or Avalonia after spike | windows maintenance, charting |
| A006 | Strategy attribution | exact/inferred/manual/unknown labels | overlapping bots fixtures |
| A007 | Futures valuation | settlement-aware with per-date instrument spec | actual VM corpus |
| A008 | Day boundary | UTC, Moscow, trade date, clearing day all selectable | boundary golden |
| A009 | Time-series market data | explicit coverage and high-frequency gaps | data licensing and sources |
| A010 | MCP/AI | local read-only query surface, no secrets in prompts | scope security test |
| A011 | Risk basis | NAV vs gross exposure vs margin guarantee separated | financial definitions |
| A012 | Other brokers | capability-based adapters, partial supported statuses | contract tests |

## 5. «Неизвестные» для документированного исследования

1. Какова фактическая максимальная историческая полнота trade IDs, order states и fill details для разных типов счёта?
2. Что именно T-Invest возвращает для вечных фьючерсов как `OPERATION_TYPE_FUNDING`, как это сочетается с VM?
3. Какие реальные API события иногда задублированы между broker fee embedded и cash fee?
4. Достаточно ли доступных исторических справочников для корректной денежной стоимости шага на каждую дату фьючерса?
5. Какие правила бухгалтерского времени для VM после перехода на единую торговую сессию?
6. Где есть исторический L2 в требуемой глубине и частоте, сколько пробелов и каковы licence/retention limits?
7. Можно ли реконструировать execution quote с достаточной временной точностью (синхронизация часов и network latency)?
8. Что сохраняет OsEngine о конкретной сделке и исходной заявке после рестарта, а что нужно отдельно логировать?
9. Какой метод разделения совместной позиции нескольких ботов наиболее полезен пользователю: virtual portfolio vs fill-origin attribution vs cost allocation?
10. Какие поля отчёта брокера корректнее отражают cash vs P&L vs tax basis?
11. Какие данные брокеров доступны кроме T-Invest (Alfa PRO API, Finam) без trading permissions?
12. Какова статистическая мощность/coverage данных для fill-probability models, прежде чем запускать ML?

Каждый ответ фиксировать в формате:
`question_id, date, source_url, observed_sample_scope, result, confidence, limitation, follow_up_test, ADR_reference`.

## 6. Scope и запреты в репозитории

- Никаких токенов, cookie, raw portfolio statements, настоящих номеров счетов, client secrets и personal trade data.
- Нельзя копировать GPL/AGPL/закрытые исходники в приватный проект без юридической проверки совместимости условий.
- Не автоматизировать торговлю из `TInvestAnalytics`, даже если SDK допускает write endpoints.
- Не делать публичный сервис по ретрансляции T-Invest данных без отдельной правовой оценки.
- Использовать синтетические/обезличенные фикстуры, но не считать их доказательством live correctness.
- Не распространять историю брокерских операций пользователя в API без его осознанного подключения/разрешений.

## 7. Журнал изменений

- 2026-11-18 v1.0: продуктовые требования, архитектура, импорт, P&L, роботы, риск, ML, roadmap и источники; реализация не начата.


## 8. Подробная ревизия исходников и peer-reviewed литературы (v1.1)

В этом файле ранее содержался общий каталог. Теперь конкретные пути функций, прочитанные реализации и инженерные примеры вынесены в [09-open-source-implementation-audit.md](09-open-source-implementation-audit.md). Научные статьи с DOI/arXiv, статусом peer-reviewed/preprint, гипотезами, данными и проверяемыми экспериментами находятся в [10-academic-research-and-experiments.md](10-academic-research-and-experiments.md).

**Лицензирование:** наличие открытого GitHub репозитория не означает разрешения копировать код; читать LICENSE/NOTICE и зависимости на выбранном commit. **Проверка:** в 09 документе отмечено, какие файлы реально просмотрены ([CODE]/[TEST]), а какие изучены по документации ([DOC]).

**Методология:** для P&L/клиринга приоритетные независимые источники — операции, брокерский отчёт и актуальная официальная спецификация; исследования OFI/fill probability не определяют денежные проводки.
