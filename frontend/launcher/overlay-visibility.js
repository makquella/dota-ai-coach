// Pure decision logic for "should the overlay be on screen" and the tray
// status line. Kept free of Electron so it can be unit-tested with node --test.

const DOTA_STATUS = {
  NOT_FOUND: "not_found",
  WAITING: "waiting",
  IN_GAME: "in_game"
};

/**
 * @param {object} input
 * @param {boolean} input.enabled      user switch (tray "Overlay", Ctrl+Alt+O)
 * @param {boolean} input.unlocked     overlay unlocked for dragging (Ctrl+Alt+L)
 * @param {boolean} input.demoRunning  replay demo is playing (no Dota needed)
 * @param {object}  input.dota         watcher state { supported, running, focused }
 * @param {boolean} input.inMatch      backend /gsi/status in_match (fresh GSI from a match)
 * @returns {{ visible: boolean, reason: string }}
 */
function overlayVisibility({ enabled, unlocked, demoRunning, dota = {}, inMatch }) {
  if (!enabled) {
    return { visible: false, reason: "overlay switched off" };
  }
  if (unlocked) {
    return { visible: true, reason: "unlocked for positioning" };
  }
  if (demoRunning) {
    return { visible: true, reason: "replay demo" };
  }
  if (!dota.supported) {
    return { visible: true, reason: "focus tracking unavailable" };
  }
  if (!dota.running) {
    return { visible: false, reason: "Dota 2 is not running" };
  }
  if (!dota.focused) {
    return { visible: false, reason: "Dota 2 is not the active window" };
  }
  if (!inMatch) {
    return { visible: false, reason: "no fresh GSI from a match" };
  }
  return { visible: true, reason: "in game" };
}

function dotaStatus({ dota = {}, inMatch }) {
  if (dota.supported && !dota.running) {
    // GSI stays "fresh" for a few seconds after Dota exits; the process wins.
    return DOTA_STATUS.NOT_FOUND;
  }
  if (inMatch) {
    // Without process tracking, fresh match data is the only proof Dota runs.
    return DOTA_STATUS.IN_GAME;
  }
  return dota.running ? DOTA_STATUS.WAITING : DOTA_STATUS.NOT_FOUND;
}

module.exports = { DOTA_STATUS, dotaStatus, overlayVisibility };
