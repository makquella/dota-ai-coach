// Profile and friends have independent owners with the same visible context.
(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.WardlyProfileRequests = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function sameView(a, b) {
    return a.view === "profile" && b.view === "profile" && a.locale === b.locale;
  }

  function create({ current, prepare = async () => {}, request }) {
    let generation = 0;
    async function load(apply, args = {}) {
      const before = { ...current() };
      if (before.view !== "profile") return false;
      const ticket = ++generation;
      await prepare();
      if (ticket !== generation || !sameView(before, current())) return false;
      // The first status preparation can discover the selected account.
      const context = { ...current() };
      const result = context.linked ? await request(args) : null;
      const now = current();
      if (ticket !== generation || !sameView(context, now) ||
          context.accountId !== now.accountId || context.linked !== now.linked) return false;
      apply(result);
      return true;
    }
    return { load, cancel() { generation += 1; } };
  }
  return { create };
});
