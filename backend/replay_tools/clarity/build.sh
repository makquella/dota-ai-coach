#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GRADLE_VERSION="${GRADLE_VERSION:-8.10.2}"
# Checksum of the official gradle-8.10.2-bin.zip; another version needs its own.
DEFAULT_GRADLE_SHA256="31c55713e40233a8303827ceb42ca48a47267a0ad4bab9177123121e71524c26"
if [ "$GRADLE_VERSION" = "8.10.2" ]; then
  GRADLE_SHA256="${GRADLE_SHA256:-$DEFAULT_GRADLE_SHA256}"
fi
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/dota-ai-coach"
GRADLE_HOME="$CACHE_DIR/gradle-$GRADLE_VERSION"
GRADLE_ZIP="$CACHE_DIR/gradle-$GRADLE_VERSION-bin.zip"

cd "$SCRIPT_DIR"

if command -v gradle >/dev/null 2>&1; then
  GRADLE_CMD=(gradle)
else
  mkdir -p "$CACHE_DIR"
  if [ ! -x "$GRADLE_HOME/bin/gradle" ]; then
    if [ -z "${GRADLE_SHA256:-}" ]; then
      echo "Set GRADLE_SHA256 to the published checksum of Gradle $GRADLE_VERSION." >&2
      exit 1
    fi
    if [ ! -f "$GRADLE_ZIP" ]; then
      echo "Downloading Gradle $GRADLE_VERSION to $GRADLE_ZIP"
      curl -L --fail --show-error \
        "https://services.gradle.org/distributions/gradle-$GRADLE_VERSION-bin.zip" \
        -o "$GRADLE_ZIP.part"
      mv "$GRADLE_ZIP.part" "$GRADLE_ZIP"
    fi
    if ! echo "$GRADLE_SHA256  $GRADLE_ZIP" | sha256sum --check --status; then
      echo "Checksum mismatch for $GRADLE_ZIP; removed it." >&2
      rm -f "$GRADLE_ZIP"
      exit 1
    fi
    rm -rf "$GRADLE_HOME"
    unzip -q "$GRADLE_ZIP" -d "$CACHE_DIR"
  fi
  GRADLE_CMD=("$GRADLE_HOME/bin/gradle")
fi

"${GRADLE_CMD[@]}" --no-daemon clean build

echo "Built $SCRIPT_DIR/dota-replay-events.jar"
