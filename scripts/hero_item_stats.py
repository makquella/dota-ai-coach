"""High-rank numbers for a hero item plan (docs/HERO_ITEM_PLANS.md), from the
open OpenDota Explorer (league games with parsed gold timelines):

- the win rate by the hero's gold at 20, 25 and 30 minutes, and the gold where
  it first reaches --win (the plan's tempo curve; net worth is ~0.96 of it);
- the item order in all won games (the usual build) and in those over the
  20-minute line (the tempo build);
- how often each counter is bought against each enemy group, and the win rate
  with and without it (draft_analysis / hero_items groups);
- the skill build: the order the basic abilities are maxed, the first point
  and each talent row's picks, with win rates (a plan's `skills`).

    python scripts/hero_item_stats.py terrorblade --since 2026-03-24

Read-only, no key; small samples and «a bought item means a farmed hero»
apply: the numbers check a plan, they do not write it.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

EXPLORER = "https://api.opendota.com/api/explorer?sql="
USER_AGENT = "Wardly hero item stats"
NET_WORTH_SHARE = 0.96  # final net worth / gold earned, Terrorblade 7.41 games
TIMEOUT = 120


def explorer(sql: str) -> list[dict]:
    request = urllib.request.Request(
        EXPLORER + urllib.parse.quote(sql), headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310
        answer = json.loads(response.read())
    if answer.get("err"):
        raise SystemExit(f"OpenDota Explorer: {answer['err']}")
    return list(answer.get("rows") or [])


def games(hero_id: int, since: int) -> list[dict]:
    rows = explorer(
        "SELECT pm.match_id, pm.player_slot, m.radiant_win, pm.gold_t[21] AS g20, "
        "pm.gold_t[26] AS g25, pm.gold_t[31] AS g30, pm.purchase_log "
        "FROM player_matches pm JOIN matches m USING(match_id) "
        f"WHERE pm.hero_id={hero_id} AND m.start_time > {since} "
        "AND array_length(pm.gold_t, 1) > 20"
    )
    for row in rows:
        row["win"] = row["radiant_win"] == (row["player_slot"] < 128)
    return rows


def enemies(hero_id: int, since: int, rows: list[dict]) -> dict[int, set[str]]:
    from app.dota_constants import hero_name

    side = {r["match_id"]: r["player_slot"] < 128 for r in rows}
    lineup: dict[int, set[str]] = defaultdict(set)
    for r in explorer(
        "SELECT o.match_id, o.player_slot, o.hero_id FROM player_matches o WHERE o.match_id IN "
        "(SELECT pm.match_id FROM player_matches pm JOIN matches m USING(match_id) "
        f"WHERE pm.hero_id={hero_id} AND m.start_time > {since})"
    ):
        if r["match_id"] in side and (r["player_slot"] < 128) != side[r["match_id"]]:
            lineup[r["match_id"]].add(hero_name(r["hero_id"]))
    return lineup


def assembled_items() -> set[str]:
    """Item keys built from a recipe (no components, consumables or parts)."""
    request = urllib.request.Request(
        "https://api.opendota.com/api/constants/items", headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310
        items = json.loads(response.read())
    return {key for key, info in items.items() if isinstance(info, dict) and info.get("components")}


def order(group: list[dict], built: set[str], title: str) -> None:
    """Assembled items bought in 20%+ of `group`, by median minute."""
    share: Counter[str] = Counter()
    minutes: dict[str, list[float]] = defaultdict(list)
    for r in group:
        seen: set[str] = set()
        for p in r.get("purchase_log") or []:
            key = p.get("key")
            if key in built and key not in seen:
                seen.add(key)
                minutes[key].append(p["time"] / 60)
        share.update(seen)
    print(f"\n{title} (share, median minute):")
    rows = [(k, c) for k, c in share.items() if group and c / len(group) >= 0.2]
    for key, count in sorted(rows, key=lambda kc: statistics.median(minutes[kc[0]])):
        median = statistics.median(minutes[key])
        print(f"  {key:22} {100 * count / len(group):3.0f}%  {median:4.0f}")


def constants(name: str) -> dict:
    request = urllib.request.Request(
        f"https://api.opendota.com/api/constants/{name}", headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310
        return dict(json.loads(response.read()))


def skills(hero_id: int, since: int, npc: str) -> None:
    """The skill build of the hero's games (ability_upgrades_arr)."""
    rows = explorer(
        "SELECT pm.player_slot, m.radiant_win, pm.ability_upgrades_arr AS ups "
        "FROM player_matches pm JOIN matches m USING(match_id) "
        f"WHERE pm.hero_id={hero_id} AND m.start_time > {since} "
        "AND pm.ability_upgrades_arr IS NOT NULL"
    )
    ids = constants("ability_ids")
    abilities = constants("abilities")
    hero = constants("hero_abilities").get(npc) or {}
    tiers = {t["name"]: (10, 15, 20, 25)[t["level"] - 1] for t in hero.get("talents") or []}
    games = []
    for r in rows:
        names = [ids.get(str(a)) for a in r["ups"] or []]
        games.append(
            {
                "names": [n for n in names if n],
                "win": r["radiant_win"] == (r["player_slot"] < 128),
            }
        )
    orders: dict[tuple[str, ...], list[dict]] = defaultdict(list)
    openings: dict[str, list[dict]] = defaultdict(list)
    for g in games:
        counts: Counter[str] = Counter()
        maxed = []
        for name in g["names"]:
            if name.startswith("special_bonus"):
                continue
            counts[name] += 1
            if counts[name] == 4:
                maxed.append(name)
        orders[tuple(maxed)].append(g)
        first = next((n for n in g["names"] if not n.startswith("special_bonus")), None)
        if first:
            openings[first].append(g)
    print(f"\nskill build ({len(games)} games):")
    print("  maxed in this order:")
    for order, group in sorted(orders.items(), key=lambda kv: -len(kv[1]))[:4]:
        print(f"    {' > '.join(order) or '-'}: {len(group)} games, win {rate(group)}")
    print("  first point:")
    for name, group in sorted(openings.items(), key=lambda kv: -len(kv[1]))[:3]:
        print(f"    {name}: {len(group)} games, win {rate(group)}")
    print("  talents:")
    for level in (10, 15, 20, 25):
        picks: dict[str, list[dict]] = defaultdict(list)
        for g in games:
            talent = next((n for n in g["names"] if tiers.get(n) == level), None)
            if talent:
                picks[talent].append(g)
        total = sum(len(v) for v in picks.values())
        for name, group in sorted(picks.items(), key=lambda kv: -len(kv[1])):
            label = (abilities.get(name) or {}).get("dname") or name
            print(f"    {level}: {label} — {len(group)} of {total}, win {rate(group)}  [{name}]")


def rate(group: list[dict]) -> str:
    return f"{100 * sum(g['win'] for g in group) / len(group):.0f}%" if group else "-"


def bought(game: dict, item: str) -> bool:
    return any(p.get("key") == item for p in game.get("purchase_log") or [])


def main() -> int:
    from app.dota_constants import hero_id_from_name
    from app.hero_items import groups

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("hero", help="e.g. terrorblade or 'Phantom Lancer'")
    parser.add_argument("--since", default="2026-03-24", help="patch start (YYYY-MM-DD)")
    parser.add_argument("--win", type=float, default=85.0, help="the tempo line, win %%")
    parser.add_argument("--items", default="", help="extra counter item keys, comma separated")
    args = parser.parse_args()
    hero_id = hero_id_from_name(args.hero.replace("_", " "))
    if hero_id is None:
        raise SystemExit(f"unknown hero {args.hero!r}")
    since = int(datetime.fromisoformat(args.since).replace(tzinfo=UTC).timestamp())
    rows = games(hero_id, since)
    if not rows:
        raise SystemExit("no games")
    print(f"{len(rows)} games since {args.since}, win {rate(rows)}")

    line: dict[int, int] = {}
    for minute, key in ((20, "g20"), (25, "g25"), (30, "g30")):
        known = [r for r in rows if r.get(key)]
        for gold in range(8000, 40001, 500):
            over = [r for r in known if r[key] >= gold]
            if len(over) >= 10 and 100 * sum(r["win"] for r in over) / len(over) >= args.win:
                line[minute] = gold
                print(
                    f"  {minute}:00  {gold}+ gold: {len(over)} games, win {rate(over)}"
                    f"  -> net worth ~{round(gold * NET_WORTH_SHARE, -2):.0f}"
                )
                break
    built = assembled_items() | {"aghanims_shard"}
    won = [r for r in rows if r["win"]]
    order(won, built, f"the usual build: items in all {len(won)} won games")
    if 20 in line:
        rich = [r for r in won if (r.get("g20") or 0) >= line[20]]
        order(rich, built, f"the tempo build: the {len(rich)} won games over the 20:00 line")

    from app.dota_constants import hero_npc_name

    skills(hero_id, since, hero_npc_name(hero_id))
    lineup = enemies(hero_id, since, rows)
    counters = {
        "evasion": ["monkey_king_bar", "bloodthorn", "javelin"],
        "illusions": ["butterfly", "hydras_breath", "hurricane_pike", "maelstrom", "mjollnir"],
        "healing": ["skadi", "spirit_vessel"],
        "escape": ["bloodthorn", "orchid", "abyssal_blade"],
        "break": ["silver_edge"],
        "jumpers": ["hurricane_pike", "butterfly", "black_king_bar"],
    }
    extra = [i for i in args.items.split(",") if i]
    print(
        "\ncounters by enemy group (bought: share in these games / elsewhere, win with / without):"
    )
    for group, heroes in groups().items():
        with_group = [r for r in rows if lineup[r["match_id"]] & set(heroes)]
        others = [r for r in rows if not lineup[r["match_id"]] & set(heroes)]
        if not with_group:
            continue
        print(f"  {group}: {len(with_group)} games, win {rate(with_group)}")
        for item in counters.get(group, []) + extra:
            yes = [r for r in with_group if bought(r, item)]
            no = [r for r in with_group if not bought(r, item)]
            elsewhere = sum(bought(r, item) for r in others) / max(1, len(others))
            print(
                f"    {item:18} {100 * len(yes) / len(with_group):3.0f}% / {100 * elsewhere:3.0f}%"
                f"   win {rate(yes):>4} / {rate(no):>4}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
