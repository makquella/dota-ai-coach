"use strict";
const assert = require("node:assert/strict");
const test = require("node:test");
const { create } = require("../renderer/profile-requests");

function fixture(prepare = async () => {}) {
  const context = { view: "profile", locale: "en", accountId: 1, linked: true };
  const pending = [], applied = [];
  const owner = create({ current: () => context, prepare, request: args => new Promise((resolve, reject) => pending.push({ args, resolve, reject })) });
  return { context, pending, applied, owner, load: (args) => owner.load(result => applied.push(result), args) };
}
const prepared = () => new Promise(resolve => setImmediate(resolve));

test("only the newest profile result applies, including a read superseded by a local action", async () => {
  const f = fixture(); const old = f.load(); await prepared();
  const action = f.load({ op: "profileMmr", args: { mmr: 3200 } }); await prepared();
  f.pending[1].resolve("new rating"); assert.equal(await action, true);
  f.pending[0].resolve("old rating"); assert.equal(await old, false);
  assert.deepEqual(f.applied, ["new rating"]);
  assert.deepEqual(f.pending.map(p => p.args), [{}, { op: "profileMmr", args: { mmr: 3200 } }]);
});

test("changed account, link state, language or view rejects a delayed profile result", async () => {
  for (const patch of [{ accountId: 2 }, { linked: false }, { locale: "uk" }, { view: "matches" }]) {
    const f = fixture(); const old = f.load(); await prepared();
    Object.assign(f.context, patch); f.pending[0].resolve("stale");
    assert.equal(await old, false); assert.deepEqual(f.applied, []);
  }
});

test("same-account leave/return and explicit account cancellation cannot revive old work", async () => {
  const f = fixture(); const old = f.load(); await prepared();
  f.context.view = "home"; f.owner.cancel(); f.context.view = "profile";
  const latest = f.load(); await prepared();
  f.pending[0].resolve("old visit"); f.pending[1].resolve("new visit");
  assert.deepEqual(await Promise.all([old, latest]), [false, true]);
  const canceled = f.load({ op: "shopEquip", args: { id: "frame_plain" } }); await prepared();
  f.owner.cancel(); f.pending[2].resolve("old account action");
  assert.equal(await canceled, false); assert.deepEqual(f.applied, ["new visit"]);
});

test("superseded status preparation cannot launch a profile or action request", async () => {
  const status = [];
  const f = fixture(() => new Promise(resolve => status.push(resolve)));
  const old = f.load(); const latest = f.load();
  status[0](); assert.equal(await old, false); assert.equal(f.pending.length, 0);
  status[1](); await prepared(); f.pending[0].resolve("latest"); assert.equal(await latest, true);
  const changed = f.load({ op: "profileMmrClear" }); f.context.locale = "uk"; status[2]();
  assert.equal(await changed, false); assert.equal(f.pending.length, 1);
});

test("status can discover the first account; unlinked and hidden profiles do not fetch", async () => {
  const f = fixture(async () => { f.context.accountId = 2; f.context.linked = true; });
  f.context.accountId = null; f.context.linked = false;
  const first = f.load(); await prepared(); f.pending[0].resolve("linked");
  assert.equal(await first, true);
  const unlinked = fixture(); unlinked.context.linked = false;
  assert.equal(await unlinked.load(), true); assert.deepEqual(unlinked.applied, [null]);
  unlinked.context.view = "home"; assert.equal(await unlinked.load(), false);
  assert.equal(unlinked.pending.length, 0);
});

test("independent friends and profile owners do not supersede each other", async () => {
  const profile = fixture(), friends = fixture();
  const drawing = profile.load(), status = friends.load({ op: "status" }); await prepared();
  const action = friends.load({ op: "remove", code: "WD-23456789" }); await prepared();
  profile.pending[0].resolve("profile"); friends.pending[1].resolve("new friends");
  friends.pending[0].resolve("old friends");
  assert.deepEqual(await Promise.all([drawing, status, action]), [true, false, true]);
  assert.deepEqual(profile.applied, ["profile"]); assert.deepEqual(friends.applied, ["new friends"]);
});

test("current normalized errors apply and transport failure permits a later retry", async () => {
  const f = fixture(); const failed = f.load(); await prepared();
  f.pending[0].reject(new Error("transport failed")); await assert.rejects(failed, /transport failed/);
  const retry = f.load(); await prepared(); f.pending[1].resolve({ ok: false, code: "offline" });
  assert.equal(await retry, true); assert.deepEqual(f.applied, [{ ok: false, code: "offline" }]);
});
