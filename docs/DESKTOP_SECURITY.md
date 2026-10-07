# Desktop: IPC и окна

F17 в 0.53.8 ограничивает полномочия renderer на границе Electron. Все privileged `ipcMain.handle` регистрируются через общий `trustedHandlers` из `renderer-security.js`.

## Кто может вызвать IPC

Обработчик запускается только если совпадают одновременно:

1. Текущее владеющее окно существует и не уничтожено.
2. `event.sender` — именно его `webContents`, который тоже ещё существует.
3. `event.senderFrame` — текущий `webContents.mainFrame`, а не вложенный frame.
4. Frame загрузил ожидаемый локальный `file:` URL с точной query string. Fragment допускается для переходов внутри того же документа.

`launcher:*` разрешены только главному окну с `renderer/index.html`. `overlay:*` — только текущему overlay с `overlay/index.html`. `skill-arrow:save/auto/cancel` — только окну калибровки с `skill-arrows/index.html?mode=calibrate`; окно стрелки с `mode=arrow` этих прав не имеет. Getter текущего окна проверяется при каждом invoke, поэтому старое окно после пересоздания не сохраняет доступ. Отсутствующий, уничтоженный или недоступный frame даёт generic `Untrusted IPC sender` без выполнения callback. URL страницы сам по себе не предоставляет полномочий: другое окно с тем же файлом и настоящим preload всё равно получает отказ.

Preload остаётся узким API с `contextIsolation=true`, `nodeIntegration=false`, `sandbox=true`. Проверка sender дополняет существующий whitelist player operations и валидацию аргументов. Данные пользователя и настройки меняются только после проверки отправителя. Токены локального backend остаются в main process; HTTP-граница описана в [LOCAL_API_SECURITY.md](LOCAL_API_SECURITY.md).

## Навигация и CSP

Главное окно, overlay, splash, окно стрелки и калибровка запрещают renderer-initiated navigation, frame navigation, redirects, attach webview и `window.open`. Main process продолжает загружать их локальные страницы через `loadFile`. Внешние ссылки приложения используют существующие явные IPC-действия и проверенные адреса через `shell.openExternal`.

Главная страница и overlay теперь задают CSP до загрузки ресурсов: default deny, scripts только `self`, fonts/local CSS только `self`, запрет direct connections, frames, objects, forms и base URL. Изображения главной страницы допускают локальные ресурсы, `dota-asset:`, data URLs и HTTPS (аватары Steam); overlay использует локальные картинки, `dota-asset:` и data URLs. Main process продолжает обслуживать assets и HTTP, renderer получает DTO через IPC.

Inline styles остаются разрешёнными в этих двух страницах: текущие компоненты задают размеры, CSS variables, графики и динамические стили. Inline/eval scripts не разрешены. Splash и skill-arrows сохраняют свой существующий CSP. Эта граница не устраняет произвольный XSS внутри уже доверенного главного документа и не защищает от программ с полномочиями того же OS-пользователя; точные permissions и argument validation по-прежнему обязательны.

## Проверки

Node-проверки используют наблюдаемые эффекты callback: чужой webContents, subframe, неверный URL/query, исчезнувший frame и старое окно не выполняют действие. Window guards отменяют navigation/redirect/webview events и всегда отказывают popup.

`--smoke-test=<file>` выполняет общий `renderer-security-smoke.js` в настоящем Electron, также в Windows packaged app и установленной NSIS-версии:

- Settings переключаются через DOM-кнопки RU/EN; проверяются язык, видимый текст и выбранная кнопка. Исходная настройка языка восстанавливается.
- В main/overlay проверяются CSP violations при внедрении inline script и direct HTTP fetch, реальный переход на здоровый локальный backend и попытка popup.
- Другие окна загружают те же локальные HTML и настоящие preloads, но их IPC получает отказ.
- Штатная калибровка открывается через main IPC и закрывается своей DOM-кнопкой Cancel через calibration IPC без изменения frame settings.
- Сохраняются предыдущие smoke-проверки backend, токенов, GSI config и graceful shutdown.

Новые smoke-модули входят в installer `build.files`, и packaging check проверяет локальные require dependencies. Skill arrow geometry, live advice и match analysis в этом исправлении не меняются.
