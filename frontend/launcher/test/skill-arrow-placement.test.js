const assert = require("node:assert/strict");
const test = require("node:test");

const {
  ARROW_SPACE,
  DEFAULT_FRAME,
  arrowLayout,
  arrowTarget,
  barRect,
  frameFractions,
  frameRect,
  validFrame
} = require("../skill-arrow-placement");

const DOTA = { x: 0, y: 0, width: 1920, height: 1080 };
const SECOND = { x: 1920, y: -200, width: 2560, height: 1440 };

test("a frame laid by hand comes back from its fractions on any window of that shape", () => {
  const rect = { x: 830, y: 980, width: 256, height: 64 };
  const fractions = frameFractions(rect, DOTA, 4);
  assert.deepEqual(frameRect(fractions, DOTA), rect);
  // The same game on a bigger monitor: the frame scales with it.
  const moved = frameRect(fractions, SECOND);
  assert.equal(moved.x, 1920 + Math.round((830 / 1920) * 2560));
  assert.equal(moved.width, Math.round((256 / 1920) * 2560));
});

test("a hero with more abilities keeps the icon size around the same centre", () => {
  const frame = frameFractions({ x: 830, y: 980, width: 256, height: 64 }, DOTA, 4);
  const six = barRect(frame, DOTA, 6);
  assert.equal(six.width, 384);
  assert.equal(six.x + six.width / 2, 830 + 128);
  assert.deepEqual(barRect(frame, DOTA, 4), { x: 830, y: 980, width: 256, height: 64 });
});

test("the arrow window sits over the bar with the slot inside it", () => {
  const bar = { x: 830, y: 980, width: 256, height: 64 };
  const layout = arrowLayout(bar, 3, 4);
  assert.equal(layout.window.y, 980 - ARROW_SPACE);
  assert.ok(layout.window.width >= 320);
  // The ultimate: the last quarter of the bar, in window coordinates.
  assert.equal(layout.window.x + layout.slot.x, 830 + 192);
  assert.equal(layout.slot.width, 64);
  assert.equal(layout.slot.y, ARROW_SPACE);
});

test("broken calibrations are not used", () => {
  assert.equal(validFrame(null), null);
  assert.equal(validFrame({ ...DEFAULT_FRAME, slots: 0 }), null);
  assert.equal(validFrame({ ...DEFAULT_FRAME, width: Number.NaN }), null);
  assert.equal(validFrame({ ...DEFAULT_FRAME, width: 3 }), null);
  assert.deepEqual(validFrame(DEFAULT_FRAME), DEFAULT_FRAME);
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
