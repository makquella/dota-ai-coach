// Pure geometry for the skill arrows (no Electron, unit-tested).
//
// The player once lays a frame over the ability icons of Dota's HUD
// (calibration). It is kept as fractions of Dota's window, so it survives a
// moved window or another monitor of the same aspect ratio, together with the
// number of abilities the bar had then: a hero with more or fewer abilities
// gets the same icon size around the same centre.

// Where the frame starts before the first calibration: the middle of the
// bottom HUD of a 16:9 game, roughly over four ability icons.
const DEFAULT_FRAME = { x: 0.43, y: 0.905, width: 0.14, height: 0.06, slots: 4 };
// Room above the icons for the label and the arrow.
const ARROW_SPACE = 76;
const MIN_WIDTH = 320;
const MAX_SLOTS = 12;

function finite(value) {
  return typeof value === "number" && Number.isFinite(value);
}

// A stored calibration, or null when it is missing or broken.
function validFrame(frame) {
  if (!frame || typeof frame !== "object") {
    return null;
  }
  const { x, y, width, height, slots } = frame;
  if (![x, y, width, height].every(finite) || !Number.isInteger(slots)) {
    return null;
  }
  if (width <= 0 || height <= 0 || width > 1 || height > 1 || slots < 1 || slots > MAX_SLOTS) {
    return null;
  }
  if (x < -0.5 || x > 1 || y < -0.5 || y > 1) {
    return null;
  }
  return { x, y, width, height, slots };
}

// Fractions of `area` → a rectangle in the same units as `area`.
function frameRect(frame, area) {
  return {
    x: Math.round(area.x + frame.x * area.width),
    y: Math.round(area.y + frame.y * area.height),
    width: Math.max(1, Math.round(frame.width * area.width)),
    height: Math.max(1, Math.round(frame.height * area.height))
  };
}

// A rectangle (the player's frame) → fractions of `area`.
function frameFractions(rect, area, slots) {
  return {
    x: (rect.x - area.x) / area.width,
    y: (rect.y - area.y) / area.height,
    width: rect.width / area.width,
    height: rect.height / area.height,
    slots: Math.min(MAX_SLOTS, Math.max(1, Math.round(slots)))
  };
}

// The icons of a bar with `slots` abilities: the calibrated icon size around
// the calibrated centre.
function barRect(frame, area, slots) {
  const rect = frameRect(frame, area);
  const count = Number.isInteger(slots) && slots > 0 ? slots : frame.slots;
  const pitch = rect.width / frame.slots;
  const width = Math.round(pitch * count);
  const centre = rect.x + rect.width / 2;
  return { x: Math.round(centre - width / 2), y: rect.y, width, height: rect.height };
}

// The arrow window over the bar and the slot inside it (window coordinates).
function arrowLayout(bar, slot, slots) {
  const width = Math.max(MIN_WIDTH, bar.width + 48);
  const x = Math.round(bar.x + bar.width / 2 - width / 2);
  const window = { x, y: bar.y - ARROW_SPACE, width, height: bar.height + ARROW_SPACE };
  const pitch = bar.width / slots;
  const slotRect = {
    x: Math.round(bar.x - x + pitch * slot),
    y: ARROW_SPACE,
    width: Math.round(pitch),
    height: bar.height
  };
  return { window, slot: slotRect };
}

// The ability to point at, from /overlay/recommendation, or null.
function arrowTarget(data) {
  const hint = data && data.map_hint;
  const ability = hint && hint.ability;
  if (!ability || typeof ability !== "object") {
    return null;
  }
  const { slot, slots, name } = ability;
  if (!Number.isInteger(slot) || !Number.isInteger(slots) || slots < 1 || slots > MAX_SLOTS) {
    return null;
  }
  if (slot < 0 || slot >= slots) {
    return null;
  }
  return { id: String(hint.id || ""), slot, slots, name: String(name || ""), title: String(hint.title || "") };
}

module.exports = {
  ARROW_SPACE,
  DEFAULT_FRAME,
  MAX_SLOTS,
  arrowLayout,
  arrowTarget,
  barRect,
  frameFractions,
  frameRect,
  validFrame
};
