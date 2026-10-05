// Hero portraits and item icons as small DOM elements, shared by the panel and
// the overlay. Pictures come from dota-asset:// (main process, cached from
// Valve's CDN); when one cannot be loaded (offline on first use, an unknown
// name) the element keeps a quiet text fallback instead of a broken image.
(function (root, factory) {
  const api = factory(() => globalThis.DotaData || root.DotaData || { heroes: {}, items: {} });
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    root.DotaIcons = api;
  }
})(typeof self !== "undefined" ? self : this, (getData) => {
  let heroByName = null;
  let itemByName = null;
  let itemKeys = null;
  let itemNames = null;

  function normalize(value) {
    return String(value ?? "")
      .trim()
      .toLowerCase()
      .replace(/[’`]/g, "'");
  }

  function indexes() {
    if (heroByName) {
      return;
    }
    const data = getData();
    heroByName = new Map();
    for (const [id, [name, key]] of Object.entries(data.heroes || {})) {
      heroByName.set(normalize(name), { id: Number(id), name, key });
      heroByName.set(key, { id: Number(id), name, key });
    }
    itemByName = new Map();
    itemKeys = new Set();
    itemNames = new Map();
    for (const [name, key] of Object.entries(data.items || {})) {
      itemByName.set(normalize(name), key);
      itemKeys.add(key);
      if (!itemNames.has(key)) {
        itemNames.set(key, name);
      }
    }
  }

  // id (number or digits), "npc_dota_hero_x", picture key or display name -> {id, name, key}
  function hero(value) {
    if (value === null || value === undefined || value === "") {
      return null;
    }
    indexes();
    const data = getData();
    const text = String(value).trim();
    if (/^\d+$/.test(text)) {
      const row = (data.heroes || {})[text];
      return row ? { id: Number(text), name: row[0], key: row[1] } : null;
    }
    const key = normalize(text).replace(/^npc_dota_hero_/, "");
    return heroByName.get(key) || heroByName.get(normalize(text)) || null;
  }

  // picture key ("bfury", "item_bfury") or display name ("Battle Fury") -> key
  function itemKey(value) {
    indexes();
    const text = normalize(value).replace(/^item_/, "");
    if (!text) {
      return null;
    }
    if (itemKeys.has(text)) {
      return text;
    }
    return itemByName.get(text) || null;
  }

  // picture key ("bfury") -> the in-game name ("Battle Fury"), else null.
  function itemName(value) {
    const key = itemKey(value);
    return key ? itemNames.get(key) || null : null;
  }

  function initials(name) {
    const words = String(name || "?")
      .replace(/[^\p{L}\p{N}\s-]/gu, "")
      .split(/[\s-]+/)
      .filter(Boolean);
    const letters = words.length > 1 ? words[0][0] + words[1][0] : (words[0] || "?").slice(0, 2);
    return letters.toUpperCase();
  }

  function picture(doc, { src, label, className, size }) {
    const box = doc.createElement("span");
    box.className = `dota-pic ${className} dota-pic-${size || "sm"}`;
    box.dataset.fallback = initials(label);
    if (label) {
      box.title = label;
    }
    if (src) {
      const img = doc.createElement("img");
      img.alt = "";
      img.decoding = "async";
      img.loading = "lazy";
      img.draggable = false;
      img.addEventListener("load", () => box.classList.add("dota-pic-loaded"));
      img.addEventListener("error", () => img.remove());
      img.src = src;
      box.append(img);
    }
    return box;
  }

  // A 16:9 hero portrait; `size`: sm (table rows), md, lg (review header).
  function heroPicture(doc, value, size = "sm") {
    const found = hero(value);
    const label = found ? found.name : String(value ?? "");
    return picture(doc, {
      src: found ? `dota-asset://hero/${found.key}` : null,
      label,
      className: "dota-hero",
      size
    });
  }

  // The hero to the waist on a transparent background (400×250), drawn large
  // behind a header; no initials fallback (it is decoration: the name is
  // written next to it), so a missing picture leaves the header plain.
  function heroArt(doc, value) {
    const found = hero(value);
    if (!found) {
      return null;
    }
    const box = doc.createElement("span");
    box.className = "dota-hero-art";
    box.setAttribute("aria-hidden", "true");
    const img = doc.createElement("img");
    img.alt = "";
    img.decoding = "async";
    img.draggable = false;
    img.addEventListener("load", () => box.classList.add("dota-pic-loaded"));
    img.addEventListener("error", () => box.remove());
    img.src = `dota-asset://hero-crop/${found.key}`;
    box.append(img);
    return box;
  }

  function itemPicture(doc, value, size = "sm", label = null) {
    const key = itemKey(value);
    return picture(doc, {
      src: key ? `dota-asset://item/${key}` : null,
      // A bare key ("bfury") is named as the game names it (the hover title).
      label: label || itemName(value) || String(value ?? ""),
      className: "dota-item",
      size
    });
  }

  // An ability's square icon by its game name ("juggernaut_blade_fury"); the
  // in-game name is the label and the initials fallback.
  function abilityPicture(doc, key, size = "sm", label = null) {
    const name = String(key ?? "").trim().toLowerCase();
    return picture(doc, {
      src: /^[a-z0-9_]{1,64}$/.test(name) ? `dota-asset://ability/${name}` : null,
      label: label || name.replace(/_/g, " "),
      className: "dota-ability",
      size
    });
  }

  return { hero, itemKey, itemName, initials, heroPicture, heroArt, itemPicture, abilityPicture };
});
