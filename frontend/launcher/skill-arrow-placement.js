// Pure geometry for the skill arrows (no Electron, unit-tested).
//
// Dota's HUD is laid out for a 1080-pixel-high picture and scaled with the
// height of the game (Full HD ×1, 2K ×1.33, 4K ×2), centred across its width.
// The ability icons sit in the middle of the bottom panel between the portrait
// and the inventory, two blocks of fixed width, so the middle of the icons
// stays in the same place whatever the number of abilities: a hero's bar, or
// one that grew with Aghanim's Scepter or Shard, is laid out from the count
// alone. Measured on a 1920×1080 screenshot of the 7.39 HUD (Shadow Fiend, six
// abilities): icons 51 px every 58 px, their top 137 px above the bottom, the
// «+» level-up buttons 40 px above them, the middle 10.5 px left of the centre.
//
// The player may still lay a frame over the icons by hand (another HUD or
// aspect ratio): it is kept as fractions of the game's picture together with
// the number of abilities it covered, and the same icon size is kept around
// the same middle for any other count.

const HUD = { height: 1080, icon: 51, pitch: 58, iconFromBottom: 137, plusAbove: 40, middle: -10.5 };
// Room above the «+» buttons for the label and the arrow.
const ARROW_SPACE = 64;
const MIN_WIDTH = 320;
const MAX_SLOTS = 12;

function finite(value) {
  return typeof value === "number" && Number.isFinite(value);
}

// The ability bar {x, y (icon top), icon, pitch, plusTop} for `slots` abilities
// inside the game's picture `area`.
function autoBar(area, slots) {
  const scale = area.height / HUD.height;
  const count = Number.isInteger(slots) && slots > 0 ? slots : 4;
  const pitch = HUD.pitch * scale;
  const icon = HUD.icon * scale;
  const width = pitch * (count - 1) + icon;
  const middle = area.x + area.width / 2 + HUD.middle * scale;
  const y = area.y + area.height - HUD.iconFromBottom * scale;
  return { x: middle - width / 2, y, icon, pitch, plusTop: y - HUD.plusAbove * scale };
}

// A frame laid by hand (fractions + the count it covered) → the bar for `slots`.
function manualBar(frame, area, slots) {
  const rect = frameRect(frame, area);
  const pitch = rect.width / (frame.slots - 1 + HUD.icon / HUD.pitch);
  const icon = (pitch * HUD.icon) / HUD.pitch;
  const count = Number.isInteger(slots) && slots > 0 ? slots : frame.slots;
  const width = pitch * (count - 1) + icon;
  const middle = rect.x + rect.width / 2;
  return { x: middle - width / 2, y: rect.y, icon, pitch, plusTop: rect.y - (HUD.plusAbove / HUD.pitch) * pitch };
}

// The icons of a bar as one rectangle (the calibration frame).
function barFrame(bar, slots) {
  return {
    x: Math.round(bar.x),
    y: Math.round(bar.y),
    width: Math.round(bar.pitch * (slots - 1) + bar.icon),
    height: Math.round(bar.icon)
  };
}

// A stored hand-laid frame, or null when it is missing or broken.
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

// The arrow window over one ability, and the column to outline inside it (the
// «+» button and the icon, window coordinates).
function arrowLayout(bar, slot) {
  const left = bar.x + bar.pitch * slot;
  const middle = left + bar.icon / 2;
  const column = bar.y + bar.icon - bar.plusTop;
  const window = {
    x: Math.round(middle - MIN_WIDTH / 2),
    y: Math.round(bar.plusTop - ARROW_SPACE),
    width: MIN_WIDTH,
    height: Math.round(ARROW_SPACE + column)
  };
  const box = {
    x: Math.round(left - window.x),
    y: Math.round(bar.plusTop - window.y),
    width: Math.round(bar.icon),
    height: Math.round(column)
  };
  return { window, slot: box };
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
  HUD,
  MAX_SLOTS,
  arrowLayout,
  arrowTarget,
  autoBar,
  barFrame,
  frameFractions,
  frameRect,
  manualBar,
  validFrame
};
