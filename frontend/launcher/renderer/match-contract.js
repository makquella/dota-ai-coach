/* Validated player status/list/detail/progress cores; see app/player_contracts.py. */
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
   * @typedef {CombatCounters & Object} MatchListItem
   * @property {number} match_id Nonnegative stored int64.
   * @property {number|null} [hero_id]
   * @property {string|null} [hero]
   * @property {boolean|null} [win] Unknown result stays null/absent.
   * @property {string[]} sources
   * @property {string|null} parse_status
   * @property {boolean} has_analysis
   * @property {boolean} has_timeline
   * @property {string[]|null} [items]
   * @property {string|null} [note]
   */

  /**
   * @typedef {Object} MatchList
   * @property {boolean} linked
   * @property {MatchListItem[]} items
   * @property {number} total Nonnegative safe integer; filtered total, not page size.
   * @property {{games:number,wins:number,winrate:number|null,avg_score:number|null}|null} [stats]
   * @property {{hero_id:number,hero:string|null,games:number}[]|null} [heroes]
   * @property {{hero_id:number|null,win:boolean|null,sort:string,ascending:boolean}|null} [filters]
   * @property {PlayerSyncStatus|null} [sync]
   * @property {{count:number,turbo:number,of:number}|null} [skipped]
   * Existing row/stat/filter extensions are preserved; unlinked responses omit them.
   */

  /**
   * @typedef {Object} Career
   * @property {boolean} linked Unlinked responses contain only this field.
   * @property {number|null} [matches] Nonnegative safe integer; zero when linked but empty.
   * @property {number|null} [analyzed]
   * @property {number|null} [wins]
   * @property {number|null} [losses]
   * @property {number|null} [winrate] 0-100 integer, null with no decided games.
   * @property {{win:boolean,length:number}|null} [streak]
   * @property {{hero:string,hero_id:number|null,matches:number,wins:number,winrate:number|null}[]|null} [heroes]
   * @property {number|null} [hero_filter]
   * @property {{hero_id:number,hero:string|null,games:number}[]|null} [hero_choices]
   * @property {{match_id:number,hero:string|null,win:boolean|null}[]|null} [series]
   * Averages, trends, findings, coach/questions and other nested extensions remain intact.
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
