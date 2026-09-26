const { spawn } = require("node:child_process");
const { EventEmitter } = require("node:events");
const fs = require("node:fs");
const path = require("node:path");
const readline = require("node:readline");

// Watches whether dota2.exe is running and whether its window is the active
// (foreground, not minimized) window.
//
// Windows: one long-lived hidden PowerShell process calls user32
// GetForegroundWindow/GetWindowThreadProcessId/IsIconic in a loop and prints a
// JSON line whenever the state changes (plus a heartbeat line every ~20 polls
// so the launcher can tell it is alive). No native Node modules are needed, and
// the helper exits by itself when the launcher process disappears.
// Linux (dev): /proc is scanned for a "dota2" process; focus is not tracked.

const WINDOWS_POLL_RUNNING_MS = 300;
const WINDOWS_POLL_IDLE_MS = 1500;
const LINUX_POLL_MS = 2000;
const MAX_FAST_FAILURES = 5;

const WINDOWS_WATCH_SCRIPT = String.raw`
$ErrorActionPreference = 'Stop'
$parentPid = __PARENT_PID__
Add-Type -Namespace DotaAICoach -Name Win32 -MemberDefinition @'
[DllImport("user32.dll")] public static extern System.IntPtr GetForegroundWindow();
[DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(System.IntPtr hWnd, out uint processId);
[DllImport("user32.dll")] public static extern bool IsIconic(System.IntPtr hWnd);
'@
$last = ''
$ticks = 0
while ($true) {
  try { $null = [System.Diagnostics.Process]::GetProcessById($parentPid) } catch { exit 0 }
  $running = $false
  $focused = $false
  $exe = ''
  $procs = [System.Diagnostics.Process]::GetProcessesByName('dota2')
  if ($procs.Length -gt 0) {
    $running = $true
    $hwnd = [DotaAICoach.Win32]::GetForegroundWindow()
    [uint32]$fgPid = 0
    [void][DotaAICoach.Win32]::GetWindowThreadProcessId($hwnd, [ref]$fgPid)
    foreach ($p in $procs) {
      if ($p.Id -eq $fgPid -and -not [DotaAICoach.Win32]::IsIconic($hwnd)) { $focused = $true }
      if (-not $exe) { try { $exe = [string]$p.Path } catch { } }
      $p.Dispose()
    }
  }
  $line = [ordered]@{ running = $running; focused = $focused; path = $exe } | ConvertTo-Json -Compress
  $ticks++
  if ($line -ne $last -or $ticks -ge 20) {
    [Console]::Out.WriteLine($line)
    [Console]::Out.Flush()
    $last = $line
    $ticks = 0
  }
  if ($running) { Start-Sleep -Milliseconds __POLL_RUNNING_MS__ } else { Start-Sleep -Milliseconds __POLL_IDLE_MS__ }
}
`;

function windowsWatchScript(parentPid) {
  return WINDOWS_WATCH_SCRIPT.replace("__PARENT_PID__", String(Number(parentPid) || 0))
    .replace("__POLL_RUNNING_MS__", String(WINDOWS_POLL_RUNNING_MS))
    .replace("__POLL_IDLE_MS__", String(WINDOWS_POLL_IDLE_MS));
}

function encodePowerShell(script) {
  return Buffer.from(script, "utf16le").toString("base64");
}

function parseWatcherLine(line) {
  try {
    const data = JSON.parse(String(line).trim());
    if (!data || typeof data !== "object") {
      return null;
    }
    return {
      running: Boolean(data.running),
      focused: Boolean(data.running) && Boolean(data.focused),
      exePath: typeof data.path === "string" ? data.path : ""
    };
  } catch {
    return null;
  }
}

function powershellPath(env = process.env) {
  const systemRoot = env.SystemRoot || env.windir || "C:\\Windows";
  const candidate = path.win32.join(systemRoot, "System32", "WindowsPowerShell", "v1.0", "powershell.exe");
  return fs.existsSync(candidate) ? candidate : "powershell.exe";
}

function isDotaRunningOnLinux(procDir = "/proc") {
  let entries = [];
  try {
    entries = fs.readdirSync(procDir);
  } catch {
    return false;
  }
  for (const entry of entries) {
    if (!/^\d+$/.test(entry)) {
      continue;
    }
    try {
      if (fs.readFileSync(path.join(procDir, entry, "comm"), "utf8").trim() === "dota2") {
        return true;
      }
    } catch {
      // Process exited while scanning.
    }
  }
  return false;
}

/**
 * state: { supported, running, focused, exePath }
 *   supported - focus tracking works on this platform (Windows only).
 * Emits "change" with the new state.
 */
function createDotaWatcher({ platform = process.platform, log = () => {}, spawnImpl = spawn, parentPid = process.pid } = {}) {
  const emitter = new EventEmitter();
  let state = { supported: platform === "win32", running: false, focused: false, exePath: "" };
  let child = null;
  let stopped = true;
  let restartTimer = null;
  let linuxTimer = null;
  let fastFailures = 0;

  function update(patch) {
    const next = { ...state, ...patch };
    if (next.exePath === "" && state.exePath && next.running) {
      next.exePath = state.exePath;
    }
    const changed = ["supported", "running", "focused", "exePath"].some((key) => next[key] !== state[key]);
    state = next;
    if (changed) {
      emitter.emit("change", { ...state });
    }
  }

  function startWindows() {
    const startedAt = Date.now();
    let sawOutput = false;
    try {
      child = spawnImpl(
        powershellPath(),
        [
          "-NoLogo",
          "-NoProfile",
          "-NonInteractive",
          "-ExecutionPolicy",
          "Bypass",
          "-EncodedCommand",
          encodePowerShell(windowsWatchScript(parentPid))
        ],
        { windowsHide: true, stdio: ["ignore", "pipe", "pipe"] }
      );
    } catch (error) {
      log(`Dota watcher could not start PowerShell: ${error.message}`);
      giveUp();
      return;
    }
    const current = child;
    readline.createInterface({ input: current.stdout }).on("line", (line) => {
      const parsed = parseWatcherLine(line);
      if (parsed) {
        sawOutput = true;
        fastFailures = 0;
        update(parsed);
        emitter.emit("report", { ...state });
      }
    });
    current.stderr.on("data", (chunk) => log(`Dota watcher: ${String(chunk).trim()}`));
    let ended = false;
    const handleEnd = (code) => {
      if (ended) {
        return;
      }
      ended = true;
      if (child === current) {
        child = null;
      }
      if (stopped) {
        return;
      }
      update({ running: false, focused: false });
      if (!sawOutput || Date.now() - startedAt < 5000) {
        fastFailures += 1;
      }
      if (fastFailures >= MAX_FAST_FAILURES) {
        giveUp();
        return;
      }
      log(`Dota watcher exited (code ${code}); restarting.`);
      restartTimer = setTimeout(startWindows, 3000);
      restartTimer.unref?.();
    };
    current.on("error", (error) => {
      log(`Dota watcher error: ${error.message}`);
      if (!current.pid) {
        // Spawn failed (e.g. PowerShell missing); "exit" will not follow.
        handleEnd(null);
      }
    });
    current.on("exit", handleEnd);
  }

  function giveUp() {
    log("Dota focus tracking is unavailable; the overlay will follow its on/off switch only.");
    update({ supported: false, running: false, focused: false });
    emitter.emit("report", { ...state });
  }

  function startLinux() {
    const tick = () => {
      const running = isDotaRunningOnLinux();
      update({ running, focused: running });
      emitter.emit("report", { ...state });
    };
    tick();
    linuxTimer = setInterval(tick, LINUX_POLL_MS);
    linuxTimer.unref?.();
  }

  emitter.start = () => {
    if (!stopped) {
      return;
    }
    stopped = false;
    if (platform === "win32") {
      startWindows();
    } else if (platform === "linux") {
      startLinux();
    }
  };

  emitter.stop = () => {
    stopped = true;
    clearTimeout(restartTimer);
    clearInterval(linuxTimer);
    if (child) {
      try {
        child.kill();
      } catch {
        // Already gone.
      }
      child = null;
    }
  };

  emitter.getState = () => ({ ...state });
  return emitter;
}

module.exports = { createDotaWatcher, parseWatcherLine, windowsWatchScript, encodePowerShell };
