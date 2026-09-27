# Evaluation results

Generated 2026-09-27T02:10:39+00:00 by `backend/scripts/evaluate_system.py` (commit 242bd23, Python 3.11.15, Linux-6.18.44-fc-v42-x86_64-with-glibc2.39). How each number is measured: see the docstring of that script.

## 1. Live pipeline latency

1971 raw GSI payloads (a 32-minute match, one per game second, after 10 warm-up ticks), in-process, ms:

| step | n | mean_ms | p50_ms | p95_ms | p99_ms | max_ms |
|---|---|---|---|---|---|---|
| POST /gsi | 1971 | 2.96 | 2.91 | 3.52 | 3.87 | 7.76 |
| GET /overlay/recommendation | 1971 | 4.01 | 4.25 | 4.93 | 5.36 | 25.4 |
| one tick (both) | 1971 | 6.97 | 7.14 | 8.15 | 8.72 | 28.42 |

The POST_GAME payload, which records the match and builds its review: 9.7 ms.

## 2. Live advice on real replays (simulated clock)

| match | states | minutes | advice_shown | advice_per_10_min | urgent | coaching | min_gap_s | suppressed_total | p95_ms |
|---|---|---|---|---|---|---|---|---|---|
| Phantom Lancer 20-30 min (match 8843382732) | 601 | 10.0 | 7 | 7.0 | 1 | 6 | 9.0 | 752 | 5.0 |
| Juggernaut 10-20 min (match 8843471434) | 601 | 10.0 | 11 | 11.0 | 3 | 8 | 4.0 | 714 | 4.9 |

**Phantom Lancer 20-30 min (match 8843382732)** — decision points: FARMING_PHASE_PRESSURE ×4, OBJECTIVE_FIGHT_CHECK ×1, RECENT_DAMAGE_WARNING ×1, LOW_HP ×1

Suppressed by the scheduler: duplicate_suppressed_count 338, repeated_post_laning_suppressed_count 303, repeated_objective_suppressed_count 16, post_laning_safety_suppressed_count 95

First advice shown:

- 20:00 (coaching): Recover farm through the safest wave-and-camp route.
- 20:45 (coaching): Avoid the pressured lane and farm a safer wave or nearby camp.
- 21:55 (coaching): Only consider the objective if your team is already grouped nearby.
- 24:25 (coaching): Avoid the pressured lane and farm a safer wave or nearby camp.

**Juggernaut 10-20 min (match 8843471434)** — decision points: LOW_HP ×4, LANING_FARM_CHECK ×2, FARMING_PHASE_PRESSURE ×2, RECENT_DAMAGE_WARNING ×1, LOW_MANA ×1, REPEATED_DEATH_PATTERN ×1

Suppressed by the scheduler: duplicate_suppressed_count 306, repeated_post_laning_suppressed_count 175, repeated_objective_suppressed_count 51, post_laning_safety_suppressed_count 141, death_route_suppressed_count 12, repeated_low_hp_suppressed_count 29

First advice shown:

- 10:00 (coaching): Recover farm through the safest wave-and-camp route.
- 10:45 (coaching): Avoid the pressured lane and farm a safer wave or nearby camp.
- 12:18 (coaching): Back up and stabilize before trading again.
- 12:22 (urgent): Reset HP before showing on another lane.

## 3. Post-match review

| source | score | sections | improvements | strengths | blocks | series | build_ms |
|---|---|---|---|---|---|---|---|
| OpenDota, parsed replay | 31 | farm, fights, items, laning, survival | 6 | 0 | build, peers, draft | deaths, denies, gold, last_hits, last_hits_target, minutes, xp | 6.4 |
| OpenDota, basic (not parsed) | 29 | farm, fights, survival | 3 | 0 | peers, draft | — | 5.0 |
| GSI only (the app's own recording) | 89 | farm, fights, items, laning, survival | 2 | 4 | map | deaths, denies, gold, last_hits, last_hits_target, minutes | 8.1 |

Career over 26 matches (12 reviewed): focus plan 3 items, best-vs-worst comparison: True, built in 9.7 ms.

## 4. AI coach fact check

Clean sentences kept: 68 of 68.

| changed fact | n | caught | rate |
|---|---|---|---|
| hero | 16 | 16 | 1.0 |
| item | 8 | 8 | 1.0 |
| number | 52 | 52 | 1.0 |
| small count 2-12 | 52 | 0 | 0.0 |
| time | 42 | 42 | 1.0 |

