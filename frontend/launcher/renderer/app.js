// Control panel: one status line (what is going on + what to do), three
// cards (current match, recent advice, overlay settings) and a collapsed
// "For developers" section with every other tool (service, GSI config, live
// GSI, recordings, replay demos, Deep Review, logs). Texts follow the system
// language (ru/en) sent by the main process as status.locale.

const I18N = {
  en: {
    tabHome: "Home",
    tabMatches: "Matches",
    tabProgress: "Progress",
    tabSettings: "Settings",
    adviceSettingsTitle: "Advice",
    languageTitle: "Language",
    languageHint: "Advice, reviews and the whole app",
    languageAuto: "Auto",
    dataTitle: "Match history",
    odTitle: "Faster match history",
    odPlaceholder: "OpenDota key",
    odSave: "Save",
    odGet: "Get a key on opendota.com",
    odClear: "Remove key",
    odHintOff: "Your match history comes from OpenDota, a free Dota statistics site. Everything works without a key, just slower. A free key from opendota.com makes it faster; it stays on this computer.",
    odHintOn: (hint) => `Key ${hint} saved: your matches load faster.`,
    odHintEnv: "A key is already set in the app's settings file.",
    odBad: "This does not look like an OpenDota key.",
    appTitle: "Main",
    service: "Coach",
    serviceStates: { running: "running", starting: "starting…", stopping: "stopping…", stopped: "stopped" },
    status: {
      loadingTitle: "Starting the coach…",
      loadingHint: "Usually takes a couple of seconds.",
      backendDownTitle: "The coach is stopped",
      backendDownHint: "No advice while it is stopped. Press «Start»: it takes a couple of seconds.",
      gsiErrorTitle: "Could not connect to Dota",
      gsiErrorHint: "No access to the Dota folder. Point to the game folder manually.",
      noDotaTitle: "Dota not found",
      noDotaHint: "Dota 2 was not found in Steam. Point to the game folder and the app does the rest.",
      noGsiTitle: "Connect Dota",
      noGsiHint: "Press «Connect»: the app puts a small file into the Dota folder, and through it the game tells the coach what happens in your match.",
      notRunningTitle: "Dota is not running",
      notRunningHint: "Start Dota 2; the coach connects by itself. You can close this window.",
      connectedTitle: "Dota is connected, waiting for a match",
      noDataTitle: "Dota is running, no data from it yet",
      waitingHintConnected: "Advice starts as soon as a match with your hero begins.",
      waitingHintNoData: "If a match is already on, restart Dota: it connects to the coach only when it starts.",
      launchOptionTitle: "Dota is not sending game data",
      launchOptionHint: "Dota needs one launch option for that. In Steam: right-click Dota 2 → Properties → Launch options, paste -gamestateintegration (the button copies it), then restart the game.",
      inGameTitle: (hero, clock) => `In game: ${[hero, clock].filter(Boolean).join(", ")}`,
      inGameHint: "Advice appears over the game while Dota is the active window.",
      inGameOverlayOff: "Advice over the game is off: it shows only here.",
      demoTitle: (preset) => `Replay demo${preset ? `: ${preset}` : ""}`,
      demoHint: "The overlay shows advice from a recorded match.",
      fullscreenTitle: "Advice is hidden by fullscreen",
      fullscreenHint:
        "Dota runs in exclusive fullscreen, where no window can be drawn on top. In Dota: Settings → Video → Display mode → Borderless window. Or turn on the voice in Settings → Advice: it is heard in any mode."
    },
    actions: {
      start: "Start the coach",
      install: "Connect",
      chooseDota: "Choose Dota folder",
      fullscreenSeen: "I can see the advice",
      copyLaunchOption: "Copy option",
      copied: "Copied"
    },
    matchTitle: "Current match",
    coverageSafety: "The full advice is for 64 heroes (carries, mids, offlaners and supports); on this hero the coach gives survival advice, map timers and role tips.",
    coverageSupport: "Support advice: your own saves, fights and objectives, stacks, pulls, wards and save items. No farm or item advice: the gold goes to your cores.",
    statHero: "Hero",
    statClock: "Match time",
    statStage: "Phase",
    statData: "Link to the game",
    dataFresh: (s) => `updated ${s} s ago`,
    matchEmptyTitle: "No match right now",
    matchEmptyHint: "Hero and time show up here when a match starts.",
    offlineTitle: "The coach is not running",
    offlineHint: "Start it to see your match here.",
    adviceTitle: "Recent advice",
    adviceWhy: "Why this advice?",
    adviceEmptyTitle: "No advice yet",
    adviceEmptyHint: "Advice shows up here as it appears over the game.",
    priority: { high: "urgent", urgent: "urgent", medium: "important", low: "tip", safe: "calm" },
    stages: { laning: "Lanes", "post-laning": "After the lanes", macro: "Mid and late game" },
    overlayTitle: "Advice card",
    overlayShow: "Show advice over the game",
    overlayReason: {
      off: "Off",
      positioning: "Shown so you can move it",
      demo: "Showing the replay demo",
      no_tracking: "Always visible: on this system the app cannot tell whether Dota is open",
      dota_not_running: "Appears in a match, over Dota",
      dota_not_focused: "Hidden while Dota is in the background",
      no_match: "Appears when a match starts",
      in_game: "On screen now"
    },
    overlayPosition: "Where on the screen",
    positionHint: "Away from the minimap and the hero panel",
    positionCustom: "Custom position, pick a preset to reset",
    posLeft: "Left",
    posRight: "Right",
    posBottom: "Bottom",
    overlaySize: "Card size",
    overlaySizeHint: "Larger on big and high-resolution screens",
    overlayTimers: "Timer strip",
    overlayTimersHint: "Always under the card: how long until the next runes, stacks, Roshan and Aegis for your role",
    overlayCompact: "Short advice",
    overlayCompactHint: "Only what to do, without the reason: less to read during a fight",
    sizeSmall: "Small",
    sizeNormal: "Normal",
    sizeLarge: "Large",
    frequencyTitle: "How often",
    frequencyCalm: "Less",
    frequencyNormal: "Normal",
    frequencyActive: "More",
    roleTitle: "Your role",
    roleAuto: "Auto",
    roleCarry: "Carry",
    roleMid: "Mid",
    roleOfflane: "Offlane",
    roleSupport: "Support",
    roleHint: {
      auto: "The coach works it out from your lane in the first minutes. Pick a role if it gets it wrong",
      carry: "Timers and tips for a carry",
      mid: "Runes and timers for a mid player",
      offlane: "Shrines, lotuses and timers for an offlaner",
      support: "Stacks, wards and runes for a support; farm advice is off"
    },
    roleNames: { carry: "carry", mid: "mid", offlane: "offlane", support: "support" },
    roleSource: {
      setting: "chosen in Settings",
      lane: "from your lane",
      history: "from your past games on this hero",
      hero: "usual for this hero"
    },
    roleNote: (role, source) => `Role: ${role}, ${source}.`,
    mapHintsTitle: "Map timers",
    mapHintsHint: "A reminder on the card 20 s before runes, shrines, Tormentor, stacks and wards — only the ones your role needs. Off also hides the timer strip",
    frequencyHint: {
      calm: "Twice the pause between tips; urgent advice is never delayed",
      normal: "Balanced pauses between tips",
      active: "Shorter pauses between tips; urgent advice as always"
    },
    voiceTitle: "Voice",
    voiceOff: "Off",
    voiceUrgent: "Urgent",
    voiceAll: "All",
    voiceTest: "Listen",
    voiceHint: {
      off: "Advice is only shown, not spoken",
      urgent: "Speaks urgent advice; heard even in exclusive fullscreen. Ctrl+Alt+R repeats",
      all: "Speaks every piece of advice; heard even in exclusive fullscreen. Ctrl+Alt+R repeats"
    },
    voiceNoVoice: "No English voice in the system: Windows Settings → Time & language → Speech",
    voiceSample: "Back off: the enemy is missing from the map.",
    overlayMove: "Move by hand",
    moveHint: "Shows the card so you can drag it anywhere",
    moveActiveHint: "Drag the card, then press Done",
    moveStart: "Move",
    moveDone: "Done",
    statsTitle: "Help improve the advice",
    statsHint: "Once a day the app sends anonymous counts: which advice was shown and which warnings came before a death. No heroes, matches, nickname or keys. Off by default.",
    statsPreview: "What is sent (today so far)",
    statsTerms: "Kept for a year.",
    statsOff: "Off: nothing is sent.",
    statsOn: "On: the first upload is tomorrow, with today's counts.",
    statsSent: (date) => `On. Last sent ${date}.`,
    statsPreviewLoading: "Collecting…",
    statsPreviewFailed: "The coach is not running: nothing to show.",
    serverDelete: "Delete my data on the server",
    serverDeleteConfirm: "Delete for sure? Press again",
    serverDeleted: "Deleted: problem reports, shared links and statistics of this computer are gone from the server.",
    serverDeleteFailed: (code) => `Could not delete (${code}): check the internet and try again.`,
    discordTitle: "Status in Discord",
    discordHint: "Your Discord friends see «Playing Juggernaut · with the Wardly coach» while Dota runs",
    discordStates: {
      idle: "It appears once Dota is running.",
      connecting: "Connecting to Discord…",
      no_discord: "Discord not found: open the Discord app on this computer (the browser version cannot show it).",
      connected: "Discord connected. The status appears once Dota is running.",
      shown: "Shown in Discord. Friends do not see it? Discord → Settings → Activity Privacy → «Share your detected activities with others».",
      rejected: (error) => `Discord did not accept the status: ${error}`
    },
    settingsMore: "More settings",
    settingsPageTitle: "Settings",
    settingsPageSub: "Everything already works. Change only what you want to.",
    zoneNow: "Now",
    zoneNowHint: "The current match and the advice it got",
    zoneHistory: "Last matches",
    zoneHistoryHint: "Open one for its review",
    zoneWeek: "Your week",
    zoneWeekHint: "The last seven days against the seven before",
    zoneAllMatches: "All matches",
    zoneGame: "In the game",
    zoneGameHint: "What you see and hear during a match",
    zoneData: "After the match",
    zoneDataHint: "A review of every match in plain words, written by the AI coach",
    zoneApp: "App",
    zoneAppHint: "Language, start with Windows, updates",
    weeklyTitle: "The week in Discord",
    weeklyHint:
      "Every Monday the week's matches, results and average score are posted to a channel of your Discord server. You need the channel's webhook link: in Discord open the channel settings → Integrations → Webhooks → New webhook → Copy webhook URL, and paste it here.",
    weeklyInputLabel: "Webhook link",
    weeklyConnect: "Connect",
    weeklySendNow: "Send now",
    weeklyDisconnect: "Disconnect",
    weeklySending: "Sending…",
    weeklyConnected: (hint) => `Connected (${hint}). The week goes to Discord every Monday.`,
    weeklySent: (date) => `Last post: ${date}.`,
    weeklyEmpty: (date) => `${date}: no matches in that week, nothing was posted.`,
    weeklyNoMatchesNow: "No matches in the last seven days: nothing to post yet.",
    weeklyErrors: {
      bad_url: "This is not a Discord webhook link: it starts with https://discord.com/api/webhooks/.",
      webhook_gone: "The webhook was deleted in Discord: create a new one and connect it again.",
      rate_limited: "Discord asks to wait: try again in a minute.",
      offline: "No connection to Discord: check the internet.",
      backend_down: "The coach is not running yet: try again in a moment.",
      busy: "Already sending…",
      fallback: "Could not post: try again later."
    },
    autostart: "Start with Windows",
    autostartOn: "Wardly opens by itself when the computer starts and waits quietly next to the clock, so you never forget it before a game.",
    autostartOff: "Off: open Wardly yourself before you play. Turn it on and Wardly will open with the computer and wait quietly next to the clock.",
    autostartUnavailable: "Available in the installed app",
    updates: "Updates",
    updateCheck: "Check",
    updateInstall: "Restart and update",
    updateHint: {
      disabled: (v) => `Version ${v} · updates work in the installed app`,
      idle: (v) => `Version ${v} · updates install by themselves`,
      checking: (v) => `Version ${v} · checking…`,
      "up-to-date": (v) => `Version ${v} · up to date`,
      downloading: (v, next, pct) => `Downloading ${next}… ${pct}%`,
      ready: (v, next) => `Version ${next} is ready. It installs by itself once Dota is closed.`,
      blocked: (v, next) => `Version ${next} is ready. It installs after you close Dota.`,
      error: (v) => `Version ${v} · could not check for updates`
    },
    whatsNewTitle: (version) => `What's new in ${version}`,
    whatsNewOk: "Got it",
    inviteTitle: "Like Wardly?",
    inviteText: "Send the link to a friend: the app is free, and playing together it is easier to follow the advice.",
    inviteCopy: "Copy the link",
    inviteLater: "Not now",
    inviteCopied: "Link copied",
    tour: {
      next: "Next",
      back: "Back",
      skip: "Skip",
      done: "Start playing",
      count: (i, n) => `${i} of ${n}`,
      steps: {
        welcome: {
          title: "Hi! This is Wardly",
          text: "The coach watches your match with you: short advice over the game and out loud, and a review with what to fix after it. A quick look around takes a minute."
        },
        status: {
          title: "Status line",
          text: "What is going on right now: is Dota found, is it sending data, is a match on. When something needs you, the button on the right does it."
        },
        setup: {
          title: "Getting started",
          text: "What is set up and what is left. Most steps do themselves; the first match with the app finishes the list."
        },
        match: {
          title: "Current match",
          text: "Your hero, the match time and the advice the coach gave. The advice itself appears over the game: you do not need to look here while playing."
        },
        matches: {
          title: "Matches",
          text: "Every match with a review: a score by area, where you died, the item timings and what to fix first. The review of a match is ready a minute or two after it ends."
        },
        progress: {
          title: "Progress",
          text: "How you play over the last games: the trends, the mistakes that repeat, your heroes, and a goal to work on."
        },
        settings: {
          title: "Card over the game",
          text: "Where the advice card sits over the game and how big it is. You can drag it by hand."
        },
        voice: {
          title: "Advice and voice",
          text: "How often the coach speaks, your role for the map timers, and the voice: it reads the advice out loud, which also works in exclusive fullscreen."
        },
        done: {
          title: "All set",
          text: "Start Dota and play a match: the first advice appears by itself. This tour can be opened again in Settings → Help."
        }
      }
    },
    summaryTitle: "Summary",
    sessionTitle: "Your evening",
    sessionHide: "Hide",
    tourTitle: "How to use Wardly",
    tourHint: "A short tour of the app, one minute",
    tourStart: "Show",
    whatsNew: {
      "0.29.2": [
        "Items against the enemy heroes: dying under Beastmaster's Primal Roar, Doom or Duel brings a Linken's Sphere tip that says why; Monkey King Bar against evasion, Spirit Vessel against healing, Dust for a support against invisible heroes.",
        "An unlearned Blink no longer counts as on cooldown, and «you died with Blink ready» needs two free seconds to press it.",
        "Repeated low-HP cards say how many times it happened and ask to heal up fully."
      ],
      "0.29.1": [
        "A mid gets the power rune timer until minute 20, not all game, and before level 6 with a Bottle the hint says to keep the rune in it for a kill."
      ],
      "0.29.0": [
        "The match review is shorter: past the three main points, the other remarks and the long list of deaths open with «Show more».",
        "The health line under each death says what it is, and «Net worth» is named plainly."
      ],
      "0.28.0": [
        "The first advice after a death names the lane or part of the map where you died, or how fast the kill came, instead of «plan a safer route».",
        "Supports: the «no save item» tip names the save item most bought on your hero and how much gold it still needs; the ward tip says where to put it (your lane's river, Roshan's pit, your own or the enemy jungle by the score).",
        "A lane under a good farm pace gets the numbers: «Recover farm: 12 last hits at minute 5, a good pace is 18+»."
      ],
      "0.27.0": [
        "The advice after a death says how many times you have died, lately or this game, instead of the same «change your route» line."
      ],
      "0.26.0": [
        "The match review has a «Skill order» card: which skill you maxed first and how pro players level your hero."
      ],
      "0.25.0": [
        "The farm cards put the numbers on the main line: your gold per minute and last hits, or how far behind a good pace you are.",
        "Advice that only changed its numbers no longer repeats every two minutes."
      ],
      "0.24.0": [
        "Which talent to take: when a talent row opens, the coach names the one pro players take on your hero."
      ],
      "0.23.0": [
        "Where the point goes: after a level-up the coach names the skill pro players level on your hero, with the whole order.",
        "The game plan shows the pro skill order, and the review says when you maxed a different skill first."
      ],
      "0.22.0": [
        "Skill points: the coach names your ultimate at 6/12/18 and the talent at 10/15/20/25 when a point is left unspent.",
        "A situational item: two deaths under stuns → Black King Bar, two burst deaths → Aeon Disk, with the reason and the gold still needed.",
        "Less banal advice: a kill streak, the kill score gap or your pace in numbers instead of the same «farm safely»."
      ],
      "0.21.0": [
        "Settings are rebuilt: five clear groups, bigger text, fewer buttons, and a plain line under every setting. Moving to another computer now explains itself step by step.",
        "«Why this advice?» under every advice on Home and in the review: what the coach saw.",
        "«What does this mean?» for the match score, the rank comparison and the focus, and no more technical words across the app."
      ],
      "0.20.0": [
        "Full advice for 25 supports (positions 4 and 5) with their own saves, reminders to place the wards in your bag and to get a save item, and a support review: your save item's timing and the wards you placed.",
        "Overlay 2.0: a timer strip under the card (runes, stacks, Roshan, Aegis for your role), a compact card and a soft fade-in — Settings → Overlay.",
        "A new Home: one card with your last match, today, streaks and focus. Progress gets a Goals zone."
      ],
      "0.19.0": [
        "Your evening: after two or more matches, Home sums up the sitting once Dota is closed, with a text to copy for friends.",
        "Progress shows where you die over the last 20 matches, and your hero's key item timing game by game.",
        "A short tour of the app (Settings → App), and the status line says plainly whether Dota's data reaches the coach."
      ],
      "0.18.0": [
        "Full advice for 18 more heroes: 8 mids (Shadow Fiend, Storm Spirit, Queen of Pain, Puck and others) and 10 offlaners (Axe, Mars, Legion Commander, Centaur and others).",
        "The coach knows their own saves (Blink, Ball Lightning, Refraction, Guardian Sprint…), and an offlaner's farm is measured against an offlaner's pace, not a carry's."
      ],
      "0.17.0": [
        "Optional anonymous statistics (Settings → App, off by default): which advice was shown and which warnings came before a death, to make the advice better. «What is sent» shows the exact text.",
        "«Delete my data on the server» removes your problem reports, shared links and statistics in one press."
      ],
      "0.16.0": [
        "In a review, «Watch» next to a death or a key moment copies the replay command that jumps 10 s before it.",
        "The match chart shows your best match on this hero as a dashed line.",
        "Home: streak goals (5 matches in a row with 5 deaths or fewer) and a gentle note after 3 losses in a row.",
        "Progress: heroes to play more and heroes to park, against your rank."
      ],
      "0.15.0": [
        "Roshan and Aegis timers: the respawn window after a kill, and your Aegis warns a minute before it expires.",
        "While you wait to respawn: how you died, what was left unpressed, what to buy now.",
        "No more «wait out the disable» when there is nothing to press after the stun."
      ],
      "0.14.0": [
        "Advice knows your hero: Blink to get out, Blade Fury to walk out of a fight, and how many seconds until your escape is back.",
        "The match map rings the places where you keep dying, with a route tip."
      ],
      "0.13.0": [
        "Advice names what to press right now: Force Staff to get out, Magic Wand with its charges, Black King Bar the moment a stun ends.",
        "After a death: the rescue item you left unpressed and the place where you keep dying."
      ],
      "0.12.0": [
        "Every tab is split into clear areas: what to look at first, then the details.",
        "Your week on Home: the score against the week before and a chart of every match.",
        "Farm advice for carries names your next item, the gold it needs and how long to farm it.",
        "Fixed: some reviews stayed on «Loading the match» forever."
      ],
      "0.11.0": [
        "The app uses the whole window: side navigation, two columns, both teams side by side.",
        "Last matches on Home, score rings in reviews and the match table.",
        "More in-game tips for every role: mid rotations and last hits, offlane hard lanes, support pulls, your key item's timing.",
        "Hard matchups in the game plan."
      ],
      "0.10.0": [
        "The week in Discord: every Monday your matches, score and heroes of the week go to your server's channel. Settings → App → The week in Discord.",
        "The Week card on Home shows the heroes you played.",
        "Problem reports no longer include the delete tokens of your shared links."
      ],
      "0.9.0": [
        "Status in Discord: your friends see «Playing <hero> · with the Wardly coach». Switch it off in Settings → App.",
        "Links to reviews and progress are shorter now: luhovyimvp.dev/r/…",
        "The website in the logo's colours."
      ],
      "0.8.0": [
        "Death reviews: HP in the last 20 seconds and the saving item that was ready but not pressed.",
        "Progress: your build on the hero — when items come in your wins and in your losses.",
        "After a match the overlay shows the summary right on the score screen.",
        "Move your history to another computer with a one-time code."
      ],
      "0.7.0": [
        "Progress → Share: a link to a page with your progress — matches, wins, averages, top heroes, what goes well and what to work on.",
        "A new start-up splash: the logo comes alive while the service starts."
      ],
      "0.6.1": [
        "Offlaner reviews: stuns and building damage against the enemy offlaner of the same match.",
        "The plan for the game shows your record on the hero next to its name.",
        "All versions and their changes are on the website: luhovyimvp.dev/changelog.html."
      ],
      "0.6.0": [
        "Role reviews: runes for a mid against the enemy mid, stacks and sentries for a support.",
        "Progress: your record against each enemy hero — who is hardest for you and whom you beat most.",
        "Ask the AI coach about your recent matches, not only one game.",
        "In game: a level-6 tip for a mid (rotation) and an offlaner (pressure)."
      ],
      "0.5.0": [
        "Dota AI Coach is now Wardly, with a new logo. Your history and settings stay.",
        "Progress → Compare with a friend: their public matches next to yours, with the heroes you both play.",
        "Share a review by link — with a preview in Discord and Telegram, no Steam ID or nickname.",
        "Settings → App → Match history: save everything to a file and load it back on any computer.",
        "The path on the match map no longer runs from a death to the fountain."
      ],
      "0.4.0": [
        "The match map is drawn on the real Dota minimap: your path, lane position, wards and deaths.",
        "Good-pace lines for gold and XP on the «Over the match» chart.",
        "A «Deaths» card: where, who killed you, unspent gold and the advice shown before each death.",
        "Mistakes that keep coming back are marked: «3 matches in a row».",
        "This week on Home: matches, score change, best match, the most frequent mistake and a 3-match plan for your focus."
      ],
      "0.3.0": [
        "Map timers on the overlay 20 s ahead: runes, wisdom shrines, lotuses, the Tormentor, neutral item tiers — only the ones your role needs.",
        "Your role is found from your lane in the first minutes (or chosen in Settings → Advice) and shown on Home.",
        "Support tips: stack a camp, take wards, leave the last hits to your carry. No carry farm advice on a support; the TP reminder works on every hero.",
        "«Send to developer» in the problem report: one click, with a note and a preview; keys, nickname and Steam ID are removed.",
        "Draft advice suggests only heroes of the position you played."
      ],
      "0.2.1": [
        "Match history no longer fails to sync when OpenDota answers slowly.",
        "The app asks OpenDota to parse your latest matches, so reviews get last hits at 10:00, the build and the chart.",
        "Draft advice suggests a hero of your role; the same-role opponent and counter items are right even without a parsed replay.",
        "Progress shows all five tiles in one row, and Home no longer cuts the hero's name."
      ],
      "0.2.0": [
        "A plan at the start of each match, and a focus: pick one mistake to work on — every review says whether you avoided it.",
        "«Ask the coach»: your own question about a match, answered from its data.",
        "Spoken advice, advice frequency, survival advice for every hero, reminders to carry a TP scroll and to spend gold while dead.",
        "Match map, this match against your usual numbers, match filters and PDF export.",
        "A check for Dota's -gamestateintegration launch option, without which no game data arrives."
      ]
    },
    setupTitle: "Getting started",
    setupHide: "Hide",
    setupCount: (done, total) => `${done} of ${total}`,
    setup: {
      service: ["The coach is running", "Starts with the app. If it stopped, restart the app."],
      dota: ["Dota 2 found", "Not in your Steam libraries: point to the game folder."],
      gsi: ["Connected to Dota", "A small file in the Dota folder: through it the game tells the coach what happens in your match."],
      launch: ["Dota shares the match", "Dota needs a launch option for it. In Steam: right-click Dota 2 → Properties → Launch options, paste -gamestateintegration."],
      data: ["Dota has talked to the coach", "Start Dota 2 (or restart it if it was running) and open any match, bots are fine."],
      account: ["Steam account linked", "Linked by itself in the first match, or enter it on the Matches tab."],
      ai: ["AI coach (optional)", "With a free Google key the AI writes a review of every match in plain words."]
    },
    setupActions: { dota: "Choose folder", gsi: "Connect", launch: "Copy", account: "Link", ai: "Set up" },
    reportTitle: "Report a problem",
    reportHint: "Something does not work? Press «Report» and describe it in a few words: the developer gets the app's log. Keys and passwords are cut out.",
    reportSave: "Save as a file instead",
    backupTitle: "Spare copy in a file",
    backupHint: "Saves all your matches and reviews into one file, for example before reinstalling Windows. Open it later in Wardly on any computer. Keys are not saved.",
    backupExport: "Save to file",
    backupImport: "Open a file",
    backupSaved: (count, file) => `Saved ${count} matches: ${file}`,
    backupLoaded: (added, linked) => `Loaded: ${added} new matches${linked ? ", account linked" : ""}. Nothing was overwritten.`,
    backupNotBackup: "This file is not a Wardly history backup.",
    backupNewer: "The backup was made by a newer version: update the app first.",
    backupFailed: "Could not do it: the coach is not running or the disk is not available.",
    transferTitle: "Move to another computer",
    zoneMyData: "Your matches",
    zoneMyDataHint: "So your history is not lost when you change computers",
    zoneHelp: "Help",
    zoneHelpHint: "How to use the app, and what to do if something breaks",
    transferIntro: "Installed Wardly on a new computer? Move your matches and reviews there, it takes a minute.",
    transferStep1: "Here, press «Get a code».",
    transferStep2: "On the new computer: Wardly → Settings → Move to another computer → «I have a code», and type it in.",
    transferHave: "I have a code",
    transferHint: "The code works for 15 minutes. Your matches travel encrypted; keys are not moved.",
    transferSend: "Get a code",
    transferReceive: "Load",
    transferInputLabel: "Code from the other computer",
    transferSending: "Encrypting and sending…",
    transferReady: (matches, time) => `The code works until ${time}. Type it in on the new computer (matches: ${matches}).`,
    transferReceiving: "Downloading and decrypting…",
    transferErrors: {
      bad_code: "Check the code: three groups of four letters and digits, as shown on the other computer.",
      not_found: "No history under this code: it has expired (15 minutes) or was already loaded. Get a new code.",
      too_big: "The history is too big to send by code: save it to a file instead.",
      rate_limited: "Too many tries for now: wait an hour or move it with a file.",
      disabled: "Moving by code is switched off right now: use a file.",
      not_backup: "The code opened something that is not a Wardly history.",
      offline: "No connection to the server: check the internet.",
      fallback: "Could not do it: try again or use a file."
    },
    reportSaving: "Collecting…",
    reportSaved: (name) => `Saved: ${name}. Send this file to the developer.`,
    reportFailed: "Could not save the file",
    reportSend: "Report",
    reportNoteLabel: "What happened? (optional)",
    reportNotePlaceholder: "For example: no advice shows in a match",
    reportPreview: "What will be sent",
    reportPreviewLoading: "Collecting the report…",
    reportTerms: "Keys are cut out. The report is kept for 180 days.",
    reportPrivacy: "Privacy",
    reportSendNow: "Send",
    reportCancel: "Cancel",
    reportSending: "Sending…",
    reportSentId: (id) => `Sent. Report number: ${id}. Mention it if you write to the developer.`,
    reportQueued: "No internet right now. The report will be sent by itself later.",
    reportQueuedCount: (count) => `Waiting to be sent: ${count}`,
    reportLast: (id) => `Last report: ${id}`,
    reportRefused: (name) =>
      name ? `The server did not accept the report. Saved a file instead: ${name}.` : "The server did not accept the report.",
    devTitle: "For developers",
    devHint: "Technical tools: the coach process, the link to the game, logs. You do not need them to play",
    factBackend: "Service",
    factDota: "Dota",
    factOverlay: "Overlay",
    factDemo: "Demo",
    factRecording: "Recording",
    factGsiConfig: "GSI config",
    factMode: "Mode",
    groupBackend: "Service",
    startBackend: "Start",
    restartBackend: "Restart",
    stopBackend: "Stop",
    showOverlay: "Show overlay",
    hideOverlay: "Hide overlay",
    hotkeys: "Ctrl+Alt+O on/off · Ctrl+Alt+L move · Ctrl+Alt+M mute 5 min · Ctrl+Alt+R repeat advice · Ctrl+Alt+1/2/3 left/right/bottom · Ctrl+Alt+D debug line",
    groupGsi: "GSI config",
    gsiPathPlaceholder: "Custom gamestate_integration folder (optional)",
    chooseFolder: "Choose",
    checkGsi: "Check",
    installGsi: "Install",
    gsiPath: (p, e) => `Config: ${p}${e ? `\nEndpoint: ${e}` : ""}`,
    gsiPathMissing: "Config not found. Choose the gamestate_integration folder and install.",
    gsiEndpoint: (e) => (e ? `Endpoint: ${e}` : "Endpoint: waiting for the service port…"),
    groupLive: "Live GSI",
    kvConnection: "Connection",
    kvLast: "Last data",
    kvHero: "Hero",
    kvTime: "Game time",
    kvStage: "Stage",
    liveConnected: "connected",
    liveWaiting: "waiting / stale",
    liveUnavailable: "service unavailable",
    liveAdvice: (a) => `Current advice: ${a}`,
    liveAdviceNone: "Current advice: none yet",
    liveAdviceLast: (t) => `Current advice: last shown at ${t}`,
    liveMissing: (m) => `Missing important fields: ${m}`,
    none: "none",
    checkLive: "Check",
    startRecording: "Record",
    stopRecording: "Stop recording",
    openRecords: "Recordings",
    groupDemo: "Replay demo",
    demoHint: "Plays recorded match states into the service; the overlay shows without Dota.",
    demoBusy: "A demo is already running. Stop it first.",
    runDemo: "Run demo",
    presetPl: "Phantom Lancer 20–30",
    presetJugg: "Juggernaut 10–20",
    deepReview: "Deep Review",
    stopDemo: "Stop",
    openResults: "Results",
    groupLogs: "Logs",
    logClean: "Clean",
    logVerbose: "Verbose",
    copyLogs: "Copy",
    clearLogs: "Clear",
    openLogs: "Logs folder",
    dotaStates: { not_found: "not found", waiting: "waiting for a match", in_game: "in game" },
    gsiConfigStates: { installed: "installed", "not found": "not found", error: "error", unknown: "unknown" },
    modes: { "Live GSI": "Live GSI", "Replay Demo": "Replay demo" },
    on: "on",
    off: "off",
    shown: "on screen",
    hidden: "hidden",
    running: "running",
    stopped: "stopped"
  },
  ru: {
    tabHome: "Главная",
    tabMatches: "Матчи",
    tabProgress: "Прогресс",
    tabSettings: "Настройки",
    adviceSettingsTitle: "Советы",
    languageTitle: "Язык",
    languageHint: "Советы, разборы и всё приложение",
    languageAuto: "Как в системе",
    dataTitle: "История матчей",
    odTitle: "Быстрая загрузка истории",
    odPlaceholder: "Ключ OpenDota",
    odSave: "Сохранить",
    odGet: "Получить ключ на opendota.com",
    odClear: "Удалить ключ",
    odHintOff: "Историю ваших матчей приложение берёт с OpenDota — бесплатного сайта статистики Доты. Без ключа всё работает, просто медленнее. Бесплатный ключ с opendota.com ускорит загрузку; он хранится только на этом компьютере.",
    odHintOn: (hint) => `Ключ ${hint} сохранён: матчи загружаются быстрее.`,
    odHintEnv: "Ключ уже задан в файле настроек приложения.",
    odBad: "Это не похоже на ключ OpenDota.",
    appTitle: "Основное",
    service: "Тренер",
    serviceStates: { running: "работает", starting: "запускается…", stopping: "останавливается…", stopped: "остановлен" },
    status: {
      loadingTitle: "Запускаем тренера…",
      loadingHint: "Обычно это пара секунд.",
      backendDownTitle: "Тренер остановлен",
      backendDownHint: "Пока он остановлен, подсказок не будет. Нажмите «Запустить» — это пара секунд.",
      gsiErrorTitle: "Не получилось подключиться к Доте",
      gsiErrorHint: "Нет доступа к папке Доты. Укажите папку игры вручную.",
      noDotaTitle: "Дота не найдена",
      noDotaHint: "Не нашли Dota 2 в Steam. Укажите папку игры — остальное приложение сделает само.",
      noGsiTitle: "Подключите Доту",
      noGsiHint: "Нажмите «Подключить»: приложение положит в папку Доты маленький файл, через который игра сообщает тренеру, что происходит в матче.",
      notRunningTitle: "Дота не запущена",
      notRunningHint: "Запустите Dota 2 — тренер подключится сам. Это окно можно закрыть.",
      connectedTitle: "Связь с Дотой есть, ждём матч",
      noDataTitle: "Дота запущена, данных от неё пока нет",
      waitingHintConnected: "Подсказки начнутся, как только стартует матч с вашим героем.",
      waitingHintNoData: "Если матч уже идёт, перезапустите Доту: к тренеру она подключается только при запуске.",
      launchOptionTitle: "Дота не передаёт данные игры",
      launchOptionHint: "Для этого Доте нужен параметр запуска. В Steam: правой кнопкой по Dota 2 → Свойства → Параметры запуска, вставьте -gamestateintegration (кнопка его скопирует) и перезапустите игру.",
      inGameTitle: (hero, clock) => `В игре: ${[hero, clock].filter(Boolean).join(", ")}`,
      inGameHint: "Подсказки появляются поверх игры, пока окно Доты активно.",
      inGameOverlayOff: "Подсказки поверх игры выключены — они видны только здесь.",
      demoTitle: (preset) => `Демо-повтор${preset ? `: ${preset}` : ""}`,
      demoHint: "Оверлей показывает подсказки из записанного матча.",
      fullscreenTitle: "Подсказки не видны из-за полноэкранного режима",
      fullscreenHint:
        "Дота запущена в эксклюзивном полноэкранном режиме — поверх него окна не рисуются. В Доте: Настройки → Видео → режим экрана «Окно без рамки» (Borderless window). Или включите голос в «Настройки → Советы» — его слышно в любом режиме."
    },
    actions: {
      start: "Запустить тренера",
      install: "Подключить",
      chooseDota: "Указать папку Доты",
      fullscreenSeen: "Подсказки видны",
      copyLaunchOption: "Скопировать параметр",
      copied: "Скопировано"
    },
    matchTitle: "Текущий матч",
    coverageSafety: "Полные подсказки — для 64 героев (керри, мид, хардлайн, саппорты); на этом герое тренер подсказывает по выживанию, таймерам карты и роли.",
    coverageSupport: "Советы саппорта: свои спасения, драки и цели, стаки, пулы, варды и спасающие предметы. Без советов по фарму и предметам — золото достаётся корам.",
    statHero: "Герой",
    statClock: "Время матча",
    statStage: "Этап",
    statData: "Связь с игрой",
    dataFresh: (s) => `обновлено ${s} с назад`,
    matchEmptyTitle: "Матч не идёт",
    matchEmptyHint: "Герой и время появятся здесь, когда начнётся матч.",
    offlineTitle: "Тренер не запущен",
    offlineHint: "Запустите его, чтобы видеть здесь свой матч.",
    adviceTitle: "Последние подсказки",
    adviceWhy: "Почему этот совет?",
    adviceEmptyTitle: "Подсказок пока нет",
    adviceEmptyHint: "Здесь появятся подсказки, которые показывались поверх игры.",
    priority: { high: "срочно", urgent: "срочно", medium: "важно", low: "совет", safe: "спокойно" },
    stages: { laning: "Линии", "post-laning": "После линий", macro: "Середина и конец игры" },
    overlayTitle: "Карточка с подсказками",
    overlayShow: "Показывать подсказки поверх игры",
    overlayReason: {
      off: "Выключено",
      positioning: "Показан, чтобы его можно было переместить",
      demo: "Показывает демо-повтор",
      no_tracking: "Всегда виден: на этой системе приложение не видит, открыта ли Дота",
      dota_not_running: "Появится в матче поверх Доты",
      dota_not_focused: "Скрыт, пока Дота в фоне",
      no_match: "Появится, когда начнётся матч",
      in_game: "Сейчас на экране"
    },
    overlayPosition: "Где на экране",
    positionHint: "В стороне от миникарты и панели героя",
    positionCustom: "Своё положение — выберите вариант, чтобы вернуть",
    posLeft: "Слева",
    posRight: "Справа",
    posBottom: "Снизу",
    overlaySize: "Размер карточки",
    overlaySizeHint: "Крупнее — для больших экранов и высокого разрешения",
    overlayTimers: "Полоса таймеров",
    overlayTimersHint: "Всегда под карточкой: сколько осталось до ближайших рун, стаков, Рошана и Аегиса для вашей роли",
    overlayCompact: "Короткие подсказки",
    overlayCompactHint: "Только что делать, без объяснения: меньше читать во время драки",
    sizeSmall: "Мелкий",
    sizeNormal: "Обычный",
    sizeLarge: "Крупный",
    frequencyTitle: "Частота советов",
    frequencyCalm: "Реже",
    frequencyNormal: "Обычно",
    frequencyActive: "Чаще",
    roleTitle: "Ваша роль",
    roleAuto: "Авто",
    roleCarry: "Керри",
    roleMid: "Мид",
    roleOfflane: "Хардлайн",
    roleSupport: "Саппорт",
    roleHint: {
      auto: "Тренер сам поймёт по вашей линии в первые минуты. Выберите роль, если он ошибается",
      carry: "Таймеры и подсказки для керри",
      mid: "Руны и таймеры для мидера",
      offlane: "Святилища, лотосы и таймеры для хардлайнера",
      support: "Стаки, варды и руны для саппорта; советы про фарм выключены"
    },
    roleNames: { carry: "керри", mid: "мид", offlane: "хардлайн", support: "саппорт" },
    roleSource: {
      setting: "выбрана в настройках",
      lane: "по линии",
      history: "по вашим прошлым играм на герое",
      hero: "обычная для героя"
    },
    roleNote: (role, source) => `Роль: ${role}, ${source}.`,
    mapHintsTitle: "Таймеры карты",
    mapHintsHint: "Напоминание на карточке за 20 секунд до рун, святилищ, Торментора, стаков и вардов — только нужных вашей роли. Выключите — пропадёт и полоса таймеров",
    frequencyHint: {
      calm: "Вдвое больше пауза между советами; срочные не задерживаются",
      normal: "Обычные паузы между советами",
      active: "Короче паузы между советами; срочные как всегда"
    },
    voiceTitle: "Голос",
    voiceOff: "Выкл",
    voiceUrgent: "Срочные",
    voiceAll: "Все",
    voiceTest: "Прослушать",
    voiceHint: {
      off: "Советы только на экране, без озвучки",
      urgent: "Озвучивает срочные советы; слышно даже в полноэкранном режиме. Ctrl+Alt+R — повторить",
      all: "Озвучивает все советы; слышно даже в полноэкранном режиме. Ctrl+Alt+R — повторить"
    },
    voiceNoVoice: "В Windows нет русского голоса: Параметры → Время и язык → Речь → Добавить голоса",
    voiceSample: "Отходите: противника не видно на карте.",
    overlayMove: "Переместить вручную",
    moveHint: "Покажет карточку, чтобы её можно было перетащить",
    moveActiveHint: "Перетащите карточку и нажмите «Готово»",
    moveStart: "Переместить",
    moveDone: "Готово",
    statsTitle: "Помочь улучшить подсказки",
    statsHint: "Раз в день приложение отправляет анонимные счётчики: какие подсказки показывались и после каких предупреждений была смерть. Без героев, матчей, ника и ключей. По умолчанию выключено.",
    statsPreview: "Что отправляется (за сегодня)",
    statsTerms: "Хранится год.",
    statsOff: "Выключено: ничего не отправляется.",
    statsOn: "Включено: первая отправка — завтра, со счётчиками за сегодня.",
    statsSent: (date) => `Включено. Последняя отправка — ${date}.`,
    statsPreviewLoading: "Собираем…",
    statsPreviewFailed: "Тренер не запущен: показать нечего.",
    serverDelete: "Удалить мои данные на сервере",
    serverDeleteConfirm: "Точно удалить? Нажмите ещё раз",
    serverDeleted: "Удалено: отчёты о проблемах, ссылки «Поделиться» и статистика этого компьютера стёрты с сервера.",
    serverDeleteFailed: (code) => `Не получилось удалить (${code}): проверьте интернет и попробуйте ещё раз.`,
    discordTitle: "Статус в Discord",
    discordHint: "Друзья в Discord видят «Матч на Juggernaut · с тренером Wardly», пока запущена Дота",
    discordStates: {
      idle: "Появится, когда запущена Дота.",
      connecting: "Подключаюсь к Discord…",
      no_discord: "Discord не найден: откройте приложение Discord на этом компьютере (в браузере статус не работает).",
      connected: "Discord подключён. Статус появится, когда запущена Дота.",
      shown: "Статус показан в Discord. Друзья не видят? Discord → Настройки → Конфиденциальность активности → «Делиться своей активностью».",
      rejected: (error) => `Discord не принял статус: ${error}`
    },
    settingsMore: "Ещё настройки",
    settingsPageTitle: "Настройки",
    settingsPageSub: "Всё уже работает. Меняйте только то, что хочется.",
    zoneNow: "Сейчас",
    zoneNowHint: "Текущий матч и подсказки в нём",
    zoneHistory: "Последние матчи",
    zoneHistoryHint: "Откройте матч, чтобы увидеть разбор",
    zoneWeek: "Ваша неделя",
    zoneWeekHint: "Последние семь дней против семи до них",
    zoneAllMatches: "Все матчи",
    zoneGame: "В игре",
    zoneGameHint: "Что вы видите и слышите во время матча",
    zoneData: "После матча",
    zoneDataHint: "Разбор каждого матча простыми словами от ИИ-тренера",
    zoneApp: "Приложение",
    zoneAppHint: "Язык, автозапуск, обновления",
    weeklyTitle: "Неделя в Discord",
    weeklyHint:
      "Каждый понедельник матчи, результаты и средняя оценка за неделю приходят в канал вашего сервера Discord. Для этого нужна ссылка канала (вебхук): в Discord откройте настройки канала → Интеграция → Вебхуки → Новый вебхук → Копировать URL вебхука и вставьте её сюда.",
    weeklyInputLabel: "Ссылка вебхука",
    weeklyConnect: "Подключить",
    weeklySendNow: "Отправить сейчас",
    weeklyDisconnect: "Отключить",
    weeklySending: "Отправляю…",
    weeklyConnected: (hint) => `Подключено (${hint}). Неделя приходит в Discord каждый понедельник.`,
    weeklySent: (date) => `Последняя отправка: ${date}.`,
    weeklyEmpty: (date) => `${date}: за ту неделю матчей не было, ничего не отправлено.`,
    weeklyNoMatchesNow: "За последние семь дней матчей нет: отправлять пока нечего.",
    weeklyErrors: {
      bad_url: "Это не ссылка вебхука Discord: она начинается с https://discord.com/api/webhooks/.",
      webhook_gone: "Вебхук удалён в Discord: создайте новый и подключите заново.",
      rate_limited: "Discord просит подождать: попробуйте через минуту.",
      offline: "Нет связи с Discord: проверьте интернет.",
      backend_down: "Тренер ещё не запущен: попробуйте через минуту.",
      busy: "Уже отправляю…",
      fallback: "Не удалось отправить: попробуйте позже."
    },
    autostart: "Автозапуск с Windows",
    autostartOn: "Wardly сам откроется при включении компьютера и будет тихо ждать возле часов. Так вы не забудете запустить его перед игрой.",
    autostartOff: "Сейчас выключено: Wardly нужно открывать самому перед игрой. Включите — и он будет сам запускаться с компьютером и тихо ждать возле часов.",
    autostartUnavailable: "Доступно в установленном приложении",
    updates: "Обновления",
    updateCheck: "Проверить",
    updateInstall: "Перезапустить и обновить",
    updateHint: {
      disabled: (v) => `Версия ${v} · обновления работают в установленном приложении`,
      idle: (v) => `Версия ${v} · обновляется само`,
      checking: (v) => `Версия ${v} · проверяем…`,
      "up-to-date": (v) => `Версия ${v} · последняя`,
      downloading: (v, next, pct) => `Загружается ${next}… ${pct}%`,
      ready: (v, next) => `Версия ${next} загружена. Установится сама, когда Дота будет закрыта.`,
      blocked: (v, next) => `Версия ${next} загружена. Установится после выхода из Доты.`,
      error: (v) => `Версия ${v} · не удалось проверить обновления`
    },
    whatsNewTitle: (version) => `Что нового в ${version}`,
    whatsNewOk: "Понятно",
    inviteTitle: "Нравится Wardly?",
    inviteText: "Скинь ссылку другу: приложение бесплатное, а играя вместе, проще следовать подсказкам.",
    inviteCopy: "Скопировать ссылку",
    inviteLater: "Не сейчас",
    inviteCopied: "Ссылка скопирована",
    tour: {
      next: "Дальше",
      back: "Назад",
      skip: "Пропустить",
      done: "Играть",
      count: (i, n) => `${i} из ${n}`,
      steps: {
        welcome: {
          title: "Привет! Это Wardly",
          text: "Тренер смотрит матч вместе с тобой: короткие советы поверх игры и голосом, а после матча — разбор, что исправить. Покажу, что где, — это займёт минуту."
        },
        status: {
          title: "Строка состояния",
          text: "Что происходит сейчас: найдена ли Дота, идут ли от неё данные, начался ли матч. Если нужно что-то сделать, справа будет кнопка."
        },
        setup: {
          title: "Первый запуск",
          text: "Что уже настроено и что осталось. Большинство шагов выполняются сами; первый матч с приложением закроет список."
        },
        match: {
          title: "Текущий матч",
          text: "Твой герой, время матча и советы тренера. Сами советы появляются поверх игры — во время матча сюда смотреть не нужно."
        },
        matches: {
          title: "Матчи",
          text: "Каждый матч с разбором: оценки по областям, где ты умирал, тайминги предметов и что исправить в первую очередь. Разбор готов через минуту-две после матча."
        },
        progress: {
          title: "Прогресс",
          text: "Как ты играешь за последние игры: тренды, повторяющиеся ошибки, твои герои и цель, над которой работать."
        },
        settings: {
          title: "Карточка в игре",
          text: "Где карточка с советом стоит поверх игры и какого она размера. Её можно перетащить руками."
        },
        voice: {
          title: "Советы и голос",
          text: "Как часто тренер подсказывает, твоя роль для таймеров карты и голос: он читает советы вслух и работает даже в полноэкранном режиме."
        },
        done: {
          title: "Всё готово",
          text: "Запусти Доту и начни матч — первая подсказка появится сама. Обучение можно открыть снова в «Настройки → Помощь»."
        }
      }
    },
    summaryTitle: "Сводка",
    sessionTitle: "Итог вечера",
    sessionHide: "Скрыть",
    tourTitle: "Как пользоваться Wardly",
    tourHint: "Короткая экскурсия по приложению, на минуту",
    tourStart: "Показать",
    whatsNew: {
      "0.29.2": [
        "Предметы против врагов: смерти под Primal Roar от Beastmaster, Doom или Duel — совет купить Linken's Sphere с объяснением; против уклонения — Monkey King Bar, против лечения — Spirit Vessel, саппорту против невидимых — Dust.",
        "Неизученный Blink больше не считается «на перезарядке», а «умерли с готовым Blink» — только если на нажатие было две свободные секунды.",
        "Повторные карточки про низкое HP говорят, какой это раз за игру, и советуют восстановиться полностью."
      ],
      "0.29.1": [
        "Мидеру таймер руны силы показывается до 20-й минуты, а не всю игру, а до 6-го уровня с Bottle подсказка советует положить руну в него и приберечь для убийства."
      ],
      "0.29.0": [
        "Разбор матча стал короче: кроме трёх главных пунктов, остальные замечания и длинный список смертей открываются кнопкой «Показать ещё».",
        "Под каждой смертью подписано, что это за линия здоровья, а «Ценность» теперь называется «Стоимость героя»."
      ],
      "0.28.0": [
        "Первый совет после смерти называет линию или часть карты, где вы погибли, или как быстро вас убили — а не «продумайте более безопасный маршрут».",
        "Саппортам: подсказка «Нет спасающего предмета» называет предмет, который чаще всего берут на вашем герое, и сколько золота на него осталось; подсказка про вард говорит, куда его поставить (река у вашей линии, логово Рошана, свой или вражеский лес по счёту).",
        "Если на линии не хватает добиваний, совет показывает цифры: «Навёрстывайте фарм: добиваний к 5-й минуте — 12, хороший темп — 18+»."
      ],
      "0.27.0": [
        "Совет после смерти говорит, сколько раз вы уже погибли — за последние минуты или за игру, — а не повторяет одно и то же «смените маршрут»."
      ],
      "0.26.0": [
        "В разборе матча появилась карточка «Прокачка»: какое умение вы вкачали первым и как качают вашего героя про-игроки."
      ],
      "0.25.0": [
        "Карточки про фарм показывают цифры в главной строке: золото в минуту и добивания или насколько вы отстали от хорошего темпа.",
        "Совет, в котором поменялись только цифры, больше не повторяется каждые две минуты."
      ],
      "0.24.0": [
        "Какой талант взять: когда открывается ряд талантов, тренер называет тот, что берут про-игроки на вашем герое."
      ],
      "0.23.0": [
        "Куда вложить очко: после нового уровня тренер называет умение, которое качают про-игроки на вашем герое, и весь порядок прокачки.",
        "План на игру показывает прокачку у про, а разбор — если первым вы вкачали другое умение."
      ],
      "0.22.0": [
        "Прокачка: тренер подскажет ультимейт на 6/12/18-м уровне и талант на 10/15/20/25-м, если очко осталось не вложенным.",
        "Предмет под ситуацию: две смерти под контролем — Black King Bar, две быстрые смерти — Aeon Disk, с причиной и недостающим золотом.",
        "Меньше банальных советов: серия убийств, разрыв в счёте или ваш темп в цифрах вместо одного и того же «фармите безопасно»."
      ],
      "0.21.0": [
        "Настройки собраны заново: пять понятных групп, крупнее шрифт, меньше кнопок и объяснение простыми словами у каждой строки. Перенос на другой компьютер — по шагам.",
        "«Почему этот совет?» под каждой подсказкой на Главной и в разборе: что увидел тренер.",
        "«Что это значит?» у оценки матча, сравнения с рангом и фокуса — и никаких технических слов по всему приложению."
      ],
      "0.20.0": [
        "Полные подсказки для 25 саппортов (четвёрки и пятёрки): их спасения, напоминания поставить варды из инвентаря и собрать предмет спасения, а в разборе — тайминг этого предмета и сколько вардов вы поставили.",
        "Оверлей 2.0: полоска таймеров под карточкой (руны, стаки, Рошан, Аегис для вашей роли), компактная карточка и плавное появление — «Настройки → Оверлей».",
        "Новая Главная: одна карточка с последним матчем, сегодняшним днём, сериями и фокусом. В «Прогрессе» — зона «Цели»."
      ],
      "0.19.0": [
        "Итог вечера: после двух и больше матчей, когда Дота закрыта, на Главной — сводка вечера и текст, который можно скопировать друзьям.",
        "В «Прогрессе» — карта ваших смертей за последние 20 матчей и тайминг ключевого предмета героя по играм.",
        "Короткое обучение по приложению (Настройки → Приложение), а строка состояния прямо пишет, есть ли связь с Дотой."
      ],
      "0.18.0": [
        "Полные подсказки ещё для 18 героев: 8 мидеров (Shadow Fiend, Storm Spirit, Queen of Pain, Puck и другие) и 10 хардлайнеров (Axe, Mars, Legion Commander, Centaur и другие).",
        "Тренер знает их собственные спасения (Blink, Ball Lightning, Refraction, Guardian Sprint…), а фарм хардлайнера сравнивается с темпом хардлайнера, а не керри."
      ],
      "0.17.0": [
        "Анонимная статистика по желанию («Настройки → Приложение», по умолчанию выключена): какие подсказки показаны и после каких предупреждений была смерть — чтобы сделать подсказки лучше. «Что отправляется» показывает точный текст.",
        "«Удалить мои данные на сервере» одним нажатием стирает ваши отчёты о проблемах, ссылки «Поделиться» и статистику."
      ],
      "0.16.0": [
        "В разборе кнопка «Смотреть» у смерти и ключевого момента копирует команду повтора, которая переносит за 10 с до него.",
        "На графике матча пунктиром — ваш лучший матч на этом герое.",
        "На главной — цели-серии (5 матчей подряд не больше 5 смертей) и мягкое предупреждение после 3 поражений подряд.",
        "В «Прогрессе» — на каких героях играть чаще, а каких лучше отложить, по сравнению с вашим званием."
      ],
      "0.15.0": [
        "Таймеры Рошана и Аегиса: окно появления после убийства и предупреждение за минуту до того, как сгорит ваш Аегис.",
        "Пока ждёте возрождения: как вас убили, что осталось не нажато и что купить сейчас.",
        "Больше нет «Переждите контроль», если после оглушения нечего нажать."
      ],
      "0.14.0": [
        "Подсказки знают вашего героя: Blink, чтобы уйти, Blade Fury, чтобы выйти из драки, и через сколько секунд откатится побег.",
        "Карта матча обводит места, где вы умираете раз за разом, и подсказывает маршрут."
      ],
      "0.13.0": [
        "Подсказки называют, что нажать прямо сейчас: Force Staff, чтобы уйти, Magic Wand с зарядами, Black King Bar сразу после оглушения.",
        "После смерти: какой спасающий предмет остался не нажат и где вы умираете раз за разом."
      ],
      "0.12.0": [
        "Каждая вкладка разбита на понятные зоны: сначала главное, потом детали.",
        "«Ваша неделя» на Главной: оценка против прошлой недели и график каждого матча.",
        "Совет по фарму для керри называет следующий предмет, сколько золота не хватает и сколько его фармить.",
        "Исправлено: некоторые разборы бесконечно показывали «Загружаем матч…»."
      ],
      "0.11.0": [
        "Приложение на весь экран: навигация слева, две колонки, обе команды рядом.",
        "«Последние матчи» на Главной, оценка кольцом в разборе и таблице матчей.",
        "Больше подсказок в игре для каждой роли: ротации и добивания мида, тяжёлая линия хардлайна, пулы саппорта, тайминг ключевого предмета.",
        "«Тяжело против» в плане на игру."
      ],
      "0.10.0": [
        "Неделя в Discord: по понедельникам матчи, оценка и герои недели приходят в канал вашего сервера. «Настройки → Приложение → Неделя в Discord».",
        "В карточке «Неделя» на Главной видно, на каких героях вы играли.",
        "В «Отчёт о проблеме» больше не попадают ключи удаления ваших ссылок «Поделиться»."
      ],
      "0.9.0": [
        "Статус в Discord: друзья видят «Матч на <герой> · с тренером Wardly». Выключается в «Настройках → Приложение».",
        "Ссылки на разборы и прогресс теперь короче: luhovyimvp.dev/r/…",
        "Сайт в цветах логотипа."
      ],
      "0.8.0": [
        "Разбор смертей: здоровье за последние 20 секунд и спасающий предмет, который был готов, но не нажат.",
        "«Прогресс»: ваш билд на герое — когда предметы приходят в победах и в поражениях.",
        "После матча оверлей показывает итог прямо на экране со счётом.",
        "Перенос истории на другой компьютер по одноразовому коду."
      ],
      "0.7.0": [
        "«Прогресс» → «Поделиться»: ссылка на страницу с вашим прогрессом — матчи, победы, средние цифры, главные герои, что получается и над чем работать.",
        "Новая заставка при запуске: логотип оживает, пока запускается служба."
      ],
      "0.6.1": [
        "Разбор хардлайнера: оглушения и урон по строениям против вражеского хардлайнера того же матча.",
        "В плане на игру рядом с героем — ваш счёт на нём.",
        "Все версии и что в них изменилось — на сайте: luhovyimvp.dev/changelog.html."
      ],
      "0.6.0": [
        "Разбор под роль: руны мида против вражеского мида, стаки и сентри саппорта.",
        "«Прогресс»: ваш счёт против каждого вражеского героя — кто неудобен и кого вы обыгрываете.",
        "ИИ-тренеру можно задать вопрос о всех последних матчах, а не только об одном.",
        "В игре: подсказка на 6-м уровне для мида (ротация) и оффлейна (давление)."
      ],
      "0.5.0": [
        "Dota AI Coach теперь называется Wardly, у него новый логотип. История и настройки на месте.",
        "«Прогресс» → «Сравнение с другом»: его открытые матчи рядом с вашими и общие герои.",
        "Разбор можно отправить ссылкой — с превью в Discord и Telegram, без Steam ID и ника.",
        "«Настройки → Приложение → История матчей»: сохранить всё в файл и загрузить на любом компьютере.",
        "Путь на карте матча больше не тянется от места смерти к фонтану."
      ],
      "0.4.0": [
        "Карта матча нарисована на настоящей миникарте Доты: ваш путь, позиция на линии, варды и смерти.",
        "На графике «По ходу матча» — хороший темп по золоту и опыту.",
        "Карточка «Смерти»: где, кто убил, сколько золота не потрачено и какая была подсказка перед смертью.",
        "Повторяющиеся ошибки отмечены: «3-й матч подряд».",
        "Неделя на главной: матчи, изменение оценки, лучший матч, частая ошибка и план на 3 матча по фокусу."
      ],
      "0.3.0": [
        "Таймеры карты на оверлее за 20 секунд: руны, святилища мудрости, лотосы, Торментор, уровни нейтральных предметов — только нужные вашей роли.",
        "Роль определяется по линии в первые минуты (или выбирается в «Настройки → Советы») и видна на главной.",
        "Подсказки саппорту: застакать лагерь, взять варды, оставить добивания керри. Советы про фарм на саппорте выключены; про ТП — на любом герое.",
        "«Отправить разработчику» в отчёте о проблеме: одна кнопка, комментарий и предпросмотр; ключи, ник и Steam ID вырезаются.",
        "Драфт предлагает только героев той позиции, на которой вы играли."
      ],
      "0.2.1": [
        "История матчей больше не срывается, когда OpenDota отвечает медленно.",
        "Приложение само просит OpenDota разобрать последние матчи — в разборе появляются добивания к 10:00, сборка и график.",
        "Драфт советует героя вашей роли; соперник по роли и предметы против врагов определяются верно и без разбора реплея.",
        "На «Прогрессе» все пять плиток в одну строку, на главной не обрезается имя героя."
      ],
      "0.2.0": [
        "План на игру в начале матча и фокус: выберите одну ошибку — в каждом разборе видно, получилось ли её избежать.",
        "«Спросить тренера»: свой вопрос о матче, ответ по его данным.",
        "Голос, частота советов, советы по выживанию на любом герое, напоминания носить TP и тратить золото после смерти.",
        "Карта матча, сравнение с вашими обычными цифрами, фильтры матчей и сохранение в PDF.",
        "Проверка параметра запуска -gamestateintegration, без которого Дота не передаёт данные."
      ]
    },
    setupTitle: "Первый запуск",
    setupHide: "Скрыть",
    setupCount: (done, total) => `${done} из ${total}`,
    setup: {
      service: ["Тренер запущен", "Запускается вместе с приложением. Если остановился — перезапустите приложение."],
      dota: ["Dota 2 найдена", "Игры нет в библиотеках Steam — укажите папку игры."],
      gsi: ["Приложение подключено к Доте", "Маленький файл в папке Доты: через него игра сообщает тренеру, что происходит в матче."],
      launch: ["Дота передаёт данные матча", "Для этого нужен параметр запуска. В Steam: правой кнопкой по Dota 2 → Свойства → Параметры запуска, вставьте -gamestateintegration."],
      data: ["Дота связалась с тренером", "Запустите Dota 2 (или перезапустите, если она была открыта) и зайдите в любой матч, можно с ботами."],
      account: ["Аккаунт Steam привязан", "Привяжется сам в первом матче, или укажите его на вкладке «Матчи»."],
      ai: ["ИИ-тренер (по желанию)", "С бесплатным ключом Google ИИ напишет разбор каждого матча простыми словами."]
    },
    setupActions: { dota: "Указать папку", gsi: "Подключить", launch: "Скопировать", account: "Привязать", ai: "Настроить" },
    reportTitle: "Сообщить о проблеме",
    reportHint: "Что-то не работает? Нажмите «Сообщить» и опишите в двух словах: разработчик получит журнал приложения. Ключи и пароли из него вырезаются.",
    reportSave: "Сохранить в файл вместо отправки",
    backupTitle: "Запасная копия в файле",
    backupHint: "Сохраняет все матчи и разборы в один файл — например, перед переустановкой Windows. Потом его можно открыть в Wardly на любом компьютере. Ключи в файл не попадают.",
    backupExport: "Сохранить в файл",
    backupImport: "Открыть файл",
    backupSaved: (count, file) => `Сохранено матчей: ${count}. Файл ${file}`,
    backupLoaded: (added, linked) => `Загружено новых матчей: ${added}${linked ? ", аккаунт привязан" : ""}. Ничего не перезаписано.`,
    backupNotBackup: "Это не файл истории Wardly.",
    backupNewer: "Файл сделан более новой версией: сначала обновите приложение.",
    backupFailed: "Не получилось: тренер не запущен или диск недоступен.",
    transferTitle: "Перенос на другой компьютер",
    zoneMyData: "Ваши матчи",
    zoneMyDataHint: "Чтобы история не потерялась при смене компьютера",
    zoneHelp: "Помощь",
    zoneHelpHint: "Как пользоваться приложением и что делать, если что-то сломалось",
    transferIntro: "Поставили Wardly на новый компьютер? Перенесите туда свои матчи и разборы — это займёт минуту.",
    transferStep1: "Здесь нажмите «Получить код».",
    transferStep2: "На новом компьютере: Wardly → Настройки → «Перенос на другой компьютер» → «У меня есть код» — и введите его.",
    transferHave: "У меня есть код",
    transferHint: "Код действует 15 минут. Матчи передаются в зашифрованном виде, ключи не переносятся.",
    transferSend: "Получить код",
    transferReceive: "Загрузить",
    transferInputLabel: "Код с другого компьютера",
    transferSending: "Шифрую и отправляю…",
    transferReady: (matches, time) => `Код действует до ${time}. Введите его на новом компьютере (матчей: ${matches}).`,
    transferReceiving: "Скачиваю и расшифровываю…",
    transferErrors: {
      bad_code: "Проверьте код: три группы по четыре буквы и цифры, как на другом компьютере.",
      not_found: "По этому коду ничего нет: он устарел (15 минут) или история уже загружена. Получите новый код.",
      too_big: "История слишком большая для переноса по коду: сохраните её в файл.",
      rate_limited: "Слишком много попыток: подождите час или перенесите файлом.",
      disabled: "Перенос по коду сейчас выключен: воспользуйтесь файлом.",
      not_backup: "Код открыл что-то, что не похоже на историю Wardly.",
      offline: "Нет связи с сервером: проверьте интернет.",
      fallback: "Не получилось: попробуйте ещё раз или перенесите файлом."
    },
    reportSaving: "Собираем…",
    reportSaved: (name) => `Сохранено: ${name}. Отправьте этот файл разработчику.`,
    reportFailed: "Не удалось сохранить файл",
    reportSend: "Сообщить",
    reportNoteLabel: "Что случилось? (необязательно)",
    reportNotePlaceholder: "Например: в матче не видно подсказок",
    reportPreview: "Что будет отправлено",
    reportPreviewLoading: "Собираем отчёт…",
    reportTerms: "Ключи вырезаны. Отчёт хранится 180 дней.",
    reportPrivacy: "Конфиденциальность",
    reportSendNow: "Отправить",
    reportCancel: "Отмена",
    reportSending: "Отправляем…",
    reportSentId: (id) => `Отправлено. Номер отчёта: ${id}. Назовите его, если будете писать разработчику.`,
    reportQueued: "Сейчас нет интернета. Отчёт отправится сам позже.",
    reportQueuedCount: (count) => `Ждут отправки: ${count}`,
    reportLast: (id) => `Последний отчёт: ${id}`,
    reportRefused: (name) =>
      name ? `Сервер не принял отчёт. Вместо этого сохранён файл: ${name}.` : "Сервер не принял отчёт.",
    devTitle: "Для разработчика",
    devHint: "Технические инструменты: процесс тренера, связь с игрой, журналы. Для игры не нужны",
    factBackend: "Сервис",
    factDota: "Дота",
    factOverlay: "Оверлей",
    factDemo: "Демо",
    factRecording: "Запись",
    factGsiConfig: "Конфиг GSI",
    factMode: "Режим",
    groupBackend: "Сервис",
    startBackend: "Запустить",
    restartBackend: "Перезапустить",
    stopBackend: "Остановить",
    showOverlay: "Показать оверлей",
    hideOverlay: "Скрыть оверлей",
    hotkeys: "Ctrl+Alt+O вкл/выкл · Ctrl+Alt+L переместить · Ctrl+Alt+M тишина 5 мин · Ctrl+Alt+R повторить совет · Ctrl+Alt+1/2/3 слева/справа/снизу · Ctrl+Alt+D отладка",
    groupGsi: "Конфиг GSI",
    gsiPathPlaceholder: "Своя папка gamestate_integration (необязательно)",
    chooseFolder: "Выбрать",
    checkGsi: "Проверить",
    installGsi: "Установить",
    gsiPath: (p, e) => `Конфиг: ${p}${e ? `\nАдрес: ${e}` : ""}`,
    gsiPathMissing: "Конфиг не найден. Выберите папку gamestate_integration и установите.",
    gsiEndpoint: (e) => (e ? `Адрес: ${e}` : "Адрес: ждём порт сервиса…"),
    groupLive: "Живой GSI",
    kvConnection: "Связь",
    kvLast: "Данные",
    kvHero: "Герой",
    kvTime: "Время",
    kvStage: "Стадия",
    liveConnected: "подключено",
    liveWaiting: "ожидание / устарело",
    liveUnavailable: "сервис недоступен",
    liveAdvice: (a) => `Текущий совет: ${a}`,
    liveAdviceNone: "Текущий совет: пока нет",
    liveAdviceLast: (t) => `Текущий совет: последний в ${t}`,
    liveMissing: (m) => `Не хватает полей: ${m}`,
    none: "нет",
    checkLive: "Проверить",
    startRecording: "Записать",
    stopRecording: "Остановить запись",
    openRecords: "Записи",
    groupDemo: "Демо-повтор",
    demoHint: "Проигрывает записанные состояния матча в сервис; оверлей виден без Доты.",
    demoBusy: "Демо уже идёт. Сначала остановите его.",
    runDemo: "Запустить демо",
    presetPl: "Phantom Lancer 20–30",
    presetJugg: "Juggernaut 10–20",
    deepReview: "Deep Review",
    stopDemo: "Остановить",
    openResults: "Результаты",
    groupLogs: "Логи",
    logClean: "Кратко",
    logVerbose: "Подробно",
    copyLogs: "Копировать",
    clearLogs: "Очистить",
    openLogs: "Папка логов",
    dotaStates: { not_found: "не найдена", waiting: "ждём матч", in_game: "в игре" },
    gsiConfigStates: { installed: "установлен", "not found": "не найден", error: "ошибка", unknown: "неизвестно" },
    modes: { "Live GSI": "Живой GSI", "Replay Demo": "Демо-повтор" },
    on: "вкл",
    off: "выкл",
    shown: "на экране",
    hidden: "скрыт",
    running: "идёт",
    stopped: "остановлено"
  }
};

const $ = (selector) => document.querySelector(selector);
const els = {
  service: $("#service"),
  serviceText: $("#service-text"),
  status: $("#status"),
  statusTitle: $("#status-title"),
  statusHint: $("#status-hint"),
  statusAction: $("#status-action"),
  statusActionLabel: $("#status-action-label"),
  matchStats: $("#match-body .stats"),
  matchEmpty: $("#match-empty"),
  coverageNote: $("#coverage-note"),
  statHero: $("#stat-hero"),
  statClock: $("#stat-clock"),
  statStage: $("#stat-stage"),
  statData: $("#stat-data"),
  adviceList: $("#advice-list"),
  adviceEmpty: $("#advice-empty"),
  overlayToggle: $("#overlay-toggle"),
  overlayHint: $("#overlay-hint"),
  positionButtons: [...document.querySelectorAll("#position-group [data-position]")],
  positionHint: $("#position-hint"),
  sizeButtons: [...document.querySelectorAll("#size-group [data-size]")],
  overlayTimers: $("#overlay-timers"),
  overlayCompact: $("#overlay-compact"),
  languageButtons: [...document.querySelectorAll("#language-group [data-language]")],
  frequencyButtons: [...document.querySelectorAll("#frequency-group [data-frequency]")],
  roleButtons: [...document.querySelectorAll("#role-group [data-role]")],
  roleHint: $("#role-hint"),
  roleNote: $("#role-note"),
  mapHints: $("#map-hints"),
  frequencyHint: $("#frequency-hint"),
  voiceButtons: [...document.querySelectorAll("#voice-group [data-voice]")],
  voiceHint: $("#voice-hint"),
  voiceTest: $("#voice-test"),
  moveToggle: $("#move-toggle"),
  moveLabel: $("#move-label"),
  moveHint: $("#move-hint"),
  autostart: $("#autostart"),
  discordPresence: $("#discord-presence"),
  discordState: $("#discord-state"),
  weeklyHint: $("#weekly-hint"),
  weeklyForm: $("#weekly-form"),
  weeklyInput: $("#weekly-input"),
  weeklyConnect: $("#weekly-connect"),
  weeklySend: $("#weekly-send"),
  weeklyClear: $("#weekly-clear"),
  autostartHint: $("#autostart-hint"),
  updateHint: $("#update-hint"),
  updateAction: $("#update-action"),
  updateLabel: $("#update-label"),
  whatsNewCard: $("#whats-new-card"),
  whatsNewHeading: $("#whats-new-heading"),
  whatsNewList: $("#whats-new-list"),
  whatsNewDismiss: $("#whats-new-dismiss"),
  inviteCard: $("#invite-card"),
  inviteCopy: $("#invite-copy"),
  inviteDismiss: $("#invite-dismiss"),
  tourStart: $("#tour-start"),
  nowZone: $("#now-zone"),
  setupCard: $("#setup-card"),
  setupSteps: $("#setup-steps"),
  setupCount: $("#setup-count"),
  setupDismiss: $("#setup-dismiss"),
  odHint: $("#od-hint"),
  odForm: $("#od-form"),
  odKey: $("#od-key"),
  odSave: $("#od-save"),
  odGet: $("#od-get"),
  odClear: $("#od-clear"),
  reportAction: $("#report-action"),
  backupExport: $("#backup-export"),
  backupImport: $("#backup-import"),
  backupHint: $("#backup-hint"),
  transferHint: $("#transfer-hint"),
  transferCode: $("#transfer-code"),
  transferSend: $("#transfer-send"),
  transferHave: $("#transfer-have"),
  transferForm: $("#transfer-form"),
  transferInput: $("#transfer-input"),
  transferReceive: $("#transfer-receive"),
  reportHint: $("#report-hint"),
  reportOpen: $("#report-open"),
  reportPanel: $("#report-panel"),
  reportNote: $("#report-note"),
  shareStats: $("#share-stats"),
  statsHint: $("#stats-hint"),
  statsPreview: $("#stats-preview"),
  statsPreviewText: $("#stats-preview-text"),
  statsPrivacy: $("#stats-privacy"),
  serverDelete: $("#server-delete"),
  reportPreview: $("#report-preview"),
  reportPreviewText: $("#report-preview-text"),
  reportPrivacy: $("#report-privacy"),
  reportSend: $("#report-send"),
  reportCancel: $("#report-cancel"),
  devTools: $("#dev-tools"),
  logs: $("#logs"),
  gsiPath: $("#gsi-path"),
  gsiDetail: $("#gsi-detail")
};
const factEls = {
  backend: $("#backend-status"),
  dota: $("#dota-status"),
  overlay: $("#overlay-status"),
  demo: $("#demo-status"),
  recording: $("#recording-status"),
  gsi: $("#gsi-status"),
  mode: $("#mode-status"),
  llm: $("#llm-status")
};
const liveEls = {
  connection: $("#live-connection"),
  last: $("#live-last"),
  hero: $("#live-hero"),
  time: $("#live-time"),
  stage: $("#live-stage"),
  advice: $("#live-advice"),
  missing: $("#live-missing")
};
const logModeButtons = { clean: $("#log-clean"), verbose: $("#log-verbose") };
const demoStartButtons = ["#run-demo", "#preset-pl", "#preset-jugg", "#deep-review"].map($).filter(Boolean);
const controlButtons = {
  startBackend: $("#start-backend"),
  restartBackend: $("#restart-backend"),
  stopBackend: $("#stop-backend"),
  startOverlay: $("#start-overlay"),
  stopOverlay: $("#stop-overlay"),
  stopDemo: $("#stop-demo"),
  startRecording: $("#start-recording"),
  stopRecording: $("#stop-recording")
};

const DEV_OPEN_KEY = "dota-ai-coach.devToolsOpen";
let locale = "en";
let textsLocale = "";
let gsiEndpoint = "";
let statusAction = null;
let lastVoice = { mode: "off", volume: 1 };
let voiceListChecked = false;
let openDotaLoaded = false;
// Problem report row: a result message stays until the panel is opened again.
let reportSticky = false;
// A transfer by code is on its way: keep its hint on re-renders.
let transferBusy = false;
// The week in Discord: the answer of the last button press, shown instead of
// the stored state until the next press; the stored state from the status.
let weeklyMessage = "";
let weeklyBusy = false;
let lastWeekly = null;
let reportPreviewLoaded = false;
let serverDeleteArmed = false;
let serverDeleteNote = "";
const seenAdvice = new Set();
const openWhy = new Set();

init();

// ---------------------------------------------------------------------------
// i18n
// ---------------------------------------------------------------------------

function lookup(table, key) {
  return key.split(".").reduce((node, part) => (node ? node[part] : undefined), table);
}

function tr(key, ...args) {
  const resolved = lookup(I18N[locale], key) ?? lookup(I18N.en, key) ?? key;
  return typeof resolved === "function" ? resolved(...args) : resolved;
}

// Like tr() for values that may be missing (backend-provided codes).
function trOr(key, fallback) {
  const value = lookup(I18N[locale], key) ?? lookup(I18N.en, key);
  return typeof value === "string" ? value : fallback;
}

function renderWeekly(state) {
  lastWeekly = state;
  const configured = Boolean(state && state.configured);
  els.weeklyForm.hidden = configured;
  els.weeklySend.hidden = !configured;
  els.weeklyClear.hidden = !configured;
  if (weeklyMessage) {
    els.weeklyHint.textContent = weeklyMessage;
    return;
  }
  if (!configured) {
    // A webhook deleted in Discord was disconnected by the launcher: say why.
    const gone = state && state.last && state.last.code === "webhook_gone";
    els.weeklyHint.textContent = gone ? `${tr("weeklyErrors.webhook_gone")} ${tr("weeklyHint")}` : tr("weeklyHint");
    return;
  }
  const last = state.last;
  const date = last && last.at ? new Date(last.at).toLocaleDateString(locale === "ru" ? "ru-RU" : "en-GB", { day: "numeric", month: "long" }) : "";
  if (last && !last.ok) {
    els.weeklyHint.textContent = trOr(`weeklyErrors.${last.code}`, tr("weeklyErrors.fallback"));
  } else if (last && last.sent) {
    els.weeklyHint.textContent = `${tr("weeklyConnected", state.hint)} ${tr("weeklySent", date)}`;
  } else if (last && !last.manual) {
    els.weeklyHint.textContent = `${tr("weeklyConnected", state.hint)} ${tr("weeklyEmpty", date)}`;
  } else {
    els.weeklyHint.textContent = tr("weeklyConnected", state.hint);
  }
}

function applyStaticTexts() {
  if (textsLocale === locale) {
    return;
  }
  textsLocale = locale;
  document.documentElement.lang = locale;
  for (const element of document.querySelectorAll("[data-i18n]")) {
    element.textContent = tr(element.dataset.i18n);
  }
  for (const element of document.querySelectorAll("[data-i18n-placeholder]")) {
    element.placeholder = tr(element.dataset.i18nPlaceholder);
  }
  for (const element of document.querySelectorAll("[data-i18n-title]")) {
    element.title = tr(element.dataset.i18nTitle);
    element.setAttribute("aria-label", element.title);
  }
  els.backupHint.textContent = tr("backupHint");
  if (!transferBusy && els.transferCode.hidden) {
    els.transferHint.textContent = tr("transferHint");
  }
}

// ---------------------------------------------------------------------------
// Wiring
// ---------------------------------------------------------------------------

async function init() {
  window.LucideIcons?.hydrate(document);

  bind("#start-backend", () => window.launcherApi.startBackend());
  bind("#stop-backend", () => window.launcherApi.stopBackend());
  bind("#restart-backend", () => window.launcherApi.restartBackend());
  bind("#start-overlay", () => window.launcherApi.startOverlay());
  bind("#stop-overlay", () => window.launcherApi.stopOverlay());
  bind("#run-demo", () => window.launcherApi.runDemo("plMacro"));
  bind("#stop-demo", () => window.launcherApi.stopDemo());
  bind("#preset-pl", () => window.launcherApi.runDemo("plMacro"));
  bind("#preset-jugg", () => window.launcherApi.runDemo("juggSafety"));
  bind("#deep-review", () => window.launcherApi.runDeepReview("plMacro"));
  bind("#open-logs", () => window.launcherApi.openLogs());
  bind("#open-results", () => window.launcherApi.openSimulationResults());
  bind("#open-readme", () => window.launcherApi.openReadme());
  bind("#clear-logs", () => window.launcherApi.clearLogs());
  bind("#copy-logs", () => window.launcherApi.copyLogs());
  bind("#log-clean", () => window.launcherApi.setLogMode("clean"));
  bind("#log-verbose", () => window.launcherApi.setLogMode("verbose"));
  bind("#check-gsi", checkGsi);
  bind("#install-gsi", () => installGsi(els.gsiPath.value));
  bind("#choose-gsi", chooseGsiFolder);
  bind("#check-live-gsi", checkLiveGsi);
  bind("#start-recording", startLiveRecording);
  bind("#stop-recording", stopLiveRecording);
  bind("#open-records", () => window.launcherApi.openSessionRecords());

  els.statusAction.addEventListener("click", async () => {
    if (!statusAction) {
      return;
    }
    const action = statusAction;
    els.statusAction.disabled = true;
    await run(action.run);
    els.statusAction.disabled = false;
    if (action.doneLabel) {
      flashLabel(els.statusActionLabel, action.doneLabel);
    }
  });
  els.overlayToggle.addEventListener("change", () =>
    run(() => (els.overlayToggle.checked ? window.launcherApi.startOverlay() : window.launcherApi.stopOverlay()))
  );
  for (const button of els.positionButtons) {
    button.addEventListener("click", () =>
      run(async () => renderStatus(await window.launcherApi.setOverlayPosition(button.dataset.position)))
    );
  }
  for (const button of els.languageButtons) {
    button.addEventListener("click", () =>
      run(async () => renderStatus(await window.launcherApi.setLanguage(button.dataset.language)))
    );
  }
  for (const button of els.sizeButtons) {
    button.addEventListener("click", () =>
      run(async () => renderStatus(await window.launcherApi.setOverlaySize(button.dataset.size)))
    );
  }
  for (const [input, key] of [[els.overlayTimers, "timers"], [els.overlayCompact, "compact"]]) {
    input.addEventListener("change", () =>
      run(async () => renderStatus(await window.launcherApi.setOverlayDisplay({ [key]: input.checked })))
    );
  }
  for (const button of els.frequencyButtons) {
    button.addEventListener("click", () =>
      run(async () => renderStatus(await window.launcherApi.setAdviceFrequency(button.dataset.frequency)))
    );
  }
  for (const button of els.roleButtons) {
    button.addEventListener("click", () =>
      run(async () => renderStatus(await window.launcherApi.setAdvicePreferences({ role: button.dataset.role })))
    );
  }
  els.mapHints.addEventListener("change", () =>
    run(async () => renderStatus(await window.launcherApi.setAdvicePreferences({ mapHints: els.mapHints.checked })))
  );
  for (const button of els.voiceButtons) {
    button.addEventListener("click", () =>
      run(async () => renderStatus(await window.launcherApi.setOverlayVoice(button.dataset.voice)))
    );
  }
  els.voiceTest.addEventListener("click", () => run(testVoice));
  window.speechSynthesis?.addEventListener?.("voiceschanged", () => renderVoiceHint(lastVoice));
  els.moveToggle.addEventListener("click", () =>
    run(async () => {
      // Pressed = the card is unlocked for dragging; pressing again locks it.
      const moving = els.moveToggle.getAttribute("aria-pressed") === "true";
      renderStatus(await window.launcherApi.setOverlayLocked(moving));
    })
  );
  els.updateAction.addEventListener("click", () =>
    run(async () => {
      if (els.updateAction.dataset.mode === "install") {
        await window.launcherApi.installUpdate();
      } else {
        renderStatus(await window.launcherApi.checkForUpdates());
      }
    })
  );
  els.odSave.addEventListener("click", () => run(saveOpenDotaKey));
  els.odKey.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      run(saveOpenDotaKey);
    }
  });
  els.odGet.addEventListener("click", () => run(() => window.launcherApi.openAiKeyPage("opendota")));
  els.odClear.addEventListener("click", () =>
    run(async () => {
      await window.launcherApi.player("odClear");
      await refreshOpenDota();
    })
  );
  document.querySelector("#tab-settings")?.addEventListener("click", () => run(refreshOpenDota));
  els.whatsNewDismiss.addEventListener("click", () =>
    run(async () => renderStatus(await window.launcherApi.dismissWhatsNew()))
  );
  // The invite: the link goes to the clipboard, the button says so, then the card goes.
  els.inviteCopy.addEventListener("click", () =>
    run(async () => {
      const status = await window.launcherApi.invite("copy");
      flashLabel(els.inviteCopy.querySelector("span"), tr("inviteCopied"));
      setTimeout(() => renderStatus(status), 1400);
    })
  );
  els.inviteDismiss.addEventListener("click", () =>
    run(async () => renderStatus(await window.launcherApi.invite("dismiss")))
  );
  els.tourStart.addEventListener("click", () => startTour());
  els.setupDismiss.addEventListener("click", () =>
    run(async () => renderStatus(await window.launcherApi.dismissSetup()))
  );
  // History backup: one file with every match and review (no keys), merged back on load.
  const backupButtons = () => [els.backupExport, els.backupImport];
  async function backupRun(action) {
    backupButtons().forEach((button) => (button.disabled = true));
    try {
      const result = await action();
      if (result && result.canceled) {
        els.backupHint.textContent = tr("backupHint");
        return;
      }
      if (result && result.ok) {
        els.backupHint.textContent = result.path
          ? tr("backupSaved", result.matches, result.path.split(/[\\/]/).pop())
          : tr("backupLoaded", result.imported?.matches?.added ?? 0, result.linked);
      } else {
        els.backupHint.textContent = tr(result?.code === "not_backup" ? "backupNotBackup" : result?.code === "newer_version" ? "backupNewer" : "backupFailed");
      }
    } finally {
      backupButtons().forEach((button) => (button.disabled = false));
    }
  }
  els.backupExport.addEventListener("click", () => run(() => backupRun(() => window.launcherApi.exportHistory())));
  // The same history by a one-time code (main.js sendHistoryByCode / receiveHistoryByCode).
  const transferError = (code) => trOr(`transferErrors.${code}`, tr("transferErrors.fallback"));
  async function transferRun(button, busyText, action) {
    transferBusy = true;
    button.disabled = true;
    els.transferCode.hidden = true;
    els.transferHint.textContent = busyText;
    try {
      await action();
    } finally {
      transferBusy = false;
      button.disabled = false;
    }
  }
  els.transferSend.addEventListener("click", () =>
    run(() =>
      transferRun(els.transferSend, tr("transferSending"), async () => {
        const result = await window.launcherApi.sendHistoryByCode();
        if (result && result.ok) {
          const time = result.expiresAt ? new Date(result.expiresAt).toLocaleTimeString(locale === "ru" ? "ru-RU" : "en-GB", { hour: "2-digit", minute: "2-digit" }) : "—";
          els.transferCode.textContent = result.code;
          els.transferCode.hidden = false;
          els.transferHint.textContent = tr("transferReady", result.matches, time);
        } else {
          els.transferHint.textContent = result?.code === "backend_down" ? tr("backupFailed") : transferError(result?.code);
        }
      })
    )
  );
  // «I have a code» opens the field on the receiving computer; the sending
  // one never needs it, so it stays folded.
  els.transferHave.addEventListener("click", () => {
    const open = els.transferForm.hidden;
    els.transferForm.hidden = !open;
    els.transferHave.setAttribute("aria-expanded", String(open));
    if (open) {
      els.transferInput.focus();
    }
  });
  els.transferForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const code = els.transferInput.value.trim();
    if (!code) {
      els.transferInput.focus();
      return;
    }
    run(() =>
      transferRun(els.transferReceive, tr("transferReceiving"), async () => {
        const result = await window.launcherApi.receiveHistoryByCode(code);
        if (result && result.ok) {
          els.transferInput.value = "";
          els.transferHint.textContent = tr("backupLoaded", result.imported?.matches?.added ?? 0, result.linked);
        } else {
          els.transferHint.textContent = result?.code === "newer_version" ? tr("backupNewer") : result?.code === "backend_down" ? tr("backupFailed") : transferError(result?.code);
        }
      })
    );
  });
  els.backupImport.addEventListener("click", () => run(() => backupRun(() => window.launcherApi.importHistory())));
  els.reportAction.addEventListener("click", () =>
    run(async () => {
      els.reportAction.disabled = true;
      reportSticky = true;
      setReportHint(tr("reportSaving"));
      try {
        const result = await window.launcherApi.saveProblemReport();
        setReportHint(
          result && result.ok ? tr("reportSaved", result.path.split(/[\\/]/).pop()) : tr("reportFailed"),
          result && result.ok ? result.path : result?.error || ""
        );
      } finally {
        els.reportAction.disabled = false;
      }
    })
  );
  els.reportOpen.addEventListener("click", () => toggleReportPanel(els.reportPanel.hidden));
  els.reportCancel.addEventListener("click", () => toggleReportPanel(false));
  els.reportPreview.addEventListener("toggle", () => {
    if (els.reportPreview.open && !reportPreviewLoaded) {
      reportPreviewLoaded = true;
      els.reportPreviewText.textContent = tr("reportPreviewLoading");
      window.launcherApi
        .previewProblemReport()
        .then((text) => {
          els.reportPreviewText.textContent = text;
        })
        .catch(() => {
          reportPreviewLoaded = false;
          els.reportPreviewText.textContent = tr("reportFailed");
        });
    }
  });
  els.reportPrivacy.addEventListener("click", () => run(() => window.launcherApi.openPrivacy()));
  els.reportSend.addEventListener("click", () =>
    run(async () => {
      els.reportSend.disabled = true;
      els.reportCancel.disabled = true;
      setReportHint(tr("reportSending"));
      try {
        const result = await window.launcherApi.sendProblemReport(els.reportNote.value);
        if (result?.ok) {
          setReportHint(tr("reportSentId", result.id));
          reportSticky = true;
          toggleReportPanel(false);
          els.reportNote.value = "";
        } else if (result?.queued) {
          setReportHint(tr("reportQueued"));
          reportSticky = true;
          toggleReportPanel(false);
        } else {
          setReportHint(tr("reportRefused", (result?.path || "").split(/[\\/]/).pop()), result?.path || "");
          reportSticky = true;
        }
      } finally {
        els.reportSend.disabled = false;
        els.reportCancel.disabled = false;
      }
    })
  );
  els.shareStats.addEventListener("change", () =>
    run(async () => {
      serverDeleteNote = "";
      renderStatus(await window.launcherApi.setShareStats(els.shareStats.checked));
    })
  );
  els.statsPreview.addEventListener("toggle", () => {
    if (!els.statsPreview.open) {
      return;
    }
    // Always fresh: the counts change with every match.
    els.statsPreviewText.textContent = tr("statsPreviewLoading");
    Promise.resolve(window.launcherApi.statsPreview())
      .then((result) => {
        els.statsPreviewText.textContent = result && result.ok ? result.text : tr("statsPreviewFailed");
      })
      .catch(() => {
        els.statsPreviewText.textContent = tr("statsPreviewFailed");
      });
  });
  els.statsPrivacy.addEventListener("click", () => run(() => window.launcherApi.openPrivacy()));
  els.serverDelete.addEventListener("click", () =>
    run(async () => {
      // Two presses: the first one asks, for a few seconds.
      if (!serverDeleteArmed) {
        serverDeleteArmed = true;
        els.serverDelete.querySelector("span").textContent = tr("serverDeleteConfirm");
        setTimeout(() => {
          serverDeleteArmed = false;
          els.serverDelete.querySelector("span").textContent = tr("serverDelete");
        }, 5000);
        return;
      }
      serverDeleteArmed = false;
      els.serverDelete.disabled = true;
      try {
        const result = await window.launcherApi.deleteServerData();
        serverDeleteNote = result && result.ok ? tr("serverDeleted") : tr("serverDeleteFailed", (result && result.code) || "?");
        els.serverDelete.querySelector("span").textContent = tr("serverDelete");
        if (result && result.status) {
          renderStatus(result.status);
        }
      } finally {
        els.serverDelete.disabled = false;
      }
    })
  );
  els.discordPresence.addEventListener("change", () =>
    run(async () => renderStatus(await window.launcherApi.setDiscordPresence(els.discordPresence.checked)))
  );
  async function weeklyRun(button, action, url) {
    if (weeklyBusy) {
      return;
    }
    weeklyBusy = true;
    button.disabled = true;
    if (action === "send") {
      weeklyMessage = tr("weeklySending");
      renderWeekly(lastWeekly);
    }
    try {
      const result = await window.launcherApi.discordWeekly(action, url);
      if (result && result.ok) {
        weeklyMessage = action === "send" && !result.sent ? tr("weeklyNoMatchesNow") : "";
        if (action === "set") {
          els.weeklyInput.value = "";
        }
      } else {
        weeklyMessage = trOr(`weeklyErrors.${result?.code}`, tr("weeklyErrors.fallback"));
      }
      if (result && result.status) {
        renderStatus(result.status);
      }
    } finally {
      weeklyBusy = false;
      button.disabled = false;
      renderWeekly(lastWeekly);
    }
  }
  els.weeklyForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const url = els.weeklyInput.value.trim();
    if (!url) {
      els.weeklyInput.focus();
      return;
    }
    run(() => weeklyRun(els.weeklyConnect, "set", url));
  });
  els.weeklySend.addEventListener("click", () => run(() => weeklyRun(els.weeklySend, "send")));
  els.weeklyClear.addEventListener("click", () => run(() => weeklyRun(els.weeklyClear, "clear")));
  els.autostart.addEventListener("change", () =>
    run(async () => {
      await window.launcherApi.setAutostart(els.autostart.checked);
      renderStatus(await window.launcherApi.getStatus());
    })
  );

  // Remember whether the developer section was open (per-user convenience).
  try {
    els.devTools.open = localStorage.getItem(DEV_OPEN_KEY) === "1";
  } catch {
    // Storage unavailable: start collapsed.
  }
  els.devTools.addEventListener("toggle", () => {
    try {
      localStorage.setItem(DEV_OPEN_KEY, els.devTools.open ? "1" : "0");
    } catch {
      // Ignore.
    }
  });

  window.launcherApi.onStatus(renderStatus);
  window.launcherApi.onLogs(renderLogs);

  renderLogs(await window.launcherApi.getLogs());
  renderStatus(await window.launcherApi.getStatus());
}

// "Copied" for a moment, then the label the next render gives it.
// ---------------------------------------------------------------------------
// First-run tour (renderer/tour.js draws it; the steps and texts are here)
// ---------------------------------------------------------------------------

const TOUR_STEPS = [
  { id: "welcome", view: "home" },
  { id: "status", view: "home", target: "#status" },
  { id: "setup", view: "home", target: "#setup-card" },
  { id: "match", view: "home", target: "#match-card" },
  { id: "matches", view: "home", target: "#tab-matches" },
  { id: "progress", view: "home", target: "#tab-progress" },
  { id: "settings", view: "settings", target: "#overlay-card" },
  { id: "voice", view: "settings", target: "#advice-settings-card" },
  { id: "done", view: "home" }
];

let tourShown = false;
let activeTour = null;

function openTourView(view) {
  const tab = document.querySelector(`#tab-${view}`);
  if (tab && tab.getAttribute("aria-selected") !== "true") {
    tab.click();
  }
}

function startTour() {
  if (activeTour || !window.LauncherTour) {
    return;
  }
  tourShown = true;
  activeTour = window.LauncherTour.start({
    steps: TOUR_STEPS.map((step) => ({ ...step, title: tr(`tour.steps.${step.id}.title`), text: tr(`tour.steps.${step.id}.text`) })),
    labels: {
      next: tr("tour.next"),
      back: tr("tour.back"),
      skip: tr("tour.skip"),
      done: tr("tour.done"),
      count: (i, n) => tr("tour.count", i, n)
    },
    openView: openTourView,
    viewSelector: ".view",
    onClose: () => {
      activeTour = null;
      openTourView("home");
      run(async () => renderStatus(await window.launcherApi.tourDone()));
    }
  });
}

function flashLabel(element, text) {
  const previous = element.textContent;
  element.textContent = text;
  setTimeout(() => {
    if (element.textContent === text) {
      element.textContent = previous;
    }
  }, 1600);
}

async function run(handler) {
  try {
    return await handler();
  } catch (error) {
    renderLogs(`${els.logs.textContent || ""}\n[renderer] ${error.message || error}\n`);
    return undefined;
  }
}

function bind(selector, handler) {
  const element = $(selector);
  if (element) {
    element.addEventListener("click", () => run(handler));
  }
}

async function checkGsi() {
  updateGsiDetail(await window.launcherApi.checkGsi(els.gsiPath.value));
}

async function installGsi(customPath) {
  updateGsiDetail(await window.launcherApi.installGsi(customPath));
}

async function chooseGsiFolder() {
  const folder = await window.launcherApi.chooseGsiFolder();
  if (folder) {
    els.gsiPath.value = folder;
    await checkGsi();
  }
}

async function checkLiveGsi() {
  renderLiveStatus(await window.launcherApi.checkLiveGsi());
}

async function startLiveRecording() {
  await window.launcherApi.startLiveRecording();
  await checkLiveGsi();
}

async function stopLiveRecording() {
  await window.launcherApi.stopLiveRecording();
  await checkLiveGsi();
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

function renderStatus(status) {
  if (!status) {
    return;
  }
  locale = I18N[status.locale] ? status.locale : "en";
  applyStaticTexts();
  gsiEndpoint = status.gsiEndpoint || "";
  document.body.dataset.loading = String(isLoading(status));

  renderService(status);
  renderStatusLine(status);
  renderSetup(status);
  renderWhatsNew(status);
  els.inviteCard.classList.toggle("hidden", !status.invite);
  // «Now» (current match, recent advice) only while Dota runs or there is advice
  // to show; with Dota closed the summary and the week lead.
  const live = status.live || {};
  els.nowZone.classList.toggle(
    "hidden",
    !(status.dotaRunning || live.inMatch || live.connected || (status.recentAdvice || []).length || status.demo === "running")
  );
  if (status.tour && !tourShown) {
    // The first start: the tour opens once the panel has drawn its first status.
    tourShown = true;
    setTimeout(() => startTour(), 400);
  }
  renderReport(status);
  if (status.backend === "running" && !openDotaLoaded) {
    openDotaLoaded = true;
    run(refreshOpenDota);
  }
  renderMatch(status);
  renderAdvice(status);
  renderOverlaySettings(status);
  renderFacts(status);
  renderControlButtons(status);
  renderLogMode(status.logMode || "clean");
  updateGsiDetail({ status: status.gsiConfig, path: status.gsiPath });
  // Matches / Progress views (renderer/matches.js).
  window.PlayerViews?.onStatus(status);
}

function setReportHint(text, title = "") {
  els.reportHint.textContent = text;
  els.reportHint.title = title;
}

function renderReport(status) {
  if (reportSticky) {
    return;
  }
  const report = status.report || {};
  const parts = [tr("reportHint")];
  if (report.queued) {
    parts.push(tr("reportQueuedCount", report.queued));
  } else if (report.last?.id) {
    parts.push(tr("reportLast", report.last.id));
  }
  setReportHint(parts.join(". "));
}

function toggleReportPanel(open) {
  els.reportPanel.hidden = !open;
  els.reportOpen.setAttribute("aria-expanded", String(open));
  if (open) {
    reportSticky = false;
    reportPreviewLoaded = false;
    els.reportPreview.open = false;
    els.reportPreviewText.textContent = "";
    els.reportNote.focus();
  }
}

// OpenDota key: the backend keeps it and only ever answers with a hint.
async function refreshOpenDota() {
  const result = await window.launcherApi.player("odStatus");
  renderOpenDota(result && result.ok ? result.data : null);
}

function renderOpenDota(data) {
  const configured = Boolean(data && data.configured);
  els.odForm.classList.toggle("hidden", configured);
  els.odClear.classList.toggle("hidden", !configured || data.source !== "app");
  els.odHint.textContent = !configured
    ? tr("odHintOff")
    : data.source === "env"
      ? tr("odHintEnv")
      : tr("odHintOn", data.key_hint || "");
}

async function saveOpenDotaKey() {
  const key = els.odKey.value.trim();
  if (!key) {
    return;
  }
  els.odSave.disabled = true;
  try {
    const result = await window.launcherApi.player("odSave", { apiKey: key });
    if (result && result.ok) {
      els.odKey.value = "";
      renderOpenDota(result.data);
    } else {
      els.odHint.textContent = tr("odBad");
    }
  } finally {
    els.odSave.disabled = false;
  }
}

// First-run checklist: the required steps in order, then the optional AI coach.
// Hidden once the required steps are done or the player hides it.
function setupSteps(status) {
  const player = status.player || {};
  // Data from the game proves Dota and the config work, wherever Dota lives.
  const dataSeen = Boolean(status.setup?.gsiSeen || status.live?.connected);
  return [
    { id: "service", done: status.backend === "running" },
    { id: "dota", done: Boolean(status.dotaDir || status.dotaRunning || dataSeen), action: () => window.launcherApi.chooseDotaFolder() },
    { id: "gsi", done: status.gsiConfig === "installed" || dataSeen, action: () => window.launcherApi.installGsi("") },
    // Shown only when Steam's saved settings could be read.
    ...(status.launchOption === "ok" || status.launchOption === "missing"
      ? [{ id: "launch", done: status.launchOption === "ok" || dataSeen, action: () => window.launcherApi.copyLaunchOption() }]
      : []),
    { id: "data", done: dataSeen },
    { id: "account", done: Boolean(player.linked), action: () => window.PlayerViews?.setView("matches") },
    {
      id: "ai",
      done: Boolean(player.aiConfigured),
      optional: true,
      action: () => {
        window.PlayerViews?.setView("settings");
        document.getElementById("ai-settings-root")?.scrollIntoView({ block: "start" });
      }
    }
  ];
}

function renderWhatsNew(status) {
  const version = String(status.whatsNew || "");
  const table = (I18N[locale] || I18N.en).whatsNew || {};
  const items = table[version];
  const show = Boolean(version && Array.isArray(items) && items.length);
  els.whatsNewCard.classList.toggle("hidden", !show);
  if (!show || els.whatsNewList.dataset.signature === `${locale}|${version}`) {
    return;
  }
  els.whatsNewList.dataset.signature = `${locale}|${version}`;
  els.whatsNewHeading.textContent = tr("whatsNewTitle", version);
  els.whatsNewList.replaceChildren(
    ...items.map((text) => {
      const item = document.createElement("li");
      item.textContent = text;
      return item;
    })
  );
}

function renderSetup(status) {
  const steps = setupSteps(status);
  const required = steps.filter((step) => !step.optional);
  const doneCount = required.filter((step) => step.done).length;
  const hide = isLoading(status) || status.setup?.dismissed || doneCount === required.length;
  els.setupCard.classList.toggle("hidden", Boolean(hide));
  if (hide) {
    return;
  }
  els.setupCount.textContent = tr("setupCount", doneCount, required.length);
  // The first open step gets the action; later ones wait for it.
  const next = steps.find((step) => !step.done);
  const signature = JSON.stringify([locale, steps.map((step) => step.done), next?.id]);
  if (els.setupSteps.dataset.signature === signature) {
    return;
  }
  els.setupSteps.dataset.signature = signature;
  els.setupSteps.replaceChildren(
    ...steps.map((step) => {
      const [title, hint] = tr(`setup.${step.id}`);
      const item = document.createElement("li");
      item.className = "setup-step";
      item.dataset.done = String(step.done);
      const mark = document.createElement("i");
      mark.className = "setup-mark";
      mark.dataset.icon = step.done ? "circle-check" : "circle";
      const text = document.createElement("span");
      text.className = "setup-text";
      const titleEl = document.createElement("span");
      titleEl.className = "setup-step-title";
      titleEl.textContent = title;
      text.append(titleEl);
      if (!step.done) {
        const hintEl = document.createElement("span");
        hintEl.className = "setup-step-hint";
        hintEl.textContent = hint;
        text.append(hintEl);
      }
      item.append(mark, text);
      if (!step.done && step.action && (step === next || step.optional)) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = step === next && !step.optional ? "btn btn-primary btn-sm" : "btn btn-sm";
        button.textContent = tr(`setupActions.${step.id}`);
        button.addEventListener("click", async () => {
          await run(step.action);
          if (step.id === "launch") {
            flashLabel(button, tr("actions.copied"));
          }
        });
        item.append(button);
      }
      return item;
    })
  );
  window.LucideIcons?.hydrate(els.setupSteps);
}

function isLoading(status) {
  return status.backend === "starting";
}

function isOffline(status) {
  return status.backend === "stopped" || status.backend === "stopping";
}

function renderService(status) {
  const state = status.backend || "stopped";
  els.service.dataset.state = state;
  const port = status.backendPort && state === "running" ? ` · :${status.backendPort}` : "";
  els.serviceText.textContent = `${tr("service")} ${tr(`serviceStates.${state}`)}${port}`;
}

function formatClock(seconds) {
  if (!Number.isFinite(seconds)) {
    return "";
  }
  const sign = seconds < 0 ? "−" : "";
  const total = Math.abs(Math.trunc(seconds));
  return `${sign}${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

function stageLabel(stage) {
  return trOr(`stages.${stage}`, stage);
}

// Decide the single status line and its one action.
function resolveStatusLine(status) {
  const live = status.live || {};
  const api = window.launcherApi;
  const actions = {
    start: { label: tr("actions.start"), icon: "play", run: () => api.startBackend() },
    install: { label: tr("actions.install"), icon: "download", run: () => installGsi("") },
    chooseDota: { label: tr("actions.chooseDota"), icon: "folder-search", run: () => api.chooseDotaFolder() },
    fullscreenSeen: { label: tr("actions.fullscreenSeen"), icon: "eye", run: () => api.dismissFullscreenWarning() },
    copyLaunchOption: { label: tr("actions.copyLaunchOption"), icon: "copy", run: () => api.copyLaunchOption(), doneLabel: tr("actions.copied") }
  };

  if (isLoading(status)) {
    return { state: "loading", title: tr("status.loadingTitle"), hint: tr("status.loadingHint") };
  }
  if (isOffline(status)) {
    return { state: "error", title: tr("status.backendDownTitle"), hint: tr("status.backendDownHint"), action: actions.start };
  }
  if (status.demo === "running") {
    return { state: "ok", title: tr("status.demoTitle", status.demoPreset), hint: tr("status.demoHint") };
  }
  if (status.gsiConfig === "error") {
    return { state: "error", title: tr("status.gsiErrorTitle"), hint: tr("status.gsiErrorHint"), action: actions.chooseDota };
  }
  if (status.gsiConfig !== "installed") {
    return status.dotaDir
      ? { state: "warn", title: tr("status.noGsiTitle"), hint: tr("status.noGsiHint"), action: actions.install }
      : { state: "error", title: tr("status.noDotaTitle"), hint: tr("status.noDotaHint"), action: actions.chooseDota };
  }
  if (status.dotaFullscreen) {
    // Sent only while Dota runs in exclusive fullscreen with the overlay on.
    return {
      state: "warn",
      title: tr("status.fullscreenTitle"),
      hint: tr("status.fullscreenHint"),
      action: actions.fullscreenSeen
    };
  }
  if (live.inMatch) {
    const hint = status.overlay === "running" ? tr("status.inGameHint") : tr("status.inGameOverlayOff");
    return { state: "ok", title: tr("status.inGameTitle", live.hero, formatClock(live.clockTime)), hint };
  }
  if (!status.dotaRunning) {
    return { state: "idle", title: tr("status.notRunningTitle"), hint: tr("status.notRunningHint") };
  }
  if (!live.connected && status.launchOption === "missing") {
    // Dota runs, the config is there, but nothing arrives: the usual cause.
    return { state: "warn", title: tr("status.launchOptionTitle"), hint: tr("status.launchOptionHint"), action: actions.copyLaunchOption };
  }
  // Dota runs outside a match: say plainly whether its data reaches the coach.
  return live.connected
    ? { state: "ok", title: tr("status.connectedTitle"), hint: tr("status.waitingHintConnected") }
    : { state: "warn", title: tr("status.noDataTitle"), hint: tr("status.waitingHintNoData") };
}

function renderStatusLine(status) {
  const line = resolveStatusLine(status);
  els.status.dataset.state = line.state;
  els.statusTitle.textContent = line.title;
  els.statusHint.textContent = line.hint || "";
  statusAction = line.action || null;
  els.statusAction.classList.toggle("hidden", !statusAction);
  if (statusAction) {
    els.statusActionLabel.textContent = statusAction.label;
    const icon = els.statusAction.querySelector("i[data-icon]");
    icon.dataset.icon = statusAction.icon;
    window.LucideIcons?.hydrate(els.statusAction);
  }
}

function skeleton(widthClass) {
  const span = document.createElement("span");
  span.className = `skeleton skeleton-line ${widthClass}`;
  return span;
}

function setEmpty(container, visible, { title, hint, icon } = {}) {
  container.classList.toggle("hidden", !visible);
  if (!visible) {
    return;
  }
  const iconEl = container.querySelector("i[data-icon]");
  if (icon && iconEl && iconEl.dataset.icon !== icon) {
    iconEl.dataset.icon = icon;
    window.LucideIcons?.hydrate(container);
  }
  if (title !== undefined) {
    container.querySelector(".empty-title").textContent = title;
  }
  if (hint !== undefined) {
    container.querySelector(".empty-hint").textContent = hint;
  }
}

function renderMatch(status) {
  const live = status.live || {};
  if (isLoading(status)) {
    els.matchStats.classList.remove("hidden");
    setEmpty(els.matchEmpty, false);
    delete els.statHero.dataset.hero;
    els.statHero.replaceChildren(skeleton("w-70"));
    els.statClock.replaceChildren(skeleton("w-40"));
    els.statStage.replaceChildren(skeleton("w-60"));
    els.statData.replaceChildren(skeleton("w-50"));
    return;
  }
  els.coverageNote.classList.add("hidden");
  els.roleNote.classList.add("hidden");
  if (isOffline(status)) {
    els.matchStats.classList.add("hidden");
    setEmpty(els.matchEmpty, true, { title: tr("offlineTitle"), hint: tr("offlineHint"), icon: "wifi-off" });
    return;
  }
  if (!live.inMatch) {
    els.matchStats.classList.add("hidden");
    setEmpty(els.matchEmpty, true, { title: tr("matchEmptyTitle"), hint: tr("matchEmptyHint"), icon: "clock" });
    return;
  }
  els.matchStats.classList.remove("hidden");
  setEmpty(els.matchEmpty, false);
  const coverageKey = live.coverage === "safety" ? "coverageSafety" : live.coverage === "support" ? "coverageSupport" : null;
  els.coverageNote.classList.toggle("hidden", !coverageKey);
  if (coverageKey) {
    els.coverageNote.textContent = tr(coverageKey);
  }
  const role = live.role && tr(`roleNames.${live.role.role}`);
  els.roleNote.classList.toggle("hidden", !live.role);
  els.roleNote.textContent = live.role ? tr("roleNote", role, tr(`roleSource.${live.role.source}`)) : "";
  if (live.hero && window.DotaIcons?.hero(live.hero)) {
    // Keep the element while the hero stays the same (no flicker every second).
    if (els.statHero.dataset.hero !== live.hero) {
      els.statHero.dataset.hero = live.hero;
      const name = document.createElement("span");
      name.textContent = live.hero;
      const label = document.createElement("span");
      label.className = "with-pic";
      label.append(window.DotaIcons.heroPicture(document, live.hero, "sm"), name);
      els.statHero.replaceChildren(label);
    }
  } else {
    delete els.statHero.dataset.hero;
    els.statHero.textContent = live.hero || "—";
  }
  els.statClock.textContent = formatClock(live.clockTime) || "—";
  els.statStage.textContent = live.stage && live.stage !== "unknown" ? stageLabel(live.stage) : "—";
  const seconds = Number.isFinite(live.secondsSinceLastGsi) ? live.secondsSinceLastGsi.toFixed(1) : null;
  const dot = document.createElement("span");
  dot.className = "dot";
  dot.dataset.tone = live.connected ? "ok" : "warn";
  const text = document.createElement("span");
  text.className = "num";
  text.textContent = seconds === null ? "—" : tr("dataFresh", seconds);
  els.statData.replaceChildren(dot, text);
}

function priorityTone(priority) {
  const value = String(priority || "").toLowerCase();
  if (value === "high" || value === "urgent") {
    return "error";
  }
  if (value === "medium") {
    return "warn";
  }
  if (value === "low" || value === "safe") {
    return "ok";
  }
  return "";
}

function renderAdvice(status) {
  if (isLoading(status)) {
    els.adviceEmpty.classList.add("hidden");
    els.adviceList.classList.remove("hidden");
    els.adviceList.replaceChildren(
      ...["w-80", "w-60", "w-70"].map((width) => {
        const item = document.createElement("li");
        item.className = "advice-item";
        item.append(skeleton(width));
        return item;
      })
    );
    return;
  }
  const items = Array.isArray(status.recentAdvice) ? status.recentAdvice : [];
  const offline = isOffline(status);
  if (offline || !items.length) {
    els.adviceList.classList.add("hidden");
    els.adviceList.replaceChildren();
    setEmpty(els.adviceEmpty, true, {
      title: offline ? tr("offlineTitle") : tr("adviceEmptyTitle"),
      hint: offline ? tr("offlineHint") : tr("adviceEmptyHint"),
      icon: offline ? "wifi-off" : "sparkles"
    });
    return;
  }
  els.adviceEmpty.classList.add("hidden");
  els.adviceList.classList.remove("hidden");
  const firstRender = seenAdvice.size === 0;
  els.adviceList.replaceChildren(
    ...items.map((advice) => {
      const key = `${advice.timestamp}|${advice.action}`;
      const item = document.createElement("li");
      item.className = "advice-item";
      if (!firstRender && !seenAdvice.has(key)) {
        item.classList.add("is-new");
      }
      seenAdvice.add(key);

      const dot = document.createElement("span");
      dot.className = "dot";
      const tone = priorityTone(advice.priority);
      if (tone) {
        dot.dataset.tone = tone;
      }
      const priority = String(advice.priority || "").toLowerCase();
      dot.title = trOr(`priority.${priority}`, priority);

      const action = document.createElement("span");
      action.className = "advice-action";
      action.textContent = advice.action || "";
      action.title = advice.action || "";

      const time = document.createElement("span");
      time.className = "advice-time";
      time.textContent = advice.game_time || "";

      const reason = document.createElement("span");
      reason.className = "advice-reason";
      reason.textContent = advice.reason || "";
      reason.title = advice.reason || "";

      item.append(dot, action, time, reason);
      // What the coach saw (backend advice_why.py), folded: the list redraws
      // every second, so the open ones are remembered by key.
      if (advice.why) {
        const why = document.createElement("details");
        why.className = "advice-why";
        why.open = openWhy.has(key);
        why.addEventListener("toggle", () => (why.open ? openWhy.add(key) : openWhy.delete(key)));
        const summary = document.createElement("summary");
        summary.textContent = tr("adviceWhy");
        const text = document.createElement("p");
        text.textContent = advice.why;
        why.append(summary, text);
        item.append(why);
      }
      return item;
    })
  );
}

function renderOverlaySettings(status) {
  const enabled = status.overlay === "running";
  els.overlayToggle.checked = enabled;
  els.overlayHint.textContent = !enabled
    ? tr("overlayReason.off")
    : status.overlayVisible
      ? tr("overlayReason.in_game")
      : tr(`overlayReason.${status.overlayReasonCode || "no_match"}`);

  const position = status.overlayPosition || "right-center";
  for (const button of els.positionButtons) {
    button.setAttribute("aria-checked", String(button.dataset.position === position));
    button.disabled = !enabled;
  }
  els.positionHint.textContent = position === "custom" ? tr("positionCustom") : tr("positionHint");

  const language = status.language || "auto";
  for (const button of els.languageButtons) {
    button.setAttribute("aria-checked", String(button.dataset.language === language));
  }

  const size = status.overlaySize || "normal";
  for (const button of els.sizeButtons) {
    button.setAttribute("aria-checked", String(button.dataset.size === size));
    button.disabled = !enabled;
  }

  const display = status.overlayDisplay || { timers: true, compact: false };
  els.overlayTimers.checked = display.timers !== false;
  els.overlayCompact.checked = display.compact === true;
  els.overlayTimers.disabled = !enabled;
  els.overlayCompact.disabled = !enabled;

  const frequency = status.adviceFrequency || "normal";
  for (const button of els.frequencyButtons) {
    button.setAttribute("aria-checked", String(button.dataset.frequency === frequency));
  }
  els.frequencyHint.textContent = tr(`frequencyHint.${frequency}`);

  const role = status.adviceRole || "auto";
  for (const button of els.roleButtons) {
    button.setAttribute("aria-checked", String(button.dataset.role === role));
  }
  els.roleHint.textContent = tr(`roleHint.${role}`);
  els.mapHints.checked = status.mapHints !== false;

  lastVoice = status.overlayVoice || { mode: "off", volume: 1 };
  for (const button of els.voiceButtons) {
    button.setAttribute("aria-checked", String(button.dataset.voice === lastVoice.mode));
    button.disabled = !enabled;
  }
  els.voiceTest.disabled = !enabled;
  renderVoiceHint(lastVoice);

  const moving = status.overlayLocked === false;
  els.moveToggle.setAttribute("aria-pressed", String(moving));
  els.moveToggle.disabled = !enabled;
  els.moveLabel.textContent = moving ? tr("moveDone") : tr("moveStart");
  els.moveHint.textContent = moving ? tr("moveActiveHint") : tr("moveHint");

  els.shareStats.checked = Boolean(status.shareStats);
  const statsDate = status.statsSentAt
    ? new Date(status.statsSentAt).toLocaleDateString(locale === "ru" ? "ru-RU" : "en-GB", { day: "numeric", month: "long" })
    : "";
  els.statsHint.textContent =
    serverDeleteNote || (!status.shareStats ? tr("statsOff") : statsDate ? tr("statsSent", statsDate) : tr("statsOn"));

  els.discordPresence.checked = status.discordPresence !== false;
  const discordState = status.discordState || { state: "idle" };
  // "Waiting for Dota" repeats the hint above: only the other states are shown.
  els.discordState.hidden = status.discordPresence === false || discordState.state === "idle";
  els.discordState.textContent =
    discordState.state === "rejected"
      ? tr("discordStates.rejected", discordState.error || "?")
      : trOr(`discordStates.${discordState.state}`, tr("discordStates.idle"));
  renderWeekly(status.discordWeekly || null);
  els.autostart.checked = Boolean(status.autostart);
  els.autostart.disabled = !status.autostartSupported;
  els.autostartHint.textContent = !status.autostartSupported
    ? tr("autostartUnavailable")
    : status.autostart
      ? tr("autostartOn")
      : tr("autostartOff");

  renderUpdate(status);
}

// The overlay speaks with the system voices; the panel only checks that one
// exists for the UI language and plays a sample.
function systemVoice() {
  return window.OverlayVoice && window.speechSynthesis
    ? window.OverlayVoice.pickVoice(window.speechSynthesis.getVoices(), locale)
    : null;
}

function renderVoiceHint(voice) {
  const mode = voice?.mode || "off";
  const found = systemVoice();
  if (mode !== "off" && !found && voiceListLoaded()) {
    els.voiceHint.textContent = tr("voiceNoVoice");
    return;
  }
  els.voiceHint.textContent = [tr(`voiceHint.${mode}`), mode !== "off" && found ? found.name : ""]
    .filter(Boolean)
    .join(" · ");
}

// Chromium fills the voice list asynchronously: an empty list right after
// start does not yet mean there are no voices.
function voiceListLoaded() {
  return (window.speechSynthesis?.getVoices() || []).length > 0 || voiceListChecked;
}

function testVoice() {
  const voice = systemVoice();
  if (!voice) {
    voiceListChecked = true;
    els.voiceHint.textContent = tr("voiceNoVoice");
    return;
  }
  const utterance = new window.SpeechSynthesisUtterance(tr("voiceSample"));
  utterance.voice = voice;
  utterance.lang = voice.lang;
  utterance.volume = Number(lastVoice.volume ?? 1);
  utterance.rate = 1.05;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

function renderUpdate(status) {
  const update = status.update || { status: "disabled" };
  const current = status.appVersion || update.currentVersion || "";
  const known = ["disabled", "idle", "checking", "up-to-date", "downloading", "ready", "error"];
  const state = known.includes(update.status) ? update.status : "idle";
  // Installing restarts the app, so it is never offered while Dota runs.
  const blocked = state === "ready" && Boolean(update.blockedByGame);
  const hintKey = blocked ? "blocked" : state;
  els.updateHint.textContent = tr(`updateHint.${hintKey}`, current, update.version || "", update.percent || 0);
  els.updateHint.title = state === "error" ? update.error || "" : "";
  const install = state === "ready";
  els.updateAction.dataset.mode = install ? "install" : "check";
  els.updateAction.classList.toggle("btn-primary", install);
  els.updateLabel.textContent = install ? tr("updateInstall") : tr("updateCheck");
  els.updateAction.disabled = blocked || state === "disabled" || state === "checking" || state === "downloading";
}

function renderFacts(status) {
  const backendPort = status.backendPort && status.backend !== "stopped" ? ` · :${status.backendPort}` : "";
  factEls.backend.textContent = `${tr(`serviceStates.${status.backend || "stopped"}`)}${backendPort}`;
  factEls.dota.textContent = tr(`dotaStates.${status.dota || "not_found"}`);
  factEls.overlay.textContent = status.overlay !== "running" ? tr("off") : status.overlayVisible ? tr("shown") : tr("hidden");
  factEls.overlay.title = status.overlayReason || "";
  factEls.demo.textContent = status.demo === "running"
    ? [tr("running"), status.demoPreset].filter(Boolean).join(" · ")
    : tr("stopped");
  factEls.recording.textContent = status.recording === "running" ? tr("running") : tr("stopped");
  factEls.gsi.textContent = tr(`gsiConfigStates.${status.gsiConfig || "unknown"}`);
  factEls.mode.textContent = trOr(`modes.${status.mode || "Live GSI"}`, status.mode || "Live GSI");
  factEls.llm.textContent = status.llm === "on" ? tr("on") : tr("off");
}

function isActiveProcess(state) {
  return state === "running" || state === "starting";
}

function renderControlButtons(status) {
  const backendRunning = isActiveProcess(status.backend);
  const overlayRunning = isActiveProcess(status.overlay);
  const demoRunning = isActiveProcess(status.demo);
  const recordingRunning = isActiveProcess(status.recording);

  controlButtons.startBackend.disabled = backendRunning;
  controlButtons.restartBackend.disabled = status.backend === "starting" || status.backend === "stopping";
  controlButtons.stopBackend.disabled = !backendRunning;
  controlButtons.startOverlay.disabled = overlayRunning;
  controlButtons.stopOverlay.disabled = !overlayRunning;
  controlButtons.stopDemo.disabled = !demoRunning;
  controlButtons.startRecording.disabled = recordingRunning;
  controlButtons.stopRecording.disabled = !recordingRunning;
  for (const button of demoStartButtons) {
    button.disabled = demoRunning;
    button.title = demoRunning ? tr("demoBusy") : "";
  }
}

function renderLogMode(mode) {
  for (const [name, button] of Object.entries(logModeButtons)) {
    button?.setAttribute("aria-checked", String(name === mode));
  }
}

function updateGsiDetail(result = {}) {
  if (result.path) {
    els.gsiDetail.textContent = tr("gsiPath", result.path, gsiEndpoint);
  } else if (result.status === "not found") {
    els.gsiDetail.textContent = `${tr("gsiPathMissing")}\n${tr("gsiEndpoint", gsiEndpoint)}`;
  } else {
    els.gsiDetail.textContent = tr("gsiEndpoint", gsiEndpoint);
  }
}

function renderLiveStatus(status = {}) {
  const setValue = (element, text, state) => {
    element.textContent = text;
    element.dataset.state = state || "";
  };
  if (status.error) {
    setValue(liveEls.connection, tr("liveUnavailable"), "bad");
    liveEls.advice.textContent = status.error;
    return;
  }
  setValue(liveEls.connection, status.gsi_connected ? tr("liveConnected") : tr("liveWaiting"), status.gsi_connected ? "good" : "bad");
  setValue(liveEls.last, status.seconds_since_last_gsi == null ? "—" : `${status.seconds_since_last_gsi} s`);
  setValue(liveEls.hero, status.hero || "—");
  setValue(liveEls.time, Number.isFinite(status.clock_time) ? formatClock(status.clock_time) : String(status.game_time ?? "—"));
  setValue(liveEls.stage, status.stage ? stageLabel(status.stage) : "—");
  liveEls.advice.textContent = status.current_advice
    ? tr("liveAdvice", status.current_advice)
    : status.last_advice_time
      ? tr("liveAdviceLast", status.last_advice_time)
      : tr("liveAdviceNone");
  const missing = Array.isArray(status.missing_important_fields) && status.missing_important_fields.length
    ? status.missing_important_fields.join(", ")
    : tr("none");
  liveEls.missing.textContent = tr("liveMissing", missing);
}

function renderLogs(logs) {
  els.logs.textContent = logs || "";
  els.logs.scrollTop = els.logs.scrollHeight;
}
