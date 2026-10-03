// The developer's statistics page (GET /admin): where players come from (visits
// and downloads per source, src/channels.js), which advice the app shows and
// which urgent warnings come right before a death, from the opt-in anonymous
// statistics (src/stats.js). The page holds no data: it asks for the admin
// token (kept in sessionStorage only) and reads /v1/admin/stats?days=N with it.
// Served with a strict CSP: its only script is /admin/app.js from this Worker.

export const ADMIN_HEADERS = {
  "content-type": "text/html; charset=utf-8",
  "cache-control": "no-store",
  "x-content-type-options": "nosniff",
  "x-robots-tag": "noindex, nofollow",
  "referrer-policy": "no-referrer",
  "content-security-policy":
    "default-src 'none'; script-src 'self'; style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
};

export const ADMIN_SCRIPT_HEADERS = {
  "content-type": "text/javascript; charset=utf-8",
  "cache-control": "no-store",
  "x-content-type-options": "nosniff"
};

export const ADMIN_HTML = `<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Wardly — статистика подсказок</title>
<style>
  :root { --bg: #0b0c0e; --card: #15171b; --line: #262a31; --text: #eceef2; --muted: #9aa0aa; --accent: #f05560; --ok: #4cc38a; --warn: #e5b454; }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--text); font: 14px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
  main { max-width: 1100px; margin: 0 auto; padding: 28px 16px 60px; }
  h1 { font-size: 22px; margin: 0 0 4px; }
  h2 { font-size: 15px; margin: 0 0 12px; }
  .muted { color: var(--muted); }
  .bar-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin: 16px 0 20px; }
  input, select, button { font: inherit; color: var(--text); background: var(--card); border: 1px solid var(--line); border-radius: 8px; padding: 6px 10px; }
  button { background: var(--accent); border-color: var(--accent); color: #fff; cursor: pointer; }
  button.ghost { background: transparent; border-color: var(--line); color: var(--text); }
  button:focus-visible, input:focus-visible, select:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 16px; }
  .tile, .card { background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px; }
  .tile b { display: block; font-size: 24px; font-variant-numeric: tabular-nums; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 12px; }
  .card { margin-bottom: 12px; overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
  th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--line); }
  th { color: var(--muted); font-weight: 500; }
  td.n, th.n { text-align: right; }
  .hot { color: var(--warn); font-weight: 600; }
  .bars { display: grid; gap: 6px; }
  .bars div { display: grid; grid-template-columns: 110px 1fr 44px; gap: 8px; align-items: center; }
  .bars i { display: block; height: 8px; border-radius: 4px; background: var(--accent); min-width: 2px; }
  .days { display: flex; align-items: flex-end; gap: 3px; height: 120px; }
  .days span { flex: 1; background: var(--accent); border-radius: 3px 3px 0 0; min-height: 2px; }
  .hidden { display: none; }
  .error { color: var(--accent); }
  code { font-size: 12px; color: var(--text); }
</style>
</head>
<body>
<main>
  <h1>Статистика подсказок</h1>
  <p class="muted">Анонимная статистика по согласию игроков: сколько раз показана подсказка каждого типа и после каких срочных предупреждений в течение 30 секунд была смерть.</p>
  <form class="bar-row" id="login">
    <label for="token" class="muted">Ключ администратора</label>
    <input id="token" type="password" autocomplete="off" size="28" required>
    <label for="days" class="muted">за</label>
    <select id="days"><option value="7">7 дней</option><option value="30" selected>30 дней</option><option value="90">90 дней</option></select>
    <button type="submit">Показать</button>
    <button type="button" class="ghost hidden" id="logout">Выйти</button>
    <span id="status" class="muted" aria-live="polite"></span>
  </form>
  <section id="view" class="hidden">
    <div class="tiles" id="tiles"></div>
    <div class="card"><h2>Откуда приходят</h2><table id="channels"></table><p class="muted">Источник — <code>?ref=</code> в ссылке на сайт (luhovyimvp.dev/?ref=pikabu). Без него: search — поисковики, direct — без перехода, other — другие сайты; site — скачивание по кнопке на сайте, когда источник неизвестен.</p></div>
    <div class="card"><h2>По дням</h2><div class="days" id="days-chart" role="img" aria-label="Устройства по дням"></div><p class="muted" id="days-note"></p></div>
    <div class="card"><h2>Подсказки: показано и смерть в течение 30 с после срочной</h2><table id="advice"></table></div>
    <div class="grid" id="dists"></div>
  </section>
</main>
<script src="/admin/app.js"></script>
</body>
</html>
`;

// Runs in the browser only (served as /admin/app.js); kept as a function so the
// Worker never evaluates it and no template escaping is needed. The deploy
// bundles it (wrangler/esbuild keep names), which adds calls to a `__name`
// helper inside the function's text — ADMIN_JS defines it first, or the page's
// script dies on its first line and the form does nothing.
function adminApp() {
  const $ = (id) => document.getElementById(id);
  const KEY = "wardly-admin-token";
  const LABELS = {
    versions: "Версии",
    langs: "Язык",
    ai: "ИИ-тренер",
    sync_errors: "Ошибки синхронизации",
    voice: "Голос",
    frequency: "Частота советов",
    role: "Роль",
    overlay: "Оверлей",
    map_hints: "Таймеры карты",
    discord: "Статус в Discord"
  };

  function el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs || {})) {
      if (key === "text") node.textContent = value;
      else if (key === "style") node.setAttribute("style", value);
      else node.setAttribute(key, value);
    }
    for (const child of children) if (child) node.append(child);
    return node;
  }

  function token() {
    try {
      return sessionStorage.getItem(KEY) || "";
    } catch {
      return "";
    }
  }

  function remember(value) {
    try {
      if (value) sessionStorage.setItem(KEY, value);
      else sessionStorage.removeItem(KEY);
    } catch {
      // Private mode: the token is asked again.
    }
  }

  function tile(label, value) {
    return el("div", { class: "tile" }, el("span", { class: "muted", text: label }), el("b", { text: String(value) }));
  }

  function bars(title, counts) {
    const entries = Object.entries(counts || {}).sort((a, b) => b[1] - a[1]);
    const max = Math.max(1, ...entries.map(([, n]) => n));
    const card = el("div", { class: "card" }, el("h2", { text: title }));
    if (!entries.length) {
      card.append(el("p", { class: "muted", text: "Пока нет данных" }));
      return card;
    }
    const list = el("div", { class: "bars" });
    for (const [key, n] of entries.slice(0, 12)) {
      list.append(
        el("div", {}, el("span", { text: key === "true" ? "вкл" : key === "false" ? "выкл" : key }), el("i", { style: `width:${Math.round((100 * n) / max)}%` }), el("span", { class: "muted", text: String(n) }))
      );
    }
    card.append(list);
    return card;
  }

  function render(stats, days) {
    $("tiles").replaceChildren(
      tile("Устройств", stats.devices),
      tile("Отправок (дней)", stats.rows),
      tile("Разобрано матчей", stats.matches),
      tile("С подсказками в игре", stats.with_advice),
      tile("Полноэкранный режим", stats.fullscreen)
    );
    const perDay = stats.by_day || [];
    const maxDay = Math.max(1, ...perDay.map((d) => d.devices));
    $("days-chart").replaceChildren(
      ...perDay.map((d) => el("span", { title: `${d.day}: ${d.devices} устр., ${d.matches} матчей, ${d.advice} подсказок`, style: `height:${Math.round((100 * d.devices) / maxDay)}%` }))
    );
    $("days-note").textContent = perDay.length ? `${perDay[0].day} — ${perDay[perDay.length - 1].day}, за ${days} дн.` : "Пока нет данных";

    const channels = stats.channels || [];
    $("channels").replaceChildren(
      el("thead", {}, el("tr", {}, el("th", { text: "Источник" }), el("th", { class: "n", text: "Заходы" }), el("th", { class: "n", text: "Скачивания" }), el("th", { class: "n", text: "Конверсия" }))),
      el(
        "tbody",
        {},
        ...(channels.length
          ? channels.map((c) =>
              el(
                "tr",
                {},
                el("td", { text: c.src }),
                el("td", { class: "n", text: String(c.visits) }),
                el("td", { class: "n", text: String(c.downloads) }),
                el("td", { class: "n", text: c.rate != null ? `${c.rate}%` : "—" })
              )
            )
          : [el("tr", {}, el("td", { class: "muted", text: "Пока нет данных" }))])
      )
    );

    const rows = Object.entries(stats.advice || {}).sort((a, b) => b[1] - a[1]);
    const table = $("advice");
    table.replaceChildren(
      el("thead", {}, el("tr", {}, el("th", { text: "Тип подсказки" }), el("th", { class: "n", text: "Показано" }), el("th", { class: "n", text: "Смерть после" }), el("th", { class: "n", text: "Доля" })))
    );
    const body = el("tbody");
    for (const [kind, shown] of rows) {
      const ignored = (stats.ignored || {})[kind] || 0;
      const share = (stats.ignored_share || {})[kind];
      body.append(
        el(
          "tr",
          {},
          el("td", { text: kind }),
          el("td", { class: "n", text: String(shown) }),
          el("td", { class: "n", text: ignored ? String(ignored) : "—" }),
          el("td", { class: share != null && share >= 30 ? "n hot" : "n", text: share != null ? `${share}%` : "—" })
        )
      );
    }
    if (!rows.length) body.append(el("tr", {}, el("td", { class: "muted", text: "Пока нет данных" })));
    table.append(body);

    const dists = [bars(LABELS.versions, stats.versions), bars(LABELS.langs, stats.langs), bars(LABELS.ai, stats.ai)];
    for (const [key, counts] of Object.entries(stats.settings || {})) dists.push(bars(LABELS[key] || key, counts));
    dists.push(bars(LABELS.sync_errors, stats.sync_errors));
    $("dists").replaceChildren(...dists);
    $("view").classList.remove("hidden");
  }

  async function load() {
    const secret = token();
    const days = $("days").value;
    if (!secret) return;
    $("status").textContent = "Загрузка…";
    $("status").className = "muted";
    try {
      const response = await fetch(`/v1/admin/stats?days=${encodeURIComponent(days)}`, {
        headers: { authorization: `Bearer ${secret}` },
        cache: "no-store"
      });
      if (response.status === 404) {
        remember("");
        $("status").textContent = "Ключ не подошёл. Если вы меняли секрет API_ADMIN_TOKEN, перезапустите выкладку: GitHub → Actions → API → Run workflow.";
        $("status").className = "error";
        $("view").classList.add("hidden");
        $("logout").classList.add("hidden");
        return;
      }
      const answer = await response.json();
      render(answer.stats, answer.days);
      $("status").textContent = "";
      $("logout").classList.remove("hidden");
    } catch (error) {
      $("status").textContent = `Не удалось загрузить: ${error.message}`;
      $("status").className = "error";
    }
  }

  $("login").addEventListener("submit", (event) => {
    event.preventDefault();
    const value = $("token").value.trim();
    if (value) remember(value);
    $("token").value = "";
    load();
  });
  $("days").addEventListener("change", load);
  $("logout").addEventListener("click", () => {
    remember("");
    $("view").classList.add("hidden");
    $("logout").classList.add("hidden");
  });
  load();
}

export const ADMIN_JS = `var __name = (target) => target;\n(${adminApp.toString()})();\n`;
