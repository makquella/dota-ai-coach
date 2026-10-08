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
    if (!rows.length && !rates.length) return null;
    const details = document.createElement("details");
    details.className = "coach-counter-evidence muted small";
    const summary = document.createElement("summary");
    const metrics = [rows.length ? "K/D/A" : "", rates.length ? "GPM/XPM" : ""].filter(Boolean).join(", ");
    summary.textContent = (language === "ru" ? "Данные для проверки " : "Data used to check ") + metrics;
    const values = document.createElement("p");
    values.textContent = [
      ...rows.map((row) => `${labels[fields.indexOf(row.field)]}: ${row.value}`),
      ...rates.map((row) => `${row.field.toUpperCase()}: ${language === "ru" ? String(row.value).replace(".", ",") : row.value}`)
    ].join(" · ");
    const scope = document.createElement("p");
    scope.textContent = rates.length ? (language === "ru"
      ? "Показатели игрока из разбора за весь матч. Они не подтверждают отдельные отрезки времени и причины событий; цели следующей игры проверяются отдельно."
      : "Player metrics reported by the analysis across the match. They do not prove time slices or event causes; next-game goals are checked separately.") : language === "ru"
      ? "Итоговые счётчики из разбора матча. Они не подтверждают время и причины событий; цели следующей игры проверяются отдельно."
      : "Reported totals from the match analysis. They do not prove event times or causes; next-game goals are checked separately.";
    details.append(summary, values, scope);
    return details;
  }
};
