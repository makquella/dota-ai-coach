# Локальний API: доступ і налагодження

У 0.53.7 локальні запити проходять перевірку до виклику обробників FastAPI. Сервіс приймає HTTP лише від loopback-клієнта з `Host` поточного порту: `127.0.0.1`, `localhost` або `[::1]`. Launcher використовує `127.0.0.1` і запускає один backend. Packaged entrypoint вимикає довіру до proxy headers і відкидає зовнішню bind address.

## Два різні права доступу

- **Control**: `Authorization: Bearer <control token>` для налаштувань, історії, діагностики, demo та решти приватних endpoints, зокрема читання. Launcher створює випадковий 256-бітний токен на запуск застосунку й передає його дочірньому backend через environment. Токен залишається в main process; renderer отримує лише DTO через IPC. Повторний запуск backend усередині того самого launcher використовує той самий токен.
- **GSI**: Dota надсилає `{"auth":{"token":"<gsi token>"}, ...}` у `POST /gsi`. Цей інший 256-бітний токен не відкриває історії й не змінює налаштувань. Launcher зберігає його в `local-api-gsi.json` у user data, щоб уже завантажений Dota config і далі працював після перезапуску тренера. Config містить лише GSI-токен. Довірений control-клієнт також може надсилати GSI для відтворення й діагностики.

Health (`/`, `/health`), Swagger/ReDoc, OpenAPI і статичні developer pages доступні без токена; приватні відповіді й будь-які зміни потребують відповідного права. Query parameters і cookies не замінюють токенів. Тіло `auth` видаляється до нормалізації GSI, census, diagnostics, запису сесії та match recovery. Bearer credentials і 64-значні hex secrets редагуються в problem reports; файли з токенами виключено з Git.

Будь-який переданий `Origin` має точно збігатися з локальною адресою й портом backend. Чужий сайт, `Origin: null` та інший localhost-порт отримують відмову навіть із правильним токеном. Відсутність Origin допустима для Dota й локальних інструментів, але не скасовує автентифікації. CORS допускає лише ці самі локальні origins; сам собою CORS не забезпечує захисту записів.

## Оновлення Dota config

Під час запуску launcher синхронізує знайдений `gamestate_integration_dota_ai_coach.cfg`: вибраний порт і блок Valve `auth.token`. Після першого переходу на 0.53.7 **перезапустіть Dota один раз**, щоб гра прочитала новий config. Якщо config встановлюється в теку вручну, використовуйте звичайну кнопку встановлення в launcher. Ігрові блоки даних і heartbeat зберігаються.

POSIX-файли credentials/config створюються з mode `0600`. У Windows діє доступ до user data й теки гри через наявні ACL; chmod не встановлює окремого Windows ACL. Backend, що запускається без launcher, використовує окремий приватний `backend/local-api-auth.json` (або `WRITABLE_DIR` у збірці), з control і GSI токенами. Хибний/неповний файл або лише одна з двох environment variables зупиняють запуск; автоматичної заміни на незахищений режим немає.

## Manual debug

Для standalone backend з `backend/`:

```bash
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

За іншого порту задайте `DOTA_AI_BACKEND_PORT` з тим самим значенням, що й `--port`. Не запускайте другого backend разом із launcher. Якщо задано `DOTA_AI_CONTROL_TOKEN` / `DOTA_AI_GSI_TOKEN`, обидва мають бути різними випадковими рядками з 64 lowercase hex символів; зберігайте їх в environment, а не в аргументах запуску чи спільних логах.

Відкрийте `/docs`, натисніть **Authorize** і вставте control-токен зі свого приватного standalone файлу. Swagger додає Bearer header до приватних запитів. На налагоджувальних сторінках для розробника `/debug/` і `/debug/overlay.html` (лише з вихідного коду, не у встановленому застосунку; без токена відкриваються лише вони самі, решта `frontend/` не віддається) є password-поле для того самого токена; значення не зберігається в localStorage. У звичайному desktop-інтерфейсі введення не потрібне.

Replay helper автоматично читає standalone credentials або використовує environment, отриманий від launcher. Кнопки demo передають обидві variables і вибраний порт у дочірній процес. Helper не пересилає токена через HTTP redirects. Для site screenshots Node-частина використовує той самий control-токен з environment чи standalone файлу; браузер отримує лише результати запитів.

## Розміри й помилки

До обробників перевіряється оголошений і реально прочитаний розмір, зокрема chunked HTTP без `Content-Length`:

| Запит | Максимум |
|---|---|
| `POST /gsi` | 4 MiB |
| `POST /player/backup` | 512 MiB, як у launcher |
| Решта тіл | 1 MiB |

Непорожні змінні запити потребують `application/json`; compressed bodies не приймаються. Коди: `401 unauthorized`, `403 untrusted_origin/nonlocal_client`, `400 invalid_host/invalid_length/invalid_json/invalid_gsi`, `413 body_too_large`, `415 json_required/unsupported_encoding`. Відповідь і diagnostics містять код причини без надісланих токенів чи тіла. Для GSI JSON також заборонено non-finite numbers і некоректні Unicode sequences. Конкурентні standalone процеси публікують повністю записаний credentials-файл атомарно й використовують одного переможця.

Це межа локального HTTP. Програми з доступом до файлів/environment того самого OS-користувача можуть отримати його credentials. Захист IPC sender, navigation і CSP підготовлено окремим F17 у 0.53.8 — [DESKTOP_SECURITY.md](DESKTOP_SECURITY.md); control-токен не призначений для виправлення XSS усередині довіреного renderer. Перевірки охоплюють реальний TCP backend, збережені сесії, паралельне створення credentials і launcher/Windows smoke з позитивними й негативними запитами. Жива Dota в CI не запускається; Valve payload перевіряється за токеном зі справжнього генератора config.
