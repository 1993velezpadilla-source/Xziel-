#!/usr/bin/env python3
from __future__ import annotations
import json, os, shutil, sys, time
from pathlib import Path
from PIL import Image, ImageFile
from gradio_client import Client, handle_file

ImageFile.LOAD_TRUNCATED_IMAGES = True

GEOMETRY = Path(os.environ["HAYUYA_GEOMETRY_INPUT"])
OUT = Path(os.environ.get("HAYUYA_OUTPUT_ROOT","out/hayuya-phone-cloud"))
JOB = os.environ.get("HAYUYA_JOB_ID","hayuya-phone")
TOKEN = os.environ.get("HF_TOKEN","").strip() or None
SPACE_URL = os.environ.get("TRELLIS_URL","https://trellis-community-trellis.hf.space")
OUT.mkdir(parents=True, exist_ok=True)
PREP = OUT / "prepared_views"
PREP.mkdir(parents=True, exist_ok=True)

def fail(msg):
    print(f"::error::{msg}")
    raise SystemExit(1)

if not GEOMETRY.is_file():
    fail(f"Missing primary reference: {GEOMETRY}")

# HAYUYA phone/cloud mode accepts a single concept/reference sheet.
# For a wide character sheet like Zombie Iglesia, recover the four full-body panels
# from the left ~76% of the sheet. This keeps the right-side closeups out of geometry.
with Image.open(GEOMETRY) as im:
    im.load()
    im = im.convert("RGB")
    w,h = im.size
    if w >= int(h*1.25):
        x0=0
        x1=int(w*0.76)
        y0=int(h*0.08)
        y1=int(h*0.96)
        span=x1-x0
        names=["front","side","back","three_quarter"]
        crops=[]
        for i,name in enumerate(names):
            a=x0+int(span*i/4)
            b=x0+int(span*(i+1)/4)
            pad=int(span*0.025)
            a=max(x0,a-pad); b=min(x1,b+pad)
            crop=im.crop((a,y0,b,y1))
            nw=max(1,round(crop.width*768/crop.height))
            crop=crop.resize((nw,768),Image.Resampling.LANCZOS)
            dst=PREP/f"{name}.png"
            crop.save(dst,"PNG",optimize=True)
            crops.append(dst)
            print("HAYUYA_VIEW_READY",name,dst,crop.size)
    else:
        dst=PREP/"front.png"
        im.save(dst,"PNG",optimize=True)
        crops=[dst]

# If only one view exists, TRELLIS can still run single-image.
multi=len(crops) >= 2

last=None
client=None
for attempt in range(1,6):
    try:
        kwargs={"verbose":True,"httpx_kwargs":{"timeout":120.0}}
        if TOKEN: kwargs["token"]=TOKEN
        client=Client(SPACE_URL,**kwargs)
        print("HAYUYA_TRELLIS_CONNECTED",attempt)
        break
    except Exception as e:
        last=e
        print(f"::warning::TRELLIS connect {attempt}/5 failed: {type(e).__name__}: {e}")
        if attempt<5: time.sleep(15*attempt)
if client is None:
    fail(f"Unable to connect to public TRELLIS ZeroGPU: {last}")

try:
    client.predict(api_name="/start_session")
except Exception as e:
    print(f"::warning::start_session: {type(e).__name__}: {e}")

if multi:
    try:
        client.predict(api_name="/lambda_1")
        print("HAYUYA_MULTIIMAGE_STATE_ENABLED")
    except Exception as e:
        fail(f"Could not enable multi-image mode: {type(e).__name__}: {e}")

def uploadable(v):
    if isinstance(v,str):
        p=Path(v)
        return handle_file(str(p)) if p.exists() else v
    if isinstance(v,dict):
        p=v.get("path")
        if isinstance(p,str) and Path(p).exists():
            return handle_file(p)
    return v

processed=[]
for p in crops:
    try:
        v=client.predict(handle_file(str(p)),api_name="/preprocess_image")
        processed.append(uploadable(v))
        print("HAYUYA_PREPROCESS_PASS",p.name)
    except Exception as e:
        fail(f"preprocess failed for {p.name}: {type(e).__name__}: {e}")

api=client.view_api(print_info=False,return_format="dict")
named=api.get("named_endpoints",{})
spec=named.get("/generate_and_extract_glb")
if not spec:
    # tolerate endpoint spelling changes
    key=next((k for k in named if "generate_and_extract_glb" in k),None)
    if key: spec=named[key]
    else: fail(f"TRELLIS GLB endpoint unavailable: {list(named)}")
    endpoint=key
else:
    endpoint="/generate_and_extract_glb"

params=[p.get("parameter_name") for p in spec.get("parameters",[])]
front=processed[0]
gallery=[{"image":v,"caption":None} for v in processed]
values={
    "image":front,
    "multiimages":gallery,
    "seed":1993,
    "ss_guidance_strength":7.5,
    "ss_sampling_steps":12,
    "slat_guidance_strength":3.0,
    "slat_sampling_steps":12,
    "multiimage_algo":"multidiffusion",
    "mesh_simplify":0.92,
    "texture_size":2048,
}
missing=[p for p in params if p not in values]
if missing:
    fail(f"Unhandled TRELLIS parameters: {missing}")
args=[values[p] for p in params]
print("HAYUYA_TRELLIS_SUBMIT",JOB,endpoint,params)
try:
    result=client.predict(*args,api_name=endpoint)
except Exception as e:
    fail(f"TRELLIS generation failed: {type(e).__name__}: {e}")

(OUT/"trellis_result.txt").write_text(repr(result),encoding="utf-8")
candidates=[]
def walk(x):
    if isinstance(x,str):
        yield x
    elif isinstance(x,dict):
        for v in x.values(): yield from walk(v)
    elif isinstance(x,(list,tuple)):
        for v in x: yield from walk(v)
    else:
        for attr in ("path","url"):
            v=getattr(x,attr,None)
            if isinstance(v,str): yield v

for s in walk(result):
    if s.lower().endswith(".glb") and Path(s).exists():
        candidates.append(Path(s))
if not candidates:
    fail(f"No downloaded GLB in TRELLIS result: {result!r}")

src=candidates[-1]
dst=OUT/"hayuya_final.glb"
shutil.copy2(src,dst)
data=dst.read_bytes()
if data[:4] != b"glTF" or len(data)<1024:
    fail("Invalid GLB output")

manifest={
    "engine":"HAYUYA PHONE CLOUD",
    "job_id":JOB,
    "compute":"GitHub-hosted CPU controller + public TRELLIS ZeroGPU",
    "phone_only":True,
    "source":str(GEOMETRY),
    "prepared_views":[p.name for p in crops],
    "multi_image":multi,
    "generator":"trellis-community/TRELLIS",
    "texture_size":2048,
    "glb":dst.name,
    "glb_bytes":len(data),
    "authenticated_hf":bool(TOKEN),
}
(OUT/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
print("HAYUYA_PHONE_CLOUD_PASS")
print(json.dumps(manifest,indent=2))
