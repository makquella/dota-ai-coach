"use strict";
const assert = require("node:assert/strict");
const test = require("node:test");
const { create } = require("../renderer/match-requests");

function fixture() {
  const context = {view:"match",matchId:"1",locale:"en"};
  const pending = [];
  const applied = [];
  const owner = create({current: () => context, request: id => new Promise(resolve => pending.push({id,resolve}))});
  return {context,pending,applied,owner,load: id => owner.load(id, value => applied.push(value))};
}

test("a later response applies once and an older response cannot overwrite it", async () => {
  const f = fixture();
  const old = f.load("1"), latest = f.load("1");
  f.pending[1].resolve("new");
  assert.equal(await latest, true);
  f.pending[0].resolve("old");
  assert.equal(await old, false);
  assert.deepEqual(f.applied, ["new"]);
});

test("leaving and returning to the same review rejects the old generation", async () => {
  const f = fixture();
  const old = f.load("1");
  f.context.view = "home";
  f.owner.cancel();
  f.context.view = "match";
  const latest = f.load("1");
  f.pending[0].resolve("old");
  f.pending[1].resolve("new");
  assert.equal(await old, false);
  assert.equal(await latest, true);
  assert.deepEqual(f.applied, ["new"]);
});

test("another review or locale cannot receive a pending result", async () => {
  for (const patch of [{matchId:"2"},{locale:"uk"},{view:"matches"}]) {
    const f = fixture();
    const work = f.load("1");
    Object.assign(f.context, patch);
    f.pending[0].resolve("wrong context");
    assert.equal(await work, false);
    assert.deepEqual(f.applied, []);
  }
});

test("a hidden or mismatched review starts no request", async () => {
  const f = fixture();
  assert.equal(await f.load("2"), false);
  f.context.view = "home";
  assert.equal(await f.load("1"), false);
  assert.equal(f.pending.length, 0);
});

test("normalized request errors apply to the current review; rejected requests do not wedge it", async () => {
  let fails = true;
  const applied = [];
  const owner = create({current: () => ({view:"match",matchId:"1",locale:"en"}), request: async () => {
    if (fails) throw new Error("transport failure");
    return {ok:false,code:"offline"};
  }});
  await assert.rejects(owner.load("1", value => applied.push(value)), /transport failure/);
  fails = false;
  assert.equal(await owner.load("1", value => applied.push(value)), true);
  assert.deepEqual(applied, [{ok:false,code:"offline"}]);
});
