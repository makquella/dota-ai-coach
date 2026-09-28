const assert = require("node:assert/strict");
const test = require("node:test");

const { ALPHABET, newTransferCode, open, parseTransferCode, seal } = require("../transfer-code");

test("a code is three groups of four readable characters", () => {
  const { code, id, secret } = newTransferCode();
  assert.match(code, /^[2-9A-HJKMNP-Z]{4}-[2-9A-HJKMNP-Z]{4}-[2-9A-HJKMNP-Z]{4}$/);
  assert.equal(id, code.slice(0, 4));
  assert.equal(secret, code.slice(5, 9) + code.slice(10));
  assert.ok(![..."01OIL"].some((c) => ALPHABET.includes(c)));
});

test("typed codes are forgiving about case, spaces and dashes, strict about the rest", () => {
  assert.deepEqual(parseTransferCode(" ab2c efgh-jkmn "), { id: "AB2C", secret: "EFGHJKMN" });
  assert.equal(parseTransferCode("AB2C-EFGH-JKM"), null);
  assert.equal(parseTransferCode("AB0C-EFGH-JKMN"), null);
  assert.equal(parseTransferCode(""), null);
});

test("only the same code opens the box", () => {
  const code = newTransferCode();
  const data = Buffer.from(JSON.stringify({ format: "wardly-backup", matches: 50 }));
  const box = seal(data, code);
  assert.equal(box.subarray(0, 4).toString(), "WDT1");
  assert.ok(!box.includes(Buffer.from("wardly-backup")), "the server sees ciphertext only");
  assert.deepEqual(open(box, code), data);
  const other = { ...code, secret: code.secret === "22222222" ? "33333333" : "22222222" };
  assert.throws(() => open(box, other), (error) => error.code === "bad_code");
  const damaged = Buffer.from(box);
  damaged[damaged.length - 1] ^= 1;
  assert.throws(() => open(damaged, code), (error) => error.code === "bad_code");
  assert.throws(() => open(Buffer.from("hello"), code), (error) => error.code === "bad_code");
});
