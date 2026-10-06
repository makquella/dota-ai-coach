// «Найти настройку»: the pure helpers of renderer/settings-search.js.
const test = require("node:test");
const assert = require("node:assert/strict");
const { normalize, terms, matches, spans } = require("../renderer/settings-search.js");

test("case, «ё» and quotes do not matter", () => {
  assert.equal(normalize("  «Голос»  ЁЖ "), "голос еж");
  assert.deepEqual(terms("Размер  размер карточки"), ["размер", "карточки"]);
});

test("every word must be found, in any order", () => {
  const row = "Размер карточки Крупнее — для больших экранов card size";
  assert.ok(matches(row, terms("карточки размер")));
  assert.ok(matches(row, terms("SIZE")));
  assert.ok(!matches(row, terms("размер голос")));
  assert.ok(matches(row, []));
});

test("a word counts from its start", () => {
  assert.ok(matches("Ключ OpenDota, ключи не переносятся", terms("ключ")));
  assert.ok(!matches("Включить или выключить карточку", terms("ключ")));
  assert.deepEqual(spans("включить ключи", terms("ключ")), [[9, 13]]);
});

test("highlights land on the original letters", () => {
  assert.deepEqual(spans("Голос: звук", terms("голос")), [[0, 5]]);
  assert.deepEqual(spans("Всё ещё", terms("ещe".replace("e", "е"))), [[4, 7]]);
  // Overlapping words merge into one span.
  assert.deepEqual(spans("голос голосом", terms("голос гол")), [[0, 5], [6, 11]]);
  assert.deepEqual(spans("text", []), []);
});
