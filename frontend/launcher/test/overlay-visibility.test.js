const assert = require("node:assert/strict");
const test = require("node:test");

const { DOTA_STATUS, dotaStatus, overlayVisibility } = require("../overlay-visibility");

const IN_DOTA = { supported: true, running: true, focused: true };
const base = { enabled: true, unlocked: false, demoRunning: false, dota: IN_DOTA, inMatch: true };

test("shown only when Dota runs, is focused and GSI is fresh from a match", () => {
  assert.equal(overlayVisibility(base).visible, true);
  assert.equal(overlayVisibility({ ...base, dota: { ...IN_DOTA, running: false, focused: false } }).visible, false);
  assert.equal(overlayVisibility({ ...base, dota: { ...IN_DOTA, focused: false } }).visible, false);
  assert.equal(overlayVisibility({ ...base, inMatch: false }).visible, false);
});

test("the on/off switch always wins", () => {
  assert.equal(overlayVisibility({ ...base, enabled: false }).visible, false);
  assert.equal(overlayVisibility({ ...base, enabled: false, unlocked: true, demoRunning: true }).visible, false);
});

test("positioning and replay demo show it without Dota", () => {
  const noDota = { ...base, dota: { supported: true, running: false, focused: false }, inMatch: false };
  assert.equal(overlayVisibility({ ...noDota, unlocked: true }).visible, true);
  assert.equal(overlayVisibility({ ...noDota, demoRunning: true }).visible, true);
});

test("falls back to the switch when focus tracking is unavailable", () => {
  const result = overlayVisibility({ ...base, dota: { supported: false, running: false, focused: false }, inMatch: false });
  assert.equal(result.visible, true);
});

test("tray status", () => {
  assert.equal(dotaStatus({ dota: { running: false }, inMatch: false }), DOTA_STATUS.NOT_FOUND);
  assert.equal(dotaStatus({ dota: { running: true }, inMatch: false }), DOTA_STATUS.WAITING);
  assert.equal(dotaStatus({ dota: { running: true }, inMatch: true }), DOTA_STATUS.IN_GAME);
});

test("a tracked but exited Dota is not reported in game while GSI is still fresh", () => {
  assert.equal(dotaStatus({ dota: { supported: true, running: false }, inMatch: true }), DOTA_STATUS.NOT_FOUND);
  // Without process tracking, fresh match data is trusted.
  assert.equal(dotaStatus({ dota: { supported: false, running: false }, inMatch: true }), DOTA_STATUS.IN_GAME);
});

test("the score screen with a fresh review shows the summary, only in focused Dota", () => {
  const scoreScreen = { ...base, inMatch: false, postGame: true };
  const shown = overlayVisibility(scoreScreen);
  assert.equal(shown.visible, true);
  assert.equal(shown.code, "post_game");
  assert.equal(overlayVisibility({ ...scoreScreen, dota: { ...IN_DOTA, focused: false } }).visible, false);
  assert.equal(overlayVisibility({ ...scoreScreen, enabled: false }).visible, false);
  assert.equal(dotaStatus({ dota: IN_DOTA, inMatch: false }), DOTA_STATUS.WAITING);
});
