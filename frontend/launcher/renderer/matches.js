// Matches, match review and Progress views of the control panel.
//
// Data comes from the backend through the main process
// (window.launcherApi.player(op, args), see PLAYER_OPS in main.js):
//   status, link, linkDetected, unlink, sync, matches, match, refreshMatch, career.
// Review texts (titles, explanations, drills) are already localized by the
// backend; this file only holds the UI labels (ru/en). Everything is built
// with DOM nodes and textContent — backend strings are never parsed as HTML.
(function () {
  const TEXT = {
    en: {
      linkTitle: "Link your Steam account",
      linkHint:
        "The coach reads your account from Dota automatically when you play. You can also paste your Friend ID (Dota profile), a steamcommunity.com/profiles/… link or an OpenDota/Dotabuff link.",
      linkPlaceholder: "Friend ID, Steam ID or profile link",
      linkButton: "Link",
      linkErrors: {
        empty: "Enter a Friend ID, Steam ID or profile link.",
        vanity_url: "Custom links (steamcommunity.com/id/…) can't be resolved. Use your Friend ID from the Dota profile.",
        unrecognized: "This doesn't look like a Steam account.",
        out_of_range: "This number is not a valid Steam account.",
        backend_down: "The coach service is not running.",
        request_failed: "Could not link the account."
      },
      detected: (name) => `Playing now: ${name}.`,
      detectedLink: "Link this account",
      detectedOther: (name) => `Dota is running on another account: ${name}.`,
      switchAccount: "Switch",
      friendId: (id) => `Friend ID ${id}`,
      sourceLabel: { gsi: "detected in Dota", manual: "linked by hand", opendota: "OpenDota" },
      change: "Change",
      refresh: "Refresh",
      syncing: "Updating history…",
      syncedAt: (when) => `History updated ${when}`,
      syncNever: "History not loaded yet",
      syncOffline: "OpenDota is off — only matches recorded by the app are shown.",
      syncError: {
        offline: "No internet — showing matches recorded by the app.",
        private: "Match data is private. In Dota: Settings → Social → Expose Public Match Data.",
        rate_limited: "OpenDota is busy, try again in a minute.",
        not_found: "OpenDota doesn't know this account yet.",
        bad_response: "OpenDota answered with an error."
      },
      matchesTitle: "Matches",
      colResult: "Result",
      colHero: "Hero",
      colKda: "K / D / A",
      colGpm: "GPM",
      colLh10: "LH@10",
      colDuration: "Time",
      colScore: "Score",
      colWhen: "Played",
      win: "Win",
      loss: "Loss",
      unknownResult: "—",
      noMatchesTitle: "No matches yet",
      noMatchesHint: "Play a match with the coach running, or press Refresh to load your history from OpenDota.",
      more: "Show more",
      liveMatch: (hero) => `Recording the current match${hero ? ` (${hero})` : ""} — the review appears right after it ends.`,
      back: "Matches",
      reviewLoading: "Loading the match…",
      reviewPending: "The review appears once the match data is loaded.",
      scoreOf: "of 100",
      sourcesParsed: "Full replay parsed by OpenDota",
      sourcesBasic: "OpenDota totals — replay not parsed yet",
      sourcesGsi: "Recorded by the app during the match",
      parseStatus: {
        waiting_opendota: "Full replay review in a few minutes (OpenDota).",
        parsing: "OpenDota is parsing the replay — the review will update by itself.",
        basic: "Replay not parsed: no minute-by-minute data.",
        not_parsed: "OpenDota could not parse the replay.",
        gsi_only: "Only the app's own recording is available (OpenDota is off).",
        private: "This match is private on OpenDota.",
        "error:not_found": "OpenDota doesn't have this match yet — try again in a few minutes.",
        "error:offline": "No internet — showing the app's own recording.",
        "error:rate_limited": "OpenDota is busy — try again in a minute.",
        "error:bad_response": "OpenDota answered with an error."
      },
      requestParse: "Request replay parse",
      parseRequested: "Requested — it usually takes 2–10 minutes.",
      focusTitle: "Focus for the next game",
      sectionsTitle: "Breakdown",
      chartTitle: "Over the match",
      chartLh: "Last hits",
      chartGold: "Gold earned",
      chartXp: "Experience",
      you: "You",
      target: "Target pace",
      deathsMarker: "Death",
      minuteLabel: (m) => `${m}:00`,
      strengthsTitle: "What went well",
      improveTitle: "What to improve",
      nothingToImprove: "No serious mistakes found in this match.",
      nothingStrong: "Nothing stood out this time.",
      drill: "Drill",
      momentsTitle: "Key moments",
      momentDeath: (killer) => (killer ? `Died to ${killer}` : "Died"),
      momentGold: (gold) => `${gold} gold on hand`,
      momentItem: (item) => item,
      momentBuyback: "Buyback",
      momentStall: (to) => `Farm stall until ${to}`,
      scoreboardTitle: "Scoreboard",
      radiant: "Radiant",
      dire: "Dire",
      colPlayer: "Player",
      colNw: "Net worth",
      colDmg: "Damage",
      stats: {
        kda: "K / D / A",
        gpm: "GPM / XPM",
        lh: "LH / DN",
        nw: "Net worth",
        dmg: "Hero damage",
        duration: "Duration"
      },
      sectionFacts: {
        laning: (s) => [s.lh10 != null && `${s.lh10} LH by 10:00`, s.lane_efficiency != null && `lane efficiency ${Math.round(s.lane_efficiency)}%`, s.lane_deaths ? `${s.lane_deaths} deaths in lane` : null],
        farm: (s) => [s.gpm != null && `${s.gpm} GPM`, s.gpm_pct != null && `better than ${Math.round(s.gpm_pct * 100)}%`],
        survival: (s) => [`${s.deaths} deaths`, s.deaths_per_10 != null && `${s.deaths_per_10} per 10 min`],
        fights: (s) => [s.kill_participation != null && `${s.kill_participation}% kill participation`],
        items: (s) => [s.first_item && `${s.first_item.item} at ${clock(s.first_item.t)}`],
        vision: (s) => [s.obs_placed != null && `${s.obs_placed} observers`, s.sen_placed != null && `${s.sen_placed} sentries`]
      },
      progressEmptyTitle: "Not enough matches yet",
      progressEmptyHint: "Statistics appear after a few reviewed matches. Refresh your history on the Matches tab.",
      tiles: { winrate: "Win rate", kda: "KDA", gpm: "GPM", lh10: "LH at 10:00", score: "Avg. score" },
      vsPrevious: (n) => `vs previous ${n}`,
      streakWin: (n) => `${n} wins in a row`,
      streakLoss: (n) => `${n} losses in a row`,
      recordLine: (w, l, n) => `${w}W – ${l}L over ${n} matches`,
      scoreChartTitle: "Score by match",
      scoreChartHint: "Last 20 matches, oldest on the left. Click a column to open the review.",
      scoreLabel: "Score",
      winKey: "win",
      lossKey: "loss",
      planTitle: "What to work on",
      planHint: "Problems that keep coming back in your recent matches, with one drill each.",
      planEmpty: "No repeated problems found — keep it up.",
      strengthsRecurring: "Your strengths",
      heroesTitle: "Heroes",
      colMatches: "Matches",
      colWinrate: "Win rate",
      analyzed: (a, n) => `${a} of ${n} matches reviewed in depth`
    },
    ru: {
      linkTitle: "Привяжите аккаунт Steam",
      linkHint:
        "Тренер сам узнаёт ваш аккаунт из Доты, когда вы играете. Можно и вручную: Friend ID из профиля в Доте, ссылка steamcommunity.com/profiles/… или ссылка на OpenDota/Dotabuff.",
      linkPlaceholder: "Friend ID, Steam ID или ссылка на профиль",
      linkButton: "Привязать",
      linkErrors: {
        empty: "Введите Friend ID, Steam ID или ссылку на профиль.",
        vanity_url: "Короткие ссылки (steamcommunity.com/id/…) не распознать. Возьмите Friend ID из профиля в Доте.",
        unrecognized: "Это не похоже на аккаунт Steam.",
        out_of_range: "Такого аккаунта Steam не бывает.",
        backend_down: "Сервис тренера не запущен.",
        request_failed: "Не удалось привязать аккаунт."
      },
      detected: (name) => `Сейчас в Доте: ${name}.`,
      detectedLink: "Привязать этот аккаунт",
      detectedOther: (name) => `В Доте другой аккаунт: ${name}.`,
      switchAccount: "Переключиться",
      friendId: (id) => `Friend ID ${id}`,
      sourceLabel: { gsi: "найден в Доте", manual: "привязан вручную", opendota: "OpenDota" },
      change: "Сменить",
      refresh: "Обновить",
      syncing: "Обновляем историю…",
      syncedAt: (when) => `История обновлена ${when}`,
      syncNever: "История ещё не загружена",
      syncOffline: "OpenDota выключен — видны только матчи, записанные приложением.",
      syncError: {
        offline: "Нет интернета — показываем матчи, записанные приложением.",
        private: "Данные матчей скрыты. В Доте: Настройки → Социальное → «Открыть публичную статистику матчей».",
        rate_limited: "OpenDota перегружен, попробуйте через минуту.",
        not_found: "OpenDota пока не знает этот аккаунт.",
        bad_response: "OpenDota ответил ошибкой."
      },
      matchesTitle: "Матчи",
      colResult: "Итог",
      colHero: "Герой",
      colKda: "У / С / П",
      colGpm: "GPM",
      colLh10: "Добив. к 10",
      colDuration: "Время",
      colScore: "Оценка",
      colWhen: "Когда",
      win: "Победа",
      loss: "Поражение",
      unknownResult: "—",
      noMatchesTitle: "Матчей пока нет",
      noMatchesHint: "Сыграйте матч с запущенным тренером или нажмите «Обновить», чтобы загрузить историю из OpenDota.",
      more: "Показать ещё",
      liveMatch: (hero) => `Записываем текущий матч${hero ? ` (${hero})` : ""} — разбор появится сразу после него.`,
      back: "Матчи",
      reviewLoading: "Загружаем матч…",
      reviewPending: "Разбор появится, когда загрузятся данные матча.",
      scoreOf: "из 100",
      sourcesParsed: "Полный разбор реплея (OpenDota)",
      sourcesBasic: "Итоги из OpenDota — реплей ещё не разобран",
      sourcesGsi: "Записано приложением во время матча",
      parseStatus: {
        waiting_opendota: "Полный разбор реплея будет через несколько минут (OpenDota).",
        parsing: "OpenDota разбирает реплей — разбор обновится сам.",
        basic: "Реплей не разобран: нет данных по минутам.",
        not_parsed: "OpenDota не смог разобрать реплей.",
        gsi_only: "Есть только запись приложения (OpenDota выключен).",
        private: "Матч скрыт в OpenDota.",
        "error:not_found": "OpenDota пока не знает этот матч — попробуйте через несколько минут.",
        "error:offline": "Нет интернета — показываем запись приложения.",
        "error:rate_limited": "OpenDota перегружен — попробуйте через минуту.",
        "error:bad_response": "OpenDota ответил ошибкой."
      },
      requestParse: "Запросить разбор реплея",
      parseRequested: "Запрос отправлен — обычно это 2–10 минут.",
      focusTitle: "Главное на следующую игру",
      sectionsTitle: "По разделам",
      chartTitle: "По ходу матча",
      chartLh: "Добивания",
      chartGold: "Золото",
      chartXp: "Опыт",
      you: "Вы",
      target: "Хороший темп",
      deathsMarker: "Смерть",
      minuteLabel: (m) => `${m}:00`,
      strengthsTitle: "Что получилось",
      improveTitle: "Что улучшить",
      nothingToImprove: "Серьёзных ошибок в этом матче не найдено.",
      nothingStrong: "В этот раз ничего не выделилось.",
      drill: "Упражнение",
      momentsTitle: "Ключевые моменты",
      momentDeath: (killer) => (killer ? `Смерть от ${killer}` : "Смерть"),
      momentGold: (gold) => `${gold} золота на руках`,
      momentItem: (item) => item,
      momentBuyback: "Байбэк",
      momentStall: (to) => `Провал в фарме до ${to}`,
      scoreboardTitle: "Итоги матча",
      radiant: "Силы Света",
      dire: "Силы Тьмы",
      colPlayer: "Игрок",
      colNw: "Ценность",
      colDmg: "Урон",
      stats: {
        kda: "У / С / П",
        gpm: "GPM / XPM",
        lh: "Добив. / денаи",
        nw: "Ценность",
        dmg: "Урон по героям",
        duration: "Длительность"
      },
      sectionFacts: {
        laning: (s) => [s.lh10 != null && `${s.lh10} добиваний к 10:00`, s.lane_efficiency != null && `эффективность ${Math.round(s.lane_efficiency)}%`, s.lane_deaths ? `смертей на линии: ${s.lane_deaths}` : null],
        farm: (s) => [s.gpm != null && `${s.gpm} GPM`, s.gpm_pct != null && `лучше ${Math.round(s.gpm_pct * 100)}% игроков`],
        survival: (s) => [`смертей: ${s.deaths}`, s.deaths_per_10 != null && `${s.deaths_per_10} за 10 мин`],
        fights: (s) => [s.kill_participation != null && `участие в убийствах ${s.kill_participation}%`],
        items: (s) => [s.first_item && `${s.first_item.item} к ${clock(s.first_item.t)}`],
        vision: (s) => [s.obs_placed != null && `обсерверов: ${s.obs_placed}`, s.sen_placed != null && `сентри: ${s.sen_placed}`]
      },
      progressEmptyTitle: "Пока мало матчей",
      progressEmptyHint: "Статистика появится после нескольких разобранных матчей. Обновите историю на вкладке «Матчи».",
      tiles: { winrate: "Винрейт", kda: "KDA", gpm: "GPM", lh10: "Добивания к 10:00", score: "Средняя оценка" },
      vsPrevious: (n) => `к прошлым ${n}`,
      streakWin: (n) => `${n} ${plural(n, "победа", "победы", "побед")} подряд`,
      streakLoss: (n) => `${n} ${plural(n, "поражение", "поражения", "поражений")} подряд`,
      recordLine: (w, l, n) => `${w} ${plural(w, "победа", "победы", "побед")} и ${l} ${plural(l, "поражение", "поражения", "поражений")} за ${n} ${plural(n, "матч", "матча", "матчей")}`,
      scoreChartTitle: "Оценка по матчам",
      scoreChartHint: "Последние 20 матчей, старые слева. Нажмите на столбец, чтобы открыть разбор.",
      scoreLabel: "Оценка",
      winKey: "победа",
      lossKey: "поражение",
      planTitle: "Над чем работать",
      planHint: "Ошибки, которые повторяются в последних матчах, и по одному упражнению на каждую.",
      planEmpty: "Повторяющихся ошибок не найдено — так держать.",
      strengthsRecurring: "Ваши сильные стороны",
      heroesTitle: "Герои",
      colMatches: "Матчи",
      colWinrate: "Винрейт",
      analyzed: (a, n) => `Подробно разобрано ${a} из ${n} матчей`
    }
  };

  // Chart colours come from the design tokens (assets/ui/tokens.css).
  const cssVar = (name, fallback) =>
    getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
  const VIZ_1 = cssVar("--viz-1", "#3987e5");
  const TAB_KEY = "dota-ai-coach.tab";
  const api = window.launcherApi;

  const state = {
    locale: "en",
    view: "home",
    status: null,
    player: null,
    matches: [],
    matchesTotal: 0,
    matchesLoaded: false,
    matchId: null,
    match: null,
    chartMetric: "lh",
    career: null,
    linkError: "",
    lastPlayerRefresh: 0
  };

  function plural(n, one, few, many) {
    n = Math.abs(Number(n) || 0);
    if (n % 10 === 1 && n % 100 !== 11) {
      return one;
    }
    if (n % 10 >= 2 && n % 10 <= 4 && !(n % 100 >= 12 && n % 100 <= 14)) {
      return few;
    }
    return many;
  }

  function t(key, ...args) {
    const table = TEXT[state.locale] || TEXT.en;
    const value = key.split(".").reduce((node, part) => (node ? node[part] : undefined), table) ??
      key.split(".").reduce((node, part) => (node ? node[part] : undefined), TEXT.en);
    return typeof value === "function" ? value(...args) : value ?? key;
  }

  // Like t() but empty for unknown keys (backend status codes).
  function tOptional(key) {
    const table = TEXT[state.locale] || TEXT.en;
    const value = key.split(".").reduce((node, part) => (node ? node[part] : undefined), table);
    return typeof value === "string" ? value : "";
  }

  function clock(seconds) {
    const value = Number(seconds);
    if (!Number.isFinite(value)) {
      return "—";
    }
    const sign = value < 0 ? "-" : "";
    const abs = Math.abs(Math.round(value));
    return `${sign}${Math.floor(abs / 60)}:${String(abs % 60).padStart(2, "0")}`;
  }

  function relativeTime(unixSeconds) {
    if (!unixSeconds) {
      return "—";
    }
    const diff = Math.round(unixSeconds - Date.now() / 1000);
    const rtf = new Intl.RelativeTimeFormat(state.locale, { numeric: "auto" });
    const abs = Math.abs(diff);
    if (abs < 3600) {
      return rtf.format(Math.round(diff / 60), "minute");
    }
    if (abs < 86400) {
      return rtf.format(Math.round(diff / 3600), "hour");
    }
    if (abs < 86400 * 30) {
      return rtf.format(Math.round(diff / 86400), "day");
    }
    return new Date(unixSeconds * 1000).toLocaleDateString(state.locale);
  }

  function relativeIso(iso) {
    const ms = Date.parse(iso || "");
    return Number.isFinite(ms) ? relativeTime(ms / 1000) : "—";
  }

  function number(value) {
    return value === null || value === undefined ? "—" : Math.round(value).toLocaleString(state.locale);
  }

  function h(tag, attrs = {}, ...children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs || {})) {
      if (value === null || value === undefined || value === false) {
        continue;
      }
      if (key === "class") {
        node.className = value;
      } else if (key === "text") {
        node.textContent = value;
      } else if (key.startsWith("on")) {
        node.addEventListener(key.slice(2), value);
      } else if (key === "dataset") {
        Object.assign(node.dataset, value);
      } else {
        node.setAttribute(key, value === true ? "" : String(value));
      }
    }
    for (const child of children.flat()) {
      if (child === null || child === undefined || child === false) {
        continue;
      }
      node.append(child instanceof Node ? child : document.createTextNode(String(child)));
    }
    return node;
  }

  function icon(name) {
    return h("i", { "data-icon": name, "aria-hidden": "true" });
  }

  function hydrate(root) {
    window.LucideIcons?.hydrate(root);
  }

  function card(title, iconName, body, extraHead) {
    return h(
      "section",
      { class: "card" },
      h("header", { class: "card-head" }, icon(iconName), h("h2", { text: title }), extraHead ? h("span", { class: "card-head-extra" }, extraHead) : null),
      h("div", { class: "card-body" }, body)
    );
  }

  function emptyState(iconName, title, hint, action) {
    return h("div", { class: "empty" }, icon(iconName), h("p", { class: "empty-title", text: title }), h("p", { class: "empty-hint", text: hint }), action || null);
  }

  function skeletonRows(count) {
    return h(
      "div",
      { class: "skeleton-stack" },
      Array.from({ length: count }, () => h("span", { class: "skeleton skeleton-line" }))
    );
  }

  function resultBadge(win) {
    const tone = win === true ? "good" : win === false ? "bad" : "idle";
    return h("span", { class: "result" }, h("span", { class: "dot", "data-tone": tone }), h("span", { text: win === true ? t("win") : win === false ? t("loss") : t("unknownResult") }));
  }

  function gradeBadge(score) {
    if (score === null || score === undefined) {
      return h("span", { class: "grade grade-none", text: "—" });
    }
    const letter = score >= 80 ? "A" : score >= 65 ? "B" : score >= 50 ? "C" : "D";
    const tone = score >= 65 ? "good" : score >= 50 ? "warn" : "bad";
    return h("span", { class: "grade" }, h("span", { class: "dot", "data-tone": tone }), h("span", { class: "num", text: `${letter} · ${score}` }));
  }

  function gradeLetter(score) {
    const letter = score >= 80 ? "A" : score >= 65 ? "B" : score >= 50 ? "C" : "D";
    const tone = score >= 65 ? "good" : score >= 50 ? "warn" : "bad";
    return h("span", { class: "grade" }, h("span", { class: "dot", "data-tone": tone }), h("span", { text: letter }));
  }

  // --- navigation -------------------------------------------------------------

  function setView(view, { remember = true } = {}) {
    state.view = view;
    const tabView = view === "match" ? "matches" : view;
    for (const tab of document.querySelectorAll(".tabs [data-view]")) {
      tab.setAttribute("aria-selected", String(tab.dataset.view === tabView));
    }
    for (const name of ["home", "matches", "match", "progress"]) {
      document.getElementById(`view-${name}`)?.classList.toggle("hidden", name !== view);
    }
    if (remember && view !== "match") {
      try {
        localStorage.setItem(TAB_KEY, view);
      } catch {
        // Per-viewer convenience only.
      }
    }
    if (view === "matches") {
      loadMatches();
    } else if (view === "progress") {
      loadCareer();
    }
    window.scrollTo({ top: 0 });
  }

  async function call(op, args) {
    try {
      return await api.player(op, args);
    } catch (error) {
      return { ok: false, code: "request_failed", detail: error.message };
    }
  }

  async function refreshPlayer() {
    const result = await call("status");
    if (result.ok) {
      state.player = result.data;
      state.lastPlayerRefresh = Date.now();
    }
    return result;
  }

  // --- account ----------------------------------------------------------------

  function linkPanel() {
    const input = h("input", { class: "input input-lg", type: "text", placeholder: t("linkPlaceholder"), "aria-label": t("linkPlaceholder"), autocomplete: "off", spellcheck: "false" });
    const error = h("p", { class: "form-error", role: "alert", text: state.linkError });
    const button = h("button", { class: "btn btn-primary", type: "submit" }, icon("link"), h("span", { text: t("linkButton") }));
    const form = h(
      "form",
      {
        class: "link-form",
        onsubmit: async (event) => {
          event.preventDefault();
          button.disabled = true;
          const result = await call("link", { steam: input.value });
          button.disabled = false;
          if (result.ok) {
            state.linkError = "";
            state.player = result.data;
            state.matchesLoaded = false;
            await afterLink();
          } else {
            state.linkError = tOptional(`linkErrors.${result.code}`) || result.detail || "";
            error.textContent = state.linkError;
          }
        }
      },
      input,
      button
    );
    const detected = state.player && state.player.detected;
    return h(
      "section",
      { class: "card link-card" },
      h(
        "div",
        { class: "card-body" },
        h("div", { class: "link-head" }, h("span", { class: "link-icon" }, icon("user")), h("div", {}, h("h2", { class: "link-title", text: t("linkTitle") }), h("p", { class: "link-hint", text: t("linkHint") }))),
        detected
          ? h(
              "div",
              { class: "detected" },
              h("span", { text: t("detected", detected.persona_name || detected.account_id) }),
              h("button", { class: "btn btn-primary btn-sm", type: "button", onclick: linkDetected }, h("span", { text: t("detectedLink") }))
            )
          : null,
        form,
        error
      )
    );
  }

  async function linkDetected() {
    const result = await call("linkDetected");
    if (result.ok) {
      state.player = result.data;
      state.matchesLoaded = false;
      await afterLink();
    }
  }

  async function afterLink() {
    await loadMatches(true);
    if (state.view === "progress") {
      loadCareer();
    }
  }

  function playerBar() {
    const player = state.player || {};
    const info = player.player || {};
    const name = info.persona_name || t("friendId", player.account_id);
    const avatar = info.avatar_url
      ? h("img", { class: "avatar", src: info.avatar_url, alt: "", referrerpolicy: "no-referrer", onerror: (e) => e.target.replaceWith(avatarFallback(name)) })
      : avatarFallback(name);
    const sync = player.sync || {};
    let syncText = t("syncNever");
    let syncTone = "idle";
    if (!player.opendota) {
      syncText = t("syncOffline");
    } else if (sync.state === "running" || sync.state === "queued") {
      syncText = t("syncing");
      syncTone = "warn";
    } else if (sync.state === "error") {
      syncText = tOptional(`syncError.${sync.error_code}`) || sync.error || "";
      syncTone = "bad";
    } else if (sync.at) {
      syncText = t("syncedAt", relativeIso(sync.at));
      syncTone = "good";
    }
    const refreshButton = h(
      "button",
      {
        class: "btn btn-sm",
        type: "button",
        disabled: !player.opendota || sync.state === "running" || sync.state === "queued",
        onclick: async () => {
          await call("sync");
          await refreshPlayer();
          renderMatches();
          pollSync();
        }
      },
      icon("refresh-cw"),
      h("span", { text: t("refresh") })
    );
    const change = h(
      "button",
      {
        class: "btn btn-sm btn-ghost",
        type: "button",
        onclick: async () => {
          const result = await call("unlink");
          if (result.ok) {
            state.player = result.data;
            state.matches = [];
            state.matchesLoaded = false;
            renderMatches();
          }
        }
      },
      h("span", { text: t("change") })
    );
    const detected = player.detected;
    return h(
      "div",
      { class: "player-bar-wrap" },
      h(
        "section",
        { class: "player-bar" },
        avatar,
        h(
          "div",
          { class: "player-info" },
          h("p", { class: "player-name", text: name }),
          h("p", { class: "player-meta" }, h("span", { class: "dot", "data-tone": syncTone }), h("span", { text: syncText }))
        ),
        h("div", { class: "player-actions" }, refreshButton, change)
      ),
      detected
        ? h(
            "div",
            { class: "notice" },
            icon("info"),
            h("span", { text: t("detectedOther", detected.persona_name || detected.account_id) }),
            h("button", { class: "btn btn-sm", type: "button", onclick: linkDetected }, h("span", { text: t("switchAccount") }))
          )
        : null
    );
  }

  function avatarFallback(name) {
    return h("span", { class: "avatar avatar-fallback", "aria-hidden": "true", text: String(name || "?").trim().charAt(0).toUpperCase() || "?" });
  }

  let syncTimer = null;
  function pollSync() {
    clearTimeout(syncTimer);
    syncTimer = setTimeout(async () => {
      await refreshPlayer();
      const running = ["queued", "running"].includes(state.player?.sync?.state) || (state.player?.pending_jobs || 0) > 0;
      if (state.view === "matches") {
        await loadMatches(true);
      }
      if (running) {
        pollSync();
      }
    }, 2500);
  }

  // --- matches table ------------------------------------------------------------

  async function loadMatches(force = false) {
    const root = document.getElementById("matches-root");
    if (!state.player || force || Date.now() - state.lastPlayerRefresh > 5000) {
      if (!state.matchesLoaded) {
        root.replaceChildren(card(t("matchesTitle"), "history", skeletonRows(5)));
      }
      await refreshPlayer();
    }
    if (state.player?.linked) {
      const result = await call("matches", { limit: Math.max(30, state.matches.length) });
      if (result.ok) {
        state.matches = result.data.items || [];
        state.matchesTotal = result.data.total || 0;
        state.matchesLoaded = true;
      }
    }
    renderMatches();
    const syncing = ["queued", "running"].includes(state.player?.sync?.state) || (state.player?.pending_jobs || 0) > 0;
    if (syncing) {
      pollSync();
    }
  }

  function renderMatches() {
    const root = document.getElementById("matches-root");
    if (!state.player) {
      return;
    }
    if (!state.player.linked) {
      root.replaceChildren(linkPanel());
      hydrate(root);
      return;
    }
    const liveMatch = state.player.live_match;
    const liveNotice = liveMatch ? h("div", { class: "notice" }, h("span", { class: "dot dot-live", "data-tone": "good" }), h("span", { text: t("liveMatch", liveMatch.hero) })) : null;
    let body;
    if (!state.matchesLoaded) {
      body = skeletonRows(5);
    } else if (!state.matches.length) {
      body = emptyState("history", t("noMatchesTitle"), t("noMatchesHint"));
    } else {
      body = h("div", { class: "table-wrap" }, matchesTable(state.matches));
      if (state.matchesTotal > state.matches.length) {
        body = h(
          "div",
          {},
          body,
          h(
            "button",
            {
              class: "btn btn-ghost btn-block",
              type: "button",
              onclick: async () => {
                const result = await call("matches", { limit: 30, offset: state.matches.length });
                if (result.ok) {
                  state.matches = state.matches.concat(result.data.items || []);
                  renderMatches();
                }
              }
            },
            h("span", { text: t("more") })
          )
        );
      }
    }
    root.replaceChildren(playerBar(), liveNotice || "", card(t("matchesTitle"), "history", body, state.matchesTotal ? h("span", { class: "num", text: String(state.matchesTotal) }) : null));
    hydrate(root);
  }

  function matchesTable(rows) {
    const head = h(
      "thead",
      {},
      h(
        "tr",
        {},
        h("th", { text: t("colResult") }),
        h("th", { text: t("colHero") }),
        h("th", { class: "num-col", text: t("colKda") }),
        h("th", { class: "num-col", text: t("colGpm") }),
        h("th", { class: "num-col hide-narrow", text: t("colLh10") }),
        h("th", { class: "num-col", text: t("colDuration") }),
        h("th", { text: t("colScore") }),
        h("th", { class: "hide-narrow", text: t("colWhen") })
      )
    );
    const body = h("tbody", {});
    for (const row of rows) {
      const open = () => openMatch(row.match_id);
      body.append(
        h(
          "tr",
          {
            class: "row-link",
            tabindex: 0,
            role: "button",
            "aria-label": `${row.hero || ""} ${row.win === true ? t("win") : row.win === false ? t("loss") : ""}`,
            onclick: open,
            onkeydown: (event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                open();
              }
            }
          },
          h("td", {}, resultBadge(row.win)),
          h("td", { class: "hero-cell", text: row.hero || "—" }),
          h("td", { class: "num-col num", text: row.kills == null ? "—" : `${row.kills} / ${row.deaths} / ${row.assists}` }),
          h("td", { class: "num-col num", text: number(row.gpm) }),
          h("td", { class: "num-col num hide-narrow", text: number(row.lh_10) }),
          h("td", { class: "num-col num", text: clock(row.duration) }),
          h("td", {}, gradeBadge(row.score)),
          h("td", { class: "muted hide-narrow", text: relativeTime(row.start_time) })
        )
      );
    }
    return h("table", { class: "table" }, head, body);
  }

  // --- match review -------------------------------------------------------------

  async function openMatch(matchId) {
    state.matchId = String(matchId);
    state.match = null;
    setView("match", { remember: false });
    renderMatch();
    const result = await call("match", { matchId: state.matchId });
    if (String(matchId) !== state.matchId) {
      return;
    }
    state.match = result.ok ? result.data : { error: result.code };
    renderMatch();
    if (state.match && state.match.loading) {
      setTimeout(() => state.matchId === String(matchId) && state.view === "match" && openMatchQuietly(matchId), 3000);
    }
  }

  async function openMatchQuietly(matchId) {
    const result = await call("match", { matchId: String(matchId) });
    if (result.ok && state.matchId === String(matchId)) {
      state.match = result.data;
      renderMatch();
    }
  }

  function renderMatch() {
    const root = document.getElementById("match-root");
    const back = h("button", { class: "btn btn-ghost btn-sm back", type: "button", onclick: () => setView("matches") }, icon("chevron-left"), h("span", { text: t("back") }));
    const detail = state.match;
    if (!detail) {
      root.replaceChildren(back, card(t("reviewLoading"), "activity", skeletonRows(6)));
      hydrate(root);
      return;
    }
    if (detail.error) {
      root.replaceChildren(back, card(t("reviewLoading"), "circle-alert", emptyState("circle-alert", t("reviewPending"), detail.error)));
      hydrate(root);
      return;
    }
    const analysis = detail.analysis;
    const summary = detail.summary || {};
    const parts = [back, reviewHeader(detail, analysis, summary)];
    if (!analysis) {
      parts.push(card(t("reviewLoading"), "hourglass", emptyState("hourglass", t("reviewPending"), tOptional(`parseStatus.${detail.parse_status}`) || "")));
    } else {
      parts.push(focusCard(analysis));
      parts.push(sectionsCard(analysis));
      const chart = chartCard(analysis);
      if (chart) {
        parts.push(chart);
      }
      parts.push(findingsCard(t("strengthsTitle"), "sparkles", analysis.strengths, t("nothingStrong"), false));
      const rest = (analysis.improvements || []).filter((f) => !(analysis.focus || []).includes(f.id));
      if (rest.length) {
        parts.push(findingsCard(t("improveTitle"), "target", rest, "", true));
      }
      const moments = momentsCard(analysis);
      if (moments) {
        parts.push(moments);
      }
    }
    if (detail.scoreboard) {
      parts.push(scoreboardCard(detail.scoreboard));
    }
    root.replaceChildren(...parts);
    hydrate(root);
    // Charts measure their container, so draw after insertion.
    root.querySelectorAll("[data-chart]").forEach((host) => drawChart(host, analysis));
  }

  function reviewHeader(detail, analysis, summary) {
    const headline = (analysis && analysis.headline) || {};
    const win = headline.win ?? summary.win;
    const score = headline.score ?? summary.score;
    const sources = detail.sources || [];
    let sourceText = t("sourcesGsi");
    if (analysis && analysis.parsed) {
      sourceText = t("sourcesParsed");
    } else if (sources.includes("opendota")) {
      sourceText = t("sourcesBasic");
    }
    const statusText = detail.parse_status && detail.parse_status !== "parsed" ? tOptional(`parseStatus.${detail.parse_status}`) : "";
    const canRequest = !(analysis && analysis.parsed) && state.player?.opendota;
    const requestButton = canRequest
      ? h(
          "button",
          {
            class: "btn btn-sm",
            type: "button",
            onclick: async (event) => {
              event.currentTarget.disabled = true;
              await call("refreshMatch", { matchId: state.matchId });
              requestNote.textContent = t("parseRequested");
            }
          },
          icon("refresh-cw"),
          h("span", { text: t("requestParse") })
        )
      : null;
    const requestNote = h("span", { class: "muted" });
    const stats = [
      [t("stats.kda"), headline.kills == null ? "—" : `${headline.kills} / ${headline.deaths} / ${headline.assists}`],
      [t("stats.gpm"), `${number(headline.gpm)} / ${number(headline.xpm)}`],
      [t("stats.lh"), `${number(headline.last_hits)} / ${number(headline.denies)}`],
      [t("stats.duration"), clock(headline.duration ?? summary.duration)]
    ];
    if (headline.net_worth) {
      stats.push([t("stats.nw"), number(headline.net_worth)]);
    }
    if (headline.hero_damage) {
      stats.push([t("stats.dmg"), number(headline.hero_damage)]);
    }
    return h(
      "section",
      { class: "review-head card" },
      h(
        "div",
        { class: "card-body review-head-body" },
        h(
          "div",
          { class: "review-title" },
          h("h2", { class: "review-hero", text: headline.hero || summary.hero || "—" }),
          h("p", { class: "review-meta" }, resultBadge(win), h("span", { class: "muted", text: `· ${relativeTime(summary.start_time)} · #${detail.match_id}` })),
          h("p", { class: "review-source" }, icon(analysis && analysis.parsed ? "circle-check" : "info"), h("span", { text: sourceText })),
          statusText ? h("p", { class: "muted small", text: statusText }) : null,
          requestButton ? h("div", { class: "row" }, requestButton, requestNote) : null
        ),
        score !== null && score !== undefined
          ? h(
              "div",
              { class: "score-block" },
              h("span", { class: "score-value", text: String(score) }),
              h("span", { class: "score-of", text: t("scoreOf") }),
              gradeLetter(score)
            )
          : null
      ),
      h(
        "dl",
        { class: "review-stats" },
        stats.map(([label, value]) => h("div", {}, h("dt", { text: label }), h("dd", { class: "num", text: value })))
      )
    );
  }

  function findingItem(finding, index) {
    return h(
      "li",
      { class: `finding finding-${finding.kind}` },
      index !== undefined ? h("span", { class: "finding-index num", text: String(index + 1) }) : h("span", { class: "dot", "data-tone": finding.kind === "strength" ? "good" : finding.severity >= 3 ? "bad" : "warn" }),
      h(
        "div",
        { class: "finding-body" },
        h("p", { class: "finding-title" }, h("span", { text: finding.title }), finding.section_label ? h("span", { class: "tag", text: finding.section_label }) : null),
        h("p", { class: "finding-text", text: finding.text }),
        finding.drill ? h("p", { class: "finding-drill" }, icon("lightbulb"), h("span", {}, h("strong", { text: `${t("drill")}: ` }), finding.drill)) : null
      )
    );
  }

  function focusCard(analysis) {
    const focus = (analysis.improvements || []).filter((f) => (analysis.focus || []).includes(f.id));
    if (!focus.length) {
      return card(t("focusTitle"), "target", emptyState("circle-check", t("nothingToImprove"), ""));
    }
    return card(t("focusTitle"), "target", h("ol", { class: "findings" }, focus.map((f, i) => findingItem(f, i))));
  }

  function findingsCard(title, iconName, findings, emptyText, improve) {
    if (!findings || !findings.length) {
      return card(title, iconName, h("p", { class: "muted", text: emptyText }));
    }
    return card(title, iconName, h("ul", { class: `findings ${improve ? "" : "findings-compact"}` }, findings.map((f) => findingItem(f))));
  }

  function sectionsCard(analysis) {
    const order = ["laning", "farm", "survival", "fights", "items", "vision"];
    const rows = order
      .filter((name) => analysis.sections && analysis.sections[name])
      .map((name) => {
        const section = analysis.sections[name];
        const factsFn = (TEXT[state.locale] || TEXT.en).sectionFacts[name];
        const facts = factsFn ? factsFn(section).filter(Boolean).join(" · ") : "";
        return h(
          "div",
          { class: "section-row" },
          h("span", { class: "section-name", text: section.label || name }),
          window.LauncherCharts.meter(section.score),
          h("span", { class: "section-score num", text: String(section.score) }),
          h("span", { class: "section-facts", text: facts })
        );
      });
    return card(t("sectionsTitle"), "gauge", h("div", { class: "sections" }, rows));
  }

  function chartCard(analysis) {
    const series = analysis.series || {};
    const metrics = [
      ["lh", t("chartLh"), series.last_hits],
      ["gold", t("chartGold"), series.gold],
      ["xp", t("chartXp"), series.xp]
    ].filter(([, , values]) => Array.isArray(values) && values.length > 2);
    if (!metrics.length) {
      return null;
    }
    if (!metrics.some(([key]) => key === state.chartMetric)) {
      state.chartMetric = metrics[0][0];
    }
    const host = h("div", { class: "chart-host", dataset: { chart: "match" } });
    const toggle = h(
      "div",
      { class: "segmented segmented-sm", role: "radiogroup", "aria-label": t("chartTitle") },
      metrics.map(([key, label]) =>
        h("button", {
          type: "button",
          role: "radio",
          "aria-checked": String(key === state.chartMetric),
          text: label,
          onclick: (event) => {
            state.chartMetric = key;
            for (const button of event.currentTarget.parentElement.children) {
              button.setAttribute("aria-checked", String(button === event.currentTarget));
            }
            drawChart(host, analysis);
          }
        })
      )
    );
    return card(t("chartTitle"), "chart-line", host, toggle);
  }

  function drawChart(host, analysis) {
    const series = analysis.series || {};
    const values = { lh: series.last_hits, gold: series.gold, xp: series.xp }[state.chartMetric] || [];
    const label = { lh: t("chartLh"), gold: t("chartGold"), xp: t("chartXp") }[state.chartMetric];
    const markers = (series.deaths || []).map((seconds) => ({ x: seconds / 60, label: `${t("deathsMarker")} ${clock(seconds)}` }));
    window.LauncherCharts.line(host, {
      series: [{ label: `${t("you")} · ${label}`, values, color: VIZ_1, area: true }],
      reference: state.chartMetric === "lh" && series.last_hits_target ? { label: t("target"), values: series.last_hits_target } : null,
      markers,
      markerLabel: t("deathsMarker"),
      xLabel: (i) => t("minuteLabel", i),
      ariaLabel: label,
      height: 210
    });
  }

  function momentsCard(analysis) {
    const moments = analysis.moments || [];
    if (!moments.length) {
      return null;
    }
    const items = moments.slice(0, 16).map((moment) => {
      let iconName = "info";
      let text = "";
      let sub = "";
      if (moment.type === "death") {
        iconName = "skull";
        text = t("momentDeath", moment.killer);
        sub = moment.gold ? t("momentGold", number(moment.gold)) : "";
      } else if (moment.type === "item") {
        iconName = "coins";
        text = t("momentItem", moment.item);
      } else if (moment.type === "buyback") {
        iconName = "rotate-cw";
        text = t("momentBuyback");
      } else if (moment.type === "farm_stall") {
        iconName = "hourglass";
        text = t("momentStall", clock(moment.to));
      }
      return h(
        "li",
        { class: `moment moment-${moment.type}` },
        h("span", { class: "moment-time num", text: clock(moment.t) }),
        h("span", { class: "moment-icon" }, icon(iconName)),
        h("span", { class: "moment-text" }, h("span", { text }), sub ? h("span", { class: "muted", text: ` · ${sub}` }) : null)
      );
    });
    return card(t("momentsTitle"), "clock", h("ol", { class: "moments" }, items));
  }

  function scoreboardCard(rows) {
    const teams = [true, false].map((radiant) => {
      const players = rows.filter((row) => row.is_radiant === radiant);
      return h(
        "div",
        { class: "team" },
        h("p", { class: "team-name", text: radiant ? t("radiant") : t("dire") }),
        h(
          "table",
          { class: "table table-compact" },
          h(
            "thead",
            {},
            h("tr", {}, h("th", { text: t("colHero") }), h("th", { class: "num-col", text: t("colKda") }), h("th", { class: "num-col", text: t("colNw") }), h("th", { class: "num-col hide-narrow", text: t("colGpm") }), h("th", { class: "num-col hide-narrow", text: t("colDmg") }))
          ),
          h(
            "tbody",
            {},
            players.map((row) =>
              h(
                "tr",
                { class: row.me ? "is-me" : "" },
                h("td", {}, h("span", { class: "hero-cell", text: row.hero || "—" }), row.name ? h("span", { class: "muted small player-sub", text: row.name }) : null),
                h("td", { class: "num-col num", text: `${row.kills ?? "—"} / ${row.deaths ?? "—"} / ${row.assists ?? "—"}` }),
                h("td", { class: "num-col num", text: number(row.net_worth) }),
                h("td", { class: "num-col num hide-narrow", text: number(row.gpm) }),
                h("td", { class: "num-col num hide-narrow", text: number(row.hero_damage) })
              )
            )
          )
        )
      );
    });
    return card(t("scoreboardTitle"), "swords", h("div", { class: "teams" }, teams));
  }

  // --- progress -------------------------------------------------------------------

  async function loadCareer() {
    const root = document.getElementById("progress-root");
    if (!state.career) {
      root.replaceChildren(card(t("tiles.winrate"), "chart-line", skeletonRows(4)));
    }
    if (!state.player) {
      await refreshPlayer();
    }
    if (!state.player?.linked) {
      root.replaceChildren(linkPanel());
      hydrate(root);
      return;
    }
    const result = await call("career");
    if (result.ok) {
      state.career = result.data;
    }
    renderCareer();
  }

  function trendDelta(trend, key, format = (v) => v) {
    const item = trend && trend[key];
    if (!item || item.delta === null || item.delta === undefined || !trend.enough) {
      return null;
    }
    const tone = item.better === true ? "good" : item.better === false ? "bad" : "idle";
    const iconName = item.direction === "up" ? "trending-up" : item.direction === "down" ? "trending-down" : "minus";
    const sign = item.delta > 0 ? "+" : "";
    return h("span", { class: `delta delta-${tone}` }, icon(iconName), h("span", { class: "num", text: `${sign}${format(item.delta)}` }), h("span", { class: "muted", text: ` ${t("vsPrevious", trend.window)}` }));
  }

  function tile(label, value, delta, sub) {
    return h("div", { class: "tile" }, h("p", { class: "tile-label", text: label }), h("p", { class: "tile-value", text: value }), delta || null, sub ? h("p", { class: "tile-sub muted", text: sub }) : null);
  }

  function renderCareer() {
    const root = document.getElementById("progress-root");
    const career = state.career;
    if (!career || !career.matches) {
      root.replaceChildren(card(t("tiles.winrate"), "chart-line", emptyState("chart-line", t("progressEmptyTitle"), t("progressEmptyHint"))));
      hydrate(root);
      return;
    }
    const avg = career.averages || {};
    const trend = career.trend || {};
    const streak = career.streak;
    const streakText = streak && streak.length >= 2 ? (streak.win ? t("streakWin", streak.length) : t("streakLoss", streak.length)) : null;
    const tiles = h(
      "div",
      { class: "tiles" },
      tile(t("tiles.winrate"), career.winrate == null ? "—" : `${career.winrate}%`, trendDelta(trend, "winrate", (v) => `${Math.round(v)}%`), streakText || t("recordLine", career.wins, career.losses, career.matches)),
      tile(t("tiles.kda"), avg.kda == null ? "—" : avg.kda.toFixed(1), trendDelta(trend, "kda", (v) => v.toFixed(1))),
      tile(t("tiles.gpm"), number(avg.gpm), trendDelta(trend, "gpm", (v) => Math.round(v))),
      tile(t("tiles.lh10"), number(avg.lh_10), trendDelta(trend, "lh_10", (v) => Math.round(v))),
      tile(t("tiles.score"), avg.score == null ? "—" : String(Math.round(avg.score)), trendDelta(trend, "score", (v) => Math.round(v)))
    );

    const chartHost = h("div", { class: "chart-host", dataset: { chart: "career" } });
    const scoreCard = card(
      t("scoreChartTitle"),
      "chart-line",
      h(
        "div",
        {},
        h("p", { class: "muted small chart-note", text: t("scoreChartHint") }),
        chartHost,
        h(
          "ul",
          { class: "chart-legend" },
          h("li", {}, h("span", { class: "chart-key chart-key-dot", style: "--key: var(--ok)" }), h("span", { text: t("winKey") })),
          h("li", {}, h("span", { class: "chart-key chart-key-dot", style: "--key: var(--error)" }), h("span", { text: t("lossKey") }))
        )
      )
    );

    const plan = career.focus_plan || [];
    const planCard = card(
      t("planTitle"),
      "target",
      plan.length
        ? h(
            "div",
            {},
            h("p", { class: "muted small", text: t("planHint") }),
            h(
              "ol",
              { class: "findings" },
              plan.map((item, index) =>
                h(
                  "li",
                  { class: "finding finding-improve" },
                  h("span", { class: "finding-index num", text: String(index + 1) }),
                  h(
                    "div",
                    { class: "finding-body" },
                    h("p", { class: "finding-title" }, h("span", { text: item.title }), item.section_label ? h("span", { class: "tag", text: item.section_label }) : null),
                    h("div", { class: "share" }, window.LauncherCharts.meter(item.share, item.share >= 50 ? "bad" : "ok"), h("span", { class: "muted small", text: item.text })),
                    item.drill ? h("p", { class: "finding-drill" }, icon("lightbulb"), h("span", {}, h("strong", { text: `${t("drill")}: ` }), item.drill)) : null
                  )
                )
              )
            )
          )
        : h("p", { class: "muted", text: t("planEmpty") })
    );

    const strengths = career.recurring_strengths || [];
    const strengthsCard = strengths.length
      ? card(
          t("strengthsRecurring"),
          "sparkles",
          h(
            "ul",
            { class: "findings findings-compact" },
            strengths.map((item) =>
              h("li", { class: "finding finding-strength" }, h("span", { class: "dot", "data-tone": "good" }), h("div", { class: "finding-body" }, h("p", { class: "finding-title", text: item.title }), h("p", { class: "finding-text muted", text: item.text })))
            )
          )
        )
      : null;

    const heroes = career.heroes || [];
    const heroesCard = heroes.length
      ? card(
          t("heroesTitle"),
          "user",
          h(
            "div",
            { class: "table-wrap" },
            h(
              "table",
              { class: "table" },
              h("thead", {}, h("tr", {}, h("th", { text: t("colHero") }), h("th", { class: "num-col", text: t("colMatches") }), h("th", { class: "num-col", text: t("colWinrate") }), h("th", { class: "num-col", text: "KDA" }), h("th", { class: "num-col hide-narrow", text: t("colGpm") }), h("th", { class: "num-col", text: t("colScore") }))),
              h(
                "tbody",
                {},
                heroes.map((hero) =>
                  h(
                    "tr",
                    {},
                    h("td", { class: "hero-cell", text: hero.hero }),
                    h("td", { class: "num-col num", text: String(hero.matches) }),
                    h("td", { class: "num-col num", text: hero.winrate == null ? "—" : `${hero.winrate}%` }),
                    h("td", { class: "num-col num", text: hero.kda == null ? "—" : hero.kda.toFixed(1) }),
                    h("td", { class: "num-col num hide-narrow", text: number(hero.gpm) }),
                    h("td", { class: "num-col num", text: hero.score == null ? "—" : String(Math.round(hero.score)) })
                  )
                )
              )
            )
          )
        )
      : null;

    root.replaceChildren(
      h("p", { class: "muted small progress-note", text: t("analyzed", career.analyzed, career.matches) }),
      tiles,
      scoreCard,
      planCard,
      strengthsCard || "",
      heroesCard || ""
    );
    hydrate(root);
    const items = (career.series || []).map((match) => ({
      label: String(match.match_id),
      value: match.score,
      title: `${match.hero || "—"} · ${match.win === true ? t("win") : match.win === false ? t("loss") : "—"}`,
      detail: relativeTime(match.start_time),
      key: match.win === true ? "win" : match.win === false ? "loss" : null,
      matchId: match.match_id
    }));
    window.LauncherCharts.columns(chartHost, {
      items,
      yMax: 100,
      color: VIZ_1,
      valueLabel: t("scoreLabel"),
      ariaLabel: t("scoreChartTitle"),
      onSelect: (item) => openMatch(item.matchId)
    });
  }

  // --- home banner + status ----------------------------------------------------------

  function renderBanner(status) {
    const banner = document.getElementById("review-banner");
    const text = document.getElementById("review-banner-text");
    const review = status.player && status.player.lastReview;
    const fresh = review && Date.now() - Date.parse(review.at || "") < 6 * 3600 * 1000;
    banner.classList.toggle("hidden", !fresh);
    if (fresh) {
      const score = review.score !== null && review.score !== undefined ? ` · ${review.score}/100` : "";
      text.textContent = state.locale === "ru" ? `Разбор последнего матча готов${score}` : `Your last match review is ready${score}`;
      banner.onclick = () => openMatch(review.match_id);
    }
  }

  function onStatus(status) {
    const localeChanged = state.locale !== (status.locale === "ru" ? "ru" : "en");
    state.locale = status.locale === "ru" ? "ru" : "en";
    state.status = status;
    renderBanner(status);
    if (localeChanged) {
      if (state.view === "matches") {
        renderMatches();
      } else if (state.view === "progress") {
        renderCareer();
      }
    }
  }

  function init() {
    for (const tab of document.querySelectorAll(".tabs [data-view]")) {
      tab.addEventListener("click", () => setView(tab.dataset.view));
    }
    document.querySelector(".tabs")?.addEventListener("keydown", (event) => {
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") {
        return;
      }
      const tabs = [...document.querySelectorAll(".tabs [data-view]")];
      const index = tabs.findIndex((tab) => tab.getAttribute("aria-selected") === "true");
      const next = tabs[(index + (event.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length];
      next.focus();
      setView(next.dataset.view);
    });
    api.onPlayerEvent?.((event) => {
      if (event.type === "open-match" && event.matchId) {
        openMatch(event.matchId);
      } else if (event.type === "review-ready" && state.view === "matches") {
        loadMatches(true);
      }
    });
    // app.js may render its first status before this script loads.
    api.getStatus?.().then((status) => status && onStatus(status)).catch(() => {});
    let saved = "home";
    try {
      saved = localStorage.getItem(TAB_KEY) || "home";
    } catch {
      // Storage unavailable: start on Home.
    }
    if (["matches", "progress"].includes(saved)) {
      setView(saved, { remember: false });
    }
    // Keep the table fresh while it is open (new matches, sync results).
    setInterval(() => {
      if (state.view === "matches" && !document.hidden) {
        loadMatches();
      }
    }, 15000);
    let resizeTimer = null;
    window.addEventListener("resize", () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        if (state.view === "match" && state.match?.analysis) {
          document.querySelectorAll("#match-root [data-chart]").forEach((host) => drawChart(host, state.match.analysis));
        } else if (state.view === "progress" && state.career) {
          renderCareer();
        }
      }, 150);
    });
  }

  window.PlayerViews = { onStatus, openMatch, setView };
  init();
})();
