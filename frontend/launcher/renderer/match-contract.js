/* Validated GET /player and match-detail cores; see app/player_contracts.py. */
(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.WardlyMatchContract = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  /**
   * @typedef {Object} PlayerSyncStatus
   * @property {string} state Existing idle/queued/running/done/error values; extensible.
   * @property {string|null} at
   * @property {string|null} error
   * @property {string|null} error_code
   * @property {number|null} [fetched] Nonnegative safe integer; absent until fetched.
   */

  /**
   * @typedef {Object} PlayerStatus
   * @property {boolean} linked
   * @property {number|null} account_id Nonnegative stored int64; null when unlinked.
   * @property {string|null} source
   * @property {boolean} opendota
   * @property {PlayerSyncStatus} sync
   * @property {number} matches Nonnegative safe integer.
   * @property {number} pending_jobs Nonnegative safe integer, includes running work.
   * @property {{configured: boolean}} ai
   * @property {boolean} opendota_key No key values are returned.
   * Existing player/detected/live/review/today/goals/tilt extensions are preserved.
   */

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
