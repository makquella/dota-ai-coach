# Pure ability normalization (0.53.43)

`ability_normalization.py` owns the existing ability name map, normalization and
Dota Plus exclusions. `gsi_values.py` owns existing scalar conversion and token
labels. Both depend only on the standard library. `skill_build.label` imports the
normalizer directly, removing its delayed reverse import of `gsi_state` and the
GSI → skill tips → skill build → GSI cycle.

GSI retains its public `normalize_abilities` wrapper and legacy scalar names;
skill tips re-export `not_hero_ability` and its prefixes. Existing raw-name,
level/cooldown/can-cast handling, zero/false, bounded nonfinite values, aliases,
deduplication, ordered dictionary input and fallback labels remain unchanged.
The skill tracker keeps its own slot-order/point-counting logic. No advice policy,
safety gate, cache/rule version or observed-signal semantics changed.

Four new functional checks cover fresh subprocess import orders, pure labeling
without loading GSI/trackers, actual HTTP GSI normalization and overlay consumers,
legacy exports, detached rows and numeric bounds. Existing skill, GSI, safety and
scheduler tests validate consuming behavior. Both pure modules are strict-mypy
clean and join the whole-app clean-module gate.

The sole F841 allowance is removed globally. Scheduler observation still calls
`_game_time_seconds_locked`: that call establishes game-clock state. Only its
unused assignment is removed, preserving the state transition. Intentional SIM
exceptions remain as documented; no automatic unsafe lint fix is used.
