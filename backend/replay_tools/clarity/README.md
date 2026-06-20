# Minimal Clarity Replay Event Helper

This helper is an offline-only Dota 2 replay event extractor. It reads a local
`.dem` file and writes JSONL events compatible with
`backend/scripts/parse_dota_demo_to_replay_events.py`.

It does not read live game memory, screen pixels, input, or the Dota process.

## Build

```bash
cd backend/replay_tools/clarity
./build.sh
```

If system `gradle` is unavailable, `build.sh` downloads Gradle into
`~/.cache/dota-ai-coach/`. The built jar is:

```text
backend/replay_tools/clarity/dota-replay-events.jar
```

The jar and Gradle build directory are ignored by git.

## Run Directly

```bash
java -jar backend/replay_tools/clarity/dota-replay-events.jar \
  --demo /path/to/replay.dem \
  --hero "Kez" \
  --player-slot 131 \
  --start 0 \
  --end 600 \
  --snapshot-interval 1 \
  --debug-entities \
  --output /tmp/replay_events.jsonl
```

## Run Through The Python Adapter

```bash
export DOTA_DEMO_PARSER_COMMAND='java -jar backend/replay_tools/clarity/dota-replay-events.jar --demo {demo} --hero {hero} --player-slot {player_slot} --start {start_seconds} --end {end_seconds} --snapshot-interval 1 --output {output}'

cd backend
source .venv/bin/activate
python scripts/parse_dota_demo_to_replay_events.py \
  --demo ../data/replays/8824199563_895334157.dem.bz2 \
  --hero "Kez" \
  --player-slot 131 \
  --start-minute 0 \
  --end-minute 10 \
  --output ../data/match_simulations/replay_events_match_8824199563_0_10.jsonl
```

## Extracted Fields

The MVP uses Clarity combat-log callbacks and selected-hero entity snapshots. It
extracts only fields that are available without guessing:

- `snapshot` events for the selected hero, approximately once per second, with
  exact HP, mana, level, alive state, position, and last-hit data when the
  relevant entities are found;
- `death` events for the selected hero;
- `purchase` events for the selected hero;
- `ability` / item-use events for the selected hero;
- `damage` and `heal` windows when the selected hero appears in the combat log;
- building `objective` events.

When current spendable gold, ability cooldowns, nearby units, or exact teamfight
context are not available from this minimal path, the helper omits those fields.
It adds `event_context` and `context_confidence` so downstream review files make
the data source clear.

Use `--debug-entities` to print whether the selected hero entity was found,
which snapshot fields were discovered, and how many snapshot events were
emitted. The helper prefers `--player-slot` through `CDOTA_PlayerResource` and
uses hero class-name matching as a fallback.

If no selected-player events are extracted, the helper exits with an error
instead of writing fake replay data.
