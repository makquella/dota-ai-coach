const assert = require("node:assert/strict");
const test = require("node:test");

const { MARGIN, anchorArea, isReachable, presetBounds } = require("../overlay-placement");

const SIZE = { width: 420, height: 140 };
const PRIMARY = { id: 1, bounds: { x: 0, y: 0, width: 1920, height: 1080 }, workArea: { x: 0, y: 0, width: 1920, height: 1040 } };
const SECOND = {
  id: 2,
  bounds: { x: 1920, y: -200, width: 2560, height: 1440 },
  workArea: { x: 1920, y: -200, width: 2560, height: 1400 }
};

test("without a Dota window the fallback area is used", () => {
  assert.deepEqual(anchorArea({ dotaRect: null, display: null, fallbackArea: PRIMARY.workArea, size: SIZE }), PRIMARY.workArea);
});

test("fullscreen Dota on the second monitor anchors the card there", () => {
  const area = anchorArea({ dotaRect: SECOND.bounds, display: SECOND, fallbackArea: PRIMARY.workArea, size: SIZE });
  assert.deepEqual(area, SECOND.bounds);
  const right = presetBounds("right-center", area, SIZE);
  assert.equal(right.x, 1920 + 2560 - 420 - MARGIN);
  assert.equal(right.y, -200 + Math.round((1440 - 140) / 2));
  const left = presetBounds("left-center", area, SIZE);
  assert.equal(left.x, 1920 + MARGIN);
});

test("windowed Dota keeps the card inside the game window", () => {
  const dotaRect = { x: 300, y: 100, width: 1280, height: 720 };
  const area = anchorArea({ dotaRect, display: PRIMARY, fallbackArea: PRIMARY.workArea, size: SIZE });
  assert.deepEqual(area, dotaRect);
  const bottom = presetBounds("bottom-center", area, SIZE);
  assert.equal(bottom.x, 300 + Math.round((1280 - 420) / 2));
  // Above the minimap / hero panel (bottom 24% of the game window).
  assert.ok(bottom.y + bottom.height <= 100 + 720 - Math.round(720 * 0.24));
});

test("a game window hanging off the screen is clipped to its monitor", () => {
  const dotaRect = { x: -200, y: 0, width: 1600, height: 900 };
  const area = anchorArea({ dotaRect, display: PRIMARY, fallbackArea: PRIMARY.workArea, size: SIZE });
  assert.deepEqual(area, { x: 0, y: 0, width: 1400, height: 900 });
});

test("a tiny game window falls back to its monitor's work area", () => {
  const dotaRect = { x: 2000, y: 0, width: 400, height: 300 };
  const area = anchorArea({ dotaRect, display: SECOND, fallbackArea: PRIMARY.workArea, size: SIZE });
  assert.deepEqual(area, SECOND.workArea);
});

test("hand-placed positions must stay reachable", () => {
  const areas = [PRIMARY.workArea, SECOND.workArea];
  assert.equal(isReachable({ x: 3000, y: 100, ...SIZE }, areas), true);
  assert.equal(isReachable({ x: 3000, y: 100, ...SIZE }, [PRIMARY.workArea]), false, "second monitor unplugged");
  assert.equal(isReachable({ x: 1900, y: 1030, ...SIZE }, [PRIMARY.workArea]), false, "only a sliver visible");
});
