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
   `/herodata`), `break` (`situational_items.BREAK_PASSIVES`), `jumpers`
   (`draft_analysis.JUMPERS`: heroes who jump onto a carry). A new group goes
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
5. **What does not fit.** A family the plan answers replaces the generic
   counter (Terrorblade's illusions family: Butterfly, no Maelstrom);
   `suppress` maps a generic `why` the plan leaves unanswered to the reason it
   is wrong for the hero.
6. **Tempo** (optional). `tempo.net_worth` is a curve `[[minute, net worth], ...]`
   from high-rank games of the hero: above it the hero wins most games (read the
   gold timelines in OpenDota Explorer, `player_matches.gold_t`; net worth is
   ~0.96 of that gold). With the player's own net worth over it (gold plus the
   items carried, `next_item.net_worth`), the counters wait and `tempo.items`
   go on. A player's GSI has no enemy or team net worth: the hero's own farm is
   the observed sign.
7. **The words.** A new `why` needs its reason in each place that shows one,
   in English and Ukrainian: `map_hints.TIPS["draft_<why>"]`,
   `death_screen.TEXT[lang]["why_<why>"]`, `post_laning_coach.SITUATIONAL_BECAUSE`
   with its Ukrainian pattern in `advice_i18n.py`. `test_hero_items.py` fails
   when one is missing.
8. **The scenarios.** Add the hero's cases to `backend/tests/test_hero_items.py`:
   each rule, the rule that must *not* fire (Anti-Mage is no escape for a
   silence: Counterspell), an owned item that answers the family, the minute
   gate, the death patterns still first, other heroes unchanged, and one live
   `/gsi` run to the overlay card.
9. **A real match.** Replay a recording on the hero (Settings → Keep match
   recordings for a week) and read which counter the card names and when.

## Terrorblade (7.41f, checked 2026-10-17)

Rules in order (the first that holds wins its family; one item per family):

| Family | Enemy lineup | Item | Why |
|---|---|---|---|
| evasion | Phantom Assassin or Windranger, and Queen of Pain, Storm Spirit, Puck, Ember Spirit, Void Spirit, Weaver, Mirana, Morphling or Faceless Void | Bloodthorn | Soul Rend: 5 s silence stops the escape; True Strike for his attacks and his illusions against the silenced target; passive pierce 40% |
| evasion | Phantom Assassin or Windranger alone (or with Anti-Mage) | Monkey King Bar | 80% pierce, nothing to cast, 1400 gold cheaper |
| healing | Alchemist, Necrophos, Huskar, Oracle or Lifestealer | Eye of Skadi, from minute 20 | in his build; attacks cut health restoration by 50%; high-rank players buy it more often against them (70% vs 61%), at the same ~27 min |
| illusions | Phantom Lancer, Naga Siren, Chaos Knight, Meepo, Terrorblade | Butterfly | 35% evasion: about a third of the illusions' attacks miss |
| lance | the same illusion heroes | Hydra's Breath | the Dragon Lance goes here, not into Pike: in Metamorphosis 30% of ranged attacks hit up to 3 more enemies, Miasma poisons them |
| lance | Slark, Phantom Assassin, Spirit Breaker | Hurricane Pike | pushes the jumper 425 away, 5 attacks from range with +100 attack speed |
| (generic) | Bristleback, Spectre, Huskar (after Skadi) | Silver Edge | the generic break counter, unchanged |

**Tempo:** with his own net worth over 12.0k at 20:00, 16.3k at 25:00 and 21.1k
at 30:00 (linear between, the same slope after), the counters wait and the next
item is the tempo build's — Manta Style, Eye of Skadi, Butterfly, Daedalus —
then the Aegis and the throne. In 617 league games of patch 7.41 (OpenDota
Explorer) he wins 86-100% with 12.5k+ gold by 20:00, 85% with 17k+ by 25:00 and
85% with 22k+ by 30:00, against 52-56% at 10-12k by 20:00.

The same games back the counters: Monkey King Bar in 45% of games against
Phantom Assassin or Windranger (12% otherwise); Bloodthorn 12% (5%) when an
escape hero is there too, won 67% against 50%; against illusion heroes Butterfly
51% (38%), Hurricane Pike 18% (44%) and Maelstrom never. Dragon Lance is his
third item in 87% of games. Samples are small (25-100 games per lineup) and a
bought item also means a farmed hero: these are checks, not proof.

The illusion, Pike and tempo rules come from a player's review (2026-10-17),
checked against the items' Valve data. Butterfly and other enemy items are not
visible to a player's GSI, so no rule may depend on them.
