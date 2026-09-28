// Start-up splash (main.js createSplash). No preload and no Node: main drives it
// with executeJavaScript("window.splash.status(...)" / "window.splash.done()").
(function () {
  const root = document.querySelector(".splash");
  const statusEl = document.getElementById("status");
  const params = new URLSearchParams(location.search);
  const TEXTS = {
    ru: { starting: "Запускаю тренера…", slow: "Первый запуск бывает дольше обычного…", ready: "Готово" },
    en: { starting: "Starting the coach…", slow: "The first start takes a little longer…", ready: "Ready" }
  };
  const lang = params.get("lang") === "ru" ? "ru" : "en";
  document.documentElement.lang = lang;
  const INTRO_MS = 900;
  const started = Date.now();
  let finished = false;

  function status(key) {
    const text = TEXTS[lang][key] || "";
    if (statusEl.textContent !== text) {
      statusEl.textContent = text;
    }
  }

  // After the intro the logo waits for the service (unless it is ready already).
  setTimeout(() => {
    if (!finished) {
      root.dataset.phase = "wait";
    }
  }, INTRO_MS);
  status("starting");

  window.splash = {
    status,
    // Returns how long main should wait before closing: the rest of the intro
    // (so the logo is always seen whole) plus the exit animation.
    done() {
      finished = true;
      status("ready");
      const rest = Math.max(0, INTRO_MS - (Date.now() - started));
      setTimeout(() => {
        root.dataset.phase = "done";
      }, rest);
      return rest + 480;
    }
  };
})();
