"use strict";
const assert = require("node:assert/strict");
const test = require("node:test");
const { create, samePlace } = require("../renderer/match-navigation");

function controller() {
  let place = { view: "home" };
  const visited = [];
  const history = create({
    current: () => place,
    visit: next => { history.note(next); place = next; visited.push(next); }
  });
  return {
    history, visited,
    go(next) { history.note(next); place = next; },
    place: () => place
  };
}

test("tab/review back and forward do not record history visits as new navigation", () => {
  const c = controller();
  c.go({ view: "matches" });
  c.go({ view: "match", matchId: "42" });
  c.go({ view: "progress" });
  assert.equal(c.history.back(), true);
  assert.deepEqual(c.place(), { view: "match", matchId: "42" });
  assert.equal(c.history.back(), true);
  assert.deepEqual(c.place(), { view: "matches" });
  assert.equal(c.history.forward(), true);
  assert.equal(c.history.forward(), true);
  assert.deepEqual(c.place(), { view: "progress" });
  assert.equal(c.history.forward(), false);
});

test("same place is a no-op and a new route clears the forward branch", () => {
  const c = controller();
  c.go({ view: "match", matchId: 42 });
  c.go({ view: "match", matchId: "42" });
  assert.equal(c.history.back(), true);
  assert.deepEqual(c.place(), { view: "home" });
  c.go({ view: "profile" });
  assert.equal(c.history.forward(), false);
  assert.equal(samePlace(null, { view: "home" }), false);
});

test("history retains the latest thirty places and starts with empty travel", () => {
  const c = controller();
  assert.equal(c.history.back(), false);
  assert.equal(c.history.forward(), false);
  for (let id = 1; id <= 40; id += 1) c.go({ view: "match", matchId: String(id) });
  for (let step = 0; step < 30; step += 1) assert.equal(c.history.back(), true);
  assert.deepEqual(c.place(), { view: "match", matchId: "10" });
  assert.equal(c.history.back(), false);
  for (let step = 0; step < 30; step += 1) assert.equal(c.history.forward(), true);
  assert.deepEqual(c.place(), { view: "match", matchId: "40" });
});

test("caller mutation and independent viewers cannot change retained places", () => {
  const c = controller();
  const other = controller();
  const original = { view: "matches" };
  c.go(original);
  c.go({ view: "match", matchId: "42" });
  original.view = "profile";
  assert.equal(c.history.back(), true);
  assert.deepEqual(c.place(), { view: "matches" });
  assert.equal(other.history.back(), false);
});

test("a visitor failure releases the movement guard and disabled notes are ignored", () => {
  let place = { view: "home" };
  let fails = true;
  const history = create({current: () => place, visit: () => { if (fails) throw new Error("draw failed"); }});
  history.note({ view: "matches" }, false);
  assert.equal(history.back(), false);
  history.note({ view: "matches" });
  place = { view: "matches" };
  assert.throws(() => history.back(), /draw failed/);
  fails = false;
  history.note({ view: "profile" });
  assert.equal(history.back(), true);
});
