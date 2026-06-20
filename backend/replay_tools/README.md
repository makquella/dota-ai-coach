# Offline Replay Tools

These tools are for offline evaluation only. They do not run during live matches
and they do not read game memory, screen pixels, or automate input.

The output is called **GSI-like replay states** because replay-derived data is
not identical to live Dota 2 Game State Integration. Replay exports may have
better historical event coverage, but they may still lack exact player intent,
live camera context, current vision, or exact HP/mana at every second.

## A. Combat Log Export Path

The current MVP supports a simple JSONL event adapter:

```bash
cd backend
python scripts/generate_replay_event_sample.py \
  --output ../data/replay_events/synthetic_juggernaut_lane_events.jsonl

python scripts/convert_replay_events_to_gsi_like.py \
  --events-jsonl ../data/replay_events/synthetic_juggernaut_lane_events.jsonl \
  --hero "Juggernaut" \
  --player-slot 1 \
  --start-minute 0 \
  --end-minute 10 \
  --interval-seconds 1 \
  --output ../data/match_simulations/replay_gsi_like_synthetic_juggernaut_0_10.jsonl

python scripts/simulate_match_advice.py \
  --simulation-file ../data/match_simulations/replay_gsi_like_synthetic_juggernaut_0_10.jsonl
```

Expected event JSONL format:

```json
{"timestamp_seconds":125,"type":"damage","player_slot":131,"hero":"Kez","data":{"damage_percent":25,"hp_after_percent":55}}
```

Supported event types in the MVP:

- `damage`
- `death`
- `heal`
- `snapshot`
- `farm`
- `purchase`
- `level`
- `position`
- `ability`
- `objective`

If exact HP or mana is unavailable, the converter carries forward the previous
known value, marks `context_confidence`, and uses damage/death events only as
conservative danger signals. It should not be treated as exact live GSI state.

## B. Offline `.dem` Parser Adapter

`backend/scripts/parse_dota_demo_to_replay_events.py` is a safe wrapper around
an external offline parser. It can locate a local `.dem` / `.dem.bz2`, try to
download a replay from an OpenDota `replay_url`, decompress `.dem.bz2`, run the
configured parser command, then normalize the parser output into the same event
JSONL format consumed by `convert_replay_events_to_gsi_like.py`.

The repository includes a minimal Clarity helper under
`backend/replay_tools/clarity/`. It is offline-only and extracts conservative
combat-log events plus selected-hero entity snapshots when Clarity exposes exact
fields. It does not claim replay data is identical to live GSI.

Build the helper:

```bash
cd backend/replay_tools/clarity
./build.sh
```

The script uses system `gradle` when available. If Gradle is not installed, it
downloads Gradle into the user cache, not into the repository. The generated
`dota-replay-events.jar` is ignored by git.

Configure a parser command with `DOTA_DEMO_PARSER_COMMAND` or
`--parser-command`. The command must write JSONL/JSON events to `{output}` or
stdout.

Supported placeholders:

- `{demo}`
- `{output}`
- `{hero}`
- `{player_slot}`
- `{start_minute}`
- `{end_minute}`
- `{start_seconds}`
- `{end_seconds}`

Example command shape:

```bash
export DOTA_DEMO_PARSER_COMMAND='java -jar backend/replay_tools/clarity/dota-replay-events.jar --demo {demo} --hero {hero} --player-slot {player_slot} --start {start_seconds} --end {end_seconds} --snapshot-interval 1 --output {output}'
```

Minimal Clarity helper output:

- selected hero `snapshot` events, approximately once per second, with exact HP,
  mana, level, alive state, position, and last-hit data when the relevant
  entities are found;
- selected hero death events when visible in the combat log;
- selected hero purchase events;
- selected hero ability/item use events;
- selected hero damage/heal windows when visible in the combat log;
- building objective events.

Known limitations:

- exact HP/mana percent is omitted unless the selected hero entity exposes it;
- raw combat-log damage may not include enough data to calculate HP percent;
- current spendable gold and cooldowns are omitted unless exposed exactly;
- `player_slot` is supplied by the CLI and hero-name matching is used to filter
  combat-log events;
- nearby units, enemy positions, and full teamfight intent are not reconstructed.

The external parser may emit either canonical events:

```json
{"timestamp_seconds":125,"type":"damage","player_slot":131,"hero":"Kez","data":{"damage_percent":25,"hp_after_percent":55,"context_confidence":"high"}}
```

or flat events:

```json
{"timestamp_seconds":125,"event_type":"damage","player_slot":131,"hero":"Kez","damage_percent":25,"hp_percent":55,"context_confidence":"high"}
```

The wrapper normalizes flat events into canonical `type` + `data` JSONL. Missing
fields are left out. Inferred or approximate values must be labelled by the
external parser with `event_context` and `context_confidence`.

This parser path must remain offline-only:

- no live match memory reading;
- no game process hooks;
- no screen reading;
- no input automation;
- no live overlay dependency.

Keeping parser output as event JSONL lets the advice simulator stay unchanged
while allowing different replay extraction tools such as Clarity or Manta.
