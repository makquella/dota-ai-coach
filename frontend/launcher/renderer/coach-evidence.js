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
    if (!rows.length) return null;
    const details = document.createElement("details");
    details.className = "coach-counter-evidence muted small";
    const summary = document.createElement("summary");
    summary.textContent = language === "ru" ? "Данные для проверки K/D/A" : "Data used to check K/D/A";
    const values = document.createElement("p");
    values.textContent = rows.map((row) => `${labels[fields.indexOf(row.field)]}: ${row.value}`).join(" · ");
    const scope = document.createElement("p");
    scope.textContent = language === "ru"
      ? "Итоговые счётчики из разбора матча. Они не подтверждают время и причины событий; цели следующей игры проверяются отдельно."
      : "Reported totals from the match analysis. They do not prove event times or causes; next-game goals are checked separately.";
    details.append(summary, values, scope);
    return details;
  }
};
