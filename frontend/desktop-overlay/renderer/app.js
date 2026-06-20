const shell = document.querySelector("#overlay-shell");
const labelEl = document.querySelector("#label");
const priorityEl = document.querySelector("#priority");
const statusRow = document.querySelector("#status-row");
const actionEl = document.querySelector("#action");
const reasonEl = document.querySelector("#reason");

let config = {
  backendUrl: "http://127.0.0.1:8000",
  pollIntervalMs: 1000,
  locked: true,
  autoHideMs: 8000,
  urgentAutoHideMs: 12000,
  debugVisible: false
};
let pollTimer = null;
let hideTimer = null;
let mutedUntil = 0;
let lastAdviceKey = "";
let lastVisibleAdvice = null;

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
    showStatus("Advice muted for 5 minutes.");
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
    showStatus(`Advice muted (${secondsUntil(mutedUntil)}s).`);
    return;
  }

  const result = await window.overlayApi.fetchRecommendation(config.backendUrl);
  if (!result.ok) {
    showStatus("Waiting for backend...");
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
    showStatus("Waiting for Dota 2 GSI...", data);
    return;
  }

  if (data.status === "stale_gsi") {
    lastVisibleAdvice = null;
    lastAdviceKey = "";
    showStatus(data.message || "Waiting for GSI...", data);
    return;
  }

  if (data.status === "monitoring") {
    showStatus(data.message || "Monitoring lane - no urgent advice.", data);
    return;
  }

  if (data.status === "unsupported_hero") {
    showStatus("Hero not supported yet", data);
    return;
  }

  if (data.status === "invalid_state") {
    showStatus("Waiting for valid GSI state...", data);
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
  actionEl.textContent = recommendation.action || "No urgent advice";
  reasonEl.textContent = recommendation.reason || "";
  renderStatusRow(data);
  reveal();

  lastVisibleAdvice = data;
  if (options.refreshTimer && key !== lastAdviceKey) {
    lastAdviceKey = key;
    scheduleAutoHide(adviceMode, data);
  }
}

function showStatus(message, data = {}) {
  clearTimeout(hideTimer);
  shell.className = "overlay-shell status";
  labelEl.textContent = statusLabel(data);
  priorityEl.textContent = data.context_confidence || "";
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
    showStatus("Listening for advice...");
  }, visibleFor);
}

function statusMessage(data) {
  if (data.suppressed_reason === "duplicate" || data.suppressed_reason === "duplicate_death_review") {
    return "No new advice.";
  }
  if (data.suppressed_reason === "rate_limit") {
    return "Advice paused to avoid overload.";
  }
  if (data.suppressed_reason === "cooldown") {
    return "Monitoring...";
  }
  return data.message || "No urgent advice.";
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

function labelText(adviceMode, data) {
  const parts = [adviceMode];
  if (data.source && data.source !== "none") {
    parts.push(data.source);
  }
  if (data.demo_mode) {
    parts.push("DEMO REPLAY MODE");
  } else if (data.current_mode === "live_gsi" || data.source_type === "live_gsi") {
    parts.push("LIVE GSI MODE");
  }
  return parts.join(" · ");
}

function statusLabel(data) {
  if (data.demo_mode) {
    return "Status · DEMO REPLAY MODE";
  }
  if (data.status === "waiting_for_gsi" || data.status === "stale_gsi") {
    return "Status · WAITING FOR GSI";
  }
  if (data.current_mode === "live_gsi" || data.source_type === "live_gsi") {
    return "Status · LIVE GSI MODE";
  }
  return "Status";
}

function priorityText(recommendation, data) {
  const parts = [];
  if (recommendation.priority) {
    parts.push(recommendation.priority);
  }
  if (data.context_confidence) {
    parts.push(data.context_confidence);
  }
  return parts.join(" · ");
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
