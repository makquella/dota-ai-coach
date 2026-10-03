// Small dependency-free SVG charts for the control panel (match review and
// progress views). Follows the dataviz rules used across the app: one axis,
// 2px lines with a 10% area wash, <=24px columns with 4px rounded tops,
// hairline recessive grid, text in text tokens (never the series colour), a
// legend for 2+ series, and a hover/focus layer (crosshair + one tooltip for
// lines, per-mark tooltip for columns). Every value shown on hover is also in
// the tables around the chart. Labels are inserted with textContent only.
(function () {
  const SVG_NS = "http://www.w3.org/2000/svg";
  const PAD = { top: 12, right: 44, bottom: 26, left: 40 };

  function el(name, attrs = {}, parent) {
    const node = document.createElementNS(SVG_NS, name);
    for (const [key, value] of Object.entries(attrs)) {
      node.setAttribute(key, String(value));
    }
    if (parent) {
      parent.appendChild(node);
    }
    return node;
  }

  function niceMax(value) {
    if (!(value > 0)) {
      return 10;
    }
    const exponent = Math.pow(10, Math.floor(Math.log10(value)));
    for (const step of [1, 2, 2.5, 5, 10]) {
      if (step * exponent >= value) {
        return step * exponent;
      }
    }
    return 10 * exponent;
  }

  function formatNumber(value) {
    if (value === null || value === undefined || Number.isNaN(value)) {
      return "—";
    }
    const abs = Math.abs(value);
    if (abs >= 10000) {
      return `${(value / 1000).toFixed(abs >= 100000 ? 0 : 1).replace(/\.0$/, "")}k`;
    }
    return Math.round(value).toLocaleString("en-US");
  }

  function tooltip(host) {
    let tip = host.querySelector(".chart-tip");
    if (!tip) {
      tip = document.createElement("div");
      tip.className = "chart-tip hidden";
      tip.setAttribute("role", "status");
      host.appendChild(tip);
    }
    return tip;
  }

  function showTip(host, tip, x, y, title, rows) {
    tip.replaceChildren();
    const head = document.createElement("div");
    head.className = "chart-tip-title";
    head.textContent = title;
    tip.appendChild(head);
    for (const row of rows) {
      const line = document.createElement("div");
      line.className = "chart-tip-row";
      const key = document.createElement("span");
      key.className = `chart-key chart-key-${row.kind || "line"}`;
      if (row.color) {
        key.style.setProperty("--key", row.color);
      }
      const value = document.createElement("strong");
      value.textContent = row.value;
      const label = document.createElement("span");
      label.textContent = row.label;
      line.append(key, value, label);
      tip.appendChild(line);
    }
    tip.classList.remove("hidden");
    const hostWidth = host.clientWidth;
    const tipWidth = tip.offsetWidth;
    const left = Math.min(Math.max(0, x + 12), Math.max(0, hostWidth - tipWidth));
    tip.style.left = `${x + 12 + tipWidth > hostWidth ? Math.max(0, x - tipWidth - 12) : left}px`;
    tip.style.top = `${Math.max(0, y - 8)}px`;
  }

  // A legend for 2+ series; the map names even a single layer (minItems 1).
  function legend(host, items, minItems = 2) {
    if (items.length < minItems) {
      return;
    }
    const list = document.createElement("ul");
    list.className = "chart-legend";
    for (const item of items) {
      const entry = document.createElement("li");
      const key = document.createElement("span");
      key.className = `chart-key chart-key-${item.kind || "line"}`;
      if (item.color) {
        key.style.setProperty("--key", item.color);
      }
      const label = document.createElement("span");
      label.textContent = item.label;
      entry.append(key, label);
      list.appendChild(entry);
    }
    host.appendChild(list);
  }

  /**
   * Line chart over x = 0..n-1.
   * options: { series: [{ label, values, color, area }], reference: { label, values },
   *            markers: [{ x, label }], markerLabel, xLabel(i), yLabel, height, ariaLabel }
   */
  function line(host, options) {
    host.replaceChildren();
    host.classList.add("chart");
    const series = (options.series || []).filter((s) => Array.isArray(s.values) && s.values.length);
    if (!series.length) {
      return;
    }
    const reference = options.reference && Array.isArray(options.reference.values) ? options.reference : null;
    const count = Math.max(...series.map((s) => s.values.length));
    const width = Math.max(280, host.clientWidth || 560);
    const height = options.height || 200;
    const innerW = width - PAD.left - PAD.right;
    const innerH = height - PAD.top - PAD.bottom;
    const all = series.flatMap((s) => s.values).concat(reference ? reference.values.slice(0, count) : []);
    // 3-5 gridline steps, each a round number (0 / 50 / 100 / 150 / 200 / 250).
    const dataMax = Math.max(...all.filter((v) => typeof v === "number"));
    const yStep = niceMax(dataMax / 5);
    const ySteps = Math.max(3, Math.ceil(dataMax / yStep));
    const yMax = yStep * ySteps;
    const x = (i) => PAD.left + (count <= 1 ? 0 : (i / (count - 1)) * innerW);
    const y = (v) => PAD.top + innerH - (v / yMax) * innerH;

    const svg = el("svg", {
      viewBox: `0 0 ${width} ${height}`,
      width,
      height,
      role: "img",
      "aria-label": options.ariaLabel || ""
    });
    // Grid + y ticks.
    for (let step = 0; step <= ySteps; step += 1) {
      const value = yStep * step;
      const yy = y(value);
      el("line", { x1: PAD.left, x2: width - PAD.right, y1: yy, y2: yy, class: step === 0 ? "chart-axis" : "chart-grid" }, svg);
      const label = el("text", { x: PAD.left - 8, y: yy + 4, class: "chart-tick", "text-anchor": "end" }, svg);
      label.textContent = formatNumber(value);
    }
    // X ticks: about 6 labels.
    const every = Math.max(1, Math.ceil(count / 6 / 5) * 5);
    for (let i = 0; i < count; i += every) {
      const label = el("text", { x: x(i), y: height - 8, class: "chart-tick", "text-anchor": "middle" }, svg);
      label.textContent = options.xLabel ? options.xLabel(i) : String(i);
    }
    if (reference) {
      const points = reference.values.slice(0, count).map((v, i) => `${x(i)},${y(v)}`).join(" ");
      el("polyline", { points, class: "chart-reference" }, svg);
    }
    for (const s of series) {
      const points = s.values.map((v, i) => [x(i), y(v || 0)]);
      if (s.area) {
        const d = `M${points[0][0]},${y(0)} L${points.map((p) => p.join(",")).join(" L")} L${points[points.length - 1][0]},${y(0)} Z`;
        el("path", { d, fill: s.color, "fill-opacity": 0.1, stroke: "none" }, svg);
      }
      el("polyline", { points: points.map((p) => p.join(",")).join(" "), class: "chart-line", stroke: s.color, ...(s.dashed ? { "stroke-dasharray": "5 4" } : {}) }, svg);
      const last = points[points.length - 1];
      el("circle", { cx: last[0], cy: last[1], r: 4, fill: s.color, class: "chart-dot" }, svg);
      const endLabel = el("text", { x: last[0] + 8, y: last[1] + 4, class: "chart-end" }, svg);
      endLabel.textContent = formatNumber(s.values[s.values.length - 1]);
    }
    // Event markers (e.g. deaths) on the baseline.
    for (const marker of options.markers || []) {
      if (marker.x < 0 || marker.x > count - 1) {
        continue;
      }
      el("path", { d: `M${x(marker.x)},${y(0) - 7} l4,6 l-8,0 z`, class: "chart-marker" }, svg);
    }
    const cross = el("line", { x1: 0, x2: 0, y1: PAD.top, y2: PAD.top + innerH, class: "chart-cross hidden" }, svg);
    host.appendChild(svg);

    const legendItems = series.map((s) => ({ label: s.label, color: s.color }));
    if (reference) {
      legendItems.push({ label: reference.label, kind: "reference" });
    }
    if ((options.markers || []).length && options.markerLabel) {
      legendItems.push({ label: options.markerLabel, kind: "marker" });
    }
    legend(host, legendItems);

    const tip = tooltip(host);
    const hit = el("rect", { x: PAD.left, y: PAD.top, width: innerW, height: innerH, fill: "transparent", tabindex: 0 }, svg);
    const pick = (clientX) => {
      const box = svg.getBoundingClientRect();
      const scale = width / box.width;
      const px = (clientX - box.left) * scale;
      return Math.max(0, Math.min(count - 1, Math.round(((px - PAD.left) / innerW) * (count - 1))));
    };
    const show = (i) => {
      cross.setAttribute("x1", x(i));
      cross.setAttribute("x2", x(i));
      cross.classList.remove("hidden");
      const rows = series.map((s) => ({ label: s.label, value: formatNumber(s.values[i]), color: s.color }));
      if (reference && reference.values[i] !== undefined) {
        rows.push({ label: reference.label, value: formatNumber(reference.values[i]), kind: "reference" });
      }
      const events = (options.markers || []).filter((m) => Math.floor(m.x) === i);
      for (const event of events) {
        rows.push({ label: event.label, value: "", kind: "marker" });
      }
      const box = svg.getBoundingClientRect();
      showTip(host, tip, (x(i) / width) * box.width, PAD.top, options.xLabel ? options.xLabel(i) : String(i), rows);
    };
    const hide = () => {
      marker.classList.add("hidden");
      cross.classList.add("hidden");
      tip.classList.add("hidden");
    };
    let focusIndex = count - 1;
    hit.addEventListener("pointermove", (event) => show(pick(event.clientX)));
    hit.addEventListener("pointerleave", hide);
    hit.addEventListener("focus", () => show(focusIndex));
    hit.addEventListener("blur", hide);
    hit.addEventListener("keydown", (event) => {
      if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
        focusIndex = Math.max(0, Math.min(count - 1, focusIndex + (event.key === "ArrowLeft" ? -1 : 1)));
        show(focusIndex);
        event.preventDefault();
      }
    });
  }

  /**
   * Column chart, one series, fixed 0..yMax.
   * options: { items: [{ label, value, title, detail, key }], yMax, color, height, onSelect(item), ariaLabel }
   */
  function columns(host, options) {
    host.replaceChildren();
    host.classList.add("chart");
    const items = options.items || [];
    if (!items.length) {
      return;
    }
    const width = Math.max(280, host.clientWidth || 560);
    const height = options.height || 180;
    const pad = { top: options.valueLabels ? 20 : 16, right: 12, bottom: options.xLabels ? 20 : 26, left: 32 };
    const innerW = width - pad.left - pad.right;
    const innerH = height - pad.top - pad.bottom;
    const yMax = options.yMax || niceMax(Math.max(...items.map((i) => i.value || 0)));
    const band = innerW / items.length;
    const barW = Math.min(24, Math.max(6, band - 4));
    const y = (v) => pad.top + innerH - (Math.max(0, v) / yMax) * innerH;

    const svg = el("svg", { viewBox: `0 0 ${width} ${height}`, width, height, role: "img", "aria-label": options.ariaLabel || "" });
    for (let step = 0; step <= 4; step += 1) {
      const value = (yMax / 4) * step;
      el("line", { x1: pad.left, x2: width - pad.right, y1: y(value), y2: y(value), class: step === 0 ? "chart-axis" : "chart-grid" }, svg);
      const label = el("text", { x: pad.left - 8, y: y(value) + 4, class: "chart-tick", "text-anchor": "end" }, svg);
      label.textContent = formatNumber(value);
    }
    const tip = tooltip(host);
    items.forEach((item, index) => {
      const cx = pad.left + band * index + band / 2;
      const top = y(item.value || 0);
      const h = Math.max(0, y(0) - top);
      const r = Math.min(4, h / 2, barW / 2);
      const group = el("g", { class: "chart-col", tabindex: 0, role: "button", "aria-label": `${item.title || item.label}: ${item.value ?? "—"}` }, svg);
      if (item.value !== null && item.value !== undefined) {
        const left = cx - barW / 2;
        const d = `M${left},${y(0)} L${left},${top + r} Q${left},${top} ${left + r},${top} L${left + barW - r},${top} Q${left + barW},${top} ${left + barW},${top + r} L${left + barW},${y(0)} Z`;
        // A muted column is context; the highlighted ones carry the series colour.
        el("path", { d, fill: item.muted ? options.mutedColor || "var(--viz-muted)" : options.color, class: "chart-bar" }, group);
        if (options.valueLabels) {
          const value = el("text", { x: cx, y: top - 6, class: item.muted ? "chart-value" : "chart-value is-strong", "text-anchor": "middle" }, group);
          value.textContent = `${formatNumber(item.value)}${options.valueSuffix || ""}`;
        }
      }
      // Hit target: the whole band, taller than the bar.
      el("rect", { x: cx - band / 2, y: pad.top, width: band, height: innerH, fill: "transparent" }, group);
      if (item.key) {
        el("circle", { cx, cy: height - 12, r: 3, class: `chart-flag chart-flag-${item.key}` }, group);
      }
      if (options.xLabels && item.label) {
        const tick = el("text", { x: cx, y: height - 6, class: "chart-tick", "text-anchor": "middle" }, group);
        tick.textContent = item.label;
      }
      const show = () => {
        const box = svg.getBoundingClientRect();
        showTip(host, tip, (cx / width) * box.width, (top / height) * box.height, item.title || item.label, [
          { label: options.valueLabel || "", value: item.value === null || item.value === undefined ? "—" : `${formatNumber(item.value)}${options.valueSuffix || ""}`, color: options.color, kind: "bar" },
          ...(item.detail ? [{ label: item.detail, value: "", kind: "none" }] : [])
        ]);
        group.classList.add("is-active");
      };
      const hide = () => {
        tip.classList.add("hidden");
        group.classList.remove("is-active");
      };
      group.addEventListener("pointerenter", show);
      group.addEventListener("pointerleave", hide);
      group.addEventListener("focus", show);
      group.addEventListener("blur", hide);
      if (options.onSelect) {
        group.addEventListener("click", () => options.onSelect(item));
        group.addEventListener("keydown", (event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            options.onSelect(item);
          }
        });
      }
    });
    host.appendChild(svg);
  }

  /** Horizontal 0..100 meter; the fill carries severity (good/ok/bad) unless `tone` is given. */
  function meter(value, tone) {
    const track = document.createElement("span");
    track.className = "meter";
    const fill = document.createElement("span");
    const clamped = Math.max(0, Math.min(100, Number(value) || 0));
    const severity = tone || (clamped >= 70 ? "good" : clamped >= 50 ? "ok" : "bad");
    fill.className = `meter-fill meter-${severity}`;
    fill.style.width = `${clamped}%`;
    track.appendChild(fill);
    return track;
  }

  // Game map pictures: "ok" once loaded, "fail" when it could not be (offline on
  // the first run): the schematic map is drawn instead.
  const mapImages = new Map();
  // Map units per second no hero walks faster than (max move speed 550 plus a blink).
  const MAP_WALK_SPEED = 800;

  /**
   * The Dota map with the match on top: the hero's path, laning position, wards
   * and deaths. Radiant is bottom-left, Dire top-right. With `background`
   * ({ href, bounds }) the game's minimap art is the ground once it has loaded
   * (the map redraws itself then); until then, or without it, a schematic map
   * of lanes, river and bases.
   * options: { bounds: [min, max], background, path, lane, wards, deaths, labels, clock(t), ariaLabel }
   */
  function map(host, options) {
    host.replaceChildren();
    host.classList.add("chart", "map-chart");
    const background = options.background && options.background.href ? options.background : null;
    const imageState = background ? mapImages.get(background.href) : null;
    if (background && imageState === undefined) {
      mapImages.set(background.href, "loading");
      const probe = new Image();
      probe.onload = () => {
        mapImages.set(background.href, "ok");
        if (host.isConnected) {
          map(host, options);
        }
      };
      probe.onerror = () => mapImages.set(background.href, "fail");
      probe.src = background.href;
    }
    const real = imageState === "ok";
    host.classList.toggle("map-real", real);
    const [min, max] = real ? background.bounds : options.bounds || [7000, 25800];
    const size = Math.max(240, Math.min(420, host.clientWidth || 360));
    const px = (x) => ((x - min) / (max - min)) * size;
    const py = (y) => size - ((y - min) / (max - min)) * size;
    const f = (value) => (value * size).toFixed(1);
    const labels = options.labels || {};
    const svg = el("svg", { viewBox: `0 0 ${size} ${size}`, width: size, height: size, role: "img", "aria-label": options.ariaLabel || "" });

    if (real) {
      const clip = el("clipPath", { id: `map-clip-${size}` }, el("defs", {}, svg));
      el("rect", { x: 0, y: 0, width: size, height: size, rx: 8 }, clip);
      el("image", { href: background.href, x: 0, y: 0, width: size, height: size, preserveAspectRatio: "none", "clip-path": `url(#map-clip-${size})`, class: "map-image" }, svg);
      for (const [x, y, text, anchor, baseline] of [
        [0.03, 0.97, labels.radiant, "start", "auto"],
        [0.97, 0.03, labels.dire, "end", "hanging"]
      ]) {
        if (text) {
          const label = el("text", { x: f(x), y: f(y), class: "map-label", "text-anchor": anchor, "dominant-baseline": baseline }, svg);
          label.textContent = text;
        }
      }
    }
    // Schematic terrain: lanes at x/y ≈ 0.16 and 0.84 of the map, mid on the
    // diagonal, the river across it, bases around the fountains.
    if (!real) {
      el("rect", { x: 0, y: 0, width: size, height: size, rx: 8, class: "map-ground" }, svg);
      el("path", { d: `M${f(0.03)},${f(0.03)} L${f(0.97)},${f(0.97)}`, class: "map-river", "stroke-width": f(0.06) }, svg);
      const lane = { class: "map-lane", "stroke-width": f(0.012) };
      el("path", { d: `M${f(0.16)},${f(0.8)} L${f(0.16)},${f(0.2)} Q${f(0.16)},${f(0.16)} ${f(0.2)},${f(0.16)} L${f(0.8)},${f(0.16)}`, ...lane }, svg);
      el("path", { d: `M${f(0.2)},${f(0.84)} L${f(0.8)},${f(0.84)} Q${f(0.84)},${f(0.84)} ${f(0.84)},${f(0.8)} L${f(0.84)},${f(0.2)}`, ...lane }, svg);
      el("path", { d: `M${f(0.2)},${f(0.8)} L${f(0.8)},${f(0.2)}`, ...lane }, svg);
      for (const [cx, cy, text, anchor] of [
        [0.13, 0.87, labels.radiant, "start"],
        [0.87, 0.13, labels.dire, "end"]
      ]) {
        el("rect", { x: f(cx - 0.07), y: f(cy - 0.07), width: f(0.14), height: f(0.14), rx: 6, class: "map-base" }, svg);
        if (text) {
          // Beside the base, along the map edge: Radiant under its base, Dire above.
          const label = el("text", { x: f(anchor === "start" ? 0.22 : 0.78), y: f(cy > 0.5 ? 0.975 : 0.025), class: "chart-tick", "text-anchor": anchor, "dominant-baseline": cy > 0.5 ? "auto" : "hanging" }, svg);
          label.textContent = text;
        }
      }
    }

    const tip = tooltip(host);
    const marks = [];
    const addMark = (group, x, y, title, rows) => {
      group.setAttribute("tabindex", "0");
      const show = () => {
        const box = svg.getBoundingClientRect();
        showTip(host, tip, (x / size) * box.width, (y / size) * box.height, title, rows);
        group.classList.add("is-active");
      };
      const hide = () => {
        tip.classList.add("hidden");
        group.classList.remove("is-active");
      };
      group.addEventListener("pointerenter", show);
      group.addEventListener("pointerleave", hide);
      group.addEventListener("focus", show);
      group.addEventListener("blur", hide);
      marks.push(group);
    };
    const legendItems = [];

    const lanePoints = options.lane || [];
    if (lanePoints.length) {
      const most = Math.max(...lanePoints.map((point) => point[2]));
      const layer = el("g", { class: "map-heat" }, svg);
      for (const [x, y, n] of lanePoints) {
        el("circle", { cx: px(x), cy: py(y), r: (2 + 5 * Math.sqrt(n / most)).toFixed(1) }, layer);
      }
      legendItems.push({ label: labels.lane || "", color: "var(--viz-1)", kind: "dot" });
    }

    const path = options.path || [];
    if (path.length > 1) {
      // A new segment after a death (respawn in the fountain), a gap of more than a
      // minute (disconnect) or a jump no hero can walk (teleport).
      const deathTimes = (options.deaths || []).map((death) => death.t).filter((t) => typeof t === "number");
      const moved = (a, b) => Math.hypot(b.x - a.x, b.y - a.y) > MAP_WALK_SPEED * Math.max(1, b.t - a.t);
      let d = "";
      path.forEach((point, index) => {
        const prev = path[index - 1];
        const jump =
          index === 0 ||
          point.t - prev.t > 60 ||
          deathTimes.some((t) => t > prev.t && t <= point.t) ||
          moved(prev, point);
        d += `${jump ? "M" : "L"}${px(point.x).toFixed(1)},${py(point.y).toFixed(1)} `;
      });
      el("path", { d: d.trim(), class: "map-path" }, svg);
      legendItems.push({ label: labels.path || "", color: "var(--viz-1)", kind: "line" });
    }

    const wards = options.wards || [];
    for (const ward of wards) {
      const x = px(ward.x);
      const y = py(ward.y);
      const group = el("g", { class: `map-ward map-ward-${ward.kind}` }, svg);
      el("circle", { cx: x, cy: y, r: 4 }, group);
      el("circle", { cx: x, cy: y, r: 9, fill: "transparent", class: "map-hit" }, group);
      const kind = ward.kind === "sen" ? labels.sentry : labels.observer;
      addMark(group, x, y, `${kind || ""} · ${options.clock ? options.clock(ward.t) : ward.t}`, []);
    }
    if (wards.some((ward) => ward.kind === "obs")) {
      legendItems.push({ label: labels.observer || "", color: "var(--viz-2)", kind: "dot" });
    }
    if (wards.some((ward) => ward.kind === "sen")) {
      legendItems.push({ label: labels.sentry || "", color: "var(--viz-2)", kind: "ring" });
    }

    // Places where the deaths repeat: a dashed ring with the count.
    const spots = options.spots || [];
    for (const spot of spots) {
      const x = px(spot.x);
      const y = py(spot.y);
      const r = Math.min(34, 12 + 4 * spot.count) * (size / 360);
      const group = el("g", { class: "map-spot" }, svg);
      el("circle", { cx: x, cy: y, r: r.toFixed(1) }, group);
      const count = el("text", { x: (x + r * 0.72).toFixed(1), y: (y - r * 0.72).toFixed(1), class: "map-spot-count", "text-anchor": "middle", "dominant-baseline": "central" }, group);
      count.textContent = String(spot.count);
      addMark(group, x, y, spot.title || "", spot.detail ? [{ label: spot.detail, value: "", kind: "none" }] : []);
    }
    if (spots.length) {
      legendItems.push({ label: labels.spot || "", color: "var(--error)", kind: "ring" });
    }

    const deaths = options.deaths || [];
    for (const death of deaths) {
      const x = px(death.x);
      const y = py(death.y);
      const group = el("g", { class: "map-death" }, svg);
      el("path", { d: `M${x - 4},${y - 4} L${x + 4},${y + 4} M${x + 4},${y - 4} L${x - 4},${y + 4}` }, group);
      el("circle", { cx: x, cy: y, r: 9, fill: "transparent", class: "map-hit" }, group);
      const rows = death.killer ? [{ label: death.killer, value: "", kind: "none" }] : [];
      addMark(group, x, y, `${labels.death || ""} · ${options.clock ? options.clock(death.t) : death.t}`, rows);
    }
    if (deaths.length) {
      legendItems.push({ label: labels.death || "", color: "var(--error)", kind: "cross" });
    }

    host.appendChild(svg);
    legend(host, legendItems, 1);
    return marks.length;
  }

  /**
   * Rating over matches (the profile's FACEIT-like graph): the y axis hugs the
   * values (not from 0), one dot per match — a win in --ok, a loss in --error,
   * an anchor (the player's own number) hollow — and one tooltip.
   * options: { points: [{ mmr, win, anchor, title, detail }], height, ariaLabel }
   */
  const SMOOTH_WINDOW = 5;

  /** A centred moving average; the first and the last value stay exact. */
  function smoothed(values) {
    const half = Math.floor(SMOOTH_WINDOW / 2);
    return values.map((value, i) => {
      if (i === 0 || i === values.length - 1) {
        return value;
      }
      const from = Math.max(0, i - half);
      const to = Math.min(values.length - 1, i + half);
      let sum = 0;
      for (let k = from; k <= to; k += 1) {
        sum += values[k];
      }
      return sum / (to - from + 1);
    });
  }

  /** A monotone cubic (Fritsch–Carlson) path through the points: smooth,
   * and it never overshoots between two of them. */
  function smoothPath(pts) {
    const n = pts.length;
    if (n < 3) {
      return `M${pts.map((p) => p.join(",")).join(" L")}`;
    }
    const dx = [];
    const slope = [];
    for (let i = 0; i < n - 1; i += 1) {
      dx.push(pts[i + 1][0] - pts[i][0]);
      slope.push((pts[i + 1][1] - pts[i][1]) / (dx[i] || 1));
    }
    const tangent = [slope[0]];
    for (let i = 1; i < n - 1; i += 1) {
      tangent.push(slope[i - 1] * slope[i] <= 0 ? 0 : (slope[i - 1] + slope[i]) / 2);
    }
    tangent.push(slope[n - 2]);
    for (let i = 0; i < n - 1; i += 1) {
      if (slope[i] === 0) {
        tangent[i] = 0;
        tangent[i + 1] = 0;
        continue;
      }
      const a = tangent[i] / slope[i];
      const b = tangent[i + 1] / slope[i];
      const h = a * a + b * b;
      if (h > 9) {
        const t = 3 / Math.sqrt(h);
        tangent[i] = t * a * slope[i];
        tangent[i + 1] = t * b * slope[i];
      }
    }
    let d = `M${pts[0][0]},${pts[0][1]}`;
    for (let i = 0; i < n - 1; i += 1) {
      const third = dx[i] / 3;
      d += ` C${pts[i][0] + third},${pts[i][1] + tangent[i] * third} ${pts[i + 1][0] - third},${pts[i + 1][1] - tangent[i + 1] * third} ${pts[i + 1][0]},${pts[i + 1][1]}`;
    }
    return d;
  }

  function rating(host, options) {
    host.replaceChildren();
    host.classList.add("chart");
    const points = (options.points || []).filter((p) => typeof p.mmr === "number");
    if (!points.length) {
      return;
    }
    const width = Math.max(280, host.clientWidth || 560);
    const height = options.height || 220;
    const pad = { top: 16, right: 56, bottom: 16, left: 48 };
    const innerW = width - pad.left - pad.right;
    const innerH = height - pad.top - pad.bottom;
    const values = points.map((p) => p.mmr);
    const step = niceMax(Math.max(25, (Math.max(...values) - Math.min(...values)) / 4));
    const low = Math.floor(Math.min(...values) / step) * step;
    const high = Math.max(low + step, Math.ceil(Math.max(...values) / step) * step);
    const count = points.length;
    const x = (i) => pad.left + (count <= 1 ? innerW / 2 : (i / (count - 1)) * innerW);
    const y = (v) => pad.top + innerH - ((v - low) / (high - low)) * innerH;
    const svg = el("svg", { viewBox: `0 0 ${width} ${height}`, width, height, role: "img", "aria-label": options.ariaLabel || "" });
    for (let value = low; value <= high; value += step) {
      el("line", { x1: pad.left, x2: width - pad.right, y1: y(value), y2: y(value), class: "chart-grid" }, svg);
      const label = el("text", { x: pad.left - 8, y: y(value) + 4, class: "chart-tick", "text-anchor": "end" }, svg);
      label.textContent = formatNumber(value);
    }
    // Every game moves the rating by ±25, so the raw line is a saw: the curve
    // shows the trend (a moving average over SMOOTH_WINDOW games, the first and
    // the last point kept exact) drawn as a smooth monotone curve. The real
    // value of each game stays in the tooltip.
    const coords = points.map((p, i) => [x(i), y(p.mmr)]);
    const trend = smoothed(values).map((v, i) => [x(i), y(v)]);
    const curve = smoothPath(trend);
    el("path", { d: `${curve} L${trend[count - 1][0]},${y(low)} L${trend[0][0]},${y(low)} Z`, class: "rating-area" }, svg);
    el("path", { d: curve, class: "chart-line rating-line" }, svg);
    points.forEach((p, i) => {
      if (!p.anchor) {
        return;
      }
      el("circle", { cx: trend[i][0], cy: trend[i][1], r: 3.5, class: "rating-dot rating-dot-anchor" }, svg);
    });
    const lastPoint = points[count - 1];
    el("circle", {
      cx: coords[count - 1][0],
      cy: coords[count - 1][1],
      r: 4,
      class: `rating-dot ${lastPoint.win ? "rating-dot-win" : "rating-dot-loss"}`
    }, svg);
    const marker = el("circle", { cx: 0, cy: 0, r: 4, class: "rating-dot rating-dot-anchor hidden" }, svg);
    const last = coords[count - 1];
    const end = el("text", { x: last[0] + 8, y: last[1] + 4, class: "chart-end" }, svg);
    end.textContent = formatNumber(points[count - 1].mmr);
    const cross = el("line", { x1: 0, x2: 0, y1: pad.top, y2: pad.top + innerH, class: "chart-cross hidden" }, svg);
    host.appendChild(svg);

    const tip = tooltip(host);
    const hit = el("rect", { x: pad.left, y: pad.top, width: innerW, height: innerH, fill: "transparent", tabindex: 0 }, svg);
    const pick = (clientX) => {
      const box = svg.getBoundingClientRect();
      const px = (clientX - box.left) * (width / box.width);
      return Math.max(0, Math.min(count - 1, Math.round(((px - pad.left) / innerW) * (count - 1))));
    };
    const show = (i) => {
      marker.setAttribute("cx", trend[i][0]);
      marker.setAttribute("cy", trend[i][1]);
      marker.classList.remove("hidden");
      cross.setAttribute("x1", coords[i][0]);
      cross.setAttribute("x2", coords[i][0]);
      cross.classList.remove("hidden");
      const p = points[i];
      const rows = [{ label: p.detail || "", value: formatNumber(p.mmr), color: "var(--accent)" }];
      const box = svg.getBoundingClientRect();
      showTip(host, tip, (coords[i][0] / width) * box.width, pad.top, p.title || "", rows);
    };
    const hide = () => {
      cross.classList.add("hidden");
      tip.classList.add("hidden");
    };
    let focusIndex = count - 1;
    hit.addEventListener("pointermove", (event) => show(pick(event.clientX)));
    hit.addEventListener("pointerleave", hide);
    hit.addEventListener("focus", () => show(focusIndex));
    hit.addEventListener("blur", hide);
    hit.addEventListener("keydown", (event) => {
      if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
        focusIndex = Math.max(0, Math.min(count - 1, focusIndex + (event.key === "ArrowLeft" ? -1 : 1)));
        show(focusIndex);
        event.preventDefault();
      }
    });
  }

  window.LauncherCharts = { line, columns, meter, map, rating, formatNumber };
})();
