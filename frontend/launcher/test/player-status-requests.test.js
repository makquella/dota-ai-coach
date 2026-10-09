"use strict";
const assert = require("node:assert/strict");
const test = require("node:test");
const { create } = require("../renderer/player-status-requests");

function fixture() {
  const pending = [], applied = [];
  const owner = create({request: () => new Promise((resolve,reject) => pending.push({resolve,reject})), apply: result => applied.push(result)});
  return {pending,applied,owner};
}
const started = () => new Promise(resolve => setImmediate(resolve));

test("concurrent consumers share a status request and apply its response once", async () => {
  const f = fixture(); const a = f.owner.load(), b = f.owner.load();
  assert.equal(a,b); await started(); assert.equal(f.pending.length, 1);
  f.pending[0].resolve({ok:true,data:{linked:true,account_id:1}});
  assert.deepEqual(await Promise.all([a,b]), [true,true]);
  assert.equal(f.applied.length, 1);
  const next = f.owner.load(); await started(); assert.equal(f.pending.length, 2);
  f.pending[1].resolve("fresh"); assert.equal(await next, true);
});

test("an account mutation invalidates every consumer of an older read", async () => {
  const f = fixture(); const a = f.owner.load(), b = f.owner.load(); await started();
  f.owner.cancel();
  f.pending[0].resolve("previous linked account");
  assert.deepEqual(await Promise.all([a,b]), [false,false]); assert.deepEqual(f.applied, []);
});

test("an old completion cannot clear or replace the newer generation's pending read", async () => {
  const f = fixture(); const old = f.owner.load(); await started(); f.owner.cancel();
  const latest = f.owner.load(); await started();
  f.pending[0].resolve("old"); assert.equal(await old, false);
  assert.equal(f.owner.load(),latest); assert.equal(f.pending.length, 2);
  f.pending[1].resolve("new"); assert.equal(await latest, true); assert.deepEqual(f.applied, ["new"]);
});

test("status can refresh across tab changes without changing the account generation", async () => {
  const f = fixture(); const work = f.owner.load(); await started();
  f.pending[0].resolve({ok:false,code:"offline"}); assert.equal(await work, true);
  assert.deepEqual(f.applied, [{ok:false,code:"offline"}]);
});

test("synchronous transport throws and rejected requests release the shared read for retries", async () => {
  for (const asynchronous of [false,true]) {
    let fails = true; const applied = [];
    const owner = create({request: () => {
      if (fails) { if (asynchronous) return Promise.reject(new Error("transport failure")); throw new Error("transport failure"); }
      return Promise.resolve("recovered");
    }, apply: value => applied.push(value)});
    const a = owner.load(), b = owner.load();
    await assert.rejects(a, /transport failure/); await assert.rejects(b, /transport failure/);
    fails = false; assert.equal(await owner.load(), true); assert.deepEqual(applied, ["recovered"]);
  }
});
