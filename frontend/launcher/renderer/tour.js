// The first-run tour («Путівник»): a dimmed panel with a cut-out around one
// element and a small card next to it — what the element is for, Back / Next /
// Skip. Pure placement rules (tested in node, test/tour.test.js) + the drawing;
// loaded as a plain script by the control panel (window.LauncherTour). The steps
// and their texts come from renderer/app.js.
(function attach(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    root.LauncherTour = api;
  }
})(typeof self !== "undefined" ? self : this, () => {
  const MARGIN = 12; // from the window edge
  const GAP = 14; // between the element and the card
  const PAD = 6; // around the element inside the cut-out

  /**
   * Where the card goes for an element's box: below it when it fits, else above,
   * else to its right, else to its left, else in the middle of the window; always
   * inside the window. `target` null → the middle (a step without an element).
   */
  function placeBubble(target, bubble, viewport) {
    const clampX = (x) => Math.max(MARGIN, Math.min(x, viewport.width - bubble.width - MARGIN));
    const clampY = (y) => Math.max(MARGIN, Math.min(y, viewport.height - bubble.height - MARGIN));
    const centered = {
      side: "center",
      left: Math.round(clampX((viewport.width - bubble.width) / 2)),
      top: Math.round(clampY((viewport.height - bubble.height) / 2))
    };
    if (!target) {
      return centered;
    }
    const middleX = target.left + target.width / 2 - bubble.width / 2;
    const middleY = target.top + target.height / 2 - bubble.height / 2;
    const below = target.top + target.height + GAP;
    if (below + bubble.height <= viewport.height - MARGIN) {
      return { side: "below", left: Math.round(clampX(middleX)), top: Math.round(below) };
    }
    const above = target.top - GAP - bubble.height;
    if (above >= MARGIN) {
      return { side: "above", left: Math.round(clampX(middleX)), top: Math.round(above) };
    }
    const right = target.left + target.width + GAP;
    if (right + bubble.width <= viewport.width - MARGIN) {
      return { side: "right", left: Math.round(right), top: Math.round(clampY(middleY)) };
    }
    const left = target.left - GAP - bubble.width;
    if (left >= MARGIN) {
      return { side: "left", left: Math.round(left), top: Math.round(clampY(middleY)) };
    }
    return centered;
  }

  /** The cut-out around an element (padded, kept inside the window). */
  function spotlight(target, viewport) {
    const left = Math.max(0, target.left - PAD);
    const top = Math.max(0, target.top - PAD);
    return {
      left,
      top,
      width: Math.min(viewport.width, target.left + target.width + PAD) - left,
      height: Math.min(viewport.height, target.top + target.height + PAD) - top
    };
  }

  /** Whether any part of an element is inside the window (scrolled away → no cut-out). */
  function onScreen(target, viewport) {
    return (
      target.width > 0 &&
      target.height > 0 &&
      target.left + target.width > 0 &&
      target.top + target.height > 0 &&
      target.left < viewport.width &&
      target.top < viewport.height
    );
  }

  /** The step to show after `index` in `direction` (+1 / -1), skipping unavailable ones; -1 past the end. */
  function nextIndex(steps, index, direction, available) {
    for (let i = index + direction; i >= 0 && i < steps.length; i += direction) {
      if (available(steps[i])) {
        return i;
      }
    }
    return direction > 0 ? -1 : index;
  }

  // --- drawing --------------------------------------------------------------------

  function visibleElement(doc, selector) {
    if (!selector) {
      return null;
    }
    const element = doc.querySelector(selector);
    if (!element || element.closest(".hidden") || element.getClientRects().length === 0) {
      return null;
    }
    return element;
  }

  /**
   * Starts the tour. options: { steps: [{ id, target?, view?, title, text, image? }],
   * labels: { next, back, skip, done, count(i, n) }, openView(view), viewSelector, onClose(completed) }.
   * A step whose element is hidden (other than by its closed view) is skipped; a
   * step without `target` never is.
   */
  function start(options) {
    const doc = options.document || document;
    const win = doc.defaultView || window;
    const { steps, labels } = options;
    // Whether a step can be shown, without switching views: its element exists and
    // nothing but a closed view (options.viewSelector, e.g. ".view") hides it.
    const available = (step) => {
      if (!step.target) {
        return true;
      }
      const element = doc.querySelector(step.target);
      if (!element) {
        return false;
      }
      const hidden = element.closest(".hidden");
      return !hidden || Boolean(options.viewSelector && hidden.matches(options.viewSelector) && !hidden.parentElement?.closest(".hidden"));
    };

    const layer = doc.createElement("div");
    layer.className = "tour";
    const spot = doc.createElement("div");
    spot.className = "tour-spot";
    const bubble = doc.createElement("section");
    bubble.className = "tour-bubble";
    bubble.setAttribute("role", "dialog");
    bubble.setAttribute("aria-modal", "true");
    bubble.setAttribute("aria-labelledby", "tour-title");
    bubble.setAttribute("aria-describedby", "tour-text");
    const count = doc.createElement("p");
    count.className = "tour-count";
    const title = doc.createElement("h2");
    title.id = "tour-title";
    title.className = "tour-title";
    const text = doc.createElement("p");
    text.id = "tour-text";
    text.className = "tour-text";
    // A step can show a picture (a real advice card) between the title and the text.
    const picture = doc.createElement("img");
    picture.className = "tour-image";
    picture.alt = "";
    picture.hidden = true;
    const actions = doc.createElement("div");
    actions.className = "tour-actions";
    const skip = button(doc, "btn btn-ghost btn-sm", labels.skip);
    const back = button(doc, "btn btn-sm", labels.back);
    const next = button(doc, "btn btn-primary btn-sm", labels.next);
    const spacer = doc.createElement("span");
    spacer.className = "tour-spacer";
    actions.append(skip, spacer, back, next);
    bubble.append(count, title, picture, text, actions);
    layer.append(spot, bubble);
    doc.body.append(layer);

    let index = -1;
    let frame = 0;
    const previousFocus = doc.activeElement;

    // `reveal`: scroll the element into view first (a new step, a resized window);
    // a scroll by the player only moves the cut-out and the card along with it.
    function position(reveal) {
      const step = steps[index];
      const viewport = { width: win.innerWidth, height: win.innerHeight };
      const element = visibleElement(doc, step.target);
      if (element && reveal) {
        element.scrollIntoView({ block: "nearest", inline: "nearest" });
      }
      const rect = element ? element.getBoundingClientRect() : null;
      const seen = rect ? { left: rect.left, top: rect.top, width: rect.width, height: rect.height } : null;
      const box = seen && onScreen(seen, viewport) ? seen : null;
      if (box) {
        const cut = spotlight(box, viewport);
        Object.assign(spot.style, { left: `${cut.left}px`, top: `${cut.top}px`, width: `${cut.width}px`, height: `${cut.height}px` });
      } else {
        Object.assign(spot.style, { left: "50%", top: "50%", width: "0px", height: "0px" });
      }
      spot.classList.toggle("tour-spot-none", !box);
      const size = bubble.getBoundingClientRect();
      const place = placeBubble(box, { width: size.width, height: size.height }, viewport);
      bubble.dataset.side = place.side;
      Object.assign(bubble.style, { left: `${place.left}px`, top: `${place.top}px` });
    }

    function show(i) {
      index = i;
      const step = steps[i];
      if (step.view) {
        options.openView?.(step.view);
      }
      const first = nextIndex(steps, -1, 1, available);
      const last = steps.length - 1 - [...steps].reverse().findIndex(available);
      const shown = steps.filter(available);
      count.textContent = labels.count(shown.indexOf(step) + 1, shown.length);
      title.textContent = step.title;
      text.textContent = step.text;
      picture.hidden = !step.image;
      if (step.image) {
        picture.src = step.image;
        // The card's size changes once the picture is there: place it again.
        picture.onload = () => position(false);
      } else {
        picture.removeAttribute("src");
      }
      bubble.classList.toggle("tour-bubble-wide", Boolean(step.image));
      back.disabled = i === first;
      next.textContent = i === last ? labels.done : labels.next;
      win.cancelAnimationFrame(frame);
      frame = win.requestAnimationFrame(() => position(true));
      next.focus();
    }

    function close(completed) {
      win.removeEventListener("resize", onResize);
      doc.removeEventListener("scroll", onScroll, true);
      doc.removeEventListener("keydown", onKey, true);
      win.cancelAnimationFrame(frame);
      layer.remove();
      if (previousFocus && typeof previousFocus.focus === "function") {
        previousFocus.focus();
      }
      options.onClose?.(completed);
    }

    function go(direction) {
      const target = nextIndex(steps, index, direction, available);
      if (target < 0) {
        close(true);
      } else if (target !== index) {
        show(target);
      }
    }

    function onResize() {
      win.cancelAnimationFrame(frame);
      frame = win.requestAnimationFrame(() => position(true));
    }

    // Any scrolling container (the page or a view inside it): follow the element.
    function onScroll() {
      win.cancelAnimationFrame(frame);
      frame = win.requestAnimationFrame(() => position(false));
    }

    function onKey(event) {
      if (event.key === "Escape") {
        event.preventDefault();
        close(false);
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        go(1);
      } else if (event.key === "ArrowLeft") {
        event.preventDefault();
        go(-1);
      } else if (event.key === "Tab") {
        // Keep the focus on the card's buttons.
        const buttons = [skip, back, next].filter((b) => !b.disabled);
        const at = buttons.indexOf(doc.activeElement);
        event.preventDefault();
        buttons[(at + (event.shiftKey ? buttons.length - 1 : 1)) % buttons.length].focus();
      }
    }

    skip.addEventListener("click", () => close(false));
    back.addEventListener("click", () => go(-1));
    next.addEventListener("click", () => go(1));
    win.addEventListener("resize", onResize);
    doc.addEventListener("scroll", onScroll, { capture: true, passive: true });
    doc.addEventListener("keydown", onKey, true);
    const first = nextIndex(steps, -1, 1, available);
    if (first < 0) {
      close(true);
    } else {
      show(first);
    }
    return { close: () => close(false) };
  }

  function button(doc, className, label) {
    const element = doc.createElement("button");
    element.type = "button";
    element.className = className;
    element.textContent = label;
    return element;
  }

  return { placeBubble, spotlight, onScreen, nextIndex, start };
});
