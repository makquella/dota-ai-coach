// Dota AI Coach website: language switch (the HTML is Russian, English lives
// here), the download button (latest GitHub release), the living advice card in
// the hero, the review showcase and small scroll effects. No dependencies.
(() => {
  const REPO = "makquella/dota-ai-coach";
  const RELEASES = `https://github.com/${REPO}/releases/latest`;
  const LANG_KEY = "dac.lang";

  const EN = {
    skip: "Skip to content",
    navLabel: "Sections",
    navFeatures: "Features",
    navHow: "How it works",
    navReview: "Review",
    navFaq: "FAQ",
    langLabel: "Language",
    navDownload: "Download",
    eyebrow: "Free · Windows · open source",
    heroTitle: 'A coach that watches <span class="accent">your game</span> with you',
    heroLead:
      "Advice over Dota 2 during the match, on screen and out loud. After the game, an honest review: where the farm went, why you died, when your item came and what the player of your rank did.",
    ctaDownload: "Download for Windows",
    ctaGithub: "Code on GitHub",
    ctaNote: "One-click install, updates itself.",
    sceneLabel: "Example of advice over the game",
    factsLabel: "In short",
    factMsUnit: "ms",
    factLatency: "to process the game data — the advice is there before you blink",
    factGsiValue: "Official",
    factGsi: "Valve's Game State Integration only: no memory reading, no inputs on your behalf",
    factFreeValue: "Free",
    checkOk: "36 last hits by 10:00 — in the data",
    checkOk2: "Maelstrom at 26:00 — in the data",
    checkBad: "50 last hits by 12:00 — sentence dropped",
    f7Tag: "Player of your rank",
    f7Title: "Compared with the one who stood across",
    f7Text: "Matchmaking picks opponents of your level, so their farm and deaths are within your reach. The review shows the gap in every number.",
    vsGpm: "Gold per minute",
    vsLh: "Last hits by 10:00",
    vsDeaths: "Deaths",
    factFree: "no subscriptions, no accounts; the AI review runs on a free Gemini key",
    factLocalValue: "Local",
    factLocal: "match history and keys stay on your computer",
    featuresKicker: "During the match and after",
    featuresTitle: "Everything a coach does — just faster and without the blame",
    f1Tag: "Live advice",
    f1Title: "Tells you what to do now, not five minutes later",
    f1Text:
      "Low HP under pressure, a gap in your farm, a risky walk to Roshan — rules spot the moment and show short advice. Urgent advice right away, the rest with pauses so it never distracts. You choose how often.",
    f1Alt: "Recent advice in the app",
    f2Tag: "Voice",
    f2Title: "Heard even in exclusive fullscreen",
    f2Text: "Speaks urgent or all advice with the Windows system voice. Works offline and never talks over itself.",
    f2Alt: "Frequency and voice settings",
    f3Tag: "Match map",
    f3Title: "Where you went and where you died",
    f3Text: "Your hero's path, deaths, wards and laning position. Keep dying on the enemy half and the coach will notice.",
    f3Alt: "Match map with deaths and the hero's path",
    f4Tag: "Build",
    f4Title: "Item timing in win rate",
    f4Text: "Compares when you finished an item with the typical timing in public matches and shows what it cost you.",
    f4Alt: "Win rate by purchase time",
    f5Tag: "AI coach",
    f5Title: "A review in words, with nothing made up",
    f5Text:
      "The model writes the review from the match data, and every number, time, hero and item is checked against it. If it doesn't match, the sentence doesn't make it in. You can also ask your own question — “why did I lose the lane?” — and the answer is checked the same way.",
    f6Tag: "Progress",
    f6Title: "See whether you're getting better",
    f6Text:
      "Win rate, farm and deaths over the last 10 games against the 10 before, recurring mistakes with drills, and your best games against your worst ones on the same hero.",
    f6Alt: "Progress tiles",
    m1: "Draft: your win rate against every enemy and the best pick from your pool",
    m2: "A first-run checklist shows what is left to set up",
    m3: "Save a review as PDF to show your team or coach",
    m4: "Live advice works without internet",
    m5: "Updates itself, never during a game",
    m6: "English and Russian",
    m7: "Focus: pick one mistake — every next review shows whether you avoided it",
    m8: "A plan at the start of each match: last-hit target, key item and your focus",
    m9: "Turbo and bot games do not skew your stats and trends",
    howKicker: "Three steps",
    howTitle: "Install it and forget it until the match starts",
    s1Title: "Install",
    s1Text: "The app finds Dota 2 in your Steam libraries and adds a small config file through which the game shares match data. Then add <code>-gamestateintegration</code> to Dota's launch options — the app will remind you.",
    s2Title: "Play as usual",
    s2Text: "Advice appears over the game only while Dota is active and a match is on. Use borderless window mode — or turn on the voice.",
    s3Title: "Review the game",
    s3Text: "A couple of minutes after the match: a score, what matters most next game and drills. Once OpenDota parses the replay, the review gets even sharper.",
    reviewKicker: "After the match",
    reviewTitle: "A review that explains instead of blaming",
    showLabel: "Parts of the review",
    t1: "Coach's review",
    t1d: "Turning points, mistakes and goals for the next game",
    t2: "Focus for the next game",
    t2d: "The three things worth the most wins",
    t3: "Over the match",
    t3d: "Last hits, gold and XP against a good pace",
    t4: "Score by match",
    t4d: "Your last 20 games at a glance",
    t5: "History",
    t5d: "Every match of your Steam account with a score",
    trustKicker: "Honestly",
    trustTitle: "No magic, and no risk to your account",
    tr1Title: "Doesn't touch the game",
    tr1Text:
      "Data comes through the official Game State Integration — the same mechanism streamer overlays use. Nothing is read from memory, nothing is pressed for you.",
    tr2Title: "Your data stays yours",
    tr2Text:
      "Match history, reviews and keys live in a local database on your computer. The app only talks to OpenDota for public stats and, if you turn it on, to an AI service.",
    tr3Title: "Rules decide, AI only phrases",
    tr3Text:
      "What to say, when and how urgently is decided by testable rules. The model is optional, only after the match, and fact-checked.",
    faqKicker: "Questions",
    faqTitle: "Frequently asked",
    q1: "Can I get banned?",
    a1: "No. Game State Integration is an official Dota 2 feature by Valve. The app doesn't inject into the game, read its memory or control your hero; the advice is like a friend's on Discord.",
    q2: "Is it really free?",
    a2: "Yes, completely. The AI review needs your own free Google Gemini key (takes a minute to get); everything else works the same without it.",
    q3: "I can't see the advice over the game",
    a3: "Windows can't draw windows over exclusive fullscreen. In Dota: Settings → Video → Borderless window. Or turn on the voice — it's heard in any mode.",
    q4: "Which heroes get live advice?",
    a4: "Full live advice (farm, items, objectives, abilities) covers 21 carries. On any other hero the coach gives survival advice: low HP, death streaks, disables, mana, buyback. The match review, map, build, draft and progress work for everyone.",
    q5: "Where does the match history come from?",
    a5: "The app records each of your matches through GSI and adds OpenDota data. For that, “Expose Public Match Data” must be on in Dota 2.",
    q6: "Do I need internet?",
    a6: "Not for advice during the game. Internet is used for OpenDota history, the AI review and updates.",
    q7: "Windows says it protected my PC",
    a7: "The installer isn't code-signed yet. Click “More info” → “Run anyway”. The code is open, so you can check what's inside.",
    finalTitle: "Your next game — with a coach",
    finalText: "Two minutes to install. The app does the rest by itself.",
    finalNote: "Windows 10 and 11 · about 120 MB",
    footerLabel: "Links",
    footerReleases: "Releases",
    footerIssues: "Report a problem",
    legal: "Dota 2 is a trademark of Valve Corporation. This project is not affiliated with or endorsed by Valve.",
    title: "Dota AI Coach — a Dota 2 coach inside the game",
    version: (v, mb) => `Version ${v} · Windows 10 and 11 · ${mb} MB`
  };

  // The live card cycles through real advice texts of the app (advice_i18n.py).
  const ADVICE = {
    ru: [
      { mode: "urgent", label: "Срочно", hp: 22, action: "Уходите с волны сейчас и восстановите HP, прежде чем вернуться.", reason: "При таком HP ещё один размен или заклинание могут вас убить." },
      { mode: "coaching", label: "Совет", hp: 64, action: "Навёрстывайте фарм по самому безопасному маршруту из волн и лагерей.", reason: "Вы отстаёте по фарму: драки до того, как выровняетесь, отодвинут тайминг." },
      { mode: "coaching", label: "Совет", hp: 81, action: "Тайминг по урону: ищите драки за ключевые цели, а не случайные стычки.", reason: "Присоединяйтесь, только если команда готова и драка идёт у ключевой цели." },
      { mode: "urgent", label: "Срочно", hp: 31, action: "Отойдите немного, заберите безопасные добивания, потом восстановите HP.", reason: "Неполное HP и давление на линии: ещё один размен может закончиться смертью." }
    ],
    en: [
      { mode: "urgent", label: "Urgent", hp: 22, action: "Leave the wave now and reset HP before rejoining.", reason: "At this HP, one more trade or spell can kill you." },
      { mode: "coaching", label: "Tip", hp: 64, action: "Recover farm through the safest wave-and-camp route.", reason: "You are behind on farm, so forcing fights before stabilizing can delay your next timing." },
      { mode: "coaching", label: "Tip", hp: 81, action: "You reached a damage timing; consider objective fights, not low-value skirmishes.", reason: "Consider joining only if your team is ready and the fight is near the objective." },
      { mode: "urgent", label: "Urgent", hp: 31, action: "Back up slightly, secure safe last hits, then reset your HP.", reason: "Reduced HP plus lane pressure can turn one more trade into a death." }
    ]
  };

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
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
    document.querySelectorAll("img[data-shot]").forEach((img) => {
      const ext = img.dataset.shot === "overlay" ? "png" : "jpg";
      img.src = `assets/shots/${lang}/${img.dataset.shot}.${ext}`;
    });
    document.querySelectorAll(".lang [data-lang]").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.lang === lang));
    });
    renderRelease();
    showAdvice(adviceIndex, true);
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
    const text = lang === "en"
      ? EN.version(release.version, mb)
      : `Версия ${release.version} · Windows 10 и 11 · ${mb} МБ`;
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

  // --- hero: the living advice card ------------------------------------------------

  const card = document.getElementById("advice");
  const labelEl = document.getElementById("advice-label");
  const actionEl = document.getElementById("advice-action");
  const reasonEl = document.getElementById("advice-reason");
  const hpEl = document.getElementById("scene-hp");
  const clockEl = document.getElementById("scene-clock");
  let adviceIndex = 0;
  let seconds = 14 * 60 + 32;

  function showAdvice(index, instant = false) {
    const items = ADVICE[lang];
    const item = items[index % items.length];
    const paint = () => {
      card.dataset.mode = item.mode;
      labelEl.textContent = item.label;
      actionEl.textContent = item.action;
      reasonEl.textContent = item.reason;
      hpEl.style.width = `${item.hp}%`;
      card.classList.remove("is-leaving");
    };
    if (instant || reducedMotion) {
      paint();
      return;
    }
    card.classList.add("is-leaving");
    setTimeout(paint, 300);
  }

  if (!reducedMotion) {
    setInterval(() => {
      adviceIndex = (adviceIndex + 1) % ADVICE.ru.length;
      showAdvice(adviceIndex);
    }, 5200);
    setInterval(() => {
      seconds += 1;
      clockEl.textContent = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
    }, 1000);
  }

  // --- review showcase --------------------------------------------------------------

  const showImg = document.getElementById("show-img");
  const tabs = [...document.querySelectorAll(".show-tabs [data-show]")];
  function selectShow(tab) {
    tabs.forEach((t) => t.setAttribute("aria-selected", String(t === tab)));
    showImg.classList.add("is-loading");
    showImg.dataset.shot = tab.dataset.show;
    showImg.alt = tab.querySelector("strong").textContent;
    showImg.onload = () => showImg.classList.remove("is-loading");
    showImg.src = `assets/shots/${lang}/${tab.dataset.show}.jpg`;
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => selectShow(tab));
    tab.addEventListener("keydown", (event) => {
      if (event.key !== "ArrowDown" && event.key !== "ArrowUp") {
        return;
      }
      event.preventDefault();
      const next = tabs[(index + (event.key === "ArrowDown" ? 1 : tabs.length - 1)) % tabs.length];
      next.focus();
      selectShow(next);
    });
  });

  // --- nav border + reveal on scroll ----------------------------------------------------

  const nav = document.querySelector(".nav");
  const onScroll = () => nav.classList.toggle("is-scrolled", window.scrollY > 8);
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  if (!reducedMotion && "IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        }
      },
      { rootMargin: "0px 0px -8% 0px" }
    );
    document.querySelectorAll(".section-head, .tile, .step, .trust-item, .faq details, .final-inner, .facts").forEach((el) => {
      el.classList.add("reveal");
      observer.observe(el);
    });
  }

  applyLanguage(initialLanguage());
  loadRelease();
})();
