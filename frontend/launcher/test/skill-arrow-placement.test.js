const assert = require("node:assert/strict");
const test = require("node:test");

const {
  ARROW_SPACE,
  arrowLayout,
  arrowTarget,
  autoBar,
  barFrame,
  frameFractions,
  manualBar,
  validFrame
} = require("../skill-arrow-placement");

const FULL_HD = { x: 0, y: 0, width: 1920, height: 1080 };
const TWO_K = { x: 0, y: 0, width: 2560, height: 1440 };

function near(actual, expected, tolerance = 1.5) {
  assert.ok(Math.abs(actual - expected) <= tolerance, `${actual} is not ${expected} ± ${tolerance}`);
}

test("Full HD: the six icons where the 1080p screenshot has them", () => {
  // Shadow Fiend, 7.39 HUD: icons at x 779, 837, 895, 953, 1011, 1069 (51 px), top 943.
  const bar = autoBar(FULL_HD, 6);
  near(bar.x, 779);
  near(bar.pitch, 58, 0.01);
  near(bar.icon, 51, 0.01);
  near(bar.y, 943);
  near(bar.plusTop, 903);
  near(bar.x + 5 * bar.pitch + bar.icon, 1120);
});

test("2K: the same bar scaled with the height and centred", () => {
  const bar = autoBar(TWO_K, 6);
  near(bar.icon, 68, 0.01);
  near(bar.y, 1440 - 137 * (4 / 3));
  near(bar.x + (5 * bar.pitch + bar.icon) / 2, 1280 - 14);
});

test("another count keeps the middle: four abilities, or a seventh from the Shard", () => {
  const six = autoBar(FULL_HD, 6);
  const middle = (bar, n) => bar.x + ((n - 1) * bar.pitch + bar.icon) / 2;
  near(middle(autoBar(FULL_HD, 4), 4), middle(six, 6), 0.01);
  near(middle(autoBar(FULL_HD, 7), 7), middle(six, 6), 0.01);
  assert.ok(autoBar(FULL_HD, 7).x < six.x);
});

test("a windowed game: the bar follows the picture, not the screen", () => {
  const windowed = { x: 300, y: 200, width: 1280, height: 720 };
  const bar = autoBar(windowed, 4);
  assert.ok(bar.x > 300 && bar.x + 4 * bar.pitch < 300 + 1280);
  near(bar.y, 200 + 720 - 137 * (720 / 1080));
});

test("the arrow window outlines the «+» button and the icon of the slot", () => {
  const bar = autoBar(FULL_HD, 6);
  const layout = arrowLayout(bar, 0);
  near(layout.window.x + layout.slot.x, 779);
  near(layout.window.y + layout.slot.y, 903);
  near(layout.slot.height, 994 - 903);
  assert.equal(layout.slot.y, ARROW_SPACE);
  // The ultimate, the sixth icon.
  const ult = arrowLayout(bar, 5);
  near(ult.window.x + ult.slot.x, 1069);
});

test("a frame laid by hand gives the same bar back, and other counts around it", () => {
  const auto = autoBar(FULL_HD, 6);
  const frame = frameFractions(barFrame(auto, 6), FULL_HD, 6);
  const manual = manualBar(validFrame(frame), FULL_HD, 6);
  near(manual.x, auto.x);
  near(manual.pitch, auto.pitch, 0.3);
  near(manual.plusTop, auto.plusTop);
  const four = manualBar(frame, FULL_HD, 4);
  near(four.x + (3 * four.pitch + four.icon) / 2, auto.x + (5 * auto.pitch + auto.icon) / 2);
});

test("broken calibrations are not used", () => {
  const good = { x: 0.4, y: 0.87, width: 0.18, height: 0.05, slots: 6 };
  assert.equal(validFrame(null), null);
  assert.equal(validFrame({ ...good, slots: 0 }), null);
  assert.equal(validFrame({ ...good, width: Number.NaN }), null);
  assert.equal(validFrame({ ...good, width: 3 }), null);
  assert.deepEqual(validFrame(good), good);
});

test("the target comes only from a skill hint with a sane slot", () => {
  const hint = { id: "skill-ult@6", title: "Learn your ultimate", ability: { slot: 3, slots: 4, name: "Omnislash" } };
  assert.deepEqual(arrowTarget({ map_hint: hint }), {
    id: "skill-ult@6",
    slot: 3,
    slots: 4,
    name: "Omnislash",
    title: "Learn your ultimate"
  });
  assert.equal(arrowTarget({ map_hint: { ...hint, ability: { slot: 4, slots: 4 } } }), null);
  assert.equal(arrowTarget({ map_hint: { id: "gold-stall@1" } }), null);
  assert.equal(arrowTarget(null), null);
});
