const { spawn } = require("node:child_process");
const { EventEmitter } = require("node:events");
const fs = require("node:fs");
const path = require("node:path");
const readline = require("node:readline");

// Watches whether dota2.exe is running, whether its window is the active
// (foreground, not minimized) window, where that window is (so the overlay can
// follow Dota to its monitor) and whether Dota runs in exclusive fullscreen,
// where no other window can be drawn on top of it.
//
// Windows: one long-lived hidden PowerShell process calls user32
// GetForegroundWindow/GetWindowThreadProcessId/IsIconic/GetClientRect and
// shell32 SHQueryUserNotificationState in a loop and prints a JSON line
// whenever the state changes (plus a heartbeat line every ~20 polls so the
// launcher can tell it is alive). No native Node modules are needed, and the
// helper exits by itself when the launcher process disappears.
// Linux (dev): /proc is scanned for a "dota2" process; focus is not tracked.

const WINDOWS_POLL_RUNNING_MS = 300;
const WINDOWS_POLL_IDLE_MS = 1500;
const LINUX_POLL_MS = 2000;
const MAX_FAST_FAILURES = 5;

// SHQueryUserNotificationState returns QUNS_RUNNING_D3D_FULL_SCREEN (3) while
// a Direct3D exclusive-fullscreen app is in front. The flag is sampled while
// Dota is focused and kept until Dota exits, so alt-tab does not clear it.
// The helper is DPI aware: "rect" is in physical screen pixels.
const WINDOWS_WATCH_SCRIPT = String.raw`
$ErrorActionPreference = 'Stop'
$parentPid = __PARENT_PID__
Add-Type -Namespace DotaAICoach -Name Win32 -MemberDefinition @'
[System.Runtime.InteropServices.StructLayout(System.Runtime.InteropServices.LayoutKind.Sequential)]
public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
[DllImport("user32.dll")] public static extern System.IntPtr GetForegroundWindow();
[DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(System.IntPtr hWnd, out uint processId);
[DllImport("user32.dll")] public static extern bool IsIconic(System.IntPtr hWnd);
public struct POINT { public int X; public int Y; }
[DllImport("user32.dll")] public static extern bool GetClientRect(System.IntPtr hWnd, out RECT rect);
[DllImport("user32.dll")] public static extern bool ClientToScreen(System.IntPtr hWnd, ref POINT point);
[DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
[DllImport("shell32.dll")] public static extern int SHQueryUserNotificationState(out int state);
'@
try { [void][DotaAICoach.Win32]::SetProcessDPIAware() } catch { }
$last = ''
$ticks = 0
$fullscreen = $false
$rect = $null
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
      $main = [System.IntPtr]::Zero
      try { $main = $p.MainWindowHandle } catch { }
      if ($main -ne [System.IntPtr]::Zero -and -not [DotaAICoach.Win32]::IsIconic($main)) {
        $r = New-Object DotaAICoach.Win32+RECT
        $o = New-Object DotaAICoach.Win32+POINT
        if ([DotaAICoach.Win32]::GetClientRect($main, [ref]$r) -and $r.Right -gt 0 -and [DotaAICoach.Win32]::ClientToScreen($main, [ref]$o)) {
          $rect = @($o.X, $o.Y, ($o.X + $r.Right), ($o.Y + $r.Bottom))
        }
      }
      $p.Dispose()
    }
    if ($focused) {
      [int]$quns = 0
      try {
        if ([DotaAICoach.Win32]::SHQueryUserNotificationState([ref]$quns) -eq 0) { $fullscreen = ($quns -eq 3) }
      } catch { }
    }
  } else {
    $fullscreen = $false
    $rect = $null
  }
  $line = [ordered]@{ running = $running; focused = $focused; path = $exe; fullscreen = $fullscreen; rect = $rect } | ConvertTo-Json -Compress
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
    const running = Boolean(data.running);
    return {
      running,
      focused: running && Boolean(data.focused),
      exePath: typeof data.path === "string" ? data.path : "",
      exclusiveFullscreen: running && Boolean(data.fullscreen),
      windowRect: running ? parseRect(data.rect) : null
    };
  } catch {
    return null;
  }
}

// [left, top, right, bottom] in physical pixels -> { x, y, width, height }.
function parseRect(value) {
  if (!Array.isArray(value) || value.length !== 4 || !value.every(Number.isFinite)) {
    return null;
  }
  const [left, top, right, bottom] = value;
  if (right <= left || bottom <= top) {
    return null;
  }
  return { x: left, y: top, width: right - left, height: bottom - top };
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
 * state: { supported, running, focused, exePath, exclusiveFullscreen, windowRect }
 *   supported           - focus tracking works on this platform (Windows only).
 *   exclusiveFullscreen - Dota was last seen in exclusive fullscreen (no overlay
 *                         can be drawn over it); reset when Dota exits.
 *   windowRect          - Dota's window in physical pixels, or null.
 * Emits "change" with the new state.
 */
function createDotaWatcher({ platform = process.platform, log = () => {}, spawnImpl = spawn, parentPid = process.pid } = {}) {
  const emitter = new EventEmitter();
  let state = {
    supported: platform === "win32",
    running: false,
    focused: false,
    exePath: "",
    exclusiveFullscreen: false,
    windowRect: null
  };
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
    const changed =
      ["supported", "running", "focused", "exePath", "exclusiveFullscreen"].some((key) => next[key] !== state[key]) ||
      JSON.stringify(next.windowRect) !== JSON.stringify(state.windowRect);
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
      update({ running: false, focused: false, exclusiveFullscreen: false, windowRect: null });
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
    update({ supported: false, running: false, focused: false, exclusiveFullscreen: false, windowRect: null });
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

module.exports = { createDotaWatcher, parseWatcherLine, parseRect, windowsWatchScript, encodePowerShell };
