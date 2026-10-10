// «Перенесення історії за кодом»: the launcher encrypts its history backup with a key
// made from the secret part of a one-time code (ABCD-EFGH-JKLM: "ABCD" is the id
// here, "EFGHJKLM" never leaves the two computers) and uploads the ciphertext.
// The other computer downloads it with the id and decrypts it locally, then
// deletes it; a mistyped secret part can try again (TRANSFER_TRIES downloads).
// The server cannot read what it keeps; it keeps it TRANSFER_MINUTES at most.

export const TRANSFER_MINUTES = 15;
export const TRANSFER_TRIES = 3;
export const TRANSFER_MAX_BYTES = 1_500_000;
export const TRANSFER_RATE_PER_HOUR = { install: 10, address: 20, claim: 30 };
// Same alphabet as the launcher's transfer-code.js (no 0/O, 1/I/L).
export const TRANSFER_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ";

export function isTransferId(value) {
  return new RegExp(`^[${TRANSFER_ALPHABET}]{4}$`).test(String(value || ""));
}

// The launcher's sealed box starts with this magic (transfer-code.js), so a
// random upload of something else is refused.
export const SEALED_MAGIC = [0x57, 0x44, 0x54, 0x31]; // "WDT1"

export function isSealed(bytes) {
  return bytes.length > SEALED_MAGIC.length + 28 && SEALED_MAGIC.every((b, i) => bytes[i] === b);
}
