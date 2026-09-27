const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { cdnUrl, createAssetHandler, parseAssetUrl } = require("../dota-assets");

const PNG = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 1, 2, 3]);

function fakeFetch(answers) {
  const calls = [];
  const fetchImpl = async (url) => {
    calls.push(url);
    const answer = answers[url];
    if (answer instanceof Error) {
      throw answer;
    }
    if (!answer) {
      return { ok: false, status: 404, arrayBuffer: async () => new ArrayBuffer(0) };
    }
    return { ok: true, status: 200, arrayBuffer: async () => answer.buffer.slice(answer.byteOffset, answer.byteOffset + answer.length) };
  };
  return { fetchImpl, calls };
}

test("only known kinds and plain names are accepted", () => {
  assert.deepEqual(parseAssetUrl("dota-asset://hero/juggernaut"), { kind: "hero", name: "juggernaut" });
  assert.deepEqual(parseAssetUrl("dota-asset://item/bfury.png"), { kind: "item", name: "bfury" });
  assert.deepEqual(parseAssetUrl("dota-asset://hero-icon/kez"), { kind: "hero-icon", name: "kez" });
  assert.equal(parseAssetUrl("dota-asset://hero/../../etc/passwd"), null);
  assert.equal(parseAssetUrl("dota-asset://hero/Juggernaut"), null);
  assert.equal(parseAssetUrl("dota-asset://ability/x"), null);
  assert.equal(parseAssetUrl("https://example.com/hero/x"), null);
  assert.equal(parseAssetUrl("not a url"), null);
  assert.equal(cdnUrl("hero-icon", "kez"), "https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes/icons/kez.png");
});

test("a picture is downloaded once, then served from disk", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "dota-assets-"));
  const { fetchImpl, calls } = fakeFetch({ [cdnUrl("item", "bfury")]: PNG });
  const handle = createAssetHandler({ root, fetchImpl });
  const first = await handle({ url: "dota-asset://item/bfury" });
  assert.equal(first.status, 200);
  assert.equal(first.headers.get("content-type"), "image/png");
  assert.deepEqual(Buffer.from(await first.arrayBuffer()), PNG);
  const second = await handle({ url: "dota-asset://item/bfury" });
  assert.equal(second.status, 200);
  assert.equal(calls.length, 1);
  assert.ok(fs.existsSync(path.join(root, "item", "bfury.png")));
});

test("offline or unknown pictures give 404 and are not asked for again at once", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "dota-assets-"));
  let clock = 0;
  const { fetchImpl, calls } = fakeFetch({ [cdnUrl("hero", "juggernaut")]: new Error("offline"), [cdnUrl("hero", "fake")]: Buffer.from("<html>") });
  const handle = createAssetHandler({ root, fetchImpl, now: () => clock });
  assert.equal((await handle({ url: "dota-asset://hero/juggernaut" })).status, 404);
  assert.equal((await handle({ url: "dota-asset://hero/juggernaut" })).status, 404);
  assert.equal(calls.length, 1);
  clock = 11 * 60 * 1000;
  await handle({ url: "dota-asset://hero/juggernaut" });
  assert.equal(calls.length, 2);
  // Something that is not a PNG is never written to the cache.
  assert.equal((await handle({ url: "dota-asset://hero/fake" })).status, 404);
  assert.ok(!fs.existsSync(path.join(root, "hero", "fake.png")));
  assert.equal((await handle({ url: "dota-asset://nope/x" })).status, 404);
});

test("parallel requests for one picture share one download", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "dota-assets-"));
  const { fetchImpl, calls } = fakeFetch({ [cdnUrl("hero", "axe")]: PNG });
  const handle = createAssetHandler({ root, fetchImpl });
  const answers = await Promise.all([1, 2, 3].map(() => handle({ url: "dota-asset://hero/axe" })));
  assert.deepEqual(answers.map((r) => r.status), [200, 200, 200]);
  assert.equal(calls.length, 1);
});
