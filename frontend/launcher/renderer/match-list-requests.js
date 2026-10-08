// Own replacement and pagination responses for the visible match selection.
(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.WardlyMatchListRequests = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function sameSelection(a, b) {
    return a.view === "matches" && b.view === "matches" && a.heroId === b.heroId &&
      a.result === b.result && a.sort === b.sort && a.asc === b.asc;
  }

  function sameContext(a, b) {
    return sameSelection(a, b) && a.linked === b.linked && a.accountId === b.accountId;
  }

  function query(context) {
    return {
      heroId: context.heroId === null ? undefined : context.heroId,
      result: context.result === "all" ? undefined : context.result,
      sort: context.sort === "date" ? undefined : context.sort,
      order: context.asc ? "asc" : undefined
    };
  }

  function create({ current, prepare, request }) {
    let generation = 0;
    let replacing = null;
    let paging = null;

    async function replace(apply) {
      const before = { ...current() };
      if (before.view !== "matches") return false;
      const ticket = ++generation;
      replacing = ticket;
      paging = null;
      try {
        await prepare();
        if (ticket !== generation || !sameSelection(before, current())) return false;
        // Status preparation may discover the linked account on the first load.
        const context = { ...current() };
        const result = context.linked
          ? await request({ limit: Math.max(30, context.count), ...query(context) }) : null;
        if (ticket !== generation || !sameContext(context, current())) return false;
        apply(result);
        return true;
      } finally {
        if (replacing === ticket) replacing = null;
      }
    }

    async function more(apply) {
      const context = { ...current() };
      if (context.view !== "matches" || !context.linked || context.count === 0 || replacing !== null || paging !== null) return false;
      const ticket = { generation };
      paging = ticket;
      try {
        const result = await request({ limit: 30, offset: context.count, ...query(context) });
        const now = current();
        if (ticket.generation !== generation || !sameContext(context, now) || context.count !== now.count) return false;
        apply(result);
        return true;
      } finally {
        if (paging === ticket) paging = null;
      }
    }

    return {
      replace, more,
      cancel() { generation += 1; replacing = null; paging = null; }
    };
  }
  return { create };
});
