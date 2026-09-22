#!/usr/bin/env python3
from __future__ import annotations
import json, os, shutil, sys
from pathlib import Path
from gradio_client import Client, handle_file

SPACE = os.environ.get("TRELLIS_SPACE", "trellis-community/TRELLIS")
REF_DIR = Path("assets/characters/llorona/reference")
OUT_DIR = Path("out/llorona-trellis")
REFS = [REF_DIR / n for n in ("front.jpg","left.jpg","back.jpg","right.jpg")]

def fail(msg):
    print(f"::error::{msg}")
    raise SystemExit(1)

for p in REFS:
    if not p.is_file():
        fail(f"Missing reference: {p}")

OUT_DIR.mkdir(parents=True, exist_ok=True)
token = os.environ.get("HF_TOKEN", "").strip() or None
print(f"Connecting to public TRELLIS Space: {SPACE} (authenticated={bool(token)})")
client = Client(SPACE, hf_token=token, verbose=True) if token else Client(SPACE, verbose=True)

api = client.view_api(print_info=False, return_format="dict")
(OUT_DIR/"api-info.json").write_text(json.dumps(api, indent=2), encoding="utf-8")

def find_endpoint(fragment: str):
    named = api.get("named_endpoints", {})
    for name in named:
        if fragment in name:
            return ("api_name", name)
    unnamed = api.get("unnamed_endpoints", {})
    for idx, info in unnamed.items():
        blob = json.dumps(info).lower()
        if fragment.lower().replace("_"," ") in blob or fragment.lower() in blob:
            return ("fn_index", int(idx))
    return None

gallery = [(handle_file(str(p)), None) for p in REFS]
front = handle_file(str(REFS[0]))

pre = find_endpoint("preprocess_images")
if pre:
    print("Preprocessing multi-view references via TRELLIS...")
    try:
        if pre[0] == "api_name":
            processed = client.predict(gallery, api_name=pre[1])
        else:
            processed = client.predict(gallery, fn_index=pre[1])
        if processed:
            gallery = processed
    except Exception as e:
        print(f"::warning::TRELLIS preprocess endpoint failed; continuing with original refs: {e}")

gen = find_endpoint("generate_and_extract_glb")
if not gen:
    # Current public Space normally exposes this endpoint; keep a direct fallback.
    gen = ("api_name", "/generate_and_extract_glb")

print(f"Calling TRELLIS generator via {gen[0]}={gen[1]}")
args = [
    front,
    gallery,
    True,       # multi-image mode
    1993,       # deterministic seed
    7.5, 12,    # sparse guidance / steps
    3.0, 12,    # structured guidance / steps
    "stochastic",
    0.95,       # simplify
    2048,       # texture size
]

try:
    if gen[0] == "api_name":
        result = client.predict(*args, api_name=gen[1])
    else:
        result = client.predict(*args, fn_index=gen[1])
except Exception as e:
    fail(f"TRELLIS generation failed: {type(e).__name__}: {e}")

print("TRELLIS returned result types:", [type(x).__name__ for x in result] if isinstance(result, tuple) else type(result).__name__)
(OUT_DIR/"result.txt").write_text(repr(result), encoding="utf-8")

candidates = []
if isinstance(result, (list, tuple)):
    for item in result:
        if isinstance(item, str) and item.lower().endswith(".glb"):
            candidates.append(Path(item))
        elif isinstance(item, dict):
            for k in ("path","url"):
                v = item.get(k)
                if isinstance(v, str) and v.lower().endswith(".glb"):
                    candidates.append(Path(v))
elif isinstance(result, str) and result.lower().endswith(".glb"):
    candidates.append(Path(result))

glb = next((p for p in reversed(candidates) if p.exists()), None)
if glb is None:
    fail(f"No downloaded GLB found in TRELLIS result: {result!r}")

dst = OUT_DIR / "llorona_trellis_multiview.glb"
shutil.copy2(glb, dst)
if dst.read_bytes()[:4] != b"glTF":
    fail("TRELLIS output does not have GLB magic")
if dst.stat().st_size < 1024:
    fail("TRELLIS GLB is unexpectedly small")

# copy video preview if returned
if isinstance(result, (list, tuple)):
    for item in result:
        if isinstance(item, str) and item.lower().endswith((".mp4",".webm")) and Path(item).exists():
            shutil.copy2(item, OUT_DIR / ("preview" + Path(item).suffix))
            break

manifest = {
    "asset": "La Llorona",
    "generator": "trellis-community/TRELLIS",
    "source_views": [p.name for p in REFS],
    "multi_image": True,
    "seed": 1993,
    "mesh_simplify": 0.95,
    "texture_size": 2048,
    "glb": dst.name,
    "glb_bytes": dst.stat().st_size,
    "authenticated_hf": bool(token),
}
(OUT_DIR/"manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print("XZIEL_LLORONA_TRELLIS_GLB_READY")
print(json.dumps(manifest, indent=2))
