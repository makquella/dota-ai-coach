const shell = document.querySelector("#overlay-shell");
const labelEl = document.querySelector("#label");
const priorityEl = document.querySelector("#priority");
const statusRow = document.querySelector("#status-row");
const actionEl = document.querySelector("#action");
const reasonEl = document.querySelector("#reason");

// Short card texts in the system language; advice itself comes from the backend.
const OVERLAY_TEXT = {
  en: {
    urgent: "Urgent",
    tip: "Tip",
    coach: "Coach",
    demo: "Demo",
    priority: { high: "high priority", urgent: "high priority", medium: "medium priority", low: "low priority", safe: "calm" },
    waitingBackend: "Waiting for the coach service…",
    backendStopped: "The coach service is stopped.",
    waitingGsi: "Waiting for Dota 2 game data…",
    waitingGsiShort: "Waiting for game data…",
    monitoring: "Watching the lane — no urgent advice.",
    unsupportedHero: "This hero is not supported yet.",
    invalidState: "Waiting for valid game data…",
    listening: "Listening for advice…",
    muted: "Advice muted for 5 minutes.",
    mutedFor: (s) => `Advice muted (${s} s).`,
    noNewAdvice: "No new advice.",
    paused: "Advice paused to avoid overload.",
    watching: "Watching…",
    noUrgent: "No urgent advice.",
    noAction: "No urgent advice"
  },
  ru: {
    urgent: "Срочно",
    tip: "Совет",
    coach: "Тренер",
    demo: "Демо",
    priority: { high: "высокий приоритет", urgent: "высокий приоритет", medium: "средний приоритет", low: "низкий приоритет", safe: "спокойно" },
    waitingBackend: "Ждём сервис тренера…",
    backendStopped: "Сервис тренера остановлен.",
    waitingGsi: "Ждём данные из Dota 2…",
    waitingGsiShort: "Ждём данные игры…",
    monitoring: "Следим за линией — срочных советов нет.",
    unsupportedHero: "Этот герой пока не поддерживается.",
    invalidState: "Ждём корректные данные игры…",
    listening: "Ждём следующий совет…",
    muted: "Советы выключены на 5 минут.",
    mutedFor: (s) => `Советы выключены (${s} с).`,
    noNewAdvice: "Новых советов нет.",
    paused: "Советы на паузе, чтобы не перегружать.",
    watching: "Наблюдаем…",
    noUrgent: "Срочных советов нет.",
    noAction: "Срочных советов нет"
  }
};

function tr(key, ...args) {
  const table = OVERLAY_TEXT[config.locale] || OVERLAY_TEXT.en;
  const value = key.split(".").reduce((node, part) => (node ? node[part] : undefined), table);
  const resolved = value ?? key.split(".").reduce((node, part) => (node ? node[part] : undefined), OVERLAY_TEXT.en) ?? key;
  return typeof resolved === "function" ? resolved(...args) : resolved;
}

let config = {
  locale: "en",
  backendUrl: "",
  backendStatus: "starting",
  pollIntervalMs: 1000,
  locked: true,
  autoHideMs: 8000,
  urgentAutoHideMs: 12000,
  debugVisible: false,
  voice: "off",
  voiceVolume: 1
};
let pollTimer = null;
let hideTimer = null;
let mutedUntil = 0;
let lastAdviceKey = "";
let lastVisibleAdvice = null;
const speaker = window.OverlayVoice && window.speechSynthesis
  ? window.OverlayVoice.createSpeaker({ synth: window.speechSynthesis, Utterance: window.SpeechSynthesisUtterance })
  : null;

init();

async function init() {
  config = { ...config, ...(await window.overlayApi.getConfig()) };
  applyConfig(config);
  window.overlayApi.onConfigUpdated((nextConfig) => {
    config = { ...config, ...nextConfig };
    applyConfig(config);
  });
  window.overlayApi.onMuted((timestamp) => {
    mutedUntil = Number(timestamp) || 0;
    speaker?.reset();
    showStatus(tr("muted"));
  });
  window.overlayApi.onRepeat?.(() => {
    if (!lastVisibleAdvice?.recommendation) {
      return;
    }
    const data = lastVisibleAdvice;
    renderAdvice(data, { refreshTimer: false });
    scheduleAutoHide(data.advice_mode || "coaching", { ...data, is_pinned: false });
    speaker?.say({
      key: lastAdviceKey,
      text: data.recommendation.action,
      adviceMode: data.advice_mode,
      mode: config.voice,
      locale: config.locale,
      volume: config.voiceVolume,
      repeat: true
    });
  });
  window.overlayApi.onToggleDebug((visible) => {
    config.debugVisible = Boolean(visible);
    applyConfig(config);
  });
  startPolling();
}

function applyConfig(nextConfig) {
  document.body.classList.toggle("locked", Boolean(nextConfig.locked));
  document.body.classList.toggle("unlocked", !nextConfig.locked);
  document.body.classList.toggle("debug-hidden", nextConfig.debugVisible === false);
}

function startPolling() {
  clearInterval(pollTimer);
  poll();
  pollTimer = setInterval(poll, Number(config.pollIntervalMs) || 1000);
}

async function poll() {
  if (Date.now() < mutedUntil) {
    showStatus(tr("mutedFor", secondsUntil(mutedUntil)));
    return;
  }

  const result = await window.overlayApi.fetchRecommendation();
  if (!result.ok) {
    showStatus(config.backendStatus === "stopped" ? tr("backendStopped") : tr("waitingBackend"));
    return;
  }

  renderOverlay(result.data);
}

function renderOverlay(data) {
  if (data.recommendation && (data.status === "active_advice" || data.status === "cooldown")) {
    renderAdvice(data, { refreshTimer: data.status !== "active_advice" });
    return;
  }

  if (data.status === "waiting_for_gsi") {
    showStatus(tr("waitingGsi"), data);
    return;
  }

  if (data.status === "stale_gsi") {
    lastVisibleAdvice = null;
    lastAdviceKey = "";
    showStatus(data.message || tr("waitingGsiShort"), data);
    return;
  }

  if (data.status === "monitoring") {
    showStatus(data.message || tr("monitoring"), data);
    return;
  }

  if (data.status === "unsupported_hero") {
    showStatus(tr("unsupportedHero"), data);
    return;
  }

  if (data.status === "invalid_state") {
    showStatus(tr("invalidState"), data);
    return;
  }

  if (data.status === "cooldown") {
    if (lastVisibleAdvice) {
      renderAdvice(lastVisibleAdvice, { refreshTimer: false });
      return;
    }
    showStatus(data.message || statusMessage(data), data);
    return;
  }

  if (!data.recommendation) {
    showStatus(statusMessage(data), data);
    return;
  }

  renderAdvice(data, { refreshTimer: true });
}

function renderAdvice(data, options = { refreshTimer: true }) {
  const recommendation = data.recommendation;
  const adviceMode = data.advice_mode || (recommendation.priority === "high" ? "urgent" : "coaching");
  const key = [
    data.decision_point,
    recommendation.action,
    recommendation.reason,
    recommendation.priority,
    data.match_death_count || 0,
    data.last_death_minute || ""
  ].join("|");

  shell.className = [
    "overlay-shell",
    adviceMode === "urgent" ? "urgent" : "coaching",
    priorityClassName(recommendation.priority)
  ].filter(Boolean).join(" ");
  labelEl.textContent = labelText(adviceMode, data);
  priorityEl.textContent = priorityText(recommendation, data);
  actionEl.textContent = recommendation.action || tr("noAction");
  reasonEl.textContent = recommendation.reason || "";
  renderStatusRow(data);
  reveal();

  lastVisibleAdvice = data;
  // Spoken once per advice while it is still current (a tip skipped because
  // another one was being spoken gets its turn on a later poll).
  if (speaker && data.status === "active_advice") {
    speaker.say({
      key,
      text: recommendation.action,
      adviceMode,
      mode: config.voice,
      locale: config.locale,
      volume: config.voiceVolume
    });
  }
  if (options.refreshTimer && key !== lastAdviceKey) {
    lastAdviceKey = key;
    scheduleAutoHide(adviceMode, data);
  }
}

function showStatus(message, data = {}) {
  clearTimeout(hideTimer);
  shell.className = "overlay-shell status";
  labelEl.textContent = statusLabel(data);
  priorityEl.textContent = "";
  actionEl.textContent = message;
  reasonEl.textContent = "";
  renderStatusRow(data);
  reveal();
}

function reveal() {
  shell.classList.remove("hidden");
}

function scheduleAutoHide(adviceMode, data = {}) {
  clearTimeout(hideTimer);
  if (data.is_pinned) {
    return;
  }

  const activeUntil = Date.parse(data.active_advice_until || "");
  const activeDuration = Number.isFinite(activeUntil) ? Math.max(0, activeUntil - Date.now()) : 0;
  const timeout = adviceMode === "urgent"
    ? Number(config.urgentAutoHideMs) || 12000
    : Number(config.autoHideMs) || 8000;
  const visibleFor = Math.max(timeout, activeDuration);
  hideTimer = setTimeout(() => {
    showStatus(tr("listening"));
  }, visibleFor);
}

function statusMessage(data) {
  if (data.suppressed_reason === "duplicate" || data.suppressed_reason === "duplicate_death_review") {
    return tr("noNewAdvice");
  }
  if (data.suppressed_reason === "rate_limit") {
    return tr("paused");
  }
  if (data.suppressed_reason === "cooldown") {
    return tr("watching");
  }
  return data.message || tr("noUrgent");
}

function renderStatusRow(data) {
  const chips = [];
  if (data.demo_mode) {
    chips.push("DEMO REPLAY MODE");
  } else if (data.status === "waiting_for_gsi" || data.status === "stale_gsi") {
    chips.push("WAITING FOR GSI");
  } else if (data.current_mode === "live_gsi" || data.source_type === "live_gsi") {
    chips.push("LIVE GSI MODE");
  }
  const hero = data.hero || "";
  const time = data.simulated_time_label || minuteLabel(data.minute);
  if (hero || time) {
    chips.push([hero, time].filter(Boolean).join(" "));
  }
  if (data.stage) {
    chips.push(data.stage);
  }
  if (Number.isFinite(data.hp_percent)) {
    chips.push(`HP ${data.hp_percent}%`);
  }
  if (Number.isFinite(data.mana_percent)) {
    chips.push(`Mana ${data.mana_percent}%`);
  }
  if (data.gpm !== null && data.gpm !== undefined) {
    chips.push(`GPM ${data.gpm}`);
  }
  if (data.last_hits !== null && data.last_hits !== undefined) {
    chips.push(`LH ${data.last_hits}`);
  }
  if (data.context_confidence) {
    chips.push(`conf ${data.context_confidence}`);
  }
  if (data.source && data.source !== "none") {
    chips.push(data.source);
  }
  if (Array.isArray(data.missing_signals) && data.missing_signals.length) {
    chips.push(`missing ${data.missing_signals.length}`);
  }

  statusRow.replaceChildren();
  if (!chips.length) {
    statusRow.classList.add("hidden");
    return;
  }

  for (const chip of chips.slice(0, 7)) {
    const item = document.createElement("span");
    item.className = "status-chip";
    item.textContent = chip;
    statusRow.appendChild(item);
  }
  statusRow.classList.remove("hidden");
}

function secondsUntil(timestamp) {
  return Math.max(0, Math.ceil((timestamp - Date.now()) / 1000));
}

// Card title: what kind of card this is. Source and mode moved to the
// debug line (Ctrl+Alt+D) to keep the card quiet during a game.
function labelText(adviceMode, data) {
  const kind = adviceMode === "urgent" ? tr("urgent") : tr("tip");
  return data.demo_mode ? `${kind} · ${tr("demo")}` : kind;
}

function statusLabel(data) {
  return data.demo_mode ? `${tr("coach")} · ${tr("demo")}` : tr("coach");
}

function priorityText(recommendation) {
  const value = String(recommendation.priority || "").toLowerCase();
  const label = value ? tr(`priority.${value}`) : "";
  return label.startsWith("priority.") ? value : label;
}

function priorityClassName(priority) {
  const value = String(priority || "").toLowerCase();
  if (value === "high" || value === "urgent") {
    return "priority-high";
  }
  if (value === "medium") {
    return "priority-medium";
  }
  if (value === "low") {
    return "priority-low";
  }
  if (value === "safe") {
    return "priority-safe";
  }
  return "";
}

function minuteLabel(minute) {
  const value = Number(minute);
  if (!Number.isFinite(value)) {
    return "";
  }
  return `${String(Math.max(0, Math.floor(value))).padStart(2, "0")}:00`;
}
