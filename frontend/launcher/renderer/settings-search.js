// «Найти настройку»: a search field over Settings. Every row (`.setting`, the
// AI coach card, the hotkey list, the developer sections) is matched with its
// card title, its zone title and the folded section it sits in, plus the
// row's `data-search` keywords (both languages, so «звук» finds «Голос»).
// Rows without a match are hidden (class `search-out`; a zone whose cards are
// all out hides itself through the `.zone` rule in styles.css), folded
// sections with a match open and close again when the search is cleared, and
// the matching words are highlighted with the CSS Custom Highlight API (no DOM
// changes, so the texts app.js rewrites every second stay its own).
// The pure helpers are UMD so test/settings-search.test.js can run them.
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    root.SettingsSearch = api;
  }
})(typeof self !== "undefined" ? self : this, function () {
  // Lower case, «ё» as «е», quotes and dashes as spaces: the same length as
  // the input for one-to-one highlights (`fold`), then collapsed (`normalize`).
  function fold(text) {
    return String(text == null ? "" : text)
      .toLowerCase()
      .replace(/ё/g, "е")
      .replace(/[«»“”"'’‘—–\-_/·.,:;!?()]/g, " ");
  }

  function normalize(text) {
    return fold(text).replace(/\s+/g, " ").trim();
  }

  // The words of a query; every one of them must be found (in any order).
  function terms(query) {
    return [...new Set(normalize(query).split(" ").filter(Boolean))];
  }

  // A word counts from its start: «ключ» finds «ключи» and «ключа», not
  // «включить» or «подключить» (Russian endings change, beginnings rarely).
  const LETTER = /[\p{L}\p{N}]/u;

  function startsAt(text, word, from) {
    for (let at = text.indexOf(word, from); at >= 0; at = text.indexOf(word, at + 1)) {
      if (at === 0 || !LETTER.test(text[at - 1])) {
        return at;
      }
    }
    return -1;
  }

  function matches(haystack, words) {
    if (!words.length) {
      return true;
    }
    const text = normalize(haystack);
    return words.every((word) => startsAt(text, word, 0) >= 0);
  }

  // [start, end) spans of every word in `text` (for highlights), merged and
  // sorted; none when folding changed the length (a rare letter whose lower
  // case is longer), so a highlight never lands on the wrong letters.
  function spans(text, words) {
    const source = String(text == null ? "" : text);
    const folded = fold(source);
    if (folded.length !== source.length || !words.length) {
      return [];
    }
    const found = [];
    for (const word of words) {
      let from = 0;
      while (word && from <= folded.length) {
        const at = startsAt(folded, word, from);
        if (at < 0) {
          break;
        }
        found.push([at, at + word.length]);
        from = at + word.length;
      }
    }
    found.sort((a, b) => a[0] - b[0]);
    const merged = [];
    for (const span of found) {
      const last = merged[merged.length - 1];
      if (last && span[0] <= last[1]) {
        last[1] = Math.max(last[1], span[1]);
      } else {
        merged.push([...span]);
      }
    }
    return merged;
  }

  // --- the page ----------------------------------------------------------------

  const ROWS = ".setting, details.hotkeys, #ai-settings-root > .card, #dev-tools .facts, #dev-tools .dev-section";
  const SKIP = "script, style, option, pre, textarea";
  const HIGHLIGHT = "settings-search";

  function attach({ view, input, empty, onChange }) {
    if (!view || !input) {
      return null;
    }
    let words = [];
    // Folded sections the search opened, to close them again afterwards.
    const opened = new Set();
    let timer = null;
    let applying = false;

    // The visible words of an element: not a report or statistics preview (a
    // <pre> with the whole report) or what the player typed.
    const textOf = (element) => {
      const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
      const parts = [];
      for (let node = walker.nextNode(); node; node = walker.nextNode()) {
        if (!node.parentElement?.closest(SKIP)) {
          parts.push(node.nodeValue);
        }
      }
      return parts.join(" ");
    };

    // A row's own text and keywords, and the titles above it (not their hints:
    // «Language, start with Windows, updates» under «App» would find every row
    // of the zone for «updates»).
    const context = (row) => {
      const parts = [textOf(row), row.dataset.search || ""];
      const cardEl = row.closest(".card");
      if (cardEl && cardEl !== row) {
        const head = cardEl.querySelector(":scope > .card-head");
        parts.push(head ? head.textContent : "", cardEl.dataset.search || "");
      }
      const zoneEl = row.closest(".zone");
      const zoneTitle = zoneEl && zoneEl.querySelector(":scope > .zone-head .zone-title");
      if (zoneTitle) {
        parts.push(zoneTitle.textContent);
      }
      for (let details = row.closest("details"); details; details = details.parentElement && details.parentElement.closest("details")) {
        const title = details.querySelector(":scope > summary > span:not(.dev-hint)");
        if (title && details !== row) {
          parts.push(title.textContent, details.dataset.search || "");
        }
      }
      return parts.join(" ");
    };

    const highlight = (elements) => {
      const registry = typeof CSS !== "undefined" ? CSS.highlights : null;
      if (!registry || typeof Highlight === "undefined") {
        return;
      }
      registry.delete(HIGHLIGHT);
      if (!words.length) {
        return;
      }
      const ranges = [];
      for (const element of elements) {
        const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
        for (let node = walker.nextNode(); node; node = walker.nextNode()) {
          if (!node.nodeValue.trim() || node.parentElement?.closest(SKIP)) {
            continue;
          }
          for (const [start, end] of spans(node.nodeValue, words)) {
            const range = document.createRange();
            range.setStart(node, start);
            range.setEnd(node, end);
            ranges.push(range);
          }
        }
      }
      if (ranges.length) {
        registry.set(HIGHLIGHT, new Highlight(...ranges));
      }
    };

    const apply = () => {
      if (applying) {
        return;
      }
      applying = true;
      try {
        const rows = [...view.querySelectorAll(ROWS)];
        const groups = [...view.querySelectorAll(".card, #ai-settings-root, details.settings-more, details.dev")];
        if (!words.length) {
          for (const element of view.querySelectorAll(".search-out")) {
            element.classList.remove("search-out");
          }
          for (const details of opened) {
            details.open = false;
          }
          opened.clear();
          if (empty) {
            empty.hidden = true;
          }
          highlight([]);
          return;
        }
        const shown = [];
        for (const row of rows) {
          const hit = matches(context(row), words);
          row.classList.toggle("search-out", !hit);
          if (hit) {
            shown.push(row);
          }
        }
        // A card or a folded section without a row left is out too; one with a
        // row left opens (and closes again when the search is cleared).
        for (const group of groups) {
          const inside = shown.some((row) => group.contains(row));
          group.classList.toggle("search-out", !inside);
          if (inside && group.tagName === "DETAILS" && !group.open) {
            group.open = true;
            opened.add(group);
          }
        }
        for (const row of shown) {
          if (row.tagName === "DETAILS" && !row.open) {
            row.open = true;
            opened.add(row);
          }
        }
        if (empty) {
          empty.hidden = shown.length > 0;
        }
        highlight([...shown, ...view.querySelectorAll(".card-head, .zone-head, summary")].filter((element) => !element.closest(".search-out")));
      } finally {
        applying = false;
      }
    };

    const set = (query) => {
      const next = terms(query);
      const changed = next.join(" ") !== words.join(" ");
      words = next;
      if (changed) {
        apply();
        if (onChange) {
          onChange(words.length > 0);
        }
      }
    };

    input.addEventListener("input", () => {
      clearTimeout(timer);
      timer = setTimeout(() => set(input.value), 60);
    });
    input.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        if (input.value) {
          input.value = "";
          set("");
        } else {
          input.blur();
        }
      }
    });
    // The AI coach card is drawn again on every load, and the texts change
    // with the status: keep the filter and the highlights on the new nodes.
    const observer = typeof MutationObserver === "function" ? new MutationObserver(() => {
      if (words.length) {
        clearTimeout(timer);
        timer = setTimeout(apply, 120);
      }
    }) : null;
    observer?.observe(view, { childList: true, subtree: true, characterData: true });

    return {
      clear() {
        input.value = "";
        set("");
      },
      focus() {
        input.focus();
        input.select();
      },
      active: () => words.length > 0,
      apply
    };
  }

  return { fold, normalize, terms, matches, spans, attach };
});
