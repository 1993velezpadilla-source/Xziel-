#!/usr/bin/env bash
set -euo pipefail

OUT="${1:-assets/animations/zombie_mocap/quaternius_zombie_apocalypse}"
BASE="https://raw.githubusercontent.com/agentkaerf/FreeModels/main/Zombie%20Apocalypse%20Kit%20-%20March%202024"

mkdir -p "$OUT"

for model in Zombie_Basic Zombie_Chubby Zombie_Arm Zombie_Ribcage; do
  echo "Downloading $model.gltf"
  curl --fail --location --retry 4 --retry-delay 2     "$BASE/Characters/glTF/$model.gltf"     --output "$OUT/$model.gltf"
  test -s "$OUT/$model.gltf"
done

curl --fail --location --retry 4 --retry-delay 2   "$BASE/License.txt"   --output "$OUT/License.txt"
test -s "$OUT/License.txt"

python3 - "$OUT" <<'PY'
import csv, hashlib, json, pathlib, sys
out = pathlib.Path(sys.argv[1])
models = ["Zombie_Basic", "Zombie_Chubby", "Zombie_Arm", "Zombie_Ribcage"]
rows = []
for model in models:
    p = out / f"{model}.gltf"
    doc = json.loads(p.read_text(encoding="utf-8"))
    buffers = doc.get("buffers", [])
    if not buffers or not all(str(b.get("uri","")).startswith("data:") for b in buffers):
        raise SystemExit(f"{model}: expected self-contained data-URI buffers")
    for anim in doc.get("animations", []):
        name = anim.get("name") or "unnamed"
        rows.append({
            "model": model,
            "animation": name,
            "source": "Quaternius Zombie Apocalypse Kit",
            "license": "CC0-1.0",
            "file": str(p),
            "file_sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
        })

if not rows:
    raise SystemExit("No animations found")

with (out / "animation_catalog.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

semantic = {}
for r in rows:
    semantic.setdefault(r["animation"], []).append(r["model"])
with (out / "animation_variants.txt").open("w", encoding="utf-8") as f:
    for name in sorted(semantic):
        f.write(f"{name}\t{len(semantic[name])}\t{','.join(semantic[name])}\n")

print(f"Zombie Apocalypse animation incidences: {len(rows)}")
print(f"Unique semantic animation names: {len(semantic)}")
PY
