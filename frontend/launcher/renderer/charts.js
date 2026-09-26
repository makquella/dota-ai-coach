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

  function legend(host, items) {
    if (items.length < 2) {
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
      el("polyline", { points: points.map((p) => p.join(",")).join(" "), class: "chart-line", stroke: s.color }, svg);
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
    const pad = { top: 16, right: 12, bottom: 26, left: 32 };
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
        el("path", { d, fill: options.color, class: "chart-bar" }, group);
      }
      // Hit target: the whole band, taller than the bar.
      el("rect", { x: cx - band / 2, y: pad.top, width: band, height: innerH, fill: "transparent" }, group);
      if (item.key) {
        el("circle", { cx, cy: height - 12, r: 3, class: `chart-flag chart-flag-${item.key}` }, group);
      }
      const show = () => {
        const box = svg.getBoundingClientRect();
        showTip(host, tip, (cx / width) * box.width, (top / height) * box.height, item.title || item.label, [
          { label: options.valueLabel || "", value: item.value === null || item.value === undefined ? "—" : formatNumber(item.value), color: options.color, kind: "bar" },
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

  window.LauncherCharts = { line, columns, meter, formatNumber };
})();
