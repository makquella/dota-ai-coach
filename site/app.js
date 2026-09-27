// Dota AI Coach website: language switch (the HTML is Russian, English lives
// here), screenshots per language, the download button (latest GitHub release)
// and small scroll effects. No dependencies.
(() => {
  const REPO = "makquella/dota-ai-coach";
  const RELEASES = `https://github.com/${REPO}/releases/latest`;
  const LANG_KEY = "dac.lang";

  const EN = {
    title: "Dota AI Coach — a Dota 2 coach right in your game",
    skip: "Skip to content",
    navLabel: "Sections",
    navIngame: "In game",
    navHow: "How it works",
    navReview: "Review",
    navFaq: "FAQ",
    langLabel: "Language",
    navDownload: "Download",
    badge: "Official Valve integration only — no risk for your account",
    h1a: "Die less.",
    h1b: "Farm more.",
    h1c: "In every game.",
    lead:
      "The coach watches the match with you and speaks up <strong>at the right moment</strong> — on screen and out loud. After the game, an honest review: where the farm went, why you died and what the player of your rank did.",
    ctaDownload: "Download for Windows",
    metaFree: "Free",
    metaOpen: "Open source",
    metaWin: "Windows 10 and 11",
    ingameTitle: "Advice right in the game",
    ingameSub: "Dota is complex. The coach tells you what to do now.",
    lowhpTitle: "Low HP",
    lowhpText: "Urgent advice at once, while you can still get away. The rest comes with pauses so it never distracts.",
    lowhpAlt: "Urgent advice: leave the wave and reset HP",
    planTitle: "Plan for this game",
    planText: "From the pick to 1:30: last hits you need by 10:00, the key item and your recurring mistake.",
    planAlt: "Plan for this game on the overlay",
    farmTitle: "Behind on farm",
    farmText: "With numbers: your last hits and a good pace for this minute.",
    farmAlt: "Farm advice with the last-hit pace",
    tpTitle: "TP scroll",
    tpText: "After minute 10 it reminds you when you have gone a minute without a TP: without it you cannot join a fight or save a tower.",
    tpAlt: "Reminder to carry a TP scroll",
    spendTitle: "Gold after death",
    spendText: "Died with spare gold? Buy parts of your next item right away. After minute 30 it keeps the buyback gold.",
    spendAlt: "Advice to spend gold while dead",
    timerTitle: "Map timers",
    timerText: "20 seconds ahead: runes, shrines, lotuses, the Tormentor. Stacks and wards for a support. The coach finds your role from your lane.",
    timerAlt: "Map timer: the Tormentor in 15 seconds",
    heroesTitle: "Full advice for 21 carries",
    heroesSub: "Farm, items, objectives and abilities. On any other hero: survival, map timers and role tips.",
    heroesNote: "Match reviews, the map, the build and progress work for all 127 heroes.",
    voiceNote: "Advice can be spoken with the Windows voice — heard even in exclusive fullscreen, where the card cannot be shown.",
    howTitle: "Install it and play",
    howSub: "No accounts, no setup. The app connects to Dota by itself.",
    step1: "Start Dota — the coach sees the match by itself through Valve's official integration",
    step1Alt: "The app sees the match: Juggernaut, 18:54",
    step2: "Play: short advice shows over the game when you need it",
    step2Alt: "The plan for this game over a real Dota 2 match",
    step3: "After the match open the review: the score, your mistakes and what to do next game",
    step3Alt: "Match review",
    reviewTitle: "Your personal coach after every match",
    reviewSub: "You play better than it seems. The review shows where you lose.",
    reviewText:
      "Every match is recorded by itself and filled in with OpenDota data. Rules count everything in numbers, and the AI coach explains the match in plain words — every number in its text is checked against the data.",
    c1: "A score for the match: lane, farm, survival, fights, items",
    c2: "Map on the Dota minimap: your hero's path, where you died and the wards",
    c3: "Build and item timings against OpenDota statistics",
    c4: "You against the player of your rank in the same role",
    c5: "One mistake in focus — and a count of whether you avoid it",
    c6: "“Ask the coach” — your own question about the match",
    insideTitle: "Everything in numbers",
    insideSub: "Not “play better”, but where exactly and by how much.",
    mapCap: "Match map: where you went and where you died. Keep dying on the enemy half and it goes into the review",
    mapAlt: "Match map with deaths and the hero's path",
    buildCap: "Build: win rate by purchase time for every item, and the pro build",
    buildAlt: "Item timings with win rates",
    chartCap: "Last hits, gold and experience by minute against a good pace, with your deaths on the chart",
    chartAlt: "Last hits by minute against a good pace",
    faqTitle: "FAQ",
    q1: "Can I get banned?",
    a1: "No. Game State Integration is an official Dota 2 feature by Valve. The app doesn't inject into the game, read its memory or control your hero; the advice is like a friend's on Discord.",
    q2: "Is it really free?",
    a2: "Yes, completely. The AI review needs your own free Google Gemini key (takes a minute to get); everything else works the same without it.",
    q3: "I can't see the advice over the game",
    a3: "Windows doesn't draw windows over exclusive fullscreen. In Dota: Settings → Video → “Borderless window”. Or turn on the voice — it is heard in any mode.",
    q4: "Which heroes get advice?",
    a4: "Full advice (farm, items, objectives, abilities) for 21 carries. On any other hero the coach helps you survive (low HP, death streaks, disables, mana, buyback) and gives map timers and tips for your role. Match reviews and progress work for every hero.",
    q5: "Where does the match history come from?",
    a5: "The app records every match by itself and fills it in with OpenDota data. For that, Expose Public Match Data must be on in Dota 2.",
    q6: "Do I need the internet?",
    a6: "Not for advice during the game. The internet is needed for the OpenDota history, the AI review and updates.",
    q7: "Windows says it “protected your PC”",
    a7: "The installer isn't code-signed yet. Click “More info” → “Run anyway”. The code is open, so you can check what's inside.",
    finalTitle: 'Your next game — <span class="accent">with a coach</span>',
    finalText: "Two minutes to install. After that the app does everything by itself and updates without you.",
    footerLabel: "Links",
    footerReleases: "Releases",
    footerIssues: "Report a problem",
    footerPrivacy: "Privacy",
    legal:
      "Dota 2 is a trademark of Valve Corporation. This project is not affiliated with or endorsed by Valve. Game frames are from the Dota 2 Steam page; hero portraits are Valve's.",
    version: (v, mb) => `Version ${v} · Windows 10 and 11 · ${mb} MB`
  };
  const RU = {};

  let lang = "ru";
  let release = null;

  document.documentElement.classList.add("js");

  // --- language ------------------------------------------------------------------

  function remember(key, value) {
    if (!(key in RU)) {
      RU[key] = value;
    }
  }

  function applyLanguage(next) {
    lang = next === "en" ? "en" : "ru";
    const table = lang === "en" ? EN : RU;
    document.documentElement.lang = lang;
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.dataset.i18n;
      remember(key, el.textContent);
      if (typeof table[key] === "string") {
        el.textContent = table[key];
      }
    });
    document.querySelectorAll("[data-i18n-html]").forEach((el) => {
      const key = el.dataset.i18nHtml;
      remember(key, el.innerHTML);
      if (typeof table[key] === "string") {
        el.innerHTML = table[key];
      }
    });
    for (const [attr, name] of [
      ["i18nAria", "aria-label"],
      ["i18nAlt", "alt"]
    ]) {
      document.querySelectorAll(`[data-${attr.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`)}]`).forEach((el) => {
        const key = el.dataset[attr];
        remember(key, el.getAttribute(name) || "");
        if (typeof table[key] === "string") {
          el.setAttribute(name, table[key]);
        }
      });
    }
    remember("title", document.title);
    document.title = table.title || RU.title;
    // Screenshots exist in both languages.
    document.querySelectorAll("img[data-img]").forEach((img) => {
      img.src = `assets/app/${lang}/${img.dataset.img}.jpg`;
    });
    document.querySelectorAll("img[data-ov]").forEach((img) => {
      img.src = `assets/overlay/${lang}/${img.dataset.ov}.webp`;
    });
    document.querySelectorAll("img[data-game]").forEach((img) => {
      img.src = `assets/game/${img.dataset.game}-${lang}.jpg`;
    });
    document.querySelectorAll("img[data-shot]").forEach((img) => {
      img.src = `assets/shots/${lang}/${img.dataset.shot}.jpg`;
    });
    document.querySelectorAll(".lang [data-lang]").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.lang === lang));
    });
    renderRelease();
  }

  function initialLanguage() {
    try {
      const saved = localStorage.getItem(LANG_KEY);
      if (saved === "ru" || saved === "en") {
        return saved;
      }
    } catch {
      // Storage blocked: fall back to the browser language.
    }
    const preferred = (navigator.languages || [navigator.language || "ru"]).map((l) => String(l).toLowerCase());
    return preferred.some((l) => /^(ru|uk|be|kk)/.test(l)) ? "ru" : "en";
  }

  document.querySelectorAll(".lang [data-lang]").forEach((button) => {
    button.addEventListener("click", () => {
      applyLanguage(button.dataset.lang);
      try {
        localStorage.setItem(LANG_KEY, lang);
      } catch {
        // Not remembered; fine.
      }
    });
  });

  // --- download: the latest release's installer ---------------------------------

  function renderRelease() {
    const buttons = document.querySelectorAll(".js-download");
    if (!release) {
      buttons.forEach((a) => (a.href = RELEASES));
      return;
    }
    buttons.forEach((a) => (a.href = release.url));
    const mb = Math.round(release.size / 1024 / 1024);
    const text = lang === "en" ? EN.version(release.version, mb) : `Версия ${release.version} · Windows 10 и 11 · ${mb} МБ`;
    document.querySelectorAll(".js-release-meta").forEach((el) => (el.textContent = text));
  }

  async function loadRelease() {
    try {
      const response = await fetch(`https://api.github.com/repos/${REPO}/releases/latest`, {
        headers: { Accept: "application/vnd.github+json" }
      });
      if (!response.ok) {
        return;
      }
      const data = await response.json();
      const asset = (data.assets || []).find((a) => /Setup-.*\.exe$/i.test(a.name));
      if (asset) {
        release = {
          url: asset.browser_download_url,
          size: asset.size,
          version: String(data.tag_name || "").replace(/^v/, "")
        };
        renderRelease();
      }
    } catch {
      // Offline or rate-limited: the buttons keep pointing at the releases page.
    }
  }

  // --- scroll effects -------------------------------------------------------------

  const nav = document.querySelector(".nav");
  const onScroll = () => nav.classList.toggle("scrolled", window.scrollY > 8);
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  const revealed = document.querySelectorAll(".section-head, .tile, .step, .split-copy, .split-stage, .heroes, .final-inner");
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add("shown");
            observer.unobserve(entry.target);
          }
        }
      },
      { rootMargin: "0px 0px -8% 0px" }
    );
    revealed.forEach((el) => {
      el.classList.add("reveal");
      observer.observe(el);
    });
  }

  applyLanguage(initialLanguage());
  loadRelease();
})();
