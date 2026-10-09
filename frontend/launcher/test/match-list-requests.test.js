"use strict";
const assert = require("node:assert/strict");
const test = require("node:test");
const { create } = require("../renderer/match-list-requests");

function fixture(prepare = async () => {}) {
  const context = { view: "matches", accountId: 1, linked: true, count: 30, heroId: null, result: "all", sort: "date", asc: false };
  const pending = [], applied = [];
  const owner = create({ current: () => context, prepare, request: args => new Promise((resolve, reject) => pending.push({ args, resolve, reject })) });
  return { context, pending, applied, owner, replace: () => owner.replace(value => applied.push(value)), more: () => owner.more(value => applied.push(value)) };
}
const prepared = () => new Promise(resolve => setImmediate(resolve));

test("rapid A/B/A filters allow only the latest selection to replace the table", async () => {
  const f = fixture();
  f.context.heroId = 8;
  const first = f.replace(); await prepared();
  f.context.heroId = 1;
  const second = f.replace(); await prepared();
  f.context.heroId = 8;
  const latest = f.replace(); await prepared();
  f.pending[2].resolve("latest Juggernaut");
  assert.equal(await latest, true);
  f.pending[0].resolve("old Juggernaut");
  f.pending[1].resolve("Anti-Mage");
  assert.deepEqual(await Promise.all([first, second]), [false, false]);
  assert.deepEqual(f.applied, ["latest Juggernaut"]);
  assert.equal(f.pending[2].args.heroId, 8);
});

test("sort/result changes reject a response even without a replacement call", async () => {
  for (const patch of [{ sort: "gpm" }, { asc: true }, { result: "win" }, { heroId: 8 }]) {
    const f = fixture(); const work = f.replace(); await prepared();
    Object.assign(f.context, patch);
    f.pending[0].resolve("old selection");
    assert.equal(await work, false);
    assert.deepEqual(f.applied, []);
  }
});

test("a superseded status preparation cannot launch an obsolete list request", async () => {
  const status = [];
  const f = fixture(() => new Promise(resolve => status.push(resolve)));
  const first = f.replace();
  f.context.sort = "gpm"; f.context.asc = true;
  const latest = f.replace();
  status[0](); assert.equal(await first, false);
  assert.equal(f.pending.length, 0);
  status[1](); await prepared();
  assert.deepEqual(f.pending[0].args, { limit: 30, heroId: undefined, result: undefined, sort: "gpm", order: "asc" });
  f.pending[0].resolve("sorted"); assert.equal(await latest, true);
});

test("first status preparation can discover an account; unlinked lists render without fetching", async () => {
  const f = fixture(async () => { f.context.accountId = 2; f.context.linked = true; });
  f.context.linked = false; f.context.accountId = null;
  const work = f.replace(); await prepared();
  f.pending[0].resolve("newly linked"); assert.equal(await work, true);
  const unlinked = fixture(); unlinked.context.linked = false;
  assert.equal(await unlinked.replace(), true);
  assert.deepEqual(unlinked.applied, [null]);
  assert.equal(unlinked.pending.length, 0);
});

test("double pagination starts one request; a subsequent page uses the new offset", async () => {
  const f = fixture();
  const first = f.more();
  assert.equal(await f.more(), false);
  assert.equal(f.pending.length, 1);
  assert.equal(f.pending[0].args.offset, 30);
  f.pending[0].resolve("page 2"); assert.equal(await first, true);
  f.context.count = 60;
  const next = f.more();
  assert.equal(f.pending[1].args.offset, 60);
  f.pending[1].resolve("page 3"); assert.equal(await next, true);
  assert.deepEqual(f.applied, ["page 2", "page 3"]);
});

test("a replacement invalidates the old page and blocks paging until it completes", async () => {
  const f = fixture(); const page = f.more();
  f.context.heroId = 8; f.context.count = 0;
  const filtered = f.replace(); await prepared();
  assert.equal(await f.more(), false);
  f.pending[1].resolve("filtered"); assert.equal(await filtered, true);
  f.pending[0].resolve("unfiltered page"); assert.equal(await page, false);
  assert.deepEqual(f.applied, ["filtered"]);
});

test("leaving and returning cancels both page and replacement responses", async () => {
  for (const operation of ["replace", "more"]) {
    const f = fixture(); const old = f[operation](); await prepared();
    f.context.view = "home"; f.owner.cancel(); f.context.view = "matches";
    const latest = f.replace(); await prepared();
    f.pending[0].resolve("previous visit"); assert.equal(await old, false);
    f.pending[1].resolve("new visit"); assert.equal(await latest, true);
    assert.deepEqual(f.applied, ["new visit"]);
  }
});

test("account/link changes invalidate both requests; changed row count invalidates a page", async () => {
  for (const operation of ["replace", "more"]) {
    for (const patch of [{ accountId: 2 }, { linked: false }]) {
      const f = fixture(); const work = f[operation](); await prepared();
      Object.assign(f.context, patch);
      f.pending[0].resolve("other account"); assert.equal(await work, false);
      assert.deepEqual(f.applied, []);
    }
  }
  const f = fixture(); const page = f.more(); f.context.count = 60;
  f.pending[0].resolve("wrong offset"); assert.equal(await page, false);
});

test("hidden lists and empty pages start no requests", async () => {
  const f = fixture(); f.context.view = "home";
  assert.equal(await f.replace(), false); assert.equal(await f.more(), false);
  f.context.view = "matches"; f.context.count = 0;
  assert.equal(await f.more(), false); assert.equal(f.pending.length, 0);
});

test("transport failures release ownership; normalized errors reach the current callback", async () => {
  for (const operation of ["replace", "more"]) {
    const f = fixture(); const failed = f[operation](); await prepared();
    f.pending[0].reject(new Error("transport failure"));
    await assert.rejects(failed, /transport failure/);
    const retry = f[operation](); await prepared();
    f.pending[1].resolve({ ok: false, code: "offline" });
    assert.equal(await retry, true);
    assert.deepEqual(f.applied, [{ ok: false, code: "offline" }]);
  }
});
