"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const { texts, versions } = require("../renderer/whats-new");

test("an update shows current notes and skipped patch versions in numeric order, at most four", () => {
  const table = Object.fromEntries(["0.53.9", "0.53.10", "0.53.11", "0.53.12", "0.53.13", "0.53.14"].map((key) => [key, ["Note"]]));
  table["0.53.8"] = [];
  assert.deepEqual(versions(table, "0.53.13", "0.53.8"), ["0.53.13", "0.53.12", "0.53.11", "0.53.10"]);
  assert.deepEqual(versions(table, "0.53.10", "0.53.9"), ["0.53.10"]);
});

test("first installation shows only its current notes and missing notes stay hidden", () => {
  const table = { "0.53.9": ["Older"], "0.53.10": ["Current"], "0.53.11": [] };
  assert.deepEqual(versions(table, "0.53.10", ""), ["0.53.10"]);
  assert.deepEqual(versions(table, "0.53.11", ""), []);
  assert.deepEqual(versions(table, "0.53.12", ""), []);
});

test("language tables are detached, include the same versions and fall back to English", () => {
  const en = texts("en");
  const ru = texts("ru");
  assert.deepEqual(Object.keys(en), Object.keys(ru));
  assert.deepEqual(texts("unknown"), en);
  const current = require("../package.json").version;
  assert.ok(en[current].length && ru[current].length);
  assert.notDeepEqual(en[current], ru[current]);
  en[current][0] = "Changed by caller";
  en["999.0.0"] = ["Extra"];
  assert.notEqual(texts("en")[current][0], "Changed by caller");
  assert.equal(texts("en")["999.0.0"], undefined);
});

test("current update notes agree with launcher lock, backend versions and bilingual release notes", () => {
  const current = require("../package.json").version;
  const lock = require("../package-lock.json");
  assert.equal(lock.version, current);
  assert.equal(lock.packages[""].version, current);
  const root = path.resolve(__dirname, "../../..");
  const backend = fs.readFileSync(path.join(root, "backend/app/main.py"), "utf8");
  assert.ok(backend.includes(`version="${current}"`), "FastAPI version");
  assert.ok(backend.includes(`"version": "${current}"`), "health version");
  const notes = fs.readFileSync(path.join(root, `docs/release-notes/v${current}.md`), "utf8");
  assert.ok(notes.includes("Что нового") && notes.includes("**In English:**"));
});
