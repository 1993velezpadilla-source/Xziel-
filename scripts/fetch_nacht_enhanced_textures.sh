#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: fetch_nacht_enhanced_textures.sh <nzp-data-root>" >&2
  exit 2
fi

ROOT="$1"
OUT="$ROOT/nzp/textures/nacht_enhanced"
META="$ROOT/nzp/licenses"
mkdir -p "$OUT" "$META"

fetch() {
  local url="$1"
  local out="$2"
  echo "Nacht Enhanced texture: $out"
  curl -fL --retry 5 --retry-delay 2 --retry-all-errors "$url" -o "$OUT/$out"
  test -s "$OUT/$out"
}

# Poly Haven CC0 1K diffuse maps.  The output names intentionally match
# original ndu.bsp texture names; Vril only consults this directory when
# xziel_nacht_enhanced is enabled on maps/ndu.bsp.
fetch "https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/cracked_concrete_wall/cracked_concrete_wall_diff_1k.jpg" "nduwall.jpg"
fetch "https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/concrete_wall_003/concrete_wall_003_diff_1k.jpg" "cons5nny3.jpg"
fetch "https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/concrete_debris/concrete_debris_diff_1k.jpg" "debris_hnf3p.jpg"
fetch "https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/rubble/rubble_diff_1k.jpg" "ground_hb3.jpg"

cat > "$META/NACHT-ENHANCED-CC0-SOURCES.txt" <<'EOF'
Nacht Enhanced opt-in texture sources
=====================================

All entries below are released under CC0 by Poly Haven.

nduwall.jpg
  Source: https://polyhaven.com/a/cracked_concrete_wall
  Original: cracked_concrete_wall_diff_1k.jpg
  Authors: Dimitrios Savva, Rico Cilliers

cons5nny3.jpg
  Source: https://polyhaven.com/a/concrete_wall_003
  Original: concrete_wall_003_diff_1k.jpg

debris_hnf3p.jpg
  Source: https://polyhaven.com/a/concrete_debris
  Original: concrete_debris_diff_1k.jpg
  Author: Amal Kumar

ground_hb3.jpg
  Source: https://polyhaven.com/a/rubble
  Original: rubble_diff_1k.jpg
  Author: Amal Kumar

License: CC0 1.0
These files are only loaded by maps/ndu.bsp when xziel_nacht_enhanced != 0.
Classic Nacht continues to use the stock texture path / embedded BSP pixels.
EOF

echo "Nacht Enhanced CC0 texture pack staged in $OUT"
