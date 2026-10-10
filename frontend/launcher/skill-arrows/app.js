// The skill arrow (mode=arrow) and its calibration screen (mode=calibrate).
// The main process sends what to draw (skill-arrow-window.js); the page holds
// no data of its own.

const TEXT = {
  en: {
    title: "Skill arrows: fine-tune the frame",
    text:
      "The arrows find your ability icons by themselves. If they miss (another HUD or screen shape), drag the frame onto the icons at the bottom — from the first ability to the last, without the talent tree — and pull the edges to fit. Arrows ←↑→↓ move it by a pixel, with Shift by ten.",
    slots: "Abilities on the bar:",
    detected: "(seen in the game)",
    save: "Save",
    reset: "Undo my changes",
    auto: "Automatic",
    cancel: "Cancel"
  },
  uk: {
    title: "Стрілки над навичками: підправити рамку",
    text:
      "Стрілки самі знаходять іконки здібностей. Якщо промахуються (інший інтерфейс чи формат екрана), перетягніть рамку на іконки внизу — від першої здібності до останньої, без дерева талантів — і підтягніть краї. Стрілки ←↑→↓ рухають рамку на піксель, із Shift — на десять.",
    slots: "Здібностей на панелі:",
    detected: "(видно в грі)",
    save: "Зберегти",
    reset: "Повернути як було",
    auto: "Автоматично",
    cancel: "Скасувати"
  }
};

const MIN_SIZE = 24;
const mode = new URLSearchParams(window.location.search).get("mode");
const $ = (id) => document.getElementById(id);

function tableFor(locale) {
  return TEXT[locale] || TEXT.en;
}

// ---------------------------------------------------------------------------
// The arrow
// ---------------------------------------------------------------------------

function showArrow(payload) {
  const slot = payload && payload.slot;
  if (!slot) {
    $("arrow").classList.add("hidden");
    return;
  }
  const centre = slot.x + slot.width / 2;
  const label = $("arrow-label");
  label.textContent = payload.name || payload.title || "";
  label.classList.toggle("hidden", !label.textContent);
  label.style.left = `${clamp(centre, 0, window.innerWidth)}px`;
  const mark = document.querySelector(".arrow-mark");
  mark.style.left = `${centre}px`;
  mark.style.top = `${slot.y - 34}px`;
  const box = $("arrow-slot");
  Object.assign(box.style, {
    left: `${slot.x}px`,
    top: `${slot.y}px`,
    width: `${slot.width}px`,
    height: `${slot.height}px`
  });
  $("arrow").classList.remove("hidden");
  // Keep the label inside the window when the slot is near an edge.
  const half = label.offsetWidth / 2;
  label.style.left = `${clamp(centre, half + 4, window.innerWidth - half - 4)}px`;
}

function clamp(value, low, high) {
  return Math.min(Math.max(value, low), Math.max(low, high));
}

// ---------------------------------------------------------------------------
// Calibration
// ---------------------------------------------------------------------------

const calibration = { frame: null, initial: null, slots: 4, drag: null };

function startCalibration(payload) {
  const text = tableFor(payload.locale);
  document.documentElement.lang = payload.locale === "uk" ? "uk" : "en";
  $("cal-title").textContent = text.title;
  $("cal-text").textContent = text.text;
  $("cal-slots-label").textContent = text.slots;
  $("cal-detected").textContent = payload.detected ? text.detected : "";
  $("cal-save").textContent = text.save;
  $("cal-reset").textContent = text.reset;
  $("cal-auto").textContent = text.auto;
  $("cal-cancel").textContent = text.cancel;
  calibration.frame = { ...payload.frame };
  calibration.initial = { ...payload.frame };
  calibration.slots = payload.slots;
  $("calibrate").classList.remove("hidden");
  drawFrame();
  $("frame").focus();
}

function drawFrame() {
  const { frame, slots } = calibration;
  Object.assign($("frame").style, {
    left: `${frame.x}px`,
    top: `${frame.y}px`,
    width: `${frame.width}px`,
    height: `${frame.height}px`
  });
  $("cal-slots").textContent = String(slots);
  $("cal-minus").disabled = slots <= 1;
  $("cal-plus").disabled = slots >= 12;
  placePanel();
  const dividers = $("frame-slots");
  if (dividers.childElementCount !== slots) {
    dividers.replaceChildren(...Array.from({ length: slots }, () => document.createElement("span")));
  }
}

// The instructions stay off the frame: at the top when it fits above the
// frame, else right under it, else at the top anyway.
function placePanel() {
  const panel = document.querySelector(".panel");
  const { frame } = calibration;
  const height = panel.offsetHeight;
  let top = 16;
  if (top + height + 16 > frame.y) {
    const below = frame.y + frame.height + 16;
    top = below + height <= window.innerHeight ? below : 8;
  }
  panel.style.top = `${Math.round(top)}px`;
}

function keepInside(frame) {
  const width = Math.min(Math.max(frame.width, MIN_SIZE), window.innerWidth);
  const height = Math.min(Math.max(frame.height, MIN_SIZE), window.innerHeight);
  return {
    x: clamp(frame.x, 0, window.innerWidth - width),
    y: clamp(frame.y, 0, window.innerHeight - height),
    width,
    height
  };
}

function onPointerDown(event) {
  if (event.button !== 0) {
    return;
  }
  const edge = event.target.dataset.edge || "move";
  calibration.drag = { edge, x: event.clientX, y: event.clientY, start: { ...calibration.frame } };
  $("frame").setPointerCapture(event.pointerId);
  event.preventDefault();
}

function onPointerMove(event) {
  const drag = calibration.drag;
  if (!drag) {
    return;
  }
  const dx = event.clientX - drag.x;
  const dy = event.clientY - drag.y;
  const next = { ...drag.start };
  if (drag.edge === "move") {
    next.x += dx;
    next.y += dy;
  } else {
    if (drag.edge.includes("w")) {
      next.x += dx;
      next.width -= dx;
    }
    if (drag.edge.includes("e")) {
      next.width += dx;
    }
    if (drag.edge.includes("n")) {
      next.y += dy;
      next.height -= dy;
    }
    if (drag.edge.includes("s")) {
      next.height += dy;
    }
  }
  calibration.frame = keepInside(next);
  drawFrame();
}

function onPointerUp() {
  calibration.drag = null;
}

function onKey(event) {
  if (mode !== "calibrate") {
    return;
  }
  if (event.key === "Escape") {
    window.skillArrowApi.cancel();
    return;
  }
  if (event.key === "Enter" && document.activeElement === $("frame")) {
    save();
    return;
  }
  const step = event.shiftKey ? 10 : 1;
  const moves = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] };
  if (!moves[event.key] || document.activeElement !== $("frame")) {
    return;
  }
  const [dx, dy] = moves[event.key];
  const frame = calibration.frame;
  calibration.frame = keepInside({ ...frame, x: frame.x + dx, y: frame.y + dy });
  drawFrame();
  event.preventDefault();
}

function setSlots(delta) {
  calibration.slots = Math.min(12, Math.max(1, calibration.slots + delta));
  drawFrame();
}

function save() {
  const { frame, slots } = calibration;
  window.skillArrowApi.save({ ...frame, slots });
}

function resetFrame() {
  calibration.frame = { ...calibration.initial };
  drawFrame();
}

if (mode === "calibrate") {
  window.skillArrowApi.onCalibrate(startCalibration);
  const frame = $("frame");
  frame.addEventListener("pointerdown", onPointerDown);
  frame.addEventListener("pointermove", onPointerMove);
  frame.addEventListener("pointerup", onPointerUp);
  frame.addEventListener("pointercancel", onPointerUp);
  $("cal-minus").addEventListener("click", () => setSlots(-1));
  $("cal-plus").addEventListener("click", () => setSlots(1));
  $("cal-save").addEventListener("click", save);
  $("cal-reset").addEventListener("click", resetFrame);
  $("cal-auto").addEventListener("click", () => window.skillArrowApi.auto());
  $("cal-cancel").addEventListener("click", () => window.skillArrowApi.cancel());
  document.addEventListener("keydown", onKey);
} else {
  window.skillArrowApi.onShow(showArrow);
}
