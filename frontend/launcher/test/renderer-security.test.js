"use strict";

const assert = require("node:assert/strict");
const path = require("node:path");
const { EventEmitter } = require("node:events");
const test = require("node:test");
const { localPage, trustedSender, trustedHandlers, protectWindow } = require("../renderer-security");

const FILE = path.resolve(__dirname, "../renderer/index.html");
const PAGE = localPage(FILE);

function renderer(url = PAGE) {
  const contents = new EventEmitter();
  contents.mainFrame = { url };
  contents.isDestroyed = () => false;
  contents.setWindowOpenHandler = (handler) => { contents.openHandler = handler; };
  const window = { webContents: contents, isDestroyed: () => false };
  return { window, event: { sender: contents, senderFrame: contents.mainFrame } };
}

test("privileged callbacks only run for the current owner's local main frame", async () => {
  const registry = new Map();
  const owner = renderer();
  let current = owner.window;
  let calls = 0;
  trustedHandlers({ handle: (name, handler) => registry.set(name, handler) }, () => current, FILE)(
    "launcher:mutate", async (_event, value) => { calls += 1; return value; }
  );
  const invoke = registry.get("launcher:mutate");
  assert.equal(await invoke(owner.event, "saved"), "saved");
  const foreign = renderer(); // Same file/URL in another webContents is still untrusted.
  const subframe = { sender: owner.event.sender, senderFrame: { url: PAGE } };
  for (const event of [foreign.event, subframe, { ...owner.event, senderFrame: null }, {}]) {
    assert.throws(() => invoke(event, "unsafe"), /Untrusted IPC sender/);
  }
  owner.event.senderFrame.url = "https://audit.invalid/";
  assert.throws(() => invoke(owner.event, "unsafe"), /Untrusted IPC sender/);
  owner.event.senderFrame.url = PAGE;
  current = null;
  assert.throws(() => invoke(owner.event, "unsafe"), /Untrusted IPC sender/);
  current = foreign.window; // Recreated window does not authorize a queued old invoke.
  assert.throws(() => invoke(owner.event, "unsafe"), /Untrusted IPC sender/);
  assert.equal(calls, 1);
});

test("calibration mode, document identity and destroyed frames fail closed", () => {
  const expected = localPage(path.resolve(__dirname, "../skill-arrows/index.html"), { mode: "calibrate" });
  const owner = renderer(expected);
  assert.equal(trustedSender(owner.event, owner.window, expected), true);
  owner.event.senderFrame.url = `${expected}#help`;
  assert.equal(trustedSender(owner.event, owner.window, expected), true);
  for (const url of [expected.replace("calibrate", "arrow"), `${expected}&extra=1`, "about:blank", "not a URL", `${PAGE}?mode=calibrate`]) {
    owner.event.senderFrame.url = url;
    assert.equal(trustedSender(owner.event, owner.window, expected), false);
  }
  owner.event.senderFrame.url = expected;
  owner.window.isDestroyed = () => true;
  assert.equal(trustedSender(owner.event, owner.window, expected), false);
  owner.window.isDestroyed = () => false;
  owner.window.webContents.isDestroyed = () => true;
  assert.equal(trustedSender(owner.event, owner.window, expected), false);
  owner.window.webContents.isDestroyed = () => false;
  Object.defineProperty(owner.event, "senderFrame", { get: () => { throw new Error("Frame disposed"); } });
  assert.equal(trustedSender(owner.event, owner.window, expected), false);
});

test("navigation, redirects, subframes, webviews and popups are denied", () => {
  const { window } = renderer();
  protectWindow(window);
  assert.deepEqual(window.webContents.openHandler({ url: "https://audit.invalid" }), { action: "deny" });
  assert.deepEqual(window.webContents.openHandler({ url: PAGE }), { action: "deny" });
  for (const name of ["will-navigate", "will-frame-navigate", "will-redirect", "will-attach-webview"]) {
    let prevented = false;
    window.webContents.emit(name, { preventDefault: () => { prevented = true; } });
    assert.equal(prevented, true, name);
  }
});
