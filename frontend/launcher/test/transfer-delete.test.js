const assert = require("node:assert/strict");
const test = require("node:test");
const transferCode = require("../transfer-code");

test("the transfer delete token comes from the whole code only", () => {
  const code = transferCode.parseTransferCode("AB2C-DEFG-HJKM");
  const token = transferCode.deleteToken(code);
  assert.match(token, /^[a-f0-9]{64}$/);
  // The receiver typing the same code gets the same token…
  assert.equal(transferCode.deleteToken(transferCode.parseTransferCode("ab2c defg hjkm")), token);
  // …the id alone (what the server sees) or another secret does not.
  assert.notEqual(transferCode.deleteToken({ id: code.id, secret: "DEFGHJKN" }), token);
  assert.notEqual(transferCode.deleteToken({ id: "AB2D", secret: code.secret }), token);
  assert.ok(!token.includes(code.secret.toLowerCase()));
});
