# Узгоджена публікація GSI

F10, перший slice у 0.53.15. Попередні присвоєння raw → normalized → timestamp дозволяли sync HTTP читачеві отримати raw Luna поруч зі старим normalized Juggernaut. Тепер `gsi_snapshot.GSIRegister` замінює один приватний snapshot лише тоді, коли побудовано raw, normalized, timestamp і previous delta context.

## Ownership і API

Frozen dataclass `GSISnapshot` immutable by convention: published dictionaries приватні, після commit ніхто їх не змінює. Incoming payload, результат update і capture відокремлено deepcopy. Caller/HTTP consumer не може змінити спільний state чи вкладені raw поля.

Окремий writer RLock серіалізує builders і reset, зокрема залежність normalization від previous context. Нормалізатор і optional enrichment працюють із приватним state; previous context фіксується **до** MatchMemory enrichment, зберігаючи попередню семантику deltas. Live callback додає MatchMemory/scheduler annotations до commit, тому `/state/current` зберігає farm/death/session signals. Failed construction не замінює попереднього повного snapshot; side effects callback не відкочуються транзакційно.

Короткий publication Lock захищає лише заміну/захоплення посилання. Reader не чекає на нормалізацію, enrichment чи deepcopy пакета, що будується: бачить цілий попередній або наступний snapshot. Lazy hero profile file cache прогрівається до writer ownership. Callback contract — лише робота в пам'яті. Debug files, census, recordings і запис PlayerService history виконуються поза обома locks. Виявлений role-prior SQLite lookup винесено перед writer owner у 0.53.19 — [GSI_ROLE_PREPARATION.md](GSI_ROLE_PREPARATION.md).

`/gsi/debug/latest` збирає raw/state/timestamp/field summary з одного capture. `/gsi/status` також використовує один capture для hero, timestamp, field coverage й in_match. Форма `/state/current` зберігається. Tests/evaluation runners викликають `reset_latest_gsi()` замість послідовного присвоєння private globals.

`/session/reset` серіалізується з GSI builder і очищує packet/delta context разом із live-memory/scheduler/coach reset. Після відповіді стан `waiting_for_gsi` до наступного Dota packet; це запобігає показу попереднього state після ручного reset. Історія матчів, акаунти, notes і provider налаштування не зачіпаються.

## Перевірки

`test_gsi_snapshot.py` використовує real normalization і HTTP, threads + Events/Barrier. Стандартний thread trace зупиняє **справжню** функцію на її вході, не замінюючи policy/normalizer. Читач і далі відповідає попереднім узгодженим пакетом, потім отримує наступний. Перевіряються:

- caller/reader alias isolation, зокрема nested dictionaries;
- failed enrichment без часткової публікації;
- два concurrent builders з послідовним previous context;
- reset і concurrent async `/gsi`/sync `/session/reset`;
- writer progress під час зупинки на реальній debug-file межі й два записи на filesystem.

Live/GSI/replay/role/death consumers проходять повний backend suite. Новий module проходить strict mypy й оголошений clean; одну стару duplicate-annotation error виправлено, baseline скорочено з 226 до 225 без нових allowances. Cold timer settings додатково прогріваються до обох owners у 0.53.20 — [GSI_TIMER_PREPARATION.md](GSI_TIMER_PREPARATION.md). Source/Windows smoke підтверджує app/backend lifecycle.

## Наступна межа F10

Це **publication slice**, а не глобальна transaction усіх runtime-об'єктів. У 0.53.18 core observation/read/reset MatchMemory, зокрема demo, отримали окреме спільне ownership — [MATCH_MEMORY_OWNERSHIP.md](MATCH_MEMORY_OWNERSHIP.md). Прямі tip/tracker mutations і цілий overlay response потребують наступної межі. Одна overlay response може брати кілька captures для різних helper calls; це не обіцянка єдиного epoch для всієї UI-відповіді. Callback failure зберігає packet register, але не відкочує вже зроблених memory/scheduler mutations. History/recording side paths зберігають власні строки/помилки й не включені в packet transaction. Завершення F10 потребує окремого snapshot/facade для цих consumers без утримання state lock на I/O.
