// Control panel: a simple status screen (Dota found, GSI connected, hero,
// match clock) plus a collapsed "For developers" section with every tool the
// launcher had before (backend, GSI config, live GSI, recordings, replay
// demos, Deep Review, logs). Texts follow the system language (ru/en).

const I18N = {
  en: {
    tagline: "Live advice for your Dota 2 matches",
    backend: "Backend",
    backendStates: { running: "running", starting: "starting…", stopping: "stopping…", stopped: "stopped" },
    bannerTitle: {
      in_game: "In game",
      waiting: "Waiting for a match",
      not_found: "Dota 2 is not running",
      starting: "Starting…",
      offline: "Backend is stopped"
    },
    bannerDetail: {
      in_game: "Advice appears over Dota while it is the active window.",
      waiting: "Dota 2 is running. Advice starts once a match with your hero begins.",
      not_found: "Start Dota 2 — the coach connects by itself. You can leave this window closed.",
      starting: "Starting the local coach service…",
      offline: "Open “For developers” below and press Start, or restart the app."
    },
    tileDota: "Dota 2",
    tileGsi: "Game data (GSI)",
    tileHero: "Hero",
    tileTime: "Match time",
    dotaRunningFocused: "Running",
    dotaRunningBackground: "Running in background",
    dotaInstalled: "Installed",
    dotaNotFound: "Not found",
    dotaNotFoundSub: "No Dota 2 in your Steam libraries. Install it or pick the folder under “For developers”.",
    gsiConnected: "Connected",
    gsiWaiting: "Waiting for data",
    gsiNotInstalled: "Not set up",
    gsiError: "Could not write config",
    gsiLastData: (s) => `Last data ${s} s ago`,
    gsiWaitingSub: "Dota sends data once it is running. Restart Dota if it was open while the config was installed.",
    gsiNotInstalledSub: "Dota needs a small config file to share game data with the coach.",
    installGsi: "Install config",
    heroNone: "—",
    heroSubIdle: "Shown once a match starts",
    stage: (s) => `Stage: ${s}`,
    timeSubIdle: "In-game clock",
    timeSubLive: "In-game clock, live",
    overlaySwitch: "Advice overlay",
    overlayOnScreen: "On screen now",
    overlayOff: "Off — no advice over the game",
    overlayReason: {
      positioning: "Unlocked for dragging — press Ctrl+Alt+L to lock",
      demo: "Showing the replay demo",
      no_tracking: "Always visible (focus tracking unavailable)",
      dota_not_running: "Appears in a match, over Dota",
      dota_not_focused: "Hidden while Dota is in the background",
      no_match: "Appears when a match starts",
      in_game: "On screen now"
    },
    autostart: "Start with Windows",
    autostartOn: "Starts hidden in the tray",
    autostartOff: "Start it yourself when you play",
    autostartUnavailable: "Available in the installed app",
    devTitle: "For developers",
    devHint: "Backend, GSI details, replay demos, recordings and logs",
    factBackend: "Backend",
    factDota: "Dota",
    factOverlay: "Overlay",
    factDemo: "Demo",
    factRecording: "Recording",
    factGsiConfig: "GSI config",
    factMode: "Mode",
    groupBackend: "Backend",
    startBackend: "Start",
    restartBackend: "Restart",
    stopBackend: "Stop",
    groupOverlay: "Overlay window",
    showOverlay: "Show",
    hideOverlay: "Hide",
    hotkeys: "Ctrl+Alt+O on/off · Ctrl+Alt+L unlock to drag · Ctrl+Alt+M mute 5 min · Ctrl+Alt+1/2/3 position · Ctrl+Alt+D debug line",
    groupGsi: "GSI config",
    gsiPathPlaceholder: "Custom gamestate_integration folder",
    chooseFolder: "Choose",
    checkGsi: "Check",
    installGsiHere: "Install here",
    gsiPath: (p, e) => `Config: ${p}${e ? ` → ${e}` : ""}`,
    gsiPathMissing: "Config not found. Pick the gamestate_integration folder and install.",
    gsiEndpoint: (e) => (e ? `Endpoint: ${e}` : "Endpoint: waiting for the backend port…"),
    groupLive: "Live GSI",
    kvConnection: "Connection",
    kvLast: "Last data",
    kvHero: "Hero",
    kvTime: "Game time",
    kvStage: "Stage",
    liveConnected: "connected",
    liveWaiting: "waiting / stale",
    liveUnavailable: "backend unavailable",
    liveAdvice: (a) => `Current advice: ${a}`,
    liveAdviceNone: "Current advice: none yet",
    liveAdviceLast: (t) => `Current advice: last shown at ${t}`,
    liveMissing: (m) => `Missing important fields: ${m}`,
    none: "none",
    checkLive: "Check live GSI",
    startRecording: "Start recording",
    stopRecording: "Stop recording",
    openRecords: "Recordings folder",
    groupDemo: "Replay demo",
    demoHint: "Plays recorded match states into the backend; the overlay shows without Dota.",
    demoBusy: "A demo is already running. Stop it before starting another one.",
    runDemo: "Run demo",
    presetPl: "Phantom Lancer 20–30",
    presetJugg: "Juggernaut 10–20",
    deepReview: "Deep Review",
    stopDemo: "Stop demo",
    openResults: "Results folder",
    groupLogs: "Logs",
    logClean: "Clean",
    logVerbose: "Verbose",
    copyLogs: "Copy",
    clearLogs: "Clear",
    openLogs: "Logs folder",
    dotaStates: { not_found: "not found", waiting: "waiting for a match", in_game: "in game" },
    gsiConfigStates: { installed: "installed", "not found": "not found", error: "error", unknown: "unknown" },
    on: "on",
    off: "off",
    shown: "on screen",
    hidden: "hidden",
    running: "running",
    stopped: "stopped",
    unknown: "unknown"
  },
  ru: {
    tagline: "Подсказки в реальном времени для матчей Dota 2",
    backend: "Сервис",
    backendStates: { running: "работает", starting: "запускается…", stopping: "останавливается…", stopped: "остановлен" },
    bannerTitle: {
      in_game: "В игре",
      waiting: "Ждём игру",
      not_found: "Дота не найдена",
      starting: "Запуск…",
      offline: "Сервис остановлен"
    },
    bannerDetail: {
      in_game: "Подсказки появляются поверх Доты, пока её окно активно.",
      waiting: "Dota 2 запущена. Подсказки начнутся, когда стартует матч с вашим героем.",
      not_found: "Запустите Dota 2 — тренер подключится сам. Это окно можно закрыть.",
      starting: "Запускаем локальный сервис тренера…",
      offline: "Откройте «Для разработчика» ниже и нажмите «Запустить» или перезапустите приложение."
    },
    tileDota: "Dota 2",
    tileGsi: "Данные игры (GSI)",
    tileHero: "Герой",
    tileTime: "Время матча",
    dotaRunningFocused: "Запущена",
    dotaRunningBackground: "Запущена в фоне",
    dotaInstalled: "Установлена",
    dotaNotFound: "Не найдена",
    dotaNotFoundSub: "Dota 2 нет в библиотеках Steam. Установите её или укажите папку в разделе «Для разработчика».",
    gsiConnected: "Подключено",
    gsiWaiting: "Ждём данные",
    gsiNotInstalled: "Не настроено",
    gsiError: "Не удалось записать конфиг",
    gsiLastData: (s) => `Данные ${s} с назад`,
    gsiWaitingSub: "Дота начнёт присылать данные после запуска. Если она была открыта во время установки конфига — перезапустите её.",
    gsiNotInstalledSub: "Доте нужен небольшой конфиг, чтобы передавать данные игры тренеру.",
    installGsi: "Установить конфиг",
    heroNone: "—",
    heroSubIdle: "Появится, когда начнётся матч",
    stage: (s) => `Стадия: ${s}`,
    timeSubIdle: "Игровые часы",
    timeSubLive: "Игровые часы, в реальном времени",
    overlaySwitch: "Оверлей с подсказками",
    overlayOnScreen: "Сейчас на экране",
    overlayOff: "Выключен — подсказок поверх игры нет",
    overlayReason: {
      positioning: "Разблокирован для перетаскивания — Ctrl+Alt+L, чтобы закрепить",
      demo: "Показывает демо-повтор",
      no_tracking: "Всегда виден (отслеживание фокуса недоступно)",
      dota_not_running: "Появится в матче поверх Доты",
      dota_not_focused: "Скрыт, пока Дота в фоне",
      no_match: "Появится, когда начнётся матч",
      in_game: "Сейчас на экране"
    },
    autostart: "Автозапуск с Windows",
    autostartOn: "Запускается скрыто в трее",
    autostartOff: "Запускайте сами перед игрой",
    autostartUnavailable: "Доступно в установленном приложении",
    devTitle: "Для разработчика",
    devHint: "Сервис, детали GSI, демо-повторы, записи и логи",
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
    groupOverlay: "Окно оверлея",
    showOverlay: "Показать",
    hideOverlay: "Скрыть",
    hotkeys: "Ctrl+Alt+O вкл/выкл · Ctrl+Alt+L разблокировать · Ctrl+Alt+M тишина 5 мин · Ctrl+Alt+1/2/3 позиция · Ctrl+Alt+D отладка",
    groupGsi: "Конфиг GSI",
    gsiPathPlaceholder: "Своя папка gamestate_integration",
    chooseFolder: "Выбрать",
    checkGsi: "Проверить",
    installGsiHere: "Установить сюда",
    gsiPath: (p, e) => `Конфиг: ${p}${e ? ` → ${e}` : ""}`,
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
    checkLive: "Проверить GSI",
    startRecording: "Начать запись",
    stopRecording: "Остановить запись",
    openRecords: "Папка записей",
    groupDemo: "Демо-повтор",
    demoHint: "Проигрывает записанные состояния матча в сервис; оверлей виден без Доты.",
    demoBusy: "Демо уже идёт. Остановите его, чтобы запустить другое.",
    runDemo: "Запустить демо",
    presetPl: "Phantom Lancer 20–30",
    presetJugg: "Juggernaut 10–20",
    deepReview: "Deep Review",
    stopDemo: "Остановить демо",
    openResults: "Папка результатов",
    groupLogs: "Логи",
    logClean: "Кратко",
    logVerbose: "Подробно",
    copyLogs: "Копировать",
    clearLogs: "Очистить",
    openLogs: "Папка логов",
    dotaStates: { not_found: "не найдена", waiting: "ждём игру", in_game: "в игре" },
    gsiConfigStates: { installed: "установлен", "not found": "не найден", error: "ошибка", unknown: "неизвестно" },
    on: "вкл",
    off: "выкл",
    shown: "на экране",
    hidden: "скрыт",
    running: "идёт",
    stopped: "остановлено",
    unknown: "неизвестно"
  }
};

const $ = (selector) => document.querySelector(selector);
const logsEl = $("#logs");
const gsiPathEl = $("#gsi-path");
const gsiDetailEl = $("#gsi-detail");
const devToolsEl = $("#dev-tools");
const overlayToggleEl = $("#overlay-toggle");
const autostartEl = $("#autostart");
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

let locale = "en";
let textsLocale = "";
let gsiEndpoint = "";
const DEV_OPEN_KEY = "dota-ai-coach.devToolsOpen";

init();

function tr(key, ...args) {
  const value = key.split(".").reduce((node, part) => (node ? node[part] : undefined), I18N[locale]);
  const fallback = key.split(".").reduce((node, part) => (node ? node[part] : undefined), I18N.en);
  const resolved = value ?? fallback ?? key;
  return typeof resolved === "function" ? resolved(...args) : resolved;
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
}

async function init() {
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
  bind("#install-gsi", () => installGsi(""));
  bind("#install-gsi-custom", () => installGsi(gsiPathEl.value));
  bind("#choose-gsi", chooseGsiFolder);
  bind("#check-live-gsi", checkLiveGsi);
  bind("#start-recording", startLiveRecording);
  bind("#stop-recording", stopLiveRecording);
  bind("#open-records", () => window.launcherApi.openSessionRecords());

  overlayToggleEl.addEventListener("change", () =>
    run(() => (overlayToggleEl.checked ? window.launcherApi.startOverlay() : window.launcherApi.stopOverlay()))
  );
  autostartEl.addEventListener("change", () =>
    run(async () => {
      await window.launcherApi.setAutostart(autostartEl.checked);
      renderStatus(await window.launcherApi.getStatus());
    })
  );

  // Remember whether the developer section was open (per-user convenience).
  try {
    devToolsEl.open = localStorage.getItem(DEV_OPEN_KEY) === "1";
  } catch {
    // Storage unavailable: start collapsed.
  }
  devToolsEl.addEventListener("toggle", () => {
    try {
      localStorage.setItem(DEV_OPEN_KEY, devToolsEl.open ? "1" : "0");
    } catch {
      // Ignore.
    }
  });

  window.launcherApi.onStatus(renderStatus);
  window.launcherApi.onLogs(renderLogs);

  renderStatus(await window.launcherApi.getStatus());
  renderLogs(await window.launcherApi.getLogs());
}

async function run(handler) {
  try {
    await handler();
  } catch (error) {
    renderLogs(`${logsEl.textContent || ""}\n[renderer] ${error.message || error}\n`);
  }
}

function bind(selector, handler) {
  const element = $(selector);
  if (element) {
    element.addEventListener("click", () => run(handler));
  }
}

async function checkGsi() {
  updateGsiDetail(await window.launcherApi.checkGsi(gsiPathEl.value));
}

async function installGsi(customPath) {
  updateGsiDetail(await window.launcherApi.installGsi(customPath));
}

async function chooseGsiFolder() {
  const folder = await window.launcherApi.chooseGsiFolder();
  if (folder) {
    gsiPathEl.value = folder;
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
// Status screen
// ---------------------------------------------------------------------------

function renderStatus(status = {}) {
  if (status.locale && status.locale !== locale) {
    locale = I18N[status.locale] ? status.locale : "en";
  }
  applyStaticTexts();
  gsiEndpoint = status.gsiEndpoint || "";

  renderBackendPill(status);
  renderBanner(status);
  renderDotaTile(status);
  renderGsiTile(status);
  renderMatchTiles(status);
  renderSwitches(status);
  renderFacts(status);
  renderControlButtons(status);
  renderLogMode(status.logMode || "clean");
  updateGsiDetail({ status: status.gsiConfig, path: status.gsiPath });
}

function screenState(status) {
  if (status.backend === "starting") {
    return "starting";
  }
  if (status.backend !== "running") {
    return "offline";
  }
  return ["in_game", "waiting", "not_found"].includes(status.dota) ? status.dota : "not_found";
}

function renderBackendPill(status) {
  const pill = $("#backend-pill");
  pill.dataset.state = status.backend || "stopped";
  const port = status.backendPort && status.backend === "running" ? ` · 127.0.0.1:${status.backendPort}` : "";
  $("#backend-pill-text").textContent = `${tr("backend")}: ${tr(`backendStates.${status.backend || "stopped"}`)}${port}`;
}

function renderBanner(status) {
  const state = screenState(status);
  $("#state-banner").dataset.state = state;
  $("#state-title").textContent = tr(`bannerTitle.${state}`);
  $("#state-detail").textContent = tr(`bannerDetail.${state}`);
}

function setTile(id, state, value, sub) {
  const tile = $(`#tile-${id}`);
  tile.dataset.state = state;
  tile.querySelector(".tile-value").textContent = value;
  tile.querySelector(".tile-sub").textContent = sub || "";
}

function renderDotaTile(status) {
  if (status.dotaRunning) {
    setTile(
      "dota",
      "good",
      status.dotaFocused ? tr("dotaRunningFocused") : tr("dotaRunningBackground"),
      status.dotaDir || ""
    );
  } else if (status.dotaDir) {
    setTile("dota", "wait", tr("dotaInstalled"), status.dotaDir);
  } else {
    setTile("dota", "bad", tr("dotaNotFound"), tr("dotaNotFoundSub"));
  }
}

function renderGsiTile(status) {
  const live = status.live || {};
  const installButton = $("#install-gsi");
  const installed = status.gsiConfig === "installed";
  installButton.classList.toggle("hidden", installed || live.connected);
  if (live.connected) {
    const seconds = Number.isFinite(live.secondsSinceLastGsi) ? live.secondsSinceLastGsi.toFixed(1) : "0";
    setTile("gsi", "good", tr("gsiConnected"), tr("gsiLastData", seconds));
  } else if (installed) {
    setTile("gsi", "wait", tr("gsiWaiting"), tr("gsiWaitingSub"));
  } else if (status.gsiConfig === "error") {
    setTile("gsi", "bad", tr("gsiError"), status.gsiPath || "");
  } else {
    setTile("gsi", "bad", tr("gsiNotInstalled"), tr("gsiNotInstalledSub"));
  }
}

function formatClock(seconds) {
  if (!Number.isFinite(seconds)) {
    return "—";
  }
  const sign = seconds < 0 ? "-" : "";
  const total = Math.abs(Math.trunc(seconds));
  return `${sign}${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

function renderMatchTiles(status) {
  const live = status.live || {};
  const inMatch = Boolean(live.inMatch);
  if (inMatch && live.hero) {
    const stage = live.stage && live.stage !== "unknown" ? tr("stage", live.stage) : "";
    setTile("hero", "good", live.hero, stage);
  } else {
    setTile("hero", "idle", tr("heroNone"), tr("heroSubIdle"));
  }
  if (inMatch && Number.isFinite(live.clockTime)) {
    setTile("time", "good", formatClock(live.clockTime), tr("timeSubLive"));
  } else {
    setTile("time", "idle", "—", tr("timeSubIdle"));
  }
}

function renderSwitches(status) {
  const enabled = status.overlay === "running";
  overlayToggleEl.checked = enabled;
  let overlaySub = tr("overlayOff");
  if (enabled) {
    overlaySub = status.overlayVisible
      ? tr("overlayOnScreen")
      : tr(`overlayReason.${status.overlayReasonCode || "no_match"}`);
  }
  $("#overlay-sub").textContent = overlaySub;

  autostartEl.checked = Boolean(status.autostart);
  autostartEl.disabled = !status.autostartSupported;
  $("#autostart-label").textContent = !status.autostartSupported
    ? tr("autostartUnavailable")
    : status.autostart
      ? tr("autostartOn")
      : tr("autostartOff");
}

function renderFacts(status) {
  const backendPort = status.backendPort && status.backend !== "stopped" ? ` · :${status.backendPort}` : "";
  factEls.backend.textContent = `${tr(`backendStates.${status.backend || "stopped"}`)}${backendPort}`;
  factEls.dota.textContent = tr(`dotaStates.${status.dota || "not_found"}`);
  factEls.overlay.textContent = status.overlay !== "running" ? tr("off") : status.overlayVisible ? tr("shown") : tr("hidden");
  factEls.overlay.title = status.overlayReason || "";
  factEls.demo.textContent = status.demo === "running" && status.demoPreset
    ? `${tr("running")} · ${status.demoPreset}`
    : status.demo === "running" ? tr("running") : tr("stopped");
  factEls.recording.textContent = status.recording === "running" ? tr("running") : tr("stopped");
  factEls.gsi.textContent = tr(`gsiConfigStates.${status.gsiConfig || "unknown"}`);
  factEls.mode.textContent = status.mode || "Live GSI";
  factEls.llm.textContent = status.llm === "on" ? tr("on") : tr("off");
}

function isActiveProcess(state) {
  return state === "running" || state === "starting";
}

function setActionEnabled(button, enabled) {
  if (button) {
    button.disabled = !enabled;
  }
}

function renderControlButtons(status = {}) {
  const backendRunning = isActiveProcess(status.backend);
  const overlayRunning = isActiveProcess(status.overlay);
  const demoRunning = isActiveProcess(status.demo);
  const recordingRunning = isActiveProcess(status.recording);

  setActionEnabled(controlButtons.startBackend, !backendRunning);
  setActionEnabled(controlButtons.restartBackend, status.backend !== "starting" && status.backend !== "stopping");
  setActionEnabled(controlButtons.stopBackend, backendRunning);
  setActionEnabled(controlButtons.startOverlay, !overlayRunning);
  setActionEnabled(controlButtons.stopOverlay, overlayRunning);
  setActionEnabled(controlButtons.stopDemo, demoRunning);
  setActionEnabled(controlButtons.startRecording, !recordingRunning);
  setActionEnabled(controlButtons.stopRecording, recordingRunning);
  for (const button of demoStartButtons) {
    button.disabled = demoRunning;
    button.title = demoRunning ? tr("demoBusy") : "";
  }
}

function renderLogMode(mode) {
  for (const [name, button] of Object.entries(logModeButtons)) {
    button?.classList.toggle("active", name === mode);
  }
}

function updateGsiDetail(result = {}) {
  const lines = [];
  if (result.path) {
    lines.push(tr("gsiPath", result.path, gsiEndpoint));
  } else if (result.status === "not found") {
    lines.push(tr("gsiPathMissing"));
  }
  if (!result.path) {
    lines.push(tr("gsiEndpoint", gsiEndpoint));
  }
  gsiDetailEl.textContent = lines.join("\n");
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
  setValue(liveEls.stage, status.stage || "—");
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
  logsEl.textContent = logs || "";
  logsEl.scrollTop = logsEl.scrollHeight;
}
