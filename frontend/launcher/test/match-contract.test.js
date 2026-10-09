"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const { combatScore } = require("../renderer/match-contract");

test("K/D/A retains every known counter independently, including zero", () => {
  assert.equal(combatScore({ kills: 0, deaths: null, assists: 5 }), "0 / — / 5");
  assert.equal(combatScore({ kills: null, deaths: 4, assists: 9 }), "— / 4 / 9");
  assert.equal(combatScore({ assists: 0 }), "— / — / 0");
  assert.equal(combatScore({ kills: 0, deaths: 0, assists: 0 }), "0 / 0 / 0");
  assert.equal(combatScore({ kills: 11, deaths: 2, assists: 14 }, "/"), "11/2/14");
});

test("entirely unknown K/D/A stays one dash for old and loading reviews", () => {
  for (const value of [null, undefined, {}, { kills: null, deaths: null, assists: null }]) {
    assert.equal(combatScore(value), "—");
  }
});

test("malformed counters cannot become visible facts or injected markup", () => {
  for (const value of [true, "2", -1, 0.5, Infinity, NaN, Number.MAX_SAFE_INTEGER + 1, "<img src=x onerror=alert(1)>"]) {
    assert.equal(combatScore({ kills: value, deaths: 0 }), "— / 0 / —");
  }
  assert.equal(combatScore({ kills: Number.MAX_SAFE_INTEGER }), `${Number.MAX_SAFE_INTEGER} / — / —`);
});
