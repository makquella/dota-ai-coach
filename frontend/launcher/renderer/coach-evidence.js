"use strict";

// Shared by the match review and saved answers. Values are text, never HTML.
window.WardlyCoachEvidence = {
  render(review, language) {
    const labels = language === "ru" ? ["Убийства", "Смерти", "Ассисты"] : ["Kills", "Deaths", "Assists"];
    const fields = ["kills", "deaths", "assists"];
    const rows = (Array.isArray(review?.counter_evidence) ? review.counter_evidence : []).filter((row) =>
      row?.source === "analysis.headline" && fields.includes(row.field) &&
      row.observed_at === null && row.precision === "reported_total" &&
      Number.isSafeInteger(row.value) && row.value >= 0
    );
    const rateFields = ["gpm", "xpm"];
    const rates = (Array.isArray(review?.rate_evidence) ? review.rate_evidence : []).filter((row) =>
      row?.source === "analysis.headline" && rateFields.includes(row.field) &&
      row.observed_at === null && row.precision === "reported_match_rate" &&
      Number.isFinite(row.value) && row.value >= 0 && row.value <= Number.MAX_SAFE_INTEGER
    );
    const farmFields = ["last_hits", "denies"];
    const farmLabels = language === "ru" ? ["Добивания", "Денаи"] : ["Last hits", "Denies"];
    const farm = (Array.isArray(review?.farm_evidence) ? review.farm_evidence : []).filter((row) =>
      row?.source === "analysis.headline" && farmFields.includes(row.field) &&
      row.observed_at === null && row.precision === "reported_total" &&
      Number.isSafeInteger(row.value) && row.value >= 0
    );
    const samples = (Array.isArray(review?.farm_slice_evidence) ? review.farm_slice_evidence : []).filter((row) =>
      farmFields.includes(row?.field) && ["player", "opponent"].includes(row.subject) &&
      (row.hero === null || typeof row.hero === "string") &&
      row.observed_at === 600 && row.precision === "reported_sample" &&
      Number.isSafeInteger(row.value) && row.value >= 0 &&
      (row.source === "analysis.lane.points" ||
        (row.source === "analysis.peers.me" && row.subject === "player" && row.field === "last_hits") ||
        (row.source === "analysis.peers.peers[0].metrics" && row.subject === "opponent" && row.field === "last_hits"))
    );
    if (!rows.length && !rates.length && !farm.length && !samples.length) return null;
    const details = document.createElement("details");
    details.className = "coach-counter-evidence muted small";
    const summary = document.createElement("summary");
    const metrics = [rows.length ? "K/D/A" : "", rates.length ? "GPM/XPM" : "", farm.length ? "LH/DN" : "", samples.length ? "LH/DN · 10:00" : ""].filter(Boolean).join(", ");
    summary.textContent = (language === "ru" ? "Данные для проверки " : "Data used to check ") + metrics;
    const values = document.createElement("p");
    values.textContent = [
      ...rows.map((row) => `${labels[fields.indexOf(row.field)]}: ${row.value}`),
      ...rates.map((row) => `${row.field.toUpperCase()}: ${language === "ru" ? String(row.value).replace(".", ",") : row.value}`),
      ...farm.map((row) => `${farmLabels[farmFields.indexOf(row.field)]}: ${row.value}`),
      ...samples.map((row) => {
        const subject = row.subject === "player" ? (language === "ru" ? "Вы" : "You") : (language === "ru" ? "Соперник" : "Opponent");
        return `10:00 · ${subject}${row.hero ? ` (${row.hero})` : ""} · ${farmLabels[farmFields.indexOf(row.field)]}: ${row.value}`;
      })
    ].join(" · ");
    const scope = document.createElement("p");
    scope.textContent = samples.length ? (language === "ru"
      ? "Показатели из разбора: итоги матча и отдельно помеченные значения к 10:00. Они не подтверждают другие отрезки времени и причины событий."
      : "Analysis metrics: match totals and separately labeled samples at 10:00. They do not prove other time slices or event causes.") : rates.length || farm.length ? (language === "ru"
      ? "Показатели игрока из разбора за весь матч. Они не подтверждают отдельные отрезки времени и причины событий; цели следующей игры проверяются отдельно."
      : "Player metrics reported by the analysis across the match. They do not prove time slices or event causes; next-game goals are checked separately.") : language === "ru"
      ? "Итоговые счётчики из разбора матча. Они не подтверждают время и причины событий; цели следующей игры проверяются отдельно."
      : "Reported totals from the match analysis. They do not prove event times or causes; next-game goals are checked separately.";
    details.append(summary, values, scope);
    return details;
  }
};
