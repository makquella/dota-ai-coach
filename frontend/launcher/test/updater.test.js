const assert = require("node:assert/strict");
const { EventEmitter } = require("node:events");
const test = require("node:test");

const { createUpdater, IDLE_INSTALL_AFTER_MS, UPDATE_STATUS } = require("../updater");

function fakeAutoUpdater() {
  const updater = new EventEmitter();
  updater.checks = 0;
  updater.installs = [];
  updater.checkForUpdates = async () => {
    updater.checks += 1;
  };
  updater.quitAndInstall = (...args) => updater.installs.push(args);
  return updater;
}

function started(options = {}) {
  const fake = fakeAutoUpdater();
  let clock = 1000;
  const updater = createUpdater({
    currentVersion: "0.1.0",
    supported: true,
    loadAutoUpdater: () => fake,
    now: () => clock,
    ...options
  });
  updater.start();
  updater.stop();
  return { updater, fake, advance: (ms) => (clock += ms) };
}

test("unsupported builds never load electron-updater", () => {
  let loaded = false;
  const updater = createUpdater({ supported: false, loadAutoUpdater: () => (loaded = true) });
  updater.start();
  updater.stop();
  assert.equal(loaded, false);
  assert.equal(updater.getState().status, UPDATE_STATUS.DISABLED);
});

test("a missing electron-updater module disables updates instead of crashing", () => {
  const updater = createUpdater({
    supported: true,
    loadAutoUpdater: () => {
      throw new Error("Cannot find module 'electron-updater'");
    }
  });
  updater.start();
  updater.stop();
  assert.equal(updater.getState().status, UPDATE_STATUS.DISABLED);
  assert.equal(updater.getState().supported, false);
});

test("events move the state from checking to ready", async () => {
  const { updater, fake } = started();
  assert.equal(fake.autoDownload, true);
  assert.equal(fake.autoInstallOnAppQuit, true);
  const states = [];
  updater.on("change", (state) => states.push(state.status));

  await updater.check();
  assert.equal(fake.checks, 1);
  fake.emit("checking-for-update");
  fake.emit("update-available", { version: "0.2.0" });
  fake.emit("download-progress", { percent: 41.6 });
  assert.equal(updater.getState().percent, 42);
  fake.emit("update-downloaded", { version: "0.2.0" });

  assert.deepEqual(states, ["checking", "downloading", "downloading", "ready"]);
  assert.equal(updater.getState().version, "0.2.0");
  // While an update is downloaded, further checks do nothing.
  await updater.check();
  assert.equal(fake.checks, 1);
});

test("an error after download keeps the ready update", () => {
  const { updater, fake } = started();
  fake.emit("update-downloaded", { version: "0.2.0" });
  fake.emit("error", new Error("net::ERR_INTERNET_DISCONNECTED"));
  assert.equal(updater.getState().status, UPDATE_STATUS.READY);
});

test("check errors are reported, not thrown", async () => {
  const { updater, fake } = started();
  fake.checkForUpdates = async () => {
    throw new Error("HttpError: 404");
  };
  const state = await updater.check();
  assert.equal(state.status, UPDATE_STATUS.ERROR);
  assert.match(state.error, /404/);
});

test("install runs only when an update is ready, silently and relaunching", () => {
  const seen = [];
  const { updater, fake } = started({ beforeInstall: (info) => seen.push(info) });
  assert.equal(updater.install(), false);
  fake.emit("update-downloaded", { version: "0.2.0" });
  assert.equal(updater.install(), true);
  assert.deepEqual(fake.installs, [[true, true]]);
  assert.deepEqual(seen, [{ unattended: false }]);
  assert.equal(updater.install(), false);
});

test("unattended install waits until Dota has been closed for a while", () => {
  let idle = false;
  const seen = [];
  const { updater, fake, advance } = started({
    canInstallNow: () => idle,
    beforeInstall: (info) => seen.push(info)
  });
  fake.emit("update-downloaded", { version: "0.2.0" });

  updater.idleTick();
  advance(IDLE_INSTALL_AFTER_MS * 2);
  updater.idleTick();
  assert.equal(fake.installs.length, 0, "never while Dota runs");

  idle = true;
  updater.idleTick();
  advance(IDLE_INSTALL_AFTER_MS - 1);
  updater.idleTick();
  assert.equal(fake.installs.length, 0);

  idle = false;
  updater.idleTick();
  idle = true;
  updater.idleTick();
  advance(IDLE_INSTALL_AFTER_MS);
  updater.idleTick();
  assert.equal(fake.installs.length, 1);
  assert.deepEqual(seen, [{ unattended: true }]);
});

test("no install while Dota runs, manual or unattended", () => {
  let gameRunning = true;
  const { updater, fake, advance } = started({ isGameRunning: () => gameRunning, canInstallNow: () => true });
  fake.emit("update-downloaded", { version: "0.2.0" });

  assert.equal(updater.install(), false, "manual install is refused mid-game");
  updater.idleTick();
  advance(IDLE_INSTALL_AFTER_MS * 2);
  updater.idleTick();
  assert.equal(fake.installs.length, 0);

  gameRunning = false;
  assert.equal(updater.install(), true);
  assert.equal(fake.installs.length, 1);
});
