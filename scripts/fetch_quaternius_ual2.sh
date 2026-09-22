#!/usr/bin/env bash
set -euo pipefail

OUT="${1:-assets/animations/zombie_mocap/quaternius_ual2}"
BASE="https://raw.githubusercontent.com/agentkaerf/FreeModels/main/Universal%20Animation%20Library%202%5BStandard%5D"

mkdir -p "$OUT"

curl --fail --location --retry 4 --retry-delay 2   "$BASE/Unreal-Godot/UAL2_Standard.glb"   --output "$OUT/UAL2_Standard.glb"

curl --fail --location --retry 4 --retry-delay 2   "$BASE/License.txt"   --output "$OUT/License.txt"

test -s "$OUT/UAL2_Standard.glb"
test -s "$OUT/License.txt"

python3 - "$OUT/UAL2_Standard.glb" "$OUT/animation_names.txt" "$OUT/zombie_animation_names.txt" <<'PY'
import json, pathlib, struct, sys
src = pathlib.Path(sys.argv[1])
all_out = pathlib.Path(sys.argv[2])
z_out = pathlib.Path(sys.argv[3])
b = src.read_bytes()
if b[:4] != b'glTF':
    raise SystemExit("not a GLB")
version, total = struct.unpack_from("<II", b, 4)
if version != 2 or total != len(b):
    raise SystemExit(f"unexpected GLB header version={version} total={total} actual={len(b)}")
pos = 12
doc = None
while pos + 8 <= len(b):
    n, typ = struct.unpack_from("<II", b, pos)
    pos += 8
    chunk = b[pos:pos+n]
    pos += n
    if typ == 0x4E4F534A:
        doc = json.loads(chunk.decode("utf-8").rstrip(" \t\r\n\x00"))
        break
if doc is None:
    raise SystemExit("GLB JSON chunk missing")
names = [a.get("name") or f"animation_{i:03d}" for i, a in enumerate(doc.get("animations", []))]
all_out.write_text("\n".join(names) + "\n", encoding="utf-8")
z = [n for n in names if any(k in n.lower() for k in ("zombie", "infected", "undead"))]
z_out.write_text("\n".join(z) + ("\n" if z else ""), encoding="utf-8")
print(f"UAL2 animations: {len(names)}; zombie-labelled: {len(z)}")
PY
