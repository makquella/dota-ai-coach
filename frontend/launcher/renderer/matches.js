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
      filterResult: "Result",
      filterResults: { all: "All", win: "Wins", loss: "Losses" },
      filterHero: "Hero",
      filterAllHeroes: "All heroes",
      filterSummary: (games, winrate, score) =>
        [`${games} ${games === 1 ? "match" : "matches"}`, winrate == null ? null : `${winrate}% wins`, score == null ? null : `average score ${score}`].filter(Boolean).join(" · "),
      filterEmptyTitle: "No matches for this filter",
      filterEmptyHint: "Pick another hero or result.",
      pdfSave: "Save PDF",
      pdfSaved: (name) => `Saved: ${name}`,
      pdfFailed: "Could not save the PDF",
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
      mapTitle: "Match map",
      mapHint: {
        path: "Where your hero went (every 15 s, recorded by the app) and where you died.",
        replay: "From the parsed replay: where you stood in the lane and where you placed wards.",
        both: "Your path (recorded by the app), laning position, wards from the replay and where you died."
      },
      mapLabels: {
        radiant: "Radiant",
        dire: "Dire",
        death: "Death",
        observer: "Observer ward",
        sentry: "Sentry ward",
        path: "Your path",
        lane: "Laning position"
      },
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
      analyzed: (a, n) => `${a} of ${n} matches reviewed in depth`,
      buildTitle: "Build",
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
      metrics: { gpm: "GPM", xpm: "XPM", lh_10: "LH at 10:00", lh_per_min: "LH per minute", deaths: "Deaths", kda: "KDA", damage_per_min: "Damage per minute", net_worth: "Net worth" },
      rankCareerTitle: "You and players of your rank",
      rankCareerNote: (rank, role, n) => `${rank || "Your rank"} · ${role} · same-role players in your ${n} reviewed matches`,
      rankCareerEmpty: "Appears after a few matches reviewed with OpenDota data.",
      colBracket: "At your rank",
      bracketHint: (rank) => `Hero win rate among all ${rank} players (OpenDota)`,
      selfTitle: (hero) => `Your best vs your worst games on ${hero}`,
      selfNote: (n) => `The best third of your last ${n} reviewed games on the hero against the worst third, by review score.`,
      selfBest: "Best",
      selfWorst: "Worst",
      selfGroup: (count, wr) => `${count} games · ${wr}% wins`,
      selfMetrics: {
        lh_10: "LH at 10:00",
        gpm: "GPM",
        deaths: "Deaths",
        lane_deaths: "Lane deaths",
        kill_participation: "Kill participation",
        first_item_t: "First big item"
      },
      draftTitle: "Draft",
      draftNote: (hero) => `${hero}'s win rate against each enemy hero (OpenDota matchup statistics).`,
      draftNoData: "No matchup statistics yet: they are loaded with the next OpenDota sync.",
      draftEnemy: "Enemy",
      draftWinrate: "Your win rate",
      draftGames: "games",
      draftPool: "Your heroes against this lineup",
      draftPoolNote: "Average win rate edge over 50% against these five heroes.",
      draftPicked: "your pick",
      draftBetter: (hero) => `${hero} fit this lineup best.`,
      draftCounters: "Answers to the enemy heroes",
      draftReasons: { evasion: "evasion", illusions: "illusions", invisibility: "invisibility", healing: "healing" },
      draftForSupports: "support's job",
      draftBought: "bought",
      coachTitle: "Coach's review",
      coachCareerTitle: "Coach's review of your recent games",
      coachTag: "AI",
      coachPending: "The coach is writing the review. It takes up to a minute.",
      coachCareerPending: "The coach is looking through your recent matches. It takes up to a minute.",
      coachWaiting: "The coach will review the match when OpenDota has parsed the replay: then there is more data.",
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
        rate_limited: "The free limit of the AI service is used up for now. Try again in a few minutes.",
        busy: "The AI service is overloaded right now. Try again in a few minutes.",
        invalid_key: "The AI service rejected the key. Check it in the AI settings.",
        timeout: "The AI service took too long to answer.",
        offline: "No connection to the AI service.",
        unverified: "The AI answer mentioned facts that are not in the data, so it was not shown. Try again.",
        bad_response: "The AI service answered with an error.",
        no_key: "No key yet."
      },
      aiSettingsTitle: "AI coach",
      aiOnTitle: "AI coach is on",
      aiCheckNow: "Check key",
      aiCheckOk: "The key works.",
      aiOffTitle: "AI coach is off",
      aiOffHint: "Explains the match in plain words, like a coach watching the replay. Free with a Google Gemini, Groq or OpenRouter key.",
      aiTurnOn: "Turn on",
      aiSetupHint: "Get a free key (takes a minute, no card) and paste it here. The coach only explains: every number still comes from the review. The match data (without your Steam ID) is sent to the chosen service.",
      aiService: "Service",
      aiKey: "API key",
      aiKeyPlaceholder: "Paste the key",
      aiModel: "Model",
      aiModelHint: "optional",
      aiGetKey: "Get a free key",
      aiSave: "Check and save",
      aiChecking: "Checking the key…",
      aiSaved: "The key works. The coach is on.",
      aiSavedWarn: (reason) => `Key saved, but the check failed: ${reason}`,
      aiSettings: "AI settings",
      aiCurrent: (provider, model, hint) => `${provider} · ${model}${hint ? ` · key ${hint}` : ""}`,
      aiEnvKey: "The key comes from the .env file.",
      aiChangeKey: "Change key",
      aiDisable: "Turn off",
      aiCancel: "Cancel"
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
      filterResult: "Результат",
      filterResults: { all: "Все", win: "Победы", loss: "Поражения" },
      filterHero: "Герой",
      filterAllHeroes: "Все герои",
      filterSummary: (games, winrate, score) =>
        [`${games} ${plural(games, "матч", "матча", "матчей")}`, winrate == null ? null : `${winrate}% побед`, score == null ? null : `средняя оценка ${score}`].filter(Boolean).join(" · "),
      filterEmptyTitle: "Нет матчей под этот фильтр",
      filterEmptyHint: "Выберите другого героя или результат.",
      pdfSave: "Сохранить PDF",
      pdfSaved: (name) => `Сохранено: ${name}`,
      pdfFailed: "Не удалось сохранить PDF",
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
      mapTitle: "Карта матча",
      mapHint: {
        path: "Где был ваш герой (каждые 15 с, записало приложение) и где вы умирали.",
        replay: "По разобранному реплею: где вы стояли на линии и где ставили варды.",
        both: "Ваш путь (записало приложение), позиция на линии и варды из реплея, места смертей."
      },
      mapLabels: {
        radiant: "Силы Света",
        dire: "Силы Тьмы",
        death: "Смерть",
        observer: "Обзорный вард",
        sentry: "Сентри",
        path: "Ваш путь",
        lane: "Позиция на линии"
      },
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
      analyzed: (a, n) => `Подробно разобрано ${a} из ${n} матчей`,
      buildTitle: "Сборка",
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
      metrics: { gpm: "GPM", xpm: "XPM", lh_10: "Добивания к 10:00", lh_per_min: "Добиваний в минуту", deaths: "Смерти", kda: "KDA", damage_per_min: "Урон в минуту", net_worth: "Ценность" },
      rankCareerTitle: "Вы и игроки вашего ранга",
      rankCareerNote: (rank, role, n) => `${rank || "Ваш ранг"} · ${role} · игроки той же роли в ваших ${n} разобранных матчах`,
      rankCareerEmpty: "Появится после нескольких матчей, разобранных по данным OpenDota.",
      colBracket: "На вашем ранге",
      bracketHint: (rank) => `Винрейт героя у всех игроков ранга ${rank} (OpenDota)`,
      selfTitle: (hero) => `Лучшие и худшие матчи на ${hero}`,
      selfNote: (n) => `Лучшая треть из ${n} последних разобранных матчей на герое против худшей трети, по оценке разбора.`,
      selfBest: "Лучшие",
      selfWorst: "Худшие",
      selfGroup: (count, wr) => `${count} матча · ${wr}% побед`,
      selfMetrics: {
        lh_10: "Добивания к 10:00",
        gpm: "GPM",
        deaths: "Смерти",
        lane_deaths: "Смерти на линии",
        kill_participation: "Участие в убийствах",
        first_item_t: "Первый большой предмет"
      },
      draftTitle: "Драфт",
      draftNote: (hero) => `Винрейт ${hero} против каждого вражеского героя (статистика матчапов OpenDota).`,
      draftNoData: "Статистики матчапов пока нет: она загрузится при следующей синхронизации с OpenDota.",
      draftEnemy: "Враг",
      draftWinrate: "Ваш винрейт",
      draftGames: "игр",
      draftPool: "Ваши герои против этого состава",
      draftPoolNote: "Средний перевес по винрейту над 50% против этих пяти героев.",
      draftPicked: "ваш пик",
      draftBetter: (hero) => `Лучше всего против этого состава подходил ${hero}.`,
      draftCounters: "Ответы на вражеских героев",
      draftReasons: { evasion: "уклонение", illusions: "иллюзии", invisibility: "невидимость", healing: "лечение" },
      draftForSupports: "задача саппорта",
      draftBought: "куплен",
      coachTitle: "Разбор тренера",
      coachCareerTitle: "Разбор тренера по последним матчам",
      coachTag: "ИИ",
      coachPending: "Тренер пишет разбор. Это занимает до минуты.",
      coachCareerPending: "Тренер смотрит ваши последние матчи. Это занимает до минуты.",
      coachWaiting: "Тренер разберёт матч, когда OpenDota разберёт реплей: тогда данных больше.",
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
        rate_limited: "Бесплатный лимит ИИ-сервиса пока исчерпан. Попробуйте через несколько минут.",
        busy: "ИИ-сервис сейчас перегружен. Попробуйте через несколько минут.",
        invalid_key: "ИИ-сервис не принял ключ. Проверьте его в настройках ИИ.",
        timeout: "ИИ-сервис слишком долго отвечал.",
        offline: "Нет связи с ИИ-сервисом.",
        unverified: "В ответе ИИ были факты, которых нет в данных, поэтому он не показан. Попробуйте ещё раз.",
        bad_response: "ИИ-сервис ответил ошибкой.",
        no_key: "Ключ ещё не указан."
      },
      aiSettingsTitle: "ИИ-тренер",
      aiOnTitle: "ИИ-тренер включён",
      aiCheckNow: "Проверить ключ",
      aiCheckOk: "Ключ работает.",
      aiOffTitle: "ИИ-тренер выключен",
      aiOffHint: "Объясняет матч простыми словами, как тренер, который смотрит реплей. Бесплатно с ключом Google Gemini, Groq или OpenRouter.",
      aiTurnOn: "Включить",
      aiSetupHint: "Получите бесплатный ключ (минута, без карты) и вставьте его сюда. Тренер только объясняет: все числа по-прежнему берутся из разбора. Данные матча (без вашего Steam ID) отправляются в выбранный сервис.",
      aiService: "Сервис",
      aiKey: "API-ключ",
      aiKeyPlaceholder: "Вставьте ключ",
      aiModel: "Модель",
      aiModelHint: "необязательно",
      aiGetKey: "Получить бесплатный ключ",
      aiSave: "Проверить и сохранить",
      aiChecking: "Проверяем ключ…",
      aiSaved: "Ключ работает. Тренер включён.",
      aiSavedWarn: (reason) => `Ключ сохранён, но проверка не прошла: ${reason}`,
      aiSettings: "Настройки ИИ",
      aiCurrent: (provider, model, hint) => `${provider} · ${model}${hint ? ` · ключ ${hint}` : ""}`,
      aiEnvKey: "Ключ берётся из файла .env.",
      aiChangeKey: "Сменить ключ",
      aiDisable: "Отключить",
      aiCancel: "Отмена"
    }
  };

  // Chart colours come from the design tokens (assets/ui/tokens.css).
  const cssVar = (name, fallback) =>
    getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
  const VIZ_1 = cssVar("--viz-1", "#3987e5");
  const TAB_KEY = "dota-ai-coach.tab";
  const api = window.launcherApi;

  const state = {
    filter: { heroId: null, result: "all" },
    careerHero: null,
    heroes: [],
    matchesStats: null,
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
    state.aiPanel = null;
    state.aiMessage = null;
    const tabView = view === "match" ? "matches" : view;
    for (const tab of document.querySelectorAll(".tabs [data-view]")) {
      tab.setAttribute("aria-selected", String(tab.dataset.view === tabView));
    }
    for (const name of ["home", "matches", "match", "progress", "settings"]) {
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
      const result = await call("matches", { limit: Math.max(30, state.matches.length), ...filterArgs() });
      if (result.ok) {
        state.matches = result.data.items || [];
        state.matchesTotal = result.data.total || 0;
        state.matchesStats = result.data.stats || null;
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
      root.replaceChildren(linkPanel());
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
    root.replaceChildren(
      playerBar(),
      liveNotice || "",
      card(t("matchesTitle"), "history", [filters, body].filter(Boolean), state.matchesTotal ? h("span", { class: "num", text: String(state.matchesTotal) }) : null)
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
      // Don't wipe a key the player is typing.
      if (changed && state.aiPanel !== "form") {
        renderMatch();
      }
    }
    scheduleMatchRefresh(matchId);
  }

  // Saves the current view as a PDF (light print theme, see @media print).
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

  function renderMatch() {
    const root = document.getElementById("match-root");
    const backButton = h("button", { class: "btn btn-ghost btn-sm back", type: "button", onclick: () => setView("matches") }, icon("chevron-left"), h("span", { text: t("back") }));
    const detail = state.match;
    const back = h("div", { class: "review-toolbar no-print" }, backButton, detail && detail.analysis ? pdfButton("match") : null);
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
      const coach = coachCard(detail.coach, "match");
      if (coach) {
        parts.push(coach);
      }
      parts.push(focusCard(analysis));
      parts.push(sectionsCard(analysis));
      const build = buildCard(analysis);
      if (build) {
        parts.push(build);
      }
      const rank = rankCard(analysis);
      if (rank) {
        parts.push(rank);
      }
      const draft = draftCard(analysis);
      if (draft) {
        parts.push(draft);
      }
      const chart = chartCard(analysis);
      if (chart) {
        parts.push(chart);
      }
      const gameMap = mapCard(analysis);
      if (gameMap) {
        parts.push(gameMap);
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
    root.querySelectorAll("[data-chart='match']").forEach((host) => drawChart(host, analysis));
    root.querySelectorAll("[data-chart='timing']").forEach((host) => drawTimingChart(host, analysis));
    root.querySelectorAll("[data-chart='map']").forEach((host) => drawMap(host, analysis.map));
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

  // Schematic map: path and deaths from the app's own recording, laning
  // position and wards from the parsed replay (either may be missing).
  function mapCard(analysis) {
    const data = analysis.map;
    if (!data || !((data.deaths || []).length || (data.wards || []).length || (data.path || []).length > 1)) {
      return null;
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

  function drawMap(host, data) {
    window.LauncherCharts.map(host, {
      bounds: data.bounds,
      path: data.path,
      lane: data.lane,
      wards: data.wards,
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
          h("span", { class: "build-item-name", text: item.name }),
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
                    row.bought ? icon("circle-check") : null,
                    h("span", { text: row.name })
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
      return Number(value).toFixed(1);
    }
    if (key === "deaths") {
      return Number(value).toFixed(Number.isInteger(value) ? 0 : 1);
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
    const text = `${Number(value).toFixed(1)}%`;
    return state.locale === "ru" ? text.replace(".", ",") : text;
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
            { class: "table" },
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
                  h("td", { class: "hero-cell", text: row.hero }),
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
                h("span", { class: "draft-pool-hero" }, h("span", { text: row.hero }), row.picked ? h("span", { class: "tag", text: t("draftPicked") }) : null),
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
                  h("span", { text: counter.heroes.join(", ") }),
                  h("span", { class: "tag", text: t(`draftReasons.${counter.reason}`) }),
                  counter.for_role ? null : h("span", { class: "muted small", text: t("draftForSupports") })
                ),
                h(
                  "div",
                  { class: "chips" },
                  counter.items.map((item) => {
                    const bought = counter.bought.includes(item);
                    return h("span", { class: `chip ${bought ? "chip-on" : ""}`, title: bought ? t("draftBought") : "" }, bought ? icon("circle-check") : null, h("span", { text: item }));
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
        )
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
      h("div", { class: "ai-form-row" }, h("span", { class: "ai-label", text: t("aiModel") }), modelInput),
      h("div", { class: "ai-form-row" }, input, save),
      h(
        "button",
        { class: "btn btn-ghost btn-sm ai-key-link", type: "button", onclick: () => api.openAiKeyPage?.(provider) },
        icon("external-link"),
        h("span", { text: t("aiGetKey") })
      ),
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

  function renderCareer() {
    const root = document.getElementById("progress-root");
    const career = state.career;
    if (!career || !career.matches) {
      root.replaceChildren(
        card(t("tiles.winrate"), "chart-line", emptyState("chart-line", t("progressEmptyTitle"), t("progressEmptyHint"))),
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
              h("thead", {}, h("tr", {}, h("th", { text: t("colHero") }), h("th", { class: "num-col", text: t("colMatches") }), h("th", { class: "num-col", text: t("colWinrate") }), h("th", { class: "num-col", text: t("colBracket"), title: career.rank_bracket_label ? t("bracketHint", career.rank_bracket_label) : "" }), h("th", { class: "num-col hide-narrow", text: "KDA" }), h("th", { class: "num-col hide-narrow", text: t("colGpm") }), h("th", { class: "num-col", text: t("colScore") }))),
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
                    h("td", { class: "num-col num muted", text: hero.bracket_winrate == null ? "—" : `${hero.bracket_winrate}%` }),
                    h("td", { class: "num-col num hide-narrow", text: hero.kda == null ? "—" : hero.kda.toFixed(1) }),
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
      h(
        "div",
        { class: "review-toolbar" },
        h("p", { class: "muted small progress-note", text: t("analyzed", career.analyzed, career.matches) }),
        h("span", { class: "toolbar-actions no-print" }, careerHeroSelect(career), pdfButton("career"))
      ),
      tiles,
      coachCard(career.coach, "career") || "",
      scoreCard,
      careerRankCard(career),
      selfCompareCard(career.self_compare) || "",
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
    if (["matches", "progress", "settings"].includes(saved)) {
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
