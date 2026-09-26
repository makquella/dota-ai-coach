// Pure geometry for the overlay window (no Electron, unit-tested).
//
// The card is placed relative to Dota's window, not the primary monitor: on a
// multi-monitor setup it follows the game to its screen, and in windowed mode
// it stays inside the game window. Without a Dota window (not running,
// minimized, focus tracking unavailable) the given fallback area is used.

const MARGIN = 24;
// The minimap and the hero panel take roughly the bottom 22% of the game.
const HUD_BOTTOM_SHARE = 0.24;
const PRESETS = ["left-center", "right-center", "bottom-center"];

function intersect(a, b) {
  const x = Math.max(a.x, b.x);
  const y = Math.max(a.y, b.y);
  const right = Math.min(a.x + a.width, b.x + b.width);
  const bottom = Math.min(a.y + a.height, b.y + b.height);
  if (right <= x || bottom <= y) {
    return null;
  }
  return { x, y, width: right - x, height: bottom - y };
}

/**
 * Area the presets are computed in.
 * @param {object|null} dotaRect  Dota's window in DIP (already converted from physical pixels)
 * @param {object|null} display   Electron display that contains most of dotaRect
 * @param {object} fallbackArea   work area used when there is no Dota window
 * @param {{width:number,height:number}} size overlay window size
 */
function anchorArea({ dotaRect, display, fallbackArea, size }) {
  if (!dotaRect || !display) {
    return fallbackArea;
  }
  // Fullscreen Dota covers the taskbar too, so clip to the full display bounds.
  const visible = intersect(dotaRect, display.bounds || display.workArea);
  if (!visible || visible.width < size.width + 2 * MARGIN || visible.height < size.height + 2 * MARGIN) {
    // A tiny game window cannot hold the card; use its monitor instead.
    return display.workArea || fallbackArea;
  }
  return visible;
}

function presetBounds(preset, area, size) {
  const { width, height } = size;
  let x = area.x + area.width - width - MARGIN;
  let y = area.y + Math.round((area.height - height) / 2);
  if (preset === "left-center") {
    x = area.x + MARGIN;
  } else if (preset === "bottom-center") {
    x = area.x + Math.round((area.width - width) / 2);
    y = area.y + area.height - Math.round(area.height * HUD_BOTTOM_SHARE) - height;
  }
  return { x: Math.round(x), y: Math.round(y), width, height };
}

// A hand-placed card must stay reachable after a monitor is unplugged or the
// resolution changes: at least a 48x48 piece of it has to be on some display.
function isReachable(bounds, displayAreas) {
  return displayAreas.some((area) => {
    const visible = intersect(bounds, area);
    return Boolean(visible && visible.width >= 48 && visible.height >= 48);
  });
}

function sameBounds(a, b) {
  return Boolean(a && b) && a.x === b.x && a.y === b.y && a.width === b.width && a.height === b.height;
}

module.exports = { MARGIN, PRESETS, anchorArea, intersect, isReachable, presetBounds, sameBounds };
