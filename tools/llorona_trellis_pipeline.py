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

# Use local files so gradio_client uploads them exactly as Gallery/Image inputs expect.
# The old URL-shaped payload bypassed Gradio's upload preprocessing and caused the Space
# to receive invalid Gallery items.
front = handle_file(str(REFS[0]))
gallery = [{"image": handle_file(str(p)), "caption": None} for p in REFS]

# First try the Space's own background-removal/centering pass. If that endpoint is
# unavailable, generation still gets the original views rather than aborting.
pre = find_endpoint("preprocess_images")
if pre:
    print("Preprocessing multi-view references via TRELLIS...")
    try:
        if pre[0] == "api_name":
            processed = client.predict(gallery, api_name=pre[1])
        else:
            processed = client.predict(gallery, fn_index=pre[1])
        print("preprocess result:", repr(processed)[:2000])
        if processed:
            gallery = processed
            # Give the required single-image parameter a valid image even though
            # generate_and_extract_glb ignores it while is_multiimage=True.
            first = gallery[0]
            if isinstance(first, dict) and "image" in first:
                front = first["image"]
            elif isinstance(first, dict) and ("path" in first or "url" in first):
                front = first
            elif isinstance(first, str):
                front = handle_file(first)
    except Exception as e:
        print(f"::warning::TRELLIS preprocess endpoint failed; continuing with uploaded refs: {e}")

gen = find_endpoint("generate_and_extract_glb")
if not gen:
    gen = ("api_name", "/generate_and_extract_glb")

# Build arguments by the current live API parameter names. The community Space added
# is_multiimage to this endpoint; omitting it shifted every later argument by one.
named = api.get("named_endpoints", {}).get("/generate_and_extract_glb", {})
param_names = [p.get("parameter_name") for p in named.get("parameters", [])]
print("TRELLIS generate parameters:", param_names)

values = {
    "image": front,
    "multiimages": gallery,
    "is_multiimage": True,
    "seed": 1993,
    "ss_guidance_strength": 7.5,
    "ss_sampling_steps": 12,
    "slat_guidance_strength": 3.0,
    "slat_sampling_steps": 12,
    "multiimage_algo": "multidiffusion",
    "mesh_simplify": 0.95,
    "texture_size": 2048,
}

if param_names:
    missing = [p for p in param_names if p not in values]
    if missing:
        fail(f"Unhandled TRELLIS API parameters: {missing}")
    args = [values[p] for p in param_names]
else:
    # Current Space contract as of this pipeline.
    args = [
        front, gallery, True, 1993, 7.5, 12, 3.0, 12,
        "multidiffusion", 0.95, 2048,
    ]

print(f"Calling TRELLIS generator via {gen[0]}={gen[1]} with {len(args)} args")
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
