#!/usr/bin/env python3
from __future__ import annotations
import json, os, shutil, sys, time
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from PIL import Image, ImageFile
from gradio_client import Client, handle_file
from mesh_gate import inspect as inspect_mesh_gate
from rig_gate import inspect as inspect_rig_gate
from texture_gate import inspect as inspect_texture_gate

ImageFile.LOAD_TRUNCATED_IMAGES = True

GEOMETRY = Path(os.environ["HAYUYA_GEOMETRY_INPUT"])
REFERENCE_DIR_RAW = os.environ.get("HAYUYA_REFERENCE_DIR","").strip()
DETAIL_DIR_RAW = os.environ.get("HAYUYA_DETAIL_DIR","").strip()
REFERENCE_DIR = Path(REFERENCE_DIR_RAW) if REFERENCE_DIR_RAW else None
DETAIL_DIR = Path(DETAIL_DIR_RAW) if DETAIL_DIR_RAW else None
OUT = Path(os.environ.get("HAYUYA_OUTPUT_ROOT","out/hayuya-phone-cloud"))
JOB = os.environ.get("HAYUYA_JOB_ID","hayuya-phone")
ASSET_PROFILE = os.environ.get("HAYUYA_ASSET_PROFILE","auto").strip() or "auto"
ANIMATION_REQUESTED = os.environ.get("HAYUYA_ANIMATION_REQUESTED","false").strip().lower() in {"1","true","yes","on"}
MOTION_PROFILE = os.environ.get("HAYUYA_MOTION_PROFILE","auto").strip() or "auto"
TEXTURE_QUALITY = os.environ.get("HAYUYA_TEXTURE_QUALITY","standard").strip() or "standard"
TOKEN = os.environ.get("HF_TOKEN","").strip() or None
SPACE_URL = os.environ.get("TRELLIS_URL","https://trellis-community-trellis.hf.space")
OUT.mkdir(parents=True, exist_ok=True)
PREP = OUT / "prepared_views"
PREP.mkdir(parents=True, exist_ok=True)
DETAIL_PREP = OUT / "prepared_details"
DETAIL_PREP.mkdir(parents=True, exist_ok=True)

QUALITY_TARGETS={"preview":768,"standard":1024,"high":1536,"ultra":2048}
PREP_TARGET=QUALITY_TARGETS.get(TEXTURE_QUALITY,1024)
IMAGE_EXTS={".png",".jpg",".jpeg",".webp",".bmp"}

def fail(msg):
    try:
        (OUT/"failure_reason.txt").write_text(str(msg).strip()+"\n", encoding="utf-8")
    except Exception:
        pass
    print(f"::error::{msg}")
    raise SystemExit(1)

if not GEOMETRY.is_file():
    fail(f"Missing primary reference: {GEOMETRY}")

# HAYUYA phone/cloud mode accepts a single image or a wide multi-view sheet.
# IMPORTANT: preserve alpha. Some generated PNGs are palette images (P mode) with
# tRNS transparency; converting those directly to RGB turns the transparent area
# into a solid palette color and TRELLIS reconstructs that background as geometry.
def has_useful_alpha(image):
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    lo, hi = image.getchannel("A").getextrema()
    return lo < 250 and hi > 0

def prepare_view(image, dst, *, target=1024):
    rgba = image.convert("RGBA")
    useful_alpha = has_useful_alpha(rgba)

    if useful_alpha:
        alpha = rgba.getchannel("A")
        mask = alpha.point(lambda v: 255 if v > 8 else 0)
        bbox = mask.getbbox()
        if bbox:
            l, t, r, b = bbox
            span = max(r-l, b-t)
            pad = max(8, round(span * 0.06))
            l=max(0,l-pad); t=max(0,t-pad)
            r=min(rgba.width,r+pad); b=min(rgba.height,b+pad)
            rgba = rgba.crop((l,t,r,b))

        # Give the object breathing room and center it on transparent canvas.
        side=max(rgba.width,rgba.height)
        margin=max(8,round(side*0.08))
        canvas=Image.new("RGBA",(side+margin*2,side+margin*2),(0,0,0,0))
        x=(canvas.width-rgba.width)//2
        y=(canvas.height-rgba.height)//2
        canvas.alpha_composite(rgba,(x,y))
        rgba=canvas.resize((target,target),Image.Resampling.LANCZOS)
        rgba.save(dst,"PNG",optimize=True)
    else:
        # No reliable alpha: keep RGB and let TRELLIS/rembg do its own removal.
        rgb=rgba.convert("RGB")
        scale=min(1.0,target/max(rgb.width,rgb.height))
        if scale < 1.0:
            rgb=rgb.resize((max(1,round(rgb.width*scale)),max(1,round(rgb.height*scale))),Image.Resampling.LANCZOS)
        rgb.save(dst,"PNG",optimize=True)

    with Image.open(dst) as check:
        check.load()
        alpha_fraction=None
        if check.mode=="RGBA":
            a=check.getchannel("A")
            hist=a.histogram()
            alpha_fraction=1.0-(hist[255]/float(check.width*check.height))
        print(
            "HAYUYA_VIEW_READY",
            dst.stem,
            dst,
            check.size,
            "mode="+check.mode,
            "alpha_fraction="+("none" if alpha_fraction is None else f"{alpha_fraction:.4f}")
        )
    return dst

with Image.open(GEOMETRY) as source:
    source.load()
    source_mode=source.mode
    source_info=dict(source.info)
    source_rgba=source.convert("RGBA")
    source_had_alpha=has_useful_alpha(source_rgba)
    w,h=source_rgba.size
    print(
        "HAYUYA_SOURCE",
        GEOMETRY,
        "mode="+source_mode,
        "size="+f"{w}x{h}",
        "palette_transparency="+str("transparency" in source_info),
        "useful_alpha="+str(source_had_alpha)
    )

    # Reject a known catastrophic input class before spending GPU quota:
    # palette+tRNS files where one almost-opaque fill color dominates the
    # visible image. This is what produced the Candyland "cross of planes".
    if source_mode == "P" and "transparency" in source_info:
        probe=source_rgba.resize((min(256,w), max(1,round(h*min(256,w)/w))), Image.Resampling.NEAREST)
        visible=[px for px in probe.getdata() if px[3] > 16]
        if visible:
            rgba_count, rgba_n = Counter(visible).most_common(1)[0]
            dominant_ratio = rgba_n / len(visible)
            print("HAYUYA_PALETTE_DIAGNOSTIC", "dominant_ratio="+f"{dominant_ratio:.4f}", "rgba="+str(rgba_count))
            if dominant_ratio > 0.35:
                fail(
                    "Rejected corrupt/suspicious palette+tRNS source before GPU generation: "
                    f"one visible RGBA value occupies {dominant_ratio:.1%} of the foreground. "
                    "Replace the source with the original RGB/RGBA reference."
                )

    if w >= int(h*1.25):
        # Legacy/reference-sheet path: recover the four body panels from the left
        # ~76% of the sheet and preserve transparency inside each crop.
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
            crop=source_rgba.crop((a,y0,b,y1))
            dst=PREP/f"{name}.png"
            crops.append(prepare_view(crop,dst,target=PREP_TARGET))
    else:
        dst=PREP/"front.png"
        crops=[prepare_view(source_rgba,dst,target=PREP_TARGET)]

# Native multi-image mode: a user/project may provide independent views instead
# of baking them into one contact sheet. Keep the primary geometry reference
# first, then add up to seven extra views. This preserves perspective evidence
# far better than asking a single image to invent the unseen side/back.
if REFERENCE_DIR and REFERENCE_DIR.is_dir():
    extras=[]
    for p in sorted(REFERENCE_DIR.iterdir()):
        if not p.is_file() or p.suffix.lower() not in IMAGE_EXTS:
            continue
        try:
            with Image.open(p) as im:
                im.load()
                dst=PREP/f"view_{len(extras)+2:02d}.png"
                extras.append(prepare_view(im,dst,target=PREP_TARGET))
        except Exception as exc:
            print(f"::warning::Skipping reference {p}: {type(exc).__name__}: {exc}")
        if len(extras)>=7:
            break
    crops.extend(extras)

# Detail/face/material crops are intentionally NOT mixed into geometry views:
# closeups have incompatible camera scale and can warp the reconstructed body.
# We still normalize/preserve them for the subsequent texture/detail refinement
# stage and expose them in the manifest.
detail_views=[]
if DETAIL_DIR and DETAIL_DIR.is_dir():
    for p in sorted(DETAIL_DIR.iterdir()):
        if not p.is_file() or p.suffix.lower() not in IMAGE_EXTS:
            continue
        try:
            with Image.open(p) as im:
                im.load()
                dst=DETAIL_PREP/f"detail_{len(detail_views)+1:02d}.png"
                detail_views.append(prepare_view(im,dst,target=PREP_TARGET))
        except Exception as exc:
            print(f"::warning::Skipping detail reference {p}: {type(exc).__name__}: {exc}")
        if len(detail_views)>=12:
            break

# If only one view exists, TRELLIS runs its true single-image path.
multi=len(crops) >= 2
print("HAYUYA_REFERENCE_SET",
      "geometry_views="+str(len(crops)),
      "detail_views="+str(len(detail_views)),
      "prep_target="+str(PREP_TARGET))

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
    "requested_texture_target":{"preview":1024,"standard":2048,"high":4096,"ultra":8192}.get(TEXTURE_QUALITY,2048),
    "texture_refinement_pending":TEXTURE_QUALITY in {"high","ultra"} or bool(detail_views),
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

# Catastrophic geometry gate: a backend returning a syntactically valid GLB is
# not enough. Reject billboard crosses, fragmented texture planes, collapsed
# bounds, and other obvious non-model outputs before the Hub ever says DONE.
gate=inspect_mesh_gate(dst)
gate_payload=asdict(gate)
(OUT/"quality_gate.json").write_text(json.dumps(gate_payload,indent=2),encoding="utf-8")
print("HAYUYA_MESH_GATE", json.dumps(gate_payload, separators=(",",":")))
if not gate.passed:
    fail("HAYUYA mesh quality gate rejected output: " + "; ".join(gate.reasons))

# Texture gate prevents the old failure mode where a geometrically valid model
# reaches DONE with no usable embedded texture or only a tiny texture. Blur is
# reported as telemetry first; fidelity refinement owns the stricter judgment.
texture_gate=inspect_texture_gate(dst, min_edge=1024)
texture_payload=asdict(texture_gate)
(OUT/"texture_gate.json").write_text(json.dumps(texture_payload,indent=2),encoding="utf-8")
print("HAYUYA_TEXTURE_GATE", json.dumps(texture_payload,separators=(",",":")))
if not texture_gate.passed:
    fail("HAYUYA texture gate rejected output: " + "; ".join(texture_gate.warnings))

# Animation readiness is profile-specific. Humanoids use skeletal rig QA;
# weapons/vehicles/mechanical props require part/pivot mechanics; foliage uses
# runtime wind/vertex motion. Never force a humanoid skeleton onto arbitrary
# assets just to make the "animation ready" badge turn green.
character_payload=None
if ASSET_PROFILE in {"auto","character.humanoid","character.creature"}:
    rig=inspect_rig_gate(dst, Path("hayuya/standards/hayuya_humanoid_v1.json"))
    rig_payload=asdict(rig)
    (OUT/"rig_gate.json").write_text(json.dumps(rig_payload,indent=2),encoding="utf-8")
    print("HAYUYA_RIG_GATE", json.dumps(rig_payload, separators=(",",":")))
    character_payload={
        "skeleton_type":rig_payload["skeleton_type"],
        "preview_pack":"hayuya_preview_pack_v1",
        "rig_ready":rig_payload["rig_ready"],
        "animation_ready":rig_payload["animation_ready"],
        "preview_animation_ready":rig_payload["preview_animation_ready"],
        "animation_clips":rig_payload["animation_clips"],
        "facial":rig_payload["facial"],
        "secondary_motion":rig_payload["secondary_motion"],
        "warnings":rig_payload["warnings"],
    }

profile_systems={
    "character.humanoid":["skeletal","morph_targets","secondary_motion"],
    "character.creature":["skeletal","morph_targets","secondary_motion"],
    "weapon.firearm":["mechanical_skeleton","transform_channels"],
    "weapon.melee":["transform_channels","optional_skeletal"],
    "prop.mechanical":["mechanical_skeleton","transform_channels"],
    "vehicle":["mechanical_skeleton","transform_channels","suspension_rig"],
    "foliage.grass":["vertex_wind","transform_channels"],
    "foliage.tree":["vertex_wind","skeletal_foliage"],
    "prop.static":["optional_transform_channels","optional_morph_targets"],
    "environment.modular":["optional_transform_channels","optional_vertex_animation"],
    "auto":[],
}
asset_payload={
    "profile":ASSET_PROFILE,
    "animation_requested":ANIMATION_REQUESTED,
    "motion_profile":MOTION_PROFILE,
    "animation_systems":profile_systems.get(ASSET_PROFILE,[]),
    "mechanical_rig_ready":False,
    "procedural_motion_ready":ASSET_PROFILE in {"foliage.grass","foliage.tree"},
    "requires_profile_postprocess":ASSET_PROFILE not in {"auto","character.humanoid","character.creature","prop.static"},
}

manifest={
    "schema":2,
    "engine":"HAYUYA PHONE CLOUD",
    "job_id":JOB,
    "asset_profile":ASSET_PROFILE,
    "animation_requested":ANIMATION_REQUESTED,
    "motion_profile":MOTION_PROFILE,
    "texture_quality":TEXTURE_QUALITY,
    "compute":"GitHub-hosted CPU controller + public TRELLIS ZeroGPU",
    "phone_only":True,
    "source":str(GEOMETRY),
    "prepared_views":[p.name for p in crops],
    "prepared_detail_views":[p.name for p in detail_views],
    "reference_dir":str(REFERENCE_DIR) if REFERENCE_DIR else "",
    "detail_dir":str(DETAIL_DIR) if DETAIL_DIR else "",
    "prep_target":PREP_TARGET,
    "multi_image":multi,
    "generator":"trellis-community/TRELLIS",
    "texture_size":2048,
    "requested_texture_target":{"preview":1024,"standard":2048,"high":4096,"ultra":8192}.get(TEXTURE_QUALITY,2048),
    "texture_refinement_pending":TEXTURE_QUALITY in {"high","ultra"} or bool(detail_views),
    "glb":dst.name,
    "glb_bytes":len(data),
    "authenticated_hf":bool(TOKEN),
    "source_mode":source_mode,
    "source_had_alpha":source_had_alpha,
    "alpha_preserved":True,
    "quality_gate":gate_payload,
    "texture_gate":texture_payload,
    "asset":asset_payload,
}
if character_payload is not None:
    manifest["character"]=character_payload
(OUT/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
print("HAYUYA_PHONE_CLOUD_PASS")
print(json.dumps(manifest,indent=2))
