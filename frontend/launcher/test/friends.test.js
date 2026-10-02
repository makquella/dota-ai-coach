"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const crypto = require("node:crypto");

const friends = require("../friends");

test("friend codes are made and read the way people type them", () => {
  const id = friends.newProfileId(crypto.randomBytes);
  assert.ok(friends.isProfileId(id));
  assert.equal(friends.friendCode("4k7p9qx2"), "WD-4K7P9QX2");
  for (const typed of ["WD-4K7P9QX2", "wd4k7p9qx2", " 4K7P 9QX2 ", "WD-4K7P-9QX2"]) {
    assert.equal(friends.normalizeCode(typed), "4k7p9qx2", typed);
  }
  // 0, 1, i, l, o are not in the alphabet: a typo is refused, not guessed.
  assert.equal(friends.normalizeCode("WD-4K7P9QX0"), null);
  assert.equal(friends.normalizeCode(""), null);
  assert.match(friends.newToken(crypto.randomBytes), /^[0-9a-f]{32}$/);
});

test("the friend list refuses bad, own, repeated and too many codes", () => {
  let result = friends.addFriend([], "WD-4K7P9QX2", "22222222");
  assert.deepEqual(result, { ok: true, list: ["4k7p9qx2"] });
  assert.equal(friends.addFriend(result.list, "4k7p9qx2", "22222222").code, "already");
  assert.equal(friends.addFriend([], "22222222", "22222222").code, "own_code");
  assert.equal(friends.addFriend([], "nope", null).code, "bad_code");
  const full = Array.from({ length: friends.MAX_FRIENDS }, (_, i) => `aaaaaa${"23456789abcdefghjkmnpqrstuvwxyz"[i % 31]}${"23456789"[Math.floor(i / 31)]}`);
  assert.equal(friends.addFriend(full, "4k7p9qx2", null).code, "too_many");
  assert.deepEqual(friends.removeFriend(["4k7p9qx2", "22222222"], "4k7p9qx2"), ["22222222"]);
});

test("the leaderboard puts the higher level first, then the rating, then the games", () => {
  const rows = friends.leaderboard([
    { id: "a", card: { level: 5, mmr: null, stats: { app_games: 40 } } },
    { id: "me", me: true, card: { level: 7, mmr: 3000, stats: { app_games: 20 } } },
    { id: "b", card: { level: 7, mmr: 3200, stats: { app_games: 10 } } },
    { id: "gone", card: null }
  ]);
  assert.deepEqual(rows.map((r) => [r.id, r.place]), [["b", 1], ["me", 2], ["a", 3]]);
});
