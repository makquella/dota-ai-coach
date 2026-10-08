# Проверка счётчиков в AI-разборе

F04, первый slice в 0.53.13. Раньше число могло быть разрешено из любого поля JSON: 160 last hits разрешали «160 kills», а числа 0–12 всегда проходили проверку. Теперь количественные утверждения о kills/deaths/assists игрока привязаны к собственным итоговым счётчикам в `analysis.headline`.

## Данные и граница

`coach_evidence.py` строит `CounterEvidence` для трёх неотрицательных integer totals. Bool, отсутствующий/невалидный счётчик не превращаются в ноль. Compact match facts содержат `match_totals` и refs `{source: analysis.headline, field, observed_at: null, precision: reported_total, value}`. Источник указывает на детерминированный разбор, а не приписывает отдельному upstream поставщику точность, которую merged analysis не хранит. Время фактического наблюдения в headline неизвестно: `observed_at` остаётся null, не выдаётся за timestamp конца матча.

`FactChecker` проверяет RU/EN числовые noun phrases «200 убийств», «kills: 200», «смерти: их было 2» и K/D/A triples по конкретным полям. Значения nested scoreboard, lane, findings, last hits или других метрик не разрешают total игрока. Неверное предложение удаляется; пустой/слишком повреждённый ответ получает обычный один retry, затем `unverified`. Модель не выбирает значение evidence: metadata формирует backend после проверки.

Эти refs подтверждают reported match totals. Числовые combat assertions с другим named hero, time/minute/lane/rate scope отклоняются консервативно: итоговый счётчик не доказывает такое утверждение. Это может убрать корректную формулировку, пока не появится ledger с отдельными subject/time slices. Prompt описывает эту границу.

`next_game`, `plan` и block `fix` остаются goal slots: будущая цель «не больше 2 смертей» не должна совпадать с прошлым total. Там сохраняется прежняя общая проверка numbers/times/names. В свободных match Q&A quantified combat statements проходят строгую проверку; numerical future targets следует оставлять в goal slots, Q&A может дать качественный совет.

## Cache и UI

`COACH_VERSION` повышен с 1 до 2. Новые cache entries записывают verification version. Legacy match review не показывается при pending, error, waiting или AI off; stored copy сохраняется до обычной регенерации. Современный stale review сохраняет прежнее поведение при приходе новых данных и отмечается stale. Career verification policy не изменена.

Сохранённые match questions проходят sentence-by-sentence проверку при чтении без provider call: ответ с неверным предложением возвращается с очищенным текстом, полностью непроверяемый ответ не показывается. Исходный cache при чтении не удаляется. Новые ответы сохраняют refs; возвращаемый view получает refs текущего разбора. При следующем ask новая история собирается из проверенного view.

В match review и answers раскрываемый элемент «Данные для проверки K/D/A» показывает totals и границу их точности на RU/EN. Он использует DOM/textContent, поддерживает legacy отсутствие metadata и отвергает malformed rows. Public share payload остаётся прежним field-by-field: refs, вопросы и source internals не публикуются.

## Проверки и следующий slice

`test_coach_evidence.py`: metric swap при разрешённом числе, small-count bypass, comma punctuation, RU/EN, K/D/A reorder, unknown vs zero, unsupported subjects/scopes, real HTTP/SQLite generation/retry/history, legacy cache upgrade/offline view. Scripted provider является внешним fixture; внутренний checker/service/storage работают реально. Новый evidence module проходит strict mypy и объявлен clean в blocking baseline; старые 226 errors не расширены.

Electron smoke создаёт настоящий disclosure DOM из bundled renderer script, открывает его на RU/EN и проверяет zero, malformed values/source и legacy отсутствие refs. Общая source/Windows smoke проверяет приложение, preload и IPC.

## GPM/XPM в 0.53.26

`MatchRateBindings` отдельно проверяет match-wide GPM и XPM игрока.
`match_rates` и `match_rates_evidence` формируются только из `analysis.headline`;
пустой ledger сохраняется в compact facts. Rate evidence имеет тот же source,
свой field, `observed_at: null`, `precision: reported_match_rate` и исходное
число. Поддерживаются finite nonnegative integer/float до JS safe-integer
границы; bool, строки и отсутствующие значения остаются unknown. Ноль остаётся
измерением. Quantified noun phrases GPM/XPM, gold/experience per minute и
«золота/опыта в минуту» должны точно совпадать со своим полем, включая дробную
часть. Округлённая, другая или nested метрика не подтверждает такое утверждение.

Названия единиц «per minute» / «в минуту» не считаются временным отрезком.
Другие time/lane/team/hero scopes требуют отдельного evidence и отклоняются.
Future goal slots сохраняют прежнюю общую проверку. Модель не формирует refs:
после deterministic проверки backend добавляет `rate_evidence` к review/answer;
UI disclosure показывает только validated rows на RU/EN, включая zero и decimal.
Combat-only legacy disclosure сохраняет прежний текст.

`COACH_VERSION` теперь 3. Match review с verification version 2 скрывается до
обычной регенерации, включая offline/AI-off view; исходный cache сохраняется.
Policy version участвует в общем digest и может вызвать обычное обновление
career cache, но career field binding здесь не добавлен. Saved Q&A при чтении
перепроверяется sentence-by-sentence без provider call и без удаления хранения;
returned refs соответствуют текущему разбору. Share payload по-прежнему не
публикует вопросы или внутренний evidence.

Новые functional checks используют настоящий HTTP, SQLite, generation/retry и
cache upgrade с внешним scripted provider. Parser checks покрывают metric swap,
small-number bypass, unsupported subject/time scope, RU/EN units и decimal,
unknown/zero/invalid rate. Source/Windows Electron smoke открывает настоящий
disclosure DOM на двух языках, проверяет combined/legacy UI и malformed rates.

Это ограниченный детерминированный parser, не полная семантическая проверка AI. Spelled-out counts, произвольные глагольные/coreference конструкции и противоречия без поддержанной числовой noun phrase здесь не доказываются. Farm/item/findings refs, временные claims, другие метрики и career ещё требуют собственных bindings. F04 остаётся открытым до следующих slices; нет заявления, что каждое AI утверждение теперь доказано.
