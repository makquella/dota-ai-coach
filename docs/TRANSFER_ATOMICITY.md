# Перенесення історії: атомарні claims

F11 у 0.53.11 зберігає наявний формат зашифрованого перенесення, TTL 15 хвилин, максимум 3 завантаження, IP/install rate limits і видалення після імпорту. Змінюється лише володіння рядком у D1 за конкурентних запитів.

## Claim і upload

Раніше claim окремо читав `tries`, потім виконував UPDATE/DELETE. Кілька запитів могли прочитати один попередній лічильник і кожен отримати ciphertext. Тепер одна SQL-команда виконує `UPDATE ... SET tries = tries + 1 WHERE id = ? AND tries < limit AND expires_at >= now RETURNING body, tries`. Лише запит, що отримав рядок із цієї команди, повертає файл. За 12 одночасних запитів рівно 3 отримують 200, решта — 404; rate limiting, як і раніше, враховує будь-який claim, знайдений чи ні.

Upload використовує `INSERT ... ON CONFLICT(id) DO NOTHING RETURNING id`. Переможець отримує 201, конкуренти — попередній 409 `taken`; вони не перезаписують body/owner і не перетворюють collision на SQLite UNIQUE error/500. Schema не змінюється, нові migrations не потрібні.

Очищення залишається окремою операцією, але видаляє лише expired/exhausted рядок. Фінальний успішний claim видаляє рядок із `tries >= limit`; failed claim видаляє лише `expires_at < now OR tries >= limit`. Якщо інший запит уже прибрав старий рядок і новий upload повторно зайняв ID, пізній cleanup не видаляє свіжого рядка з нульовим tries і чинним TTL. Рядок може коротко залишатися з exhausted counter між claim і cleanup, але більше не видає body.

Шифротекст копіюється з `RETURNING` до cleanup. Останній успішний claim віддає попередній файл, а нові claims повторно зайнятого ID — уже новий файл. Помилка доставки відповіді, як і раніше, витрачає спробу: ліміт стосується виданих відповідей, а не успішно розшифрованих імпортів на клієнті. Сервер не отримує secret part коду чи ключа розшифрування.

## Справжній local D1

З `services/api/`:

```bash
npm ci --no-audit --no-fund
npm run test:unit
npm run test:integration
# обидва набори:
npm test
```

Integration harness використовує офіційний Miniflare/workerd, справжній D1 binding і всі поточні SQL migrations; немає cloud credentials і remote DB. Miniflare оголошено direct dev dependency з тією самою exact версією, яку вже використовував locked Wrangler: додаткової версії рушія в графі немає. Для Miniflare 5 застосовується його офіційний `convertV4MiniflareOptions`; source modules явно завантажуються з `src/`. Кожна перевірка створює ізольований runtime і закриває його після тесту.

Перевіряються concurrent claims, concurrent insert collisions з незміненими owner/body, device deletion з правильним install ID, TTL і дві справжні затримки cleanup. Для останніх handler викликає реальний D1 через adapter, який лише затримує виконання DELETE; усі SQL statements виконуються рушієм без заміни результату чи шаблону SQL. Свіжий upload проходить через HTTP справжнього Worker до відновлення старого cleanup.

Поточні migration files складаються зі звичайних DDL statements; harness виконує кожну після видалення SQL line comments. У разі додавання triggers чи string literals із semicolons loader треба розширити. Це мінімальний integration harness для transfer, а не доказ усіх SQL paths Worker. Швидкі unit tests решти routes зберігаються.

API workflow запускає обидва набори через `npm test`, потім звичайний Worker dry-run bundle і local migrations. Зміна готується PR; remote deploy не запускався. Поведінка AES-GCM/scrypt на launcher і формат локального backup не змінюються.
