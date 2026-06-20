#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GRADLE_VERSION="${GRADLE_VERSION:-8.10.2}"
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/dota-ai-coach"
GRADLE_HOME="$CACHE_DIR/gradle-$GRADLE_VERSION"
GRADLE_ZIP="$CACHE_DIR/gradle-$GRADLE_VERSION-bin.zip"

cd "$SCRIPT_DIR"

if command -v gradle >/dev/null 2>&1; then
  GRADLE_CMD=(gradle)
else
  mkdir -p "$CACHE_DIR"
  if [ ! -x "$GRADLE_HOME/bin/gradle" ]; then
    if [ ! -f "$GRADLE_ZIP" ]; then
      echo "Downloading Gradle $GRADLE_VERSION to $GRADLE_ZIP"
      curl -L --fail --show-error \
        "https://services.gradle.org/distributions/gradle-$GRADLE_VERSION-bin.zip" \
        -o "$GRADLE_ZIP"
    fi
    rm -rf "$GRADLE_HOME"
    unzip -q "$GRADLE_ZIP" -d "$CACHE_DIR"
  fi
  GRADLE_CMD=("$GRADLE_HOME/bin/gradle")
fi

"${GRADLE_CMD[@]}" --no-daemon clean build

echo "Built $SCRIPT_DIR/dota-replay-events.jar"
