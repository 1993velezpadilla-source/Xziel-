#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: stage_nacht_enchanted_map.sh <nzp-data-root>" >&2
  exit 2
fi

ROOT="$1"
if [ "${XZIEL_INCLUDE_NACHT_ENCHANTED:-1}" = "0" ]; then
  echo "Nacht Enchanted practice map disabled for this package."
  exit 0
fi

SRC_BSP="$(find "$ROOT" -type f -path '*/maps/ndu.bsp' -print -quit)"
if [ -z "$SRC_BSP" ]; then
  echo "Could not locate stock ndu.bsp in staged NZ:P data" >&2
  exit 1
fi

MAPDIR="$(dirname "$SRC_BSP")"
cp "$SRC_BSP" "$MAPDIR/ndu_enchanted.bsp"

for ext in way mbox mb2; do
  if [ -f "$MAPDIR/ndu.$ext" ]; then
    cp "$MAPDIR/ndu.$ext" "$MAPDIR/ndu_enchanted.$ext"
  fi
done

cat > "$MAPDIR/ndu_enchanted.txt" <<'EOF'
Nacht: Enchanted Lab
Training build: the classic bunker
layout is duplicated as a separate
playable map so Xziel can practice
modern materials, lighting, audio,
FX, animation and gore without
mutating stock Nacht. This derivative
practice map is excluded from the
future original-game public release.
Xziel
1
1
EOF

while IFS= read -r preview; do
  [ -n "$preview" ] || continue
  dir="$(dirname "$preview")"
  ext="${preview##*.}"
  cp "$preview" "$dir/ndu_enchanted.$ext"
done < <(find "$ROOT" -type f \( -path '*/gfx/menu/custom/ndu.png' -o -path '*/gfx/menu/custom/ndu.tga' -o -path '*/gfx/lscreen/ndu.png' -o -path '*/gfx/lscreen/ndu.tga' \))

LICENSE_DIR="$ROOT/nzp/licenses"
mkdir -p "$LICENSE_DIR"
cat > "$LICENSE_DIR/NACHT-ENCHANTED-PRACTICE-MAP.txt" <<'EOF'
Nacht: Enchanted Lab
=====================

This development-only map is a separate runtime copy of the NZ:P Nacht der
Untoten map data used to practice Xziel's Quake/Vril presentation pipeline.
The original NZ:P asset package remains under its bundled license notice.

XZIEL_INCLUDE_NACHT_ENCHANTED=0 removes this derivative practice map from a
future original/public Xziel package. The long-term original map should carry
forward pacing and atmosphere lessons, not copyrighted map geometry/art/audio.
EOF

echo "Staged maps/ndu_enchanted.bsp and matching gameplay metadata."
