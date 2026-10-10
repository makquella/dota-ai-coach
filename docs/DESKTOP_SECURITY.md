# Desktop: IPC і вікна

F17 у 0.53.8 обмежує повноваження renderer на межі Electron. Усі privileged `ipcMain.handle` реєструються через спільний `trustedHandlers` з `renderer-security.js`.

## Хто може викликати IPC

Обробник запускається, лише якщо водночас збігаються:

1. Поточне вікно-власник існує й не знищене.
2. `event.sender` — саме його `webContents`, який теж іще існує.
3. `event.senderFrame` — поточний `webContents.mainFrame`, а не вкладений frame.
4. Frame завантажив очікуваний локальний `file:` URL з точним query string. Fragment допускається для переходів усередині того самого документа.

`launcher:*` дозволені лише головному вікну з `renderer/index.html`. `overlay:*` — лише поточному overlay з `overlay/index.html`. `skill-arrow:save/auto/cancel` — лише вікну калібрування з `skill-arrows/index.html?mode=calibrate`; вікно стрілки з `mode=arrow` цих прав не має. Getter поточного вікна перевіряється під час кожного invoke, тому старе вікно після перестворення не зберігає доступу. Відсутній, знищений чи недоступний frame дає generic `Untrusted IPC sender` без виконання callback. URL сторінки сам собою не надає повноважень: інше вікно з тим самим файлом і справжнім preload усе одно отримує відмову.

Preload залишається вузьким API з `contextIsolation=true`, `nodeIntegration=false`, `sandbox=true`. Перевірка sender доповнює наявний whitelist player operations і валідацію аргументів. Дані користувача й налаштування змінюються лише після перевірки відправника. Токени локального backend залишаються в main process; HTTP-межу описано в [LOCAL_API_SECURITY.md](LOCAL_API_SECURITY.md).

## Навігація і CSP

Головне вікно, overlay, splash, вікно стрілки й калібрування забороняють renderer-initiated navigation, frame navigation, redirects, attach webview і `window.open`. Main process і далі завантажує їхні локальні сторінки через `loadFile`. Зовнішні посилання застосунку використовують наявні явні IPC-дії та перевірені адреси через `shell.openExternal`.

Головна сторінка й overlay тепер задають CSP до завантаження ресурсів: default deny, scripts лише `self`, fonts/local CSS лише `self`, заборона direct connections, frames, objects, forms і base URL. Зображення головної сторінки допускають локальні ресурси, `dota-asset:`, data URLs і HTTPS (аватари Steam); overlay використовує локальні картинки, `dota-asset:` і data URLs. Main process і далі обслуговує assets та HTTP, renderer отримує DTO через IPC.

Inline styles залишаються дозволеними на цих двох сторінках: поточні компоненти задають розміри, CSS variables, графіки й динамічні стилі. Inline/eval scripts не дозволено. Splash і skill-arrows зберігають свій наявний CSP. Ця межа не усуває довільного XSS усередині вже довіреного головного документа й не захищає від програм із повноваженнями того самого OS-користувача; точні permissions і argument validation, як і раніше, обов'язкові.

## Перевірки

Node-перевірки використовують спостережувані ефекти callback: чужий webContents, subframe, хибний URL/query, зниклий frame і старе вікно не виконують дії. Window guards скасовують navigation/redirect/webview events і завжди відмовляють popup.

`--smoke-test=<file>` виконує спільний `renderer-security-smoke.js` у справжньому Electron, також у Windows packaged app і встановленій NSIS-версії:

- Settings перемикаються через DOM-кнопки UK/EN; перевіряються мова, видимий текст і вибрана кнопка. Вихідне налаштування мови відновлюється.
- У main/overlay перевіряються CSP violations під час впровадження inline script і direct HTTP fetch, реальний перехід на здоровий локальний backend і спроба popup.
- Інші вікна завантажують ті самі локальні HTML і справжні preloads, але їхній IPC отримує відмову.
- Штатне калібрування відкривається через main IPC і закривається своєю DOM-кнопкою Cancel через calibration IPC без зміни frame settings.
- Зберігаються попередні smoke-перевірки backend, токенів, GSI config і graceful shutdown.

Нові smoke-модулі входять до installer `build.files`, і packaging check перевіряє локальні require dependencies. Skill arrow geometry, live advice та match analysis у цьому виправленні не змінюються.
