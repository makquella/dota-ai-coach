// «Друзья» (0.35): the pure parts — friend codes, the list kept in settings and
// the leaderboard order. main.js does the requests (services/api: PUT
// /v1/profile/<id>, POST /v1/profiles) and keeps the token; this module has no
// Electron or network, so test/friends.test.js runs it as it is.
"use strict";

const ID_ALPHABET = "23456789abcdefghjkmnpqrstuvwxyz";
const ID_LENGTH = 8;
const MAX_FRIENDS = 50;

/** A new random profile id (the friend code without "WD-"). */
function newProfileId(randomBytes) {
  const bytes = randomBytes(ID_LENGTH);
  return Array.from(bytes, (b) => ID_ALPHABET[b % ID_ALPHABET.length]).join("");
}

/** A token only this launcher keeps (32 hex characters). */
function newToken(randomBytes) {
  return Array.from(randomBytes(16), (b) => b.toString(16).padStart(2, "0")).join("");
}

function isProfileId(value) {
  return new RegExp(`^[${ID_ALPHABET}]{${ID_LENGTH}}$`).test(String(value || ""));
}

/** A code as people type it ("WD-4K7P 9QX2", "wd4k7p9qx2") → the id, or null. */
function normalizeCode(value) {
  const id = String(value || "")
    .toLowerCase()
    .trim()
    .replace(/^wd-?/, "")
    .replace(/[\s-]/g, "");
  return isProfileId(id) ? id : null;
}

function friendCode(id) {
  return `WD-${String(id || "").toUpperCase()}`;
}

/** The friend list with one more code: { ok, list } or { ok: false, code }. */
function addFriend(list, value, ownId) {
  const id = normalizeCode(value);
  const current = Array.isArray(list) ? list.filter(isProfileId) : [];
  if (!id) {
    return { ok: false, code: "bad_code" };
  }
  if (id === ownId) {
    return { ok: false, code: "own_code" };
  }
  if (current.includes(id)) {
    return { ok: false, code: "already" };
  }
  if (current.length >= MAX_FRIENDS) {
    return { ok: false, code: "too_many" };
  }
  return { ok: true, list: [...current, id] };
}

function removeFriend(list, id) {
  return (Array.isArray(list) ? list : []).filter((item) => item !== id);
}

/**
 * The leaderboard: the player and the friends whose cards came back, best
 * first — by level, then the rating (when shown), then matches with Wardly.
 * rows: [{ id, card, me }] → the same rows with `place` 1..n.
 */
function leaderboard(rows) {
  const key = (row) => [
    Number(row.card?.level) || 0,
    Number.isFinite(row.card?.mmr) ? row.card.mmr : -1,
    Number(row.card?.stats?.app_games) || 0
  ];
  return rows
    .filter((row) => row && row.card)
    .slice()
    .sort((a, b) => {
      const [ka, kb] = [key(a), key(b)];
      for (let i = 0; i < ka.length; i += 1) {
        if (ka[i] !== kb[i]) {
          return kb[i] - ka[i];
        }
      }
      return a.me ? -1 : b.me ? 1 : 0;
    })
    .map((row, index) => ({ ...row, place: index + 1 }));
}

module.exports = {
  MAX_FRIENDS,
  addFriend,
  friendCode,
  isProfileId,
  leaderboard,
  newProfileId,
  newToken,
  normalizeCode,
  removeFriend
};
