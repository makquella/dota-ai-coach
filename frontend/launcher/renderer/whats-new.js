// Update history and numeric version selection, shared by the panel and checks.
(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.WardlyWhatsNew = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const TEXT = {
    en: {
      "0.53.31": [
        "AI match reviews and saved answers check last hits and denies against their own totals, with separate data for samples at 10:00 and opponent comparisons."
      ],
      "0.53.30": [
        "Delayed history responses cannot replace a newer filter or sort; repeated More clicks cannot duplicate a page."
      ],
      "0.53.29": [
        "Delayed review responses cannot replace a newer selection or update a review after changing tabs or language."
      ],
      "0.53.28": [
        "Returning from a review keeps the match row focused through the table refresh; back/forward history is checked in both languages."
      ],
      "0.53.27": [
        "The match table preserves partial K/D/A, notes and unknown results when paging, sorting and filtering; these flows are checked in both interface languages."
      ],
      "0.53.26": [
        "AI match reviews and answers check GPM and XPM against their own player metrics and show the data used for verification."
      ],
      "0.53.25": [
        "Player polling preserves idle, queued, running, completed and failed sync states, with zero counts kept distinct from missing data."
      ],
      "0.53.24": [
        "The update history keeps its Russian and English summaries, including versions skipped during an update."
      ],
      "0.53.23": [
        "A delayed demo frame cannot restore the overlay after session reset or replace a newer demo frame."
      ],
      "0.53.22": [
        "Map, skill and shop tips update together; hints prepared before a session reset are discarded."
      ],
      "0.53.21": [
        "Enemy, lane, teleport and objective tracker reads stay consistent during game updates and session resets."
      ],
      "0.53.20": [
        "Roshan and Aegis timer settings load before game-state updates, keeping the first timer event and reset responsive."
      ],
      "0.53.19": [
        "Session reset no longer waits for role-history lookup; game state updates use the prepared role data."
      ],
      "0.53.18": [
        "Match-memory summaries stay consistent while game data, demo replay and resets update the session."
      ],
      "0.53.17": [
        "Match K/D/A keeps known values, including zero, and shows a dash for each missing counter."
      ],
      "0.53.16": [
        "Match-screen translations now have their own module, with the same copy and number formatting checked in both languages."
      ],
      "0.53.15": [
        "GSI packet, state and timestamp now update together. Reset clears the old packet and waits for fresh Dota data."
      ],
      "0.53.14": [
        "Background tasks now have an independent checked executor, preserving delayed retries and safe shutdown."
      ],
      "0.53.13": [
        "The AI checks match kills, deaths and assists against their own counters. Open the review’s data disclosure to see the reported totals."
      ],
      "0.53.12": [
        "Documentation and site checks are faster while app changes retain the required Windows installer validation."
      ],
      "0.53.11": [
        "History transfer now handles simultaneous downloads and code collisions safely. Late cleanup preserves a fresh transfer that reused a code."
      ],
      "0.53.10": [
        "Installer releases now require the same source version to pass the shared checks before publishing."
      ],
      "0.53.9": [
        "Improved automated update checks to detect new code errors earlier."
      ],
      "0.53.8": [
        "Protected the app’s windows: privileged actions only accept their own local interface, and unexpected navigation or popups are blocked."
      ],
      "0.53.7": [
        "Websites can no longer change the coach’s local settings or send game data. Dota uses a separate protected connection; restart Dota once after updating."
      ],
      "0.53.6": [
        "History backups are checked before loading and restored as one operation. A damaged cache no longer interrupts opening a review."
      ],
      "0.53.5": [
        "Repeated background requests are deduplicated while running. Shutdown cancels waiting jobs and gives active jobs limited time to finish."
      ],
      "0.53.4": [
        "Finished matches are kept for retry if saving fails, including after a restart. Recording continues for the next match."
      ],
      "0.53.3": [
        "The packaged coach now uses the same pinned library versions as its automated checks."
      ],
      "0.53.2": [
        "Updated the app engine and dependencies with security fixes."
      ],
      "0.53.1": [
        "Advice keeps working when its diagnostic log cannot be saved. The error is included in a problem report."
      ],
      "0.53.0": [
        "Ctrl+K finds anything: a tab, a match by hero or your note, Progress on a hero, a setting or an action.",
        "Notes show on Home's last matches too."
      ],
      "0.52.0": [
        "Find a setting: a search field on top of Settings (Ctrl+F) keeps only the rows with your words.",
        "Interface size in Settings → App (90–125 %), or Ctrl + plus / minus.",
        "Notes on matches: your own line in the review header, marked in the match table too.",
        "The mouse's back / forward buttons and Alt+←/→ walk the pages you opened; ↑/↓ move through the match table."
      ],
      "0.51.0": [
        "Open any match by its number: paste it, or an OpenDota, Dotabuff or STRATZ link, next to the match filters — older games than your synced history get a full review too.",
        "The review's chart shows your items under the minutes: when each finished item came.",
        "While you wait to respawn, the overlay's card shows the icon of the item to buy."
      ],
      "0.50.0": [
        "Items everywhere: the match table shows what you ended each game with, the review's header too, and the scoreboard shows every player's items.",
        "Home's last matches carry their items as well; hover an item for its name."
      ],
      "0.49.0": [
        "Skill tips show the ability's own icon, and the pros' skill order as icons with the one to level now outlined; the review's skill card has the icons too.",
        "Long pages have section links: the review's top bar and Progress list their parts, jump to one with a click and mark the part you are reading.",
        "Press ? on any tab for the list of hotkeys; the match table remembers how you sorted it."
      ],
      "0.48.0": [
        "Sort your matches: click a column in the table (score, gold, last hits, duration, KDA, date); click again to flip the order.",
        "Profile shows the award you are closest to next, and the deaths list draws the last 20 seconds of HP more clearly.",
        "Small fixes: tables in the side column line up with the card text, «What does this mean?» no longer covers a table row, the review header reads more calmly."
      ],
      "0.47.0": [
        "The in-game card has a coloured stripe on its left: red urgent, yellow a tip, green a calm note, cream the map and the plan.",
        "While Dota runs, Home shows the current match first.",
        "Calmer details: achievement progress and sparks in cream, a dash instead of an empty ring for matches without a review, “More settings” as a folded row."
      ],
      "0.46.0": [
        "Scroll down a review and its top bar stays with you: the hero, the result, the score and ‹ Newer · Older ›.",
        "Progress tiles show your last 20 matches: wins and losses, and how gold, last hits and the score went.",
        "Match scores on the charts are coloured like the score rings; the first start shows its progress and a real advice card."
      ],
      "0.45.0": [
        "A new look: Wardly's red, warmer colours and bolder headings, the same as on the site.",
        "The review header and the current match show your hero large; win and loss are coloured tags.",
        "Your Steam name and picture at the bottom of the side menu open your profile.",
        "Clearer English texts in the in-game tips and the reviews."
      ],
      "0.44.2": [
        "A review saved as a PDF keeps every hero and item picture, charts at their real size and no cards over each other.",
        "Clearer in-game and review texts in Russian."
      ],
      "0.44.1": [
        "When the coach is starting or stopped, Matches, Progress and Profile say so (with a button to start it) instead of loading forever or asking to link your account again.",
        "A narrow window uses its whole width; reviews write numbers the way your language does."
      ],
      "0.44.0": [
        "Reviews in a row: “‹ Newer · Older ›” next to “Matches”, or the ← and → keys. Every review also links the match on OpenDota, Dotabuff and STRATZ.",
        "Hotkeys: Ctrl+1…5 open the tabs, Esc goes back to the match list; the whole list is in Settings → “Hotkeys”. The tray menu opens your latest review.",
        "Urgent advice on the card is red now, and while you move the card it shows a sample advice of the real size.",
        "Numbers as you read them, chart tooltips that close, a tidier Progress and Profile, and tabs that say what they will show before your account is linked."
      ],
      "0.43.2": [
        "Skill arrows find the ability icons by themselves (Full HD, 2K, 4K) and point at the “+” button to press; a hero with more abilities, or a new one from Aghanim's or the Shard, needs nothing. “Fine-tune” stays for another HUD.",
        "No more “plan a safer route” card before the horn: the moment the hero appears on the map is no death."
      ],
      "0.43.1": [
        "Role chosen by accident: if “Your role” says support but you play mid or carry, the card and Home say so once, with a button to switch back to Auto."
      ],
      "0.43.0": [
        "Arrows over your abilities: when a skill point is due, an arrow and the ability's name appear right over its icon on Dota's bar. Lay the frame over your ability icons once: Settings → “Arrows over your abilities” → “Set up the frame”."
      ],
      "0.42.0": [
        "Your starting items as icons: the card shows what Divine and Immortal players buy on your hero in your role — already during strategy time.",
        "The game plan draws the build as icons with the usual minute of each item.",
        "Gold piling up: the card names the part of your next item you can buy right now."
      ],
      "0.41.0": [
        "The first skill point stays on the card until you level it; the game plan comes 20 seconds before the horn.",
        "No starting items or gold piling up: the card says so for every role, even with map timers off.",
        "A card that stays the same for 20 seconds fades into the background; the next new one comes back bright."
      ],
      "0.40.3": [
        "A new first-run tour: real advice cards with what each line means, map calls, the game plan, the profile, the AI coach and help. Open it in Settings → Help → “Show”."
      ],
      "0.40.2": [
        "Mid: when the next power rune is coming and your Bottle still holds the last one, the card tells you to use it first.",
        "Fewer repeats: the farm pace card and the support's “No observer wards” come less often once you have seen them three times, and the ward reminder waits after you place your last ward."
      ],
      "0.40.1": [
        "The rating graph on the Profile tab is now a smooth line through your games instead of a zigzag.",
        "Your profile page for friends looks the way it does in the app: the same frame, banner and name colour, and your Steam avatar.",
        "Long titles in the shop sit in the middle of their card."
      ],
      "0.40.0": [
        "The first skill point: before the horn the card names the skill pros on your hero start with (when most of their games agree)."
      ],
      "0.39.0": [
        "“Hard lane” and “Your lane”: when the hero in your lane has beaten you (or lost to you) in the lane before, the card says so in the first minutes, with your record against them."
      ],
      "0.38.0": [
        "“Missing” calls in the laning stage: when the enemy mid or your lane opponent has not been seen for 20 seconds, the card warns you (and the voice says it when it reads every advice)."
      ],
      "0.37.0": [
        "A “Lane” card in the match review: last hits, denies, gold and XP at 3, 5, 7 and 10 minutes against the enemy core of your lane, and whether the lane was won.",
        "“Your lanes” on Progress: how many of your last lanes you won, and the heroes you lose the lane to."
      ],
      "0.36.0": [
        "Lane tips for cores in the first ten minutes: no regen on the way to lane, half HP with nothing to heal, no Magic Stick yet, too few denies.",
        "Items against the enemy lineup: Pipe of Insight or Black King Bar against magic damage, Glimmer Cape or Ghost Scepter for a support."
      ],
      "0.35.0": [
        "Friends on the “Profile” tab: show your profile by a friend code, add friends by theirs and see who is on top — level, rating, looks.",
        "Your profile as a page to send to a chat: api.luhovyimvp.dev/p/<code>."
      ],
      "0.34.0": [
        "New tab “Profile”: your rating graph like on FACEIT — enter your MMR once and every ranked game moves it.",
        "Levels, achievements and sparks for playing with Wardly.",
        "Spend sparks in the profile shop: avatar frames, banners, name colours and titles; the rare ones need a level or an achievement."
      ],
      "0.32.0": [
        "New in “More settings”: keep match recordings for a week. Save any match as a file and send it to the developer, the next day too.",
        "The problem report says which match the app recorded last and whether its review is ready."
      ],
      "0.31.2": [
        "A problem report sent after restarting the app still shows what the game sent during your last match."
      ],
      "0.31.1": [
        "The death review names a Haste, Invisibility, Shield or Illusion rune left unused in the Bottle.",
        "Fixed: the review showed a dash instead of the hero's ability when you died with it ready."
      ],
      "0.31.0": [
        "Low HP with a Haste, Invisibility, Shield or Illusion rune in the Bottle: the coach tells you to use it and run.",
        "A Regeneration or Water rune in the Bottle counts as healing, and a Bottle holding another rune no longer does.",
        "A power rune kept in the Bottle for 30 seconds: a reminder to use it for a kill."
      ],
      "0.30.3": [
        "Checked on real games: the enemies on the minimap, item readiness and the Roshan events reach the coach.",
        "The Roshan timer no longer loses the kill among chat messages and other game events."
      ],
      "0.30.2": [
        "The Roshan and Aegis timers now get their data from the game: restart Dota once after this update.",
        "Items in the backpack no longer count as ready to press.",
        "The problem report shows which data the game really sends: play a match and send one."
      ],
      "0.30.1": [
        "More heroes in the item advice: Linken's Sphere against Reaper's Scythe, Charge of Darkness and Winter's Curse, Maelstrom for a carry against illusion heroes, Dust against Mirana, Templar Assassin and Invoker."
      ],
      "0.30.0": [
        "Losing 30% HP or more in 5 seconds brings the urgent card at once, before HP is critical.",
        "The low-HP card shows what to press, how fast HP is falling and how many times it happened this game.",
        "A third death in one place this game is named after the death and on the respawn screen."
      ],
      "0.29.2": [
        "Items against the enemy heroes: dying under Beastmaster's Primal Roar, Doom or Duel brings a Linken's Sphere tip that says why; Monkey King Bar against evasion, Spirit Vessel against healing, Dust for a support against invisible heroes.",
        "An unlearned Blink no longer counts as on cooldown, and “you died with Blink ready” needs two free seconds to press it.",
        "Repeated low-HP cards say how many times it happened and ask to heal up fully."
      ],
      "0.29.1": [
        "A mid gets the power rune timer until minute 20, not all game, and before level 6 with a Bottle the hint says to keep the rune in it for a kill."
      ],
      "0.29.0": [
        "The match review is shorter: past the three main points, the other remarks and the long list of deaths open with “Show more”.",
        "The health line under each death says what it is, and “Net worth” is named plainly."
      ],
      "0.28.0": [
        "The first advice after a death names the lane or part of the map where you died, or how fast the kill came, instead of “plan a safer route”.",
        "Supports: the “no save item” tip names the save item most bought on your hero and how much gold it still needs; the ward tip says where to put it (your lane's river, Roshan's pit, your own or the enemy jungle by the score).",
        "A lane under a good farm pace gets the numbers: “Recover farm: 12 last hits at minute 5, a good pace is 18+”."
      ],
      "0.27.0": [
        "The advice after a death says how many times you have died, lately or this game, instead of the same “change your route” line."
      ],
      "0.26.0": [
        "The match review has a “Skill order” card: which skill you maxed first and how pro players level your hero."
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
        "Less banal advice: a kill streak, the kill score gap or your pace in numbers instead of the same “farm safely”."
      ],
      "0.21.0": [
        "Settings are rebuilt: five clear groups, bigger text, fewer buttons, and a plain line under every setting. Moving to another computer now explains itself step by step.",
        "“Why this advice?” under every advice on Home and in the review: what the coach saw.",
        "“What does this mean?” for the match score, the rank comparison and the focus, and no more technical words across the app."
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
        "Optional anonymous statistics (Settings → App, off by default): which advice was shown and which warnings came before a death, to make the advice better. “What is sent” shows the exact text.",
        "“Delete my data on the server” removes your problem reports, shared links and statistics in one press."
      ],
      "0.16.0": [
        "In a review, “Watch” next to a death or a key moment copies the replay command that jumps 10 s before it.",
        "The match chart shows your best match on this hero as a dashed line.",
        "Home: streak goals (5 matches in a row with 5 deaths or fewer) and a gentle note after 3 losses in a row.",
        "Progress: heroes to play more and heroes to park, against your rank."
      ],
      "0.15.0": [
        "Roshan and Aegis timers: the respawn window after a kill, and your Aegis warns a minute before it expires.",
        "While you wait to respawn: how you died, what was left unpressed, what to buy now.",
        "No more “wait out the disable” when there is nothing to press after the stun."
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
        "Fixed: some reviews stayed on “Loading the match” forever."
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
        "Status in Discord: your friends see “Playing <hero> · with the Wardly coach”. Switch it off in Settings → App.",
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
        "Good-pace lines for gold and XP on the “Over the match” chart.",
        "A “Deaths” card: where, who killed you, unspent gold and the advice shown before each death.",
        "Mistakes that keep coming back are marked: “3 matches in a row”.",
        "This week on Home: matches, score change, best match, the most frequent mistake and a 3-match plan for your focus."
      ],
      "0.3.0": [
        "Map timers on the overlay 20 s ahead: runes, wisdom shrines, lotuses, the Tormentor, neutral item tiers — only the ones your role needs.",
        "Your role is found from your lane in the first minutes (or chosen in Settings → Advice) and shown on Home.",
        "Support tips: stack a camp, take wards, leave the last hits to your carry. No carry farm advice on a support; the TP reminder works on every hero.",
        "“Send to developer” in the problem report: one click, with a note and a preview; keys, nickname and Steam ID are removed.",
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
        "“Ask the coach”: your own question about a match, answered from its data.",
        "Spoken advice, advice frequency, survival advice for every hero, reminders to carry a TP scroll and to spend gold while dead.",
        "Match map, this match against your usual numbers, match filters and PDF export.",
        "A check for Dota's -gamestateintegration launch option, without which no game data arrives."
      ]
    },
    ru: {
      "0.53.31": [
        "AI-разборы и сохранённые ответы проверяют добивания и денаи по собственным итогам матча, отдельно — данные к 10:00 и сравнение с соперником."
      ],
      "0.53.30": [
        "Запоздавшие ответы истории не заменяют новый фильтр или сортировку; повторные нажатия «Ещё» не дублируют страницу."
      ],
      "0.53.29": [
        "Задержавшийся ответ разбора не заменяет новый выбор и не обновляет разбор после смены вкладки или языка."
      ],
      "0.53.28": [
        "Возврат из разбора сохраняет фокус строки при обновлении таблицы; история переходов назад/вперёд проверяется на двух языках."
      ],
      "0.53.27": [
        "Таблица матчей сохраняет частичный K/D/A, заметки и неизвестный результат при загрузке страниц, сортировке и фильтрации; эти действия проверяются на двух языках."
      ],
      "0.53.26": [
        "AI-разбор и ответы проверяют GPM и XPM по соответствующим показателям игрока и показывают данные для проверки."
      ],
      "0.53.25": [
        "Статус игрока сохраняет состояния ожидания, очереди, выполнения, завершения и ошибки синхронизации; нулевые счётчики отличаются от отсутствующих данных."
      ],
      "0.53.24": [
        "История обновлений сохраняет русские и английские описания, включая пропущенные при обновлении версии."
      ],
      "0.53.23": [
        "Задержавшийся демо-кадр не возвращает оверлей после сброса сессии и не заменяет более новый кадр."
      ],
      "0.53.22": [
        "Подсказки карты, прокачки и покупок обновляются вместе; подготовленные до сброса сессии подсказки отбрасываются."
      ],
      "0.53.21": [
        "Сведения о врагах, линии, телепортации и объектах читаются согласованно при обновлении игры и сбросе сессии."
      ],
      "0.53.20": [
        "Настройки таймеров Рошана и Аегиса загружаются перед обновлением состояния, сохраняя отзывчивость первого события и сброса."
      ],
      "0.53.19": [
        "Сброс сессии не ждёт чтения истории для определения роли; игровое состояние использует заранее подготовленные данные."
      ],
      "0.53.18": [
        "Сводка памяти матча обновляется согласованно при поступлении игровых и демо-данных и при сбросе сессии."
      ],
      "0.53.17": [
        "K/D/A матча сохраняет известные значения, включая ноль, и показывает прочерк для каждого отсутствующего счётчика."
      ],
      "0.53.16": [
        "Переводы экранов матчей выделены в отдельный модуль; прежние тексты и форматирование чисел проверяются на обоих языках."
      ],
      "0.53.15": [
        "GSI-пакет, состояние и время получения обновляются вместе. Сброс очищает прежний пакет и ждёт свежие данные Dota."
      ],
      "0.53.14": [
        "Фоновые задачи выделены в самостоятельную проверяемую очередь с прежними отложенными повторными попытками и безопасной остановкой."
      ],
      "0.53.13": [
        "ИИ проверяет убийства, смерти и ассисты по их собственным счётчикам матча. В разборе можно раскрыть данные, на которых основана проверка."
      ],
      "0.53.12": [
        "Документация и сайт проверяются быстрее, а изменения приложения сохраняют обязательную проверку Windows-установщика."
      ],
      "0.53.11": [
        "Перенос истории теперь надёжно обрабатывает одновременные скачивания и совпадения кодов. Поздняя очистка сохраняет новый перенос с повторно занятым кодом."
      ],
      "0.53.10": [
        "Для выпуска установщика теперь нужны общие проверки той же версии исходного кода перед публикацией."
      ],
      "0.53.9": [
        "Улучшены автоматические проверки обновлений, чтобы раньше находить новые ошибки в коде."
      ],
      "0.53.8": [
        "Защищены окна приложения: действия принимаются только от своего локального интерфейса, а посторонние переходы и всплывающие окна блокируются."
      ],
      "0.53.7": [
        "Сайты больше не могут менять локальные настройки тренера или отправлять игровые данные. Дота использует отдельное защищённое подключение; после обновления перезапустите Доту один раз."
      ],
      "0.53.6": [
        "Файл истории проверяется до загрузки и восстанавливается целиком одной операцией. Повреждённый кеш больше не мешает открыть разбор."
      ],
      "0.53.5": [
        "Повторные фоновые запросы не дублируют выполняющуюся задачу. При закрытии тренер отменяет ожидающие задачи и ограниченно ждёт активные."
      ],
      "0.53.4": [
        "Если завершённый матч не удаётся сохранить, тренер повторит попытку, в том числе после перезапуска. Следующий матч продолжает записываться."
      ],
      "0.53.3": [
        "Готовый тренер теперь использует те же закреплённые версии библиотек, что и автоматические проверки."
      ],
      "0.53.2": [
        "Обновлены движок приложения и зависимости с исправлениями безопасности."
      ],
      "0.53.1": [
        "Советы продолжают работать, если журнал не удаётся сохранить. Ошибка попадёт в отчёт о проблеме."
      ],
      "0.53.0": [
        "Ctrl+K находит всё: вкладку, матч по герою или вашей заметке, «Прогресс на герое», настройку или действие.",
        "Значок заметки теперь и в «Последних матчах» на Главной."
      ],
      "0.52.0": [
        "Поиск по настройкам: поле вверху «Настроек» (Ctrl+F) оставляет только строки с вашими словами.",
        "Размер интерфейса в «Настройки» → «Приложение» (90–125 %) или Ctrl + плюс / минус.",
        "Заметки к матчам: ваша строчка в шапке разбора, значком — и в таблице матчей.",
        "Боковые кнопки мыши и Alt+←/→ ходят по открытым страницам; ↑/↓ — по строкам таблицы матчей."
      ],
      "0.51.0": [
        "Любой матч по номеру: вставьте номер или ссылку OpenDota, Dotabuff или STRATZ рядом с фильтрами матчей — полный разбор получат и игры старше вашей истории.",
        "На графике разбора под минутами — ваши предметы: когда пришёл каждый собранный предмет.",
        "Пока вы ждёте возрождения, карточка оверлея показывает иконку предмета, который стоит купить."
      ],
      "0.50.0": [
        "Предметы везде: в таблице матчей видно, с чем вы закончили каждую игру, то же — в шапке разбора, а в «Итогах матча» — предметы всех десяти игроков.",
        "У «Последних матчей» на Главной тоже есть предметы; наведите на иконку — появится название."
      ],
      "0.49.0": [
        "Подсказки по прокачке показывают иконку способности, а порядок прокачки у про — иконками, нужная сейчас обведена; в карточке «Прокачка» разбора тоже иконки.",
        "У длинных страниц есть разделы: в верхней полосе разбора и в «Прогрессе» — ссылки на части страницы, переход в один клик, текущая часть подсвечена.",
        "Клавиша ? на любой вкладке показывает горячие клавиши; таблица матчей помнит, как вы её отсортировали."
      ],
      "0.48.0": [
        "Матчи можно сортировать: нажмите на столбец таблицы (оценка, золото, добивания, длительность, У/С/П, дата), ещё раз — в обратную сторону.",
        "В профиле видно ближайшую награду, а в списке смертей понятнее график здоровья за последние 20 секунд.",
        "Мелочи: таблицы в узкой колонке ровно по краю текста, «Что это значит?» больше не наезжает на строку таблицы, шапка разбора спокойнее."
      ],
      "0.47.0": [
        "У карточки в игре цветная полоска слева: красная — срочно, жёлтая — совет, зелёная — спокойная подсказка, кремовая — карта и план.",
        "Пока Дота запущена, «Главная» показывает текущий матч первым.",
        "Спокойнее мелочи: прогресс наград и искры кремовые, у матча без разбора — прочерк вместо пустого кольца, «Ещё настройки» — раскрывающаяся строка."
      ],
      "0.46.0": [
        "При прокрутке разбора верхняя полоса остаётся на месте: герой, итог, оценка и «‹ Новее · Старее ›».",
        "Плитки «Прогресса» показывают последние 20 матчей: победы и поражения, как менялись золото, добивания и оценка.",
        "Оценки матчей на графиках окрашены как кольца оценок; первый запуск показывает, сколько осталось, и пример настоящей подсказки."
      ],
      "0.45.0": [
        "Новый облик: фирменный красный Wardly, тёплые цвета и выразительные заголовки — как на сайте.",
        "В шапке разбора и в текущем матче — ваш герой крупным планом, победа и поражение — цветные метки.",
        "Ваш ник и аватар Steam внизу бокового меню открывают профиль.",
        "Понятнее английские тексты подсказок и разборов."
      ],
      "0.44.2": [
        "Разбор в PDF: на месте все портреты героев и иконки предметов, графики нормального размера, карточки не наезжают друг на друга.",
        "Понятнее тексты подсказок в игре и разборов: «Смерть от Axe», «Денаев к 4:00», «Пулл в 2:15» и другие мелочи."
      ],
      "0.44.1": [
        "Когда тренер запускается или остановлен, «Матчи», «Прогресс» и «Профиль» так и говорят (с кнопкой запуска), а не грузятся бесконечно и не просят заново привязать аккаунт.",
        "Узкое окно использует всю ширину; в разборах дробные числа записаны через запятую."
      ],
      "0.44.0": [
        "Разборы подряд: «‹ Новее · Старее ›» рядом с «Матчи» или клавиши ← и →. В каждом разборе есть ссылки на этот матч на OpenDota, Dotabuff и STRATZ.",
        "Горячие клавиши: Ctrl+1…5 открывают вкладки, Esc возвращает к списку матчей; весь список — в «Настройки → Горячие клавиши». В меню в трее — разбор последнего матча.",
        "Срочный совет на карточке теперь красный, а пока вы перемещаете карточку, на ней виден пример совета настоящего размера.",
        "Числа записаны как принято (7,5), подсказки на графиках закрываются, «Прогресс» и «Профиль» аккуратнее, а вкладки до привязки аккаунта рассказывают, что на них будет."
      ],
      "0.43.2": [
        "Стрелки над навыками сами находят иконки способностей (Full HD, 2K, 4K) и показывают на кнопку «+», которую нужно нажать. У героя с другим числом способностей и после новой способности от аганима или шарда ничего настраивать не нужно. «Подправить» осталось на случай другого интерфейса.",
        "Больше нет карточки «спланируйте безопасный маршрут» до горна: появление героя на карте — не смерть."
      ],
      "0.43.1": [
        "Роль выбрана по ошибке: если в «Ваша роль» стоит саппорт, а вы играете мид или керри, карточка и Главная один раз скажут об этом — с кнопкой, чтобы вернуть «Авто»."
      ],
      "0.43.0": [
        "Стрелки над навыками: когда есть очко навыка, над нужной иконкой на панели Доты появляется стрелка с названием способности. Один раз совместите рамку с иконками: «Настройки → Стрелки над навыками → Настроить рамку»."
      ],
      "0.42.0": [
        "Стартовые предметы иконками: карточка показывает, что покупают на вашем герое и вашей роли игроки Divine и Immortal, — уже на стадии стратегии.",
        "План на игру рисует сборку иконками с обычной минутой каждого предмета.",
        "Копится золото — карточка называет часть следующего предмета, которую можно купить прямо сейчас."
      ],
      "0.41.0": [
        "Первое очко навыка держится на карточке, пока вы его не вложите; план на игру появляется за 20 секунд до горна.",
        "Пустой инвентарь в начале или копящееся золото: карточка скажет об этом на любой роли, даже с выключенными таймерами карты.",
        "Карточка, которая не меняется 20 секунд, становится полупрозрачной; новая снова яркая — её сразу заметно."
      ],
      "0.40.3": [
        "Новое обучение: настоящие карточки советов с объяснением, что значит каждая строка, подсказки по карте, план на игру, профиль, ИИ-тренер и помощь. Открыть: «Настройки → Помощь → Показать»."
      ],
      "0.40.2": [
        "Мид: если подходит руна силы, а в бутылке ещё лежит прошлая, карточка напомнит сначала использовать её.",
        "Меньше повторов: карточка про темп фарма и «Нет вардов» у саппорта приходят реже после трёх раз, а напоминание о вардах ждёт, если вы только что поставили последний."
      ],
      "0.40.1": [
        "График рейтинга во вкладке «Профиль» теперь плавная линия, а не ломаная.",
        "Страница вашего профиля для друзей выглядит как в приложении: та же рамка, баннер и цвет ника, и ваша аватарка из Steam.",
        "Длинные титулы в магазине стоят по центру карточки."
      ],
      "0.40.0": [
        "Первое очко навыка: ещё до начала игры карточка подскажет, с какого навыка начинают про-игроки на вашем герое (если большинство их игр сходится)."
      ],
      "0.39.0": [
        "«Тяжёлая линия» и «Удобная линия»: если герой на вашей линии уже не раз обыгрывал вас на линии (или проигрывал вам), карточка скажет об этом в первые минуты — со счётом ваших прошлых линий против него."
      ],
      "0.38.0": [
        "Подсказка «соперник пропал» на линии: если мида соперника или вашего соперника по линии не видно 20 секунд, карточка предупредит (а голос скажет, если он читает все советы)."
      ],
      "0.37.0": [
        "Карточка «Линия» в разборе матча: добивания, денаи, золото и опыт на 3, 5, 7 и 10-й минутах против кора соперника на вашей линии и итог линии.",
        "«Ваши линии» в «Прогрессе»: сколько последних линий вы выиграли и против каких героев проигрываете линию."
      ],
      "0.36.0": [
        "Советы на линии для коров в первые десять минут: нет регенерации по дороге на линию, половина HP и нечем лечиться, ещё нет Magic Stick, мало добитых своих крипов.",
        "Предметы против состава врага: Pipe of Insight или Black King Bar против магического урона, Glimmer Cape или Ghost Scepter для саппорта."
      ],
      "0.35.0": [
        "Друзья на вкладке «Профиль»: покажите профиль по коду друга, добавьте друзей по их кодам и смотрите, кто выше — уровень, рейтинг, оформление.",
        "Ваш профиль страницей, которую можно скинуть в чат: api.luhovyimvp.dev/p/<код>."
      ],
      "0.34.0": [
        "Новая вкладка «Профиль»: график рейтинга как на FACEIT — введите свой MMR один раз, и каждая рейтинговая игра будет его двигать.",
        "Уровни, награды и искры за игру с Wardly.",
        "Тратьте искры в магазине профиля: рамки аватара, баннеры, цвет ника и титулы; редкие открываются с уровнем или за награду."
      ],
      "0.32.0": [
        "Новое в «Ещё настройках»: записи матчей хранятся неделю. Любой матч можно сохранить файлом и отправить разработчику — хоть на следующий день.",
        "Отчёт о проблеме показывает, какой матч приложение записало последним и готов ли его разбор."
      ],
      "0.31.2": [
        "Отчёт о проблеме, отправленный после перезапуска приложения, всё равно показывает, что игра присылала в последнем матче."
      ],
      "0.31.1": [
        "Разбор смерти говорит, если в бутылке осталась неиспользованная руна ускорения, невидимости, щита или иллюзий.",
        "Исправлено: в разборе стоял прочерк вместо способности героя, с которой вы погибли, не нажав её."
      ],
      "0.31.0": [
        "Мало HP, а в бутылке руна ускорения, невидимости, щита или иллюзий — тренер подскажет нажать её и уходить.",
        "Руна регенерации или воды в бутылке считается лечением, а бутылка с другой руной — больше нет.",
        "Руна силы лежит в бутылке 30 секунд — подсказка использовать её для убийства."
      ],
      "0.30.3": [
        "Проверено на настоящих играх: враги на мини-карте, готовность предметов и события Рошана доходят до тренера.",
        "Таймер Рошана больше не теряет убийство среди сообщений чата и других событий игры."
      ],
      "0.30.2": [
        "Таймер Рошана и Аегиса теперь получает данные из игры: один раз перезапустите Доту после обновления.",
        "Предметы в рюкзаке больше не считаются готовыми к нажатию.",
        "Отчёт о проблеме показывает, какие данные игра присылает на самом деле: сыграйте матч и отправьте его."
      ],
      "0.30.1": [
        "Больше героев в советах по предметам: Linken's Sphere против Reaper's Scythe, Charge of Darkness и Winter's Curse, Maelstrom керри против героев с иллюзиями, Dust против Mirana, Templar Assassin и Invoker."
      ],
      "0.30.0": [
        "Если за 5 секунд ушло 30 % здоровья и больше, срочная карточка появляется сразу, до критического HP.",
        "Карточка низкого HP показывает, что нажать, как быстро падает здоровье и какой это раз за игру.",
        "Третья смерть в одном месте за игру называется в совете после смерти и на экране возрождения."
      ],
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
    }
  };

  // "0.51.0" > "0.50.2": the parts as numbers.
  function newerVersion(a, b) {
    const x = String(a).split(".").map((part) => Number.parseInt(part, 10) || 0);
    const y = String(b).split(".").map((part) => Number.parseInt(part, 10) || 0);
    for (let i = 0; i < Math.max(x.length, y.length); i += 1) {
      if ((x[i] || 0) !== (y[i] || 0)) {
        return (x[i] || 0) > (y[i] || 0);
      }
    }
    return false;
  }

  // The new version's bullets, then those of the versions an update skipped
  // (0.49 → 0.51 also lists 0.50), newest first, four versions at most.
  function whatsNewVersions(table, current, from) {
    return Object.keys(table)
      .filter((version) => Array.isArray(table[version]) && table[version].length)
      .filter((version) => version === current || (from && newerVersion(version, from) && newerVersion(current, version)))
      .sort((a, b) => (newerVersion(a, b) ? -1 : newerVersion(b, a) ? 1 : 0))
      .slice(0, 4);
  }


  // Copies keep callers from mutating the module's static history.
  function texts(language) {
    const table = TEXT[language === "ru" ? "ru" : "en"];
    return Object.fromEntries(Object.entries(table).map(([version, bullets]) => [version, [...bullets]]));
  }

  return { texts, versions: whatsNewVersions };
});
