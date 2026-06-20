# Fallback vs Local LLM Simulation Comparison

## Scenario

- fallback report: `/home/artem/Study/CourseWork/dota-ai-coach/backend/simulation_results/match_advice_simulation_20260601_215643.json`
- local LLM report: `/home/artem/Study/CourseWork/dota-ai-coach/backend/simulation_results/match_advice_simulation_20260601_214858.json`
- source_type: `replay_gsi_like`
- duration: `10` minutes
- states processed: `601`
- context confidence distribution: `{"high": 404, "medium": 197}`

## Summary Table

| Metric | Fallback-only | Local LLM blocking | Comment |
|---|---:|---:|---|
| source_type | replay_gsi_like | replay_gsi_like |  |
| duration_minutes | 10 | 10 |  |
| total_states_processed | 601 | 601 |  |
| states_per_minute | 60.1 | 60.1 |  |
| total_advice_shown | 10 | 10 | Same frequency; scheduler controlled volume. |
| advice_per_minute | 1 | 1 | Useful for overload check. |
| fits_duration_target | yes | yes | Pass/fail against expected hints for this replay duration. |
| active_advice_count | 103 | 103 |  |
| monitoring_count | 380 | 380 |  |
| pinned_advice_count | 75 | 75 |  |
| repeated_advice_suppressed_count | 123 | 123 |  |
| urgent_advice_count | 2 | 2 |  |
| coaching_advice_count | 8 | 8 |  |
| fallback_count | 10 | 10 | Fallback remains the baseline safety layer. |
| llm_count | 0 | 6 |  |
| llm_applied_count | 0 | 5 | How many full advice events used LLM wording. |
| llm_applied_rate | 0.0% | 83.3% |  |
| llm_skipped_by_policy_count | 0 | 4 | Safety skips for urgent/death/status-like advice. |
| llm_timeout_count | 0 | 0 | Should stay low for stable offline comparison. |
| llm_invalid_count | 0 | 1 | Should stay low for stable offline comparison. |
| stale_response_count | 0 | 0 | Should stay low for stable offline comparison. |
| average_latency | 0.000s | 1.508s | LLM latency cost; fallback should stay near zero. |
| p95_latency | 0.000s | 1.720s | LLM latency cost; fallback should stay near zero. |
| decision_points | {"ABILITY_SAFETY_COOLDOWN": 30, "BAD_FIGHT_RISK": 5, "DEATH_LOW_RESOURCE": 22, "LANING_FARM_CHECK": 54, "LOW_HP": 32, "LOW_HP_WARNING": 31, "RECENT_DAMAGE_WARNING": 22, "REPEATED_DEATH_PATTERN": 25, "SOFT_STATUS": 380} | {"ABILITY_SAFETY_COOLDOWN": 30, "BAD_FIGHT_RISK": 5, "DEATH_LOW_RESOURCE": 22, "LANING_FARM_CHECK": 54, "LOW_HP": 32, "LOW_HP_WARNING": 31, "RECENT_DAMAGE_WARNING": 22, "REPEATED_DEATH_PATTERN": 25, "SOFT_STATUS": 380} | See distribution below. |

## Decision Point Distribution

### Fallback-only

| Decision point | Count |
|---|---:|
| SOFT_STATUS | 380 |
| LANING_FARM_CHECK | 54 |
| LOW_HP | 32 |
| LOW_HP_WARNING | 31 |
| ABILITY_SAFETY_COOLDOWN | 30 |
| REPEATED_DEATH_PATTERN | 25 |
| DEATH_LOW_RESOURCE | 22 |
| RECENT_DAMAGE_WARNING | 22 |
| BAD_FIGHT_RISK | 5 |

### Local LLM blocking

| Decision point | Count |
|---|---:|
| SOFT_STATUS | 380 |
| LANING_FARM_CHECK | 54 |
| LOW_HP | 32 |
| LOW_HP_WARNING | 31 |
| ABILITY_SAFETY_COOLDOWN | 30 |
| REPEATED_DEATH_PATTERN | 25 |
| DEATH_LOW_RESOURCE | 22 |
| RECENT_DAMAGE_WARNING | 22 |
| BAD_FIGHT_RISK | 5 |

## Interpretation

- Advice frequency was controlled by the local policy and scheduler; the LLM did not increase hint volume.
- Blocking mode successfully applied LLM responses offline without stale-response losses.
- The local LLM can improve wording at the cost of added per-advice latency.
- Some advice remained fallback-first by policy, especially urgent low-HP, death review, or status-safe cases.
- Priority and time_window remain controlled by local advice_policy, even when LLM wording is applied.

_Generated at 2026-06-01T21:56:54.638332+00:00._
