// Owned browser-like history; view rendering, scroll and IPC stay in matches.js.
(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.WardlyMatchNavigation = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function samePlace(a, b) {
    return Boolean(a && b) && a.view === b.view && String(a.matchId || "") === String(b.matchId || "");
  }

  /**
   * @param {{current: function(): {view:string,matchId?:string|number}, visit: function(Object): void}} dependencies
   * @returns {{note:function(Object, boolean=):void, back:function():boolean, forward:function():boolean}}
   */
  function create({ current, visit }) {
    const back = [];
    const forward = [];
    let moving = false;

    function note(next, enabled = true) {
      const here = current();
      if (moving || !enabled || samePlace(here, next)) return;
      back.push({ ...here });
      if (back.length > 30) back.shift();
      forward.length = 0;
    }

    function travel(from, to) {
      const place = from.pop();
      if (!place) return false;
      to.push({ ...current() });
      moving = true;
      try {
        visit({ ...place });
      } finally {
        moving = false;
      }
      return true;
    }

    return { note, back: () => travel(back, forward), forward: () => travel(forward, back) };
  }

  return { create, samePlace };
});
