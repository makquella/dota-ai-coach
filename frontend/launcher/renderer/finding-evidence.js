"use strict";

// Only measurements produced by the local analyzer can become source labels.
(() => {
  const sources = {
    obs_placed: {"opendota.obs_log": "log_count", "opendota.obs_placed": "reported_total", "gsi.inventory_changes": "inventory_estimate"},
    sen_placed: {"opendota.sen_log": "log_count", "opendota.sen_placed": "reported_total"},
    lh10: {"opendota.lh_t": "sample", "gsi.samples": ["sample", "carried_sample"]},
    lane_deaths: {"opendota.kills_log": "log_count", "gsi.deaths": "log_count"}
  };
  const fields = {wards_low: ["obs_placed"], wards_high: ["obs_placed", "sen_placed"], lh10_low: ["lh10"], lh10_great: ["lh10"], lane_deaths: ["lane_deaths"]};
  const params = {obs_placed: "obs", sen_placed: "sen", lh10: "lh10", lane_deaths: "count"};
  const count = (value) => Number.isSafeInteger(value) && value >= 0;
  function valid(row) {
    if (!row || typeof row.field !== "string" || typeof row.source !== "string" || typeof row.precision !== "string" || !Object.hasOwn(sources, row.field) || !count(row.value)) return false;
    const allowed = sources[row.field][row.source];
    if (!(Array.isArray(allowed) ? allowed.includes(row.precision) : allowed && allowed === row.precision)) return false;
    if (row.field === "lh10") {
      if (!count(row.observed_at) || (row.precision === "sample" ? row.observed_at !== 600 : row.observed_at < 570 || row.observed_at >= 600)) return false;
    } else if (row.observed_at !== null) return false;
    const coverage = row.coverage;
    if (coverage !== null && !validCoverage(coverage)) return false;
    return row.source.startsWith("gsi.") ? coverage !== null : coverage === null;
  }
  function validCoverage(coverage) {
    if (!coverage || !count(coverage.start) || !count(coverage.end) || coverage.start > coverage.end || typeof coverage.complete !== "boolean" || !Array.isArray(coverage.gaps)) return false;
    if (coverage.gaps.some(g => !Array.isArray(g) || g.length !== 2 || !g.every(count) || g[0] < coverage.start || g[0] >= g[1] || g[1] > coverage.end)) return false;
    return !coverage.complete || (!coverage.gaps.length && coverage.start <= 15);
  }
  const clock = seconds => `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
  function coverageNode(c, language) {
    const uk = language === "uk";
    const node = document.createElement("p");
    node.textContent = `${uk ? "Запис" : "Recording"}: ${clock(c.start)}–${clock(c.end)} · ${c.complete ? (uk ? "покриття повного матчу" : "full match coverage") : (uk ? "неповні дані" : "partial data")}`;
    if (c.gaps.length) node.textContent += ` · ${uk ? "пропуски" : "gaps"}: ${c.gaps.map(g => g.map(clock).join("–")).join(", ")}`;
    return node;
  }
  function renderRows(values, language) {
    const rows = (Array.isArray(values) ? values : []).filter(valid);
    if (!rows.length) return null;
    const uk = language === "uk";
    const labels = uk ? {obs_placed: "Обсервер-варди", sen_placed: "Сентрі", lh10: "Добивання", lane_deaths: "Смерті до 10:00"} : {obs_placed: "Observer wards", sen_placed: "Sentry wards", lh10: "Last hits", lane_deaths: "Deaths before 10:00"};
    const methods = uk ? {log_count: "зафіксовані події", reported_total: "підсумок OpenDota", inventory_estimate: "оцінка за змінами інвентарю", sample: "зразок", carried_sample: "останній доступний зразок"} : {log_count: "recorded events", reported_total: "OpenDota total", inventory_estimate: "estimate from inventory changes", sample: "sample", carried_sample: "last available sample"};
    const details = document.createElement("details");
    details.className = "finding-evidence muted small";
    const summary = document.createElement("summary");
    summary.textContent = uk ? "Джерело й покриття даних" : "Source and data coverage";
    details.append(summary);
    for (const row of rows) {
      const value = document.createElement("p");
      value.textContent = `${labels[row.field]}: ${row.value} · ${methods[row.precision]}${row.observed_at !== null ? ` · ${clock(row.observed_at)}` : ""} · ${row.source}`;
      details.append(value);
      if (row.coverage) details.append(coverageNode(row.coverage, language));
    }
    const scope = document.createElement("p");
    scope.textContent = uk ? "Невідомі інтервали не дорівнюють нулю. Ці дані не доводять причин подій." : "Unknown intervals do not mean zero. These measurements do not prove event causes.";
    details.append(scope);
    return details;
  }
  const api = {
    valid,
    renderRows,
    renderCoverage(coverage, language) {
      if (!validCoverage(coverage)) return null;
      const node = coverageNode(coverage, language);
      node.className = "review-source muted small";
      return node;
    },
    render(finding, language) {
      const permitted = Object.hasOwn(fields, finding?.id) ? fields[finding.id] : [];
      return renderRows((Array.isArray(finding?.evidence) ? finding.evidence : []).filter(row => permitted.includes(row?.field) && count(finding?.params?.[params[row.field]]) && row.value === finding.params[params[row.field]]), language);
    }
  };
  if (typeof module !== "undefined") module.exports = api;
  if (typeof window !== "undefined") window.WardlyFindingEvidence = api;
})();
