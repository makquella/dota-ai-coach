// «Знайти налаштування»: the pure helpers of renderer/settings-search.js.
const test = require("node:test");
const assert = require("node:assert/strict");
const { normalize, terms, matches, spans } = require("../renderer/settings-search.js");

test("case, «ґ», apostrophes and quotes do not matter", () => {
  assert.equal(normalize("  «Голос»  Ґанок "), "голос ганок");
  assert.deepEqual(terms("Розмір  розмір картки"), ["розмір", "картки"]);
});

test("every word must be found, in any order", () => {
  const row = "Розмір картки Більша — для великих екранів card size";
  assert.ok(matches(row, terms("картки розмір")));
  assert.ok(matches(row, terms("SIZE")));
  assert.ok(!matches(row, terms("розмір голос")));
  assert.ok(matches(row, []));
});

test("a word counts from its start", () => {
  assert.ok(matches("Ключ OpenDota, ключі не переносяться", terms("ключ")));
  assert.ok(!matches("Увімкнути чи вимкнути картку", terms("ключ")));
  assert.deepEqual(spans("підключити ключі", terms("ключ")), [[11, 15]]);
});

test("highlights land on the original letters", () => {
  assert.deepEqual(spans("Голос: звук", terms("голос")), [[0, 5]]);
  assert.deepEqual(spans("Комп’ютер ґанок", terms("ганок")), [[10, 15]]);
  // A typed apostrophe finds the typographic one, and the word stays whole.
  assert.deepEqual(spans("Комп’ютер ґанок", terms("комп'ютер")), [[0, 9]]);
  // Overlapping words merge into one span.
  assert.deepEqual(spans("голос голосом", terms("голос гол")), [[0, 5], [6, 11]]);
  assert.deepEqual(spans("text", []), []);
});
