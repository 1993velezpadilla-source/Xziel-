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
space_url = os.environ.get("TRELLIS_URL", "https://trellis-community-trellis.hf.space")
print(f"Connecting to public TRELLIS Space: {space_url} (authenticated={bool(token)})")

# ZeroGPU can be slow to wake. The default httpx timeout is too short for /config.
# Use the direct Space URL and retry instead of failing the whole GitHub job.
import time
last_err = None
client = None
for attempt in range(1, 6):
    try:
        kwargs = dict(verbose=True, httpx_kwargs={"timeout": 120.0})
        if token:
            kwargs["token"] = token
        client = Client(space_url, **kwargs)
        print(f"TRELLIS client connected on attempt {attempt}")
        break
    except Exception as e:
        last_err = e
        print(f"::warning::TRELLIS connect attempt {attempt}/5 failed: {type(e).__name__}: {e}")
        if attempt < 5:
            time.sleep(15 * attempt)
if client is None:
    fail(f"Unable to connect to TRELLIS after retries: {last_err}")

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

# Reproduce the Gradio UI sequence exactly:
# 1) demo.load -> start_session (creates tmp/<session_hash>)
# 2) select Multiple Images tab -> /lambda_1 (sets hidden gr.State True)
# 3) preprocess each view as an Image input
# 4) call generate_and_extract_glb; Gradio injects the hidden state automatically.
print("Starting TRELLIS session...")
try:
    client.predict(api_name="/start_session")
except Exception as e:
    print(f"::warning::start_session returned {type(e).__name__}: {e}")

print("Selecting TRELLIS Multiple Images mode...")
try:
    client.predict(api_name="/lambda_1")
    print("TRELLIS_MULTIIMAGE_STATE_ENABLED")
except Exception as e:
    fail(f"Could not enable TRELLIS multi-image state: {type(e).__name__}: {e}")

def as_uploadable(value):
    # gradio_client outputs may be a local downloaded filepath, a FileData-like dict,
    # or (less commonly) a raw string path. Normalize to something accepted as input.
    if isinstance(value, str):
        p = Path(value)
        return handle_file(str(p)) if p.exists() else value
    if isinstance(value, dict):
        p = value.get("path")
        if isinstance(p, str) and Path(p).exists():
            return handle_file(p)
        return value
    return value

print("Preprocessing four orthographic views individually...")
processed = []
for p in REFS:
    try:
        out = client.predict(handle_file(str(p)), api_name="/preprocess_image")
        print(f"preprocessed {p.name}: {type(out).__name__}")
        processed.append(as_uploadable(out))
    except Exception as e:
        fail(f"TRELLIS preprocess_image failed for {p.name}: {type(e).__name__}: {e}")

front = processed[0]
gallery = [{"image": item, "caption": None} for item in processed]

gen = find_endpoint("generate_and_extract_glb")
if not gen:
    gen = ("api_name", "/generate_and_extract_glb")

named = api.get("named_endpoints", {}).get("/generate_and_extract_glb", {})
param_names = [p.get("parameter_name") for p in named.get("parameters", [])]
print("TRELLIS public generate parameters:", param_names)

# is_multiimage is intentionally absent here because it is a gr.State, not a public
# parameter. /lambda_1 above set that hidden state to True in this Client session.
values = {
    "image": front,
    "multiimages": gallery,
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
    args = [
        front, gallery, 1993, 7.5, 12, 3.0, 12,
        "multidiffusion", 0.95, 2048,
    ]

print(f"Calling TRELLIS generator via {gen[0]}={gen[1]} with hidden multi-image state=True")
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
