"""
scheduler.constants - configuration constants for the scheduler.

Extracted verbatim from advice_scheduler.py as part of the Phase 2 split
(no behavior change). The cooldown constants are derived from the UX-policy
intervals (advice_ux_policy is a leaf module; no cycle).

DEATH_REVIEW_DECISIONS is re-exported from app.advice_scheduler (rule 3)
because scripts/simulate_match_advice.py imports it from there.
"""

from __future__ import annotations

from app.advice_ux_policy import REGULAR_ADVICE_INTERVAL_SECONDS, URGENT_ADVICE_INTERVAL_SECONDS

SOFT_INTERVAL_SECONDS = REGULAR_ADVICE_INTERVAL_SECONDS
REGULAR_ADVICE_COOLDOWN_SECONDS = REGULAR_ADVICE_INTERVAL_SECONDS
URGENT_LOW_HP_COOLDOWN_SECONDS = URGENT_ADVICE_INTERVAL_SECONDS
LLM_REFINEMENT_EVERY_N_ADVICES = 3

DEATH_REVIEW_DECISIONS = {
    "DEATH_REVIEW",
    "REPEATED_DEATH_PATTERN",
    "DEATH_WITH_ESCAPE_ON_COOLDOWN",
    "DEATH_LOW_RESOURCE",
}
COACHING_GAME_TIME_GAP_SECONDS = 45
POST_LANING_GAME_TIME_GAP_SECONDS = 60
SAME_ACTION_GAME_TIME_GAP_SECONDS = 120
# The farm pace cards (post_laning_coach: the pace, the farm to recover) change
# only their numbers: the same line comes back at most this often.
FARM_PACE_REPEAT_SECONDS = 240
FARM_PACE_PREFIX = ("Keep farming: ", "Recover farm: ")
RECENT_SAFETY_GAME_TIME_GAP_SECONDS = 35
HEARTBEAT_NUDGE_SECONDS = 150
HEARTBEAT_DUPLICATE_WAIT_SECONDS = 180
