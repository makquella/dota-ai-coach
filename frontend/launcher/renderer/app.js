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
    languageTitle: "Language",
    languageHint: "Advice, reviews and the whole app",
    languageAuto: "Auto",
    dataTitle: "Match data",
    odTitle: "OpenDota key (optional)",
    odPlaceholder: "API key",
    odSave: "Save",
    odGet: "Get a key on opendota.com",
    odClear: "Remove key",
    odHintOff: "Without a key OpenDota allows about 60 requests a minute, so history loads slower. The key stays on this computer.",
    odHintOn: (hint) => `Key ${hint} saved: history and replays load faster.`,
    odHintEnv: "The key from the .env file is used.",
    odBad: "This does not look like an OpenDota key.",
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
      launchOptionTitle: "Dota is not sending game data",
      launchOptionHint: "Add -gamestateintegration to Dota 2 launch options (Steam → Dota 2 → Properties → Launch options), then restart the game.",
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
      fullscreenSeen: "I can see the advice",
      copyLaunchOption: "Copy option",
      copied: "Copied"
    },
    matchTitle: "Current match",
    coverageSafety: "Farm and item advice is for carry heroes; on this hero the coach gives survival advice, map timers and role tips.",
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
    overlaySize: "Card size",
    overlaySizeHint: "Larger on big and high-resolution screens",
    sizeSmall: "Small",
    sizeNormal: "Normal",
    sizeLarge: "Large",
    frequencyTitle: "How often",
    frequencyCalm: "Less",
    frequencyNormal: "Normal",
    frequencyActive: "More",
    weekTitle: "This week",
    roleTitle: "Your role",
    roleAuto: "Auto",
    roleCarry: "Carry",
    roleMid: "Mid",
    roleOfflane: "Offlane",
    roleSupport: "Support",
    roleHint: {
      auto: "Found from your lane in the first minutes; timers and tips follow it",
      carry: "Timers and tips for a carry",
      mid: "Runes and timers for a mid player",
      offlane: "Shrines, lotuses and timers for an offlaner",
      support: "Stacks, wards and runes for a support; farm advice is off"
    },
    roleNames: { carry: "carry", mid: "mid", offlane: "offlane", support: "support" },
    roleSource: {
      setting: "chosen in Settings",
      lane: "from your lane",
      history: "from your past games on this hero",
      hero: "usual for this hero"
    },
    roleNote: (role, source) => `Role: ${role}, ${source}.`,
    mapHintsTitle: "Map timers",
    mapHintsHint: "Runes, shrines, Tormentor, stacks and wards 20 s ahead, on the overlay card",
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
      urgent: "Speaks urgent advice; heard even in exclusive fullscreen. Ctrl+Alt+R repeats",
      all: "Speaks every piece of advice; heard even in exclusive fullscreen. Ctrl+Alt+R repeats"
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
    whatsNewTitle: (version) => `What's new in ${version}`,
    whatsNewOk: "Got it",
    whatsNew: {
      "0.7.0": [
        "Progress → Share: a link to a page with your progress — matches, wins, averages, top heroes, what goes well and what to work on.",
        "A new start-up splash: the logo comes alive while the service starts."
      ],
      "0.6.1": [
        "Offlaner reviews: stuns and building damage against the enemy offlaner of the same match.",
        "The plan for the game shows your record on the hero next to its name.",
        "All versions and their changes are on the website: luhovyimvp.dev/changelog.html."
      ],
      "0.6.0": [
        "Role reviews: runes for a mid against the enemy mid, stacks and sentries for a support.",
        "Progress: your record against each enemy hero — who is hardest for you and whom you beat most.",
        "Ask the AI coach about your recent matches, not only one game.",
        "In game: a level-6 tip for a mid (rotation) and an offlaner (pressure)."
      ],
      "0.5.0": [
        "Dota AI Coach is now Wardly, with a new logo. Your history and settings stay.",
        "Progress → Compare with a friend: their public matches next to yours, with the heroes you both play.",
        "Share a review by link — with a preview in Discord and Telegram, no Steam ID or nickname.",
        "Settings → App → Match history: save everything to a file and load it back on any computer.",
        "The path on the match map no longer runs from a death to the fountain."
      ],
      "0.4.0": [
        "The match map is drawn on the real Dota minimap: your path, lane position, wards and deaths.",
        "Good-pace lines for gold and XP on the «Over the match» chart.",
        "A «Deaths» card: where, who killed you, unspent gold and the advice shown before each death.",
        "Mistakes that keep coming back are marked: «3 matches in a row».",
        "This week on Home: matches, score change, best match, the most frequent mistake and a 3-match plan for your focus."
      ],
      "0.3.0": [
        "Map timers on the overlay 20 s ahead: runes, wisdom shrines, lotuses, the Tormentor, neutral item tiers — only the ones your role needs.",
        "Your role is found from your lane in the first minutes (or chosen in Settings → Advice) and shown on Home.",
        "Support tips: stack a camp, take wards, leave the last hits to your carry. No carry farm advice on a support; the TP reminder works on every hero.",
        "«Send to developer» in the problem report: one click, with a note and a preview; keys, nickname and Steam ID are removed.",
        "Draft advice suggests only heroes of the position you played."
      ],
      "0.2.1": [
        "Match history no longer fails to sync when OpenDota answers slowly.",
        "The app asks OpenDota to parse your latest matches, so reviews get last hits at 10:00, the build and the chart.",
        "Draft advice suggests a hero of your role; the same-role opponent and counter items are right even without a parsed replay.",
        "Progress shows all five tiles in one row, and Home no longer cuts the hero's name."
      ],
      "0.2.0": [
        "A plan at the start of each match, and a focus: pick one mistake to work on — every review says whether you avoided it.",
        "«Ask the coach»: your own question about a match, answered from its data.",
        "Spoken advice, advice frequency, survival advice for every hero, reminders to carry a TP scroll and to spend gold while dead.",
        "Match map, this match against your usual numbers, match filters and PDF export.",
        "A check for Dota's -gamestateintegration launch option, without which no game data arrives."
      ]
    },
    setupTitle: "Getting started",
    setupHide: "Hide",
    setupCount: (done, total) => `${done} of ${total}`,
    setup: {
      service: ["The coach service is running", "Starts with the app; restart it in Settings → «For developers» if it stopped."],
      dota: ["Dota 2 found", "Not in your Steam libraries: point to the game folder."],
      gsi: ["Game data config installed", "A small file in the Dota folder that lets the game share match data."],
      launch: ["Launch option -gamestateintegration", "Without it Dota does not share game data. Steam → Dota 2 → Properties → Launch options: add -gamestateintegration."],
      data: ["First data from Dota received", "Start Dota 2 (or restart it after installing the config) and open any match, bots are fine."],
      account: ["Steam account linked", "Linked by itself in the first match, or enter it on the Matches tab."],
      ai: ["AI coach (optional)", "A free Gemini key writes a coach review of every match."]
    },
    setupActions: { dota: "Choose folder", gsi: "Install", launch: "Copy", account: "Link", ai: "Set up" },
    reportTitle: "Problem report",
    reportHint: "Logs and settings for the developer, without keys",
    reportSave: "Save file",
    backupTitle: "Match history",
    backupHint: "Every match, review and AI answer in one file: to keep a copy or move to another computer. Keys are not saved.",
    backupExport: "Save to file",
    backupImport: "Load from file",
    backupSaved: (count, file) => `Saved ${count} matches: ${file}`,
    backupLoaded: (added, linked) => `Loaded: ${added} new matches${linked ? ", account linked" : ""}. Nothing was overwritten.`,
    backupNotBackup: "This file is not a Wardly history backup.",
    backupNewer: "The backup was made by a newer version: update the app first.",
    backupFailed: "Could not do it: the service is not running or the disk is not available.",
    reportSaving: "Collecting…",
    reportSaved: (name) => `Saved: ${name}. Send this file to the developer.`,
    reportFailed: "Could not save the file",
    reportSend: "Send to developer",
    reportNoteLabel: "What happened? (optional)",
    reportNotePlaceholder: "For example: the overlay does not show in a match",
    reportPreview: "What will be sent",
    reportPreviewLoading: "Collecting the report…",
    reportTerms: "API keys are removed. The report is kept for 180 days.",
    reportPrivacy: "Privacy",
    reportSendNow: "Send",
    reportCancel: "Cancel",
    reportSending: "Sending…",
    reportSentId: (id) => `Sent. Report number: ${id}. Mention it if you write to the developer.`,
    reportQueued: "No connection to the service. The report will be sent automatically later.",
    reportQueuedCount: (count) => `Waiting to be sent: ${count}`,
    reportLast: (id) => `Last report: ${id}`,
    reportRefused: (name) =>
      name ? `The service did not accept the report. Saved a file instead: ${name}.` : "The service did not accept the report.",
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
    hotkeys: "Ctrl+Alt+O on/off · Ctrl+Alt+L move · Ctrl+Alt+M mute 5 min · Ctrl+Alt+R repeat advice · Ctrl+Alt+1/2/3 left/right/bottom · Ctrl+Alt+D debug line",
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
    languageTitle: "Язык",
    languageHint: "Советы, разборы и всё приложение",
    languageAuto: "Как в системе",
    dataTitle: "Данные матчей",
    odTitle: "Ключ OpenDota (по желанию)",
    odPlaceholder: "Ключ API",
    odSave: "Сохранить",
    odGet: "Получить ключ на opendota.com",
    odClear: "Удалить ключ",
    odHintOff: "Без ключа OpenDota даёт около 60 запросов в минуту, история загружается медленнее. Ключ хранится только на этом компьютере.",
    odHintOn: (hint) => `Ключ ${hint} сохранён: история и разборы грузятся быстрее.`,
    odHintEnv: "Используется ключ из файла .env.",
    odBad: "Это не похоже на ключ OpenDota.",
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
      launchOptionTitle: "Дота не передаёт данные игры",
      launchOptionHint: "Добавьте -gamestateintegration в параметры запуска Dota 2 (Steam → Dota 2 → Свойства → Параметры запуска) и перезапустите игру.",
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
      fullscreenSeen: "Подсказки видны",
      copyLaunchOption: "Скопировать параметр",
      copied: "Скопировано"
    },
    matchTitle: "Текущий матч",
    coverageSafety: "Советы по фарму и предметам — для керри; на этом герое тренер подсказывает по выживанию, таймерам карты и роли.",
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
    overlaySize: "Размер карточки",
    overlaySizeHint: "Крупнее — для больших экранов и высокого разрешения",
    sizeSmall: "Мелкий",
    sizeNormal: "Обычный",
    sizeLarge: "Крупный",
    frequencyTitle: "Частота советов",
    frequencyCalm: "Реже",
    frequencyNormal: "Обычно",
    frequencyActive: "Чаще",
    weekTitle: "Неделя",
    roleTitle: "Ваша роль",
    roleAuto: "Авто",
    roleCarry: "Керри",
    roleMid: "Мид",
    roleOfflane: "Хардлайн",
    roleSupport: "Саппорт",
    roleHint: {
      auto: "Определяется по линии в первые минуты; по ней выбираются таймеры и подсказки",
      carry: "Таймеры и подсказки для керри",
      mid: "Руны и таймеры для мидера",
      offlane: "Святилища, лотосы и таймеры для хардлайнера",
      support: "Стаки, варды и руны для саппорта; советы про фарм выключены"
    },
    roleNames: { carry: "керри", mid: "мид", offlane: "хардлайн", support: "саппорт" },
    roleSource: {
      setting: "выбрана в настройках",
      lane: "по линии",
      history: "по вашим прошлым играм на герое",
      hero: "обычная для героя"
    },
    roleNote: (role, source) => `Роль: ${role}, ${source}.`,
    mapHintsTitle: "Таймеры карты",
    mapHintsHint: "Руны, святилища, Торментор, стаки и варды за 20 с — на карточке оверлея",
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
      urgent: "Озвучивает срочные советы; слышно даже в полноэкранном режиме. Ctrl+Alt+R — повторить",
      all: "Озвучивает все советы; слышно даже в полноэкранном режиме. Ctrl+Alt+R — повторить"
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
    whatsNewTitle: (version) => `Что нового в ${version}`,
    whatsNewOk: "Понятно",
    whatsNew: {
      "0.7.0": [
        "«Прогресс» → «Поделиться»: ссылка на страницу с вашим прогрессом — матчи, победы, средние цифры, главные герои, что получается и над чем работать.",
        "Новая заставка при запуске: логотип оживает, пока запускается служба."
      ],
      "0.6.1": [
        "Разбор хардлайнера: оглушения и урон по строениям против вражеского хардлайнера того же матча.",
        "В плане на игру рядом с героем — ваш счёт на нём.",
        "Все версии и что в них изменилось — на сайте: luhovyimvp.dev/changelog.html."
      ],
      "0.6.0": [
        "Разбор под роль: руны мида против вражеского мида, стаки и сентри саппорта.",
        "«Прогресс»: ваш счёт против каждого вражеского героя — кто неудобен и кого вы обыгрываете.",
        "ИИ-тренеру можно задать вопрос о всех последних матчах, а не только об одном.",
        "В игре: подсказка на 6-м уровне для мида (ротация) и оффлейна (давление)."
      ],
      "0.5.0": [
        "Dota AI Coach теперь называется Wardly, у него новый логотип. История и настройки на месте.",
        "«Прогресс» → «Сравнение с другом»: его открытые матчи рядом с вашими и общие герои.",
        "Разбор можно отправить ссылкой — с превью в Discord и Telegram, без Steam ID и ника.",
        "«Настройки → Приложение → История матчей»: сохранить всё в файл и загрузить на любом компьютере.",
        "Путь на карте матча больше не тянется от места смерти к фонтану."
      ],
      "0.4.0": [
        "Карта матча нарисована на настоящей миникарте Доты: ваш путь, позиция на линии, варды и смерти.",
        "На графике «По ходу матча» — хороший темп по золоту и опыту.",
        "Карточка «Смерти»: где, кто убил, сколько золота не потрачено и какая была подсказка перед смертью.",
        "Повторяющиеся ошибки отмечены: «3-й матч подряд».",
        "Неделя на главной: матчи, изменение оценки, лучший матч, частая ошибка и план на 3 матча по фокусу."
      ],
      "0.3.0": [
        "Таймеры карты на оверлее за 20 секунд: руны, святилища мудрости, лотосы, Торментор, уровни нейтральных предметов — только нужные вашей роли.",
        "Роль определяется по линии в первые минуты (или выбирается в «Настройки → Советы») и видна на главной.",
        "Подсказки саппорту: застакать лагерь, взять варды, оставить добивания керри. Советы про фарм на саппорте выключены; про ТП — на любом герое.",
        "«Отправить разработчику» в отчёте о проблеме: одна кнопка, комментарий и предпросмотр; ключи, ник и Steam ID вырезаются.",
        "Драфт предлагает только героев той позиции, на которой вы играли."
      ],
      "0.2.1": [
        "История матчей больше не срывается, когда OpenDota отвечает медленно.",
        "Приложение само просит OpenDota разобрать последние матчи — в разборе появляются добивания к 10:00, сборка и график.",
        "Драфт советует героя вашей роли; соперник по роли и предметы против врагов определяются верно и без разбора реплея.",
        "На «Прогрессе» все пять плиток в одну строку, на главной не обрезается имя героя."
      ],
      "0.2.0": [
        "План на игру в начале матча и фокус: выберите одну ошибку — в каждом разборе видно, получилось ли её избежать.",
        "«Спросить тренера»: свой вопрос о матче, ответ по его данным.",
        "Голос, частота советов, советы по выживанию на любом герое, напоминания носить TP и тратить золото после смерти.",
        "Карта матча, сравнение с вашими обычными цифрами, фильтры матчей и сохранение в PDF.",
        "Проверка параметра запуска -gamestateintegration, без которого Дота не передаёт данные."
      ]
    },
    setupTitle: "Первый запуск",
    setupHide: "Скрыть",
    setupCount: (done, total) => `${done} из ${total}`,
    setup: {
      service: ["Сервис тренера запущен", "Запускается вместе с приложением; если остановился, перезапустите в «Настройки → Для разработчика»."],
      dota: ["Dota 2 найдена", "Игры нет в библиотеках Steam — укажите папку игры."],
      gsi: ["Конфиг данных игры установлен", "Небольшой файл в папке Доты, через который игра передаёт данные матча."],
      launch: ["Параметр запуска -gamestateintegration", "Без него Дота не передаёт данные. Steam → Dota 2 → Свойства → Параметры запуска: добавьте -gamestateintegration."],
      data: ["Первые данные из Доты получены", "Запустите Dota 2 (или перезапустите после установки конфига) и зайдите в любой матч, можно с ботами."],
      account: ["Аккаунт Steam привязан", "Привяжется сам в первом матче, или укажите его на вкладке «Матчи»."],
      ai: ["ИИ-тренер (по желанию)", "Бесплатный ключ Gemini — и к каждому матчу будет разбор тренера."]
    },
    setupActions: { dota: "Указать папку", gsi: "Установить", launch: "Скопировать", account: "Привязать", ai: "Настроить" },
    reportTitle: "Отчёт о проблеме",
    reportHint: "Журналы и настройки для разработчика, без ключей",
    reportSave: "Сохранить файл",
    backupTitle: "История матчей",
    backupHint: "Все матчи, разборы и ответы ИИ одним файлом: для копии или переноса на другой компьютер. Ключи не сохраняются.",
    backupExport: "Сохранить в файл",
    backupImport: "Загрузить из файла",
    backupSaved: (count, file) => `Сохранено матчей: ${count}. Файл ${file}`,
    backupLoaded: (added, linked) => `Загружено новых матчей: ${added}${linked ? ", аккаунт привязан" : ""}. Ничего не перезаписано.`,
    backupNotBackup: "Это не файл истории Wardly.",
    backupNewer: "Файл сделан более новой версией: сначала обновите приложение.",
    backupFailed: "Не получилось: служба не запущена или диск недоступен.",
    reportSaving: "Собираем…",
    reportSaved: (name) => `Сохранено: ${name}. Отправьте этот файл разработчику.`,
    reportFailed: "Не удалось сохранить файл",
    reportSend: "Отправить разработчику",
    reportNoteLabel: "Что случилось? (необязательно)",
    reportNotePlaceholder: "Например: в матче не видно оверлея",
    reportPreview: "Что будет отправлено",
    reportPreviewLoading: "Собираем отчёт…",
    reportTerms: "Ключи API вырезаны. Отчёт хранится 180 дней.",
    reportPrivacy: "Конфиденциальность",
    reportSendNow: "Отправить",
    reportCancel: "Отмена",
    reportSending: "Отправляем…",
    reportSentId: (id) => `Отправлено. Номер отчёта: ${id}. Назовите его, если будете писать разработчику.`,
    reportQueued: "Нет связи с сервисом. Отчёт отправится сам позже.",
    reportQueuedCount: (count) => `Ждут отправки: ${count}`,
    reportLast: (id) => `Последний отчёт: ${id}`,
    reportRefused: (name) =>
      name ? `Сервис не принял отчёт. Вместо этого сохранён файл: ${name}.` : "Сервис не принял отчёт.",
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
    hotkeys: "Ctrl+Alt+O вкл/выкл · Ctrl+Alt+L переместить · Ctrl+Alt+M тишина 5 мин · Ctrl+Alt+R повторить совет · Ctrl+Alt+1/2/3 слева/справа/снизу · Ctrl+Alt+D отладка",
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
  coverageNote: $("#coverage-note"),
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
  sizeButtons: [...document.querySelectorAll("#size-group [data-size]")],
  languageButtons: [...document.querySelectorAll("#language-group [data-language]")],
  frequencyButtons: [...document.querySelectorAll("#frequency-group [data-frequency]")],
  roleButtons: [...document.querySelectorAll("#role-group [data-role]")],
  roleHint: $("#role-hint"),
  roleNote: $("#role-note"),
  mapHints: $("#map-hints"),
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
  whatsNewCard: $("#whats-new-card"),
  whatsNewHeading: $("#whats-new-heading"),
  whatsNewList: $("#whats-new-list"),
  whatsNewDismiss: $("#whats-new-dismiss"),
  setupCard: $("#setup-card"),
  setupSteps: $("#setup-steps"),
  setupCount: $("#setup-count"),
  setupDismiss: $("#setup-dismiss"),
  odHint: $("#od-hint"),
  odForm: $("#od-form"),
  odKey: $("#od-key"),
  odSave: $("#od-save"),
  odGet: $("#od-get"),
  odClear: $("#od-clear"),
  reportAction: $("#report-action"),
  backupExport: $("#backup-export"),
  backupImport: $("#backup-import"),
  backupHint: $("#backup-hint"),
  reportHint: $("#report-hint"),
  reportOpen: $("#report-open"),
  reportPanel: $("#report-panel"),
  reportNote: $("#report-note"),
  reportPreview: $("#report-preview"),
  reportPreviewText: $("#report-preview-text"),
  reportPrivacy: $("#report-privacy"),
  reportSend: $("#report-send"),
  reportCancel: $("#report-cancel"),
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
let openDotaLoaded = false;
// Problem report row: a result message stays until the panel is opened again.
let reportSticky = false;
let reportPreviewLoaded = false;
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
  els.backupHint.textContent = tr("backupHint");
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
    if (action.doneLabel) {
      flashLabel(els.statusActionLabel, action.doneLabel);
    }
  });
  els.overlayToggle.addEventListener("change", () =>
    run(() => (els.overlayToggle.checked ? window.launcherApi.startOverlay() : window.launcherApi.stopOverlay()))
  );
  for (const button of els.positionButtons) {
    button.addEventListener("click", () =>
      run(async () => renderStatus(await window.launcherApi.setOverlayPosition(button.dataset.position)))
    );
  }
  for (const button of els.languageButtons) {
    button.addEventListener("click", () =>
      run(async () => renderStatus(await window.launcherApi.setLanguage(button.dataset.language)))
    );
  }
  for (const button of els.sizeButtons) {
    button.addEventListener("click", () =>
      run(async () => renderStatus(await window.launcherApi.setOverlaySize(button.dataset.size)))
    );
  }
  for (const button of els.frequencyButtons) {
    button.addEventListener("click", () =>
      run(async () => renderStatus(await window.launcherApi.setAdviceFrequency(button.dataset.frequency)))
    );
  }
  for (const button of els.roleButtons) {
    button.addEventListener("click", () =>
      run(async () => renderStatus(await window.launcherApi.setAdvicePreferences({ role: button.dataset.role })))
    );
  }
  els.mapHints.addEventListener("change", () =>
    run(async () => renderStatus(await window.launcherApi.setAdvicePreferences({ mapHints: els.mapHints.checked })))
  );
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
  els.odSave.addEventListener("click", () => run(saveOpenDotaKey));
  els.odKey.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      run(saveOpenDotaKey);
    }
  });
  els.odGet.addEventListener("click", () => run(() => window.launcherApi.openAiKeyPage("opendota")));
  els.odClear.addEventListener("click", () =>
    run(async () => {
      await window.launcherApi.player("odClear");
      await refreshOpenDota();
    })
  );
  document.querySelector("#tab-settings")?.addEventListener("click", () => run(refreshOpenDota));
  els.whatsNewDismiss.addEventListener("click", () =>
    run(async () => renderStatus(await window.launcherApi.dismissWhatsNew()))
  );
  els.setupDismiss.addEventListener("click", () =>
    run(async () => renderStatus(await window.launcherApi.dismissSetup()))
  );
  // History backup: one file with every match and review (no keys), merged back on load.
  const backupButtons = () => [els.backupExport, els.backupImport];
  async function backupRun(action) {
    backupButtons().forEach((button) => (button.disabled = true));
    try {
      const result = await action();
      if (result && result.canceled) {
        els.backupHint.textContent = tr("backupHint");
        return;
      }
      if (result && result.ok) {
        els.backupHint.textContent = result.path
          ? tr("backupSaved", result.matches, result.path.split(/[\\/]/).pop())
          : tr("backupLoaded", result.imported?.matches?.added ?? 0, result.linked);
      } else {
        els.backupHint.textContent = tr(result?.code === "not_backup" ? "backupNotBackup" : result?.code === "newer_version" ? "backupNewer" : "backupFailed");
      }
    } finally {
      backupButtons().forEach((button) => (button.disabled = false));
    }
  }
  els.backupExport.addEventListener("click", () => run(() => backupRun(() => window.launcherApi.exportHistory())));
  els.backupImport.addEventListener("click", () => run(() => backupRun(() => window.launcherApi.importHistory())));
  els.reportAction.addEventListener("click", () =>
    run(async () => {
      els.reportAction.disabled = true;
      reportSticky = true;
      setReportHint(tr("reportSaving"));
      try {
        const result = await window.launcherApi.saveProblemReport();
        setReportHint(
          result && result.ok ? tr("reportSaved", result.path.split(/[\\/]/).pop()) : tr("reportFailed"),
          result && result.ok ? result.path : result?.error || ""
        );
      } finally {
        els.reportAction.disabled = false;
      }
    })
  );
  els.reportOpen.addEventListener("click", () => toggleReportPanel(els.reportPanel.hidden));
  els.reportCancel.addEventListener("click", () => toggleReportPanel(false));
  els.reportPreview.addEventListener("toggle", () => {
    if (els.reportPreview.open && !reportPreviewLoaded) {
      reportPreviewLoaded = true;
      els.reportPreviewText.textContent = tr("reportPreviewLoading");
      window.launcherApi
        .previewProblemReport()
        .then((text) => {
          els.reportPreviewText.textContent = text;
        })
        .catch(() => {
          reportPreviewLoaded = false;
          els.reportPreviewText.textContent = tr("reportFailed");
        });
    }
  });
  els.reportPrivacy.addEventListener("click", () => run(() => window.launcherApi.openPrivacy()));
  els.reportSend.addEventListener("click", () =>
    run(async () => {
      els.reportSend.disabled = true;
      els.reportCancel.disabled = true;
      setReportHint(tr("reportSending"));
      try {
        const result = await window.launcherApi.sendProblemReport(els.reportNote.value);
        if (result?.ok) {
          setReportHint(tr("reportSentId", result.id));
          reportSticky = true;
          toggleReportPanel(false);
          els.reportNote.value = "";
        } else if (result?.queued) {
          setReportHint(tr("reportQueued"));
          reportSticky = true;
          toggleReportPanel(false);
        } else {
          setReportHint(tr("reportRefused", (result?.path || "").split(/[\\/]/).pop()), result?.path || "");
          reportSticky = true;
        }
      } finally {
        els.reportSend.disabled = false;
        els.reportCancel.disabled = false;
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

// "Copied" for a moment, then the label the next render gives it.
function flashLabel(element, text) {
  const previous = element.textContent;
  element.textContent = text;
  setTimeout(() => {
    if (element.textContent === text) {
      element.textContent = previous;
    }
  }, 1600);
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
  renderWhatsNew(status);
  renderReport(status);
  if (status.backend === "running" && !openDotaLoaded) {
    openDotaLoaded = true;
    run(refreshOpenDota);
  }
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

function setReportHint(text, title = "") {
  els.reportHint.textContent = text;
  els.reportHint.title = title;
}

function renderReport(status) {
  if (reportSticky) {
    return;
  }
  const report = status.report || {};
  const parts = [tr("reportHint")];
  if (report.queued) {
    parts.push(tr("reportQueuedCount", report.queued));
  } else if (report.last?.id) {
    parts.push(tr("reportLast", report.last.id));
  }
  setReportHint(parts.join(". "));
}

function toggleReportPanel(open) {
  els.reportPanel.hidden = !open;
  els.reportOpen.setAttribute("aria-expanded", String(open));
  if (open) {
    reportSticky = false;
    reportPreviewLoaded = false;
    els.reportPreview.open = false;
    els.reportPreviewText.textContent = "";
    els.reportNote.focus();
  }
}

// OpenDota key: the backend keeps it and only ever answers with a hint.
async function refreshOpenDota() {
  const result = await window.launcherApi.player("odStatus");
  renderOpenDota(result && result.ok ? result.data : null);
}

function renderOpenDota(data) {
  const configured = Boolean(data && data.configured);
  els.odForm.classList.toggle("hidden", configured);
  els.odClear.classList.toggle("hidden", !configured || data.source !== "app");
  els.odHint.textContent = !configured
    ? tr("odHintOff")
    : data.source === "env"
      ? tr("odHintEnv")
      : tr("odHintOn", data.key_hint || "");
}

async function saveOpenDotaKey() {
  const key = els.odKey.value.trim();
  if (!key) {
    return;
  }
  els.odSave.disabled = true;
  try {
    const result = await window.launcherApi.player("odSave", { apiKey: key });
    if (result && result.ok) {
      els.odKey.value = "";
      renderOpenDota(result.data);
    } else {
      els.odHint.textContent = tr("odBad");
    }
  } finally {
    els.odSave.disabled = false;
  }
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
    // Shown only when Steam's saved settings could be read.
    ...(status.launchOption === "ok" || status.launchOption === "missing"
      ? [{ id: "launch", done: status.launchOption === "ok" || dataSeen, action: () => window.launcherApi.copyLaunchOption() }]
      : []),
    { id: "data", done: dataSeen },
    { id: "account", done: Boolean(player.linked), action: () => window.PlayerViews?.setView("matches") },
    {
      id: "ai",
      done: Boolean(player.aiConfigured),
      optional: true,
      action: () => {
        window.PlayerViews?.setView("settings");
        document.getElementById("ai-settings-root")?.scrollIntoView({ block: "start" });
      }
    }
  ];
}

function renderWhatsNew(status) {
  const version = String(status.whatsNew || "");
  const table = (I18N[locale] || I18N.en).whatsNew || {};
  const items = table[version];
  const show = Boolean(version && Array.isArray(items) && items.length);
  els.whatsNewCard.classList.toggle("hidden", !show);
  if (!show || els.whatsNewList.dataset.signature === `${locale}|${version}`) {
    return;
  }
  els.whatsNewList.dataset.signature = `${locale}|${version}`;
  els.whatsNewHeading.textContent = tr("whatsNewTitle", version);
  els.whatsNewList.replaceChildren(
    ...items.map((text) => {
      const item = document.createElement("li");
      item.textContent = text;
      return item;
    })
  );
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
        button.addEventListener("click", async () => {
          await run(step.action);
          if (step.id === "launch") {
            flashLabel(button, tr("actions.copied"));
          }
        });
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
    fullscreenSeen: { label: tr("actions.fullscreenSeen"), icon: "eye", run: () => api.dismissFullscreenWarning() },
    copyLaunchOption: { label: tr("actions.copyLaunchOption"), icon: "copy", run: () => api.copyLaunchOption(), doneLabel: tr("actions.copied") }
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
  if (!live.connected && status.launchOption === "missing") {
    // Dota runs, the config is there, but nothing arrives: the usual cause.
    return { state: "warn", title: tr("status.launchOptionTitle"), hint: tr("status.launchOptionHint"), action: actions.copyLaunchOption };
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
    delete els.statHero.dataset.hero;
    els.statHero.replaceChildren(skeleton("w-70"));
    els.statClock.replaceChildren(skeleton("w-40"));
    els.statStage.replaceChildren(skeleton("w-60"));
    els.statData.replaceChildren(skeleton("w-50"));
    return;
  }
  els.coverageNote.classList.add("hidden");
  els.roleNote.classList.add("hidden");
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
  els.coverageNote.classList.toggle("hidden", live.coverage !== "safety");
  const role = live.role && tr(`roleNames.${live.role.role}`);
  els.roleNote.classList.toggle("hidden", !live.role);
  els.roleNote.textContent = live.role ? tr("roleNote", role, tr(`roleSource.${live.role.source}`)) : "";
  if (live.hero && window.DotaIcons?.hero(live.hero)) {
    // Keep the element while the hero stays the same (no flicker every second).
    if (els.statHero.dataset.hero !== live.hero) {
      els.statHero.dataset.hero = live.hero;
      const name = document.createElement("span");
      name.textContent = live.hero;
      const label = document.createElement("span");
      label.className = "with-pic";
      label.append(window.DotaIcons.heroPicture(document, live.hero, "sm"), name);
      els.statHero.replaceChildren(label);
    }
  } else {
    delete els.statHero.dataset.hero;
    els.statHero.textContent = live.hero || "—";
  }
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

  const language = status.language || "auto";
  for (const button of els.languageButtons) {
    button.setAttribute("aria-checked", String(button.dataset.language === language));
  }

  const size = status.overlaySize || "normal";
  for (const button of els.sizeButtons) {
    button.setAttribute("aria-checked", String(button.dataset.size === size));
    button.disabled = !enabled;
  }

  const frequency = status.adviceFrequency || "normal";
  for (const button of els.frequencyButtons) {
    button.setAttribute("aria-checked", String(button.dataset.frequency === frequency));
  }
  els.frequencyHint.textContent = tr(`frequencyHint.${frequency}`);

  const role = status.adviceRole || "auto";
  for (const button of els.roleButtons) {
    button.setAttribute("aria-checked", String(button.dataset.role === role));
  }
  els.roleHint.textContent = tr(`roleHint.${role}`);
  els.mapHints.checked = status.mapHints !== false;

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
