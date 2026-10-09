"use strict";

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

const TOKEN = /^[a-f0-9]{64}$/;

function loadLocalApiAuth(filePath) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  if (!fs.existsSync(filePath)) {
    const temporary = `${filePath}.${crypto.randomBytes(8).toString("hex")}.tmp`;
    const fd = fs.openSync(temporary, "wx", 0o600);
    try {
      try {
        fs.writeFileSync(fd, JSON.stringify({ version: 1, gsi: crypto.randomBytes(32).toString("hex") }));
        fs.fsyncSync(fd);
      } finally {
        fs.closeSync(fd);
      }
      try {
        fs.linkSync(temporary, filePath);
      } catch (error) {
        if (error.code !== "EEXIST") throw error;
      }
    } finally {
      fs.unlinkSync(temporary);
    }
  }
  let data;
  try {
    const stat = fs.lstatSync(filePath);
    if (!stat.isFile() || stat.size > 4096) throw new Error();
    data = JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    throw new Error("Could not read local API credentials.");
  }
  if (data?.version !== 1 || typeof data.gsi !== "string" || !TOKEN.test(data.gsi)) {
    throw new Error("Invalid local API credentials.");
  }
  fs.chmodSync(filePath, 0o600);
  let control;
  do { control = crypto.randomBytes(32).toString("hex"); } while (control === data.gsi);
  return Object.freeze({ control, gsi: data.gsi });
}

function controlHeaders(url, base, token) {
  const destination = new URL(url, base);
  const origin = new URL(base);
  if (origin.protocol !== "http:" || origin.hostname !== "127.0.0.1" || destination.origin !== origin.origin || destination.username || destination.password || !TOKEN.test(token)) {
    throw new Error("Invalid backend endpoint or credentials.");
  }
  return { "Content-Type": "application/json", Authorization: `Bearer ${token}` };
}

function renderGsiConfig(endpoint, token) {
  const url = new URL(endpoint);
  if (url.protocol !== "http:" || url.hostname !== "127.0.0.1" || url.pathname !== "/gsi" || url.search || url.hash || url.username || url.password || !TOKEN.test(token)) {
    throw new Error("Invalid local GSI configuration.");
  }
  return `"Wardly GSI"
{
  "uri"           "${endpoint}"
  "timeout"       "5.0"
  "buffer"        "0.1"
  "throttle"      "0.1"
  "heartbeat"     "2.0"
  "auth"
  {
    "token"       "${token}"
  }
  "data"
  {
    "provider"    "1"
    "map"         "1"
    "player"      "1"
    "hero"        "1"
    "abilities"   "1"
    "items"       "1"
    "buildings"   "1"
    "events"      "1"
    "minimap"     "1"
  }
}
`;
}

module.exports = { loadLocalApiAuth, controlHeaders, renderGsiConfig };
