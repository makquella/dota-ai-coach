// Shared status reads coalesce; account mutations invalidate older reads.
(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.WardlyPlayerStatusRequests = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function create({ request, apply }) {
    let generation = 0;
    let pending = null;
    function load() {
      if (pending) return pending.promise;
      const entry = { generation, promise: null };
      pending = entry;
      entry.promise = (async () => {
        try {
          // Defer even a synchronous transport throw until pending is installed.
          const result = await Promise.resolve().then(request);
          if (entry.generation !== generation) return false;
          apply(result);
          return true;
        } finally {
          if (pending === entry) pending = null;
        }
      })();
      return entry.promise;
    }
    return { load, cancel() { generation += 1; pending = null; } };
  }
  return { create };
});
