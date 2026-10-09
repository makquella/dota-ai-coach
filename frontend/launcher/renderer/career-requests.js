// Only the latest visible Progress selection may apply a career response.
(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.WardlyCareerRequests = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function sameSelection(a, b) {
    return a.view === "progress" && b.view === "progress" && a.heroId === b.heroId && a.locale === b.locale;
  }

  function create({ current, prepare, request }) {
    let generation = 0;
    async function load(apply) {
      const before = { ...current() };
      if (before.view !== "progress") return false;
      const ticket = ++generation;
      await prepare();
      if (ticket !== generation || !sameSelection(before, current())) return false;
      // The first status load may discover the selected account.
      const context = { ...current() };
      const result = context.linked
        ? await request(context.heroId === null ? {} : { heroId: context.heroId }) : null;
      const now = current();
      if (ticket !== generation || !sameSelection(context, now) ||
          context.accountId !== now.accountId || context.linked !== now.linked) return false;
      apply(result);
      return true;
    }
    return { load, cancel() { generation += 1; } };
  }
  return { create };
});
