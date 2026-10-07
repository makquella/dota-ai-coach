# Локальный API: доступ и отладка

В 0.53.7 локальные запросы проходят проверку до вызова обработчиков FastAPI. Сервис принимает HTTP только от loopback-клиента с `Host` текущего порта: `127.0.0.1`, `localhost` или `[::1]`. Launcher использует `127.0.0.1` и запускает один backend. Packaged entrypoint отключает доверие к proxy headers и отвергает внешний bind address.

## Два разных права доступа

- **Control**: `Authorization: Bearer <control token>` для настроек, истории, диагностики, demo и остальных частных endpoints, включая чтение. Launcher создаёт случайный 256-битный токен на запуск приложения и передаёт его дочернему backend через environment. Токен остаётся в main process; renderer получает только DTO через IPC. Повторный запуск backend внутри того же launcher использует тот же токен.
- **GSI**: Dota отправляет `{"auth":{"token":"<gsi token>"}, ...}` в `POST /gsi`. Этот другой 256-битный токен не открывает историю и не меняет настройки. Launcher сохраняет его в `local-api-gsi.json` в user data, чтобы уже загруженный Dota config продолжал работать после перезапуска тренера. Config содержит только GSI-токен. Доверенный control-клиент также может отправлять GSI для воспроизведения и диагностики.

Health (`/`, `/health`), Swagger/ReDoc, OpenAPI и статические developer pages доступны без токена; частные ответы и любые изменения требуют соответствующего права. Query parameters и cookies не заменяют токены. Тело `auth` удаляется до нормализации GSI, census, diagnostics, записи сессии и match recovery. Bearer credentials и 64-значные hex secrets редактируются в problem reports; файлы с токенами исключены из Git.

Любой переданный `Origin` должен точно совпадать с локальным адресом и портом backend. Чужой сайт, `Origin: null` и другой localhost-порт получают отказ даже с верным токеном. Отсутствие Origin допустимо для Dota и локальных инструментов, но не отменяет аутентификацию. CORS допускает только эти же локальные origins; сам по себе CORS не обеспечивает защиту записей.

## Обновление Dota config

При запуске launcher синхронизирует найденный `gamestate_integration_dota_ai_coach.cfg`: выбранный порт и блок Valve `auth.token`. После первого перехода на 0.53.7 **перезапустите Dota один раз**, чтобы игра прочитала новый config. Если config устанавливается в папку вручную, используйте обычную кнопку установки в launcher. Игровые блоки данных и heartbeat сохраняются.

POSIX-файлы credentials/config создаются с mode `0600`. В Windows действует доступ к user data и папке игры через существующие ACL; chmod не устанавливает отдельный Windows ACL. Backend, запускаемый без launcher, использует отдельный приватный `backend/local-api-auth.json` (или `WRITABLE_DIR` в сборке), с control и GSI токенами. Неверный/неполный файл или только одна из двух environment variables останавливают запуск; автоматической замены на незащищённый режим нет.

## Manual debug

Для standalone backend из `backend/`:

```bash
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

При другом порте задайте `DOTA_AI_BACKEND_PORT` с тем же значением, что `--port`. Не запускайте второй backend вместе с launcher. Если заданы `DOTA_AI_CONTROL_TOKEN` / `DOTA_AI_GSI_TOKEN`, оба должны быть разными случайными строками из 64 lowercase hex символов; храните их в environment, а не в аргументах запуска или общих логах.

Откройте `/docs`, нажмите **Authorize** и вставьте control-токен из своего приватного standalone файла. Swagger добавляет Bearer header к частным запросам. В простых developer pages `/frontend/index.html` и `/frontend/overlay.html` есть password-поле для того же токена; значение не сохраняется в localStorage. В обычном desktop интерфейсе ввод не нужен.

Replay helper автоматически читает standalone credentials или использует environment, полученный от launcher. Кнопки demo передают обе variables и выбранный порт в дочерний процесс. Helper не пересылает токен через HTTP redirects. Для site screenshots Node-часть использует тот же control-токен из environment или standalone файла; браузер получает только результаты запросов.

## Размеры и ошибки

До обработчиков проверяется объявленный и реально прочитанный размер, включая chunked HTTP без `Content-Length`:

| Запрос | Максимум |
|---|---|
| `POST /gsi` | 4 MiB |
| `POST /player/backup` | 512 MiB, как в launcher |
| Остальные тела | 1 MiB |

Непустые изменяющие запросы требуют `application/json`; compressed bodies не принимаются. Коды: `401 unauthorized`, `403 untrusted_origin/nonlocal_client`, `400 invalid_host/invalid_length/invalid_json/invalid_gsi`, `413 body_too_large`, `415 json_required/unsupported_encoding`. Ответ и diagnostics содержат код причины без присланных токенов или тела. Для GSI JSON также запрещены non-finite numbers и некорректные Unicode sequences. Конкурирующие standalone процессы публикуют полностью записанный credentials-файл атомарно и используют одного победителя.

Это граница локального HTTP. Программы с доступом к файлам/environment того же OS-пользователя могут получить его credentials. Защита IPC sender, navigation и CSP относится к отдельному F17; control-токен не предназначен для исправления XSS внутри доверенного renderer. Проверки включают реальный TCP backend, сохранённые сессии, параллельное создание credentials и launcher/Windows smoke с положительными и отрицательными запросами. Живая Dota в CI не запускается; Valve payload проверяется по токену из настоящего генератора config.
