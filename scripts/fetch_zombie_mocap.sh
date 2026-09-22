#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-assets/animations/zombie_mocap}"
MANIFEST="${2:-tools/zombie_mocap_manifest.tsv}"
BASE="https://huggingface.co/datasets/gbionics/cmu-fbx/resolve/main/animations"

mkdir -p "$ROOT/cmu"

tail -n +2 "$MANIFEST" | while IFS=$'\t' read -r clip_id category variant subject notes; do
  [ -n "$clip_id" ] || continue
  dest_dir="$ROOT/cmu/$category"
  dest="$dest_dir/${variant}__${clip_id}.fbx"
  mkdir -p "$dest_dir"

  echo "Downloading $clip_id -> $dest"
  curl --fail --location --retry 4 --retry-delay 2 \
    "$BASE/${clip_id}.fbx?download=true" \
    --output "$dest"

  test -s "$dest"
done

python3 - "$ROOT" "$MANIFEST" <<'PY'
import csv, hashlib, pathlib, sys
root = pathlib.Path(sys.argv[1])
manifest = pathlib.Path(sys.argv[2])
rows = []
with manifest.open(newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f, delimiter="\t"):
        p = root / "cmu" / r["category"] / f'{r["variant_label"]}__{r["clip_id"]}.fbx'
        if not p.exists():
            raise SystemExit(f"missing downloaded clip: {p}")
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        rows.append({**r, "path": str(p), "bytes": p.stat().st_size, "sha256": h,
                     "source_url": f'https://huggingface.co/datasets/gbionics/cmu-fbx/resolve/main/animations/{r["clip_id"]}.fbx'})
with (root / "catalog.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
print(f"catalogued {len(rows)} clips")
PY
