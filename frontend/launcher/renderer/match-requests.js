// Only the latest request for the visible review/locale may apply its result.
(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.WardlyMatchRequests = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function create({ current, request }) {
    let generation = 0;
    async function load(matchId, apply) {
      const context = { ...current() };
      if (context.view !== "match" || String(context.matchId) !== String(matchId)) return false;
      const ticket = ++generation;
      const result = await request(matchId);
      const now = current();
      if (ticket !== generation || now.view !== "match" ||
          String(now.matchId) !== String(context.matchId) || now.locale !== context.locale) return false;
      // Check and synchronous application share one JS turn; no await in between.
      apply(result);
      return true;
    }
    return { load, cancel() { generation += 1; } };
  }
  return { create };
});
