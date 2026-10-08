# Согласованная публикация GSI

F10, первый slice в 0.53.15. Прежние присваивания raw → normalized → timestamp позволяли sync HTTP читателю получить raw Luna рядом со старым normalized Juggernaut. Теперь `gsi_snapshot.GSIRegister` заменяет один приватный snapshot, только когда построены raw, normalized, timestamp и previous delta context.

## Ownership и API

Frozen dataclass `GSISnapshot` immutable by convention: published dictionaries приватны, после commit никто их не меняет. Incoming payload, результат update и capture отделены deepcopy. Caller/HTTP consumer не может изменить общий state или вложенные raw поля.

Отдельный writer RLock сериализует builders и reset, включая зависимость normalization от previous context. Нормализатор и optional enrichment работают с частным state; previous context фиксируется **до** MatchMemory enrichment, сохраняя прежнюю семантику deltas. Live callback добавляет MatchMemory/scheduler annotations до commit, поэтому `/state/current` сохраняет farm/death/session signals. Failed construction не заменяет прежний полный snapshot; side effects callback не откатываются транзакционно.

Короткий publication Lock защищает только замену/захват ссылки. Reader не ждёт нормализацию, enrichment или deepcopy строящегося пакета: видит целый предыдущий либо следующий snapshot. Lazy hero profile file cache прогревается до writer ownership. Callback contract — только работа в памяти. Debug files, census, recordings и запись PlayerService history выполняются вне обоих locks. При проверке следующего slice обнаружен remaining role-prior lookup в live callback: он может читать SQLite под writer owner и требует отдельного исправления.

`/gsi/debug/latest` собирает raw/state/timestamp/field summary из одного capture. `/gsi/status` также использует один capture для hero, timestamp, field coverage и in_match. Форма `/state/current` сохраняется. Tests/evaluation runners вызывают `reset_latest_gsi()` вместо последовательного присваивания private globals.

`/session/reset` сериализуется с GSI builder и очищает packet/delta context вместе с live-memory/scheduler/coach reset. После ответа состояние `waiting_for_gsi` до следующего Dota packet; это предотвращает показ прежнего state после ручного reset. История матчей, аккаунты, notes и provider настройки не затрагиваются.

## Проверки

`test_gsi_snapshot.py` использует real normalization и HTTP, threads + Events/Barrier. Стандартный thread trace останавливает **настоящую** функцию на её входе, не заменяя policy/normalizer. Читатель продолжает отвечать предыдущим согласованным пакетом, затем получает следующий. Проверяются:

- caller/reader alias isolation, включая nested dictionaries;
- failed enrichment без частичной публикации;
- два concurrent builders с последовательным previous context;
- reset и concurrent async `/gsi`/sync `/session/reset`;
- writer progress при остановке на реальной debug-file границе и две записи на filesystem.

Live/GSI/replay/role/death consumers проходят полный backend suite. Новый module проходит strict mypy и объявлен clean; один старый duplicate-annotation error исправлен, baseline сокращён с 226 до 225 без новых allowances. Source/Windows smoke подтверждает app/backend lifecycle.

## Следующая граница F10

Это **publication slice**, не глобальная transaction всех runtime объектов. В 0.53.18 core observation/read/reset MatchMemory, включая demo, получили отдельную общую ownership — [MATCH_MEMORY_OWNERSHIP.md](MATCH_MEMORY_OWNERSHIP.md). Прямые tip/tracker mutations и целый overlay response требуют следующей границы. Один overlay response может брать несколько captures для разных helper calls; это не обещание единого epoch для всего UI ответа. Callback failure сохраняет packet register, но не откатывает уже сделанные memory/scheduler mutations. History/recording side paths сохраняют собственные сроки/ошибки и не включены в packet transaction. Завершение F10 требует отдельного snapshot/facade для этих consumers без удержания state lock на I/O.
