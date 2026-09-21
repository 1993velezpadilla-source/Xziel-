#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: fetch_nacht_enhanced_textures.sh <nzp-data-root>" >&2
  exit 2
fi

ROOT="$1"
OUT="$ROOT/nzp/textures/nacht_enhanced"
META="$ROOT/nzp/licenses"
CACHE="$OUT/.sources"
mkdir -p "$OUT" "$META" "$CACHE"

fetch_source() {
  local slug="$1"
  local out="$2"
  local url="https://dl.polyhaven.org/file/ph-assets/Textures/jpg/2k/$slug/${slug}_diff_2k.jpg"
  echo "Nacht Enchanted 2K material: $slug"
  curl -fL --retry 5 --retry-delay 2 --retry-all-errors "$url" -o "$CACHE/$out"
  test -s "$CACHE/$out"
}

alias_tex() {
  local source="$1"
  shift
  for name in "$@"; do
    cp "$CACHE/$source" "$OUT/$name.jpg"
  done
}

# High-detail external diffuse maps. We keep authored source quality high and
# let Vril/OpenGL mip/filter policy handle runtime distance rather than baking
# the entire map down to old WAD resolution.
fetch_source "cracked_concrete_wall" "wall.jpg"
fetch_source "worn_plaster_wall" "plaster.jpg"
fetch_source "concrete_debris" "debris.jpg"
fetch_source "concrete_floor" "floor.jpg"
fetch_source "concrete_floor_01" "tile.jpg"
fetch_source "rusty_metal_sheet" "metal_sheet.jpg"
fetch_source "rusty_metal_02" "metal_blue.jpg"
fetch_source "rusty_metal" "metal_door.jpg"
fetch_source "rusty_painted_metal" "metal_painted.jpg"
fetch_source "weathered_planks" "wood_dark.jpg"
fetch_source "medieval_wood" "wood_structural.jpg"
fetch_source "wood_planks" "wood_board.jpg"

# Opaque surfaces that cover almost all visible bunker geometry.
# Vril uses the BSP texture token verbatim when probing external files.
# Android/Linux filesystems are case-sensitive, and the original map contains
# both uppercase and mixed-case spellings. Ship explicit aliases so the real
# renderer cannot silently fall back to the embedded low-resolution WAD art.
alias_tex wall.jpg nduwall NDUWALL NDUWall
alias_tex plaster.jpg cons5nny3 CONS5NNY3 conS5NNY3
alias_tex debris.jpg debris_hnf3p DEBRIS_HNF3P debris_HNf3P
alias_tex floor.jpg ground_hb3 GROUND_HB3
alias_tex tile.jpg 3tiles_grey_64 3TILES_GREY_64
alias_tex metal_sheet.jpg doorway_met DOORWAY_MET
alias_tex metal_blue.jpg m_metal_darkblu M_METAL_DARKBLU m_metal_darkBlu
alias_tex wood_dark.jpg w_wood_brown_re W_WOOD_BROWN_RE box_side_o BOX_SIDE_O
alias_tex wood_structural.jpg w_s_wooden_b64 W_S_WOODEN_B64
alias_tex wood_board.jpg board_fe BOARD_FE
alias_tex metal_door.jpg ndu_doors_64 NDU_DOORS_64
alias_tex metal_painted.jpg m_cupb_front M_CUPB_FRONT

rm -rf "$CACHE"

cat > "$META/NACHT-ENHANCED-CC0-SOURCES.txt" <<'EOF'
Nacht Enchanted external material sources
=========================================

All materials below are Poly Haven CC0 assets. The Enchanted practice build
uses 2K diffuse maps as external Vril textures instead of intentionally
reducing source quality to legacy Quake texture resolution.

cracked_concrete_wall -> NDUWALL
worn_plaster_wall -> CONS5NNY3
concrete_debris -> DEBRIS_HNF3P
concrete_floor -> GROUND_HB3
concrete_floor_01 -> 3TILES_GREY_64
rusty_metal_sheet -> DOORWAY_MET
rusty_metal_02 -> M_METAL_DARKBLU
rusty_metal -> NDU_DOORS_64
rusty_painted_metal -> M_CUPB_FRONT
weathered_planks -> W_WOOD_BROWN_RE, BOX_SIDE_O
medieval_wood -> W_S_WOODEN_B64
wood_planks -> BOARD_FE

Source pages:
https://polyhaven.com/a/cracked_concrete_wall
https://polyhaven.com/a/worn_plaster_wall
https://polyhaven.com/a/concrete_debris
https://polyhaven.com/a/concrete_floor
https://polyhaven.com/a/concrete_floor_01
https://polyhaven.com/a/rusty_metal_sheet
https://polyhaven.com/a/rusty_metal_02
https://polyhaven.com/a/rusty_metal
https://polyhaven.com/a/rusty_painted_metal
https://polyhaven.com/a/weathered_planks
https://polyhaven.com/a/medieval_wood
https://polyhaven.com/a/wood_planks

License: CC0 1.0
EOF

echo "Nacht Enchanted full opaque-surface material pass staged in $OUT"
