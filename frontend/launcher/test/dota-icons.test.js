const assert = require("node:assert/strict");
const test = require("node:test");

global.window = global;
require("../renderer/dota-data.js");
const icons = require("../renderer/dota-icons.js");

function fakeDocument() {
  const make = (tag) => {
    const listeners = {};
    const node = {
      tagName: tag.toUpperCase(),
      className: "",
      dataset: {},
      children: [],
      classList: { added: [], add(name) { this.added.push(name); } },
      append(child) { node.children.push(child); },
      remove() { node.removed = true; },
      addEventListener(name, fn) { listeners[name] = fn; },
      fire(name) { listeners[name]?.(); }
    };
    return node;
  };
  return { createElement: make };
}

test("heroes are found by id, npc name, key or display name", () => {
  assert.equal(icons.hero(8).key, "juggernaut");
  assert.equal(icons.hero("8").name, "Juggernaut");
  assert.equal(icons.hero("npc_dota_hero_antimage").name, "Anti-Mage");
  assert.equal(icons.hero("Anti-Mage").key, "antimage");
  assert.equal(icons.hero("  nature's prophet ").key, "furion");
  assert.equal(icons.hero("Largo").id, 155);
  assert.equal(icons.hero("Nobody"), null);
  assert.equal(icons.hero(null), null);
});

test("items are found by key or display name", () => {
  assert.equal(icons.itemKey("Battle Fury"), "bfury");
  assert.equal(icons.itemKey("item_black_king_bar"), "black_king_bar");
  assert.equal(icons.itemKey("maelstrom"), "maelstrom");
  assert.equal(icons.itemKey("Town Portal Scroll"), "tpscroll");
  assert.equal(icons.itemKey("Not an item"), null);
});

test("pictures point to dota-asset:// and fall back to initials", () => {
  const doc = fakeDocument();
  const heroBox = icons.heroPicture(doc, 8, "lg");
  assert.equal(heroBox.className, "dota-pic dota-hero dota-pic-lg");
  assert.equal(heroBox.dataset.fallback, "JU");
  assert.equal(heroBox.children[0].src, "dota-asset://hero/juggernaut");
  heroBox.children[0].fire("error");
  assert.equal(heroBox.children[0].removed, true);
  const item = icons.itemPicture(doc, "Black King Bar");
  assert.equal(item.children[0].src, "dota-asset://item/black_king_bar");
  assert.equal(item.dataset.fallback, "BK");
  const unknown = icons.heroPicture(doc, "Mystery Hero");
  assert.equal(unknown.children.length, 0);
  assert.equal(unknown.dataset.fallback, "MH");
  assert.equal(icons.initials("Anti-Mage"), "AM");
});

test("ability icons point to dota-asset://ability by the game name", () => {
  const doc = fakeDocument();
  const box = icons.abilityPicture(doc, "juggernaut_blade_fury", "md", "Blade Fury");
  assert.equal(box.className, "dota-pic dota-ability dota-pic-md");
  assert.equal(box.children[0].src, "dota-asset://ability/juggernaut_blade_fury");
  assert.equal(box.dataset.fallback, "BF");
  assert.equal(box.title, "Blade Fury");
  // A name that is no plain game name never reaches the asset handler.
  const odd = icons.abilityPicture(doc, "../etc/passwd");
  assert.equal(odd.children.length, 0);
});
