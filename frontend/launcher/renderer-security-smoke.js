"use strict";

// Real renderer/preload/IPC checks shared by source and packaged Windows smoke.
const { BrowserWindow } = require("electron");
const path = require("node:path");
const { protectWindow } = require("./renderer-security");

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function until(predicate, timeoutMs = 5000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await predicate()) return true;
    await delay(50);
  }
  return false;
}

async function runRendererSecuritySmoke({ mainWindow, overlayWindow, skillArrows, backendUrl, requestBackend, step }) {
  const main = mainWindow.webContents;
  const originalSort = await main.executeJavaScript("localStorage.getItem('dota-ai-coach.matches-sort')");
  const originalLanguage = (await main.executeJavaScript("window.launcherApi.getStatus()")).language;
  // Actual validated restore into the smoke backend's dedicated temporary DB.
  const restored = await requestBackend("/player/backup", "POST", {
    format: "wardly-backup", version: 1, account_id: 12345,
    tables: {
      players: [{ account_id: 12345, persona_name: "Smoke" }],
      matches: Array.from({ length: 32 }, (_, index) => ({
        account_id: 12345, match_id: 8100000001 + index,
        start_time: 1700000000 + index, duration: 1800,
        hero_id: index % 2 === 0 ? 8 : 1,
        hero: index % 2 === 0 ? "Juggernaut" : "Anti-Mage",
        win: index === 15 ? null : index % 2 === 0,
        kills: 0, deaths: null, assists: 5, gpm: 400 + index,
        note: "<b>Тест / Test</b>", sources: "gsi", parse_status: "",
      })),
    },
  });
  step("linked history fixture restored in isolated smoke database", restored.linked === true);
  // Fresh private view state obtains the fixture through genuine preload/IPC.
  await main.loadFile(path.join(__dirname, "renderer/index.html"));
  try {
    for (const [lang, label] of [["ru", "Язык"], ["en", "Language"]]) {
      await main.executeJavaScript(`document.querySelector('#tab-settings').click(); document.querySelector('[data-language="${lang}"]').click(); true`);
      const drawn = await until(() => main.executeJavaScript(`document.documentElement.lang === '${lang}' && document.querySelector('#language-title').textContent === '${label}' && document.querySelector('[data-language="${lang}"]').getAttribute('aria-checked') === 'true'`));
      step(`settings UI and trusted IPC (${lang})`, drawn);
      await main.executeJavaScript("window.PlayerViews.setView('matches', { remember: false }); true");
      const matchCopy = await until(() => main.executeJavaScript(`(() => {
        const root = document.querySelector('#matches-root');
        const linked = ${JSON.stringify(lang === "ru" ? "Матчи" : "Matches")};
        const unlinked = ${JSON.stringify(lang === "ru" ? "Привяжите аккаунт Steam" : "Link your Steam account")};
        return !document.querySelector('#view-matches').classList.contains('hidden')
          && !root.querySelector('.skeleton') && (root.textContent.includes(unlinked) || root.textContent.includes(linked));
      })()`));
      step(`matches UI and extracted texts (${lang})`, matchCopy);
      const linkedRows = await until(() => main.executeJavaScript("document.querySelectorAll('#matches-root tbody .row-link').length >= 30"), 10000);
      const partial = linkedRows && await main.executeJavaScript(`(() => {
        const rows = [...document.querySelectorAll('#matches-root tbody .row-link')];
        return rows.every(row => row.cells[2].textContent === '0 / — / 5' && row.querySelector('.row-note')?.title === '<b>Тест / Test</b>' && !row.querySelector('b'))
          && rows.some(row => row.dataset.result === 'unknown');
      })()`);
      await main.executeJavaScript("document.querySelector('#matches-root .table-wrap + .btn-block')?.click(); true");
      const paged = await until(() => main.executeJavaScript("document.querySelectorAll('#matches-root tbody .row-link').length === 32"));
      let sorted = true;
      for (let click = 0; click < 2; click += 1) {
        const direction = await main.executeJavaScript("(() => { const th = document.querySelector('#matches-root thead th:nth-child(4)'); const next = th.getAttribute('aria-sort') === 'descending' ? 'ascending' : 'descending'; th.querySelector('button').click(); return next; })()");
        sorted = sorted && await until(() => main.executeJavaScript(`document.querySelector('#matches-root thead th:nth-child(4)')?.getAttribute('aria-sort') === '${direction}' && document.querySelector('#matches-root tbody tr')?.cells[3].textContent === '${direction === "ascending" ? 400 : 431}'`));
      }
      await main.executeJavaScript("(() => { const select = document.querySelector('#matches-root .filter-bar select'); select.value = '8'; select.dispatchEvent(new Event('change', {bubbles:true})); })()");
      const filtered = await until(() => main.executeJavaScript("(() => { const rows = [...document.querySelectorAll('#matches-root tbody .row-link')]; return rows.length === 16 && rows.every(row => row.cells[1].textContent.includes('Juggernaut')); })()"));
      await main.executeJavaScript("(() => { const select = document.querySelector('#matches-root .filter-bar select'); select.value = ''; select.dispatchEvent(new Event('change', {bubbles:true})); })()");
      const cleared = await until(() => main.executeJavaScript("document.querySelectorAll('#matches-root tbody .row-link').length === 30 && Boolean(document.querySelector('#matches-root .table-wrap + .btn-block'))"));
      step(`linked match table paging, sorting, filter and partial counters (${lang})`, partial && paged && sorted && filtered && cleared, JSON.stringify({partial,paged,sorted,filtered,cleared}));
      await main.executeJavaScript("window.PlayerViews.setView('home', {remember:false}); window.PlayerViews.setView('matches', {remember:false}); true");
      const matchId = await main.executeJavaScript("(() => { const row = document.querySelector('#matches-root tbody .row-link'); const id = row.dataset.matchId; row.click(); return id; })()");
      const review = await until(() => main.executeJavaScript("!document.querySelector('#view-match').classList.contains('hidden') && Boolean(document.querySelector('#match-root .back')) && !document.querySelector('#match-root .skeleton')"));
      await main.executeJavaScript("document.body.dispatchEvent(new KeyboardEvent('keydown', {key:'ArrowLeft',altKey:true,bubbles:true,cancelable:true})); true");
      const back = await until(() => main.executeJavaScript("!document.querySelector('#view-matches').classList.contains('hidden') && document.querySelector('#view-match').classList.contains('hidden')"));
      await main.executeJavaScript("document.body.dispatchEvent(new KeyboardEvent('keydown', {key:'ArrowRight',altKey:true,bubbles:true,cancelable:true})); true");
      const forward = await until(() => main.executeJavaScript("!document.querySelector('#view-match').classList.contains('hidden') && Boolean(document.querySelector('#match-root .back')) && !document.querySelector('#match-root .skeleton')"));
      await main.executeJavaScript(`window.__wardlyReturnRow = document.querySelector('#matches-root tr[data-match-id="${matchId}"]'); document.querySelector('#match-root .back')?.click(); true`);
      const returned = await until(() => main.executeJavaScript(`!document.querySelector('#view-matches').classList.contains('hidden') && document.activeElement?.dataset.matchId === ${JSON.stringify(matchId)} && document.activeElement !== window.__wardlyReturnRow`));
      await main.executeJavaScript("delete window.__wardlyReturnRow; true");
      step(`review history back, forward and focused return (${lang})`, review && back && forward && returned, JSON.stringify({review,back,forward,returned}));
      const history = await main.executeJavaScript(`(() => {
        window.PlayerViews.setView('home', { remember: false });
        const version = ${JSON.stringify(require("./package.json").version)};
        renderWhatsNew({ whatsNew: version, whatsNewFrom: '0.0.0' });
        const card = document.querySelector('#whats-new-card');
        const heading = document.querySelector('#whats-new-heading');
        const list = document.querySelector('#whats-new-list');
        const label = ${JSON.stringify(lang === "ru" ? "Что нового в " : "What's new in ")};
        const also = ${JSON.stringify(lang === "ru" ? "Также в " : "Also in ")};
        const table = window.WardlyWhatsNew.texts(${JSON.stringify(lang)});
        return !card.classList.contains('hidden') && heading.textContent === label + version
          && list.querySelectorAll('.whats-new-version').length === 3
          && [...list.querySelectorAll('.whats-new-version')].every(node => node.textContent.startsWith(also))
          && table[version].every(text => list.textContent.includes(text));
      })()`);
      step(`update history and skipped versions DOM (${lang})`, history);
    }
  } finally {
    await main.executeJavaScript(`(() => { const value = ${JSON.stringify(originalSort)}; if (value === null) localStorage.removeItem('dota-ai-coach.matches-sort'); else localStorage.setItem('dota-ai-coach.matches-sort', value); })()`);
    await main.executeJavaScript(`window.launcherApi.setLanguage(${JSON.stringify(originalLanguage)})`);
    await main.executeJavaScript("window.launcherApi.getStatus().then(renderWhatsNew)");
  }

  const partialCounters = await main.executeJavaScript(`(() => {
    const node = document.createElement('span');
    node.textContent = window.WardlyMatchContract.combatScore({ kills: 0, deaths: null, assists: 5 });
    document.body.append(node);
    const valid = node.textContent === '0 / — / 5' && !node.textContent.includes('null');
    node.remove();
    return valid && window.WardlyMatchContract.combatScore({ deaths: 4, assists: 9 }) === '— / 4 / 9';
  })()`);
  step("match counter contract renders partial and zero totals", partialCounters);

  for (const [language, label] of [["ru", "Убийства: 0"], ["en", "Kills: 0"]]) {
    const rendered = await main.executeJavaScript(`(() => {
      const row = { source: 'analysis.headline', field: 'kills', observed_at: null, precision: 'reported_total', value: 0 };
      const node = window.WardlyCoachEvidence.render({ counter_evidence: [row] }, ${JSON.stringify(language)});
      document.body.append(node);
      node.querySelector('summary').click();
      // The smoke window is hidden; Chromium may suspend animation frames.
      // The details click and text content are synchronous DOM operations.
      const valid = node.open && node.textContent.includes(${JSON.stringify(label)}) && node.querySelectorAll('p').length === 2;
      node.remove();
      return valid;
    })()`);
    step(`coach counter evidence DOM (${language})`, rendered);
  }
  const rejected = await main.executeJavaScript(`(() => {
    const row = { source: 'analysis.headline', field: 'kills', observed_at: null, precision: 'reported_total', value: '<img src=x onerror=alert(1)>' };
    return window.WardlyCoachEvidence.render({ counter_evidence: [row] }, 'en') === null
      && window.WardlyCoachEvidence.render({}, 'ru') === null
      && window.WardlyCoachEvidence.render({ counter_evidence: [{...row, value: 2, source: 'unknown'}] }, 'en') === null;
  })()`);
  step("coach evidence rejects malformed data and supports legacy reviews", rejected);

  for (const [language, decimal] of [["ru", "430,5"], ["en", "430.5"]]) {
    const rendered = await main.executeJavaScript(`(() => {
      const rate = { source: 'analysis.headline', field: 'gpm', observed_at: null, precision: 'reported_match_rate', value: 0 };
      const node = window.WardlyCoachEvidence.render({ rate_evidence: [rate, {...rate, field: 'xpm', value: 430.5}] }, ${JSON.stringify(language)});
      document.body.append(node);
      node.querySelector('summary').click();
      const valid = node.open && node.querySelector('summary').textContent.includes('GPM/XPM')
        && node.textContent.includes('GPM: 0') && node.textContent.includes('XPM: ' + ${JSON.stringify(decimal)})
        && !node.textContent.includes('undefined') && node.querySelectorAll('p').length === 2;
      node.remove();
      const combined = window.WardlyCoachEvidence.render({rate_evidence: [rate], counter_evidence: [{...rate, field: 'kills', precision: 'reported_total'}]}, ${JSON.stringify(language)});
      const bad = [true, '390', -1, NaN, Infinity, Number.MAX_SAFE_INTEGER + 1];
      return valid && combined.textContent.includes('K/D/A, GPM/XPM')
        && bad.every(value => window.WardlyCoachEvidence.render({rate_evidence: [{...rate, value}]}, 'en') === null)
        && window.WardlyCoachEvidence.render({rate_evidence: [{...rate, precision: 'reported_total'}]}, 'en') === null;
    })()`);
    step(`coach rate evidence DOM (${language})`, rendered);
  }

  for (const [name, contents] of [["panel", main], ["overlay", overlayWindow.webContents]]) {
    const policy = await contents.executeJavaScript(`(async () => {
      const violations = [];
      const observe = (event) => violations.push(event.effectiveDirective);
      document.addEventListener('securitypolicyviolation', observe);
      window.__wardlyInjectedScript = false;
      const script = document.createElement('script');
      script.textContent = 'window.__wardlyInjectedScript = true';
      document.head.append(script);
      let blockedFetch = false;
      try { await fetch(${JSON.stringify(`${backendUrl}/health`)}); } catch { blockedFetch = true; }
      await new Promise((resolve) => setTimeout(resolve, 50));
      script.remove();
      document.removeEventListener('securitypolicyviolation', observe);
      return !window.__wardlyInjectedScript && blockedFetch && violations.includes('script-src-elem') && violations.includes('connect-src');
    })()`);
    step(`${name} CSP blocks injected script and direct HTTP`, policy);

    let navigated = false;
    const before = contents.getURL();
    const attempted = () => { navigated = true; };
    contents.on("will-navigate", attempted);
    contents.on("will-frame-navigate", attempted);
    try {
      await contents.executeJavaScript(`location.assign(${JSON.stringify(`${backendUrl}/health`)}); true`);
      await until(() => navigated);
      step(`${name} navigation rejected`, navigated && contents.getURL() === before);
    } finally {
      contents.removeListener("will-navigate", attempted);
      contents.removeListener("will-frame-navigate", attempted);
    }
    let created = false;
    const popup = (window) => { created = true; window.destroy(); };
    contents.on("did-create-window", popup);
    try {
      const denied = await contents.executeJavaScript(`window.open(${JSON.stringify(`${backendUrl}/health`)}) === null`);
      await delay(100);
      step(`${name} popup rejected`, denied && !created);
    } finally {
      contents.removeListener("did-create-window", popup);
    }
  }

  await main.executeJavaScript("window.launcherApi.skillArrows('calibrate')");
  const calibration = skillArrows.window();
  const drawn = calibration && await until(() => calibration.webContents.executeJavaScript("Boolean(document.querySelector('#calibrate')) && !document.querySelector('#calibrate').classList.contains('hidden') && Boolean(document.querySelector('#cal-title')?.textContent)"));
  step("trusted calibration renderer opened", drawn);

  for (const [name, file, preload, invoke] of [
    ["panel", "renderer/index.html", "preload.js", "window.launcherApi.getStatus()"],
    ["overlay", "overlay/index.html", "overlay-preload.js", "window.overlayApi.getConfig()"],
    ["calibration", "skill-arrows/index.html", "skill-arrows-preload.js", "window.skillArrowApi.auto()"],
  ]) {
    // Another webContents with the genuine preload and exact same local URL
    // must not gain the owning window's privileges.
    const unowned = new BrowserWindow({ show: false, webPreferences: {
      preload: path.join(__dirname, preload), contextIsolation: true, nodeIntegration: false, sandbox: true,
    } });
    protectWindow(unowned);
    try {
      await unowned.loadFile(path.join(__dirname, file), name === "calibration" ? { query: { mode: "calibrate" } } : {});
      const denied = await unowned.webContents.executeJavaScript(`${invoke}.then(() => false, (error) => error.message.includes('Untrusted IPC sender'))`);
      step(`${name} IPC rejects a different window`, denied);
    } finally {
      unowned.destroy();
    }
  }

  if (drawn) {
    await calibration.webContents.executeJavaScript("document.querySelector('#cal-cancel').click(); true");
    step("trusted calibration IPC cancels", await until(() => !skillArrows.state().calibrating));
  }
}

module.exports = { runRendererSecuritySmoke };
