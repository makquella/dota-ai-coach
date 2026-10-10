"use strict";

// Shared by the match review and saved answers. Values are text, never HTML.
window.WardlyCoachEvidence = {
  render(review, language) {
    const labels = language === "uk" ? ["Вбивства", "Смерті", "Асисти"] : ["Kills", "Deaths", "Assists"];
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
    const farmLabels = language === "uk" ? ["Добивання", "Денаї"] : ["Last hits", "Denies"];
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
        (["opendota.lh_t", "gsi.samples"].includes(row.source) && row.subject === "player" && row.field === "last_hits") ||
        (row.source === "analysis.peers.me" && row.subject === "player" && row.field === "last_hits") ||
        (row.source === "analysis.peers.peers[0].metrics" && row.subject === "opponent" && row.field === "last_hits"))
    );
    const finding = window.WardlyFindingEvidence.renderRows(review?.finding_evidence, language);
    if (!rows.length && !rates.length && !farm.length && !samples.length) return finding;
    const details = document.createElement("details");
    details.className = "coach-counter-evidence muted small";
    const summary = document.createElement("summary");
    const metrics = [rows.length ? "K/D/A" : "", rates.length ? "GPM/XPM" : "", farm.length ? "LH/DN" : "", samples.length ? "LH/DN · 10:00" : ""].filter(Boolean).join(", ");
    summary.textContent = (language === "uk" ? "Дані для перевірки " : "Data used to check ") + metrics;
    const values = document.createElement("p");
    values.textContent = [
      ...rows.map((row) => `${labels[fields.indexOf(row.field)]}: ${row.value}`),
      ...rates.map((row) => `${row.field.toUpperCase()}: ${language === "uk" ? String(row.value).replace(".", ",") : row.value}`),
      ...farm.map((row) => `${farmLabels[farmFields.indexOf(row.field)]}: ${row.value}`),
      ...samples.map((row) => {
        const subject = row.subject === "player" ? (language === "uk" ? "Ви" : "You") : (language === "uk" ? "Суперник" : "Opponent");
        return `10:00 · ${subject}${row.hero ? ` (${row.hero})` : ""} · ${farmLabels[farmFields.indexOf(row.field)]}: ${row.value}`;
      })
    ].join(" · ");
    const scope = document.createElement("p");
    scope.textContent = samples.length ? (language === "uk"
      ? "Показники з розбору: підсумки матчу й окремо позначені значення до 10:00. Вони не підтверджують інші відрізки часу й причини подій."
      : "Analysis metrics: match totals and separately labeled samples at 10:00. They do not prove other time slices or event causes.") : rates.length || farm.length ? (language === "uk"
      ? "Показники гравця з розбору за весь матч. Вони не підтверджують окремі відрізки часу й причини подій; цілі наступної гри перевіряються окремо."
      : "Player metrics reported by the analysis across the match. They do not prove time slices or event causes; next-game goals are checked separately.") : language === "uk"
      ? "Підсумкові лічильники з розбору матчу. Вони не підтверджують час і причини подій; цілі наступної гри перевіряються окремо."
      : "Reported totals from the match analysis. They do not prove event times or causes; next-game goals are checked separately.";
    details.append(summary, values, scope);
    if (finding) details.append(finding);
    return details;
  }
};
