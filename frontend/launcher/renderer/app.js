// Control panel: one status line (what is going on + what to do), three
// cards (current match, recent advice, overlay settings) and a collapsed
// "For developers" section with every other tool (service, GSI config, live
// GSI, recordings, replay demos, Deep Review, logs). Texts follow the system
// language (ru/en) sent by the main process as status.locale.

const I18N = {
  en: {
    tabHome: "Home",
    tabMatches: "Matches",
    tabProgress: "Progress",
    tabSettings: "Settings",
    adviceSettingsTitle: "Advice",
    appTitle: "App",
    service: "Service",
    serviceStates: { running: "running", starting: "starting…", stopping: "stopping…", stopped: "stopped" },
    status: {
      loadingTitle: "Starting the service…",
      loadingHint: "Usually takes a couple of seconds.",
      backendDownTitle: "The service is not running",
      backendDownHint: "Advice will not arrive while the local service is stopped.",
      gsiErrorTitle: "Could not write the GSI config",
      gsiErrorHint: "No access to the Dota folder. Point to the game folder manually.",
      noDotaTitle: "Dota not found",
      noDotaHint: "Dota 2 is not in your Steam libraries. Point to the game folder and the config is installed for you.",
      noGsiTitle: "Connect Dota",
      noGsiHint: "Install the GSI config: a small file in the game folder that lets Dota share match data.",
      notRunningTitle: "Dota is not running",
      notRunningHint: "Start Dota 2; the coach connects by itself. You can close this window.",
      waitingTitle: "Ready, waiting for a match",
      waitingHintConnected: "Advice starts as soon as a match with your hero begins.",
      waitingHintNoData: "If a match is already on, restart Dota: it reads the GSI config at start.",
      inGameTitle: (hero, clock) => `In game: ${[hero, clock].filter(Boolean).join(", ")}`,
      inGameHint: "Advice appears over the game while Dota is the active window.",
      inGameOverlayOff: "The overlay is off, advice shows only here.",
      demoTitle: (preset) => `Replay demo${preset ? `: ${preset}` : ""}`,
      demoHint: "The overlay shows advice from a recorded match.",
      fullscreenTitle: "The overlay is hidden by fullscreen",
      fullscreenHint:
        "Dota runs in exclusive fullscreen, where no window can be drawn on top. In Dota: Settings → Video → Display mode → Borderless window. Or turn on the voice in Settings → Advice: it is heard in any mode."
    },
    actions: {
      start: "Start service",
      install: "Install config",
      chooseDota: "Choose Dota folder",
      fullscreenSeen: "I can see the advice"
    },
    matchTitle: "Current match",
    statHero: "Hero",
    statClock: "Match time",
    statStage: "Stage",
    statData: "Game data",
    dataFresh: (s) => `${s} s ago`,
    matchEmptyTitle: "No match right now",
    matchEmptyHint: "Hero and time show up here when a match starts.",
    offlineTitle: "No connection to the service",
    offlineHint: "Start the service to see match data.",
    adviceTitle: "Recent advice",
    adviceEmptyTitle: "No advice yet",
    adviceEmptyHint: "Advice shows up here as it appears over the game.",
    priority: { high: "high priority", urgent: "high priority", medium: "medium priority", low: "low priority", safe: "calm" },
    stages: { laning: "Laning", "post-laning": "After laning", macro: "Mid/late game" },
    overlayTitle: "Overlay",
    overlayShow: "Show advice over the game",
    overlayReason: {
      off: "Off",
      positioning: "Shown so you can move it",
      demo: "Showing the replay demo",
      no_tracking: "Always visible (focus tracking unavailable)",
      dota_not_running: "Appears in a match, over Dota",
      dota_not_focused: "Hidden while Dota is in the background",
      no_match: "Appears when a match starts",
      in_game: "On screen now"
    },
    overlayPosition: "Position",
    positionHint: "Away from the minimap and the hero panel",
    positionCustom: "Custom position, pick a preset to reset",
    posLeft: "Left",
    posRight: "Right",
    posBottom: "Bottom",
    frequencyTitle: "How often",
    frequencyCalm: "Less",
    frequencyNormal: "Normal",
    frequencyActive: "More",
    frequencyHint: {
      calm: "Twice the pause between tips; urgent advice is never delayed",
      normal: "Balanced pauses between tips",
      active: "Shorter pauses between tips; urgent advice as always"
    },
    voiceTitle: "Voice",
    voiceOff: "Off",
    voiceUrgent: "Urgent",
    voiceAll: "All",
    voiceTest: "Listen",
    voiceHint: {
      off: "Advice is only shown, not spoken",
      urgent: "Speaks urgent advice; heard even in exclusive fullscreen",
      all: "Speaks every piece of advice; heard even in exclusive fullscreen"
    },
    voiceNoVoice: "No English voice in the system: Windows Settings → Time & language → Speech",
    voiceSample: "Back off: the enemy is missing from the map.",
    overlayMove: "Move by hand",
    moveHint: "Shows the card so you can drag it anywhere",
    moveActiveHint: "Drag the card, then press Done",
    moveStart: "Move",
    moveDone: "Done",
    autostart: "Start with Windows",
    autostartOn: "Starts hidden in the tray",
    autostartOff: "Start it yourself before playing",
    autostartUnavailable: "Available in the installed app",
    updates: "Updates",
    updateCheck: "Check",
    updateInstall: "Restart and update",
    updateHint: {
      disabled: (v) => `Version ${v} · updates work in the installed app`,
      idle: (v) => `Version ${v} · updates install by themselves`,
      checking: (v) => `Version ${v} · checking…`,
      "up-to-date": (v) => `Version ${v} · up to date`,
      downloading: (v, next, pct) => `Downloading ${next}… ${pct}%`,
      ready: (v, next) => `Version ${next} is ready. It installs by itself once Dota is closed.`,
      blocked: (v, next) => `Version ${next} is ready. It installs after you close Dota.`,
      error: (v) => `Version ${v} · could not check for updates`
    },
    setupTitle: "Getting started",
    setupHide: "Hide",
    setupCount: (done, total) => `${done} of ${total}`,
    setup: {
      service: ["The coach service is running", "Starts with the app; restart it in Settings → «For developers» if it stopped."],
      dota: ["Dota 2 found", "Not in your Steam libraries: point to the game folder."],
      gsi: ["Game data config installed", "A small file in the Dota folder that lets the game share match data."],
      data: ["First data from Dota received", "Start Dota 2 (or restart it after installing the config) and open any match, bots are fine."],
      account: ["Steam account linked", "Linked by itself in the first match, or enter it on the Matches tab."],
      ai: ["AI coach (optional)", "A free Gemini key writes a coach review of every match."]
    },
    setupActions: { dota: "Choose folder", gsi: "Install", account: "Link", ai: "Set up" },
    reportTitle: "Problem report",
    reportHint: "Saves one file with logs for the developer, without keys",
    reportSave: "Save",
    reportSaving: "Collecting…",
    reportSaved: (name) => `Saved: ${name}. Send this file to the developer.`,
    reportFailed: "Could not save the file",
    devTitle: "For developers",
    devHint: "Service, GSI, replay demos, recordings, logs",
    factBackend: "Service",
    factDota: "Dota",
    factOverlay: "Overlay",
    factDemo: "Demo",
    factRecording: "Recording",
    factGsiConfig: "GSI config",
    factMode: "Mode",
    groupBackend: "Service",
    startBackend: "Start",
    restartBackend: "Restart",
    stopBackend: "Stop",
    showOverlay: "Show overlay",
    hideOverlay: "Hide overlay",
    hotkeys: "Ctrl+Alt+O on/off · Ctrl+Alt+L move · Ctrl+Alt+M mute 5 min · Ctrl+Alt+1/2/3 left/right/bottom · Ctrl+Alt+D debug line",
    groupGsi: "GSI config",
    gsiPathPlaceholder: "Custom gamestate_integration folder (optional)",
    chooseFolder: "Choose",
    checkGsi: "Check",
    installGsi: "Install",
    gsiPath: (p, e) => `Config: ${p}${e ? `\nEndpoint: ${e}` : ""}`,
    gsiPathMissing: "Config not found. Choose the gamestate_integration folder and install.",
    gsiEndpoint: (e) => (e ? `Endpoint: ${e}` : "Endpoint: waiting for the service port…"),
    groupLive: "Live GSI",
    kvConnection: "Connection",
    kvLast: "Last data",
    kvHero: "Hero",
    kvTime: "Game time",
    kvStage: "Stage",
    liveConnected: "connected",
    liveWaiting: "waiting / stale",
    liveUnavailable: "service unavailable",
    liveAdvice: (a) => `Current advice: ${a}`,
    liveAdviceNone: "Current advice: none yet",
    liveAdviceLast: (t) => `Current advice: last shown at ${t}`,
    liveMissing: (m) => `Missing important fields: ${m}`,
    none: "none",
    checkLive: "Check",
    startRecording: "Record",
    stopRecording: "Stop recording",
    openRecords: "Recordings",
    groupDemo: "Replay demo",
    demoHint: "Plays recorded match states into the service; the overlay shows without Dota.",
    demoBusy: "A demo is already running. Stop it first.",
    runDemo: "Run demo",
    presetPl: "Phantom Lancer 20–30",
    presetJugg: "Juggernaut 10–20",
    deepReview: "Deep Review",
    stopDemo: "Stop",
    openResults: "Results",
    groupLogs: "Logs",
    logClean: "Clean",
    logVerbose: "Verbose",
    copyLogs: "Copy",
    clearLogs: "Clear",
    openLogs: "Logs folder",
    dotaStates: { not_found: "not found", waiting: "waiting for a match", in_game: "in game" },
    gsiConfigStates: { installed: "installed", "not found": "not found", error: "error", unknown: "unknown" },
    modes: { "Live GSI": "Live GSI", "Replay Demo": "Replay demo" },
    on: "on",
    off: "off",
    shown: "on screen",
    hidden: "hidden",
    running: "running",
    stopped: "stopped"
  },
  ru: {
    tabHome: "Главная",
    tabMatches: "Матчи",
    tabProgress: "Прогресс",
    tabSettings: "Настройки",
    adviceSettingsTitle: "Советы",
    appTitle: "Приложение",
    service: "Сервис",
    serviceStates: { running: "работает", starting: "запускается…", stopping: "останавливается…", stopped: "остановлен" },
    status: {
      loadingTitle: "Запускаем сервис…",
      loadingHint: "Обычно это пара секунд.",
      backendDownTitle: "Сервис не запущен",
      backendDownHint: "Подсказки не придут, пока локальный сервис остановлен.",
      gsiErrorTitle: "Не удалось записать конфиг GSI",
      gsiErrorHint: "Нет доступа к папке Доты. Укажите папку игры вручную.",
      noDotaTitle: "Дота не найдена",
      noDotaHint: "Dota 2 нет в библиотеках Steam. Укажите папку игры — конфиг установится сам.",
      noGsiTitle: "Подключите Доту",
      noGsiHint: "Установите конфиг GSI — небольшой файл в папке игры, через который Дота передаёт данные матча.",
      notRunningTitle: "Дота не запущена",
      notRunningHint: "Запустите Dota 2 — тренер подключится сам. Это окно можно закрыть.",
      waitingTitle: "Готово, ждём матч",
      waitingHintConnected: "Подсказки начнутся, как только стартует матч с вашим героем.",
      waitingHintNoData: "Если матч уже идёт, перезапустите Доту: конфиг GSI читается при старте игры.",
      inGameTitle: (hero, clock) => `В игре: ${[hero, clock].filter(Boolean).join(", ")}`,
      inGameHint: "Подсказки появляются поверх игры, пока окно Доты активно.",
      inGameOverlayOff: "Оверлей выключен — подсказки видны только здесь.",
      demoTitle: (preset) => `Демо-повтор${preset ? `: ${preset}` : ""}`,
      demoHint: "Оверлей показывает подсказки из записанного матча.",
      fullscreenTitle: "Оверлей не виден из-за полноэкранного режима",
      fullscreenHint:
        "Дота запущена в эксклюзивном полноэкранном режиме — поверх него окна не рисуются. В Доте: Настройки → Видео → режим экрана «Окно без рамки» (Borderless window). Или включите голос в «Настройки → Советы» — его слышно в любом режиме."
    },
    actions: {
      start: "Запустить сервис",
      install: "Установить конфиг",
      chooseDota: "Указать папку Доты",
      fullscreenSeen: "Подсказки видны"
    },
    matchTitle: "Текущий матч",
    statHero: "Герой",
    statClock: "Время матча",
    statStage: "Стадия",
    statData: "Данные игры",
    dataFresh: (s) => `${s} с назад`,
    matchEmptyTitle: "Матч не идёт",
    matchEmptyHint: "Герой и время появятся здесь, когда начнётся матч.",
    offlineTitle: "Нет связи с сервисом",
    offlineHint: "Запустите сервис, чтобы видеть данные матча.",
    adviceTitle: "Последние подсказки",
    adviceEmptyTitle: "Подсказок пока нет",
    adviceEmptyHint: "Здесь появятся подсказки, которые показывались поверх игры.",
    priority: { high: "высокий приоритет", urgent: "высокий приоритет", medium: "средний приоритет", low: "низкий приоритет", safe: "спокойно" },
    stages: { laning: "Лайнинг", "post-laning": "После лайнинга", macro: "Середина/поздняя игра" },
    overlayTitle: "Оверлей",
    overlayShow: "Показывать подсказки поверх игры",
    overlayReason: {
      off: "Выключено",
      positioning: "Показан, чтобы его можно было переместить",
      demo: "Показывает демо-повтор",
      no_tracking: "Всегда виден (отслеживание фокуса недоступно)",
      dota_not_running: "Появится в матче поверх Доты",
      dota_not_focused: "Скрыт, пока Дота в фоне",
      no_match: "Появится, когда начнётся матч",
      in_game: "Сейчас на экране"
    },
    overlayPosition: "Положение",
    positionHint: "В стороне от миникарты и панели героя",
    positionCustom: "Своё положение — выберите вариант, чтобы вернуть",
    posLeft: "Слева",
    posRight: "Справа",
    posBottom: "Снизу",
    frequencyTitle: "Частота советов",
    frequencyCalm: "Реже",
    frequencyNormal: "Обычно",
    frequencyActive: "Чаще",
    frequencyHint: {
      calm: "Вдвое больше пауза между советами; срочные не задерживаются",
      normal: "Обычные паузы между советами",
      active: "Короче паузы между советами; срочные как всегда"
    },
    voiceTitle: "Голос",
    voiceOff: "Выкл",
    voiceUrgent: "Срочные",
    voiceAll: "Все",
    voiceTest: "Прослушать",
    voiceHint: {
      off: "Советы только на экране, без озвучки",
      urgent: "Озвучивает срочные советы; слышно даже в полноэкранном режиме",
      all: "Озвучивает все советы; слышно даже в полноэкранном режиме"
    },
    voiceNoVoice: "В Windows нет русского голоса: Параметры → Время и язык → Речь → Добавить голоса",
    voiceSample: "Отходите: противника не видно на карте.",
    overlayMove: "Переместить вручную",
    moveHint: "Покажет карточку, чтобы её можно было перетащить",
    moveActiveHint: "Перетащите карточку и нажмите «Готово»",
    moveStart: "Переместить",
    moveDone: "Готово",
    autostart: "Автозапуск с Windows",
    autostartOn: "Запускается скрыто в трее",
    autostartOff: "Запускайте сами перед игрой",
    autostartUnavailable: "Доступно в установленном приложении",
    updates: "Обновления",
    updateCheck: "Проверить",
    updateInstall: "Перезапустить и обновить",
    updateHint: {
      disabled: (v) => `Версия ${v} · обновления работают в установленном приложении`,
      idle: (v) => `Версия ${v} · обновляется само`,
      checking: (v) => `Версия ${v} · проверяем…`,
      "up-to-date": (v) => `Версия ${v} · последняя`,
      downloading: (v, next, pct) => `Загружается ${next}… ${pct}%`,
      ready: (v, next) => `Версия ${next} загружена. Установится сама, когда Дота будет закрыта.`,
      blocked: (v, next) => `Версия ${next} загружена. Установится после выхода из Доты.`,
      error: (v) => `Версия ${v} · не удалось проверить обновления`
    },
    setupTitle: "Первый запуск",
    setupHide: "Скрыть",
    setupCount: (done, total) => `${done} из ${total}`,
    setup: {
      service: ["Сервис тренера запущен", "Запускается вместе с приложением; если остановился, перезапустите в «Настройки → Для разработчика»."],
      dota: ["Dota 2 найдена", "Игры нет в библиотеках Steam — укажите папку игры."],
      gsi: ["Конфиг данных игры установлен", "Небольшой файл в папке Доты, через который игра передаёт данные матча."],
      data: ["Первые данные из Доты получены", "Запустите Dota 2 (или перезапустите после установки конфига) и зайдите в любой матч, можно с ботами."],
      account: ["Аккаунт Steam привязан", "Привяжется сам в первом матче, или укажите его на вкладке «Матчи»."],
      ai: ["ИИ-тренер (по желанию)", "Бесплатный ключ Gemini — и к каждому матчу будет разбор тренера."]
    },
    setupActions: { dota: "Указать папку", gsi: "Установить", account: "Привязать", ai: "Настроить" },
    reportTitle: "Отчёт о проблеме",
    reportHint: "Сохранит файл с журналами для разработчика, без ключей",
    reportSave: "Сохранить",
    reportSaving: "Собираем…",
    reportSaved: (name) => `Сохранено: ${name}. Отправьте этот файл разработчику.`,
    reportFailed: "Не удалось сохранить файл",
    devTitle: "Для разработчика",
    devHint: "Сервис, GSI, демо-повторы, записи, логи",
    factBackend: "Сервис",
    factDota: "Дота",
    factOverlay: "Оверлей",
    factDemo: "Демо",
    factRecording: "Запись",
    factGsiConfig: "Конфиг GSI",
    factMode: "Режим",
    groupBackend: "Сервис",
    startBackend: "Запустить",
    restartBackend: "Перезапустить",
    stopBackend: "Остановить",
    showOverlay: "Показать оверлей",
    hideOverlay: "Скрыть оверлей",
    hotkeys: "Ctrl+Alt+O вкл/выкл · Ctrl+Alt+L переместить · Ctrl+Alt+M тишина 5 мин · Ctrl+Alt+1/2/3 слева/справа/снизу · Ctrl+Alt+D отладка",
    groupGsi: "Конфиг GSI",
    gsiPathPlaceholder: "Своя папка gamestate_integration (необязательно)",
    chooseFolder: "Выбрать",
    checkGsi: "Проверить",
    installGsi: "Установить",
    gsiPath: (p, e) => `Конфиг: ${p}${e ? `\nАдрес: ${e}` : ""}`,
    gsiPathMissing: "Конфиг не найден. Выберите папку gamestate_integration и установите.",
    gsiEndpoint: (e) => (e ? `Адрес: ${e}` : "Адрес: ждём порт сервиса…"),
    groupLive: "Живой GSI",
    kvConnection: "Связь",
    kvLast: "Данные",
    kvHero: "Герой",
    kvTime: "Время",
    kvStage: "Стадия",
    liveConnected: "подключено",
    liveWaiting: "ожидание / устарело",
    liveUnavailable: "сервис недоступен",
    liveAdvice: (a) => `Текущий совет: ${a}`,
    liveAdviceNone: "Текущий совет: пока нет",
    liveAdviceLast: (t) => `Текущий совет: последний в ${t}`,
    liveMissing: (m) => `Не хватает полей: ${m}`,
    none: "нет",
    checkLive: "Проверить",
    startRecording: "Записать",
    stopRecording: "Остановить запись",
    openRecords: "Записи",
    groupDemo: "Демо-повтор",
    demoHint: "Проигрывает записанные состояния матча в сервис; оверлей виден без Доты.",
    demoBusy: "Демо уже идёт. Сначала остановите его.",
    runDemo: "Запустить демо",
    presetPl: "Phantom Lancer 20–30",
    presetJugg: "Juggernaut 10–20",
    deepReview: "Deep Review",
    stopDemo: "Остановить",
    openResults: "Результаты",
    groupLogs: "Логи",
    logClean: "Кратко",
    logVerbose: "Подробно",
    copyLogs: "Копировать",
    clearLogs: "Очистить",
    openLogs: "Папка логов",
    dotaStates: { not_found: "не найдена", waiting: "ждём матч", in_game: "в игре" },
    gsiConfigStates: { installed: "установлен", "not found": "не найден", error: "ошибка", unknown: "неизвестно" },
    modes: { "Live GSI": "Живой GSI", "Replay Demo": "Демо-повтор" },
    on: "вкл",
    off: "выкл",
    shown: "на экране",
    hidden: "скрыт",
    running: "идёт",
    stopped: "остановлено"
  }
};

const $ = (selector) => document.querySelector(selector);
const els = {
  service: $("#service"),
  serviceText: $("#service-text"),
  status: $("#status"),
  statusTitle: $("#status-title"),
  statusHint: $("#status-hint"),
  statusAction: $("#status-action"),
  statusActionLabel: $("#status-action-label"),
  matchStats: $("#match-body .stats"),
  matchEmpty: $("#match-empty"),
  statHero: $("#stat-hero"),
  statClock: $("#stat-clock"),
  statStage: $("#stat-stage"),
  statData: $("#stat-data"),
  adviceList: $("#advice-list"),
  adviceEmpty: $("#advice-empty"),
  overlayToggle: $("#overlay-toggle"),
  overlayHint: $("#overlay-hint"),
  positionButtons: [...document.querySelectorAll("#position-group [data-position]")],
  positionHint: $("#position-hint"),
  frequencyButtons: [...document.querySelectorAll("#frequency-group [data-frequency]")],
  frequencyHint: $("#frequency-hint"),
  voiceButtons: [...document.querySelectorAll("#voice-group [data-voice]")],
  voiceHint: $("#voice-hint"),
  voiceTest: $("#voice-test"),
  moveToggle: $("#move-toggle"),
  moveLabel: $("#move-label"),
  moveHint: $("#move-hint"),
  autostart: $("#autostart"),
  autostartHint: $("#autostart-hint"),
  updateHint: $("#update-hint"),
  updateAction: $("#update-action"),
  updateLabel: $("#update-label"),
  setupCard: $("#setup-card"),
  setupSteps: $("#setup-steps"),
  setupCount: $("#setup-count"),
  setupDismiss: $("#setup-dismiss"),
  reportAction: $("#report-action"),
  reportHint: $("#report-hint"),
  devTools: $("#dev-tools"),
  logs: $("#logs"),
  gsiPath: $("#gsi-path"),
  gsiDetail: $("#gsi-detail")
};
const factEls = {
  backend: $("#backend-status"),
  dota: $("#dota-status"),
  overlay: $("#overlay-status"),
  demo: $("#demo-status"),
  recording: $("#recording-status"),
  gsi: $("#gsi-status"),
  mode: $("#mode-status"),
  llm: $("#llm-status")
};
const liveEls = {
  connection: $("#live-connection"),
  last: $("#live-last"),
  hero: $("#live-hero"),
  time: $("#live-time"),
  stage: $("#live-stage"),
  advice: $("#live-advice"),
  missing: $("#live-missing")
};
const logModeButtons = { clean: $("#log-clean"), verbose: $("#log-verbose") };
const demoStartButtons = ["#run-demo", "#preset-pl", "#preset-jugg", "#deep-review"].map($).filter(Boolean);
const controlButtons = {
  startBackend: $("#start-backend"),
  restartBackend: $("#restart-backend"),
  stopBackend: $("#stop-backend"),
  startOverlay: $("#start-overlay"),
  stopOverlay: $("#stop-overlay"),
  stopDemo: $("#stop-demo"),
  startRecording: $("#start-recording"),
  stopRecording: $("#stop-recording")
};

const DEV_OPEN_KEY = "dota-ai-coach.devToolsOpen";
let locale = "en";
let textsLocale = "";
let gsiEndpoint = "";
let statusAction = null;
let lastVoice = { mode: "off", volume: 1 };
let voiceListChecked = false;
const seenAdvice = new Set();

init();

// ---------------------------------------------------------------------------
// i18n
// ---------------------------------------------------------------------------

function lookup(table, key) {
  return key.split(".").reduce((node, part) => (node ? node[part] : undefined), table);
}

function tr(key, ...args) {
  const resolved = lookup(I18N[locale], key) ?? lookup(I18N.en, key) ?? key;
  return typeof resolved === "function" ? resolved(...args) : resolved;
}

// Like tr() for values that may be missing (backend-provided codes).
function trOr(key, fallback) {
  const value = lookup(I18N[locale], key) ?? lookup(I18N.en, key);
  return typeof value === "string" ? value : fallback;
}

function applyStaticTexts() {
  if (textsLocale === locale) {
    return;
  }
  textsLocale = locale;
  document.documentElement.lang = locale;
  for (const element of document.querySelectorAll("[data-i18n]")) {
    element.textContent = tr(element.dataset.i18n);
  }
  for (const element of document.querySelectorAll("[data-i18n-placeholder]")) {
    element.placeholder = tr(element.dataset.i18nPlaceholder);
  }
  for (const element of document.querySelectorAll("[data-i18n-title]")) {
    element.title = tr(element.dataset.i18nTitle);
    element.setAttribute("aria-label", element.title);
  }
}

// ---------------------------------------------------------------------------
// Wiring
// ---------------------------------------------------------------------------

async function init() {
  window.LucideIcons?.hydrate(document);

  bind("#start-backend", () => window.launcherApi.startBackend());
  bind("#stop-backend", () => window.launcherApi.stopBackend());
  bind("#restart-backend", () => window.launcherApi.restartBackend());
  bind("#start-overlay", () => window.launcherApi.startOverlay());
  bind("#stop-overlay", () => window.launcherApi.stopOverlay());
  bind("#run-demo", () => window.launcherApi.runDemo("plMacro"));
  bind("#stop-demo", () => window.launcherApi.stopDemo());
  bind("#preset-pl", () => window.launcherApi.runDemo("plMacro"));
  bind("#preset-jugg", () => window.launcherApi.runDemo("juggSafety"));
  bind("#deep-review", () => window.launcherApi.runDeepReview("plMacro"));
  bind("#open-logs", () => window.launcherApi.openLogs());
  bind("#open-results", () => window.launcherApi.openSimulationResults());
  bind("#open-readme", () => window.launcherApi.openReadme());
  bind("#clear-logs", () => window.launcherApi.clearLogs());
  bind("#copy-logs", () => window.launcherApi.copyLogs());
  bind("#log-clean", () => window.launcherApi.setLogMode("clean"));
  bind("#log-verbose", () => window.launcherApi.setLogMode("verbose"));
  bind("#check-gsi", checkGsi);
  bind("#install-gsi", () => installGsi(els.gsiPath.value));
  bind("#choose-gsi", chooseGsiFolder);
  bind("#check-live-gsi", checkLiveGsi);
  bind("#start-recording", startLiveRecording);
  bind("#stop-recording", stopLiveRecording);
  bind("#open-records", () => window.launcherApi.openSessionRecords());

  els.statusAction.addEventListener("click", async () => {
    if (!statusAction) {
      return;
    }
    const action = statusAction;
    els.statusAction.disabled = true;
    await run(action.run);
    els.statusAction.disabled = false;
  });
  els.overlayToggle.addEventListener("change", () =>
    run(() => (els.overlayToggle.checked ? window.launcherApi.startOverlay() : window.launcherApi.stopOverlay()))
  );
  for (const button of els.positionButtons) {
    button.addEventListener("click", () =>
      run(async () => renderStatus(await window.launcherApi.setOverlayPosition(button.dataset.position)))
    );
  }
  for (const button of els.frequencyButtons) {
    button.addEventListener("click", () =>
      run(async () => renderStatus(await window.launcherApi.setAdviceFrequency(button.dataset.frequency)))
    );
  }
  for (const button of els.voiceButtons) {
    button.addEventListener("click", () =>
      run(async () => renderStatus(await window.launcherApi.setOverlayVoice(button.dataset.voice)))
    );
  }
  els.voiceTest.addEventListener("click", () => run(testVoice));
  window.speechSynthesis?.addEventListener?.("voiceschanged", () => renderVoiceHint(lastVoice));
  els.moveToggle.addEventListener("click", () =>
    run(async () => {
      // Pressed = the card is unlocked for dragging; pressing again locks it.
      const moving = els.moveToggle.getAttribute("aria-pressed") === "true";
      renderStatus(await window.launcherApi.setOverlayLocked(moving));
    })
  );
  els.updateAction.addEventListener("click", () =>
    run(async () => {
      if (els.updateAction.dataset.mode === "install") {
        await window.launcherApi.installUpdate();
      } else {
        renderStatus(await window.launcherApi.checkForUpdates());
      }
    })
  );
  els.setupDismiss.addEventListener("click", () =>
    run(async () => renderStatus(await window.launcherApi.dismissSetup()))
  );
  els.reportAction.addEventListener("click", () =>
    run(async () => {
      els.reportAction.disabled = true;
      els.reportHint.textContent = tr("reportSaving");
      try {
        const result = await window.launcherApi.saveProblemReport();
        els.reportHint.textContent = result && result.ok
          ? tr("reportSaved", result.path.split(/[\\/]/).pop())
          : tr("reportFailed");
        els.reportHint.title = result && result.ok ? result.path : result?.error || "";
      } finally {
        els.reportAction.disabled = false;
      }
    })
  );
  els.autostart.addEventListener("change", () =>
    run(async () => {
      await window.launcherApi.setAutostart(els.autostart.checked);
      renderStatus(await window.launcherApi.getStatus());
    })
  );

  // Remember whether the developer section was open (per-user convenience).
  try {
    els.devTools.open = localStorage.getItem(DEV_OPEN_KEY) === "1";
  } catch {
    // Storage unavailable: start collapsed.
  }
  els.devTools.addEventListener("toggle", () => {
    try {
      localStorage.setItem(DEV_OPEN_KEY, els.devTools.open ? "1" : "0");
    } catch {
      // Ignore.
    }
  });

  window.launcherApi.onStatus(renderStatus);
  window.launcherApi.onLogs(renderLogs);

  renderLogs(await window.launcherApi.getLogs());
  renderStatus(await window.launcherApi.getStatus());
}

async function run(handler) {
  try {
    return await handler();
  } catch (error) {
    renderLogs(`${els.logs.textContent || ""}\n[renderer] ${error.message || error}\n`);
    return undefined;
  }
}

function bind(selector, handler) {
  const element = $(selector);
  if (element) {
    element.addEventListener("click", () => run(handler));
  }
}

async function checkGsi() {
  updateGsiDetail(await window.launcherApi.checkGsi(els.gsiPath.value));
}

async function installGsi(customPath) {
  updateGsiDetail(await window.launcherApi.installGsi(customPath));
}

async function chooseGsiFolder() {
  const folder = await window.launcherApi.chooseGsiFolder();
  if (folder) {
    els.gsiPath.value = folder;
    await checkGsi();
  }
}

async function checkLiveGsi() {
  renderLiveStatus(await window.launcherApi.checkLiveGsi());
}

async function startLiveRecording() {
  await window.launcherApi.startLiveRecording();
  await checkLiveGsi();
}

async function stopLiveRecording() {
  await window.launcherApi.stopLiveRecording();
  await checkLiveGsi();
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

function renderStatus(status) {
  if (!status) {
    return;
  }
  locale = I18N[status.locale] ? status.locale : "en";
  applyStaticTexts();
  gsiEndpoint = status.gsiEndpoint || "";
  document.body.dataset.loading = String(isLoading(status));

  renderService(status);
  renderStatusLine(status);
  renderSetup(status);
  renderMatch(status);
  renderAdvice(status);
  renderOverlaySettings(status);
  renderFacts(status);
  renderControlButtons(status);
  renderLogMode(status.logMode || "clean");
  updateGsiDetail({ status: status.gsiConfig, path: status.gsiPath });
  // Matches / Progress views (renderer/matches.js).
  window.PlayerViews?.onStatus(status);
}

// First-run checklist: the required steps in order, then the optional AI coach.
// Hidden once the required steps are done or the player hides it.
function setupSteps(status) {
  const player = status.player || {};
  // Data from the game proves Dota and the config work, wherever Dota lives.
  const dataSeen = Boolean(status.setup?.gsiSeen || status.live?.connected);
  return [
    { id: "service", done: status.backend === "running" },
    { id: "dota", done: Boolean(status.dotaDir || status.dotaRunning || dataSeen), action: () => window.launcherApi.chooseDotaFolder() },
    { id: "gsi", done: status.gsiConfig === "installed" || dataSeen, action: () => window.launcherApi.installGsi("") },
    { id: "data", done: dataSeen },
    { id: "account", done: Boolean(player.linked), action: () => window.PlayerViews?.setView("matches") },
    { id: "ai", done: Boolean(player.aiConfigured), optional: true, action: () => window.PlayerViews?.setView("progress") }
  ];
}

function renderSetup(status) {
  const steps = setupSteps(status);
  const required = steps.filter((step) => !step.optional);
  const doneCount = required.filter((step) => step.done).length;
  const hide = isLoading(status) || status.setup?.dismissed || doneCount === required.length;
  els.setupCard.classList.toggle("hidden", Boolean(hide));
  if (hide) {
    return;
  }
  els.setupCount.textContent = tr("setupCount", doneCount, required.length);
  // The first open step gets the action; later ones wait for it.
  const next = steps.find((step) => !step.done);
  const signature = JSON.stringify([locale, steps.map((step) => step.done), next?.id]);
  if (els.setupSteps.dataset.signature === signature) {
    return;
  }
  els.setupSteps.dataset.signature = signature;
  els.setupSteps.replaceChildren(
    ...steps.map((step) => {
      const [title, hint] = tr(`setup.${step.id}`);
      const item = document.createElement("li");
      item.className = "setup-step";
      item.dataset.done = String(step.done);
      const mark = document.createElement("i");
      mark.className = "setup-mark";
      mark.dataset.icon = step.done ? "circle-check" : "circle";
      const text = document.createElement("span");
      text.className = "setup-text";
      const titleEl = document.createElement("span");
      titleEl.className = "setup-step-title";
      titleEl.textContent = title;
      text.append(titleEl);
      if (!step.done) {
        const hintEl = document.createElement("span");
        hintEl.className = "setup-step-hint";
        hintEl.textContent = hint;
        text.append(hintEl);
      }
      item.append(mark, text);
      if (!step.done && step.action && (step === next || step.optional)) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = step === next && !step.optional ? "btn btn-primary btn-sm" : "btn btn-sm";
        button.textContent = tr(`setupActions.${step.id}`);
        button.addEventListener("click", () => run(step.action));
        item.append(button);
      }
      return item;
    })
  );
  window.LucideIcons?.hydrate(els.setupSteps);
}

function isLoading(status) {
  return status.backend === "starting";
}

function isOffline(status) {
  return status.backend === "stopped" || status.backend === "stopping";
}

function renderService(status) {
  const state = status.backend || "stopped";
  els.service.dataset.state = state;
  const port = status.backendPort && state === "running" ? ` · :${status.backendPort}` : "";
  els.serviceText.textContent = `${tr("service")} ${tr(`serviceStates.${state}`)}${port}`;
}

function formatClock(seconds) {
  if (!Number.isFinite(seconds)) {
    return "";
  }
  const sign = seconds < 0 ? "−" : "";
  const total = Math.abs(Math.trunc(seconds));
  return `${sign}${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

function stageLabel(stage) {
  return trOr(`stages.${stage}`, stage);
}

// Decide the single status line and its one action.
function resolveStatusLine(status) {
  const live = status.live || {};
  const api = window.launcherApi;
  const actions = {
    start: { label: tr("actions.start"), icon: "play", run: () => api.startBackend() },
    install: { label: tr("actions.install"), icon: "download", run: () => installGsi("") },
    chooseDota: { label: tr("actions.chooseDota"), icon: "folder-search", run: () => api.chooseDotaFolder() },
    fullscreenSeen: { label: tr("actions.fullscreenSeen"), icon: "eye", run: () => api.dismissFullscreenWarning() }
  };

  if (isLoading(status)) {
    return { state: "loading", title: tr("status.loadingTitle"), hint: tr("status.loadingHint") };
  }
  if (isOffline(status)) {
    return { state: "error", title: tr("status.backendDownTitle"), hint: tr("status.backendDownHint"), action: actions.start };
  }
  if (status.demo === "running") {
    return { state: "ok", title: tr("status.demoTitle", status.demoPreset), hint: tr("status.demoHint") };
  }
  if (status.gsiConfig === "error") {
    return { state: "error", title: tr("status.gsiErrorTitle"), hint: tr("status.gsiErrorHint"), action: actions.chooseDota };
  }
  if (status.gsiConfig !== "installed") {
    return status.dotaDir
      ? { state: "warn", title: tr("status.noGsiTitle"), hint: tr("status.noGsiHint"), action: actions.install }
      : { state: "error", title: tr("status.noDotaTitle"), hint: tr("status.noDotaHint"), action: actions.chooseDota };
  }
  if (status.dotaFullscreen) {
    // Sent only while Dota runs in exclusive fullscreen with the overlay on.
    return {
      state: "warn",
      title: tr("status.fullscreenTitle"),
      hint: tr("status.fullscreenHint"),
      action: actions.fullscreenSeen
    };
  }
  if (live.inMatch) {
    const hint = status.overlay === "running" ? tr("status.inGameHint") : tr("status.inGameOverlayOff");
    return { state: "ok", title: tr("status.inGameTitle", live.hero, formatClock(live.clockTime)), hint };
  }
  if (!status.dotaRunning) {
    return { state: "idle", title: tr("status.notRunningTitle"), hint: tr("status.notRunningHint") };
  }
  return {
    state: "warn",
    title: tr("status.waitingTitle"),
    hint: live.connected ? tr("status.waitingHintConnected") : tr("status.waitingHintNoData")
  };
}

function renderStatusLine(status) {
  const line = resolveStatusLine(status);
  els.status.dataset.state = line.state;
  els.statusTitle.textContent = line.title;
  els.statusHint.textContent = line.hint || "";
  statusAction = line.action || null;
  els.statusAction.classList.toggle("hidden", !statusAction);
  if (statusAction) {
    els.statusActionLabel.textContent = statusAction.label;
    const icon = els.statusAction.querySelector("i[data-icon]");
    icon.dataset.icon = statusAction.icon;
    window.LucideIcons?.hydrate(els.statusAction);
  }
}

function skeleton(widthClass) {
  const span = document.createElement("span");
  span.className = `skeleton skeleton-line ${widthClass}`;
  return span;
}

function setEmpty(container, visible, { title, hint, icon } = {}) {
  container.classList.toggle("hidden", !visible);
  if (!visible) {
    return;
  }
  const iconEl = container.querySelector("i[data-icon]");
  if (icon && iconEl && iconEl.dataset.icon !== icon) {
    iconEl.dataset.icon = icon;
    window.LucideIcons?.hydrate(container);
  }
  if (title !== undefined) {
    container.querySelector(".empty-title").textContent = title;
  }
  if (hint !== undefined) {
    container.querySelector(".empty-hint").textContent = hint;
  }
}

function renderMatch(status) {
  const live = status.live || {};
  if (isLoading(status)) {
    els.matchStats.classList.remove("hidden");
    setEmpty(els.matchEmpty, false);
    els.statHero.replaceChildren(skeleton("w-70"));
    els.statClock.replaceChildren(skeleton("w-40"));
    els.statStage.replaceChildren(skeleton("w-60"));
    els.statData.replaceChildren(skeleton("w-50"));
    return;
  }
  if (isOffline(status)) {
    els.matchStats.classList.add("hidden");
    setEmpty(els.matchEmpty, true, { title: tr("offlineTitle"), hint: tr("offlineHint"), icon: "wifi-off" });
    return;
  }
  if (!live.inMatch) {
    els.matchStats.classList.add("hidden");
    setEmpty(els.matchEmpty, true, { title: tr("matchEmptyTitle"), hint: tr("matchEmptyHint"), icon: "clock" });
    return;
  }
  els.matchStats.classList.remove("hidden");
  setEmpty(els.matchEmpty, false);
  els.statHero.textContent = live.hero || "—";
  els.statClock.textContent = formatClock(live.clockTime) || "—";
  els.statStage.textContent = live.stage && live.stage !== "unknown" ? stageLabel(live.stage) : "—";
  const seconds = Number.isFinite(live.secondsSinceLastGsi) ? live.secondsSinceLastGsi.toFixed(1) : null;
  const dot = document.createElement("span");
  dot.className = "dot";
  dot.dataset.tone = live.connected ? "ok" : "warn";
  const text = document.createElement("span");
  text.className = "num";
  text.textContent = seconds === null ? "—" : tr("dataFresh", seconds);
  els.statData.replaceChildren(dot, text);
}

function priorityTone(priority) {
  const value = String(priority || "").toLowerCase();
  if (value === "high" || value === "urgent") {
    return "error";
  }
  if (value === "medium") {
    return "warn";
  }
  if (value === "low" || value === "safe") {
    return "ok";
  }
  return "";
}

function renderAdvice(status) {
  if (isLoading(status)) {
    els.adviceEmpty.classList.add("hidden");
    els.adviceList.classList.remove("hidden");
    els.adviceList.replaceChildren(
      ...["w-80", "w-60", "w-70"].map((width) => {
        const item = document.createElement("li");
        item.className = "advice-item";
        item.append(skeleton(width));
        return item;
      })
    );
    return;
  }
  const items = Array.isArray(status.recentAdvice) ? status.recentAdvice : [];
  const offline = isOffline(status);
  if (offline || !items.length) {
    els.adviceList.classList.add("hidden");
    els.adviceList.replaceChildren();
    setEmpty(els.adviceEmpty, true, {
      title: offline ? tr("offlineTitle") : tr("adviceEmptyTitle"),
      hint: offline ? tr("offlineHint") : tr("adviceEmptyHint"),
      icon: offline ? "wifi-off" : "sparkles"
    });
    return;
  }
  els.adviceEmpty.classList.add("hidden");
  els.adviceList.classList.remove("hidden");
  const firstRender = seenAdvice.size === 0;
  els.adviceList.replaceChildren(
    ...items.map((advice) => {
      const key = `${advice.timestamp}|${advice.action}`;
      const item = document.createElement("li");
      item.className = "advice-item";
      if (!firstRender && !seenAdvice.has(key)) {
        item.classList.add("is-new");
      }
      seenAdvice.add(key);

      const dot = document.createElement("span");
      dot.className = "dot";
      const tone = priorityTone(advice.priority);
      if (tone) {
        dot.dataset.tone = tone;
      }
      const priority = String(advice.priority || "").toLowerCase();
      dot.title = trOr(`priority.${priority}`, priority);

      const action = document.createElement("span");
      action.className = "advice-action";
      action.textContent = advice.action || "";
      action.title = advice.action || "";

      const time = document.createElement("span");
      time.className = "advice-time";
      time.textContent = advice.game_time || "";

      const reason = document.createElement("span");
      reason.className = "advice-reason";
      reason.textContent = advice.reason || "";
      reason.title = advice.reason || "";

      item.append(dot, action, time, reason);
      return item;
    })
  );
}

function renderOverlaySettings(status) {
  const enabled = status.overlay === "running";
  els.overlayToggle.checked = enabled;
  els.overlayHint.textContent = !enabled
    ? tr("overlayReason.off")
    : status.overlayVisible
      ? tr("overlayReason.in_game")
      : tr(`overlayReason.${status.overlayReasonCode || "no_match"}`);

  const position = status.overlayPosition || "right-center";
  for (const button of els.positionButtons) {
    button.setAttribute("aria-checked", String(button.dataset.position === position));
    button.disabled = !enabled;
  }
  els.positionHint.textContent = position === "custom" ? tr("positionCustom") : tr("positionHint");

  const frequency = status.adviceFrequency || "normal";
  for (const button of els.frequencyButtons) {
    button.setAttribute("aria-checked", String(button.dataset.frequency === frequency));
  }
  els.frequencyHint.textContent = tr(`frequencyHint.${frequency}`);

  lastVoice = status.overlayVoice || { mode: "off", volume: 1 };
  for (const button of els.voiceButtons) {
    button.setAttribute("aria-checked", String(button.dataset.voice === lastVoice.mode));
    button.disabled = !enabled;
  }
  els.voiceTest.disabled = !enabled;
  renderVoiceHint(lastVoice);

  const moving = status.overlayLocked === false;
  els.moveToggle.setAttribute("aria-pressed", String(moving));
  els.moveToggle.disabled = !enabled;
  els.moveLabel.textContent = moving ? tr("moveDone") : tr("moveStart");
  els.moveHint.textContent = moving ? tr("moveActiveHint") : tr("moveHint");

  els.autostart.checked = Boolean(status.autostart);
  els.autostart.disabled = !status.autostartSupported;
  els.autostartHint.textContent = !status.autostartSupported
    ? tr("autostartUnavailable")
    : status.autostart
      ? tr("autostartOn")
      : tr("autostartOff");

  renderUpdate(status);
}

// The overlay speaks with the system voices; the panel only checks that one
// exists for the UI language and plays a sample.
function systemVoice() {
  return window.OverlayVoice && window.speechSynthesis
    ? window.OverlayVoice.pickVoice(window.speechSynthesis.getVoices(), locale)
    : null;
}

function renderVoiceHint(voice) {
  const mode = voice?.mode || "off";
  const found = systemVoice();
  if (mode !== "off" && !found && voiceListLoaded()) {
    els.voiceHint.textContent = tr("voiceNoVoice");
    return;
  }
  els.voiceHint.textContent = [tr(`voiceHint.${mode}`), mode !== "off" && found ? found.name : ""]
    .filter(Boolean)
    .join(" · ");
}

// Chromium fills the voice list asynchronously: an empty list right after
// start does not yet mean there are no voices.
function voiceListLoaded() {
  return (window.speechSynthesis?.getVoices() || []).length > 0 || voiceListChecked;
}

function testVoice() {
  const voice = systemVoice();
  if (!voice) {
    voiceListChecked = true;
    els.voiceHint.textContent = tr("voiceNoVoice");
    return;
  }
  const utterance = new window.SpeechSynthesisUtterance(tr("voiceSample"));
  utterance.voice = voice;
  utterance.lang = voice.lang;
  utterance.volume = Number(lastVoice.volume ?? 1);
  utterance.rate = 1.05;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

function renderUpdate(status) {
  const update = status.update || { status: "disabled" };
  const current = status.appVersion || update.currentVersion || "";
  const known = ["disabled", "idle", "checking", "up-to-date", "downloading", "ready", "error"];
  const state = known.includes(update.status) ? update.status : "idle";
  // Installing restarts the app, so it is never offered while Dota runs.
  const blocked = state === "ready" && Boolean(update.blockedByGame);
  const hintKey = blocked ? "blocked" : state;
  els.updateHint.textContent = tr(`updateHint.${hintKey}`, current, update.version || "", update.percent || 0);
  els.updateHint.title = state === "error" ? update.error || "" : "";
  const install = state === "ready";
  els.updateAction.dataset.mode = install ? "install" : "check";
  els.updateAction.classList.toggle("btn-primary", install);
  els.updateLabel.textContent = install ? tr("updateInstall") : tr("updateCheck");
  els.updateAction.disabled = blocked || state === "disabled" || state === "checking" || state === "downloading";
}

function renderFacts(status) {
  const backendPort = status.backendPort && status.backend !== "stopped" ? ` · :${status.backendPort}` : "";
  factEls.backend.textContent = `${tr(`serviceStates.${status.backend || "stopped"}`)}${backendPort}`;
  factEls.dota.textContent = tr(`dotaStates.${status.dota || "not_found"}`);
  factEls.overlay.textContent = status.overlay !== "running" ? tr("off") : status.overlayVisible ? tr("shown") : tr("hidden");
  factEls.overlay.title = status.overlayReason || "";
  factEls.demo.textContent = status.demo === "running"
    ? [tr("running"), status.demoPreset].filter(Boolean).join(" · ")
    : tr("stopped");
  factEls.recording.textContent = status.recording === "running" ? tr("running") : tr("stopped");
  factEls.gsi.textContent = tr(`gsiConfigStates.${status.gsiConfig || "unknown"}`);
  factEls.mode.textContent = trOr(`modes.${status.mode || "Live GSI"}`, status.mode || "Live GSI");
  factEls.llm.textContent = status.llm === "on" ? tr("on") : tr("off");
}

function isActiveProcess(state) {
  return state === "running" || state === "starting";
}

function renderControlButtons(status) {
  const backendRunning = isActiveProcess(status.backend);
  const overlayRunning = isActiveProcess(status.overlay);
  const demoRunning = isActiveProcess(status.demo);
  const recordingRunning = isActiveProcess(status.recording);

  controlButtons.startBackend.disabled = backendRunning;
  controlButtons.restartBackend.disabled = status.backend === "starting" || status.backend === "stopping";
  controlButtons.stopBackend.disabled = !backendRunning;
  controlButtons.startOverlay.disabled = overlayRunning;
  controlButtons.stopOverlay.disabled = !overlayRunning;
  controlButtons.stopDemo.disabled = !demoRunning;
  controlButtons.startRecording.disabled = recordingRunning;
  controlButtons.stopRecording.disabled = !recordingRunning;
  for (const button of demoStartButtons) {
    button.disabled = demoRunning;
    button.title = demoRunning ? tr("demoBusy") : "";
  }
}

function renderLogMode(mode) {
  for (const [name, button] of Object.entries(logModeButtons)) {
    button?.setAttribute("aria-checked", String(name === mode));
  }
}

function updateGsiDetail(result = {}) {
  if (result.path) {
    els.gsiDetail.textContent = tr("gsiPath", result.path, gsiEndpoint);
  } else if (result.status === "not found") {
    els.gsiDetail.textContent = `${tr("gsiPathMissing")}\n${tr("gsiEndpoint", gsiEndpoint)}`;
  } else {
    els.gsiDetail.textContent = tr("gsiEndpoint", gsiEndpoint);
  }
}

function renderLiveStatus(status = {}) {
  const setValue = (element, text, state) => {
    element.textContent = text;
    element.dataset.state = state || "";
  };
  if (status.error) {
    setValue(liveEls.connection, tr("liveUnavailable"), "bad");
    liveEls.advice.textContent = status.error;
    return;
  }
  setValue(liveEls.connection, status.gsi_connected ? tr("liveConnected") : tr("liveWaiting"), status.gsi_connected ? "good" : "bad");
  setValue(liveEls.last, status.seconds_since_last_gsi == null ? "—" : `${status.seconds_since_last_gsi} s`);
  setValue(liveEls.hero, status.hero || "—");
  setValue(liveEls.time, Number.isFinite(status.clock_time) ? formatClock(status.clock_time) : String(status.game_time ?? "—"));
  setValue(liveEls.stage, status.stage ? stageLabel(status.stage) : "—");
  liveEls.advice.textContent = status.current_advice
    ? tr("liveAdvice", status.current_advice)
    : status.last_advice_time
      ? tr("liveAdviceLast", status.last_advice_time)
      : tr("liveAdviceNone");
  const missing = Array.isArray(status.missing_important_fields) && status.missing_important_fields.length
    ? status.missing_important_fields.join(", ")
    : tr("none");
  liveEls.missing.textContent = tr("liveMissing", missing);
}

function renderLogs(logs) {
  els.logs.textContent = logs || "";
  els.logs.scrollTop = els.logs.scrollHeight;
}
