const test = require("node:test");
const assert = require("node:assert/strict");
const { placeBubble, spotlight, onScreen, nextIndex } = require("../renderer/tour.js");

const viewport = { width: 1280, height: 800 };
const bubble = { width: 340, height: 180 };

test("the card goes below an element when it fits, centred on it", () => {
  const place = placeBubble({ left: 400, top: 100, width: 200, height: 40 }, bubble, viewport);
  assert.deepEqual(place, { side: "below", left: 330, top: 154 });
});

test("the card goes above an element near the bottom", () => {
  const place = placeBubble({ left: 400, top: 700, width: 200, height: 60 }, bubble, viewport);
  assert.equal(place.side, "above");
  assert.equal(place.top, 700 - 14 - 180);
});

test("a tall element puts the card to its side", () => {
  const right = placeBubble({ left: 20, top: 20, width: 220, height: 760 }, bubble, viewport);
  assert.equal(right.side, "right");
  assert.equal(right.left, 20 + 220 + 14);
  const left = placeBubble({ left: 900, top: 20, width: 370, height: 760 }, bubble, viewport);
  assert.equal(left.side, "left");
  assert.equal(left.left, 900 - 14 - 340);
});

test("the card stays inside the window", () => {
  const place = placeBubble({ left: 1200, top: 100, width: 60, height: 30 }, bubble, viewport);
  assert.equal(place.side, "below");
  assert.equal(place.left, 1280 - 340 - 12);
  const edge = placeBubble({ left: 0, top: 100, width: 40, height: 30 }, bubble, viewport);
  assert.equal(edge.left, 12);
});

test("no element or no room → the middle of the window", () => {
  assert.deepEqual(placeBubble(null, bubble, viewport), { side: "center", left: 470, top: 310 });
  const full = placeBubble({ left: 0, top: 0, width: 1280, height: 800 }, bubble, viewport);
  assert.equal(full.side, "center");
});

test("the cut-out is padded and kept inside the window", () => {
  assert.deepEqual(spotlight({ left: 100, top: 50, width: 200, height: 40 }, viewport), {
    left: 94,
    top: 44,
    width: 212,
    height: 52
  });
  assert.deepEqual(spotlight({ left: 2, top: 0, width: 1280, height: 30 }, viewport), {
    left: 0,
    top: 0,
    width: 1280,
    height: 36
  });
});

test("steps with a hidden element are skipped both ways; past the end is -1", () => {
  const steps = [{ id: "a" }, { id: "b", hidden: true }, { id: "c" }, { id: "d", hidden: true }];
  const available = (step) => !step.hidden;
  assert.equal(nextIndex(steps, -1, 1, available), 0);
  assert.equal(nextIndex(steps, 0, 1, available), 2);
  assert.equal(nextIndex(steps, 2, 1, available), -1);
  assert.equal(nextIndex(steps, 2, -1, available), 0);
  assert.equal(nextIndex(steps, 0, -1, available), 0);
});

test("an element scrolled out of the window has no cut-out", () => {
  const viewport = { width: 1000, height: 800 };
  assert.equal(onScreen({ left: 100, top: 100, width: 200, height: 50 }, viewport), true);
  assert.equal(onScreen({ left: 100, top: 780, width: 200, height: 50 }, viewport), true);
  assert.equal(onScreen({ left: 100, top: -60, width: 200, height: 50 }, viewport), false);
  assert.equal(onScreen({ left: 100, top: 820, width: 200, height: 50 }, viewport), false);
  assert.equal(onScreen({ left: 100, top: 100, width: 0, height: 0 }, viewport), false);
});
