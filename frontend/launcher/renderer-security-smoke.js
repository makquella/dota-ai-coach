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

async function runRendererSecuritySmoke({ mainWindow, overlayWindow, skillArrows, backendUrl, step }) {
  const main = mainWindow.webContents;
  const originalLanguage = (await main.executeJavaScript("window.launcherApi.getStatus()")).language;
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
