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
      pfTitle: "Profile",
      pfSub: "Your rating, level and achievements with Wardly.",
      pfLevel: (n) => `Level ${n}`,
      pfXp: (into, need) => `${into} / ${need} XP to the next level`,
      pfSparks: "Sparks",
      pfSparksHint: "Earned by playing with the coach: 10 a match, 5 more for a win, more for every achievement tier. Spend them on profile looks.",
      pfGames: "Matches with Wardly",
      pfWithApp: "With the coach",
      pfWinrate: "Win rate",
      pfHours: "Hours with the coach",
      pfNoName: "Player",
      pfRating: "Rating",
      pfRatingNone: "Enter your MMR from Dota to start the graph: every ranked game then moves it.",
      pfRatingMedal: "Estimated from your medal. Enter your MMR from Dota for your own line.",
      pfRatingManual: (step) => `An estimate: a ranked game moves it by about ${step}. Correct it when it drifts from Dota.`,
      pfNow: "Now",
      pfPeak: "Peak",
      pfLast20: "Last 20 games",
      pfRecord: (w, l) => `${w}–${l}`,
      pfMmrLabel: "Your MMR now",
      pfMmrPlaceholder: "e.g. 3200",
      pfMmrSave: "Save",
      pfMmrClear: "Back to the medal estimate",
      pfMmrBad: "Enter a number from 0 to 15000.",
      pfWin: "Win",
      pfLoss: "Loss",
      pfAnchor: "Your number",
      pfAchievements: "Achievements",
      pfAchievementsHint: "For matches played with Wardly. Every tier gives sparks.",
      pfTierNone: "Not started",
      pfTier: (name, tier, tiers) => `${name} · ${tier}/${tiers}`,
      pfDone: "All tiers done",
      pfReward: (n) => `+${n} sparks`,
      pfProgress: (value, target) => `${value} / ${target}`,
      pfEmpty: "Play a match with Wardly running: it starts your level, achievements and sparks.",
      pfFriends: "Friends",
      pfFriendsHint: "Show your profile to friends by a code and see theirs: level, rating, looks and achievements.",
      pfFriendsOff: "Your profile is visible only to you. Show it, and friends who have your code see your card: name, level, medal, achievements, looks and matches with Wardly — no Steam ID and no match list.",
      pfFriendsShow: "Show my profile to friends",
      pfFriendsHide: "Hide my profile",
      pfFriendsCode: "Your friend code",
      pfFriendsCopy: "Copy code",
      pfFriendsCopyLink: "Copy link",
      pfFriendsOpen: "Open the page",
      pfFriendsCopied: "Copied.",
      pfFriendsShowMmr: "Show my rating",
      pfFriendsAdd: "Add",
      pfFriendsAddPlaceholder: "Friend code, e.g. WD-4K7P9QX2",
      pfFriendsEmpty: "No friends yet: send them your code, and add theirs.",
      pfFriendsYou: "You",
      pfFriendsRemove: "Remove",
      pfFriendsWeek: (n) => `${n} this week`,
      pfFriendsMissing: (codes) => `Hidden or not found: ${codes}`,
      pfFriendsErrors: { bad_code: "That is not a friend code.", own_code: "That is your own code.", already: "Already in the list.", too_many: "50 friends at most.", offline: "No connection to the server.", disabled: "Friends are switched off on the server for now.", rate_limited: "Too many requests: try again in an hour.", backend_down: "The coach service is not running." },
      pfShop: "Profile looks",
      pfShopHint: "Spend sparks on how your profile looks. Rare ones need a level or an achievement.",
      pfKinds: { frame: "Avatar frames", banner: "Banners", name: "Name colour", title: "Titles" },
      pfBuy: (price) => `Buy · ${price}`,
      pfWear: "Wear",
      pfWorn: "Worn",
      pfFree: "Free",
      pfNeedSparks: (n) => `${n} more ${n === 1 ? "spark" : "sparks"}`,
      pfLockedHint: "Not open yet: see the line above",
      pfNeedLevel: (n) => `From level ${n}`,
      pfNeedAchievement: (name, tier) => `For «${name}», tier ${tier}`,
      pfShopErrors: { not_enough: "Not enough sparks yet.", locked_level: "Your level is too low for it.", locked_achievement: "It comes with an achievement.", owned: "You already have it." },
      linkTitle: "Link your Steam account",
      linkHint:
        "The coach reads your account from Dota automatically when you play. You can also paste your Friend ID (Dota profile), a steamcommunity.com/profiles/… link or an OpenDota/Dotabuff link.",
      linkPlaceholder: "Friend ID, Steam ID or profile link",
      linkButton: "Link",
      linkSoon: "Once your account is linked, here you get:",
      newerMatch: "Newer",
      olderMatch: "Older",
      newerMatchHint: (hero) => `The newer match${hero ? ` (${hero})` : ""} · ←`,
      olderMatchHint: (hero) => `The older match${hero ? ` (${hero})` : ""} · →`,
      openOnSite: (name) => `Open this match on ${name}`,
      progressSoon: "Once a few matches are reviewed, here you get:",
      linkPerks: {
        matches: [
          ["target", "every game with its score and what to fix first"],
          ["skull", "each death: the minute, the place and what was ready to press"],
          ["swords", "your build next to the pros and players of your rank"]
        ],
        progress: [
          ["trending-up", "your last 10 games against the 10 before"],
          ["repeat", "the mistakes that repeat, and one focus for the next game"],
          ["map", "your heroes, your lanes and where you die most"]
        ],
        profile: [
          ["chart-line", "your rating graph and your level"],
          ["trophy", "achievements and looks for your card"],
          ["users", "friends by code and a leaderboard"]
        ]
      },
      progressSub: "How your game changes from match to match",
      linkErrors: {
        empty: "Enter a Friend ID, Steam ID or profile link.",
        vanity_url: "Custom links (steamcommunity.com/id/…) can't be resolved. Use your Friend ID from the Dota profile.",
        unrecognized: "This doesn't look like a Steam account.",
        out_of_range: "This number is not a valid Steam account.",
        backend_down: "The coach is not running.",
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
      matchesSub: "Every game with its review: open one to see what to fix",
      matchesTableTitle: "Match history",
      progressTitle: "Progress",
      zoneFix: "What to fix",
      zoneFixHint: "The coach's review and the goal for the next game",
      zoneStory: "How the match went",
      zoneStoryHint: "Farm and gold over time, deaths, the advice you got",
      zoneScores: "Scores and comparison",
      zoneScoresHint: "Areas of the game, what went well, your rank",
      zoneMapItems: "Map and items",
      zoneMapItemsHint: "Where you were, what you bought and when",
      zoneTeams: "Teams",
      zoneSummary: "Summary",
      zoneSummaryHint: "Your last 10 matches against the 10 before",
      zoneCoach: "Coach",
      zoneCoachHint: "What keeps coming back and what to train",
      zoneGames: "Games and heroes",
      zoneGamesHint: "The score of every match and your heroes",
      zoneCompare: "Comparison",
      zoneCompareHint: "Players of your rank, enemy heroes, a friend",
      zoneHero: "Your main hero",
      zoneHeroHint: "Your best games against your worst, your build",
      colResult: "Result",
      colHero: "Hero",
      colKda: "K / D / A",
      colGpm: "Gold/min",
      colLh10: "Last hits by 10:00",
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
      filterResult: "Result",
      filterResults: { all: "All", win: "Wins", loss: "Losses" },
      filterHero: "Hero",
      filterAllHeroes: "All heroes",
      filterSummary: (games, winrate, score) =>
        [`${games} ${games === 1 ? "match" : "matches"}`, winrate == null ? null : `${winrate}% wins`, score == null ? null : `average score ${score}`].filter(Boolean).join(" · "),
      skippedModes: (count, turbo, of) =>
        `${count} of your last ${of} games are not reviewed${turbo ? ` (Turbo: ${turbo})` : ""}: Turbo, bot games and special modes have different norms.`,
      filterEmptyTitle: "No matches for this filter",
      filterEmptyHint: "Pick another hero or result.",
      pdfSave: "Save PDF",
      pdfSaved: (name) => `Saved: ${name}`,
      pdfFailed: "Could not save the PDF",
      reviewLoading: "Loading the match…",
      reviewPending: "The review appears once the match data is loaded.",
      reviewError: "Could not open the match",
      reviewRenderFailed: "This is a bug in the app. Please report it (Settings → Help → Report a problem) so it can be fixed.",
      scoreOf: "of 100",
      sourcesParsed: "Full replay parsed by OpenDota",
      sourcesBasic: "Match totals only — the full replay review is not ready yet",
      sourcesGsi: "Recorded by the app during the match",
      parseStatus: {
        waiting_opendota: "Full replay review in a few minutes (OpenDota).",
        parsing: "OpenDota is studying the replay — the review fills in by itself.",
        basic: "Replay not parsed: no minute-by-minute data.",
        not_parsed: "OpenDota could not study the replay, so the review is shorter.",
        gsi_only: "Only the app's own recording is available (OpenDota is off).",
        private: "This match is private on OpenDota. In Dota: Settings → Social → Expose Public Match Data (works for the next matches); the review uses the app's own recording meanwhile.",
        "error:not_found": "OpenDota doesn't have this match yet — try again in a few minutes.",
        "error:offline": "No internet — showing the app's own recording.",
        "error:rate_limited": "OpenDota is busy — try again in a minute.",
        "error:bad_response": "OpenDota answered with an error."
      },
      requestParse: "Request replay parse",
      parseRequested: "Requested — it usually takes 2–10 minutes.",
      focusTitle: "Focus for the next game",
      sectionsTitle: "Breakdown",
      explainTitle: "What does this mean?",
      explainScore:
        "The score (0 to 100) shows how close the match was to good play for your role: lane, farm, survival, fights, items and, for a support, vision, each on its own scale. 65+ is good (B), 80+ is great (A), under 50 is a match to learn from (D). A win or a loss does not change it: you can lose with 80 and win with 30.",
      explainRank:
        "Matchmaking puts players of about the same rank into one game, so the player of your role in this match (on either side) shows what is usual at your rank. Above them — you did better than your rank; below — there is room to grow.",
      explainFocus:
        "The focus is the one mistake you work on. After every match the coach checks whether it happened again: a green mark means it did not. One thing at a time is easier to fix than everything at once.",
      chartTitle: "Over the match",
      mapTitle: "Match map",
      deathsTitle: (count) => `Deaths · ${count}`,
      weekGames: "Matches",
      weekVsPrevious: "vs the week before",
      weekRecord: (w, l) => `${w}W · ${l}L`,
      weekScoreNote: {
        no_score: "No reviewed matches this week yet",
        no_previous: "No matches the week before to compare with",
        no_previous_score: "The week before has no reviewed matches"
      },
      weekChartTitle: "Score of every match this week",
      weekBest: "Best match",
      weekHeroes: "Heroes:",
      weekHeroTitle: (hero, games, wins) => `${hero}: ${games} ${games === 1 ? "match" : "matches"}, ${wins} ${wins === 1 ? "win" : "wins"}`,
      weekProblem: "Most often:",
      weekProblemText: (title, count, of) => `${title} — in ${count} of ${of} matches`,
      weekFocus: "Focus:",
      weekPlanProgress: (met, played, plan) => `${met} of ${played} done · plan: ${plan} matches in a row`,
      weekPlanNext: "Next match",
      sessionGames: "Matches",
      sessionScore: "Average score",
      sessionVsUsual: "vs your usual",
      sessionUsual: (score) => `Your usual: ${score}`,
      sessionNoScore: "No reviewed matches yet",
      sessionTime: (minutes) => (minutes >= 60 ? `${Math.floor(minutes / 60)} h ${String(minutes % 60).padStart(2, "0")} min played` : `${minutes} min played`),
      sessionDeaths: (deaths) => `deaths a match on average: ${deaths}`,
      sessionProblem: "To work on:",
      sessionProblemText: (title, count, of) => `${title} — in ${count} of ${of}`,
      sessionFocus: (title, met, total) => `Focus «${title}»: done in ${met} of ${total}`,
      sessionCopy: "Copy for friends",
      sessionCopied: "Copied",
      sessionPreview: "What will be copied",
      deathsNoPattern: "No repeating cause across these deaths.",
      deathNoFacts: "Nothing else is known about this death.",
      deathGold: (gold) => `${gold} unspent gold`,
      deathAfterRespawn: (seconds) => `${seconds} s after respawning`,
      deathWarned: (time, action) => `The coach warned at ${time}: «${action}»`,
      deathNote: {
        enemy_half: "on the enemy half",
        unspent_gold: "with 1000+ unspent gold",
        warned: "after a warning",
        soon_after_respawn: "right after respawning",
        saver_ready: "a saving item was ready",
        burst: "killed in under 3 s"
      },
      deathLastTitle: "HP in the last 20 s",
      deathBurst: (seconds) => `From 70%+ HP to death in ${seconds} s`,
      deathReady: "Ready and not used:",
      deathReadyStunned: "Ready, but you were disabled:",
      deathZone: { top: "top lane", mid: "mid lane", bot: "bottom lane", jungle: "jungle", base: "base" },
      mapEmpty: "No positions for this match yet. They come from a parsed replay (the app asks OpenDota to parse your 5 newest matches of the week) or from a match played with the app running: your path and where you died.",
      mapHint: {
        path: "Where your hero went (every 15 s, recorded by the app) and where you died.",
        replay: "From the parsed replay: where you stood in the lane, where you placed wards and where you died in team fights.",
        both: "Your path (recorded by the app), laning position, wards from the replay and where you died."
      },
      mapLabels: {
        radiant: "Radiant",
        dire: "Dire",
        death: "Death",
        observer: "Observer ward",
        sentry: "Sentry ward",
        path: "Your path",
        lane: "Laning position",
        spot: "Where deaths repeat"
      },
      mapSpotTitle: (count, place) => `${count} deaths · ${place}`,
      mapSpotLine: (place, count) => `Most often: ${place} (${count} ${count === 1 ? "death" : "deaths"})`,
      watchMoment: "Watch",
      watchMomentHint: "Copies a Dota console command. Open this match's replay in Dota, press \\ for the console and paste it: the replay jumps to about 10 s before this moment.",
      watchCopied: "Copied: paste in the replay console",
      watchFailed: "Could not copy",
      bestOnHeroLine: (score) => `Your best match on this hero (${score})`,
      bestOnHeroNote: (score, when) => `Dashed: your best match on this hero, score ${score} (${when}).`,
      bestOnHeroSelf: (of) => `This is your best match on this hero out of ${of}.`,
      mapDeaths: "Deaths",
      killedBy: (hero) => `Killed by ${hero}`,
      mapSide: { own: "on your half", river: "in the river", enemy: "on the enemy half" },
      mapWards: "Wards placed",
      mapWardsLine: (obs, sen) => `${obs} observer · ${sen} sentry`,
      chartLh: "Last hits",
      chartGold: "Gold earned",
      chartXp: "Experience",
      you: "You",
      target: "Target pace",
      deathsMarker: "Death",
      minuteLabel: (m) => `${m}:00`,
      strengthsTitle: "What went well",
      improveTitle: "What to improve",
      foldMore: (n) => `Show ${n} more`,
      foldLess: "Show less",
      repeatInARow: (n) => `${n} matches in a row — a habit, not bad luck`,
      repeatInLast: (n, of) => `Also in ${n} of your previous ${of} matches`,
      nothingToImprove: "No serious mistakes found in this match.",
      nothingStrong: "Nothing stood out this time.",
      drill: "Drill",
      momentsTitle: "Key moments",
      adviceLogTitle: "Advice during the match",
      adviceWhy: "Why this advice?",
      adviceLogHint: (n, urgent) => `${n} ${n === 1 ? "tip" : "tips"} over the game, ${urgent} urgent. Worth checking whether you followed them.`,
      adviceLogMore: (n) => `Show all ${n}`,
      adviceLogDeath: (time) => `Died at ${time}`,
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
        gpm: "Gold and XP per minute",
        lh: "Last hits / denies",
        nw: "Net worth",
        dmg: "Hero damage",
        duration: "Duration"
      },
      sectionFacts: {
        laning: (s) => [s.lh10 != null && `${s.lh10} last hits by 10:00`, s.lane_efficiency != null && `lane efficiency ${Math.round(s.lane_efficiency)}%`, s.lane_deaths ? `${s.lane_deaths} deaths in lane` : null, s.runes != null && `${s.runes} runes${s.enemy_runes != null ? ` (enemy mid ${s.enemy_runes})` : ""}`],
        farm: (s) => [s.gpm != null && `${s.gpm} gold a minute`, s.gpm_pct != null && `better than ${Math.round(s.gpm_pct * 100)}%`],
        survival: (s) => [`${s.deaths} deaths`, s.deaths_per_10 != null && `${s.deaths_per_10} per 10 min`],
        fights: (s) => [s.kill_participation != null && `${s.kill_participation}% kill participation`, s.stuns != null && `${s.stuns} s of stuns${s.enemy_stuns != null ? ` (enemy offlaner ${s.enemy_stuns} s)` : ""}`, s.enemy_tower_damage != null && s.tower_damage != null && `${s.tower_damage} building damage (enemy offlaner ${s.enemy_tower_damage})`],
        items: (s) => [
          s.first_item && `${s.first_item.item} at ${clock(s.first_item.t)}`,
          s.save_item && `Save item: ${s.save_item.item} at ${clock(s.save_item.t)}`,
          "save_item" in s && !s.save_item && "No save item"
        ],
        vision: (s) => [s.obs_placed != null && `${s.obs_placed} observers`, s.sen_placed != null && `${s.sen_placed} sentries`, s.camps_stacked != null && `${s.camps_stacked} stacks`]
      },
      progressEmptyTitle: "Not enough matches yet",
      progressEmptyHint: "Statistics appear after a few reviewed matches. Refresh your history on the Matches tab.",
      tiles: { winrate: "Win rate", kda: "KDA", gpm: "Gold per minute", lh10: "Last hits at 10:00", score: "Avg. score" },
      vsPrevious: (n) => `vs previous ${n}`,
      streakWin: (n) => `${n} wins in a row`,
      streakLoss: (n) => `${n} losses in a row`,
      recordLine: (w, l, n) => `${w}W – ${l}L over ${n} matches`,
      scoreChartTitle: "Score by match",
      scoreChartHint: "Last 20 matches, oldest on the left. Click a column to open the review; no column means the match has no detailed review.",
      scoreLabel: "Score",
      winKey: "win",
      lossKey: "loss",
      baselineIntro: (games, hero) => `Against your ${games} other ${games === 1 ? "match" : "matches"} on ${hero}:`,
      baselineLabels: { score: "score", gpm: "gold/min", lh_10: "last hits at 10", deaths: "deaths" },
      baselineSame: "as usual",
      baselineTitle: (average) => `Your average: ${average}`,
      goalTitle: "Your focus",
      goalHint: "One problem at a time: every next match shows whether it came back.",
      goalSince: (date) => `since ${date}`,
      goalProgress: (met, total) => `Done in ${met} of ${total} ${total === 1 ? "match" : "matches"}`,
      goalWaiting: "Play a match: after it you will see here whether it worked.",
      goalStreak: (n) => `${n} matches in a row without it`,
      goalClear: "Stop tracking",
      goalSet: "Make it my focus",
      goalSetFailed: "Could not save the focus, try again",
      goalCurrent: "Focus",
      goalMet: "done",
      goalMissed: "happened again",
      goalMatch: (title, met) => `Your focus «${title}»: ${met ? "done in this match" : "it happened again"}`,
      planTitle: "What to work on",
      planHint: "Problems that keep coming back in your recent matches, with one drill each.",
      planEmpty: "No repeated problems found — keep it up.",
      strengthsRecurring: "Your strengths",
      heroesTitle: "Heroes",
      colMatches: "Matches",
      colWinrate: "Win rate",
      analyzed: (a, n) => `${a} of ${n} matches reviewed in depth`,
      buildTitle: "Build",
      lanesTitle: "Your lanes",
      lanesLine: (won, even, lost, games) => `Of your last ${games} lanes: ${won} won, ${even} even, ${lost} lost.`,
      lanesGold: (diff) => `On average ${diff} gold against your lane opponent by minute 10.`,
      lanesHard: (list) => `Lanes lost more than once against: ${list}.`,
      lanesDot: (hero, enemy, result, diff) => `${hero} against ${enemy}: ${result}, ${diff} gold by minute 10`,
      laneTitle: "Lane",
      laneVs: "against",
      laneResult: { won: "Lane won", even: "Even lane", lost: "Lane lost" },
      laneMinute: (m) => `${m}:00`,
      laneColMinute: "Minute",
      laneColLh: "Last hits",
      laneColDn: "Denies",
      laneColGold: "Gold",
      laneColXp: "XP",
      laneTurn: (m) => `The gap opened at minute ${m}.`,
      laneOthers: (heroes, diff) => `Also in the lane: ${heroes}; the whole lane's gold by minute 10: ${diff}.`,
      laneNote: "You : them; gold and XP as the difference. From the parsed replay.",
      skillsTitle: "Skill order",
      skillsYours: "Yours first:",
      skillsPro: "How pros max their skills on this hero:",
      skillsSame: (name) => `You also maxed ${name} first, like the pros.`,
      skillsDiff: (yours, pro) => `You maxed ${yours} first; pros start with ${pro}.`,
      skillsNote: (agree, games) => `${agree} of ${games} recent pro games start this way. The in-game tip names where each point goes.`,
      buildTimingNote: "Win rate of the hero by purchase time (OpenDota public matches). Your timing is highlighted. The earliest timings mostly come from games that were already going well, so the target is the usual timing.",
      buildNoTimings: "No timing data for these items yet.",
      buildItemLine: (wr, t, typicalT, typicalWr) => `${wr}% wins when bought by ${t} · usually bought by ${typicalT} — ${typicalWr}%`,
      buildItemTypical: (wr, t) => `${wr}% wins when bought by ${t} · the usual timing for the hero`,
      buildBy: (t) => `by ${t}`,
      buildPopular: "Common build (pro players)",
      buildPhase: { early: "Early", mid: "Core", late: "Late" },
      buildBought: "bought",
      buildTimingTip: (t) => `Bought by ${t}`,
      winrateLabel: "Win rate",
      rankTitle: "You and your rank",
      rankMatchNote: (rank, role, heroes) => `${rank ? `Match rank: ${rank} · ` : ""}compared with the ${role} of this match${heroes ? ` (${heroes})` : ""}`,
      rankNoPeers: "No player of the same role in this match to compare with.",
      colMetric: "Metric",
      colYou: "You",
      colOpponent: "Opponent",
      colPeers: "Your rank",
      colDiff: "Difference",
      metrics: { gpm: "Gold per minute", xpm: "XP per minute", lh_10: "Last hits at 10:00", lh_per_min: "Last hits per minute", deaths: "Deaths", kda: "KDA", damage_per_min: "Damage per minute", net_worth: "Net worth" },
      rankCareerTitle: "You and players of your rank",
      rankCareerNote: (rank, role, n) => `${rank || "Your rank"} · ${role} · same-role players in your ${n} reviewed matches`,
      rankCareerEmpty: "Appears after a few matches reviewed with OpenDota data.",
      colBracket: "At your rank",
      bracketHint: (rank) => `Hero win rate among all ${rank} players (OpenDota)`,
      shareButton: "Share",
      shareTitle: "Share this review",
      shareWhat: "A page with this review: hero, result, score, the match numbers, the areas and what to improve. Anyone with the link can open it.",
      shareNot: "Not published: the match number, your Steam ID, nickname and the other players. The link works for 90 days, and you can delete it at any time.",
      shareCoach: "Add the AI coach's summary",
      shareCreate: "Create a link",
      shareCreating: "Creating the link…",
      shareLink: "Link to the review",
      shareCopy: "Copy",
      shareCopied: "Copied.",
      shareOpen: "Open",
      shareDelete: "Delete the link",
      shareDeleted: "The link is deleted.",
      shareExpires: (date) => `Works until ${date}.`,
      shareWithCoach: "With the AI coach's summary.",
      shareFailed: (code) => `Could not do it${code ? ` (${code})` : ""}: check the internet and try again.`,
      shareTitleProgress: "Share your progress",
      shareWhatProgress: "A page with your progress over all heroes: matches, win rate, averages, the last 10 against the 10 before, top heroes, what goes well and what to work on. Anyone with the link can open it.",
      shareNotProgress: "Not published: match numbers, your Steam ID, nickname, the other players and your questions to the coach. The link works for 90 days, and you can delete it at any time.",
      shareLinkProgress: "Link to your progress",
      trendTitle: (item) => `${item}: timing game by game`,
      trendLine: (recent, n, before, m) => `Last ${n} games: ${recent}; the ${m} before: ${before}.`,
      trendRecentOnly: (recent, n) => `Last ${n} games: ${recent} (median).`,
      trendSooner: (gap) => `${gap} sooner`,
      trendLater: (gap) => `${gap} later`,
      trendSame: "about the same",
      trendMinute: "Minute",
      deathMapTitle: "Where you die",
      deathMapNote: (matches, total, per) => `Matches with a map: ${matches}. ${total} deaths, ${per} a match.`,
      deathMapTurned: "Dire games are turned half a turn, so your base is always bottom left.",
      deathMapSpot: (place, count, matches) => `${place}: ${count} deaths in ${matches} matches`,
      deathMapSpots: "Deaths keep repeating here:",
      deathMapLate: (pct) => `After minute 10: ${pct}% of deaths on the enemy half`,
      opponentsTitle: "Enemy heroes",
      opponentsNote: (n, min) => `Your record against each enemy hero in ${n} matches with a known lineup (heroes met ${min}+ times).`,
      opponentsHard: "Hardest to play against",
      opponentsEasy: "You beat them most often",
      opponentRecord: (w, l, wr) => `${w}–${l} · ${wr}%`,
      poolTitle: "Your hero pool",
      poolNote: "Your win rate on each hero (4+ games) against how players of your rank do on it.",
      poolMore: "Play them more",
      poolPark: "Better to park them for now",
      poolRecord: (w, n, wr, br) => `${w} of ${n} won · ${wr}%${br == null ? "" : ` (your rank: ${br}%)`}`,
      goalsTitle: "Your goals",
      streaksTitle: "Streaks",
      goalMakeTop: (title) => `Make it the focus: ${title}`,
      zoneGoals: "Goals",
      zoneGoalsHint: "What you work on and how the last matches went",
      summaryLast: "Last match",
      summaryTip: "Main thing to fix",
      summaryStrength: "What went well",
      summaryOpen: "Open the review",
      summaryToday: "Today",
      summaryNoGames: "No matches yet today",
      summaryFocus: "Your focus",
      summaryFocusProgress: (met, total) => `done in ${met} of ${total}`,
      summaryNoFocus: "Pick one problem to work on: the coach checks every match against it.",
      summaryPickFocus: "Pick in Progress",
      streakFewDeaths: (target) => `${target} matches in a row with 5 deaths or fewer`,
      streakGoodScore: (target) => `${target} matches in a row with a score of 60+`,
      streakProgress: (cur, target) => `${Math.min(cur, target)} of ${target}`,
      streakMet: (cur) => `done: ${cur} in a row`,
      streakBest: (best) => `Your best run in the last 30 matches: ${best}`,
      tiltLosses: (n) => `${n} losses in a row. Maybe take a break, or play something just for fun.`,
      tiltScore: (a, b, usual) => `Your last two scores are ${a} and ${b}, while you usually get about ${usual}. Maybe take a break.`,
      friendTitle: "Compare with a friend",
      friendHint: "A friend's Friend ID, Steam ID or profile link (steamcommunity.com/profiles/…). Their public OpenDota matches are compared with yours: the last 20 games of each.",
      friendPlaceholder: "Friend ID, Steam ID or profile link",
      friendCompare: "Compare",
      friendSelf: "That is your own account.",
      friendFailed: "Could not save the friend.",
      friendLoading: (name) => `Loading the matches of ${name} from OpenDota…`,
      friendPrivate: (name) => `${name} hides their match data.`,
      friendPrivateHint: "They can allow it in Dota 2: Settings → Social → «Expose Public Match Data». Then press Refresh (OpenDota needs a match played after that).",
      friendOffline: "The comparison needs OpenDota (internet).",
      friendError: (code) => `OpenDota did not answer${code ? ` (${code})` : ""}. Try Refresh later.`,
      friendRefresh: "Refresh",
      friendUpdating: "Updating…",
      friendChange: "Another friend",
      friendGroup: "Games",
      friendGroups: { all: "All games", core: "Core", support: "Support" },
      friendYou: "You",
      friendGames: (me, friend) => `games: you ${me}, friend ${friend}`,
      friendFew: (n) => `Too few games to say who is ahead: ${n}+ for each of you.`,
      friendMetrics: { win_rate: "Win rate", kills: "Kills", deaths: "Deaths", assists: "Assists", gpm: "Gold per minute", xpm: "XP per minute", lh_per_min: "Last hits per minute", damage_per_min: "Hero damage per minute" },
      friendCommon: "Heroes you both played",
      friendHeroGames: (g1, w1, g2, w2) => `you ${g1} · ${w1 ?? "—"}%   friend ${g2} · ${w2 ?? "—"}%`,
      friendTheirHeroes: (name) => `Most played by ${name}`,
      friendNote: "Averages per game, public OpenDota data, ranked and normal modes only. Core or support is judged by last hits a minute.",
      rankHistoryTitle: "Your rank medal",
      rankUp: (from, to, since) => `Up from ${from} to ${to} since ${since}.`,
      rankDown: (from, to, since) => `Down from ${from} to ${to} since ${since}.`,
      rankNote: "The app notes your medal every time it updates your history, and marks when it changes.",
      heroBuildTitle: (hero) => `Your build on ${hero}`,
      buildNote: (n, wins) => `Your items in ${n} reviewed games on the hero (${wins} wins): when they come in wins and in losses, and how often you win with and without them.`,
      buildItem: "Item",
      buildGames: "Games",
      buildWinrate: "Wins with it",
      buildWithout: "Without it",
      buildWinTime: "In wins",
      buildLossTime: "In losses",
      selfTitle: (hero) => `Your best vs your worst games on ${hero}`,
      selfNote: (n) => `The best third of your last ${n} reviewed games on the hero against the worst third, by review score.`,
      selfBest: "Best",
      selfWorst: "Worst",
      selfGroup: (count, wr) => `${count} games · ${wr}% wins`,
      selfMetrics: {
        lh_10: "Last hits at 10:00",
        gpm: "Gold/min",
        deaths: "Deaths",
        lane_deaths: "Lane deaths",
        kill_participation: "Kill participation",
        first_item_t: "First big item"
      },
      draftTitle: "Draft",
      draftNote: (hero) => `How often ${hero} wins against each enemy hero (public match statistics from OpenDota).`,
      draftNoData: "No statistics for these heroes yet: they load the next time your history updates.",
      draftEnemy: "Enemy",
      draftWinrate: "Your win rate",
      draftGames: "games",
      draftPool: "Your heroes against this lineup",
      draftPoolNote: "Average win rate edge over 50% against these five heroes.",
      draftPicked: "your pick",
      draftBetter: (hero) => `${hero} fit this lineup best.`,
      draftCounters: "Answers to the enemy heroes",
      draftReasons: { evasion: "evasion", illusions: "illusions", invisibility: "invisibility", healing: "healing", targeted: "killed you with a disable" },
      draftForSupports: "support's job",
      draftBought: "bought",
      coachTitle: "Coach's review",
      coachCareerTitle: "Coach's review of your recent games",
      coachTag: "AI",
      coachPending: "The coach is writing the review. It takes up to a minute.",
      coachCareerPending: "The coach is looking through your recent matches. It takes up to a minute.",
      coachWaiting: "The AI waits until OpenDota has studied the replay (usually a few minutes): then it has more to go on.",
      coachNow: "Review now",
      coachUpdating: "Updating with the new data…",
      coachRetry: "Try again",
      coachRewrite: "Rewrite",
      coachNotEnough: (n) => `The coach needs at least ${n} reviewed matches.`,
      coachTurning: "Turning points",
      coachMistakes: "Main mistakes",
      coachFix: "Next time",
      coachStrengths: "What went well",
      coachNextGame: "Goals for the next game",
      coachPatterns: "Recurring problems",
      coachTrain: "How to train it",
      coachPlan: "Plan for the next games",
      coachFooter: (provider, model) => `Written by AI (${provider} · ${model}) from the data of the review. Numbers, times, heroes and items are checked against it.`,
      coachErrors: {
        rate_limited: "The free AI limit is used up for now. Try again in a few minutes.",
        busy: "The AI is overloaded right now. Try again in a few minutes.",
        invalid_key: "The key did not work. Check it in the AI coach settings.",
        region: "This AI does not work from your country. Choose another one (OpenRouter, for example) or turn on a VPN; the key is kept.",
        timeout: "The AI took too long to answer.",
        offline: "No connection to the AI: check the internet.",
        unverified: "The AI answer mentioned facts that are not in the data, so it was not shown. Try again.",
        bad_response: "The AI answered with an error. Try again later.",
        no_key: "No key yet."
      },
      askTitle: "Ask the coach",
      askHint: "A question about this match. The answer uses only this match's data and goes through the same fact check.",
      askPlaceholder: "For example: why did I lose the lane?",
      askButton: "Ask",
      askThinking: "The coach is thinking…",
      askSuggestions: ["What decided this game for me?", "What should I change in the lane?", "Was my build on time?"],
      askCareerHint: "A question about your recent matches: heroes, enemies, habits. The answer uses only your statistics and goes through the same fact check.",
      askCareerPlaceholder: "For example: which enemy heroes are hardest for me?",
      askCareerSuggestions: ["Which enemy heroes are hardest for me?", "What mistake costs me the most games?", "Which hero should I play more?"],
      askErrors: {
        unverified: "The coach could not answer this from the match data. Try asking differently.",
        empty_question: "Type a question first.",
        no_review: "The review of this match is not ready yet.",
        not_enough: "Not enough reviewed matches yet: open a few reviews first.",
        off: "Turn the AI coach on in Settings first."
      },
      aiSettingsTitle: "AI coach",
      aiOnTitle: "AI coach is on",
      aiCheckNow: "Check key",
      aiCheckOk: "The key works.",
      aiOffTitle: "AI coach is off",
      aiOffHint: "After every match the AI explains in plain words what went well and what to fix, like a coach watching your replay. Free: you only need a key from Google (Gemini), Groq or OpenRouter.",
      aiTurnOn: "Turn on",
      aiSetupHint: "A key is like a password that lets the app use the AI. Get a free one (a minute, no card) and paste it here. The AI only explains: every number still comes from the review. Your match data (without your Steam ID) goes to the site you chose.",
      aiService: "Where the key is from",
      aiKey: "Key",
      aiKeyPlaceholder: "Paste the key",
      aiModel: "AI model",
      aiAdvanced: "For advanced users",
      aiModelHint: "leave empty for the default",
      aiGetKey: "Get a free key",
      aiSave: "Check and save",
      aiChecking: "Checking the key…",
      aiSaved: "The key works. The coach is on.",
      aiSavedWarn: (reason) => `Key saved, but the check failed: ${reason}`,
      aiSettings: "AI settings",
      aiCurrent: (provider, model, hint) => [provider, model, hint ? `key ${hint}` : ""].filter(Boolean).join(" · "),
      aiEnvKey: "A key is already set in the settings file of the app.",
      aiChangeKey: "Change key",
      aiDisable: "Turn off",
      aiCancel: "Cancel"
    },
    ru: {
      pfTitle: "Профиль",
      pfSub: "Ваш рейтинг, уровень и награды с Wardly.",
      pfLevel: (n) => `Уровень ${n}`,
      pfXp: (into, need) => `${into} / ${need} опыта до следующего уровня`,
      pfSparks: "Искры",
      pfSparksHint: "Даются за игру с тренером: 10 за матч, ещё 5 за победу и больше за каждую ступень награды. Тратятся на оформление профиля.",
      pfGames: "Матчей с Wardly",
      pfWithApp: "С тренером",
      pfWinrate: "Процент побед",
      pfHours: "Часов с тренером",
      pfNoName: "Игрок",
      pfRating: "Рейтинг",
      pfRatingNone: "Введите свой MMR из Доты, чтобы начать график: дальше его двигает каждая рейтинговая игра.",
      pfRatingMedal: "Оценка по медали. Введите свой MMR из Доты — график станет вашим.",
      pfRatingManual: (step) => `Это оценка: рейтинговая игра двигает его примерно на ${step}. Поправьте, если разойдётся с Дотой.`,
      pfNow: "Сейчас",
      pfPeak: "Пик",
      pfLast20: "За 20 игр",
      pfRecord: (w, l) => `${w}–${l}`,
      pfMmrLabel: "Ваш MMR сейчас",
      pfMmrPlaceholder: "например, 3200",
      pfMmrSave: "Сохранить",
      pfMmrClear: "Вернуть оценку по медали",
      pfMmrBad: "Введите число от 0 до 15000.",
      pfWin: "Победа",
      pfLoss: "Поражение",
      pfAnchor: "Ваше число",
      pfAchievements: "Награды",
      pfAchievementsHint: "За матчи, сыгранные с Wardly. Каждая ступень даёт искры.",
      pfTierNone: "Не начато",
      pfTier: (name, tier, tiers) => `${name} · ${tier}/${tiers}`,
      pfDone: "Все ступени пройдены",
      pfReward: (n) => `+${n} искр`,
      pfProgress: (value, target) => `${value} / ${target}`,
      pfEmpty: "Сыграйте матч с запущенным Wardly — с него начнутся уровень, награды и искры.",
      pfFriends: "Друзья",
      pfFriendsHint: "Покажите профиль друзьям по коду и смотрите их: уровень, рейтинг, оформление и награды.",
      pfFriendsOff: "Сейчас ваш профиль видите только вы. Покажите его — и друзья с вашим кодом увидят карточку: ник, уровень, медаль, награды, оформление и матчи с Wardly. Без Steam ID и списка матчей.",
      pfFriendsShow: "Показать профиль друзьям",
      pfFriendsHide: "Скрыть профиль",
      pfFriendsCode: "Ваш код друга",
      pfFriendsCopy: "Скопировать код",
      pfFriendsCopyLink: "Скопировать ссылку",
      pfFriendsOpen: "Открыть страницу",
      pfFriendsCopied: "Скопировано.",
      pfFriendsShowMmr: "Показывать мой рейтинг",
      pfFriendsAdd: "Добавить",
      pfFriendsAddPlaceholder: "Код друга, например WD-4K7P9QX2",
      pfFriendsEmpty: "Друзей пока нет: отправьте им свой код и добавьте их.",
      pfFriendsYou: "Вы",
      pfFriendsRemove: "Убрать",
      pfFriendsWeek: (n) => `${n} за неделю`,
      pfFriendsMissing: (codes) => `Скрыты или не найдены: ${codes}`,
      pfFriendsErrors: { bad_code: "Это не код друга.", own_code: "Это ваш собственный код.", already: "Уже в списке.", too_many: "Не больше 50 друзей.", offline: "Нет связи с сервером.", disabled: "Друзья на сервере сейчас выключены.", rate_limited: "Слишком много запросов: попробуйте через час.", backend_down: "Служба тренера не запущена." },
      pfShop: "Оформление",
      pfShopHint: "Тратьте искры на вид профиля. Редкие вещи открываются с уровнем или за награду.",
      pfKinds: { frame: "Рамки аватара", banner: "Баннеры", name: "Цвет ника", title: "Титулы" },
      pfBuy: (price) => `Купить · ${price}`,
      pfWear: "Надеть",
      pfWorn: "Надето",
      pfFree: "Бесплатно",
      pfNeedSparks: (n) => `Ещё ${n} ${plural(n, "искра", "искры", "искр")}`,
      pfLockedHint: "Пока закрыто: условие написано выше",
      pfNeedLevel: (n) => `С ${n}-го уровня`,
      pfNeedAchievement: (name, tier) => `За награду «${name}», ступень ${tier}`,
      pfShopErrors: { not_enough: "Пока не хватает искр.", locked_level: "Нужен уровень выше.", locked_achievement: "Даётся за награду.", owned: "Уже есть." },
      linkTitle: "Привяжите аккаунт Steam",
      linkHint:
        "Тренер сам узнаёт ваш аккаунт из Доты, когда вы играете. Можно и вручную: Friend ID из профиля в Доте, ссылка steamcommunity.com/profiles/… или ссылка на OpenDota/Dotabuff.",
      linkPlaceholder: "Friend ID, Steam ID или ссылка на профиль",
      linkButton: "Привязать",
      linkSoon: "Когда аккаунт привязан, здесь будут:",
      newerMatch: "Новее",
      olderMatch: "Старее",
      newerMatchHint: (hero) => `Более новый матч${hero ? ` (${hero})` : ""} · ←`,
      olderMatchHint: (hero) => `Более старый матч${hero ? ` (${hero})` : ""} · →`,
      openOnSite: (name) => `Открыть этот матч на ${name}`,
      progressSoon: "Когда разобранных матчей станет больше, здесь будут:",
      linkPerks: {
        matches: [
          ["target", "все ваши игры с оценкой и тем, что исправить в первую очередь"],
          ["skull", "каждая смерть: минута, место и что было готово к нажатию"],
          ["swords", "ваш билд рядом с про-игроками и игроками вашего ранга"]
        ],
        progress: [
          ["trending-up", "последние 10 игр против 10 игр до них"],
          ["repeat", "ошибки, которые повторяются, и один фокус на следующую игру"],
          ["map", "ваши герои, ваши линии и где вы умираете чаще всего"]
        ],
        profile: [
          ["chart-line", "график рейтинга и ваш уровень"],
          ["trophy", "награды и оформление вашей карточки"],
          ["users", "друзья по коду и таблица лидеров"]
        ]
      },
      progressSub: "Как меняется ваша игра от матча к матчу",
      linkErrors: {
        empty: "Введите Friend ID, Steam ID или ссылку на профиль.",
        vanity_url: "Короткие ссылки (steamcommunity.com/id/…) не распознать. Возьмите Friend ID из профиля в Доте.",
        unrecognized: "Это не похоже на аккаунт Steam.",
        out_of_range: "Такого аккаунта Steam не бывает.",
        backend_down: "Тренер не запущен.",
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
        private: "Данные матчей скрыты. В Доте: Настройки → Социальное → включите общий доступ к данным матчей (Expose Public Match Data).",
        rate_limited: "OpenDota перегружен, попробуйте через минуту.",
        not_found: "OpenDota пока не знает этот аккаунт.",
        bad_response: "OpenDota ответил ошибкой."
      },
      matchesTitle: "Матчи",
      matchesSub: "Все игры с разборами: откройте матч, чтобы увидеть, что исправить",
      matchesTableTitle: "История матчей",
      progressTitle: "Прогресс",
      zoneFix: "Что исправить",
      zoneFixHint: "Разбор тренера и цель на следующую игру",
      zoneStory: "Как шёл матч",
      zoneStoryHint: "Фарм и золото по ходу игры, смерти, ваши подсказки",
      zoneScores: "Оценки и сравнение",
      zoneScoresHint: "Разделы игры, что получилось, ваш ранг",
      zoneMapItems: "Карта и предметы",
      zoneMapItemsHint: "Где вы были, что и когда купили",
      zoneTeams: "Составы",
      zoneSummary: "Итоги",
      zoneSummaryHint: "Последние 10 матчей против 10 предыдущих",
      zoneCoach: "Тренер",
      zoneCoachHint: "Что повторяется и что тренировать",
      zoneGames: "Матчи и герои",
      zoneGamesHint: "Оценка каждого матча и ваши герои",
      zoneCompare: "Сравнение",
      zoneCompareHint: "Игроки вашего ранга, вражеские герои, друг",
      zoneHero: "Ваш основной герой",
      zoneHeroHint: "Лучшие игры против худших, ваш билд",
      colResult: "Итог",
      colHero: "Герой",
      colKda: "У / С / П",
      colGpm: "Золото/мин",
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
      filterResult: "Результат",
      filterResults: { all: "Все", win: "Победы", loss: "Поражения" },
      filterHero: "Герой",
      filterAllHeroes: "Все герои",
      filterSummary: (games, winrate, score) =>
        [`${games} ${plural(games, "матч", "матча", "матчей")}`, winrate == null ? null : `${winrate}% побед`, score == null ? null : `средняя оценка ${score}`].filter(Boolean).join(" · "),
      skippedModes: (count, turbo, of) =>
        `Не разбираем ${count} из ${of} последних игр${turbo ? ` (Турбо: ${turbo})` : ""}: в Турбо, играх с ботами и особых режимах другие нормы.`,
      filterEmptyTitle: "Нет матчей под этот фильтр",
      filterEmptyHint: "Выберите другого героя или результат.",
      pdfSave: "Сохранить PDF",
      pdfSaved: (name) => `Сохранено: ${name}`,
      pdfFailed: "Не удалось сохранить PDF",
      reviewLoading: "Загружаем матч…",
      reviewPending: "Разбор появится, когда загрузятся данные матча.",
      reviewError: "Не удалось открыть матч",
      reviewRenderFailed: "Это ошибка приложения. Сообщите о ней («Настройки → Помощь → Сообщить о проблеме»), чтобы её исправили.",
      scoreOf: "из 100",
      sourcesParsed: "Полный разбор реплея (OpenDota)",
      sourcesBasic: "Пока только итоги матча — полный разбор реплея ещё не готов",
      sourcesGsi: "Записано приложением во время матча",
      parseStatus: {
        waiting_opendota: "Полный разбор реплея будет через несколько минут (OpenDota).",
        parsing: "OpenDota изучает реплей — разбор дополнится сам.",
        basic: "Реплей не разобран: нет данных по минутам.",
        not_parsed: "OpenDota не смог изучить реплей, поэтому разбор короче.",
        gsi_only: "Есть только запись приложения (OpenDota выключен).",
        private: "Матч скрыт в OpenDota. В Доте: Настройки → Социальное → включите общий доступ к данным матчей (Expose Public Match Data) (сработает для следующих матчей); пока разбор строится по записи приложения.",
        "error:not_found": "OpenDota пока не знает этот матч — попробуйте через несколько минут.",
        "error:offline": "Нет интернета — показываем запись приложения.",
        "error:rate_limited": "OpenDota перегружен — попробуйте через минуту.",
        "error:bad_response": "OpenDota ответил ошибкой."
      },
      requestParse: "Запросить разбор реплея",
      parseRequested: "Запрос отправлен — обычно это 2–10 минут.",
      focusTitle: "Главное на следующую игру",
      sectionsTitle: "По разделам",
      explainTitle: "Что это значит?",
      explainScore:
        "Оценка от 0 до 100 — насколько матч похож на хорошую игру на вашей роли: линия, фарм, выживание, драки, предметы, а у саппорта ещё и обзор, у каждой части своя шкала. 65 и выше — хорошо (B), 80 и выше — отлично (A), ниже 50 — матч, на котором стоит поучиться (D). Победа или поражение на оценку не влияют: можно проиграть с 80 и выиграть с 30.",
      explainRank:
        "Подбор матчей собирает в одну игру игроков примерно одного ранга, поэтому игрок вашей роли в этом матче (из любой команды) показывает, как обычно играют на вашем ранге. Вы выше него — сыграли лучше своего ранга; ниже — есть куда расти.",
      explainFocus:
        "Фокус — одна ошибка, над которой вы работаете. После каждого матча тренер проверяет, повторилась ли она: зелёная отметка — не повторилась. Одну вещь исправить проще, чем всё сразу.",
      chartTitle: "По ходу матча",
      mapTitle: "Карта матча",
      deathsTitle: (count) => `Смерти · ${count}`,
      weekGames: "Матчи",
      weekVsPrevious: "к прошлой неделе",
      weekRecord: (w, l) => `${w} ${plural(w, "победа", "победы", "побед")} · ${l} ${plural(l, "поражение", "поражения", "поражений")}`,
      weekScoreNote: {
        no_score: "На этой неделе ещё нет разобранных матчей",
        no_previous: "Неделей раньше матчей не было — сравнить не с чем",
        no_previous_score: "Неделей раньше нет разобранных матчей"
      },
      weekChartTitle: "Оценка каждого матча за неделю",
      weekBest: "Лучший матч",
      weekHeroes: "Герои:",
      weekHeroTitle: (hero, games, wins) => `${hero}: матчей ${games}, побед ${wins}`,
      weekProblem: "Чаще всего:",
      weekProblemText: (title, count, of) => `${title} — в ${count} из ${of} матчей`,
      weekFocus: "Фокус:",
      weekPlanProgress: (met, played, plan) => `получилось ${met} из ${played} · план: ${plan} матча подряд`,
      weekPlanNext: "Следующий матч",
      sessionGames: "Матчи",
      sessionScore: "Средняя оценка",
      sessionVsUsual: "к обычной",
      sessionUsual: (score) => `Обычно: ${score}`,
      sessionNoScore: "Разборов пока нет",
      sessionTime: (minutes) => (minutes >= 60 ? `${Math.floor(minutes / 60)} ч ${String(minutes % 60).padStart(2, "0")} мин в игре` : `${minutes} мин в игре`),
      sessionDeaths: (deaths) => `смертей за матч в среднем: ${String(deaths).replace(".", ",")}`,
      sessionProblem: "Над чем работать:",
      sessionProblemText: (title, count, of) => `${title} — в ${count} из ${of}`,
      sessionFocus: (title, met, total) => `Фокус «${title}»: получилось в ${met} из ${total}`,
      sessionCopy: "Скопировать для друзей",
      sessionCopied: "Скопировано",
      sessionPreview: "Что скопируется",
      deathsNoPattern: "Повторяющейся причины у этих смертей нет.",
      deathNoFacts: "Больше об этой смерти ничего не известно.",
      deathGold: (gold) => `${gold} непотраченного золота`,
      deathAfterRespawn: (seconds) => `через ${seconds} с после возрождения`,
      deathWarned: (time, action) => `Тренер предупреждал в ${time}: «${action}»`,
      deathNote: {
        enemy_half: "на половине врага",
        unspent_gold: "с 1000+ непотраченного золота",
        warned: "после предупреждения",
        soon_after_respawn: "сразу после возрождения",
        saver_ready: "спасающий предмет был готов",
        burst: "убиты быстрее 3 с"
      },
      deathLastTitle: "Здоровье за последние 20 с",
      deathBurst: (seconds) => `С 70%+ здоровья до смерти за ${seconds} с`,
      deathReady: "Был готов и не нажат:",
      deathReadyStunned: "Был готов, но герой был в контроле:",
      deathZone: { top: "верхняя линия", mid: "центр", bot: "нижняя линия", jungle: "лес", base: "база" },
      mapEmpty: "Для этого матча пока нет позиций. Они берутся из разобранного реплея (приложение само просит OpenDota разобрать 5 последних матчей за неделю) или из матча, сыгранного с запущенным приложением: ваш путь и места смертей.",
      mapHint: {
        path: "Где был ваш герой (каждые 15 с, записало приложение) и где вы умирали.",
        replay: "По разобранному реплею: где вы стояли на линии, где ставили варды и где умирали в драках.",
        both: "Ваш путь (записало приложение), позиция на линии и варды из реплея, места смертей."
      },
      mapLabels: {
        radiant: "Силы Света",
        dire: "Силы Тьмы",
        death: "Смерть",
        observer: "Обзорный вард",
        sentry: "Сентри",
        path: "Ваш путь",
        lane: "Позиция на линии",
        spot: "Место, где умираете снова"
      },
      mapSpotTitle: (count, place) => `${count} ${plural(count, "смерть", "смерти", "смертей")} · ${place}`,
      mapSpotLine: (place, count) => `Чаще всего: ${place} (${count} ${plural(count, "смерть", "смерти", "смертей")})`,
      watchMoment: "Смотреть",
      watchMomentHint: "Копирует команду консоли Доты. Откройте запись этого матча в Доте, нажмите \\ (консоль) и вставьте: запись перемотается примерно за 10 с до этого момента.",
      watchCopied: "Скопировано: вставьте в консоль записи",
      watchFailed: "Не удалось скопировать",
      bestOnHeroLine: (score) => `Ваш лучший матч на герое (${score})`,
      bestOnHeroNote: (score, when) => `Пунктир — ваш лучший матч на этом герое, оценка ${score} (${when}).`,
      bestOnHeroSelf: (of) => `Это ваш лучший матч на этом герое из ${of}.`,
      mapDeaths: "Смерти",
      killedBy: (hero) => `Убил: ${hero}`,
      mapSide: { own: "на своей половине", river: "у реки", enemy: "на половине противника" },
      mapWards: "Поставлено вардов",
      mapWardsLine: (obs, sen) => `${obs} обзорных · ${sen} сентри`,
      chartLh: "Добивания",
      chartGold: "Золото",
      chartXp: "Опыт",
      you: "Вы",
      target: "Хороший темп",
      deathsMarker: "Смерть",
      minuteLabel: (m) => `${m}:00`,
      strengthsTitle: "Что получилось",
      improveTitle: "Что улучшить",
      foldMore: (n) => `Показать ещё ${n}`,
      foldLess: "Свернуть",
      repeatInARow: (n) => `${n}-й матч подряд — это привычка, а не случайность`,
      repeatInLast: (n, of) => `Было и в ${n} из ${of} прошлых матчей`,
      nothingToImprove: "Серьёзных ошибок в этом матче не найдено.",
      nothingStrong: "В этот раз ничего не выделилось.",
      drill: "Упражнение",
      momentsTitle: "Ключевые моменты",
      adviceLogTitle: "Подсказки во время матча",
      adviceWhy: "Почему этот совет?",
      adviceLogHint: (n, urgent) => `${n} ${plural(n, "подсказка", "подсказки", "подсказок")} за игру, срочных — ${urgent}. Стоит проверить, получилось ли им следовать.`,
      adviceLogMore: (n) => `Показать все (${n})`,
      adviceLogDeath: (time) => `Смерть в ${time}`,
      momentDeath: (killer) => (killer ? `Смерть от ${killer}` : "Смерть"),
      momentGold: (gold) => `${gold} золота на руках`,
      momentItem: (item) => item,
      momentBuyback: "Байбэк",
      momentStall: (to) => `Провал в фарме до ${to}`,
      scoreboardTitle: "Итоги матча",
      radiant: "Силы Света",
      dire: "Силы Тьмы",
      colPlayer: "Игрок",
      colNw: "Стоимость",
      colDmg: "Урон",
      stats: {
        kda: "У / С / П",
        gpm: "Золото и опыт в минуту",
        lh: "Добивания / денаи",
        nw: "Стоимость героя",
        dmg: "Урон по героям",
        duration: "Длительность"
      },
      sectionFacts: {
        laning: (s) => [s.lh10 != null && `${s.lh10} добиваний к 10:00`, s.lane_efficiency != null && `эффективность ${Math.round(s.lane_efficiency)}%`, s.lane_deaths ? `смертей на линии: ${s.lane_deaths}` : null, s.runes != null && `рун: ${s.runes}${s.enemy_runes != null ? ` (у вражеского мида ${s.enemy_runes})` : ""}`],
        farm: (s) => [s.gpm != null && `${s.gpm} золота в минуту`, s.gpm_pct != null && `лучше ${Math.round(s.gpm_pct * 100)}% игроков`],
        survival: (s) => [`смертей: ${s.deaths}`, s.deaths_per_10 != null && `${s.deaths_per_10} за 10 мин`],
        fights: (s) => [s.kill_participation != null && `участие в убийствах ${s.kill_participation}%`, s.stuns != null && `оглушений ${s.stuns} с${s.enemy_stuns != null ? ` (у вражеского хардлайнера ${s.enemy_stuns} с)` : ""}`, s.enemy_tower_damage != null && s.tower_damage != null && `урон по строениям ${s.tower_damage} (у вражеского хардлайнера ${s.enemy_tower_damage})`],
        items: (s) => [
          s.first_item && `${s.first_item.item} к ${clock(s.first_item.t)}`,
          s.save_item && `Спасающий предмет: ${s.save_item.item} к ${clock(s.save_item.t)}`,
          "save_item" in s && !s.save_item && "Нет спасающего предмета"
        ],
        vision: (s) => [s.obs_placed != null && `обсерверов: ${s.obs_placed}`, s.sen_placed != null && `сентри: ${s.sen_placed}`, s.camps_stacked != null && `стаков: ${s.camps_stacked}`]
      },
      progressEmptyTitle: "Пока мало матчей",
      progressEmptyHint: "Статистика появится после нескольких разобранных матчей. Обновите историю на вкладке «Матчи».",
      tiles: { winrate: "Винрейт", kda: "KDA", gpm: "Золото в минуту", lh10: "Добивания к 10:00", score: "Средняя оценка" },
      vsPrevious: (n) => `к прошлым ${n}`,
      streakWin: (n) => `${n} ${plural(n, "победа", "победы", "побед")} подряд`,
      streakLoss: (n) => `${n} ${plural(n, "поражение", "поражения", "поражений")} подряд`,
      recordLine: (w, l, n) => `${w} ${plural(w, "победа", "победы", "побед")} и ${l} ${plural(l, "поражение", "поражения", "поражений")} за ${n} ${plural(n, "матч", "матча", "матчей")}`,
      scoreChartTitle: "Оценка по матчам",
      scoreChartHint: "Последние 20 матчей, старые слева. Нажмите на столбец, чтобы открыть разбор; нет столбца — у матча нет подробного разбора.",
      scoreLabel: "Оценка",
      winKey: "победа",
      lossKey: "поражение",
      baselineIntro: (games, hero) => `Против ваших ${games} ${plural(games, "другого матча", "других матчей", "других матчей")} на ${hero}:`,
      baselineLabels: { score: "оценка", gpm: "золото/мин", lh_10: "добиваний к 10", deaths: "смертей" },
      baselineSame: "как обычно",
      baselineTitle: (average) => `Ваш средний: ${average}`,
      goalTitle: "Ваш фокус",
      goalHint: "Одна проблема за раз: в каждом следующем матче видно, повторилась ли она.",
      goalSince: (date) => `с ${date}`,
      goalProgress: (met, total) => `Получилось в ${met} из ${total} ${plural(total, "матча", "матчей", "матчей")}`,
      goalWaiting: "Сыграйте матч — после него здесь будет видно, получилось ли.",
      goalStreak: (n) => `${n} ${plural(n, "матч", "матча", "матчей")} подряд без этой ошибки`,
      goalClear: "Снять фокус",
      goalSet: "Сделать фокусом",
      goalSetFailed: "Не удалось сохранить фокус, попробуйте ещё раз",
      goalCurrent: "Фокус",
      goalMet: "получилось",
      goalMissed: "повторилось",
      goalMatch: (title, met) => `Ваш фокус «${title}»: ${met ? "в этом матче получилось" : "снова повторилось"}`,
      planTitle: "Над чем работать",
      planHint: "Ошибки, которые повторяются в последних матчах, и по одному упражнению на каждую.",
      planEmpty: "Повторяющихся ошибок не найдено — так держать.",
      strengthsRecurring: "Ваши сильные стороны",
      heroesTitle: "Герои",
      colMatches: "Матчи",
      colWinrate: "Винрейт",
      analyzed: (a, n) => `Подробно разобрано ${a} из ${n} матчей`,
      buildTitle: "Сборка",
      lanesTitle: "Ваши линии",
      lanesLine: (won, even, lost, games) => `Из последних ${games} линий: выиграно ${won}, на равных ${even}, проиграно ${lost}.`,
      lanesGold: (diff) => `В среднем ${diff} золота против соперника по линии к 10-й минуте.`,
      lanesHard: (list) => `Линии, проигранные не раз, против: ${list}.`,
      lanesDot: (hero, enemy, result, diff) => `${hero} против ${enemy}: ${result.toLowerCase()}, ${diff} золота к 10-й минуте`,
      laneTitle: "Линия",
      laneVs: "против",
      laneResult: { won: "Линия выиграна", even: "Линия на равных", lost: "Линия проиграна" },
      laneMinute: (m) => `${m}:00`,
      laneColMinute: "Минута",
      laneColLh: "Добивания",
      laneColDn: "Денаи",
      laneColGold: "Золото",
      laneColXp: "Опыт",
      laneTurn: (m) => `Разрыв появился с ${m}-й минуты.`,
      laneOthers: (heroes, diff) => `Ещё на линии: ${heroes}; золото всей линии к 10-й минуте: ${diff}.`,
      laneNote: "Вы : соперник; золото и опыт — разница. По разобранной записи матча.",
      skillsTitle: "Прокачка",
      skillsYours: "Ваше первое:",
      skillsPro: "Как максят умения про-игроки на этом герое:",
      skillsSame: (name) => `Первым вы вкачали до конца ${name} — как и про-игроки.`,
      skillsDiff: (yours, pro) => `Первым вы вкачали до конца ${yours}, а про-игроки начинают с ${pro}.`,
      skillsNote: (agree, games) => `Так начинают ${agree} из ${games} недавних про-матчей. Подсказка в игре назовёт, куда вложить каждое очко.`,
      buildTimingNote: "Винрейт героя в зависимости от времени покупки (публичные матчи OpenDota). Ваш тайминг выделен. Самые ранние тайминги — чаще всего игры, которые и так шли хорошо, поэтому цель — обычный тайминг.",
      buildNoTimings: "По этим предметам пока нет данных о таймингах.",
      buildItemLine: (wr, t, typicalT, typicalWr) => `${wr}% побед при покупке к ${t} · обычно покупают к ${typicalT}: ${typicalWr}%`,
      buildItemTypical: (wr, t) => `${wr}% побед при покупке к ${t} · обычный тайминг для героя`,
      buildBy: (t) => `к ${t}`,
      buildPopular: "Частая сборка (про-игроки)",
      buildPhase: { early: "Начало", mid: "Основа", late: "Поздняя игра" },
      buildBought: "куплено",
      buildTimingTip: (t) => `Покупка к ${t}`,
      winrateLabel: "Винрейт",
      rankTitle: "Вы и ваш ранг",
      rankMatchNote: (rank, role, heroes) => `${rank ? `Ранг матча: ${rank} · ` : ""}сравнение с ${role} этого матча${heroes ? ` (${heroes})` : ""}`,
      rankNoPeers: "В этом матче нет игрока той же роли для сравнения.",
      colMetric: "Показатель",
      colYou: "Вы",
      colOpponent: "Соперник",
      colPeers: "Ваш ранг",
      colDiff: "Разница",
      metrics: { gpm: "Золото в минуту", xpm: "Опыт в минуту", lh_10: "Добивания к 10:00", lh_per_min: "Добиваний в минуту", deaths: "Смерти", kda: "KDA", damage_per_min: "Урон в минуту", net_worth: "Стоимость героя" },
      rankCareerTitle: "Вы и игроки вашего ранга",
      rankCareerNote: (rank, role, n) => `${rank || "Ваш ранг"} · ${role} · игроки той же роли в ваших ${n} разобранных матчах`,
      rankCareerEmpty: "Появится после нескольких матчей, разобранных по данным OpenDota.",
      colBracket: "На вашем ранге",
      bracketHint: (rank) => `Винрейт героя у всех игроков ранга ${rank} (OpenDota)`,
      shareButton: "Поделиться",
      shareTitle: "Поделиться разбором",
      shareWhat: "Страница с этим разбором: герой, результат, оценка, цифры матча, разделы и что улучшить. Открыть её сможет любой, у кого есть ссылка.",
      shareNot: "Не публикуется: номер матча, ваш Steam ID, ник и другие игроки. Ссылка работает 90 дней, её можно удалить в любой момент.",
      shareCoach: "Добавить вывод ИИ-тренера",
      shareCreate: "Создать ссылку",
      shareCreating: "Создаю ссылку…",
      shareLink: "Ссылка на разбор",
      shareCopy: "Копировать",
      shareCopied: "Скопировано.",
      shareOpen: "Открыть",
      shareDelete: "Удалить ссылку",
      shareDeleted: "Ссылка удалена.",
      shareExpires: (date) => `Работает до ${date}.`,
      shareWithCoach: "С выводом ИИ-тренера.",
      shareFailed: (code) => `Не получилось${code ? ` (${code})` : ""}: проверьте интернет и попробуйте ещё раз.`,
      shareTitleProgress: "Поделиться прогрессом",
      shareWhatProgress: "Страница с вашим прогрессом по всем героям: матчи, процент побед, средние цифры, последние 10 матчей против 10 до них, главные герои, что получается и над чем работать. Открыть её сможет любой, у кого есть ссылка.",
      shareNotProgress: "Не публикуется: номера матчей, ваш Steam ID, ник, другие игроки и ваши вопросы тренеру. Ссылка работает 90 дней, её можно удалить в любой момент.",
      shareLinkProgress: "Ссылка на прогресс",
      trendTitle: (item) => `${item}: тайминг по играм`,
      trendLine: (recent, n, before, m) => `Последние ${n} ${plural(n, "игра", "игры", "игр")}: ${recent}; ${m} ${plural(m, "игра", "игры", "игр")} до этого: ${before}.`,
      trendRecentOnly: (recent, n) => `Последние ${n} ${plural(n, "игра", "игры", "игр")}: ${recent} (медиана).`,
      trendSooner: (gap) => `на ${gap} раньше`,
      trendLater: (gap) => `на ${gap} позже`,
      trendSame: "примерно так же",
      trendMinute: "Минута",
      deathMapTitle: "Где вы умираете",
      deathMapNote: (matches, total, per) => `Матчей с картой: ${matches}. ${total} ${plural(total, "смерть", "смерти", "смертей")}, ${String(per).replace(".", ",")} за матч.`,
      deathMapTurned: "Игры за Силы Тьмы повёрнуты на пол-оборота: ваша база всегда слева внизу.",
      deathMapSpot: (place, count, matches) => `${place}: ${count} ${plural(count, "смерть", "смерти", "смертей")} в ${matches} ${plural(matches, "матче", "матчах", "матчах")}`,
      deathMapSpots: "Здесь смерти повторяются:",
      deathMapLate: (pct) => `После 10-й минуты на половине противника: ${pct}% смертей`,
      opponentsTitle: "Вражеские герои",
      opponentsNote: (n, min) => `Ваш счёт против каждого вражеского героя в ${n} матчах с известным составом (герои, встреченные ${min}+ раза).`,
      opponentsHard: "Против них сложнее всего",
      opponentsEasy: "Их вы обыгрываете чаще всего",
      opponentRecord: (w, l, wr) => `${w}–${l} · ${wr}%`,
      poolTitle: "Ваш пул героев",
      poolNote: "Ваш процент побед на каждом герое (от 4 игр) против того, как на нём играют игроки вашего звания.",
      poolMore: "Играйте на них чаще",
      poolPark: "Их лучше пока отложить",
      poolRecord: (w, n, wr, br) => `${w} из ${n} побед · ${wr}%${br == null ? "" : ` (на вашем звании ${br}%)`}`,
      goalsTitle: "Ваши цели",
      streaksTitle: "Серии",
      goalMakeTop: (title) => `Сделать фокусом: ${title}`,
      zoneGoals: "Цели",
      zoneGoalsHint: "Над чем вы работаете и как прошли последние матчи",
      summaryLast: "Последний матч",
      summaryTip: "Главное исправить",
      summaryStrength: "Что получилось",
      summaryOpen: "Открыть разбор",
      summaryToday: "Сегодня",
      summaryNoGames: "Сегодня матчей ещё не было",
      summaryFocus: "Ваш фокус",
      summaryFocusProgress: (met, total) => `получилось в ${met} из ${total}`,
      summaryNoFocus: "Выберите одну проблему, над которой работать: тренер проверит по ней каждый матч.",
      summaryPickFocus: "Выбрать в «Прогрессе»",
      streakFewDeaths: (target) => `${target} ${plural(target, "матч", "матча", "матчей")} подряд — не больше 5 смертей`,
      streakGoodScore: (target) => `${target} ${plural(target, "матч", "матча", "матчей")} подряд с оценкой 60+`,
      streakProgress: (cur, target) => `${Math.min(cur, target)} из ${target}`,
      streakMet: (cur) => `выполнено: ${cur} подряд`,
      streakBest: (best) => `Лучшая серия за последние 30 матчей: ${best}`,
      tiltLosses: (n) => `${n} ${plural(n, "поражение", "поражения", "поражений")} подряд. Может, перерыв — или сыграйте что-нибудь просто для удовольствия.`,
      tiltScore: (a, b, usual) => `Две последние оценки — ${a} и ${b}, а обычно у вас около ${usual}. Может, сделать перерыв?`,
      friendTitle: "Сравнение с другом",
      friendHint: "Friend ID друга, Steam ID или ссылка на профиль (steamcommunity.com/profiles/…). Сравниваются открытые матчи из OpenDota: последние 20 игр каждого.",
      friendPlaceholder: "Friend ID, Steam ID или ссылка на профиль",
      friendCompare: "Сравнить",
      friendSelf: "Это ваш собственный аккаунт.",
      friendFailed: "Не удалось сохранить друга.",
      friendLoading: (name) => `Загружаю матчи ${name} из OpenDota…`,
      friendPrivate: (name) => `${name} скрывает данные матчей.`,
      friendPrivateHint: "Их можно открыть в Dota 2: Настройки → Сообщество → «Открыть данные матчей». Потом нажмите «Обновить» (OpenDota нужен хотя бы один матч после этого).",
      friendOffline: "Для сравнения нужен OpenDota (интернет).",
      friendError: (code) => `OpenDota не ответил${code ? ` (${code})` : ""}. Попробуйте «Обновить» позже.`,
      friendRefresh: "Обновить",
      friendUpdating: "Обновляю…",
      friendChange: "Другой друг",
      friendGroup: "Игры",
      friendGroups: { all: "Все игры", core: "Кор", support: "Саппорт" },
      friendYou: "Вы",
      friendGames: (me, friend) => `игр: у вас ${me}, у друга ${friend}`,
      friendFew: (n) => `Слишком мало игр, чтобы сказать, кто впереди: нужно ${n}+ у каждого.`,
      friendMetrics: { win_rate: "Процент побед", kills: "Убийства", deaths: "Смерти", assists: "Помощь", gpm: "Золото в минуту", xpm: "Опыт в минуту", lh_per_min: "Добивания в минуту", damage_per_min: "Урон по героям в минуту" },
      friendCommon: "Герои, на которых играли оба",
      friendHeroGames: (g1, w1, g2, w2) => `вы ${g1} · ${w1 ?? "—"}%   друг ${g2} · ${w2 ?? "—"}%`,
      friendTheirHeroes: (name) => `Чаще всего играет ${name}`,
      friendNote: "Средние за игру, открытые данные OpenDota, только рейтинговые и обычные режимы. Кор или саппорт — по добиваниям в минуту.",
      rankHistoryTitle: "Ваше звание",
      rankUp: (from, to, since) => `С ${since} вы поднялись с ${from} до ${to}.`,
      rankDown: (from, to, since) => `С ${since} звание снизилось с ${from} до ${to}.`,
      rankNote: "Приложение запоминает ваше звание каждый раз, когда обновляет историю, и отмечает, когда оно меняется.",
      heroBuildTitle: (hero) => `Ваш билд на ${hero}`,
      buildNote: (n, wins) => `Ваши предметы в ${n} разобранных матчах на герое (побед: ${wins}): когда они приходят в победах и в поражениях и как часто вы выигрываете с ними и без них.`,
      buildItem: "Предмет",
      buildGames: "Игр",
      buildWinrate: "Побед с ним",
      buildWithout: "Без него",
      buildWinTime: "В победах",
      buildLossTime: "В поражениях",
      selfTitle: (hero) => `Лучшие и худшие матчи на ${hero}`,
      selfNote: (n) => `Лучшая треть из ${n} последних разобранных матчей на герое против худшей трети, по оценке разбора.`,
      selfBest: "Лучшие",
      selfWorst: "Худшие",
      selfGroup: (count, wr) => `${count} матча · ${wr}% побед`,
      selfMetrics: {
        lh_10: "Добивания к 10:00",
        gpm: "Золото/мин",
        deaths: "Смерти",
        lane_deaths: "Смерти на линии",
        kill_participation: "Участие в убийствах",
        first_item_t: "Первый большой предмет"
      },
      draftTitle: "Драфт",
      draftNote: (hero) => `Как часто ${hero} побеждает каждого вражеского героя (статистика публичных матчей OpenDota).`,
      draftNoData: "Статистики по этим героям пока нет: она загрузится при следующем обновлении истории.",
      draftEnemy: "Враг",
      draftWinrate: "Ваш винрейт",
      draftGames: "игр",
      draftPool: "Ваши герои против этого состава",
      draftPoolNote: "Средний перевес по винрейту над 50% против этих пяти героев.",
      draftPicked: "ваш пик",
      draftBetter: (hero) => `Лучше всего против этого состава подходил ${hero}.`,
      draftCounters: "Ответы на вражеских героев",
      draftReasons: { evasion: "уклонение", illusions: "иллюзии", invisibility: "невидимость", healing: "лечение", targeted: "убивал контролем" },
      draftForSupports: "задача саппорта",
      draftBought: "куплен",
      coachTitle: "Разбор тренера",
      coachCareerTitle: "Разбор тренера по последним матчам",
      coachTag: "ИИ",
      coachPending: "Тренер пишет разбор. Это занимает до минуты.",
      coachCareerPending: "Тренер смотрит ваши последние матчи. Это занимает до минуты.",
      coachWaiting: "ИИ ждёт, пока OpenDota изучит реплей (обычно несколько минут): так у него больше данных.",
      coachNow: "Разобрать сейчас",
      coachUpdating: "Обновляется по новым данным…",
      coachRetry: "Повторить",
      coachRewrite: "Написать заново",
      coachNotEnough: (n) => `Тренеру нужно хотя бы ${n} разобранных матча.`,
      coachTurning: "Ключевые моменты",
      coachMistakes: "Главные ошибки",
      coachFix: "В следующий раз",
      coachStrengths: "Что получилось",
      coachNextGame: "Цели на следующую игру",
      coachPatterns: "Повторяющиеся проблемы",
      coachTrain: "Как тренировать",
      coachPlan: "План на следующие игры",
      coachFooter: (provider, model) => `Написано ИИ (${provider} · ${model}) по данным разбора. Числа, время, герои и предметы сверены с ними.`,
      coachErrors: {
        rate_limited: "Бесплатный лимит ИИ пока исчерпан. Попробуйте через несколько минут.",
        busy: "ИИ сейчас перегружен. Попробуйте через несколько минут.",
        invalid_key: "Ключ не подошёл. Проверьте его в настройках ИИ-тренера.",
        region: "Этот ИИ не работает из вашей страны. Выберите другой (например, OpenRouter) или включите VPN; ключ сохранён.",
        timeout: "ИИ слишком долго отвечал.",
        offline: "Нет связи с ИИ: проверьте интернет.",
        unverified: "В ответе ИИ были факты, которых нет в данных, поэтому он не показан. Попробуйте ещё раз.",
        bad_response: "ИИ ответил ошибкой. Попробуйте позже.",
        no_key: "Ключ ещё не указан."
      },
      askTitle: "Спросить тренера",
      askHint: "Вопрос об этом матче. Ответ строится только по данным матча и проходит ту же проверку фактов.",
      askPlaceholder: "Например: почему я проиграл линию?",
      askButton: "Спросить",
      askThinking: "Тренер думает…",
      askSuggestions: ["Что решило эту игру?", "Что изменить на линии?", "Вовремя ли я собрал предметы?"],
      askCareerHint: "Вопрос о ваших последних матчах: герои, противники, привычки. Ответ строится только по вашей статистике и проходит ту же проверку фактов.",
      askCareerPlaceholder: "Например: против каких героев мне сложнее всего?",
      askCareerSuggestions: ["Против каких героев мне сложнее всего?", "Какая ошибка стоит мне больше всего игр?", "На каком герое мне стоит играть чаще?"],
      askErrors: {
        unverified: "Тренер не смог ответить по данным этого матча. Попробуйте спросить иначе.",
        empty_question: "Сначала напишите вопрос.",
        no_review: "Разбор этого матча ещё не готов.",
        not_enough: "Пока мало разобранных матчей: сначала откройте несколько разборов.",
        off: "Сначала включите ИИ-тренера в настройках."
      },
      aiSettingsTitle: "ИИ-тренер",
      aiOnTitle: "ИИ-тренер включён",
      aiCheckNow: "Проверить ключ",
      aiCheckOk: "Ключ работает.",
      aiOffTitle: "ИИ-тренер выключен",
      aiOffHint: "После каждого матча ИИ простыми словами объясняет, что получилось и что исправить, — как тренер, который посмотрел ваш реплей. Бесплатно: нужен только ключ от Google (Gemini), Groq или OpenRouter.",
      aiTurnOn: "Включить",
      aiSetupHint: "Ключ — это как пароль, с которым приложение может обращаться к ИИ. Получите бесплатный (минута, без карты) и вставьте сюда. ИИ только объясняет: все числа по-прежнему берутся из разбора. Данные матча (без вашего Steam ID) уходят на выбранный сайт.",
      aiService: "Откуда ключ",
      aiKey: "Ключ",
      aiKeyPlaceholder: "Вставьте ключ",
      aiModel: "Модель ИИ",
      aiAdvanced: "Для опытных",
      aiModelHint: "оставьте пустым — будет по умолчанию",
      aiGetKey: "Получить бесплатный ключ",
      aiSave: "Проверить и сохранить",
      aiChecking: "Проверяем ключ…",
      aiSaved: "Ключ работает. Тренер включён.",
      aiSavedWarn: (reason) => `Ключ сохранён, но проверка не прошла: ${reason}`,
      aiSettings: "Настройки ИИ",
      aiCurrent: (provider, model, hint) => [provider, model, hint ? `ключ ${hint}` : ""].filter(Boolean).join(" · "),
      aiEnvKey: "Ключ уже задан в файле настроек приложения.",
      aiChangeKey: "Сменить ключ",
      aiDisable: "Отключить",
      aiCancel: "Отмена"
    }
  };

  // Chart colours come from the design tokens (assets/ui/tokens.css).
  const cssVar = (name, fallback) =>
    getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
  const VIZ_1 = cssVar("--viz-1", "#3987e5");
  const VIZ_2 = cssVar("--viz-2", "#e5963a");
  const TAB_KEY = "dota-ai-coach.tab";
  const api = window.launcherApi;

  const state = {
    filter: { heroId: null, result: "all" },
    careerHero: null,
    heroes: [],
    matchesStats: null,
    matchesSkipped: null,
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
    profile: null,
    friends: null,
    linkError: "",
    lastPlayerRefresh: 0,
    // AI coach settings panel: null (closed) | "form" | "info"
    aiPanel: null,
    ai: null,
    aiMessage: null
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

  // A fraction the way the player reads it: «7,5» in Russian, «7.5» in English.
  function decimal(value, digits = 1) {
    if (value === null || value === undefined || !Number.isFinite(Number(value))) {
      return "—";
    }
    return Number(value).toLocaleString(state.locale, { minimumFractionDigits: digits, maximumFractionDigits: digits });
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

  // A hero portrait / item icon next to its name (dota-icons.js); plain text
  // when the icon module is missing.
  function heroLabel(value, name, size = "sm") {
    const text = name || window.DotaIcons?.hero(value)?.name || String(value ?? "—");
    if (!window.DotaIcons || value === null || value === undefined || value === "") {
      return h("span", { class: "hero-cell", text });
    }
    return h("span", { class: "hero-cell with-pic" }, window.DotaIcons.heroPicture(document, value, size), h("span", { text }));
  }

  function itemPic(value, size = "sm") {
    return window.DotaIcons ? window.DotaIcons.itemPicture(document, value, size) : null;
  }

  function itemLabel(value, name, size = "sm") {
    return h("span", { class: "item-label with-pic" }, itemPic(value, size), h("span", { text: name || String(value ?? "") }));
  }

  function card(title, iconName, body, extraHead) {
    return h(
      "section",
      { class: "card" },
      h("header", { class: "card-head" }, icon(iconName), h("h2", { text: title }), extraHead ? h("span", { class: "card-head-extra" }, extraHead) : null),
      h("div", { class: "card-body" }, body)
    );
  }

  // A long list shows its first `keep` items and a «show N more» button; the
  // rest is only hidden on screen, so a saved PDF keeps every item.
  function foldList(list, keep) {
    const items = Array.from(list.children);
    if (items.length <= keep + 1) {
      return list;
    }
    items.slice(keep).forEach((item) => item.classList.add("fold-extra"));
    const hidden = items.length - keep;
    const wrap = h("div", { class: "fold is-folded" }, list);
    const toggle = h("button", { class: "btn btn-ghost btn-sm fold-toggle no-print", type: "button", text: t("foldMore", hidden) });
    toggle.addEventListener("click", () => {
      const folded = wrap.classList.toggle("is-folded");
      toggle.textContent = folded ? t("foldMore", hidden) : t("foldLess");
    });
    wrap.appendChild(toggle);
    return wrap;
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

  // «What does this mean?» under a card whose numbers are not obvious: a
  // folded explanation, so it costs one line until someone asks.
  function explain(key) {
    return h("details", { class: "explain no-print" }, h("summary", {}, icon("circle-help"), h("span", { text: t("explainTitle") })), h("p", { text: t(key) }));
  }

  // The letter next to the score ring: the ring already carries the colour, so
  // no third signal (a coloured dot) for the same value.
  function gradeLetter(score) {
    const letter = score >= 80 ? "A" : score >= 65 ? "B" : score >= 50 ? "C" : "D";
    return h("span", { class: "grade", text: letter });
  }

  // --- navigation -------------------------------------------------------------

  function setView(view, { remember = true } = {}) {
    state.view = view;
    state.aiPanel = null;
    state.aiMessage = null;
    const tabView = view === "match" ? "matches" : view;
    for (const tab of document.querySelectorAll(".tabs [data-view]")) {
      tab.setAttribute("aria-selected", String(tab.dataset.view === tabView));
    }
    for (const name of ["home", "matches", "match", "progress", "profile", "settings"]) {
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
    } else if (view === "profile") {
      loadProfile();
    } else if (view === "settings") {
      renderAiSettings({ load: true });
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

  // The tab's title and the link form, with what the tab will show once linked.
  function linkPage(view) {
    const titles = { matches: ["matchesTitle", "matchesSub"], progress: ["progressTitle", "progressSub"], profile: ["pfTitle", "pfSub"] };
    const [title, sub] = titles[view] || titles.matches;
    return [pageHead(t(title), t(sub)), linkPanel(view)];
  }

  function linkPanel(view) {
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
        error,
        linkPerks(view)
      )
    );
  }

  function linkPerks(view, heading = "linkSoon") {
    const perks = t(`linkPerks.${view}`);
    if (!Array.isArray(perks)) {
      return null;
    }
    return h(
      "div",
      { class: "link-perks" },
      h("p", { class: "link-perks-title", text: t(heading) }),
      h("ul", {}, perks.map(([name, text]) => h("li", {}, icon(name), h("span", { text }))))
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
      const result = await call("matches", { limit: Math.max(30, state.matches.length), ...filterArgs() });
      if (result.ok) {
        state.matches = result.data.items || [];
        state.matchesTotal = result.data.total || 0;
        state.matchesStats = result.data.stats || null;
        state.matchesSkipped = result.data.skipped || null;
        state.heroes = result.data.heroes || [];
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
      root.replaceChildren(...linkPage("matches"));
      hydrate(root);
      return;
    }
    const liveMatch = state.player.live_match;
    const liveNotice = liveMatch ? h("div", { class: "notice" }, h("span", { class: "dot dot-live", "data-tone": "good" }), h("span", { text: t("liveMatch", liveMatch.hero) })) : null;
    let body;
    const filtered = state.filter.heroId !== null || state.filter.result !== "all";
    if (!state.matchesLoaded) {
      body = skeletonRows(5);
    } else if (!state.matches.length && filtered) {
      body = emptyState("history", t("filterEmptyTitle"), t("filterEmptyHint"));
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
                const result = await call("matches", { limit: 30, offset: state.matches.length, ...filterArgs() });
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
    const filters = state.matchesLoaded && (state.heroes.length > 1 || filtered) ? filterBar() : null;
    const skipped = state.matchesLoaded && state.matchesSkipped
      ? h("p", { class: "muted small skipped-note", text: t("skippedModes", state.matchesSkipped.count, state.matchesSkipped.turbo, state.matchesSkipped.of) })
      : null;
    root.replaceChildren(
      pageHead(t("matchesTitle"), t("matchesSub")),
      playerBar(),
      liveNotice || "",
      card(t("matchesTableTitle"), "history", [filters, body, skipped].filter(Boolean), state.matchesTotal ? h("span", { class: "num", text: String(state.matchesTotal) }) : null)
    );
    hydrate(root);
  }

  function filterArgs() {
    return {
      heroId: state.filter.heroId === null ? undefined : state.filter.heroId,
      result: state.filter.result === "all" ? undefined : state.filter.result
    };
  }

  function setFilter(patch) {
    state.filter = { ...state.filter, ...patch };
    state.matches = [];
    loadMatches();
  }

  // Result + hero filter and what the filtered games add up to.
  function filterBar() {
    const results = h(
      "div",
      { class: "segmented segmented-sm", role: "radiogroup", "aria-label": t("filterResult") },
      ["all", "win", "loss"].map((value) =>
        h("button", {
          type: "button",
          role: "radio",
          "aria-checked": String(state.filter.result === value),
          text: t(`filterResults.${value}`),
          onclick: () => setFilter({ result: value })
        })
      )
    );
    const select = h(
      "select",
      {
        class: "input select",
        "aria-label": t("filterHero"),
        onchange: (event) => setFilter({ heroId: event.target.value === "" ? null : Number(event.target.value) })
      },
      h("option", { value: "", text: t("filterAllHeroes") }),
      state.heroes.map((hero) => {
        const option = h("option", { value: String(hero.hero_id), text: `${hero.hero || "—"} · ${hero.games}` });
        option.selected = state.filter.heroId === hero.hero_id;
        return option;
      })
    );
    const stats = state.matchesStats;
    const summary = stats && stats.games
      ? h("p", { class: "muted small filter-summary num", text: t("filterSummary", stats.games, stats.winrate, stats.avg_score) })
      : null;
    return h("div", { class: "filter-bar" }, h("div", { class: "filter-controls" }, results, select), summary);
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
            dataset: { result: row.win === true ? "win" : row.win === false ? "loss" : "unknown" },
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
          h("td", {}, heroLabel(row.hero_id || row.hero, row.hero || "—")),
          h("td", { class: "num-col num", text: row.kills == null ? "—" : `${row.kills} / ${row.deaths} / ${row.assists}` }),
          h("td", { class: "num-col num", text: number(row.gpm) }),
          h("td", { class: "num-col num hide-narrow", text: number(row.lh_10) }),
          h("td", { class: "num-col num", text: clock(row.duration) }),
          h("td", {}, h("span", { class: "score-cell" }, scoreRing(row.score, "sm"), row.score == null ? null : gradeLetter(row.score))),
          h("td", { class: "muted hide-narrow", text: relativeTime(row.start_time) })
        )
      );
    }
    return h("table", { class: "table" }, head, body);
  }

  // --- match review -------------------------------------------------------------

  async function openMatch(matchId) {
    state.adviceLogOpen = false;
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
    scheduleMatchRefresh(String(matchId));
  }

  // While the review is loading (queued OpenDota fetch) or OpenDota is still
  // parsing the replay, re-ask the backend; stops when the view changes.
  const PENDING_PARSE = new Set(["waiting_opendota", "parsing"]);
  let matchRefreshTimer = null;

  function scheduleMatchRefresh(matchId) {
    clearTimeout(matchRefreshTimer);
    const detail = state.match;
    if (!detail || detail.error || state.matchId !== matchId || state.view !== "match") {
      return;
    }
    const coachPending = detail.coach?.state === "pending";
    const waiting = detail.loading || coachPending || PENDING_PARSE.has(detail.parse_status);
    if (!waiting) {
      return;
    }
    const fast = detail.loading || coachPending;
    matchRefreshTimer = setTimeout(() => openMatchQuietly(matchId), fast ? 4000 : 30000);
  }

  async function openMatchQuietly(matchId) {
    if (state.matchId !== matchId || state.view !== "match") {
      return;
    }
    const result = await call("match", { matchId });
    if (result.ok && state.matchId === matchId && state.view === "match") {
      const changed = JSON.stringify(result.data) !== JSON.stringify(state.match);
      state.match = result.data;
      // Don't wipe a key or a question the player is typing, or a question on its way.
      const asking = state.askBusy || Boolean(document.querySelector(".ask-input")?.value.trim());
      if (changed && state.aiPanel !== "form" && !asking) {
        renderMatch();
      }
    }
    scheduleMatchRefresh(matchId);
  }

  // Saves the current view as a PDF (light print theme, see @media print).
  // «Поделиться разбором»: a link to the public part of the review (main.js createShare).
  // `kind` "progress": the same panel for the Progress page (main.js keys it "progress").
  function shareButton(panel, detail, kind = "match") {
    const button = h("button", { class: "btn btn-ghost btn-sm", type: "button", "aria-expanded": "false" }, icon("share-2"), h("span", { text: t("shareButton") }));
    button.addEventListener("click", async () => {
      const open = panel.hidden;
      panel.hidden = !open;
      button.setAttribute("aria-expanded", String(open));
      if (open) {
        panel.replaceChildren(skeletonRows(2));
        const status = await api.shareStatus(shareKey(detail, kind));
        renderSharePanel(panel, detail, status && status.ok ? status.share : null, "", kind);
      }
    });
    return button;
  }

  function shareKey(detail, kind) {
    return kind === "progress" ? "progress" : String(detail.match_id);
  }

  function renderSharePanel(panel, detail, share, message, kind = "match") {
    const matchId = shareKey(detail, kind);
    const text = (key, ...args) => t(kind === "progress" && TEXT.en[`${key}Progress`] ? `${key}Progress` : key, ...args);
    const coachReady = detail.coach && detail.coach.state === "ready";
    const note = h("p", { class: "muted small share-note", role: "status", text: message || "" });
    let body;
    if (share) {
      const expires = new Date(share.expiresAt).toLocaleDateString(state.locale === "ru" ? "ru-RU" : "en-GB");
      const link = h("input", { class: "input share-link", type: "text", readonly: true, value: share.url, "aria-label": text("shareLink") });
      link.addEventListener("focus", () => link.select());
      body = h(
        "div",
        { class: "share-body" },
        h("div", { class: "link-form" }, link, h("button", { class: "btn btn-primary", type: "button", onclick: async () => {
          const copied = await api.shareCopy(matchId);
          renderSharePanel(panel, detail, share, copied ? t("shareCopied") : "", kind);
        } }, icon("copy"), h("span", { text: t("shareCopy") }))),
        h("p", { class: "muted small", text: t("shareExpires", expires) + (share.withCoach ? ` ${t("shareWithCoach")}` : "") }),
        h(
          "div",
          { class: "toolbar-actions" },
          h("button", { class: "btn btn-ghost btn-sm", type: "button", onclick: () => api.shareOpen(matchId) }, icon("external-link"), h("span", { text: t("shareOpen") })),
          h("button", { class: "btn btn-ghost btn-sm", type: "button", onclick: async (event) => {
            event.currentTarget.disabled = true;
            const result = await api.shareDelete(matchId);
            renderSharePanel(panel, detail, result && result.ok ? null : share, result && result.ok ? t("shareDeleted") : t("shareFailed", result?.code || ""), kind);
          } }, icon("trash-2"), h("span", { text: t("shareDelete") }))
        )
      );
    } else {
      const coach = coachReady ? h("input", { type: "checkbox", class: "checkbox", id: "share-coach", checked: true }) : null;
      const create = h("button", { class: "btn btn-primary", type: "button" }, icon("share-2"), h("span", { text: t("shareCreate") }));
      create.addEventListener("click", async () => {
        create.disabled = true;
        note.textContent = t("shareCreating");
        const result = await api.shareCreate(matchId, Boolean(coach && coach.checked));
        renderSharePanel(panel, detail, result && result.ok ? result.share : null, result && result.ok ? "" : t("shareFailed", result?.code || ""), kind);
      });
      body = h(
        "div",
        { class: "share-body" },
        h("p", { text: text("shareWhat") }),
        h("p", { class: "muted small", text: text("shareNot") }),
        coach ? h("label", { class: "share-check" }, coach, h("span", { text: t("shareCoach") })) : null,
        h("div", { class: "toolbar-actions" }, create)
      );
    }
    panel.replaceChildren(
      h("header", { class: "card-head" }, icon("share-2"), h("h2", { text: text("shareTitle") })),
      h("div", { class: "card-body" }, body, note)
    );
    hydrate(panel);
  }

  function pdfButton(kind) {
    const note = h("span", { class: "muted small pdf-note" });
    const button = h(
      "button",
      {
        class: "btn btn-ghost btn-sm",
        type: "button",
        onclick: async () => {
          button.disabled = true;
          note.textContent = "";
          const printDate = document.getElementById("print-date");
          if (printDate) {
            printDate.textContent = new Date().toLocaleDateString(state.locale === "ru" ? "ru-RU" : "en-GB");
          }
          try {
            const result = await api.exportPdf(kind, kind === "match" ? String(state.matchId) : "");
            if (result && result.ok) {
              note.textContent = t("pdfSaved", result.path.split(/[\\/]/).pop());
            } else if (result && !result.canceled) {
              note.textContent = t("pdfFailed");
            }
          } finally {
            button.disabled = false;
          }
        }
      },
      icon("printer"),
      h("span", { text: t("pdfSave") })
    );
    return h("span", { class: "pdf-action" }, note, button);
  }

  // A review that fails to draw must say so: before, the loading skeleton
  // stayed on screen forever.
  function renderMatch() {
    try {
      drawMatch();
    } catch (error) {
      console.error("review render failed", error);
      const root = document.getElementById("match-root");
      const back = h("div", { class: "review-toolbar no-print" }, h("button", { class: "btn btn-ghost btn-sm back", type: "button", onclick: () => setView("matches") }, icon("chevron-left"), h("span", { text: t("back") })));
      root.replaceChildren(back, card(t("reviewError"), "circle-alert", emptyState("circle-alert", t("reviewRenderFailed"), String(error && error.message ? error.message : error))));
      hydrate(root);
    }
  }

  // The match next to the open one in the list the player came from (newest
  // first): step -1 = newer, +1 = older. Null when the review was opened from
  // elsewhere and the match is not in the loaded list, or at its end.
  function neighbourMatch(step) {
    const index = state.matches.findIndex((row) => String(row.match_id) === state.matchId);
    return index < 0 ? null : state.matches[index + step] || null;
  }

  // «‹ Newer · Older ›» next to «Back»: several reviews in a row without the list.
  function neighbourButtons() {
    if (!state.matches.some((row) => String(row.match_id) === state.matchId)) {
      return null;
    }
    const button = (step, iconName, label, hint) => {
      const row = neighbourMatch(step);
      const parts = [h("span", { text: label })];
      parts[step < 0 ? "unshift" : "push"](icon(iconName));
      return h(
        "button",
        {
          class: "btn btn-ghost btn-sm",
          type: "button",
          disabled: !row,
          title: row ? hint(row.hero || "") : "",
          onclick: () => row && openMatch(row.match_id)
        },
        parts
      );
    };
    return h(
      "span",
      { class: "neighbour-nav" },
      button(-1, "chevron-left", t("newerMatch"), (hero) => t("newerMatchHint", hero)),
      button(1, "chevron-right", t("olderMatch"), (hero) => t("olderMatchHint", hero))
    );
  }

  function drawMatch() {
    const root = document.getElementById("match-root");
    const backButton = h("button", { class: "btn btn-ghost btn-sm back", type: "button", onclick: () => setView("matches") }, icon("chevron-left"), h("span", { text: t("back") }));
    const detail = state.match;
    const sharePanel = h("section", { class: "card share-panel no-print", hidden: true });
    const back = h(
      "div",
      { class: "review-toolbar no-print" },
      h("span", { class: "review-nav" }, backButton, neighbourButtons()),
      detail && detail.analysis
        ? h("span", { class: "toolbar-actions" }, shareButton(sharePanel, detail), pdfButton("match"))
        : null
    );
    if (!detail) {
      root.replaceChildren(back, card(t("reviewLoading"), "activity", skeletonRows(6)));
      hydrate(root);
      return;
    }
    if (detail.error) {
      root.replaceChildren(back, card(t("reviewError"), "circle-alert", emptyState("circle-alert", t("reviewPending"), detail.error)));
      hydrate(root);
      return;
    }
    const analysis = detail.analysis;
    const summary = detail.summary || {};
    const parts = [back, sharePanel, reviewHeader(detail, analysis, summary)];
    if (!analysis) {
      parts.push(card(t("reviewLoading"), "hourglass", emptyState("hourglass", t("reviewPending"), tOptional(`parseStatus.${detail.parse_status}`) || "")));
    } else {
      // The story of the match on the left, the side facts on the right (one
      // column in a narrow window, main first).
      const main = [];
      const side = [];
      const add = (list, element) => {
        if (element) {
          list.push(element);
        }
      };
      // Zones: what to fix first, then how the match went; on the side the
      // scores and comparisons, then the map and the items.
      const rest = (analysis.improvements || []).filter((f) => !(analysis.focus || []).includes(f.id));
      add(main, zone(t("zoneFix"), t("zoneFixHint"), [
        coachCard(detail.coach, "match"),
        focusCard(analysis, detail),
        // Past «what to fix first» the rest starts folded: a first review
        // was a wall of lists.
        rest.length ? findingsCard(t("improveTitle"), "target", rest, "", true, detail.repeats, 1) : null,
        askCard(detail)
      ]));
      add(main, zone(t("zoneStory"), t("zoneStoryHint"), [chartCard(analysis), laneCard(analysis), deathsCard(analysis), adviceLogCard(analysis)]));
      add(side, zone(t("zoneScores"), t("zoneScoresHint"), [
        sectionsCard(analysis),
        findingsCard(t("strengthsTitle"), "sparkles", analysis.strengths, t("nothingStrong"), false),
        rankCard(analysis),
        draftCard(analysis)
      ]));
      add(side, zone(t("zoneMapItems"), t("zoneMapItemsHint"), [mapCard(analysis), buildCard(analysis), skillsCard(analysis), momentsCard(analysis)]));
      parts.push(twoColumns(main, side));
    }
    if (detail.scoreboard) {
      parts.push(zone(t("zoneTeams"), "", [scoreboardCard(detail.scoreboard)]));
    }
    root.replaceChildren(...parts);
    hydrate(root);
    // Charts measure their container, so draw after insertion.
    drawMatchCharts(root, analysis);
  }

  // A page title (Matches, Progress) with its one-line summary and actions.
  function pageHead(title, sub, actions) {
    return h(
      "header",
      { class: "page-head" },
      h("div", { class: "page-head-text" }, h("h1", { class: "page-title", text: title }), sub ? h("p", { class: "page-sub", text: sub }) : null),
      actions ? h("div", { class: "page-actions no-print" }, actions) : null
    );
  }

  // Cards grouped under a small heading (styles.css .zone); null without cards.
  function zone(title, hint, cards) {
    const items = cards.filter(Boolean);
    if (!items.length) {
      return null;
    }
    return h("section", { class: "zone" }, h("header", { class: "zone-head" }, h("h2", { class: "zone-title", text: title }), hint ? h("p", { class: "zone-hint", text: hint }) : null), items);
  }

  // Main and side cards as two columns (styles.css .layout-2).
  function twoColumns(main, side) {
    return h("div", { class: "layout-2" }, h("div", { class: "col col-main" }, main), h("div", { class: "col col-side" }, side));
  }

  // Each chart host by its kind (also on window resize).
  function drawMatchCharts(root, analysis) {
    if (!root || !analysis) {
      return;
    }
    root.querySelectorAll("[data-chart='match']").forEach((host) => drawChart(host, analysis));
    root.querySelectorAll("[data-chart='timing']").forEach((host) => drawTimingChart(host, analysis));
    root.querySelectorAll("[data-chart='map']").forEach((host) => drawMap(host, analysis.map));
    root.querySelectorAll("[data-chart='map-empty']").forEach((host) => drawMap(host, {}));
  }

  // «OpenDota · Dotabuff · STRATZ»: the same match on the sites players use.
  function matchSiteLinks(matchId) {
    if (!/^\d{1,20}$/.test(String(matchId ?? "")) || typeof api.openMatchSite !== "function") {
      return null;
    }
    const sites = [["opendota", "OpenDota"], ["dotabuff", "Dotabuff"], ["stratz", "STRATZ"]];
    return h(
      "span",
      { class: "site-links no-print" },
      sites.map(([site, name]) =>
        h("button", { class: "site-link", type: "button", title: t("openOnSite", name), onclick: () => api.openMatchSite(site, String(matchId)) }, h("span", { text: name }), icon("external-link"))
      )
    );
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
        window.DotaIcons ? h("div", { class: "review-portrait" }, window.DotaIcons.heroPicture(document, summary.hero_id || headline.hero_id || headline.hero || summary.hero, "lg")) : null,
        h(
          "div",
          { class: "review-title" },
          h("h2", { class: "review-hero", text: headline.hero || summary.hero || "—" }),
          h("p", { class: "review-meta" }, resultBadge(win), h("span", { class: "muted", text: `· ${relativeTime(summary.start_time)} · #${detail.match_id}` }), matchSiteLinks(detail.match_id)),
          h("p", { class: "review-source" }, icon(analysis && analysis.parsed ? "circle-check" : "info"), h("span", { text: sourceText })),
          statusText ? h("p", { class: "muted small", text: statusText }) : null,
          baselineLine(detail.baseline),
          detail.focus
            ? h(
                "p",
                { class: "review-goal", dataset: { met: String(detail.focus.met) } },
                h("span", { class: "dot", "data-tone": detail.focus.met ? "good" : "bad" }),
                h("span", { text: t("goalMatch", detail.focus.title, detail.focus.met) })
              )
            : null,
          requestButton ? h("div", { class: "row" }, requestButton, requestNote) : null
        ),
        score !== null && score !== undefined
          ? h(
              "div",
              { class: "score-block", title: `${score} ${t("scoreOf")}` },
              scoreRing(score, "lg"),
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

  // "Against your 8 other matches on Juggernaut: score +17 · GPM +94 · deaths −2".
  function baselineLine(baseline) {
    if (!baseline || !baseline.metrics || !baseline.metrics.length) {
      return null;
    }
    const format = (key, value) => {
      const rounded = key === "deaths" ? Math.round(value * 10) / 10 : Math.round(value);
      const text = Math.abs(rounded).toLocaleString(state.locale);
      return `${rounded > 0 ? "+" : rounded < 0 ? "−" : ""}${text}`;
    };
    return h(
      "p",
      { class: "review-baseline" },
      h("span", { class: "muted", text: t("baselineIntro", baseline.games, baseline.hero || "—") }),
      baseline.metrics.map((metric) =>
        h(
          "span",
          {
            class: "baseline-chip num",
            dataset: { tone: metric.tone },
            title: t("baselineTitle", metric.key === "deaths" ? metric.average.toLocaleString(state.locale) : Math.round(metric.average).toLocaleString(state.locale))
          },
          metric.tone === "same" ? null : h("span", { class: "dot", "data-tone": metric.tone }),
          h("span", { text: `${t(`baselineLabels.${metric.key}`)} ${metric.tone === "same" ? t("baselineSame") : format(metric.key, metric.delta)}` })
        )
      )
    );
  }

  // finding_history: the same problem in the player's earlier matches.
  function repeatNote(repeat) {
    if (!repeat) {
      return null;
    }
    const text = repeat.in_a_row >= 3 ? t("repeatInARow", repeat.in_a_row) : t("repeatInLast", repeat.in_last, repeat.of);
    return h("p", { class: "finding-repeat" }, icon("repeat"), h("span", { text }));
  }

  function findingItem(finding, index, repeats) {
    return h(
      "li",
      { class: `finding finding-${finding.kind}` },
      index !== undefined ? h("span", { class: "finding-index num", text: String(index + 1) }) : h("span", { class: "dot", "data-tone": finding.kind === "strength" ? "good" : finding.severity >= 3 ? "bad" : "warn" }),
      h(
        "div",
        { class: "finding-body" },
        h("p", { class: "finding-title" }, h("span", { text: finding.title }), finding.section_label ? h("span", { class: "tag", text: finding.section_label }) : null),
        h("p", { class: "finding-text", text: finding.text }),
        repeatNote(repeats && repeats[finding.id]),
        finding.drill ? h("p", { class: "finding-drill" }, icon("lightbulb"), h("span", {}, h("strong", { text: `${t("drill")}: ` }), finding.drill)) : null
      )
    );
  }

  function focusCard(analysis, detail) {
    const focus = (analysis.improvements || []).filter((f) => (analysis.focus || []).includes(f.id));
    if (!focus.length) {
      return card(t("focusTitle"), "target", emptyState("circle-check", t("nothingToImprove"), ""));
    }
    const list = h("ol", { class: "findings" });
    const render = () =>
      list.replaceChildren(
        ...focus.map((finding, index) => {
          const item = findingItem(finding, index, detail && detail.repeats);
          const body = item.querySelector(".finding-body");
          if (detail && detail.focus_id === finding.id) {
            item.querySelector(".finding-title").append(h("span", { class: "tag tag-accent", text: t("goalCurrent") }));
          } else if (detail && (detail.focusable || []).includes(finding.id)) {
            // Work on it from the next game (the Progress page tracks it).
            body.append(
              h(
                "button",
                {
                  class: "btn btn-ghost btn-sm goal-set no-print",
                  type: "button",
                  onclick: async (event) => {
                    event.currentTarget.disabled = true;
                    const button = event.currentTarget;
                    const result = await call("focusSet", { findingId: finding.id });
                    if (!result.ok) {
                      button.disabled = false;
                      button.replaceChildren(icon("circle-alert"), h("span", { text: t("goalSetFailed") }));
                      hydrate(button);
                      return;
                    }
                    detail.focus_id = finding.id;
                    state.career = null;
                    render();
                    hydrate(list);
                  }
                },
                icon("target"),
                h("span", { text: t("goalSet") })
              )
            );
          }
          return item;
        })
      );
    render();
    return card(t("focusTitle"), "target", list);
  }

  function findingsCard(title, iconName, findings, emptyText, improve, repeats, fold) {
    if (!findings || !findings.length) {
      return card(title, iconName, h("p", { class: "muted", text: emptyText }));
    }
    const list = h("ul", { class: `findings ${improve ? "" : "findings-compact"}` }, findings.map((f) => findingItem(f, undefined, repeats)));
    return card(title, iconName, fold ? foldList(list, fold) : list);
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
    return card(t("sectionsTitle"), "gauge", h("div", {}, h("div", { class: "sections" }, rows), explain("explainScore")));
  }

  // Schematic map: path and deaths from the app's own recording, laning
  // position and wards from the parsed replay (either may be missing).
  function mapCard(analysis) {
    const data = analysis.map;
    const hasData = Boolean(
      data && ((data.deaths || []).length || (data.wards || []).length || (data.path || []).length > 1 || (data.lane || []).length)
    );
    if (!hasData) {
      // No positions (an unparsed replay, no app during the game): the map
      // itself and how to get the positions.
      const body = h(
        "div",
        {},
        h("p", { class: "muted small chart-note", text: t("mapEmpty") }),
        h("div", { class: "map-layout" }, h("div", { class: "chart-host", dataset: { chart: "map-empty" } }))
      );
      return card(t("mapTitle"), "map", body);
    }
    const hasPath = (data.path || []).length > 1;
    const hasReplay = (data.wards || []).length > 0 || (data.lane || []).length > 0;
    const hintKey = hasPath && hasReplay ? "both" : hasPath ? "path" : "replay";
    const facts = [];
    const deaths = data.deaths || [];
    if (deaths.length) {
      const bySide = data.deaths_by_side || {};
      facts.push(h("p", { class: "fact-line" }, h("strong", { text: t("mapDeaths") }), h("span", { class: "num", text: String(deaths.length) })));
      for (const side of ["own", "river", "enemy"]) {
        if (bySide[side]) {
          facts.push(h("p", { class: "fact-line muted small" }, h("span", { text: t(`mapSide.${side}`) }), h("span", { class: "num", text: String(bySide[side]) })));
        }
      }
      const spot = (data.spots || [])[0];
      if (spot && spot.label) {
        facts.push(h("p", { class: "fact-line map-spot-line" }, h("span", { text: t("mapSpotLine", spot.label, spot.count) })));
      }
    }
    const wards = data.wards || [];
    if (wards.length) {
      const obs = wards.filter((w) => w.kind === "obs").length;
      facts.push(h("p", { class: "fact-line" }, h("strong", { text: t("mapWards") }), h("span", { class: "num", text: String(wards.length) })));
      facts.push(h("p", { class: "muted small", text: t("mapWardsLine", obs, wards.length - obs) }));
    }
    const body = h(
      "div",
      {},
      h("p", { class: "muted small chart-note", text: t(`mapHint.${hintKey}`) }),
      h("div", { class: "map-layout" }, h("div", { class: "chart-host", dataset: { chart: "map" } }), facts.length ? h("div", { class: "map-facts" }, facts) : null)
    );
    return card(t("mapTitle"), "map", body);
  }

  // The game's minimap (patch 7.40 art, as OpenDota publishes it): positions in
  // replay units 8192..24576 on both axes cover the whole picture.
  const MAP_BACKGROUND = { href: "dota-asset://map/detailed_740", bounds: [8192, 24576] };

  function drawMap(host, data) {
    window.LauncherCharts.map(host, {
      background: MAP_BACKGROUND,
      bounds: data.bounds,
      path: data.path,
      lane: data.lane,
      wards: data.wards,
      // Places where the deaths repeat (map_analysis.death_spots), with their times.
      spots: (data.spots || []).map((spot) => ({
        ...spot,
        title: t("mapSpotTitle", spot.count, spot.label || ""),
        detail: (spot.times || []).map(clock).join(", ")
      })),
      deaths: (data.deaths || []).map((death) => ({ ...death, killer: death.killer ? t("killedBy", death.killer) : "" })),
      labels: t("mapLabels"),
      clock,
      ariaLabel: t("mapTitle")
    });
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
    const best = state.match && state.match.best_on_hero;
    let note = null;
    if (best && best.self_best) {
      note = h("p", { class: "muted small chart-note", text: t("bestOnHeroSelf", best.of) });
    } else if (best && best.score) {
      note = h("p", { class: "muted small chart-note", text: t("bestOnHeroNote", best.score, relativeTime(best.start_time)) });
    }
    return card(t("chartTitle"), "chart-line", note ? h("div", {}, host, note) : host, toggle);
  }

  function drawChart(host, analysis) {
    const series = analysis.series || {};
    const values = { lh: series.last_hits, gold: series.gold, xp: series.xp }[state.chartMetric] || [];
    const label = { lh: t("chartLh"), gold: t("chartGold"), xp: t("chartXp") }[state.chartMetric];
    const markers = (series.deaths || []).map((seconds) => ({ x: seconds / 60, label: `${t("deathsMarker")} ${clock(seconds)}` }));
    // The player's best match on this hero, dashed (PlayerService._best_on_hero).
    const best = state.match && state.match.best_on_hero;
    const bestSeries = best && best.series ? { lh: best.series.last_hits, gold: best.series.gold, xp: best.series.xp }[state.chartMetric] : null;
    const lines = [{ label: `${t("you")} · ${label}`, values, color: VIZ_1, area: true }];
    if (Array.isArray(bestSeries) && bestSeries.length > 2) {
      lines.push({ label: t("bestOnHeroLine", best.score), values: bestSeries, color: VIZ_2, dashed: true });
    }
    window.LauncherCharts.line(host, {
      series: lines,
      reference: (() => {
        const target = { lh: series.last_hits_target, gold: series.gold_target, xp: series.xp_target }[state.chartMetric];
        return Array.isArray(target) && target.length ? { label: t("target"), values: target } : null;
      })(),
      markers,
      markerLabel: t("deathsMarker"),
      xLabel: (i) => t("minuteLabel", i),
      ariaLabel: label,
      height: 210
    });
  }

  // --- build + rank (match) ---------------------------------------------------------

  function buildCard(analysis) {
    const build = analysis.build;
    if (!build || !(build.items || []).length) {
      return null;
    }
    const rows = build.items.map((item, index) => {
      const timing = item.timing;
      return h(
        "div",
        { class: "build-item" },
        h(
          "div",
          { class: "build-item-head" },
          h("span", { class: "build-item-name with-pic" }, itemPic(item.key || item.name, "md"), h("span", { text: item.name })),
          h("span", { class: "muted num", text: t("buildBy", clock(item.t)) })
        ),
        timing
          ? h(
              "div",
              {},
              h("p", { class: "small build-item-line", text: timingLine(timing) }),
              h("div", { class: "chart-host chart-mini", dataset: { chart: "timing", index: String(index) } })
            )
          : null
      );
    });
    const popular = build.popular || {};
    const phases = ["mid", "late", "early"].filter((phase) => (popular[phase] || []).length);
    const popularBlock = phases.length
      ? h(
          "div",
          { class: "build-popular" },
          h("p", { class: "section-name", text: t("buildPopular") }),
          phases.map((phase) =>
            h(
              "div",
              { class: "build-phase" },
              h("span", { class: "muted small build-phase-label", text: t(`buildPhase.${phase}`) }),
              h(
                "div",
                { class: "chips" },
                popular[phase].map((row) =>
                  h(
                    "span",
                    { class: `chip ${row.bought ? "chip-on" : ""}`, title: row.bought ? t("buildBought") : "" },
                    itemPic(row.key || row.name, "sm"),
                    h("span", { text: row.name }),
                    row.bought ? icon("circle-check") : null
                  )
                )
              )
            )
          )
        )
      : null;
    return card(
      t("buildTitle"),
      "coins",
      h(
        "div",
        { class: "build" },
        build.has_timings ? h("p", { class: "muted small", text: t("buildTimingNote") }) : h("p", { class: "muted small", text: t("buildNoTimings") }),
        rows,
        popularBlock
      )
    );
  }

  // The first skill maxed against the pro order on the hero (backend skill_build.py).
  // «Линия»: the lane minute by minute against its enemy core (lane_duel.py,
  // parsed replays only).
  function laneCard(analysis) {
    const lane = analysis.lane;
    if (!lane || !(lane.points || []).length) {
      return null;
    }
    const signed = (value) => (value === null || value === undefined ? "—" : value > 0 ? `+${value}` : `${value}`);
    const tone = (value) => (value === null || value === undefined || value === 0 ? "" : value > 0 ? "good" : "bad");
    const pair = (mine, theirs) => (mine === null || mine === undefined ? "—" : `${mine} : ${theirs ?? "—"}`);
    const rows = lane.points.map((point) =>
      h(
        "tr",
        {},
        h("td", { class: "num", text: t("laneMinute", point.minute) }),
        h("td", { class: "num-col num", text: pair(point.lh, point.enemy_lh) }),
        h("td", { class: "num-col num", text: pair(point.dn, point.enemy_dn) }),
        h("td", { class: "num-col num", "data-state": tone(point.gold_diff), text: signed(point.gold_diff) }),
        h("td", { class: "num-col num", "data-state": tone(point.xp_diff), text: signed(point.xp_diff) })
      )
    );
    const others = (lane.enemies || []).filter((hero) => hero !== lane.enemy);
    return card(
      t("laneTitle"),
      "swords",
      h(
        "div",
        { class: "lane-duel" },
        h(
          "div",
          { class: "lane-head" },
          heroLabel(lane.hero_id, lane.hero),
          h("span", { class: "muted", text: t("laneVs") }),
          heroLabel(lane.enemy_id, lane.enemy),
          h("span", { class: `lane-result lane-${lane.result}`, text: t(`laneResult.${lane.result}`) })
        ),
        h(
          "div",
          { class: "table-wrap table-wrap-tight" },
          h(
            "table",
            { class: "table lane-table" },
            h(
              "thead",
              {},
              h(
                "tr",
                {},
                h("th", { text: t("laneColMinute") }),
                h("th", { class: "num-col", text: t("laneColLh") }),
                h("th", { class: "num-col", text: t("laneColDn") }),
                h("th", { class: "num-col", text: t("laneColGold") }),
                h("th", { class: "num-col", text: t("laneColXp") })
              )
            ),
            h("tbody", {}, rows)
          )
        ),
        h("p", { class: "muted small", text: [lane.turn ? t("laneTurn", lane.turn) : null, others.length ? t("laneOthers", others.join(", "), signed(lane.total_diff)) : null, t("laneNote")].filter(Boolean).join(" ") })
      )
    );
  }

  function skillsCard(analysis) {
    const skills = analysis.skills;
    if (!skills || !(skills.order || []).length) {
      return null;
    }
    return card(
      t("skillsTitle"),
      "list-checks",
      h(
        "div",
        { class: "skills" },
        h("p", { text: skills.same ? t("skillsSame", skills.yours) : t("skillsDiff", skills.yours, skills.pro) }),
        h("p", { class: "section-name", text: t("skillsPro") }),
        h(
          "div",
          { class: "chips" },
          skills.order.map((name, index) =>
            h("span", { class: `chip ${name === skills.yours ? "chip-on" : ""}` }, h("span", { class: "num", text: `${index + 1}` }), h("span", { text: name }))
          )
        ),
        // The player's first skill when the pros rarely max it: shown apart, marked.
        skills.in_order === false || !skills.order.includes(skills.yours)
          ? h("div", { class: "chips" }, h("span", { class: "muted small", text: t("skillsYours") }), h("span", { class: "chip chip-on" }, h("span", { text: skills.yours })))
          : null,
        h("p", { class: "muted small", text: t("skillsNote", skills.agree, skills.games) })
      )
    );
  }

  function timingLine(timing) {
    if (timing.bucket === timing.typical_bucket) {
      return t("buildItemTypical", timing.winrate, clock(timing.bucket));
    }
    return t("buildItemLine", timing.winrate, clock(timing.bucket), clock(timing.typical_bucket), timing.typical_winrate);
  }

  function drawTimingChart(host, analysis) {
    const item = (analysis.build?.items || [])[Number(host.dataset.index)];
    const timing = item && item.timing;
    if (!timing) {
      return;
    }
    window.LauncherCharts.columns(host, {
      items: timing.buckets.map((bucket) => ({
        label: clock(bucket.time),
        value: bucket.winrate,
        title: t("buildTimingTip", clock(bucket.time)),
        detail: `${number(bucket.games)} ${state.locale === "ru" ? "игр" : "games"}`,
        muted: bucket.time !== timing.bucket
      })),
      // 0-based columns, but no taller than needed so a 10-point gap is visible.
      yMax: Math.min(100, Math.ceil((Math.max(...timing.buckets.map((b) => b.winrate)) + 10) / 20) * 20),
      valueLabels: true,
      valueSuffix: "%",
      color: VIZ_1,
      valueLabel: t("winrateLabel"),
      ariaLabel: `${item.name}: ${t("winrateLabel")}`,
      height: 130,
      xLabels: true
    });
  }

  const RANK_METRICS = ["gpm", "lh_10", "deaths", "kda", "damage_per_min", "net_worth"];
  const LOWER_BETTER = new Set(["deaths"]);

  function formatMetric(key, value) {
    if (value === null || value === undefined) {
      return "—";
    }
    if (key === "kda" || key === "lh_per_min") {
      return decimal(value);
    }
    if (key === "deaths") {
      return Number.isInteger(value) ? number(value) : decimal(value);
    }
    return number(value);
  }

  function diffCell(key, you, other, betterOverride) {
    if (you === null || you === undefined || other === null || other === undefined) {
      return h("td", { class: "num-col num muted", text: "—" });
    }
    const diff = you - other;
    const threshold = Math.max(0.01, Math.abs(other) * 0.03);
    const better = betterOverride !== undefined ? betterOverride : Math.abs(diff) <= threshold ? null : LOWER_BETTER.has(key) ? diff < 0 : diff > 0;
    const tone = better === true ? "good" : better === false ? "bad" : "idle";
    const sign = diff > 0 ? "+" : diff < 0 ? "−" : "";
    return h("td", { class: `num-col num delta-${tone}`, text: `${sign}${formatMetric(key, Math.abs(diff))}` });
  }

  function percent1(value) {
    return `${decimal(value)}%`;
  }

  function signedPercent(value) {
    return `${value > 0 ? "+" : value < 0 ? "−" : ""}${percent1(Math.abs(value))}`;
  }

  function winrateTone(winrate) {
    return winrate >= 52 ? "good" : winrate <= 48 ? "bad" : "idle";
  }

  function selfValue(key, value, item) {
    if (key === "first_item_t") {
      return item ? `${item} · ${clock(value)}` : clock(value);
    }
    if (key === "kill_participation") {
      return `${Math.round(value)}%`;
    }
    if (key === "deaths" || key === "lane_deaths") {
      return percent1(value).replace("%", "").replace(/[.,]0$/, "");
    }
    return number(value);
  }

  // --- compare with a friend (backend friend_compare.py) ---------------------------

  const friendState = { group: "all", data: null, error: "", timer: null, host: null };

  function friendCard() {
    const host = h("section", { class: "card friend-card", dataset: { card: "friend" } });
    friendState.host = host;
    if (friendState.data) {
      renderFriend();
    } else {
      host.replaceChildren(...friendShell(skeletonRows(3)));
    }
    loadFriend();
    return host;
  }

  // The card's header and body (the same markup as card()), for host.replaceChildren.
  function friendShell(body, extraHead) {
    return [
      h("header", { class: "card-head" }, icon("users"), h("h2", { text: t("friendTitle") }), extraHead ? h("span", { class: "card-head-extra" }, extraHead) : null),
      h("div", { class: "card-body" }, body)
    ];
  }

  async function loadFriend(op = "friend", args = {}) {
    clearTimeout(friendState.timer);
    const result = await call(op, { group: friendState.group, ...args });
    if (!friendState.host || !friendState.host.isConnected) {
      return;
    }
    if (result.ok) {
      friendState.data = result.data;
      friendState.error = result.data.state === "self" ? t("friendSelf") : "";
    } else {
      friendState.error = tOptional(`linkErrors.${result.code}`) || result.detail || t("friendFailed");
    }
    renderFriend();
    const data = friendState.data;
    if (data && (data.state === "loading" || data.refreshing) && state.view === "progress") {
      friendState.timer = setTimeout(() => loadFriend(), 3000);
    }
  }

  function friendForm(value = "") {
    const input = h("input", { class: "input", type: "text", value, placeholder: t("friendPlaceholder"), "aria-label": t("friendPlaceholder"), autocomplete: "off", spellcheck: "false" });
    const button = h("button", { class: "btn btn-primary", type: "submit" }, icon("users"), h("span", { text: t("friendCompare") }));
    return h(
      "div",
      {},
      h("p", { class: "muted small", text: t("friendHint") }),
      h(
        "form",
        {
          class: "link-form friend-form no-print",
          onsubmit: async (event) => {
            event.preventDefault();
            button.disabled = true;
            await loadFriend("friendSet", { steam: input.value });
          }
        },
        input,
        button
      ),
      friendState.error ? h("p", { class: "form-error", role: "alert", text: friendState.error }) : null
    );
  }

  function friendActions(data) {
    const busy = data.refreshing || data.state === "loading";
    return h(
      "span",
      { class: "toolbar-actions no-print" },
      // Icon buttons with their names as tooltips: two worded buttons squeezed
      // the card's title («Сравнение с другом») onto two lines.
      data.state !== "loading"
        ? h("button", {
            class: "btn btn-ghost btn-sm btn-icon",
            type: "button",
            disabled: busy,
            title: busy ? t("friendUpdating") : t("friendRefresh"),
            "aria-label": busy ? t("friendUpdating") : t("friendRefresh"),
            onclick: () => loadFriend("friendRefresh")
          }, icon("refresh-cw"))
        : null,
      h("button", {
        class: "btn btn-ghost btn-sm btn-icon",
        type: "button",
        title: t("friendChange"),
        "aria-label": t("friendChange"),
        onclick: () => loadFriend("friendRemove").then(() => loadFriend())
      }, icon("x"))
    );
  }

  function friendValue(key, value) {
    if (value === null || value === undefined) {
      return "—";
    }
    if (key === "win_rate") {
      return `${value}%`;
    }
    return ["kills", "deaths", "assists", "lh_per_min"].includes(key) ? decimal(value) : number(value);
  }

  function renderFriend() {
    const host = friendState.host;
    const data = friendState.data;
    if (!host) {
      return;
    }
    if (!data || data.state === "none" || data.state === "self" || data.state === "unlinked") {
      host.replaceChildren(...friendShell(friendForm()));
      hydrate(host);
      return;
    }
    const friend = data.friend || {};
    const who = friend.name || String(friend.account_id || "");
    if (data.state !== "ready") {
      const text = {
        loading: t("friendLoading", who),
        private: t("friendPrivate", who),
        offline: t("friendOffline"),
        error: t("friendError", data.code || "")
      }[data.state] || "";
      host.replaceChildren(
        ...friendShell(
          h("div", {}, data.state === "loading" ? skeletonRows(3) : null, h("p", { class: "muted", text }), data.state === "private" ? h("p", { class: "muted small", text: t("friendPrivateHint") }) : null),
          friendActions(data)
        )
      );
      hydrate(host);
      return;
    }
    const groups = h(
      "div",
      { class: "segmented segmented-sm no-print", role: "radiogroup", "aria-label": t("friendGroup") },
      ["all", "core", "support"].map((group) =>
        h("button", {
          type: "button",
          role: "radio",
          "aria-checked": String(data.group === group),
          disabled: group !== "all" && !(data.groups?.[group]?.me && data.groups?.[group]?.friend),
          text: t(`friendGroups.${group}`),
          onclick: () => {
            friendState.group = group;
            loadFriend();
          }
        })
      )
    );
    const cell = (row, side) =>
      h("td", { class: `num-col num${row.better === side ? " friend-better" : ""}`, text: friendValue(row.key, row[side]) });
    const table = h(
      "div",
      { class: "table-wrap table-wrap-tight" },
      h(
        "table",
        { class: "table" },
        h("thead", {}, h("tr", {}, h("th", { text: t("colMetric") }), h("th", { class: "num-col", text: t("friendYou") }), h("th", { class: "num-col", text: who }))),
        h("tbody", {}, data.rows.map((row) => h("tr", {}, h("td", { text: t(`friendMetrics.${row.key}`) }), cell(row, "me"), cell(row, "friend"))))
      )
    );
    const heroLine = (hero) =>
      h(
        "li",
        { class: "friend-hero" },
        heroLabel(hero.hero_id, hero.hero),
        h("span", { class: "muted num", text: t("friendHeroGames", hero.me.games, hero.me.win_rate, hero.friend.games, hero.friend.win_rate) })
      );
    const theirHeroes = (data.friend_heroes || []).map((hero) => h("span", { class: "chip with-pic" }, heroLabel(hero.hero_id, hero.hero), h("span", { class: "num muted", text: ` · ${hero.games}` })));
    host.replaceChildren(
      ...friendShell(
        h(
          "div",
          { class: "friend" },
          h(
            "div",
            { class: "friend-head" },
            h("div", {}, h("p", { class: "friend-name", text: who }), h("p", { class: "muted small", text: [friend.rank, t("friendGames", data.games.me, data.games.friend)].filter(Boolean).join(" · ") })),
            groups
          ),
          data.enough ? null : h("p", { class: "muted small", text: t("friendFew", data.min_games) }),
          table,
          data.common_heroes?.length ? h("div", {}, h("p", { class: "friend-sub", text: t("friendCommon") }), h("ul", { class: "friend-heroes" }, data.common_heroes.map(heroLine))) : null,
          theirHeroes.length ? h("div", {}, h("p", { class: "friend-sub", text: t("friendTheirHeroes", who) }), h("div", { class: "chips" }, theirHeroes)) : null,
          h("p", { class: "muted small", text: t("friendNote") })
        ),
        friendActions(data)
      )
    );
    hydrate(host);
  }

  // Every death of the last 20 matches with a map, as if always Radiant
  // (app/career_deaths.py); the map itself is drawn once the card is in the page.
  function deathMapCard(data) {
    if (!data || !(data.deaths || []).length) {
      return null;
    }
    const facts = [h("p", { class: "fact-line" }, h("strong", { text: t("mapDeaths") }), h("span", { class: "num", text: String(data.total) }))];
    for (const side of ["own", "river", "enemy"]) {
      if (data.by_side && data.by_side[side]) {
        facts.push(h("p", { class: "fact-line muted small" }, h("span", { text: t(`mapSide.${side}`) }), h("span", { class: "num", text: String(data.by_side[side]) })));
      }
    }
    const spots = (data.spots || []).filter((spot) => spot.label);
    if (spots.length) {
      facts.push(h("p", { class: "friend-sub", text: t("deathMapSpots") }));
      for (const spot of spots) {
        facts.push(h("p", { class: "fact-line map-spot-line small" }, h("span", { text: t("deathMapSpot", spot.label, spot.count, spot.matches) })));
      }
    }
    if (data.enemy_share_late != null) {
      facts.push(h("p", { class: "muted small", text: t("deathMapLate", data.enemy_share_late) }));
    }
    const body = h(
      "div",
      {},
      h("p", { class: "muted small chart-note", text: `${t("deathMapNote", data.matches, data.total, data.per_match)} ${t("deathMapTurned")}` }),
      h("div", { class: "map-layout" }, h("div", { class: "chart-host", dataset: { chart: "career-map" } }), h("div", { class: "map-facts" }, facts))
    );
    return card(t("deathMapTitle"), "skull", body);
  }

  function drawCareerMap(host, data) {
    window.LauncherCharts.map(host, {
      background: MAP_BACKGROUND,
      bounds: data.bounds,
      spots: (data.spots || []).map((spot) => ({ ...spot, title: t("mapSpotTitle", spot.count, spot.label || "") })),
      deaths: (data.deaths || []).map((death) => ({
        ...death,
        killer: [death.hero, death.killer ? t("killedBy", death.killer) : null].filter(Boolean).join(" · ")
      })),
      labels: t("mapLabels"),
      clock,
      ariaLabel: t("deathMapTitle")
    });
  }

  // The record against enemy heroes met 3+ times (career_analysis.opponents).
  function opponentsCard(record) {
    if (!record || !(record.hard?.length || record.easy?.length)) {
      return null;
    }
    const row = (hero) =>
      h(
        "li",
        { class: "friend-hero" },
        heroLabel(hero.hero_id, hero.hero),
        h("span", { class: "muted num", text: t("opponentRecord", hero.wins, hero.losses, hero.winrate) })
      );
    return card(
      t("opponentsTitle"),
      "swords",
      h(
        "div",
        { class: "friend" },
        h("p", { class: "muted small", text: t("opponentsNote", record.matches, record.min_games) }),
        record.hard?.length ? h("div", {}, h("p", { class: "friend-sub", text: t("opponentsHard") }), h("ul", { class: "friend-heroes" }, record.hard.map(row))) : null,
        record.easy?.length ? h("div", {}, h("p", { class: "friend-sub", text: t("opponentsEasy") }), h("ul", { class: "friend-heroes" }, record.easy.map(row))) : null
      )
    );
  }

  // Heroes to play more and to park (career_analysis.hero_pool), all heroes only.
  // «Ваши линии»: the judged lanes of the last 20 reviewed matches (lane_duel.career_lanes).
  function lanesCard(lanes) {
    if (!lanes || !lanes.games) {
      return null;
    }
    const signed = (value) => (value === null || value === undefined ? "—" : value > 0 ? `+${value}` : `${value}`);
    const dots = (lanes.games_list || []).map((game) =>
      h("button", {
        type: "button",
        class: `lane-dot lane-${game.result}`,
        title: t("lanesDot", game.hero || "—", game.enemy || "—", t(`laneResult.${game.result}`), signed(game.gold_diff)),
        "aria-label": t("lanesDot", game.hero || "—", game.enemy || "—", t(`laneResult.${game.result}`), signed(game.gold_diff)),
        onclick: () => (game.match_id ? openMatch(game.match_id) : null)
      })
    );
    return card(
      t("lanesTitle"),
      "swords",
      h(
        "div",
        { class: "lanes" },
        h("p", { text: t("lanesLine", lanes.won, lanes.even, lanes.lost, lanes.games) }),
        h("div", { class: "lane-dots" }, dots),
        lanes.gold_diff === null ? null : h("p", { class: "muted small", text: t("lanesGold", signed(lanes.gold_diff)) }),
        (lanes.hard || []).length ? h("p", { class: "muted small", text: t("lanesHard", lanes.hard.map((row) => `${row.hero} (${row.lost})`).join(", ")) }) : null
      )
    );
  }

  function heroPoolCard(pool) {
    if (!pool || !(pool.play_more?.length || pool.park?.length)) {
      return null;
    }
    const row = (hero) =>
      h(
        "li",
        { class: "friend-hero" },
        heroLabel(hero.hero_id, hero.hero),
        h("span", { class: "muted num", text: t("poolRecord", hero.wins, hero.matches, hero.winrate, hero.bracket_winrate == null ? null : Math.round(hero.bracket_winrate)) })
      );
    return card(
      t("poolTitle"),
      "users",
      h(
        "div",
        { class: "friend" },
        h("p", { class: "muted small", text: t("poolNote") }),
        pool.play_more?.length ? h("div", {}, h("p", { class: "friend-sub", text: t("poolMore") }), h("ul", { class: "friend-heroes" }, pool.play_more.map(row))) : null,
        pool.park?.length ? h("div", {}, h("p", { class: "friend-sub", text: t("poolPark") }), h("ul", { class: "friend-heroes" }, pool.park.map(row))) : null
      )
    );
  }

  // The rank medal over time (app/rank_history.py): shown once it has changed.
  function rankHistoryCard(history) {
    if (!history || !(history.steps || []).length || history.steps.length < 2) {
      return null;
    }
    const day = (iso) => new Date(`${iso}T12:00:00Z`).toLocaleDateString(state.locale === "ru" ? "ru-RU" : "en-GB");
    const line = history.change >= 0
      ? t("rankUp", history.first, history.current, day(history.since))
      : t("rankDown", history.first, history.current, day(history.since));
    return card(
      t("rankHistoryTitle"),
      "trending-up",
      h(
        "div",
        { class: "draft" },
        h("p", { text: line }),
        h(
          "div",
          { class: "death-summary" },
          history.steps.map((step) => h("span", { class: "chip" }, h("span", { text: step.label || "—" }), h("span", { class: "muted num", text: ` · ${day(step.date)}` })))
        ),
        h("p", { class: "muted small", text: t("rankNote") })
      )
    );
  }

  // The player's own build on the hero (app/hero_build.py).
  function heroBuildCard(build) {
    if (!build || !(build.items || []).length) {
      return null;
    }
    const pct = (value) => (value == null ? "—" : `${value}%`);
    const time = (value) => (value == null ? "—" : clock(value));
    return card(
      t("heroBuildTitle", build.hero),
      "coins",
      h(
        "div",
        { class: "draft" },
        h("p", { class: "muted small", text: t("buildNote", build.matches, build.wins) }),
        build.highlights.length ? coachList(build.highlights, "idle") : null,
        h(
          "div",
          { class: "table-wrap table-wrap-tight" },
          h(
            "table",
            { class: "table table-wrapping" },
            h(
              "thead",
              {},
              h(
                "tr",
                {},
                h("th", { text: t("buildItem") }),
                h("th", { class: "num-col", text: t("buildGames") }),
                h("th", { class: "num-col", text: t("buildWinrate") }),
                h("th", { class: "num-col hide-narrow", text: t("buildWithout") }),
                h("th", { class: "num-col", text: t("buildWinTime") }),
                h("th", { class: "num-col", text: t("buildLossTime") })
              )
            ),
            h(
              "tbody",
              {},
              build.items.map((row) =>
                h(
                  "tr",
                  {},
                  h("td", {}, itemLabel(row.item, row.item)),
                  h("td", { class: "num-col num", text: String(row.games) }),
                  h("td", { class: "num-col num", text: pct(row.winrate) }),
                  h("td", { class: "num-col num muted hide-narrow", text: pct(row.winrate_without) }),
                  h("td", { class: "num-col num", text: time(row.t_win) }),
                  h("td", { class: "num-col num muted", text: time(row.t_loss) })
                )
              )
            )
          )
        ),
        itemTrendBlock(build.timing_trend)
      )
    );
  }

  // The key item's timing game by game (hero_build.timing_trend): drawn by drawItemTrend.
  function itemTrendBlock(trend) {
    if (!trend || !(trend.points || []).length) {
      return null;
    }
    let line;
    if (Number.isFinite(trend.change)) {
      const tone = trend.change < -30 ? "good" : trend.change > 30 ? "bad" : "idle";
      const word = trend.change < -30 ? t("trendSooner", clock(-trend.change)) : trend.change > 30 ? t("trendLater", clock(trend.change)) : t("trendSame");
      line = h(
        "p",
        { class: "small" },
        h("span", { text: t("trendLine", clock(trend.recent), trend.recent_games, clock(trend.before), trend.before_games) }),
        " ",
        h("span", { class: `delta delta-${tone}`, text: word })
      );
    } else {
      line = h("p", { class: "small", text: t("trendRecentOnly", clock(trend.recent), trend.recent_games) });
    }
    return h(
      "div",
      { class: "item-trend" },
      h("p", { class: "friend-sub" }, itemLabel(trend.item, t("trendTitle", trend.item))),
      line,
      h("div", { class: "chart-host", dataset: { chart: "item-trend" } })
    );
  }

  function drawItemTrend(host, trend) {
    window.LauncherCharts.columns(host, {
      items: trend.points.map((point, index) => ({
        label: String(point.match_id ?? index),
        value: Math.round(point.t / 6) / 10,
        title: `${trend.item} · ${clock(point.t)}`,
        detail: point.win ? t("win") : t("loss"),
        key: point.win ? "win" : "loss",
        matchId: point.match_id
      })),
      height: 120,
      color: VIZ_1,
      valueLabel: t("trendMinute"),
      ariaLabel: t("trendTitle", trend.item),
      onSelect: (item) => (item.matchId ? openMatch(item.matchId) : null)
    });
  }

  function selfCompareCard(compare) {
    if (!compare) {
      return null;
    }
    const groupHead = (label, group) => h("th", { class: "num-col" }, h("span", { text: label }), h("span", { class: "self-group muted", text: t("selfGroup", group.count, group.winrate ?? "—") }));
    return card(
      t("selfTitle", compare.hero),
      "trophy",
      h(
        "div",
        { class: "draft" },
        h("p", { class: "muted small", text: t("selfNote", compare.matches) }),
        compare.highlights.length ? coachList(compare.highlights, "idle") : null,
        h(
          "div",
          { class: "table-wrap table-wrap-tight" },
          h(
            "table",
            { class: "table table-wrapping" },
            h("thead", {}, h("tr", {}, h("th", { text: t("colMetric") }), groupHead(t("selfBest"), compare.best), groupHead(t("selfWorst"), compare.worst))),
            h(
              "tbody",
              {},
              compare.rows.map((row) =>
                h(
                  "tr",
                  {},
                  h("td", { text: t(`selfMetrics.${row.key}`) }),
                  h("td", { class: "num-col num", text: selfValue(row.key, row.best, compare.first_items?.best) }),
                  h("td", { class: "num-col num muted", text: selfValue(row.key, row.worst, compare.first_items?.worst) })
                )
              )
            )
          )
        )
      )
    );
  }

  function draftCard(analysis) {
    const draft = analysis.draft;
    if (!draft) {
      return null;
    }
    const parts = [];
    if (draft.has_matchups) {
      parts.push(h("p", { class: "muted small", text: t("draftNote", draft.hero) }));
      parts.push(
        h(
          "div",
          { class: "table-wrap table-wrap-tight" },
          h(
            "table",
            { class: "table" },
            h("thead", {}, h("tr", {}, h("th", { text: t("draftEnemy") }), h("th", { class: "num-col", text: t("draftWinrate") }), h("th", { class: "num-col hide-narrow", text: t("draftGames") }))),
            h(
              "tbody",
              {},
              draft.enemies.map((row) =>
                h(
                  "tr",
                  {},
                  h("td", {}, heroLabel(row.hero_id || row.hero, row.hero)),
                  row.winrate == null
                    ? h("td", { class: "num-col num muted", text: "—" })
                    : h("td", { class: "num-col num" }, h("span", { class: "dot", "data-tone": winrateTone(row.winrate) }), percent1(row.winrate)),
                  h("td", { class: "num-col num muted hide-narrow", text: row.games ? number(row.games) : "" })
                )
              )
            )
          )
        )
      );
    } else {
      parts.push(h("p", { class: "muted", text: t("draftNoData") }));
    }
    if ((draft.pool || []).length > 1) {
      parts.push(
        h(
          "div",
          { class: "draft-block" },
          h("h3", { class: "coach-section-title", text: t("draftPool") }),
          h("p", { class: "muted small", text: t("draftPoolNote") }),
          h(
            "ul",
            { class: "draft-pool" },
            draft.pool.map((row) =>
              h(
                "li",
                { class: row.hero === draft.better_pick ? "is-best" : "" },
                h("span", { class: "draft-pool-hero" }, heroLabel(row.hero_id || row.hero, row.hero), row.picked ? h("span", { class: "tag", text: t("draftPicked") }) : null),
                h("span", { class: "num draft-edge" }, h("span", { class: "dot", "data-tone": row.edge >= 2 ? "good" : row.edge <= -2 ? "bad" : "idle" }), signedPercent(row.edge))
              )
            )
          ),
          draft.better_pick ? h("p", { class: "small", text: t("draftBetter", draft.better_pick) }) : null
        )
      );
    }
    if ((draft.counters || []).length) {
      parts.push(
        h(
          "div",
          { class: "draft-block" },
          h("h3", { class: "coach-section-title", text: t("draftCounters") }),
          h(
            "ul",
            { class: "draft-counters" },
            draft.counters.map((counter) =>
              h(
                "li",
                {},
                h(
                  "p",
                  { class: "draft-counter-head" },
                  h("span", { class: "draft-counter-heroes" }, counter.heroes.map((heroName) => heroLabel(heroName, heroName))),
                  h("span", { class: "tag", text: t(`draftReasons.${counter.reason}`) }),
                  counter.for_role ? null : h("span", { class: "muted small", text: t("draftForSupports") })
                ),
                h(
                  "div",
                  { class: "chips" },
                  counter.items.map((item) => {
                    const bought = counter.bought.includes(item);
                    return h("span", { class: `chip ${bought ? "chip-on" : ""}`, title: bought ? t("draftBought") : "" }, itemPic(item, "sm"), h("span", { text: item }), bought ? icon("circle-check") : null);
                  })
                )
              )
            )
          )
        )
      );
    }
    return card(t("draftTitle"), "shield", h("div", { class: "draft" }, parts));
  }

  function rankCard(analysis) {
    const peers = analysis.peers;
    if (!peers) {
      return null;
    }
    const heroes = (peers.peers || []).map((p) => p.hero).filter(Boolean).slice(0, 2).join(", ");
    const note = h("p", { class: "muted small", text: t("rankMatchNote", peers.lobby_rank_label, peers.role_label || "", heroes) });
    if (!(peers.peers || []).length) {
      return card(t("rankTitle"), "swords", h("div", {}, note, h("p", { class: "muted", text: t("rankNoPeers") })));
    }
    const rows = RANK_METRICS.filter((key) => peers.me[key] !== null && peers.me[key] !== undefined).map((key) =>
      h(
        "tr",
        {},
        h("td", { text: t(`metrics.${key}`) }),
        h("td", { class: "num-col num", text: formatMetric(key, peers.me[key]) }),
        h("td", { class: "num-col num", text: formatMetric(key, peers.avg[key]) }),
        diffCell(key, peers.me[key], peers.avg[key])
      )
    );
    return card(
      t("rankTitle"),
      "swords",
      h(
        "div",
        {},
        note,
        h(
          "div",
          { class: "table-wrap table-wrap-tight" },
          h(
            "table",
            { class: "table" },
            h("thead", {}, h("tr", {}, h("th", { text: t("colMetric") }), h("th", { class: "num-col", text: t("colYou") }), h("th", { class: "num-col", text: t("colOpponent") }), h("th", { class: "num-col", text: t("colDiff") }))),
            h("tbody", {}, rows)
          )
        ),
        explain("explainRank")
      )
    );
  }

  function careerRankCard(career) {
    const rank = career.rank;
    if (!rank || !(rank.metrics || []).length) {
      return card(t("rankCareerTitle"), "swords", h("p", { class: "muted", text: t("rankCareerEmpty") }));
    }
    const rows = rank.metrics.map((row) =>
      h(
        "tr",
        {},
        h("td", { text: t(`metrics.${row.key}`) }),
        h("td", { class: "num-col num", text: formatMetric(row.key, row.you) }),
        h("td", { class: "num-col num", text: formatMetric(row.key, row.peers) }),
        diffCell(row.key, row.you, row.peers, row.better)
      )
    );
    return card(
      t("rankCareerTitle"),
      "swords",
      h(
        "div",
        {},
        h("p", { class: "muted small", text: t("rankCareerNote", rank.rank_label, rank.role_label || "", rank.matches) }),
        h(
          "div",
          { class: "table-wrap table-wrap-tight" },
          h(
            "table",
            { class: "table" },
            h("thead", {}, h("tr", {}, h("th", { text: t("colMetric") }), h("th", { class: "num-col", text: t("colYou") }), h("th", { class: "num-col", text: t("colPeers") }), h("th", { class: "num-col", text: t("colDiff") }))),
            h("tbody", {}, rows)
          )
        )
      )
    );
  }

  // Every death with what is known around it (app/death_review.py).
  function deathsCard(analysis) {
    const block = analysis.death_review;
    const deaths = (block && block.deaths) || [];
    if (!deaths.length) {
      return null;
    }
    const notes = Object.entries(block.notes || {}).filter(([, count]) => count > 0);
    const summary = notes.length
      ? h(
          "div",
          { class: "death-summary" },
          notes.map(([note, count]) => h("span", { class: "chip" }, h("span", { text: t(`deathNote.${note}`) }), h("span", { class: "num", text: ` · ${count}` })))
        )
      : h("p", { class: "muted small", text: t("deathsNoPattern") });
    const rows = deaths.map((death) => {
      const where = [
        death.zone ? t(`deathZone.${death.zone}`) : null,
        death.side ? t(`mapSide.${death.side}`) : null
      ].filter(Boolean).join(" · ");
      const facts = [
        death.killer ? t("killedBy", death.killer) : null,
        where || null,
        Number.isFinite(death.gold) ? t("deathGold", number(death.gold)) : null,
        Number.isFinite(death.after_respawn) ? t("deathAfterRespawn", death.after_respawn) : null
      ].filter(Boolean);
      return h(
        "li",
        { class: "moment death-row" },
        h("span", { class: "moment-time num", text: clock(death.t) }),
        h("span", { class: "moment-icon" }, icon("skull")),
        h(
          "span",
          { class: "death-body" },
          h("span", { text: facts.join(" · ") || t("deathNoFacts") }),
          death.warning
            ? h("span", { class: "muted small death-warning", text: t("deathWarned", clock(death.warning.t), death.warning.action || "") })
            : null,
          deathLast(death)
        ),
        watchButton(analysis, death.t)
      );
    });
    const body = h("div", {}, summary, foldList(h("ol", { class: "moments deaths-list" }, rows), 3));
    return card(t("deathsTitle", deaths.length), "skull", body);
  }

  // «Watch this moment»: copies the Dota console command that jumps the replay
  // to REPLAY_LEAD seconds before it (analysis.replay: the recording's offset
  // between game time and the match clock; live-recorded matches only).
  const REPLAY_LEAD = 10;

  function replayTick(analysis, at) {
    const replay = analysis && analysis.replay;
    if (!replay || !Number.isFinite(replay.clock_offset) || !Number.isFinite(at)) {
      return null;
    }
    return Math.max(0, Math.round((at + replay.clock_offset - REPLAY_LEAD) * (replay.tick_rate || 30)));
  }

  function watchButton(analysis, at) {
    const tick = replayTick(analysis, at);
    if (tick === null || !api.copyReplayTick) {
      return null;
    }
    const label = h("span", { text: t("watchMoment") });
    return h(
      "button",
      {
        type: "button",
        class: "btn btn-ghost btn-sm watch-moment no-print",
        title: t("watchMomentHint"),
        onclick: async (event) => {
          const button = event.currentTarget;
          const result = await api.copyReplayTick(tick);
          label.textContent = result && result.ok ? t("watchCopied") : t("watchFailed");
          button.classList.toggle("is-done", Boolean(result && result.ok));
        }
      },
      icon("play"),
      label
    );
  }

  // The last 20 s before a death (live GSI, app/last_moments.py): an HP line,
  // a burst kill and the saving items that were ready.
  function deathLast(death) {
    const last = death.last;
    if (!last || !Array.isArray(last.hp) || !last.hp.length) {
      return null;
    }
    const W = 160;
    const H = 32;
    const x = (s) => ((20 + Math.max(-20, Math.min(0, s))) / 20) * W;
    const y = (hp) => H - 2 - (Math.max(0, Math.min(100, hp)) / 100) * (H - 4);
    const points = [...last.hp, [0, 0]].map(([s, hp]) => `${x(s).toFixed(1)},${y(hp).toFixed(1)}`).join(" ");
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.setAttribute("class", "death-hp");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", `${t("deathLastTitle")}: ${last.hp.map(([, hp]) => `${hp}%`).join(", ")}`);
    const line = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
    line.setAttribute("points", points);
    svg.append(line);
    // What the line is, in words: a bare falling line meant nothing to a new player.
    const lines = [h("span", { class: "muted small", text: t("deathLastTitle") })];
    if (last.burst_s) {
      lines.push(h("span", { class: "muted small", text: t("deathBurst", last.burst_s) }));
    }
    // Ready while the hero could act (the same second): "not pressed"; ready only
    // while disabled: said as such.
    const unpressed = (death.notes || []).includes("saver_ready");
    const keys = unpressed ? last.usable || [] : last.ready || [];
    const names = (unpressed ? last.usable_names : last.ready_names) || [];
    if (keys.length) {
      lines.push(
        h(
          "span",
          { class: "muted small death-ready" },
          h("span", { text: t(unpressed ? "deathReady" : "deathReadyStunned") }),
          keys.map((key, index) =>
            h(
              "span",
              { class: "death-item" },
              // A bottled rune ("rune:Haste") shows the Bottle's icon.
              window.DotaIcons
                ? window.DotaIcons.itemPicture(document, String(key).startsWith("rune:") ? "item_bottle" : key, "sm", names[index])
                : null,
              h("span", { text: names[index] || key })
            )
          )
        )
      );
    }
    return h("span", { class: "death-last", title: t("deathLastTitle") }, svg, h("span", { class: "death-last-text" }, lines));
  }

  function momentsCard(analysis) {
    // Deaths have their own card when the review has one.
    const moments = (analysis.moments || []).filter(
      (moment) => moment.type !== "death" || !(analysis.death_review && analysis.death_review.deaths || []).length
    );
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
        h("span", { class: "moment-text" }, h("span", { text }), sub ? h("span", { class: "muted", text: ` · ${sub}` }) : null),
        watchButton(analysis, moment.t)
      );
    });
    return card(t("momentsTitle"), "clock", h("ol", { class: "moments" }, items));
  }

  // What the coach said during this match (the app's own recording).
  function adviceLogCard(analysis) {
    const advice = analysis.advice || [];
    if (!advice.length) {
      return null;
    }
    const shown = state.adviceLogOpen ? advice : advice.slice(0, 8);
    const follow = analysis.advice_follow || { ignored: [] };
    const deathAfter = new Map((follow.ignored || []).map((item) => [item.t, item.death_t]));
    const list = h(
      "ol",
      { class: "moments advice-log" },
      shown.map((item) =>
        h(
          "li",
          { class: "moment" },
          h("span", { class: "moment-time num", text: clock(item.t) }),
          h("span", { class: "moment-icon" }, h("span", { class: "dot", "data-tone": item.mode === "urgent" ? "bad" : "warn" })),
          h(
            "span",
            { class: "moment-text" },
            h("span", { text: item.action }),
            item.reason ? h("span", { class: "muted advice-log-reason", text: item.reason }) : null,
            item.why ? h("details", { class: "advice-why" }, h("summary", { text: t("adviceWhy") }), h("p", { text: item.why })) : null,
            deathAfter.has(item.t)
              ? h("span", { class: "advice-log-death" }, icon("skull"), h("span", { text: t("adviceLogDeath", clock(deathAfter.get(item.t))) }))
              : null
          )
        )
      )
    );
    const more = advice.length > shown.length
      ? h(
          "button",
          {
            class: "btn btn-ghost btn-sm no-print",
            type: "button",
            onclick: () => {
              state.adviceLogOpen = true;
              renderMatch();
            }
          },
          h("span", { text: t("adviceLogMore", advice.length) })
        )
      : null;
    const urgent = advice.filter((item) => item.mode === "urgent").length;
    return card(
      t("adviceLogTitle"),
      "lightbulb",
      [h("p", { class: "muted small chart-note", text: t("adviceLogHint", advice.length, urgent) }), list, more].filter(Boolean)
    );
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
                h("td", {}, heroLabel(row.hero_id || row.hero, row.hero || "—"), row.name ? h("span", { class: "muted small player-sub", text: row.name }) : null),
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

  // --- AI coach -------------------------------------------------------------------

  function coachCard(coach, kind) {
    if (!coach || coach.state === "none") {
      return null;
    }
    const title = t(kind === "career" ? "coachCareerTitle" : "coachTitle");
    if (coach.state === "not_enough") {
      return card(title, "graduation-cap", h("p", { class: "muted", text: t("coachNotEnough", coach.need) }));
    }
    if (coach.state === "off" && !coach.review) {
      return aiOffCard(title);
    }
    const body = [];
    const review = coach.review;
    if (review) {
      body.push(kind === "career" ? careerReview(review) : matchReview(review));
    } else if (coach.state === "pending") {
      body.push(h("p", { class: "muted small", text: t(kind === "career" ? "coachCareerPending" : "coachPending") }), skeletonRows(4));
    } else if (coach.state === "waiting") {
      body.push(h("p", { class: "muted", text: t("coachWaiting") }));
    }
    const status = coachStatusLine(coach, kind);
    if (status) {
      body.push(status);
    }
    if (review) {
      body.push(h("p", { class: "coach-footer muted small", text: t("coachFooter", coach.provider_label || "AI", coach.model || "") }));
    }
    const panel = aiPanel(kind);
    if (panel) {
      body.push(panel);
    }
    const settingsButton =
      coach.state !== "off"
        ? h(
            "button",
            {
              class: "btn btn-ghost btn-sm",
              type: "button",
              "aria-expanded": String(Boolean(state.aiPanel)),
              onclick: () => toggleAiPanel(kind, state.aiPanel ? null : "info")
            },
            icon("settings"),
            h("span", { text: t("aiSettings") })
          )
        : null;
    const head = h("span", { class: "coach-head" }, h("span", { class: "tag", text: t("coachTag") }), settingsButton);
    return h("div", { class: "coach-card" }, card(title, "graduation-cap", body, head));
  }

  // "Ask the coach": a free question about this match, answered from its facts.
  // «Спросить тренера» about one match (op "ask") or, with `career`, the recent matches.
  function askCard(detail, career = false) {
    const coach = detail.coach;
    if (!coach || coach.state === "off" || coach.state === "none") {
      return null;
    }
    const history = h("div", { class: "ask-history" });
    const renderHistory = () =>
      history.replaceChildren(
        ...(detail.questions || []).map((qa) =>
          h("div", { class: "ask-item" }, h("p", { class: "ask-q", text: qa.question }), h("p", { class: "ask-a", text: qa.answer }))
        )
      );
    renderHistory();
    const input = h("input", { class: "input ask-input", type: "text", maxlength: "300", placeholder: t(career ? "askCareerPlaceholder" : "askPlaceholder"), "aria-label": t("askTitle") });
    const button = h("button", { class: "btn btn-primary btn-sm", type: "submit" }, icon("send"), h("span", { text: t("askButton") }));
    const note = h("p", { class: "muted small ask-note", role: "status" });
    const pending = h("div", { class: "ask-pending hidden" }, h("p", { class: "muted small", text: t("askThinking") }), skeletonRows(2));
    const chips = h(
      "div",
      { class: "ask-chips" },
      t(career ? "askCareerSuggestions" : "askSuggestions").map((question) =>
        h("button", { class: "chip ask-chip", type: "button", text: question, onclick: () => submit(question) })
      )
    );
    async function submit(question) {
      const text = String(question || "").trim();
      if (!text) {
        note.textContent = t("askErrors.empty_question");
        return;
      }
      input.value = text;
      button.disabled = true;
      input.disabled = true;
      chips.querySelectorAll("button").forEach((chip) => {
        chip.disabled = true;
      });
      note.textContent = "";
      pending.classList.remove("hidden");
      state.askBusy = true;
      const result = career ? await call("askCareer", { question: text }) : await call("ask", { matchId: detail.match_id, question: text });
      state.askBusy = false;
      pending.classList.add("hidden");
      button.disabled = false;
      input.disabled = false;
      chips.querySelectorAll("button").forEach((chip) => {
        chip.disabled = false;
      });
      if (result.ok && result.data && result.data.ok) {
        input.value = "";
        detail.questions = result.data.history || [];
        renderHistory();
        return;
      }
      const code = (result.data && result.data.code) || (/time/i.test(result.detail || "") ? "timeout" : "bad_response");
      note.textContent = tOptional(`askErrors.${code}`) || tOptional(`coachErrors.${code}`) || t("coachErrors.bad_response");
    }
    const form = h(
      "form",
      {
        class: "ask-form no-print",
        onsubmit: (event) => {
          event.preventDefault();
          submit(input.value);
        }
      },
      input,
      button
    );
    return card(t("askTitle"), "message-circle", [
      h("p", { class: "muted small no-print", text: t(career ? "askCareerHint" : "askHint") }),
      form,
      h("div", { class: "no-print" }, chips),
      pending,
      note,
      history
    ]);
  }

  function coachStatusLine(coach, kind) {
    const request = async (event) => {
      event.currentTarget.disabled = true;
      await requestCoach(kind);
    };
    if (coach.state === "pending" && coach.review) {
      return h("p", { class: "coach-status muted small" }, h("span", { class: "skeleton skeleton-dot" }), h("span", { text: t("coachUpdating") }));
    }
    if (coach.state === "waiting") {
      return h("div", { class: "coach-actions" }, h("button", { class: "btn btn-sm", type: "button", onclick: request }, icon("graduation-cap"), h("span", { text: t("coachNow") })));
    }
    if (coach.state === "error") {
      return h(
        "div",
        { class: "coach-status coach-error", role: "status" },
        icon("circle-alert"),
        h("span", { text: tOptional(`coachErrors.${coach.error}`) || t("coachErrors.bad_response") }),
        h("button", { class: "btn btn-sm", type: "button", onclick: request }, icon("refresh-cw"), h("span", { text: t("coachRetry") }))
      );
    }
    if (coach.state === "ready" && coach.review) {
      return h("div", { class: "coach-actions" }, h("button", { class: "btn btn-ghost btn-sm", type: "button", onclick: request }, icon("rotate-cw"), h("span", { text: t("coachRewrite") })));
    }
    return null;
  }

  function matchReview(review) {
    const parts = [h("p", { class: "coach-summary", text: review.summary })];
    if (review.turning_points?.length) {
      parts.push(
        coachSection(
          t("coachTurning"),
          h(
            "ul",
            { class: "coach-moments" },
            review.turning_points.map((point) => h("li", {}, h("span", { class: "coach-time num", text: point.time }), h("span", { text: point.text })))
          )
        )
      );
    }
    if (review.mistakes?.length) {
      parts.push(coachSection(t("coachMistakes"), coachBlocks(review.mistakes, t("coachFix"))));
    }
    if (review.strengths?.length) {
      parts.push(coachSection(t("coachStrengths"), coachList(review.strengths, "good")));
    }
    if (review.next_game?.length) {
      parts.push(coachSection(t("coachNextGame"), coachGoals(review.next_game)));
    }
    return h("div", { class: "coach-review" }, parts);
  }

  function careerReview(review) {
    const parts = [h("p", { class: "coach-summary", text: review.summary })];
    if (review.patterns?.length) {
      parts.push(coachSection(t("coachPatterns"), coachBlocks(review.patterns, t("coachTrain"))));
    }
    if (review.strengths?.length) {
      parts.push(coachSection(t("coachStrengths"), coachList(review.strengths, "good")));
    }
    if (review.plan?.length) {
      parts.push(coachSection(t("coachPlan"), coachGoals(review.plan)));
    }
    return h("div", { class: "coach-review" }, parts);
  }

  function coachSection(title, content) {
    return h("div", { class: "coach-section" }, h("h3", { class: "coach-section-title", text: title }), content);
  }

  function coachBlocks(blocks, fixLabel) {
    return h(
      "ol",
      { class: "findings" },
      blocks.map((block, index) =>
        h(
          "li",
          { class: "finding" },
          h("span", { class: "finding-index num", text: String(index + 1) }),
          h(
            "div",
            { class: "finding-body" },
            h("p", { class: "finding-title", text: block.title }),
            h("p", { class: "finding-text", text: block.detail }),
            block.fix ? h("p", { class: "finding-drill" }, icon("lightbulb"), h("span", {}, h("strong", { text: `${fixLabel}: ` }), block.fix)) : null
          )
        )
      )
    );
  }

  function coachList(lines, tone) {
    return h("ul", { class: "coach-list" }, lines.map((line) => h("li", {}, h("span", { class: "dot", "data-tone": tone }), h("span", { text: line }))));
  }

  function coachGoals(lines) {
    return h("ol", { class: "coach-goals" }, lines.map((line, index) => h("li", {}, h("span", { class: "coach-goal-index num", text: String(index + 1) }), h("span", { text: line }))));
  }

  async function requestCoach(kind) {
    if (kind === "career") {
      await call("coachCareer");
      await loadCareer();
      return;
    }
    const matchId = state.matchId;
    await call("coachMatch", { matchId });
    await openMatchQuietly(matchId);
  }

  // Off: one compact row; the form opens in place.
  function aiOffCard(title) {
    const open = state.aiPanel === "form";
    const row = h(
      "div",
      { class: "ai-off" },
      h("div", { class: "ai-off-text" }, h("p", { class: "ai-off-title", text: t("aiOffTitle") }), h("p", { class: "muted small", text: t("aiOffHint") })),
      open ? null : h("button", { class: "btn btn-primary btn-sm", type: "button", onclick: () => toggleAiPanel(currentKind(), "form") }, h("span", { text: t("aiTurnOn") }))
    );
    return h("div", { class: "coach-card no-print" }, card(title, "graduation-cap", [row, aiPanel(currentKind())].filter(Boolean), h("span", { class: "tag", text: t("coachTag") })));
  }

  function currentKind() {
    return state.view === "progress" ? "career" : state.view === "settings" ? "settings" : "match";
  }

  // Settings → AI coach: the same key form as in the reviews, in one place.
  async function renderAiSettings({ load = false } = {}) {
    const root = document.getElementById("ai-settings-root");
    if (!root) {
      return;
    }
    if (load || !state.ai) {
      const result = await call("aiStatus");
      state.ai = result.ok ? result.data : state.ai;
    }
    const ai = state.ai || {};
    let body;
    if (state.aiPanel && state.view === "settings") {
      body = aiPanel("settings");
    } else if (ai.configured) {
      const note = h("p", { class: "ai-message", role: "status" });
      body = h(
        "div",
        { class: "ai-off" },
        h(
          "div",
          { class: "ai-off-text" },
          h("p", { class: "ai-off-title", text: t("aiOnTitle") }),
          h("p", { class: "muted small", text: t("aiCurrent", ai.provider_label || "", ai.model || "", ai.key_hint || "") }),
          ai.source === "env" ? h("p", { class: "muted small", text: t("aiEnvKey") }) : null,
          note
        ),
        h(
          "div",
          { class: "ai-panel-actions" },
          h(
            "button",
            {
              class: "btn btn-sm",
              type: "button",
              onclick: async (event) => {
                event.currentTarget.disabled = true;
                note.className = "ai-message muted";
                note.textContent = t("aiChecking");
                const check = await call("aiCheck");
                const code = check.ok ? (check.data.ok ? null : check.data.code) : "offline";
                note.className = `ai-message ${code ? "ai-message-bad" : "ai-message-ok"}`;
                note.textContent = code ? tOptional(`coachErrors.${code}`) || code : t("aiCheckOk");
                event.currentTarget.disabled = false;
              }
            },
            h("span", { text: t("aiCheckNow") })
          ),
          h("button", { class: "btn btn-ghost btn-sm", type: "button", onclick: () => toggleAiPanel("settings", "info") }, icon("settings"), h("span", { text: t("aiChangeKey") }))
        )
      );
    } else {
      body = h(
        "div",
        { class: "ai-off" },
        h("div", { class: "ai-off-text" }, h("p", { class: "ai-off-title", text: t("aiOffTitle") }), h("p", { class: "muted small", text: t("aiOffHint") })),
        h("button", { class: "btn btn-primary btn-sm", type: "button", onclick: () => toggleAiPanel("settings", "form") }, h("span", { text: t("aiTurnOn") }))
      );
    }
    root.replaceChildren(card(t("aiSettingsTitle"), "graduation-cap", body));
    hydrate(root);
  }

  async function toggleAiPanel(kind, panel) {
    state.aiPanel = panel;
    state.aiMessage = null;
    if (panel && !state.ai) {
      const result = await call("aiStatus");
      state.ai = result.ok ? result.data : null;
    }
    rerender(kind);
  }

  function rerender(kind) {
    if (kind === "career") {
      renderCareer();
    } else if (kind === "settings") {
      renderAiSettings();
    } else {
      renderMatch();
    }
    const input = document.querySelector(".ai-form input[type='password']");
    if (state.aiPanel === "form" && input && !input.value) {
      input.focus();
    }
  }

  function aiPanel(kind) {
    if (!state.aiPanel) {
      return null;
    }
    const ai = state.ai || {};
    const message = state.aiMessage ? h("p", { class: `ai-message ai-message-${state.aiMessage.tone}`, role: "status", text: state.aiMessage.text }) : null;
    if (state.aiPanel === "info" && ai.configured) {
      return h(
        "div",
        { class: "ai-panel" },
        h("p", { class: "small", text: t("aiCurrent", ai.provider_label || "", ai.model || "", ai.key_hint || "") }),
        ai.source === "env" ? h("p", { class: "muted small", text: t("aiEnvKey") }) : null,
        message,
        h(
          "div",
          { class: "ai-panel-actions" },
          h("button", { class: "btn btn-sm", type: "button", onclick: () => toggleAiPanel(kind, "form") }, h("span", { text: t("aiChangeKey") })),
          ai.source === "app"
            ? h(
                "button",
                {
                  class: "btn btn-ghost btn-sm",
                  type: "button",
                  onclick: async () => {
                    const result = await call("aiClear");
                    state.ai = result.ok ? result.data : state.ai;
                    state.aiPanel = null;
                    await reloadAfterAi(kind);
                  }
                },
                h("span", { text: t("aiDisable") })
              )
            : null
        )
      );
    }
    return aiForm(kind, message);
  }

  function aiForm(kind, message) {
    const providers = state.ai?.providers || [
      { id: "gemini", label: "Gemini" },
      { id: "groq", label: "Groq" },
      { id: "openrouter", label: "OpenRouter" }
    ];
    let provider = state.ai?.provider && providers.some((p) => p.id === state.ai.provider) ? state.ai.provider : providers[0].id;
    const choice = h(
      "div",
      { class: "segmented segmented-sm", role: "radiogroup", "aria-label": t("aiService") },
      providers.map((item) =>
        h("button", {
          type: "button",
          role: "radio",
          "aria-checked": String(item.id === provider),
          text: item.label,
          onclick: (event) => {
            provider = item.id;
            modelInput.placeholder = `${defaultModel(provider)} (${t("aiModelHint")})`;
            for (const button of choice.querySelectorAll("button")) {
              button.setAttribute("aria-checked", String(button === event.currentTarget));
            }
          }
        })
      )
    );
    const input = h("input", { class: "input", type: "password", placeholder: t("aiKeyPlaceholder"), "aria-label": t("aiKey"), autocomplete: "off", spellcheck: "false" });
    const defaultModel = (id) => providers.find((p) => p.id === id)?.model || "";
    const modelInput = h("input", { class: "input", type: "text", placeholder: `${defaultModel(provider)} (${t("aiModelHint")})`, "aria-label": t("aiModel"), autocomplete: "off", spellcheck: "false" });
    const save = h("button", { class: "btn btn-primary btn-sm", type: "submit" }, h("span", { text: t("aiSave") }));
    const status = h("p", { class: "ai-message", role: "status" });
    const form = h(
      "form",
      {
        class: "ai-form",
        onsubmit: async (event) => {
          event.preventDefault();
          if (!input.value.trim()) {
            input.focus();
            return;
          }
          save.disabled = true;
          input.disabled = true;
          modelInput.disabled = true;
          status.className = "ai-message muted";
          status.textContent = t("aiChecking");
          const saved = await call("aiSave", { provider, apiKey: input.value, model: modelInput.value.trim() });
          if (!saved.ok) {
            save.disabled = false;
            input.disabled = false;
            modelInput.disabled = false;
            status.className = "ai-message ai-message-bad";
            status.textContent = saved.detail || t("coachErrors.bad_response");
            return;
          }
          state.ai = saved.data;
          const check = await call("aiCheck");
          const code = check.ok ? (check.data.ok ? null : check.data.code) : "offline";
          if (code === "invalid_key") {
            // A wrong key is not kept.
            const cleared = await call("aiClear");
            state.ai = cleared.ok ? cleared.data : state.ai;
            save.disabled = false;
            input.disabled = false;
            modelInput.disabled = false;
            status.className = "ai-message ai-message-bad";
            status.textContent = t("coachErrors.invalid_key");
            return;
          }
          state.aiPanel = code ? "info" : null;
          state.aiMessage = code ? { tone: "warn", text: t("aiSavedWarn", tOptional(`coachErrors.${code}`) || code) } : null;
          await reloadAfterAi(kind);
        }
      },
      h("div", { class: "ai-form-row" }, h("span", { class: "ai-label", text: t("aiService") }), choice),
      h("div", { class: "ai-form-row" }, input, save),
      h(
        "button",
        { class: "btn btn-ghost btn-sm ai-key-link", type: "button", onclick: () => api.openAiKeyPage?.(provider) },
        icon("external-link"),
        h("span", { text: t("aiGetKey") })
      ),
      // The model id is for people who know which one they want: folded away.
      h("details", { class: "ai-advanced" }, h("summary", { text: t("aiAdvanced") }), h("div", { class: "ai-form-row" }, h("span", { class: "ai-label", text: t("aiModel") }), modelInput)),
      status
    );
    if (message) {
      form.append(message);
    }
    return h(
      "div",
      { class: "ai-panel" },
      h("p", { class: "muted small", text: t("aiSetupHint") }),
      form,
      h("div", { class: "ai-panel-actions" }, h("button", { class: "btn btn-ghost btn-sm", type: "button", onclick: () => toggleAiPanel(kind, null) }, h("span", { text: t("aiCancel") })))
    );
  }

  async function reloadAfterAi(kind) {
    await refreshPlayer();
    if (kind === "settings") {
      await renderAiSettings({ load: true });
    } else if (kind === "career") {
      await loadCareer();
    } else if (state.matchId) {
      await openMatchQuietly(state.matchId);
      renderMatch();
    }
  }

  // --- progress -------------------------------------------------------------------

  // --- profile ----------------------------------------------------------------

  async function loadProfile() {
    const root = document.getElementById("profile-root");
    if (!state.profile) {
      root.replaceChildren(card(t("pfTitle"), "user", skeletonRows(4)));
    }
    if (!state.player) {
      await refreshPlayer();
    }
    if (!state.player?.linked) {
      root.replaceChildren(...linkPage("profile"));
      hydrate(root);
      return;
    }
    const result = await call("profile");
    if (result.ok) {
      state.profile = result.data.profile;
    }
    renderProfile();
    loadFriends();
  }

  // Friends come from the server: drawn when they arrive, the profile does not wait.
  async function loadFriends(request = { op: "status" }) {
    try {
      const result = await api.friends?.(request);
      if (result) {
        state.friends = result;
      }
    } catch {
      state.friends = { ok: false, code: "offline" };
    }
    if (state.view === "profile") {
      const host = document.getElementById("pf-friends");
      if (host) {
        host.replaceWith(friendsCard());
        hydrate(document.getElementById("profile-root"));
      }
    }
  }

  function renderProfile() {
    const root = document.getElementById("profile-root");
    const profile = state.profile;
    if (!root || state.view !== "profile") {
      return;
    }
    if (!profile) {
      root.replaceChildren(pageHead(t("pfTitle"), t("pfSub")), card(t("pfTitle"), "user", emptyState("user", t("pfTitle"), t("pfEmpty"))));
      hydrate(root);
      return;
    }
    root.replaceChildren(
      pageHead(t("pfTitle"), t("pfSub")),
      profileHeader(profile),
      twoColumns([ratingCard(profile.rating)], [statsCard(profile)]),
      zone(t("pfAchievements"), t("pfAchievementsHint"), [achievementsCard(profile.achievements || [])]),
      zone(t("pfFriends"), t("pfFriendsHint"), [friendsCard()]),
      zone(t("pfShop"), t("pfShopHint"), [shopCard(profile)])
    );
    hydrate(root);
    root.querySelectorAll("[data-chart='rating']").forEach((host) => drawRating(host, profile.rating));
  }

  function profileHeader(profile) {
    const player = profile.player || {};
    const level = profile.level || { level: 1, into: 0, need: 300 };
    // No Steam name yet (the account was linked by hand and OpenDota has not
    // answered): a plain «Player» and the person icon, never the app's name.
    const name = player.name || t("pfNoName");
    const initials = player.name ? h("span", { class: "pf-initials", text: name.trim().slice(0, 2).toUpperCase() }) : h("span", { class: "pf-initials" }, h("i", { "data-icon": "user", "data-size": "28", "aria-hidden": "true" }));
    const worn = profile.equipped || {};
    const shopItem = (id) => (profile.shop || []).find((item) => item.id === id);
    const avatar = h("div", { class: "pf-avatar" }, initials);
    if (player.avatar_url && /^https:\/\//.test(player.avatar_url)) {
      const img = h("img", { src: player.avatar_url, alt: "", referrerpolicy: "no-referrer" });
      img.addEventListener("error", () => img.remove());
      avatar.append(img);
    }
    const percent = Math.max(0, Math.min(100, Math.round((100 * level.into) / Math.max(1, level.need))));
    const title = worn.title && worn.title !== "title_none" ? shopItem(worn.title)?.name : null;
    return h(
      "section",
      { class: "card pf-header" },
      h("div", { class: `pf-banner cos-${worn.banner || "banner_plain"}`, "aria-hidden": "true" }),
      h(
        "div",
        { class: "pf-identity" },
        h("div", { class: `pf-avatar-wrap cos-${worn.frame || "frame_plain"}` }, avatar),
        h(
          "div",
          { class: "pf-name-block" },
          h("p", { class: `pf-name cos-${worn.name || "name_plain"}`, text: name }),
          title ? h("p", { class: `pf-title cos-${worn.title}`, text: title }) : null,
          h(
            "p",
            { class: "pf-meta" },
            h("span", { class: "pf-level", text: t("pfLevel", level.level) }),
            player.rank_label ? h("span", { class: "pf-rank", text: player.rank_label }) : null
          ),
          h(
            "div",
            { class: "pf-xp", title: t("pfXp", level.into, level.need) },
            h("div", { class: "pf-xp-bar" }, h("span", { style: `width: ${percent}%` })),
            h("span", { class: "pf-xp-text muted", text: t("pfXp", level.into, level.need) })
          )
        ),
        h(
          "div",
          { class: "pf-sparks", title: t("pfSparksHint") },
          icon("sparkles"),
          h("span", { class: "pf-sparks-value", text: String(profile.sparks?.balance ?? 0) }),
          h("span", { class: "pf-sparks-label", text: t("pfSparks") })
        )
      )
    );
  }

  function statsCard(profile) {
    const stats = profile.stats || {};
    return card(
      t("pfWithApp"),
      "trophy",
      h(
        "div",
        { class: "tiles tiles-compact" },
        tile(t("pfGames"), String(stats.app_games ?? 0)),
        tile(t("pfWinrate"), stats.app_winrate === null || stats.app_winrate === undefined ? "—" : `${stats.app_winrate}%`),
        tile(t("pfHours"), hoursText(stats.app_hours))
      )
    );
  }

  // 0 → «0», 2.5 → «2,5», 37.4 → «37».
  function hoursText(value) {
    const hours = Number(value) || 0;
    if (hours <= 0) {
      return "0";
    }
    return hours >= 10 ? number(Math.round(hours)) : decimal(hours);
  }

  function ratingCard(rating) {
    const form = h(
      "form",
      { class: "pf-mmr-form no-print" },
      h("label", { class: "pf-mmr-label", for: "pf-mmr", text: t("pfMmrLabel") }),
      h("input", { id: "pf-mmr", class: "input", type: "number", min: "0", max: "15000", step: "1", inputmode: "numeric", placeholder: t("pfMmrPlaceholder") }),
      h("button", { class: "btn", type: "submit", text: t("pfMmrSave") }),
      rating && rating.source === "manual" ? h("button", { class: "btn btn-ghost", type: "button", "data-mmr-clear": "1", text: t("pfMmrClear") }) : null,
      h("p", { class: "pf-mmr-error muted", role: "status", "aria-live": "polite" })
    );
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const input = form.querySelector("input");
      const value = Number.parseInt(input.value, 10);
      const error = form.querySelector(".pf-mmr-error");
      if (!Number.isFinite(value) || value < 0 || value > 15000) {
        error.textContent = t("pfMmrBad");
        return;
      }
      const result = await call("profileMmr", { mmr: value });
      if (result.ok) {
        state.profile = result.data.profile;
        renderProfile();
      } else {
        error.textContent = t("pfMmrBad");
      }
    });
    form.querySelector("[data-mmr-clear]")?.addEventListener("click", async () => {
      const result = await call("profileMmrClear");
      if (result.ok) {
        state.profile = result.data.profile;
        renderProfile();
      }
    });
    if (!rating) {
      return card(t("pfRating"), "chart-line", [h("p", { class: "muted", text: t("pfRatingNone") }), form]);
    }
    const change = rating.change_20 || 0;
    const sign = change > 0 ? "+" : "";
    const head = h(
      "div",
      { class: "pf-rating-head" },
      h("div", { class: "pf-rating-now" }, h("span", { class: "pf-rating-label muted", text: t("pfNow") }), h("span", { class: "pf-rating-value", text: `≈ ${rating.current}` })),
      h(
        "div",
        { class: "pf-rating-side" },
        h("span", { class: `pf-rating-change ${change > 0 ? "up" : change < 0 ? "down" : ""}`, text: `${sign}${change}` }),
        h("span", { class: "muted", text: `${t("pfLast20")} · ${t("pfRecord", rating.wins_20, rating.losses_20)}` }),
        h("span", { class: "muted", text: `${t("pfPeak")} ${rating.peak}` })
      )
    );
    const note = rating.source === "medal" ? t("pfRatingMedal") : t("pfRatingManual", rating.step);
    return card(t("pfRating"), "chart-line", [head, h("div", { class: "chart-host pf-rating-chart", "data-chart": "rating" }), h("p", { class: "muted small", text: note }), form]);
  }

  function drawRating(host, rating) {
    if (!rating || !window.LauncherCharts?.rating) {
      return;
    }
    const dateFormat = { day: "numeric", month: "short" };
    const points = rating.points.map((point) => {
      const date = point.t ? new Date(point.t * 1000).toLocaleDateString(state.locale === "ru" ? "ru-RU" : "en-GB", dateFormat) : "";
      const hero = point.hero_id ? window.DotaIcons?.hero(point.hero_id)?.name : null;
      const what = point.anchor ? t("pfAnchor") : point.win ? t("pfWin") : t("pfLoss");
      return { ...point, title: date, detail: [what, hero].filter(Boolean).join(" · ") };
    });
    window.LauncherCharts.rating(host, { points, ariaLabel: t("pfRating") });
  }

  // «Друзья»: the own code (or the button that shows the profile), the add form
  // and the leaderboard of the player and the friends.
  function friendsCard() {
    const data = state.friends;
    const note = h("p", { class: "pf-friends-note muted", role: "status", "aria-live": "polite" });
    const errorText = (code) => tOptional(`pfFriendsErrors.${code}`) || code;
    if (data?.addError) {
      note.textContent = errorText(data.addError);
    } else if (data?.error) {
      note.textContent = errorText(data.error);
    }
    const parts = [];
    if (!data) {
      parts.push(skeletonRows(2));
    } else if (!data.enabled) {
      parts.push(
        h("p", { class: "muted", text: t("pfFriendsOff") }),
        h("button", { class: "btn btn-primary", type: "button", onclick: () => loadFriends({ op: "enable" }) }, icon("users"), h("span", { text: t("pfFriendsShow") }))
      );
    } else {
      const copied = (what) => async () => {
        await api.friends({ op: "copy", what });
        note.textContent = t("pfFriendsCopied");
      };
      parts.push(
        h(
          "div",
          { class: "pf-code-row" },
          h("div", {}, h("p", { class: "muted small", text: t("pfFriendsCode") }), h("p", { class: "pf-code", text: data.code || "—" })),
          h(
            "div",
            { class: "pf-code-actions" },
            h("button", { class: "btn", type: "button", onclick: copied("code") }, icon("copy"), h("span", { text: t("pfFriendsCopy") })),
            data.url ? h("button", { class: "btn btn-ghost", type: "button", onclick: copied("link") }, icon("link"), h("span", { text: t("pfFriendsCopyLink") })) : null,
            data.url ? h("button", { class: "btn btn-ghost", type: "button", onclick: () => api.friends({ op: "open" }) }, icon("external-link"), h("span", { text: t("pfFriendsOpen") })) : null
          )
        ),
        h(
          "label",
          { class: "pf-check" },
          h("input", { type: "checkbox", class: "switch", role: "switch", checked: data.showMmr ? true : null, onchange: (event) => loadFriends({ op: "showMmr", value: event.target.checked }) }),
          h("span", { text: t("pfFriendsShowMmr") })
        )
      );
    }
    const input = h("input", { class: "input", type: "text", maxlength: "20", spellcheck: "false", autocomplete: "off", placeholder: t("pfFriendsAddPlaceholder"), "aria-label": t("pfFriendsAddPlaceholder") });
    const form = h("form", { class: "pf-add-form" }, input, h("button", { class: "btn", type: "submit", text: t("pfFriendsAdd") }));
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      if (input.value.trim()) {
        loadFriends({ op: "add", code: input.value.trim() });
      }
    });
    parts.push(form);
    const rows = data?.rows || [];
    if (data && rows.filter((row) => !row.me).length === 0) {
      parts.push(h("p", { class: "muted", text: t("pfFriendsEmpty") }));
    }
    if (rows.length) {
      parts.push(h("ol", { class: "pf-board" }, rows.map((row) => boardRow(row))));
    }
    if (data?.missing?.length) {
      parts.push(h("p", { class: "muted small", text: t("pfFriendsMissing", data.missing.join(", ")) }));
    }
    parts.push(note);
    if (data?.enabled) {
      parts.push(h("button", { class: "btn btn-ghost btn-sm pf-hide", type: "button", text: t("pfFriendsHide"), onclick: () => loadFriends({ op: "disable" }) }));
    }
    return h("section", { class: "card", id: "pf-friends" }, h("div", { class: "card-body pf-friends" }, parts));
  }

  // A friend's Steam avatar from its image hash (the card keeps nothing else of it).
  function friendAvatar(hash, initials) {
    const avatar = h("div", { class: "pf-avatar" }, h("span", { class: "pf-initials small", text: initials }));
    if (/^[0-9a-f]{40}$/.test(String(hash || ""))) {
      const img = h("img", { src: `https://avatars.steamstatic.com/${hash}_full.jpg`, alt: "", referrerpolicy: "no-referrer" });
      img.addEventListener("error", () => img.remove());
      avatar.append(img);
    }
    return avatar;
  }

  function boardRow(row) {
    const card = row.card || {};
    const worn = card.equipped || {};
    const initials = String(card.name || "?").trim().slice(0, 2).toUpperCase();
    const meta = [t("pfLevel", card.level || 1), card.rank_label, Number.isFinite(card.mmr) ? `≈ ${card.mmr}` : null, t("pfFriendsWeek", card.stats?.week_games || 0)].filter(Boolean).join(" · ");
    return h(
      "li",
      { class: `pf-board-row${row.me ? " me" : ""}` },
      h("span", { class: "pf-place", text: String(row.place) }),
      h("div", { class: `pf-avatar-wrap mini cos-${worn.frame || "frame_plain"}` }, friendAvatar(card.avatar, initials)),
      h(
        "div",
        { class: "pf-board-who" },
        h("p", {}, h("span", { class: `pf-name mini cos-${worn.name || "name_plain"}`, text: card.name || "—" }), row.me ? h("span", { class: "pf-you", text: t("pfFriendsYou") }) : null),
        card.title ? h("p", { class: `pf-title cos-${worn.title || ""}`, text: card.title }) : null,
        h("p", { class: "muted small", text: meta })
      ),
      row.me
        ? null
        : h("button", { class: "btn btn-ghost btn-sm", type: "button", text: t("pfFriendsRemove"), onclick: () => loadFriends({ op: "remove", code: row.id }) })
    );
  }

  // The shop: every look by kind with a preview, its price or condition and
  // one button (buy, wear, or worn).
  function shopCard(profile) {
    const badges = Object.fromEntries((profile.achievements || []).map((badge) => [badge.id, badge.title]));
    const message = h("p", { class: "pf-shop-message muted", role: "status", "aria-live": "polite" });
    const act = async (op, id) => {
      const result = await call(op, { id });
      if (result.ok) {
        state.profile = result.data.profile;
        renderProfile();
      } else {
        message.textContent = tOptional(`pfShopErrors.${result.code}`) || "";
      }
    };
    const groups = ["frame", "banner", "name", "title"].map((kind) => {
      const items = (profile.shop || []).filter((item) => item.kind === kind);
      return h(
        "section",
        { class: "pf-shop-group" },
        h("h3", { class: "pf-shop-kind", text: t(`pfKinds.${kind}`) }),
        h(
          "ul",
          { class: "pf-shop-items" },
          items.map((item) => {
            let condition = null;
            if (!item.owned && item.locked === "level") {
              condition = t("pfNeedLevel", item.level);
            } else if (!item.owned && item.locked === "achievement" && item.achievement) {
              condition = t("pfNeedAchievement", badges[item.achievement.id] || item.achievement.id, item.achievement.tier);
            }
            let button;
            if (item.equipped) {
              button = h("button", { class: "btn btn-sm", type: "button", disabled: true, text: t("pfWorn") });
            } else if (item.owned) {
              button = h("button", { class: "btn btn-sm", type: "button", text: t("pfWear"), onclick: () => act("shopEquip", item.id) });
            } else if (item.locked) {
              // Closed by a level or an achievement: a lock with the price, not a «Buy» that does nothing.
              button = h(
                "button",
                { class: "btn btn-sm pf-shop-closed", type: "button", disabled: true, title: t("pfLockedHint") },
                icon("lock"),
                h("span", { text: item.price ? String(item.price) : t("pfFree") })
              );
            } else if (!item.affordable) {
              // How many sparks are missing, instead of a dimmed «Buy».
              const missing = Math.max(1, (item.price || 0) - (profile.sparks?.balance ?? 0));
              button = h("button", { class: "btn btn-sm pf-shop-closed", type: "button", disabled: true, text: t("pfNeedSparks", missing) });
            } else {
              button = h("button", {
                class: "btn btn-sm btn-primary",
                type: "button",
                text: item.price ? t("pfBuy", item.price) : t("pfFree"),
                onclick: () => act("shopBuy", item.id)
              });
            }
            return h(
              "li",
              { class: `pf-shop-item${item.equipped ? " worn" : ""}${item.locked && !item.owned ? " locked" : ""}` },
              shopPreview(item, profile),
              h("p", { class: "pf-shop-name", text: item.name }),
              condition ? h("p", { class: "pf-shop-condition muted", text: condition }) : null,
              button
            );
          })
        )
      );
    });
    return h("section", { class: "card" }, h("div", { class: "card-body pf-shop" }, groups, message));
  }

  function shopPreview(item, profile) {
    const cls = `cos-${item.id}`;
    if (item.kind === "frame") {
      return h("div", { class: "pf-preview" }, h("div", { class: `pf-avatar-wrap mini ${cls}` }, h("div", { class: "pf-avatar" })));
    }
    if (item.kind === "banner") {
      return h("div", { class: `pf-preview pf-banner mini ${cls}` });
    }
    if (item.kind === "name") {
      return h("div", { class: "pf-preview" }, h("span", { class: `pf-name mini ${cls}`, text: profile.player?.name || t("pfNoName") }));
    }
    return h("div", { class: "pf-preview" }, h("span", { class: `pf-title ${cls}`, text: item.id === "title_none" ? "—" : item.name }));
  }

  function achievementsCard(list) {
    // Alone under the «Награды» zone heading: no second title on the card.
    return h(
      "section",
      { class: "card" },
      h("div", { class: "card-body" }, h(
        "ul",
        { class: "pf-badges" },
        list.map((badge) => {
          const percent = badge.done ? 100 : Math.max(0, Math.min(100, Math.round((100 * badge.value) / Math.max(1, badge.target))));
          return h(
            "li",
            { class: `pf-badge tier-${badge.tier}${badge.done ? " done" : ""}` },
            // No tier yet: an empty medal slot with a dim cup, not a stray dot.
            h("div", { class: "pf-badge-medal", "aria-hidden": "true" }, badge.tier ? h("span", { text: String(badge.tier) }) : icon("trophy")),
            h(
              "div",
              { class: "pf-badge-body" },
              h("p", { class: "pf-badge-title", text: badge.title }),
              h("p", { class: "pf-badge-tier muted", text: badge.tier ? t("pfTier", badge.tier_name, badge.tier, badge.tiers) : t("pfTierNone") }),
              h("p", { class: "pf-badge-text", text: badge.done ? t("pfDone") : badge.text }),
              badge.done
                ? null
                : h(
                    "div",
                    { class: "pf-badge-progress" },
                    h("div", { class: "pf-xp-bar" }, h("span", { style: `width: ${percent}%` })),
                    h("span", { class: "muted", text: t("pfProgress", badge.value, badge.target) }),
                    badge.reward ? h("span", { class: "pf-badge-reward", text: t("pfReward", badge.reward) }) : null
                  )
            )
          );
        })
      )
      )
    );
  }

  async function loadCareer() {
    const root = document.getElementById("progress-root");
    if (!state.career) {
      root.replaceChildren(card(t("tiles.winrate"), "chart-line", skeletonRows(4)));
    }
    if (!state.player) {
      await refreshPlayer();
    }
    if (!state.player?.linked) {
      root.replaceChildren(...linkPage("progress"));
      hydrate(root);
      return;
    }
    const result = await call("career", careerArgs());
    if (result.ok) {
      state.career = result.data;
    }
    renderCareer();
    scheduleCareerRefresh();
  }

  let careerRefreshTimer = null;

  // While the coach writes the career review, ask again every few seconds.
  function scheduleCareerRefresh() {
    clearTimeout(careerRefreshTimer);
    if (state.career?.coach?.state !== "pending" || state.view !== "progress") {
      return;
    }
    careerRefreshTimer = setTimeout(async () => {
      if (state.view !== "progress") {
        return;
      }
      const result = await call("career", careerArgs());
      if (result.ok) {
        const changed = JSON.stringify(result.data) !== JSON.stringify(state.career);
        state.career = result.data;
        if (changed && state.aiPanel !== "form") {
          renderCareer();
        }
      }
      scheduleCareerRefresh();
    }, 4000);
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

  function careerArgs() {
    return state.careerHero === null ? {} : { heroId: state.careerHero };
  }

  // "All heroes" or one hero for the whole Progress page.
  function careerHeroSelect(career) {
    const heroes = career.hero_choices || [];
    if (heroes.length < 2 && state.careerHero === null) {
      return null;
    }
    const select = h(
      "select",
      {
        class: "input select",
        "aria-label": t("filterHero"),
        onchange: async (event) => {
          state.careerHero = event.target.value === "" ? null : Number(event.target.value);
          await loadCareer();
        }
      },
      h("option", { value: "", text: t("filterAllHeroes") }),
      heroes.map((hero) => {
        const option = h("option", { value: String(hero.hero_id), text: `${hero.hero || "—"} · ${hero.games}` });
        option.selected = state.careerHero === hero.hero_id;
        return option;
      })
    );
    return select;
  }

  async function setGoal(findingId, button) {
    if (button) {
      button.disabled = true;
    }
    const result = await call("focusSet", { findingId });
    if (result.ok && state.career) {
      state.career = { ...state.career, focus: result.data };
      renderCareer();
    } else if (button) {
      button.disabled = false;
    }
  }

  async function clearGoal() {
    const result = await call("focusClear");
    if (result.ok && state.career) {
      state.career = { ...state.career, focus: null };
      renderCareer();
    }
  }

  // «Goals» at the top of Progress: the focus (or the most repeated problem to
  // make one) and the streak goals of the status (app/player_goals.py).
  function goalsCard(career) {
    const left = career.focus ? goalBody(career.focus) : noFocusBody(career);
    const goals = ((state.status && state.status.player && state.status.player.goals) || []).filter((goal) => GOAL_TEXT[goal.id]);
    const streaks = goals.length
      ? h(
          "div",
          { class: "streaks" },
          h("p", { class: "friend-sub", text: t("streaksTitle") }),
          goals.map((goal) =>
            h(
              "div",
              { class: "streak", dataset: { met: String(Boolean(goal.met)) } },
              h("p", { class: "streak-head" }, h("span", { text: t(GOAL_TEXT[goal.id], goal.target) }), h("span", { class: "num muted", text: goal.met ? t("streakMet", goal.current) : t("streakProgress", goal.current, goal.target) })),
              h("span", { class: "streak-bar", role: "img", "aria-label": t("streakProgress", goal.current, goal.target) }, h("span", { style: `width: ${Math.min(100, Math.round((100 * goal.current) / goal.target))}%` })),
              h("p", { class: "muted small", text: t("streakBest", goal.best) })
            )
          )
        )
      : null;
    return card(t("goalsTitle"), "target", h("div", { class: "goals-grid" }, left, streaks));
  }

  function noFocusBody(career) {
    // The most repeated problem with a drill: one click makes it the focus.
    const top = (career.recurring || []).find((item) => item.id && item.drill);
    return h(
      "div",
      { class: "goal" },
      h("p", { class: "friend-sub", text: t("goalTitle") }),
      h("p", { class: "muted small", text: t("summaryNoFocus") }),
      top
        ? h(
            "button",
            { type: "button", class: "btn btn-sm goal-make no-print", onclick: (event) => setGoal(top.id, event.currentTarget) },
            icon("target"),
            h("span", { text: t("goalMakeTop", top.title) })
          )
        : null,
      explain("explainFocus")
    );
  }

  // The problem the player chose to work on and how the matches since went.
  function goalBody(focus) {
    const since = focus.since ? new Date(focus.since).toLocaleDateString(state.locale === "ru" ? "ru-RU" : "en-GB", { day: "numeric", month: "long" }) : "";
    const marks = (focus.results || []).map((result) =>
      h("button", {
        class: "goal-mark",
        type: "button",
        dataset: { met: String(result.met) },
        title: `${result.hero || "—"}: ${result.met ? t("goalMet") : t("goalMissed")}`,
        "aria-label": `${result.hero || "—"}: ${result.met ? t("goalMet") : t("goalMissed")}`,
        onclick: () => openMatch(result.match_id)
      })
    );
    const progress = focus.total
      ? [t("goalProgress", focus.met, focus.total), focus.streak >= 2 ? t("goalStreak", focus.streak) : null].filter(Boolean).join(" · ")
      : t("goalWaiting");
    return h(
        "div",
        { class: "goal" },
        h("p", { class: "friend-sub", text: t("goalTitle") }),
        h("p", { class: "finding-title" }, h("span", { text: focus.title }), focus.section_label ? h("span", { class: "tag", text: focus.section_label }) : null),
        focus.drill ? h("p", { class: "finding-drill" }, icon("lightbulb"), h("span", {}, h("strong", { text: `${t("drill")}: ` }), focus.drill)) : null,
        marks.length ? h("div", { class: "goal-marks" }, marks) : null,
        h("p", { class: "muted small num", text: since ? `${progress} · ${t("goalSince", since)}` : progress }),
        h("div", { class: "row no-print" }, h("button", { class: "btn btn-ghost btn-sm", type: "button", onclick: clearGoal }, h("span", { text: t("goalClear") }))),
        explain("explainFocus")
      );
  }

  function renderCareer() {
    const root = document.getElementById("progress-root");
    const career = state.career;
    if (!career || !career.matches) {
      root.replaceChildren(
        pageHead(t("progressTitle"), t("progressSub")),
        h("section", { class: "card" }, h("div", { class: "card-body" }, emptyState("chart-line", t("progressEmptyTitle"), t("progressEmptyHint")), linkPerks("progress", "progressSoon"))),
        (career && coachCard(career.coach, "career")) || ""
      );
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
      tile(t("tiles.kda"), decimal(avg.kda), trendDelta(trend, "kda", (v) => decimal(v))),
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
                    h(
                      "p",
                      { class: "finding-title" },
                      h("span", { text: item.title }),
                      item.section_label ? h("span", { class: "tag", text: item.section_label }) : null,
                      career.focus && career.focus.id === item.id ? h("span", { class: "tag tag-accent", text: t("goalCurrent") }) : null
                    ),
                    h("div", { class: "share" }, window.LauncherCharts.meter(item.share, item.share >= 50 ? "bad" : "ok"), h("span", { class: "muted small", text: item.text })),
                    item.drill ? h("p", { class: "finding-drill" }, icon("lightbulb"), h("span", {}, h("strong", { text: `${t("drill")}: ` }), item.drill)) : null,
                    career.focus && career.focus.id === item.id
                      ? null
                      : h(
                          "button",
                          { class: "btn btn-ghost btn-sm goal-set no-print", type: "button", onclick: (event) => setGoal(item.id, event.currentTarget) },
                          icon("target"),
                          h("span", { text: t("goalSet") })
                        )
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
              // Headers wrap («На вашем / ранге»): seven columns fit the main column without a sideways scroll.
              { class: "table table-wrapping" },
              h("thead", {}, h("tr", {}, h("th", { text: t("colHero") }), h("th", { class: "num-col", text: t("colMatches") }), h("th", { class: "num-col", text: t("colWinrate") }), h("th", { class: "num-col", text: t("colBracket"), title: career.rank_bracket_label ? t("bracketHint", career.rank_bracket_label) : "" }), h("th", { class: "num-col hide-narrow", text: "KDA" }), h("th", { class: "num-col hide-narrow", text: t("colGpm") }), h("th", { class: "num-col", text: t("colScore") }))),
              h(
                "tbody",
                {},
                heroes.map((hero) =>
                  h(
                    "tr",
                    {},
                    h("td", {}, heroLabel(hero.hero_id || hero.hero, hero.hero)),
                    h("td", { class: "num-col num", text: String(hero.matches) }),
                    h("td", { class: "num-col num", text: hero.winrate == null ? "—" : `${hero.winrate}%` }),
                    h("td", { class: "num-col num muted", text: hero.bracket_winrate == null ? "—" : percent1(hero.bracket_winrate) }),
                    h("td", { class: "num-col num hide-narrow", text: decimal(hero.kda) }),
                    h("td", { class: "num-col num hide-narrow", text: number(hero.gpm) }),
                    h("td", { class: "num-col num", text: hero.score == null ? "—" : String(Math.round(hero.score)) })
                  )
                )
              )
            )
          )
        )
      : null;

    const sharePanel = h("section", { class: "card share-panel no-print", hidden: true });
    root.replaceChildren(
      pageHead(t("progressTitle"), t("analyzed", career.analyzed, career.matches), [
        careerHeroSelect(career),
        // Progress over all heroes only: that is what the page shows.
        state.careerHero === null && career.analyzed ? shareButton(sharePanel, career, "progress") : null,
        pdfButton("career")
      ].filter(Boolean)),
      sharePanel,
      zone(t("zoneSummary"), t("zoneSummaryHint"), [tiles]),
      zone(t("zoneGoals"), t("zoneGoalsHint"), [goalsCard(career)]),
      twoColumns(
        [
          zone(t("zoneCoach"), t("zoneCoachHint"), [
            coachCard(career.coach, "career"),
            planCard,
            // Asking needs at least one review (the backend answers not_enough without one).
            state.careerHero === null && career.analyzed ? askCard(career, true) : null
          ]),
          zone(t("zoneGames"), t("zoneGamesHint"), [
            scoreCard,
            deathMapCard(career.death_map),
            lanesCard(career.lanes),
            heroesCard,
            state.careerHero === null ? heroPoolCard(career.hero_pool) : null,
            strengthsCard
          ])
        ].filter(Boolean),
        [
          zone(t("zoneCompare"), t("zoneCompareHint"), [
            careerRankCard(career),
            state.careerHero === null ? rankHistoryCard(career.rank_history) : null,
            opponentsCard(career.opponents),
            state.careerHero === null ? friendCard() : null
          ]),
          zone(t("zoneHero"), t("zoneHeroHint"), [selfCompareCard(career.self_compare), heroBuildCard(career.hero_build)])
        ].filter(Boolean)
      )
    );
    hydrate(root);
    const careerMap = root.querySelector('[data-chart="career-map"]');
    if (careerMap) {
      drawCareerMap(careerMap, career.death_map);
    }
    const itemTrend = root.querySelector('[data-chart="item-trend"]');
    if (itemTrend) {
      drawItemTrend(itemTrend, career.hero_build.timing_trend);
    }
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

  // --- home: the summary (app/home_summary.py) -------------------------------------------

  // Tilt warning and streak goals (app/player_goals.py) inside the summary.
  const GOAL_TEXT = { few_deaths: "streakFewDeaths", good_score: "streakGoodScore" };
  const SUMMARY_REFRESH_MS = 60 * 1000;

  async function refreshSummary(status) {
    const review = status.player && status.player.lastReview;
    const today = status.player && status.player.today;
    const key = [state.locale, review ? `${review.match_id}|${review.at}` : "", status.player && status.player.accountId, today ? today.games : 0].join("|");
    if (state.summaryKey === key && Date.now() - (state.summaryAt || 0) < SUMMARY_REFRESH_MS) {
      return;
    }
    state.summaryKey = key;
    state.summaryAt = Date.now();
    const result = await call("summary");
    renderSummary(result.ok ? result.data.summary : null);
  }

  function todayLine(today) {
    const ru = state.locale === "ru";
    if (!today) {
      return t("summaryNoGames");
    }
    return [
      ru ? `${today.games} ${plural(today.games, "матч", "матча", "матчей")}` : `${today.games} ${today.games === 1 ? "match" : "matches"}`,
      `${today.wins}–${today.losses}`,
      today.avg_score == null ? null : ru ? `средняя оценка ${today.avg_score}` : `average score ${today.avg_score}`,
      // Today's matches judged by the focus (the focus block below spans days).
      today.focus_total ? (ru ? `фокус ${today.focus_met} из ${today.focus_total}` : `focus ${today.focus_met} of ${today.focus_total}`) : null
    ].filter(Boolean).join(" · ");
  }

  function goalChips(goals) {
    return (goals || [])
      .filter((goal) => GOAL_TEXT[goal.id])
      .map((goal) =>
        h(
          "span",
          { class: "chip goal-chip", "data-met": String(Boolean(goal.met)), title: t("streakBest", goal.best) },
          icon(goal.met ? "circle-check" : "target"),
          h("span", { text: t(GOAL_TEXT[goal.id], goal.target) }),
          h("span", { class: "goal-count num", text: goal.met ? t("streakMet", goal.current) : t("streakProgress", goal.current, goal.target) })
        )
      );
  }

  function renderSummary(summary) {
    const cardEl = document.getElementById("summary-card");
    const body = document.getElementById("summary-body");
    if (!cardEl || !body) {
      return;
    }
    cardEl.classList.toggle("hidden", !summary);
    if (!summary) {
      body.replaceChildren();
      return;
    }
    const last = summary.last;
    const result = last.win === true ? "win" : last.win === false ? "loss" : "unknown";
    const facts = [
      last.kills == null ? null : `${last.kills}/${last.deaths}/${last.assists}`,
      last.duration ? clock(last.duration) : null,
      relativeTime(last.start_time)
    ].filter(Boolean).join(" · ");
    const tip = last.tip || last.strength;
    const lastBlock = h(
      "button",
      { type: "button", class: "summary-last", dataset: { result }, onclick: () => openMatch(last.match_id) },
      h(
        "span",
        { class: "summary-last-head" },
        window.DotaIcons ? window.DotaIcons.heroPicture(document, last.hero_id || last.hero, "md") : null,
        h(
          "span",
          { class: "summary-last-text" },
          h("span", { class: "summary-label", text: t("summaryLast") }),
          h("span", { class: "summary-hero" }, h("span", { text: last.hero || "—" }), h("span", { class: `result-tag result-${result}`, text: last.win === true ? t("win") : last.win === false ? t("loss") : "—" })),
          h("span", { class: "muted small num", text: facts })
        ),
        scoreRing(last.score, "md")
      ),
      tip
        ? h(
            "span",
            { class: "summary-tip" },
            h("span", { class: "summary-tip-label", text: last.tip ? t("summaryTip") : t("summaryStrength") }),
            h("span", { class: "summary-tip-title", text: tip.title || "" }),
            last.tip && tip.drill ? h("span", { class: "muted small", text: tip.drill }) : null
          )
        : null,
      h("span", { class: "summary-open" }, h("span", { text: t("summaryOpen") }), icon("chevron-right"))
    );
    const tilt = summary.tilt
      ? h("p", { class: "tilt-line", role: "status", text: summary.tilt.reason === "losses" ? t("tiltLosses", summary.tilt.losses) : t("tiltScore", summary.tilt.scores[0], summary.tilt.scores[1], summary.tilt.usual) })
      : null;
    const chips = goalChips(summary.goals);
    const today = h(
      "div",
      { class: "summary-block" },
      h("p", { class: "summary-label", text: t("summaryToday") }),
      h("p", { class: "summary-value num", text: todayLine(summary.today) }),
      tilt,
      chips.length ? h("div", { class: "goals-line" }, chips) : null
    );
    let focusBlock;
    if (summary.focus) {
      const focus = summary.focus;
      const marks = focus.results.map((row) =>
        h("button", {
          type: "button",
          class: "goal-mark",
          dataset: { met: String(row.met) },
          title: `${row.hero || "—"}: ${row.met ? t("goalMet") : t("goalMissed")}`,
          "aria-label": `${row.hero || "—"}: ${row.met ? t("goalMet") : t("goalMissed")}`,
          onclick: () => openMatch(row.match_id)
        })
      );
      focusBlock = h(
        "div",
        { class: "summary-block" },
        h("p", { class: "summary-label", text: t("summaryFocus") }),
        h("p", { class: "summary-value", text: focus.title || "" }),
        marks.length
          ? h("div", { class: "week-plan-row" }, h("div", { class: "goal-marks" }, marks), h("span", { class: "muted small num", text: t("summaryFocusProgress", focus.met, focus.total) }))
          : h("p", { class: "muted small", text: t("goalWaiting") })
      );
    } else {
      focusBlock = h(
        "div",
        { class: "summary-block" },
        h("p", { class: "summary-label", text: t("summaryFocus") }),
        h("p", { class: "muted small", text: t("summaryNoFocus") }),
        h("button", { type: "button", class: "btn btn-sm", onclick: () => setView("progress") }, h("span", { text: t("summaryPickFocus") }))
      );
    }
    body.replaceChildren(h("div", { class: "summary-grid" }, lastBlock, h("div", { class: "summary-side" }, today, focusBlock)));
    hydrate(body);
  }

  // --- home: the last seven days ---------------------------------------------------

  const WEEK_REFRESH_MS = 60 * 1000;

  async function refreshWeek(status) {
    const review = status.player && status.player.lastReview;
    const key = `${state.locale}|${review ? review.match_id : ""}|${status.player && status.player.accountId}`;
    if (state.weekKey === key && Date.now() - (state.weekAt || 0) < WEEK_REFRESH_MS) {
      return;
    }
    state.weekKey = key;
    state.weekAt = Date.now();
    const result = await call("week");
    renderWeek(result.ok ? result.data.week : null);
  }

  // «Последние матчи» on Home: the newest reviewed games, asked again when a new
  // review is written (the same key as the week) or after a minute.
  const RECENT_MATCHES = 6;

  async function refreshRecent(status) {
    const review = status.player && status.player.lastReview;
    const key = `${review ? review.match_id : ""}|${status.player && status.player.accountId}`;
    if (state.recentKey === key && Date.now() - (state.recentAt || 0) < WEEK_REFRESH_MS) {
      return;
    }
    state.recentKey = key;
    state.recentAt = Date.now();
    const result = await call("matches", { limit: RECENT_MATCHES });
    renderRecent(result.ok ? result.data.items || [] : []);
  }

  function renderRecent(rows) {
    const cardEl = document.getElementById("recent-card");
    const list = document.getElementById("recent-list");
    if (!cardEl || !list) {
      return;
    }
    cardEl.classList.toggle("hidden", !rows.length);
    list.replaceChildren(
      ...rows.map((row) => {
        const kda = row.kills == null ? null : `${row.kills}/${row.deaths}/${row.assists}`;
        const facts = [kda, row.duration ? clock(row.duration) : null, relativeTime(row.start_time)].filter(Boolean).join(" · ");
        const result = row.win === true ? "win" : row.win === false ? "loss" : "unknown";
        return h(
          "li",
          {},
          h(
            "button",
            {
              type: "button",
              class: "recent-item",
              dataset: { result },
              "aria-label": `${row.hero || ""} ${row.win === true ? t("win") : row.win === false ? t("loss") : ""}`,
              onclick: () => openMatch(row.match_id)
            },
            window.DotaIcons ? window.DotaIcons.heroPicture(document, row.hero_id || row.hero, "md") : null,
            h(
              "span",
              { class: "recent-text" },
              h("span", { class: "recent-hero", text: row.hero || "—" }),
              h("span", { class: "recent-facts muted num", text: facts })
            ),
            scoreRing(row.score, "sm")
          )
        );
      })
    );
  }

  // The review score as a small ring (0–100) in the grade's tone; "—" without one.
  function scoreRing(score, size = "md") {
    const known = Number.isFinite(score);
    const tone = !known ? "idle" : score >= 65 ? "good" : score >= 50 ? "warn" : "bad";
    const radius = 15.5;
    const length = 2 * Math.PI * radius;
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 36 36");
    svg.setAttribute("aria-hidden", "true");
    const arcs = [["ring-track", null]];
    if (known && score > 0) {
      arcs.push(["ring-value", (Math.min(100, score) / 100) * length]);
    }
    for (const [cls, dash] of arcs) {
      const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      circle.setAttribute("cx", "18");
      circle.setAttribute("cy", "18");
      circle.setAttribute("r", String(radius));
      circle.setAttribute("class", cls);
      if (dash !== null) {
        circle.setAttribute("stroke-dasharray", `${dash} ${length}`);
      }
      svg.append(circle);
    }
    return h(
      "span",
      { class: `score-ring score-ring-${size}`, dataset: { tone }, title: known ? `${t("scoreLabel")}: ${score}` : "" },
      svg,
      h("span", { class: "score-ring-value num", text: known ? String(Math.round(score)) : "—" })
    );
  }

  // --- home: «Итог вечера» (app/session_summary.py) --------------------------------

  async function refreshSession(status) {
    // Only once Dota is closed: during the evening the card would be about half of it.
    if (status.dotaRunning) {
      renderSession(null, status);
      return;
    }
    const review = status.player && status.player.lastReview;
    const key = `${state.locale}|${review ? review.match_id : ""}|${status.player && status.player.accountId}`;
    if (state.sessionKey === key && Date.now() - (state.sessionAt || 0) < WEEK_REFRESH_MS) {
      renderSession(state.session, status);
      return;
    }
    state.sessionKey = key;
    state.sessionAt = Date.now();
    const result = await call("session");
    state.session = result.ok ? result.data.session : null;
    renderSession(state.session, status);
  }

  function renderSession(session, status) {
    const cardEl = document.getElementById("session-card");
    const body = document.getElementById("session-body");
    if (!cardEl || !body) {
      return;
    }
    const show = Boolean(session && session.id !== (status && status.sessionSeen));
    cardEl.classList.toggle("hidden", !show);
    if (!show) {
      return;
    }
    if (body.dataset.sessionId === `${state.locale}|${session.id}|${session.avg_score}`) {
      return; // drawn already: keep the copy button's state
    }
    body.dataset.sessionId = `${state.locale}|${session.id}|${session.avg_score}`;
    document.getElementById("session-dismiss").onclick = async () => {
      const result = await window.launcherApi.session({ dismiss: session.id });
      cardEl.classList.add("hidden");
      if (result && result.status) {
        state.status = { ...state.status, sessionSeen: session.id };
      }
    };
    let change = null;
    if (Number.isFinite(session.score_change)) {
      const tone = session.score_change > 0 ? "good" : session.score_change < 0 ? "bad" : "idle";
      const iconName = session.score_change > 0 ? "trending-up" : session.score_change < 0 ? "trending-down" : "minus";
      change = h("span", { class: `delta delta-${tone}` }, icon(iconName), h("span", { class: "num", text: `${session.score_change > 0 ? "+" : ""}${session.score_change}` }), h("span", { class: "muted", text: ` ${t("sessionVsUsual")}` }));
    }
    const tiles = [
      tile(t("sessionGames"), String(session.games), null, t("weekRecord", session.wins, session.losses)),
      tile(
        t("sessionScore"),
        session.avg_score == null ? "—" : String(session.avg_score),
        change,
        session.avg_score == null ? t("sessionNoScore") : change ? null : session.usual_score != null ? t("sessionUsual", session.usual_score) : null
      )
    ];
    if (session.best) {
      tiles.push(
        h(
          "button",
          { type: "button", class: "tile tile-link", onclick: () => openMatch(session.best.match_id) },
          h("p", { class: "tile-label", text: t("weekBest") }),
          h("p", { class: "tile-value with-pic" }, window.DotaIcons?.hero(session.best.hero) ? window.DotaIcons.heroPicture(document, session.best.hero, "sm") : null, h("span", { class: "num", text: String(session.best.score) })),
          h("p", { class: "tile-sub muted", text: session.best.hero || "" })
        )
      );
    }
    const facts = [t("sessionTime", session.minutes), session.avg_deaths != null ? t("sessionDeaths", session.avg_deaths) : null].filter(Boolean).join(" · ");
    const lines = [h("p", { class: "week-line muted num", text: facts })];
    const heroes = (session.heroes || []).filter((hero) => hero && hero.hero);
    if (heroes.length) {
      lines.push(
        h(
          "p",
          { class: "week-line week-heroes" },
          h("span", { class: "muted", text: `${t("weekHeroes")} ` }),
          heroes.map((hero) =>
            h(
              "span",
              { class: "week-hero", title: t("weekHeroTitle", hero.hero, hero.games, hero.wins) },
              window.DotaIcons?.hero(hero.hero) ? window.DotaIcons.heroPicture(document, hero.hero, "sm") : null,
              h("span", { text: hero.hero }),
              h("span", { class: "muted num", text: `${hero.wins}–${hero.games - hero.wins}` })
            )
          )
        )
      );
    }
    if (session.top_problem) {
      lines.push(h("p", { class: "week-line" }, h("span", { class: "muted", text: `${t("sessionProblem")} ` }), h("span", { text: t("sessionProblemText", session.top_problem.title, session.top_problem.count, session.top_problem.of) })));
    }
    if (session.focus) {
      lines.push(h("p", { class: "week-line", text: t("sessionFocus", session.focus.title, session.focus.met, session.focus.total) }));
    }
    const copy = h("button", { type: "button", class: "btn btn-primary btn-sm" }, icon("copy"), h("span", { text: t("sessionCopy") }));
    copy.addEventListener("click", async () => {
      const result = await window.launcherApi.session("copy");
      if (result && result.ok) {
        const label = copy.querySelector("span");
        label.textContent = t("sessionCopied");
        setTimeout(() => {
          label.textContent = t("sessionCopy");
        }, 1600);
      }
    });
    const preview = h(
      "details",
      { class: "session-preview" },
      h("summary", { text: t("sessionPreview") }),
      h("pre", { class: "report-preview-text", tabindex: "0", text: session.text || "" })
    );
    body.replaceChildren(h("div", { class: "tiles week-tiles" }, tiles), ...lines, h("div", { class: "session-actions" }, copy), preview);
    hydrate(body);
  }

  let shownWeek = null;

  function renderWeek(week) {
    shownWeek = week;
    const cardEl = document.getElementById("week-card");
    const body = document.getElementById("week-body");
    if (!cardEl || !body) {
      return;
    }
    cardEl.classList.toggle("hidden", !week);
    if (!week) {
      body.replaceChildren();
      return;
    }
    let change = null;
    if (Number.isFinite(week.score_change)) {
      const tone = week.score_change > 0 ? "good" : week.score_change < 0 ? "bad" : "idle";
      const iconName = week.score_change > 0 ? "trending-up" : week.score_change < 0 ? "trending-down" : "minus";
      change = h("span", { class: `delta delta-${tone}` }, icon(iconName), h("span", { class: "num", text: `${week.score_change > 0 ? "+" : ""}${week.score_change}` }), h("span", { class: "muted", text: ` ${t("weekVsPrevious")}` }));
    }
    // Without a comparison, say which side is missing (weekly_summary
    // score_note) instead of leaving the tile half empty.
    const scoreNote = change ? null : tOptional(`weekScoreNote.${week.score_note}`) || null;
    const tiles = [
      tile(t("weekGames"), String(week.games), null, t("weekRecord", week.wins, week.losses)),
      tile(t("tiles.score"), week.avg_score == null ? "—" : String(week.avg_score), change, scoreNote)
    ];
    if (week.best) {
      const best = h(
        "button",
        { type: "button", class: "tile tile-link", onclick: () => openMatch(week.best.match_id) },
        h("p", { class: "tile-label", text: t("weekBest") }),
        h("p", { class: "tile-value with-pic" }, window.DotaIcons?.hero(week.best.hero) ? window.DotaIcons.heroPicture(document, week.best.hero, "sm") : null, h("span", { class: "num", text: String(week.best.score) })),
        h("p", { class: "tile-sub muted", text: week.best.hero || "" })
      );
      tiles.push(best);
    }
    const lines = [];
    const heroes = (week.heroes || []).filter((hero) => hero && hero.hero);
    if (heroes.length > 1) {
      lines.push(
        h(
          "p",
          { class: "week-line week-heroes" },
          h("span", { class: "muted", text: `${t("weekHeroes")} ` }),
          heroes.map((hero) =>
            h(
              "span",
              { class: "week-hero", title: t("weekHeroTitle", hero.hero, hero.games, hero.wins) },
              window.DotaIcons?.hero(hero.hero) ? window.DotaIcons.heroPicture(document, hero.hero, "sm") : null,
              h("span", { text: hero.hero }),
              h("span", { class: "muted num", text: `${hero.wins}–${hero.games - hero.wins}` })
            )
          )
        )
      );
    }
    if (week.top_problem) {
      lines.push(h("p", { class: "week-line" }, h("span", { class: "muted", text: `${t("weekProblem")} ` }), h("span", { text: t("weekProblemText", week.top_problem.title, week.top_problem.count, week.top_problem.of) })));
    }
    if (week.focus) {
      const plan = week.focus;
      const marks = Array.from({ length: plan.plan }, (_, index) => {
        const result = plan.results[index];
        return h("span", { class: "goal-mark", dataset: { met: result ? String(result.met) : "none" }, title: result ? `${result.hero || "—"}: ${result.met ? t("goalMet") : t("goalMissed")}` : t("weekPlanNext") });
      });
      lines.push(
        h(
          "div",
          { class: "week-plan" },
          h("p", { class: "week-line" }, h("span", { class: "muted", text: `${t("weekFocus")} ` }), h("span", { text: plan.title || "" })),
          h("div", { class: "week-plan-row" }, h("div", { class: "goal-marks" }, marks), h("span", { class: "muted small num", text: t("weekPlanProgress", plan.met, plan.results.length, plan.plan) })),
          plan.drill ? h("p", { class: "muted small", text: plan.drill }) : null
        )
      );
    }
    // Every match of the week as a column (its score, win or loss); a click opens it.
    const scored = (week.matches || []).filter((match) => Number.isFinite(match.score));
    const chartHost = scored.length > 1 ? h("div", { class: "chart-host week-chart" }) : null;
    body.replaceChildren(h("div", { class: "tiles week-tiles" }, tiles), chartHost ? h("p", { class: "week-chart-title muted small", text: t("weekChartTitle") }) : null, chartHost, ...lines);
    hydrate(body);
    if (chartHost) {
      window.LauncherCharts.columns(chartHost, {
        items: scored.map((match) => ({
          label: String(match.match_id),
          value: match.score,
          title: `${match.hero || "—"} · ${match.win === true ? t("win") : match.win === false ? t("loss") : "—"}`,
          detail: relativeTime(match.start_time),
          key: match.win === true ? "win" : match.win === false ? "loss" : null,
          matchId: match.match_id
        })),
        yMax: 100,
        height: 132,
        color: VIZ_1,
        valueLabel: t("scoreLabel"),
        ariaLabel: t("weekChartTitle"),
        onSelect: (item) => openMatch(item.matchId)
      });
    }
  }

  function onStatus(status) {
    const localeChanged = state.locale !== (status.locale === "ru" ? "ru" : "en");
    state.locale = status.locale === "ru" ? "ru" : "en";
    state.status = status;
    if (status.backend === "running" && status.player && status.player.linked) {
      refreshSummary(status).catch(() => {});
      refreshWeek(status).catch(() => {});
      refreshRecent(status).catch(() => {});
      refreshSession(status).catch(() => {});
    } else {
      renderSummary(null);
      renderWeek(null);
      renderRecent([]);
      renderSession(null, status);
    }
    if (localeChanged) {
      // Texts from the backend (reviews, progress) come in the new language only
      // when asked again.
      if (state.view === "matches") {
        renderMatches();
      } else if (state.view === "progress") {
        loadCareer();
      } else if (state.view === "match" && state.matchId) {
        openMatchQuietly(state.matchId).then(() => renderMatch());
      } else if (state.view === "settings") {
        renderAiSettings();
      }
    }
  }

  function init() {
    document.getElementById("zone-all-matches")?.addEventListener("click", () => setView("matches"));
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
    // Keyboard: Ctrl+1…5 opens a tab, Esc leaves a match review for the list,
    // ←/→ in a review open the newer / older match of the list.
    // Never while typing, and never under the first-run tour (it owns Esc).
    document.addEventListener("keydown", (event) => {
      if (event.defaultPrevented || event.altKey || event.metaKey || document.querySelector(".tour")) {
        return;
      }
      if (event.target?.closest?.("input, textarea, select, [contenteditable='true']")) {
        return;
      }
      if (event.ctrlKey && !event.shiftKey && /^[1-5]$/.test(event.key)) {
        const tab = document.querySelectorAll(".tabs [data-view]")[Number(event.key) - 1];
        if (tab) {
          event.preventDefault();
          tab.focus();
          setView(tab.dataset.view);
        }
      } else if (event.key === "Escape" && !event.ctrlKey && state.view === "match") {
        event.preventDefault();
        setView("matches");
      } else if ((event.key === "ArrowLeft" || event.key === "ArrowRight") && !event.ctrlKey && !event.shiftKey && state.view === "match") {
        // ← newer, → older; the tabs and the charts keep their own arrows.
        if (event.target?.closest?.(".tabs")) {
          return;
        }
        const row = neighbourMatch(event.key === "ArrowLeft" ? -1 : 1);
        if (row) {
          event.preventDefault();
          openMatch(row.match_id);
        }
      }
    });
    api.onPlayerEvent?.((event) => {
      if (event.type === "open-match" && event.matchId) {
        openMatch(event.matchId);
      } else if (event.type === "open-home") {
        // The evening summary's tray note: its card is on Home.
        setView("home");
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
    if (["matches", "progress", "profile", "settings"].includes(saved)) {
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
          drawMatchCharts(document.getElementById("match-root"), state.match.analysis);
        } else if (state.view === "progress" && state.career) {
          renderCareer();
        } else if (state.view === "profile" && state.profile) {
          renderProfile();
        } else if (state.view === "home" && shownWeek) {
          renderWeek(shownWeek); // the score chart measures its column
        }
      }, 150);
    });
  }

  window.PlayerViews = { onStatus, openMatch, setView };
  init();
})();
