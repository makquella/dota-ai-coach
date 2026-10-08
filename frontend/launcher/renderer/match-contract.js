/* The validated core of GET /player/matches/{id}; see app/player_contracts.py. */
(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.WardlyMatchContract = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  /**
   * @typedef {Object} CombatCounters
   * @property {number|null} [kills] Nonnegative integer, null/absent when unknown.
   * @property {number|null} [deaths] Nonnegative integer, null/absent when unknown.
   * @property {number|null} [assists] Nonnegative integer, null/absent when unknown.
   */

  /**
   * @typedef {Object} MatchDetail
   * @property {number} match_id SQLite nonnegative int64; large IDs need a future string contract.
   * @property {CombatCounters} summary Other existing summary fields are preserved.
   * @property {string[]|null} sources
   * @property {string} parse_status
   * @property {{headline: CombatCounters}|null} analysis Other review sections are preserved.
   * @property {boolean} loading
   */

  /**
   * Render each counter independently, retaining zero and partial measurements.
   * Defensive checks also handle older/malformed local data before it reaches textContent.
   * @param {CombatCounters|null|undefined} counters
   * @param {string} [separator]
   * @returns {string}
   */
  function combatScore(counters, separator = " / ") {
    const values = ["kills", "deaths", "assists"].map((key) => {
      const value = counters?.[key];
      return Number.isSafeInteger(value) && value >= 0 ? String(value) : "—";
    });
    return values.every((value) => value === "—") ? "—" : values.join(separator);
  }

  return { combatScore };
});
