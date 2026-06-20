const API_URL = "http://127.0.0.1:8000/recommend";
const REQUEST_TIMEOUT_MS = 35000;

const presets = {
  antimage: {
    hero: "Anti-Mage",
    role: "carry",
    minute: 14,
    level: 10,
    gold: 1800,
    items: ["Power Treads", "Ring of Health", "Claymore"],
    hp_percent: 70,
    game_state: "enemy_pressure_mid",
    team_status: "supports_dead"
  },
  juggernaut: {
    hero: "Juggernaut",
    role: "carry",
    minute: 22,
    level: 14,
    gold: 800,
    items: ["Power Treads", "Maelstrom", "Magic Wand"],
    hp_percent: 28,
    game_state: "skirmish_near_top_tier2",
    team_status: "all_alive"
  },
  luna: {
    hero: "Luna",
    role: "carry",
    minute: 27,
    level: 16,
    gold: 3200,
    items: ["Power Treads", "Manta Style", "Helm of the Dominator"],
    hp_percent: 85,
    game_state: "team_fight_breaking_out_bot",
    team_status: "full_team_alive"
  }
};

const scenarioInput = document.querySelector("#scenario-input");
const recommendButton = document.querySelector("#recommend-button");
const loadingMessage = document.querySelector("#loading-message");
const presetButtons = document.querySelectorAll(".preset-button");
const resultPanel = document.querySelector("#result-panel");
const errorPanel = document.querySelector("#error-panel");
const errorSummary = document.querySelector("#error-summary");
const errorMessage = document.querySelector("#error-message");

const resultFields = {
  action: document.querySelector("#result-action"),
  reason: document.querySelector("#result-reason"),
  risk: document.querySelector("#result-risk"),
  priority: document.querySelector("#result-priority"),
  time_window: document.querySelector("#result-time-window"),
  source: document.querySelector("#result-source")
};

setScenario("antimage");

presetButtons.forEach((button) => {
  button.addEventListener("click", () => {
    setScenario(button.dataset.preset);
    clearMessages();
  });
});

recommendButton.addEventListener("click", async () => {
  clearMessages();
  setLoading(true);
  let timeoutId;

  try {
    const payload = parseScenario();
    const controller = new AbortController();
    timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    const response = await fetch(API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload),
      signal: controller.signal
    });

    const data = await readJsonResponse(response);

    if (!response.ok) {
      throw formatBackendError(data, response.status);
    }

    showRecommendation(data);
  } catch (error) {
    if (error.name === "AbortError") {
      showError(
        "The backend took too long to respond.",
        `Request timed out after ${Math.round(REQUEST_TIMEOUT_MS / 1000)} seconds.`
      );
      return;
    }

    if (error instanceof TypeError) {
      showError(
        "Could not reach the backend. Make sure FastAPI is running at http://127.0.0.1:8000.",
        error.message
      );
      return;
    }

    showError(
      error.userMessage ?? "Something went wrong while generating the recommendation.",
      error.details ?? error.message
    );
  } finally {
    if (timeoutId) {
      window.clearTimeout(timeoutId);
    }
    setLoading(false);
  }
});

function parseScenario() {
  try {
    return JSON.parse(scenarioInput.value);
  } catch (error) {
    throw createDisplayError(
      "The JSON is not valid. Fix the syntax and try again.",
      error.message
    );
  }
}

async function readJsonResponse(response) {
  const text = await response.text();

  if (!text) {
    return {};
  }

  try {
    return JSON.parse(text);
  } catch {
    throw createDisplayError(
      "The backend returned a response the frontend could not read.",
      `Backend returned non-JSON response with status ${response.status}.`
    );
  }
}

function showRecommendation(data) {
  for (const field of Object.keys(resultFields)) {
    resultFields[field].textContent = data[field] ?? "";
  }

  resultPanel.classList.remove("hidden");
}

function showError(summary, details) {
  errorSummary.textContent = summary;
  errorMessage.textContent = details;
  errorPanel.classList.remove("hidden");
}

function clearMessages() {
  resultPanel.classList.add("hidden");
  errorPanel.classList.add("hidden");
  errorSummary.textContent = "";
  errorMessage.textContent = "";
}

function formatBackendError(data, status) {
  if (Array.isArray(data.detail)) {
    const details = data.detail
      .map((item) => {
        const location = Array.isArray(item.loc) ? item.loc.join(".") : "request";
        return `${location}: ${item.msg}`;
      })
      .join("\n");

    return createDisplayError(
      "The backend rejected this scenario. Check the highlighted fields in the technical details.",
      details
    );
  }

  if (typeof data.detail === "string") {
    return createDisplayError("The backend rejected this request.", data.detail);
  }

  return createDisplayError(
    "The backend could not generate a recommendation for this request.",
    `Request failed with status ${status}.`
  );
}

function setScenario(presetName) {
  scenarioInput.value = JSON.stringify(presets[presetName], null, 2);
}

function setLoading(isLoading) {
  recommendButton.disabled = isLoading;
  recommendButton.textContent = isLoading ? "Generating..." : "Get Recommendation";
  loadingMessage.classList.toggle("hidden", !isLoading);
}

function createDisplayError(userMessage, details) {
  const error = new Error(details);
  error.userMessage = userMessage;
  error.details = details;
  return error;
}
