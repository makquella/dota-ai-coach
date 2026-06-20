const statusEls = {
  backend: document.querySelector("#backend-status"),
  overlay: document.querySelector("#overlay-status"),
  demo: document.querySelector("#demo-status"),
  recording: document.querySelector("#recording-status"),
  gsi: document.querySelector("#gsi-status"),
  mode: document.querySelector("#mode-status"),
  llm: document.querySelector("#llm-status")
};
const logsEl = document.querySelector("#logs");
const gsiPathEl = document.querySelector("#gsi-path");
const gsiDetailEl = document.querySelector("#gsi-detail");
const liveEls = {
  connection: document.querySelector("#live-connection"),
  last: document.querySelector("#live-last"),
  hero: document.querySelector("#live-hero"),
  time: document.querySelector("#live-time"),
  stage: document.querySelector("#live-stage"),
  advice: document.querySelector("#live-advice"),
  missing: document.querySelector("#live-missing")
};
const logModeButtons = {
  clean: document.querySelector("#log-clean"),
  verbose: document.querySelector("#log-verbose")
};
const demoStartButtons = [
  document.querySelector("#run-demo"),
  document.querySelector("#preset-pl"),
  document.querySelector("#preset-jugg"),
  document.querySelector("#deep-review")
].filter(Boolean);
const controlButtons = {
  startBackend: document.querySelector("#start-backend"),
  stopBackend: document.querySelector("#stop-backend"),
  startOverlay: document.querySelector("#start-overlay"),
  stopOverlay: document.querySelector("#stop-overlay"),
  stopDemo: document.querySelector("#stop-demo"),
  startRecording: document.querySelector("#start-recording"),
  stopRecording: document.querySelector("#stop-recording")
};

init();

async function init() {
  bind("#start-backend", () => window.launcherApi.startBackend());
  bind("#stop-backend", () => window.launcherApi.stopBackend());
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
  bind("#install-gsi", installGsi);
  bind("#choose-gsi", chooseGsiFolder);
  bind("#check-live-gsi", checkLiveGsi);
  bind("#start-recording", startLiveRecording);
  bind("#stop-recording", stopLiveRecording);
  bind("#open-records", () => window.launcherApi.openSessionRecords());

  window.launcherApi.onStatus(renderStatus);
  window.launcherApi.onLogs(renderLogs);

  renderStatus(await window.launcherApi.getStatus());
  renderLogs(await window.launcherApi.getLogs());
}

function bind(selector, handler) {
  const element = document.querySelector(selector);
  if (!element) {
    return;
  }
  element.addEventListener("click", async () => {
    try {
      await handler();
    } catch (error) {
      renderLogs(`${logsEl.textContent || ""}\n[renderer] ${error.message || error}\n`);
    }
  });
}

async function checkGsi() {
  const result = await window.launcherApi.checkGsi(gsiPathEl.value);
  updateGsiDetail(result);
}

async function installGsi() {
  const result = await window.launcherApi.installGsi(gsiPathEl.value);
  updateGsiDetail(result);
}

async function chooseGsiFolder() {
  const folder = await window.launcherApi.chooseGsiFolder();
  if (folder) {
    gsiPathEl.value = folder;
    await checkGsi();
  }
}

async function checkLiveGsi() {
  const status = await window.launcherApi.checkLiveGsi();
  renderLiveStatus(status);
}

async function startLiveRecording() {
  await window.launcherApi.startLiveRecording();
  await checkLiveGsi();
}

async function stopLiveRecording() {
  await window.launcherApi.stopLiveRecording();
  await checkLiveGsi();
}

function renderStatus(status) {
  setChip(statusEls.backend, `Backend: ${status.backend || "unknown"}`, status.backend);
  setChip(statusEls.overlay, `Overlay: ${status.overlay || "unknown"}`, status.overlay);
  const demoText = status.demo === "running" && status.demoPreset
    ? `Demo: running · ${status.demoPreset}`
    : `Demo: ${status.demo || "stopped"}`;
  setChip(statusEls.demo, demoText, status.demo);
  setChip(statusEls.recording, `Recording: ${status.recording || "stopped"}`, status.recording);
  setChip(statusEls.gsi, `GSI config: ${status.gsiConfig || "unknown"}`, normalizeClass(status.gsiConfig));
  setChip(statusEls.mode, `Mode: ${status.mode || "Live GSI"}`, "running");
  setChip(statusEls.llm, `LLM: ${status.llm || "off"}`, status.llm);
  renderLogMode(status.logMode || "clean");
  renderControlButtons(status);
  updateGsiDetail({ status: status.gsiConfig, path: status.gsiPath });
}

function renderControlButtons(status = {}) {
  const backendRunning = isActiveProcess(status.backend);
  const overlayRunning = isActiveProcess(status.overlay);
  const demoRunning = isActiveProcess(status.demo);
  const recordingRunning = isActiveProcess(status.recording);

  setActionEnabled(controlButtons.startBackend, !backendRunning);
  setActionEnabled(controlButtons.stopBackend, backendRunning);
  setActionEnabled(controlButtons.startOverlay, !overlayRunning);
  setActionEnabled(controlButtons.stopOverlay, overlayRunning);
  setActionEnabled(controlButtons.stopDemo, demoRunning);
  setActionEnabled(controlButtons.startRecording, !recordingRunning);
  setActionEnabled(controlButtons.stopRecording, recordingRunning);
  renderDemoButtons(demoRunning);
}

function isActiveProcess(state) {
  return state === "running" || state === "starting";
}

function setActionEnabled(button, enabled) {
  if (!button) {
    return;
  }
  button.disabled = !enabled;
  button.classList.toggle("is-action-enabled", Boolean(enabled));
}

function renderDemoButtons(isDemoRunning) {
  for (const button of demoStartButtons) {
    button.disabled = isDemoRunning;
    button.classList.toggle("is-action-enabled", !isDemoRunning);
    button.title = isDemoRunning ? "Demo is already running. Stop Demo before starting another preset." : "";
  }
}

function renderLogMode(mode) {
  for (const [name, button] of Object.entries(logModeButtons)) {
    if (!button) {
      continue;
    }
    button.classList.toggle("active", name === mode);
  }
}

function setChip(element, text, state) {
  element.textContent = text;
  element.className = `chip ${normalizeClass(state)}`;
}

function normalizeClass(value) {
  return String(value || "unknown")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function updateGsiDetail(result = {}) {
  if (result.path) {
    gsiDetailEl.textContent = `GSI config path: ${result.path}`;
  } else if (result.status === "not found") {
    gsiDetailEl.textContent = "GSI config not found. Enter or choose the gamestate_integration folder, then install.";
  } else {
    gsiDetailEl.textContent = "Default endpoint: http://127.0.0.1:8000/gsi";
  }
}

function renderLiveStatus(status = {}) {
  if (status.error) {
    setChip(liveEls.connection, "GSI: backend unavailable", "stopped");
    liveEls.advice.textContent = `Current advice: ${status.error}`;
    return;
  }
  setChip(liveEls.connection, `GSI: ${status.gsi_connected ? "connected" : "waiting/stale"}`, status.gsi_connected ? "running" : "stopped");
  setChip(liveEls.last, `Last GSI: ${status.seconds_since_last_gsi ?? "n/a"}s`, status.gsi_connected ? "running" : "stopped");
  setChip(liveEls.hero, `Hero: ${status.hero || "unknown"}`, "running");
  setChip(liveEls.time, `Game time: ${status.game_time ?? "unknown"}`, "running");
  setChip(liveEls.stage, `Stage: ${status.stage || "unknown"}`, "running");
  liveEls.advice.textContent = status.current_advice
    ? `Current advice: ${status.current_advice}`
    : `Current advice: ${status.last_advice_time ? `last shown at ${status.last_advice_time}` : "none yet"}`;
  const missing = Array.isArray(status.missing_important_fields) && status.missing_important_fields.length
    ? status.missing_important_fields.join(", ")
    : "none";
  liveEls.missing.textContent = `Missing important fields: ${missing}`;
}

function renderLogs(logs) {
  logsEl.textContent = logs || "";
  logsEl.scrollTop = logsEl.scrollHeight;
}
