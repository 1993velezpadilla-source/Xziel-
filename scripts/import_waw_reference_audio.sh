#!/usr/bin/env bash
set -euo pipefail

# Optional local-only import for classic World at War Zombies reference audio.
# No copyrighted audio is downloaded by this script and no audio bytes are
# committed to the repository. Set XZIEL_WAW_AUDIO_DIR to a directory that
# contains files you are authorized to use.
if [ "$#" -ne 1 ]; then
  echo "usage: import_waw_reference_audio.sh <nzp-data-root>" >&2
  exit 2
fi

ROOT="$1"
SRC="${XZIEL_WAW_AUDIO_DIR:-}"
DEST="$ROOT/nzp/sounds/xziel/waw"
META="$ROOT/nzp/licenses"

mkdir -p "$DEST" "$META"

cat > "$META/XZIEL-WAW-REFERENCE-AUDIO.txt" <<'EOF'
Classic World at War Zombies audio integration
===============================================

This build system can optionally import locally supplied classic WaW Zombies
audio into sounds/xziel/waw. The Xziel repository does not distribute those
audio files.

Known original aliases/events documented by public WaW modding references:
- mx_game_over  -> classic end-of-game music/sting
- round_over    -> end_of_round
- chalk         -> chalk_one_up
- WAVE_1        -> initial zombie wave presentation context

If local files are absent, the game falls back to NZ:P's stock sounds.
EOF

if [ -z "$SRC" ]; then
  echo "XZIEL_WAW_AUDIO_DIR not set; using redistributable NZ:P fallback audio."
  exit 0
fi

if [ ! -d "$SRC" ]; then
  echo "XZIEL_WAW_AUDIO_DIR does not exist: $SRC" >&2
  exit 1
fi

copy_optional() {
  local name="$1"
  if [ -f "$SRC/$name" ]; then
    cp "$SRC/$name" "$DEST/$name"
    echo "Imported local WaW reference audio: $name"
  else
    echo "Optional local WaW audio missing: $name"
  fi
}

copy_optional "waw_game_over.wav"
copy_optional "waw_round_start_laugh.wav"
copy_optional "waw_chalk.wav"
copy_optional "waw_round_over.wav"

# Record only hashes/filenames in the packaged license metadata.
{
  echo
  echo "Locally imported files:"
  for f in "$DEST"/*.wav; do
    [ -e "$f" ] || continue
    sha256sum "$f" | sed "s#  $DEST/#  #"
  done
} >> "$META/XZIEL-WAW-REFERENCE-AUDIO.txt"
