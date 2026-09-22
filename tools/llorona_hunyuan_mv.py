#!/usr/bin/env python3
from __future__ import annotations
import json, os, shutil, sys, time
from pathlib import Path
from gradio_client import Client, handle_file
from PIL import Image, ImageFile

SPACE = os.environ.get("HUNYUAN_SPACE", "tencent/Hunyuan3D-2mv")
SPACE_URL = os.environ.get("HUNYUAN_URL", "https://tencent-hunyuan3d-2mv.hf.space")
REF_DIR = Path("assets/characters/llorona/reference")
OUT_DIR = Path("out/llorona-hunyuan-mv")
REFS = {
    "front": REF_DIR / "front.jpg",
    "back": REF_DIR / "back.jpg",
    "left": REF_DIR / "left.jpg",
    "right": REF_DIR / "right.jpg",
}

def fail(msg):
    print(f"::error::{msg}")
    raise SystemExit(1)

for name,p in REFS.items():
    if not p.is_file() or p.stat().st_size < 1024:
        fail(f"Missing/invalid {name} reference: {p}")

OUT_DIR.mkdir(parents=True, exist_ok=True)
token = os.environ.get("HF_TOKEN", "").strip() or None

def connect():
    last=None
    for attempt in range(1,6):
        try:
            kwargs={"verbose":True,"httpx_kwargs":{"timeout":120.0}}
            if token:
                kwargs["token"]=token
            c=Client(SPACE_URL, **kwargs)
            print(f"Hunyuan3D client connected attempt={attempt}")
            return c
        except Exception as e:
            last=e
            print(f"::warning::Hunyuan connect {attempt}/5 failed: {type(e).__name__}: {e}")
            if attempt<5:
                time.sleep(15*attempt)
    fail(f"Unable to connect to Hunyuan3D-2mv: {last}")

client=connect()
api=client.view_api(print_info=False, return_format="dict")
(OUT_DIR/"api-info.json").write_text(json.dumps(api,indent=2),encoding="utf-8")

named=api.get("named_endpoints",{})

def choose_endpoint():
    # Prefer the textured path if public; otherwise shape-only still gives a real GLB.
    for candidate in ("/generation_all","/shape_generation"):
        if candidate in named:
            return candidate
    for name in named:
        if "generation_all" in name:
            return name
    for name in named:
        if "shape_generation" in name:
            return name
    fail(f"No Hunyuan generation endpoint found. endpoints={list(named)}")

endpoint=choose_endpoint()
spec=named[endpoint]
params=spec.get("parameters",[])
print("Using endpoint",endpoint)
print("Parameters",[p.get("parameter_name") for p in params])

# Normalize every reference into a fresh PNG. Some of the early JPEG blobs in this
# branch were visually readable but had truncated streams; PIL can recover them and
# writing PNG gives Hunyuan a strict, clean input.
ImageFile.LOAD_TRUNCATED_IMAGES = True
clean_dir = OUT_DIR / "clean_inputs"
clean_dir.mkdir(parents=True, exist_ok=True)
clean = {}
for name, src in REFS.items():
    dst = clean_dir / f"{name}.png"
    im = Image.open(src)
    im.load()
    im = im.convert("RGBA")
    im.save(dst, "PNG", optimize=True)
    # Re-open strictly to verify the newly written stream.
    check = Image.open(dst)
    check.verify()
    clean[name] = dst
    print("CLEAN_REF_PASS", name, dst, dst.stat().st_size)

files={k:handle_file(str(p)) for k,p in clean.items()}
overrides={
    "caption":"",
    "image":None,
    "mv_image_front":files["front"],
    "mv_image_back":files["back"],
    "mv_image_left":files["left"],
    "mv_image_right":files["right"],
    "steps":40,
    "num_steps":40,
    "guidance_scale":7.5,
    "cfg_scale":7.5,
    "seed":1993,
    "octree_resolution":256,
    "check_box_rembg":True,
    "num_chunks":200000,
    "randomize_seed":False,
}
args=[]
used={}
for p in params:
    n=p.get("parameter_name")
    if n in overrides:
        v=overrides[n]
    elif p.get("parameter_has_default"):
        v=p.get("parameter_default")
    else:
        fail(f"Unhandled required Hunyuan parameter: {n}")
    args.append(v); used[n]=v if n not in files else "<file>"
(OUT_DIR/"request.json").write_text(json.dumps({
    "endpoint":endpoint,
    "parameters":{k:("<file>" if hasattr(v,"get") and isinstance(v,dict) and "path" in v else v) for k,v in used.items()},
    "source_views":[str(p) for p in REFS.values()],
},indent=2,default=str),encoding="utf-8")

print("Submitting Hunyuan3D-2mv multi-view generation...")
try:
    result=client.predict(*args, api_name=endpoint)
except Exception as e:
    fail(f"Hunyuan generation failed: {type(e).__name__}: {e}")

print("Result:",repr(result)[:8000])
(OUT_DIR/"result.txt").write_text(repr(result),encoding="utf-8")

def walk(x):
    if isinstance(x,str):
        yield x
    elif isinstance(x,dict):
        for v in x.values():
            yield from walk(v)
    elif isinstance(x,(list,tuple)):
        for v in x:
            yield from walk(v)
    else:
        for attr in ("path","url"):
            v=getattr(x,attr,None)
            if isinstance(v,str):
                yield v

paths=[]
for s in walk(result):
    if s.lower().endswith(".glb") and Path(s).exists():
        paths.append(Path(s))
if not paths:
    fail(f"No downloaded GLB found in Hunyuan result: {result!r}")

# Prefer the textured output when generation_all returns both white and textured meshes.
src=next((p for p in paths if "textured" in p.name.lower()), paths[-1])
dst=OUT_DIR/"llorona_hunyuan_mv_hq.glb"
shutil.copy2(src,dst)

data=dst.read_bytes()
if data[:4] != b"glTF":
    fail(f"Invalid GLB magic: {data[:16]!r}")
if len(data)<1024:
    fail(f"GLB unexpectedly small: {len(data)}")

manifest={
    "asset":"La Llorona",
    "generator":"Tencent Hunyuan3D-2mv",
    "endpoint":endpoint,
    "views":list(REFS.keys()),
    "seed":1993,
    "steps":40,
    "guidance_scale":7.5,
    "octree_resolution":256,
    "glb":dst.name,
    "glb_bytes":len(data),
    "source_result_paths":[str(p) for p in paths],
    "authenticated_hf":bool(token),
}
(OUT_DIR/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
print("XZIEL_LLORONA_HUNYUAN_MV_GLB_READY")
print(json.dumps(manifest,indent=2))
