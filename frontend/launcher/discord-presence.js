// Discord Rich Presence: «Играет в Dota 2 · Juggernaut · с тренером Wardly» on the
// player's Discord profile. Discord's desktop client listens on a local IPC pipe
// (discord-ipc-0..9); the frames are an int32 op, an int32 length and JSON. No
// bot, no token, no server: only the public Application ID. Nothing is sent when
// Discord is not running, and the switch in Settings turns it off.
//
// Pure parts (frames, pipe paths, the activity) are tested in
// test/discord-presence.test.js, the client against a fake Discord pipe.

const net = require("node:net");
const crypto = require("node:crypto");

const CLIENT_ID = "1554093692971655250";
const OP = { HANDSHAKE: 0, FRAME: 1, CLOSE: 2, PING: 3, PONG: 4 };
const SITE_URL = "https://luhovyimvp.dev";
const RETRY_MS = 30_000;

function encode(op, payload) {
  const json = Buffer.from(JSON.stringify(payload), "utf8");
  const header = Buffer.alloc(8);
  header.writeInt32LE(op, 0);
  header.writeInt32LE(json.length, 4);
  return Buffer.concat([header, json]);
}

/** Whole frames out of a stream buffer: { frames: [{ op, data }], rest }. */
function decode(buffer) {
  const frames = [];
  let offset = 0;
  while (buffer.length - offset >= 8) {
    const op = buffer.readInt32LE(offset);
    const length = buffer.readInt32LE(offset + 4);
    if (length < 0 || buffer.length - offset - 8 < length) {
      break;
    }
    const body = buffer.subarray(offset + 8, offset + 8 + length).toString("utf8");
    let data = null;
    try {
      data = JSON.parse(body);
    } catch {
      data = null;
    }
    frames.push({ op, data });
    offset += 8 + length;
  }
  return { frames, rest: buffer.subarray(offset) };
}

function ipcPath(index, { platform = process.platform, env = process.env } = {}) {
  if (platform === "win32") {
    return `\\\\?\\pipe\\discord-ipc-${index}`;
  }
  const base = env.XDG_RUNTIME_DIR || env.TMPDIR || env.TMP || env.TEMP || "/tmp";
  return `${base.replace(/\/+$/, "")}/discord-ipc-${index}`;
}

const TEXT = {
  ru: {
    match: (hero) => (hero ? `Матч на ${hero}` : "Матч в Dota 2"),
    menu: "В меню Dota 2",
    coach: "С тренером Wardly",
    large: "Wardly — тренер по Dota 2",
    button: "Wardly — тренер по Доте"
  },
  en: {
    match: (hero) => (hero ? `Playing ${hero}` : "In a Dota 2 match"),
    menu: "In the Dota 2 menu",
    coach: "With the Wardly coach",
    large: "Wardly — a Dota 2 coach",
    button: "Wardly — Dota 2 coach"
  }
};

/**
 * The activity for the current state, or null to clear it (Dota not running).
 * @param {{ dotaRunning: boolean, inMatch: boolean, hero: string|null, startedAt: number|null, lang: string }} input
 */
function buildActivity({ dotaRunning, inMatch, hero, startedAt, lang }) {
  if (!dotaRunning && !inMatch) {
    return null;
  }
  const t = TEXT[lang === "ru" ? "ru" : "en"];
  const activity = {
    details: inMatch ? t.match(hero) : t.menu,
    state: t.coach,
    assets: { large_image: "wardly", large_text: t.large },
    buttons: [{ label: t.button, url: SITE_URL }],
    instance: false
  };
  if (inMatch && Number.isFinite(startedAt)) {
    activity.timestamps = { start: Math.floor(startedAt / 1000) };
  }
  return activity;
}

/**
 * A small client: connects when there is something to show, sends the latest
 * activity (same one twice is sent once), reconnects every RETRY_MS while
 * Discord is closed. `log(message)` gets connection changes only.
 */
function createDiscordPresence({
  clientId = CLIENT_ID,
  connect = (path) => net.createConnection(path),
  pathFor = ipcPath,
  log = () => {},
  retryMs = RETRY_MS,
  pid = process.pid
} = {}) {
  let socket = null;
  let ready = false;
  let connecting = false;
  let wanted; // undefined: nothing asked yet; null: clear
  let sent = "";
  let retryTimer = null;
  let buffer = Buffer.alloc(0);
  let stopped = false;

  function send(activity) {
    const key = JSON.stringify(activity);
    if (!ready || !socket || key === sent) {
      return;
    }
    sent = key;
    socket.write(encode(OP.FRAME, { cmd: "SET_ACTIVITY", args: { pid, activity }, nonce: crypto.randomUUID() }));
  }

  function reset() {
    ready = false;
    connecting = false;
    sent = "";
    buffer = Buffer.alloc(0);
    if (socket) {
      socket.removeAllListeners();
      socket.destroy();
      socket = null;
    }
  }

  function scheduleRetry() {
    if (stopped || retryTimer || !wanted) {
      return;
    }
    retryTimer = setTimeout(() => {
      retryTimer = null;
      open();
    }, retryMs);
    retryTimer.unref?.();
  }

  function tryPipe(index) {
    if (index > 9) {
      connecting = false;
      scheduleRetry();
      return;
    }
    const candidate = connect(pathFor(index));
    candidate.once("error", () => {
      candidate.destroy();
      tryPipe(index + 1);
    });
    candidate.once("connect", () => {
      candidate.removeAllListeners("error");
      socket = candidate;
      socket.on("data", onData);
      socket.on("error", () => {});
      socket.on("close", () => {
        if (ready) {
          log("Discord closed the connection.");
        }
        reset();
        scheduleRetry();
      });
      socket.write(encode(OP.HANDSHAKE, { v: 1, client_id: clientId }));
    });
  }

  function onData(chunk) {
    buffer = Buffer.concat([buffer, chunk]);
    const { frames, rest } = decode(buffer);
    buffer = rest;
    for (const frame of frames) {
      if (frame.op === OP.PING) {
        socket.write(encode(OP.PONG, frame.data || {}));
      } else if (frame.op === OP.CLOSE) {
        log(`Discord refused the connection: ${frame.data && frame.data.message}`);
        reset();
        scheduleRetry();
        return;
      } else if (frame.op === OP.FRAME && frame.data && frame.data.evt === "READY") {
        ready = true;
        connecting = false;
        log("Connected to Discord.");
        if (wanted !== undefined) {
          send(wanted);
        }
      }
    }
  }

  function open() {
    if (stopped || socket || connecting) {
      return;
    }
    connecting = true;
    tryPipe(0);
  }

  return {
    /** The activity to show (null clears it). */
    update(activity) {
      wanted = activity;
      if (ready) {
        send(activity);
      } else if (activity) {
        open();
      }
    },
    isReady: () => ready,
    stop() {
      stopped = true;
      clearTimeout(retryTimer);
      retryTimer = null;
      if (socket && ready) {
        try {
          socket.write(encode(OP.FRAME, { cmd: "SET_ACTIVITY", args: { pid }, nonce: crypto.randomUUID() }));
        } catch {
          // Closing anyway.
        }
      }
      reset();
    }
  };
}

module.exports = { CLIENT_ID, OP, buildActivity, createDiscordPresence, decode, encode, ipcPath };
