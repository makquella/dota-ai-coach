// Spoken advice (optional): Chromium's speechSynthesis with the voices of the
// system (Windows: SAPI voices such as "Microsoft Irina" for Russian). Works
// even when exclusive fullscreen hides the card. Pure rules + a small speaker
// so the rules run in node tests; loaded as a plain script by the overlay and
// the control panel (window.OverlayVoice).
(function attach(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    root.OverlayVoice = api;
  }
})(typeof self !== "undefined" ? self : this, () => {
  const MODES = ["off", "urgent", "all"];
  // Tips never talk over each other; an urgent one interrupts a tip.
  const MIN_GAP_MS = 4000;
  const MAX_CHARS = 160;

  function normalizeMode(mode) {
    return MODES.includes(mode) ? mode : "off";
  }

  function wantsSpeech(mode, adviceMode) {
    const current = normalizeMode(mode);
    return current === "all" || (current === "urgent" && adviceMode === "urgent");
  }

  // A voice for the language: local (offline) voices first, then any.
  function pickVoice(voices, locale) {
    const prefix = String(locale || "en").toLowerCase().slice(0, 2);
    const matching = (voices || []).filter((voice) => String(voice.lang || "").toLowerCase().startsWith(prefix));
    return matching.find((voice) => voice.localService) || matching[0] || null;
  }

  // Only the action is spoken: the reason is for reading.
  function speechText(action) {
    const text = String(action || "").replace(/\s+/g, " ").trim();
    if (text.length <= MAX_CHARS) {
      return text;
    }
    const cut = text.slice(0, MAX_CHARS);
    const end = Math.max(cut.lastIndexOf(". "), cut.lastIndexOf(", "), cut.lastIndexOf(" "));
    return cut.slice(0, end > 40 ? end : MAX_CHARS).trim();
  }

  // synth: speechSynthesis-like ({speak, cancel, speaking, getVoices});
  // Utterance: SpeechSynthesisUtterance-like constructor.
  function createSpeaker({ synth, Utterance, now = () => Date.now() }) {
    let lastKey = "";
    let lastAt = -Infinity;

    // Returns what happened: "spoken" | "off" | "same" | "busy" | "too_soon" | "no_voice" | "empty".
    // repeat: asked for by the player (hotkey): spoken whenever the voice is
    // on at all, right away, even if it was just said.
    function say({ key, text, adviceMode, mode, locale, volume = 1, repeat = false }) {
      if (!synth || !Utterance || !(repeat ? normalizeMode(mode) !== "off" : wantsSpeech(mode, adviceMode))) {
        return "off";
      }
      if (key && key === lastKey && !repeat) {
        return "same";
      }
      const spoken = speechText(text);
      if (!spoken) {
        return "empty";
      }
      const urgent = adviceMode === "urgent" || repeat;
      if (!urgent && (synth.speaking || now() - lastAt < MIN_GAP_MS)) {
        return synth.speaking ? "busy" : "too_soon";
      }
      const voice = pickVoice(synth.getVoices(), locale);
      if (!voice) {
        return "no_voice";
      }
      if (urgent) {
        synth.cancel();
      }
      const utterance = new Utterance(spoken);
      utterance.lang = voice.lang;
      try {
        utterance.voice = voice;
      } catch {
        // Not a real SpeechSynthesisVoice: the language picks the voice.
      }
      utterance.volume = Math.min(1, Math.max(0, Number(volume)));
      utterance.rate = 1.05;
      synth.speak(utterance);
      lastKey = key || "";
      lastAt = now();
      return "spoken";
    }

    function reset() {
      lastKey = "";
      lastAt = -Infinity;
      if (synth) {
        synth.cancel();
      }
    }

    return { say, reset };
  }

  return { MODES, MIN_GAP_MS, createSpeaker, normalizeMode, pickVoice, speechText, wantsSpeech };
});
