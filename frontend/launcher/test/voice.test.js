const assert = require("node:assert/strict");
const test = require("node:test");

const { createSpeaker, pickVoice, speechText, wantsSpeech } = require("../overlay/voice");

const VOICES = [
  { name: "Microsoft David", lang: "en-US", localService: true },
  { name: "Google русский", lang: "ru-RU", localService: false },
  { name: "Microsoft Irina", lang: "ru-RU", localService: true }
];

function fakeSynth() {
  const synth = {
    speaking: false,
    spoken: [],
    cancels: 0,
    getVoices: () => VOICES,
    speak(utterance) {
      synth.spoken.push(utterance);
    },
    cancel() {
      synth.cancels += 1;
    }
  };
  return synth;
}

class Utterance {
  constructor(text) {
    this.text = text;
  }
}

function speaker(synth, clock) {
  return createSpeaker({ synth, Utterance, now: () => clock.t });
}

test("modes decide which advice is spoken", () => {
  assert.equal(wantsSpeech("off", "urgent"), false);
  assert.equal(wantsSpeech("urgent", "urgent"), true);
  assert.equal(wantsSpeech("urgent", "coaching"), false);
  assert.equal(wantsSpeech("all", "coaching"), true);
  assert.equal(wantsSpeech("loud", "urgent"), false);
});

test("a local voice of the UI language is preferred", () => {
  assert.equal(pickVoice(VOICES, "ru").name, "Microsoft Irina");
  assert.equal(pickVoice(VOICES, "en").name, "Microsoft David");
  assert.equal(pickVoice(VOICES.slice(0, 1), "ru"), null);
});

test("long actions are cut at a word boundary", () => {
  const text = `${"Farm the safe lane jungle camps ".repeat(8)}now`;
  const spoken = speechText(text);
  assert.ok(spoken.length <= 160 && !spoken.endsWith(" "));
  assert.equal(speechText("  Back   off.  "), "Back off.");
});

test("each advice is spoken once, tips keep a gap, urgent interrupts", () => {
  const synth = fakeSynth();
  const clock = { t: 0 };
  const voice = speaker(synth, clock);
  const tip = { key: "a", text: "Stack the camp", adviceMode: "coaching", mode: "all", locale: "ru" };

  assert.equal(voice.say(tip), "spoken");
  assert.equal(synth.spoken[0].voice.name, "Microsoft Irina");
  assert.equal(voice.say(tip), "same");

  clock.t = 1000;
  assert.equal(voice.say({ ...tip, key: "b" }), "too_soon");
  clock.t = 5000;
  synth.speaking = true;
  assert.equal(voice.say({ ...tip, key: "b" }), "busy");

  assert.equal(voice.say({ ...tip, key: "c", adviceMode: "urgent", text: "Back off" }), "spoken");
  assert.equal(synth.cancels, 1);
  assert.equal(synth.spoken.at(-1).text, "Back off");
});

test("urgent-only mode ignores tips; no voice for the language is reported", () => {
  const synth = fakeSynth();
  const voice = speaker(synth, { t: 0 });
  assert.equal(voice.say({ key: "a", text: "Stack", adviceMode: "coaching", mode: "urgent", locale: "ru" }), "off");
  synth.getVoices = () => VOICES.slice(0, 1);
  assert.equal(voice.say({ key: "b", text: "Отходите", adviceMode: "urgent", mode: "urgent", locale: "ru" }), "no_voice");
  assert.equal(synth.spoken.length, 0);
});
