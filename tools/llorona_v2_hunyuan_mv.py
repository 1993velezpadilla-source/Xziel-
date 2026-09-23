#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path

from gradio_client import Client, handle_file
from PIL import Image

SPACE_URL = os.environ.get("HUNYUAN_URL", "https://tencent-hunyuan3d-2mv.hf.space")
REF_ROOT = Path("assets/characters/llorona/v2/hayuya")
VIEW_DIR = REF_ROOT / "individual"
DETAIL_DIR = REF_ROOT / "details"
OUT_DIR = Path("out/llorona-v2-hunyuan")

PRIMARY = {
    "front": VIEW_DIR / "llorona_front.png",
    "back": VIEW_DIR / "llorona_back.png",
    "left": VIEW_DIR / "llorona_left_side.png",
    "right": VIEW_DIR / "llorona_right_side.png",
}

ALL_VIEWS = [
    VIEW_DIR / "llorona_front.png",
    VIEW_DIR / "llorona_front_45_right.png",
    VIEW_DIR / "llorona_right_side.png",
    VIEW_DIR / "llorona_back_45_right.png",
    VIEW_DIR / "llorona_back.png",
    VIEW_DIR / "llorona_back_45_left.png",
    VIEW_DIR / "llorona_left_side.png",
    VIEW_DIR / "llorona_front_45_left.png",
]

DETAILS = [
    DETAIL_DIR / "llorona_face_closeup.png",
    DETAIL_DIR / "llorona_hair_detail.png",
    DETAIL_DIR / "llorona_torso_detail.png",
    DETAIL_DIR / "llorona_rosary_cross.png",
    DETAIL_DIR / "llorona_dress_detail.png",
    DETAIL_DIR / "llorona_hem_detail.png",
    DETAIL_DIR / "llorona_hand_detail.png",
]

def fail(msg: str) -> None:
    print(f"::error::{msg}")
    raise SystemExit(1)

for p in ALL_VIEWS + DETAILS:
    if not p.is_file() or p.stat().st_size < 1024:
        fail(f"Missing/invalid V2 reference: {p}")

OUT_DIR.mkdir(parents=True, exist_ok=True)
clean_dir = OUT_DIR / "clean_inputs"
clean_dir.mkdir(parents=True, exist_ok=True)

# Normalize the four geometry views without changing their visual content.
clean = {}
for name, src in PRIMARY.items():
    dst = clean_dir / f"{name}.png"
    im = Image.open(src).convert("RGBA")
    im.save(dst, "PNG", optimize=True)
    Image.open(dst).verify()
    clean[name] = dst
    print("V2_PRIMARY_REF_PASS", name, src, src.stat().st_size)

# Package every angle/detail for downstream 8-view texture projection and QA.
pkg = OUT_DIR / "reference_pack"
pkg.mkdir(parents=True, exist_ok=True)
for p in ALL_VIEWS + DETAILS:
    shutil.copy2(p, pkg / p.name)

token = os.environ.get("HF_TOKEN", "").strip() or None

def connect() -> Client:
    last = None
    for attempt in range(1, 6):
        try:
            kwargs = {"verbose": True, "httpx_kwargs": {"timeout": 120.0}}
            if token:
                kwargs["token"] = token
            c = Client(SPACE_URL, **kwargs)
            print(f"Hunyuan3D connected attempt={attempt}")
            return c
        except Exception as e:
            last = e
            print(f"::warning::Hunyuan connect {attempt}/5 failed: {type(e).__name__}: {e}")
            if attempt < 5:
                time.sleep(15 * attempt)
    fail(f"Unable to connect to Hunyuan3D-2mv: {last}")

client = connect()
api = client.view_api(print_info=False, return_format="dict")
(OUT_DIR / "api-info.json").write_text(json.dumps(api, indent=2), encoding="utf-8")
named = api.get("named_endpoints", {})

endpoint = "/shape_generation" if "/shape_generation" in named else next(
    (n for n in named if "shape_generation" in n), None
)
if not endpoint:
    fail(f"No shape generation endpoint. endpoints={list(named)}")

params = named[endpoint].get("parameters", [])
files = {k: handle_file(str(v)) for k, v in clean.items()}

overrides = {
    "caption": "",
    "image": None,
    "mv_image_front": files["front"],
    "mv_image_back": None,  # Hunyuan3D-2mv back slot is currently broken (PyMeshLabException).
    "mv_image_left": files["left"],
    "mv_image_right": files["right"],
    "steps": 5,
    "num_steps": 5,
    "guidance_scale": 5.0,
    "cfg_scale": 5.0,
    "seed": 1993,
    "octree_resolution": 256,
    "check_box_rembg": True,
    "num_chunks": 8000,
    "randomize_seed": False,
}

args = []
used = {}
for p in params:
    name = p.get("parameter_name")
    if name in overrides:
        value = overrides[name]
    elif p.get("parameter_has_default"):
        value = p.get("parameter_default")
    else:
        fail(f"Unhandled required Hunyuan parameter: {name}")
    args.append(value)
    used[name] = "<file>" if name.startswith("mv_image_") and value is not None else value

request = {
    "endpoint": endpoint,
    "parameters": used,
    "geometry_views": ["front", "left", "right"],
    "back_reference_reserved_for_texture": str(PRIMARY["back"]),
    "all_reference_views": [p.name for p in ALL_VIEWS],
    "detail_refs": [p.name for p in DETAILS],
    "seed": 1993,
}
(OUT_DIR / "request.json").write_text(json.dumps(request, indent=2, default=str), encoding="utf-8")

print("Submitting Llorona V2 to Hunyuan3D-2mv...")
try:
    result = client.predict(*args, api_name=endpoint)
except Exception as e:
    fail(f"Hunyuan generation failed: {type(e).__name__}: {e}")

(OUT_DIR / "result.txt").write_text(repr(result), encoding="utf-8")
print("Result:", repr(result)[:8000])

def walk(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from walk(v)
    elif isinstance(x, (list, tuple)):
        for v in x:
            yield from walk(v)
    else:
        for attr in ("path", "url"):
            v = getattr(x, attr, None)
            if isinstance(v, str):
                yield v

glbs = []
for s in walk(result):
    p = Path(s)
    if s.lower().endswith(".glb") and p.exists():
        glbs.append(p)

if not glbs:
    fail(f"No GLB returned by Hunyuan. result={result!r}")

for p in glbs:
    shutil.copy2(p, OUT_DIR / f"source_{p.name}")

# shape_generation is intentionally used: generation_all currently crashes
# remotely with PyMeshLabException. The V2 texture stage is handled separately.
preferred = next((p for p in glbs if "white_mesh" in p.name.lower()), None)
if preferred is None:
    preferred = glbs[0]

dst = OUT_DIR / "llorona_v2_hunyuan_hq.glb"
shutil.copy2(preferred, dst)

data = dst.read_bytes()
if data[:4] != b"glTF":
    fail(f"Invalid GLB magic: {data[:16]!r}")
if len(data) < 1024:
    fail(f"GLB unexpectedly small: {len(data)}")

manifest = {
    "asset": "La Llorona V2",
    "generator": "Tencent Hunyuan3D-2mv /shape_generation",
    "endpoint": endpoint,
    "geometry_input_views": ["front", "left", "right"],
    "back_reference_reserved_for_texture": PRIMARY["back"].name,
    "reference_pack_views": [p.name for p in ALL_VIEWS],
    "reference_pack_details": [p.name for p in DETAILS],
    "seed": 1993,
    "steps": 5,
    "guidance_scale": 5.0,
    "octree_resolution": 256,
    "selected_glb_source": preferred.name,
    "output_glb": dst.name,
    "glb_bytes": len(data),
    "all_returned_glbs": [p.name for p in glbs],
    "authenticated_hf": bool(token),
}
(OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print("XZIEL_LLORONA_V2_HUNYUAN_READY")
print(json.dumps(manifest, indent=2))
