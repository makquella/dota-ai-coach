# Перенос истории: атомарные claims

F11 в 0.53.11 сохраняет существующий формат зашифрованного переноса, TTL 15 минут, максимум 3 скачивания, IP/install rate limits и удаление после импорта. Изменяется только владение строкой в D1 при конкурентных запросах.

## Claim и upload

Раньше claim отдельно читал `tries`, затем выполнял UPDATE/DELETE. Несколько запросов могли прочитать один прежний счётчик и каждый получить ciphertext. Теперь одна SQL-команда выполняет `UPDATE ... SET tries = tries + 1 WHERE id = ? AND tries < limit AND expires_at >= now RETURNING body, tries`. Только запрос, получивший строку из этой команды, возвращает файл. При 12 одновременных запросах ровно 3 получают 200, остальные — 404; rate limiting по-прежнему учитывает любой claim, найденный или нет.

Upload использует `INSERT ... ON CONFLICT(id) DO NOTHING RETURNING id`. Победитель получает 201, конкуренты — прежний 409 `taken`; они не перезаписывают body/owner и не превращают collision в SQLite UNIQUE error/500. Schema не меняется, новые migrations не нужны.

Очистка остаётся отдельной операцией, но удаляет только expired/exhausted строку. Финальный успешный claim удаляет строку с `tries >= limit`; failed claim удаляет только `expires_at < now OR tries >= limit`. Если другой запрос уже убрал старую строку и новый upload повторно занял ID, поздний cleanup не удаляет свежую строку с нулевым tries и действующим TTL. Строка может кратко оставаться с exhausted counter между claim и cleanup, но больше не выдаёт body.

Цифртекст копируется из `RETURNING` до cleanup. Последний успешный claim отдаёт прежний файл, а новые claims повторно занятого ID — уже новый файл. Ошибка доставки ответа по-прежнему расходует попытку: лимит относится к выданным ответам, не к успешно расшифрованным импортам на клиенте. Сервер не получает secret part кода или ключ расшифровки.

## Настоящий local D1

Из `services/api/`:

```bash
npm ci --no-audit --no-fund
npm run test:unit
npm run test:integration
# оба набора:
npm test
```

Integration harness использует официальный Miniflare/workerd, настоящий D1 binding и все текущие SQL migrations; нет cloud credentials и remote DB. Miniflare объявлен direct dev dependency с той же exact версией, которую уже использовал locked Wrangler: дополнительной версии движка в графе нет. Для Miniflare 5 применяется его официальный `convertV4MiniflareOptions`; source modules явно загружаются из `src/`. Каждая проверка создаёт изолированный runtime и закрывает его после теста.

Проверяются concurrent claims, concurrent insert collisions с неизменённым owner/body, device deletion с правильным install ID, TTL и две настоящие задержки cleanup. Для последних handler вызывает реальный D1 через adapter, который только задерживает исполнение DELETE; все SQL statements исполняются движком без замены результата или шаблона SQL. Свежий upload проходит через HTTP настоящего Worker до возобновления старого cleanup.

Текущие migration files состоят из обычных DDL statements; harness выполняет каждую после удаления SQL line comments. При добавлении triggers или string literals с semicolons loader нужно расширить. Это минимальный integration harness для transfer, а не доказательство всех SQL paths Worker. Быстрые unit tests остальных routes сохраняются.

API workflow запускает оба набора через `npm test`, затем обычный Worker dry-run bundle и local migrations. Изменение готовится PR; remote deploy не запускался. Поведение AES-GCM/scrypt на launcher и формат локального backup не меняются.
