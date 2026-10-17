# Hero item plans

The live counter items (`backend/app/situational_items.py`) answer an enemy hero
by kind and position: a carry against evasion gets Monkey King Bar, whoever the
carry is. A hero item plan (`data/heroes/item_plans/<hero>.json`, loaded by
`backend/app/hero_items.py`) says what **this** hero buys instead. Terrorblade
is the first plan and the reference for the others.

The plan's counters come after the death patterns (BKB after deaths under stuns,
Linken's against a single-target disabler, Aeon Disk after bursts) and replace
the generic counters of the same family. `suppress` drops a generic counter that
does not fit the hero. Outside the plan's `positions` the generic counters stay.
The enemies come only from the enemy icon on the minimap (`enemy_heroes.py`):
allies and the player's own hero are never counted.

## The checklist for a hero

1. **The hero's build.** Read `data/meta/stratz_builds.json` (STRATZ
   Divine–Immortal, refreshed weekly) for the position: the core items and
   their minutes. A counter that is already in the build is "buy it earlier";
   one that is off the build needs a reason strong enough to change it.
2. **The mechanics, from Valve, for the current patch.** For every item the
   plan names, read `https://www.dota2.com/datafeed/itemdata?language=english&item_id=<id>`
   (ids from `/datafeed/itemlist`) and write the fact the rule depends on into
   its `basis`: e.g. Bloodthorn 7.41f gives True Strike to the hero's *controlled
   units* against the silenced target, which is why it suits an illusion hero.
   Hero abilities from `/datafeed/herodata?hero_id=<id>`. No rule from memory.
3. **The enemy groups.** Rules name groups from `hero_items.groups()`:
   `evasion`, `illusions`, `healing` (`draft_analysis.COUNTERS`), `escape`
   (`draft_analysis.ESCAPES`: escapes a silence stops, spell names from
   `/herodata`), `break` (`situational_items.BREAK_PASSIVES`). A new group goes
   into those tables with its own check, not into one plan.
4. **The rules**, in order; the first that holds wins its `family`:
   - `why` — the reason shown (one of `hero_items.WHYS`);
   - `item` / `name` — the OpenDota item key and the English name;
   - `enemy` (and `also`, a second group that must be seen too);
   - `minute` — from when the live farm advice may name it (the draft card
     early in the match ignores it);
   - `basis` — the build line or the Valve fact behind it.
   Put the more specific rule first (Bloodthorn for evasion **and** an escape,
   then Monkey King Bar for evasion alone).
5. **What does not fit.** `suppress` maps a generic `why` to the reason it is
   wrong for the hero (Terrorblade: no Maelstrom against illusions).
6. **The words.** A new `why` needs its reason in each place that shows one,
   in English and Ukrainian: `map_hints.TIPS["draft_<why>"]`,
   `death_screen.TEXT[lang]["why_<why>"]`, `post_laning_coach.SITUATIONAL_BECAUSE`
   with its Ukrainian pattern in `advice_i18n.py`. `test_hero_items.py` fails
   when one is missing.
7. **The scenarios.** Add the hero's cases to `backend/tests/test_hero_items.py`:
   each rule, the rule that must *not* fire (Anti-Mage is no escape for a
   silence: Counterspell), an owned item that answers the family, the minute
   gate, the death patterns still first, other heroes unchanged, and one live
   `/gsi` run to the overlay card.
8. **A real match.** Replay a recording on the hero (Settings → Keep match
   recordings for a week) and read which counter the card names and when.

## Terrorblade (7.41f, checked 2026-10-17)

| Enemy lineup | Item | Why |
|---|---|---|
| Phantom Assassin or Windranger, and Queen of Pain, Storm Spirit, Puck, Ember Spirit, Void Spirit, Weaver, Mirana, Morphling or Faceless Void | Bloodthorn | Soul Rend: 5 s silence stops the escape; True Strike for his attacks and his illusions against the silenced target; passive pierce 40% |
| Phantom Assassin or Windranger alone (or with Anti-Mage) | Monkey King Bar | 80% pierce, nothing to cast, 1400 gold cheaper |
| Alchemist, Necrophos, Huskar, Oracle or Lifestealer | Eye of Skadi earlier | in his build (~28 min); attacks cut health restoration by 50% |
| Phantom Lancer, Naga Siren, Chaos Knight, Meepo, Terrorblade | — | no Maelstrom: off his build (open check) |
| Bristleback, Spectre, Huskar (after Skadi) | Silver Edge | the generic break counter, unchanged |

Open checks before the next plans: an answer to illusion heroes for
Terrorblade; Butterfly and other enemy items are not visible to a player's
GSI, so no rule may depend on them.
