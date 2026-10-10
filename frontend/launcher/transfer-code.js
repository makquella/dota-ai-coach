// «Перенесення історії за кодом»: a one-time code and the encryption around it.
// Pure Node (no Electron), tested in test/transfer-code.test.js.
//
// The code is ABCD-EFGH-JKLM. "ABCD" is the id the API keeps the upload under;
// "EFGHJKLM" (40 bits) makes the key and never leaves the two computers, so the
// server stores a box it cannot open. The key is scrypt(secret, id) — slow on
// purpose — and the box is AES-256-GCM: WDT1 | iv (12) | tag (16) | ciphertext.

const crypto = require("node:crypto");

// No 0/O and 1/I/L: the code is read off one screen and typed on another.
const ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ";
const MAGIC = Buffer.from("WDT1");
const SCRYPT = { N: 2 ** 15, r: 8, p: 1, maxmem: 64 * 1024 * 1024 };

function randomChars(count, randomBytes = crypto.randomBytes) {
  // Rejection sampling keeps every character equally likely.
  const limit = 256 - (256 % ALPHABET.length);
  let out = "";
  while (out.length < count) {
    for (const byte of randomBytes(count * 2)) {
      if (byte < limit && out.length < count) {
        out += ALPHABET[byte % ALPHABET.length];
      }
    }
  }
  return out;
}

function newTransferCode(randomBytes = crypto.randomBytes) {
  const chars = randomChars(12, randomBytes);
  const id = chars.slice(0, 4);
  const secret = chars.slice(4);
  return { id, secret, code: `${id}-${secret.slice(0, 4)}-${secret.slice(4)}` };
}

/** "abcd efgh-jklm" -> { id, secret }; null for anything else. */
function parseTransferCode(input) {
  const text = String(input || "")
    .toUpperCase()
    .replace(/[\s-]+/g, "");
  if (text.length !== 12 || [...text].some((c) => !ALPHABET.includes(c))) {
    return null;
  }
  return { id: text.slice(0, 4), secret: text.slice(4) };
}

function keyFor(id, secret) {
  return crypto.scryptSync(secret, `wardly-transfer:${id}`, 32, SCRYPT);
}

function seal(data, { id, secret }) {
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv("aes-256-gcm", keyFor(id, secret), iv);
  const body = Buffer.concat([cipher.update(data), cipher.final()]);
  return Buffer.concat([MAGIC, iv, cipher.getAuthTag(), body]);
}

/** The data back, or an error with code "bad_code" (wrong code or a damaged box). */
function open(box, { id, secret }) {
  const bytes = Buffer.from(box);
  if (bytes.length < MAGIC.length + 28 || !bytes.subarray(0, 4).equals(MAGIC)) {
    throw Object.assign(new Error("not a Wardly transfer"), { code: "bad_code" });
  }
  const iv = bytes.subarray(4, 16);
  const tag = bytes.subarray(16, 32);
  try {
    const decipher = crypto.createDecipheriv("aes-256-gcm", keyFor(id, secret), iv);
    decipher.setAuthTag(tag);
    return Buffer.concat([decipher.update(bytes.subarray(32)), decipher.final()]);
  } catch {
    throw Object.assign(new Error("wrong code"), { code: "bad_code" });
  }
}

/** The token that cancels this transfer on the server (64 hex). Derived from the
 * whole code, so only the sender and the receiver have it; the server keeps
 * its hash (services/api deleteTransfer). */
function deleteToken({ id, secret }) {
  return crypto.createHmac("sha256", keyFor(id, secret)).update("wardly-transfer-delete").digest("hex");
}

module.exports = { ALPHABET, newTransferCode, parseTransferCode, seal, open, deleteToken };
