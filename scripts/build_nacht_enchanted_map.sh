#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: build_nacht_enchanted_map.sh <nzp-data-root>" >&2
  exit 2
fi

DATA_ROOT="$1"
if [ "${XZIEL_INCLUDE_NACHT_ENCHANTED:-1}" = "0" ]; then
  echo "Nacht Enchanted practice map disabled for this package."
  exit 0
fi

XZIEL_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$XZIEL_ROOT/build/nacht-enchanted-source"
SRC="$WORK/assets"
MAP_SRC="$SRC/source/maps/ndu_enchanted"
WAD_ROOT="$SRC/source/textures/wad"
TOOLS="$WORK/tools"

rm -rf "$WORK"
mkdir -p "$WORK" "$TOOLS"

echo "==> Sparse-cloning NZ:P map source and the three WAD source sets"
git clone --depth 1 --filter=blob:none --sparse https://github.com/nzp-team/assets.git "$SRC"
git -C "$SRC" sparse-checkout set   source/maps/ndu   'source/textures/wad/Ju[s]tice_null2'   source/textures/wad/zhlt   source/textures/wad/chalk_drawings

mkdir -p "$MAP_SRC"
cp "$SRC/source/maps/ndu/ndu.map" "$MAP_SRC/ndu_enchanted.map"

# The base geometry/layout remains the community NZ:P Nacht map for this
# practice derivative, but this BSP is compiled independently and receives its
# own authored lighting entities. That means we can keep pushing the map
# without mutating or aliasing the stock ndu.bsp.
cat >> "$MAP_SRC/ndu_enchanted.map" <<'EOF'

{
"classname" "light"
"origin" "1080 2368 96"
"_light" "120 70 175 105"
}
{
"classname" "light"
"origin" "1390 1780 176"
"_light" "118 126 168 82"
}
{
"classname" "light"
"origin" "1260 2360 270"
"_light" "72 100 155 78"
}
{
"classname" "light"
"origin" "1910 2520 270"
"_light" "158 98 54 70"
}
{
"classname" "light"
"origin" "1180 1800 116"
"_light" "136 88 46 62"
}
{
"classname" "light"
"origin" "687 2096 144"
"_light" "58 82 130 72"
}
EOF

echo "==> Building only the WADs required by Nacht"
WADMAKER_ZIP="$TOOLS/wadmaker.zip"
curl -fL --retry 5 --retry-delay 2 --retry-all-errors   https://github.com/pwitvoet/wadmaker/releases/download/1.3/WadMaker_1.3_linux64.zip   -o "$WADMAKER_ZIP"
mkdir -p "$TOOLS/wadmaker"
unzip -q -j "$WADMAKER_ZIP" -d "$TOOLS/wadmaker"
chmod +x "$TOOLS/wadmaker/WadMaker"

build_wad() {
  local name="$1"
  local source_dir="$WAD_ROOT/$name"
  local scratch="$WORK/wad-$RANDOM"
  mkdir -p "$scratch"
  cp -a "$source_dir/." "$scratch/"

  # NZ:P stores Quake '*' texture names with '$' in Git for Windows safety.
  find "$scratch" -depth -type f -name '*$*' -print0 | while IFS= read -r -d '' f; do
    mv -- "$f" "${f//\$/\*}"
  done

  "$TOOLS/wadmaker/WadMaker" "$scratch" "$WAD_ROOT/$name.wad" -nologfile
  test -s "$WAD_ROOT/$name.wad"
  rm -rf "$scratch"
}

build_wad 'Ju[s]tice_null2'
build_wad zhlt
build_wad chalk_drawings

echo "==> Compiling independent ndu_enchanted BSP with VHLT"
VHLT_ZIP="$TOOLS/vhlt.zip"
curl -fL --retry 5 --retry-delay 2 --retry-all-errors   https://github.com/nzp-team/vhlt/releases/download/Vanilla/vhlt-v34-linux-x86_64.zip   -o "$VHLT_ZIP"
mkdir -p "$TOOLS/vhlt"
unzip -q "$VHLT_ZIP" -d "$TOOLS/vhlt"
chmod +x "$TOOLS/vhlt/"*

(
  cd "$MAP_SRC"
  "$TOOLS/vhlt/hlcsg" -threads 8 -wadautodetect ndu_enchanted.map
  "$TOOLS/vhlt/hlbsp" -threads 8 ndu_enchanted.map
  "$TOOLS/vhlt/hlvis" -threads 8 -maxdistance 750 ndu_enchanted.bsp
  "$TOOLS/vhlt/hlrad" -threads 8 -extra ndu_enchanted.bsp
)

MAPDIR="$DATA_ROOT/nzp/maps"
mkdir -p "$MAPDIR"
cp "$MAP_SRC/ndu_enchanted.bsp" "$MAPDIR/ndu_enchanted.bsp"

for ext in way mbox mb2; do
  if [ -f "$MAPDIR/ndu.$ext" ]; then
    cp "$MAPDIR/ndu.$ext" "$MAPDIR/ndu_enchanted.$ext"
  fi
done

cat > "$MAPDIR/ndu_enchanted.txt" <<'EOF'
Nacht: Enchanted Lab
A development-only rebuilt variant
of the classic NZ:P bunker layout.
The geometry is compiled separately
with its own lighting/material pass
for Xziel horror, touch, animation
and gore experiments. The eventual
original Xziel release map will use
new geometry and original art.
Xziel
1
1
EOF

LICENSE_DIR="$DATA_ROOT/nzp/licenses"
mkdir -p "$LICENSE_DIR"
cat > "$LICENSE_DIR/NACHT-ENCHANTED-PRACTICE-MAP.txt" <<'EOF'
Nacht: Enchanted Lab
=====================

Development/reference derivative built from NZ:P's CC-BY-SA asset/map source.
It is intentionally isolated and must not ship inside the eventual original
commercial Xziel game map.

Source: https://github.com/nzp-team/assets/tree/main/source/maps/ndu
License: see the bundled NZP-ASSETS-CC-BY-SA-4.0 notice.

Set XZIEL_INCLUDE_NACHT_ENCHANTED=0 for an original-game package.
EOF

echo "Built source-derived maps/ndu_enchanted.bsp: $(stat -c '%s bytes' "$MAPDIR/ndu_enchanted.bsp")"
