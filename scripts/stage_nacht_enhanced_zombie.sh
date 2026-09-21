#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: stage_nacht_enhanced_zombie.sh <asset-work-root>" >&2
  exit 2
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ASSET_WORK="$1"
SRC="$ROOT/assets/nacht_enhanced/models/librequake"
DEST="$ASSET_WORK/nzp/models/xziel/nacht"
LIC="$ASSET_WORK/nzp/licenses"

mkdir -p "$DEST" "$LIC"
cp "$SRC/zombie.mdl" "$DEST/zombie_lq.mdl"

# Vril's SDL Alias loader looks for <model>.mdl_0.tga before using the
# embedded paletted skin. Preserve the legal source texture at full 256x128.
python3 - "$SRC/zombie.png" "$DEST/zombie_lq.mdl_0.tga" <<'PY'
from pathlib import Path
from PIL import Image
import sys
src = Path(sys.argv[1])
dst = Path(sys.argv[2])
im = Image.open(src).convert("RGB")
im.save(dst, format="TGA")
print(f"staged Nacht replacement zombie texture: {im.size[0]}x{im.size[1]}")
PY

cp "$SRC/COPYING.txt" "$LIC/LIBREQUAKE-BSD-3-CLAUSE.txt"
cp "$SRC/CREDITS.txt" "$LIC/LIBREQUAKE-CREDITS.txt"
cp "$SRC/SOURCE.txt" "$LIC/XZIEL-NACHT-ZOMBIE-SOURCE.txt"

python3 - "$DEST/zombie_lq.mdl" <<'PY'
from pathlib import Path
import struct
import sys
p = Path(sys.argv[1])
b = p.read_bytes()
if len(b) < 84:
    raise SystemExit("replacement zombie MDL is truncated")
ident, version = struct.unpack_from("<II", b, 0)
numskins, skinwidth, skinheight, numverts, numtris, numframes = struct.unpack_from("<IIIIII", b, 48)
if ident != 0x4F504449:
    raise SystemExit(f"unexpected MDL ident: 0x{ident:08x}")
if version != 6:
    raise SystemExit(f"unexpected MDL version: {version}")
if numverts <= 0 or numverts > 2000:
    raise SystemExit(f"Vril alias vertex budget violated: {numverts}")
if numframes < 211:
    raise SystemExit(f"replacement zombie has too few animation frames: {numframes}")
if numskins < 1 or skinwidth <= 0 or skinheight <= 0:
    raise SystemExit("replacement zombie has invalid skin metadata")
print(f"validated Nacht zombie MDL: verts={numverts} tris={numtris} frames={numframes} skin={skinwidth}x{skinheight}")
PY
