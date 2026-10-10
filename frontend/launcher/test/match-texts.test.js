"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const { create } = require("../renderer/match-texts");

test("match copy binds the view's number/decimal/clock formatters", () => {
  const calls = [];
  const format = (kind) => (value) => { calls.push([kind, value]); return `${kind}(${value})`; };
  const text = create({ number: format("number"), decimal: format("decimal"), clock: format("clock"), plural: format("plural") });
  for (const lang of ["uk", "en"]) {
    const facts = text[lang].sectionFacts.fights({ stuns: 2.5, enemy_stuns: 3.5, tower_damage: 400, enemy_tower_damage: 500 }).filter(Boolean).join(" ");
    assert.ok(facts.includes("decimal(2.5)") && facts.includes("decimal(3.5)"));
    assert.ok(facts.includes("number(400)") && facts.includes("number(500)"));
    const items = text[lang].sectionFacts.items({ first_item: { item: "Maelstrom", t: 1200 }, save_item: { item: "Glimmer Cape", t: 1400 } }).filter(Boolean).join(" ");
    assert.ok(items.includes("clock(1200)") && items.includes("clock(1400)"));
  }
  assert.equal(calls.length, 12);
});

test("Ukrainian plurals keep using the supplied function", () => {
  const calls = [];
  const text = create({ plural: (...args) => { calls.push(args); return "chosen-form"; } });
  assert.equal(text.uk.pfNeedSparks(3), "Ще 3 chosen-form");
  assert.deepEqual(calls, [[3, "іскра", "іскри", "іскор"]]);
});

test("formatters can follow locale switches without recreating the tables", () => {
  let locale = "en";
  const text = create({ decimal: (value) => `${locale}:${value}` });
  assert.ok(text.en.sectionFacts.fights({ stuns: 2.5 }).filter(Boolean).join(" ").includes("en:2.5"));
  locale = "uk";
  assert.ok(text.uk.sectionFacts.fights({ stuns: 2.5 }).filter(Boolean).join(" ").includes("uk:2.5"));
});
