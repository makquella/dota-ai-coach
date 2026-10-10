"use strict";
const assert = require("node:assert/strict");
const test = require("node:test");
const { create } = require("../renderer/career-requests");

function fixture(prepare = async () => {}) {
  const context = {view:"progress",heroId:null,locale:"en",accountId:1,linked:true};
  const pending = [], applied = [];
  const owner = create({current: () => context, prepare, request: args => new Promise((resolve,reject) => pending.push({args,resolve,reject}))});
  return {context,pending,applied,owner,load: () => owner.load(result => applied.push(result))};
}
const prepared = () => new Promise(resolve => setImmediate(resolve));

test("rapid hero A/B/A requests allow only the latest response to apply", async () => {
  const f = fixture(); f.context.heroId = 8;
  const a = f.load(); await prepared();
  f.context.heroId = 1; const b = f.load(); await prepared();
  f.context.heroId = 8; const latest = f.load(); await prepared();
  f.pending[2].resolve("new A"); assert.equal(await latest, true);
  f.pending[0].resolve("old A"); f.pending[1].resolve("B");
  assert.deepEqual(await Promise.all([a,b]), [false,false]);
  assert.deepEqual(f.applied, ["new A"]);
  assert.deepEqual(f.pending.map(p => p.args), [{heroId:8},{heroId:1},{heroId:8}]);
});

test("changed locale, hero, view or account cannot receive an earlier response", async () => {
  for (const patch of [{locale:"uk"},{heroId:8},{view:"home"},{accountId:2},{linked:false}]) {
    const f = fixture(); const work = f.load(); await prepared();
    Object.assign(f.context,patch); f.pending[0].resolve("stale");
    assert.equal(await work, false); assert.deepEqual(f.applied, []);
  }
});

test("leaving and returning to the same hero invalidates the previous visit", async () => {
  const f = fixture(); const old = f.load(); await prepared();
  f.context.view = "home"; f.owner.cancel(); f.context.view = "progress";
  const latest = f.load(); await prepared();
  f.pending[0].resolve("old visit"); f.pending[1].resolve("new visit");
  assert.deepEqual(await Promise.all([old,latest]), [false,true]);
  assert.deepEqual(f.applied, ["new visit"]);
});

test("superseded or locale-changed status preparation cannot start a career fetch", async () => {
  const status = [];
  const f = fixture(() => new Promise(resolve => status.push(resolve)));
  const old = f.load(); f.context.heroId = 8; const latest = f.load();
  status[0](); assert.equal(await old, false); assert.equal(f.pending.length, 0);
  status[1](); await prepared(); f.pending[0].resolve("hero 8");
  assert.equal(await latest, true);
  const localized = f.load(); f.context.locale = "uk"; status[2]();
  assert.equal(await localized, false); assert.equal(f.pending.length, 1);
});

test("first status preparation may discover an account; unlinked and hidden views do not fetch", async () => {
  const f = fixture(async () => {f.context.accountId = 2; f.context.linked = true;});
  f.context.accountId = null; f.context.linked = false;
  const work = f.load(); await prepared(); f.pending[0].resolve("linked");
  assert.equal(await work, true); assert.deepEqual(f.pending[0].args, {});
  const unlinked = fixture(); unlinked.context.linked = false;
  assert.equal(await unlinked.load(), true); assert.deepEqual(unlinked.applied, [null]);
  unlinked.context.view = "matches"; assert.equal(await unlinked.load(), false);
  assert.equal(unlinked.pending.length, 0);
});

test("quiet and foreground callbacks share the same generation", async () => {
  const f = fixture();
  const quiet = f.owner.load(value => f.applied.push({quiet:value})); await prepared();
  const foreground = f.owner.load(value => f.applied.push({foreground:value})); await prepared();
  f.pending[1].resolve("latest"); assert.equal(await foreground, true);
  f.pending[0].resolve("stale poll"); assert.equal(await quiet, false);
  assert.deepEqual(f.applied, [{foreground:"latest"}]);
});

test("normalized errors apply; a rejected external request does not prevent retry", async () => {
  const f = fixture(); const failed = f.load(); await prepared();
  f.pending[0].reject(new Error("transport failure")); await assert.rejects(failed, /transport failure/);
  const retry = f.load(); await prepared();
  f.pending[1].resolve({ok:false,code:"offline"}); assert.equal(await retry, true);
  assert.deepEqual(f.applied, [{ok:false,code:"offline"}]);
});
