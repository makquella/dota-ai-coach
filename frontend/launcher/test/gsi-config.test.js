"use strict";

// The GSI config the launcher writes into Dota decides which blocks the game
// sends at all: a block the backend reads but the config does not ask for
// never arrives (until 0.31 "events" was missing, so the Roshan and Aegis
// timers never got a single event in a real game).
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const MAIN = fs.readFileSync(path.join(__dirname, "..", "main.js"), "utf8");

function configBlocks() {
  const start = MAIN.indexOf("function gsiConfigText()");
  const body = MAIN.slice(start, MAIN.indexOf("\n}\n", start));
  const data = body.slice(body.indexOf('"data"'));
  return [...data.matchAll(/"([a-z_]+)"\s+"1"/g)].map((match) => match[1]);
}

test("the GSI config asks for every block the backend reads", () => {
  const blocks = configBlocks();
  for (const block of ["provider", "map", "player", "hero", "abilities", "items", "events", "minimap"]) {
    assert.ok(blocks.includes(block), `missing "${block}" in gsiConfigText`);
  }
});
