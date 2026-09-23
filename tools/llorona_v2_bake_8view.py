#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import os
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage
import trimesh
import xatlas

SRC_DIR = Path(os.environ.get("LLORONA_V2_HUNYUAN_DIR", "out/llorona-v2-hunyuan"))
REF_ROOT = Path(os.environ.get("LLORONA_V2_REF_DIR", "assets/characters/llorona/v2/hayuya"))
VIEW_DIR = REF_ROOT / "individual"
DETAIL_DIR = REF_ROOT / "details"
OUT = Path(os.environ.get("LLORONA_V2_BAKE_OUT", "out/llorona-v2-texture"))
TARGET_FACES = int(os.environ.get("LLORONA_TARGET_FACES", "240000"))
TEX_SIZE = int(os.environ.get("LLORONA_TEXTURE_SIZE", "1024"))
TARGET_HEIGHT_M = float(os.environ.get("LLORONA_HEIGHT_M", "1.72"))
CHUNK_TEXELS = int(os.environ.get("LLORONA_CHUNK_TEXELS", "160000"))

OUT.mkdir(parents=True, exist_ok=True)

def fail(msg: str) -> None:
    print(f"::error::{msg}")
    raise SystemExit(1)

def find_mesh() -> Path:
    for name in ("llorona_v2_hunyuan_hq.glb", "source_white_mesh.glb", "white_mesh.glb"):
        p = SRC_DIR / name
        if p.is_file() and p.stat().st_size > 1024:
            return p
    for p in SRC_DIR.rglob("*.glb"):
        if p.stat().st_size > 1024:
            return p
    fail(f"No V2 GLB under {SRC_DIR}")

VIEW_FILES = {
    "front": "llorona_front.png",
    "front_45_right": "llorona_front_45_right.png",
    "right": "llorona_right_side.png",
    "back_45_right": "llorona_back_45_right.png",
    "back": "llorona_back.png",
    "back_45_left": "llorona_back_45_left.png",
    "left": "llorona_left_side.png",
    "front_45_left": "llorona_front_45_left.png",
}

DETAIL_FILES = {
    "face": "llorona_face_closeup.png",
    "hair": "llorona_hair_detail.png",
    "torso": "llorona_torso_detail.png",
    "rosary": "llorona_rosary_cross.png",
    "dress": "llorona_dress_detail.png",
    "hem": "llorona_hem_detail.png",
    "hand": "llorona_hand_detail.png",
}

for p in [VIEW_DIR / x for x in VIEW_FILES.values()] + [DETAIL_DIR / x for x in DETAIL_FILES.values()]:
    if not p.is_file() or p.stat().st_size < 1024:
        fail(f"Missing V2 reference: {p}")

def bilinear_rgb(im: np.ndarray, u: np.ndarray, v: np.ndarray) -> np.ndarray:
    h, w = im.shape[:2]
    x = np.clip(u, 0.0, 1.0) * (w - 1)
    y = np.clip(v, 0.0, 1.0) * (h - 1)
    x0, y0 = np.floor(x).astype(np.int32), np.floor(y).astype(np.int32)
    x1, y1 = np.minimum(x0 + 1, w - 1), np.minimum(y0 + 1, h - 1)
    fx, fy = (x - x0)[:, None], (y - y0)[:, None]
    a = im[y0, x0] * (1.0 - fx) + im[y0, x1] * fx
    b = im[y1, x0] * (1.0 - fx) + im[y1, x1] * fx
    return a * (1.0 - fy) + b * fy

def bilinear_mask(im: np.ndarray, u: np.ndarray, v: np.ndarray) -> np.ndarray:
    h, w = im.shape[:2]
    x = np.clip(u, 0.0, 1.0) * (w - 1)
    y = np.clip(v, 0.0, 1.0) * (h - 1)
    x0, y0 = np.floor(x).astype(np.int32), np.floor(y).astype(np.int32)
    x1, y1 = np.minimum(x0 + 1, w - 1), np.minimum(y0 + 1, h - 1)
    fx, fy = x - x0, y - y0
    a = im[y0, x0] * (1.0 - fx) + im[y0, x1] * fx
    b = im[y1, x0] * (1.0 - fx) + im[y1, x1] * fx
    return a * (1.0 - fy) + b * fy

def crop_foreground(path: Path, margin_frac: float = 0.025) -> tuple[np.ndarray, np.ndarray, dict]:
    rgb = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32)
    h, w = rgb.shape[:2]
    border = np.concatenate([
        rgb[:max(2, h//40)].reshape(-1,3),
        rgb[-max(2, h//40):].reshape(-1,3),
        rgb[:, :max(2, w//40)].reshape(-1,3),
        rgb[:, -max(2, w//40):].reshape(-1,3),
    ], axis=0)
    bg = np.median(border, axis=0)
    dist = np.linalg.norm(rgb - bg[None,None,:], axis=2)
    mask = (dist > 11.0).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7,7), np.uint8), iterations=2)
    mask = cv2.dilate(mask, np.ones((5,5), np.uint8), iterations=1)
    ys, xs = np.where(mask > 0)
    if len(xs) < 64:
        fail(f"Foreground detection failed: {path}")
    x0,x1,y0,y1 = int(xs.min()), int(xs.max())+1, int(ys.min()), int(ys.max())+1
    mx,my = int((x1-x0)*margin_frac), int((y1-y0)*margin_frac)
    x0,x1=max(0,x0-mx),min(w,x1+mx)
    y0,y1=max(0,y0-my),min(h,y1+my)
    cropped = rgb[y0:y1, x0:x1]
    cmask = mask[y0:y1, x0:x1].astype(np.float32)
    meta = {"width":w,"height":h,"crop":[x0,y0,x1,y1],"bg":[float(x) for x in bg],"foregroundFraction":float(mask.mean())}
    return cropped, cmask, meta

mesh_path = find_mesh()
scene = trimesh.load(mesh_path, force="scene")
if not scene.geometry:
    fail("V2 Hunyuan GLB has no geometry")
src = max(scene.geometry.values(), key=lambda g: len(g.faces)).copy()
raw_vertices, raw_faces = len(src.vertices), len(src.faces)
src.remove_unreferenced_vertices()
keep = np.asarray(src.unique_faces(), dtype=bool) & np.asarray(src.nondegenerate_faces(), dtype=bool)
src.update_faces(keep)
src.remove_unreferenced_vertices()
clean_vertices, clean_faces = len(src.vertices), len(src.faces)

if TARGET_FACES > 0 and len(src.faces) > TARGET_FACES:
    try:
        candidate = src.simplify_quadric_decimation(face_count=TARGET_FACES, aggression=4)
        candidate.remove_unreferenced_vertices()
        good = np.asarray(candidate.unique_faces(), dtype=bool) & np.asarray(candidate.nondegenerate_faces(), dtype=bool)
        candidate.update_faces(good)
        candidate.remove_unreferenced_vertices()
        if len(candidate.vertices) >= 20000 and len(candidate.faces) >= int(TARGET_FACES * 0.7):
            src = candidate
    except Exception as e:
        print(f"::warning::Decimation unavailable; using clean full mesh: {type(e).__name__}: {e}")

V = np.asarray(src.vertices, dtype=np.float64)
F = np.asarray(src.faces, dtype=np.uint32)
N = np.asarray(src.vertex_normals, dtype=np.float64)
mins0,maxs0 = V.min(0),V.max(0)
height0=float((maxs0-mins0)[1])
if height0 <= 1e-6:
    fail("Degenerate V2 Hunyuan bounds")
V=(V-np.array([0.0,mins0[1],0.0]))*(TARGET_HEIGHT_M/height0)
mins,maxs=V.min(0),V.max(0)
extent=maxs-mins

angles = {
    "front": 0.0,
    "front_45_right": -45.0,
    "right": -90.0,
    "back_45_right": -135.0,
    "back": 180.0,
    "back_45_left": 135.0,
    "left": 90.0,
    "front_45_left": 45.0,
}
views={}
quality={}
for name,filename in VIEW_FILES.items():
    im,mask,meta=crop_foreground(VIEW_DIR/filename)
    a=math.radians(angles[name])
    d=np.array([math.sin(a),0.0,math.cos(a)],dtype=np.float64)
    hvec=np.array([d[2],0.0,-d[0]],dtype=np.float64)
    proj=V@hvec
    views[name]={
        "image":im,"mask":mask,"direction":d,"hvec":hvec,
        "pmin":float(proj.min()),"pmax":float(proj.max()),"meta":meta
    }
    quality[name]=meta

details={}
for name,filename in DETAIL_FILES.items():
    im,mask,meta=crop_foreground(DETAIL_DIR/filename, margin_frac=0.01)
    details[name]=(im,mask,meta)

(OUT/"reference_quality.json").write_text(json.dumps(quality,indent=2),encoding="utf-8")

def feather_interval(x: np.ndarray, lo: float, hi: float, amount: float=0.12) -> np.ndarray:
    f=max((hi-lo)*amount,1e-6)
    return np.clip((x-lo)/f,0.0,1.0)*np.clip((hi-x)/f,0.0,1.0)

def detail_sample(key: str, xn: np.ndarray, yn: np.ndarray, region: tuple[float,float,float,float]) -> tuple[np.ndarray,np.ndarray]:
    x0,x1,y0,y1=region
    im,mask,_=details[key]
    u=np.clip((xn-x0)/max(x1-x0,1e-9),0.0,1.0)
    v=np.clip(1.0-(yn-y0)/max(y1-y0,1e-9),0.0,1.0)
    return bilinear_rgb(im,u,v),bilinear_mask(mask,u,v)

def project_color(pos: np.ndarray, nrm: np.ndarray) -> np.ndarray:
    if len(pos)==0:
        return np.empty((0,3),np.float32)
    nrm=nrm/np.maximum(np.linalg.norm(nrm,axis=1,keepdims=True),1e-9)
    xn=(pos[:,0]-mins[0])/max(extent[0],1e-9)
    yn=(pos[:,1]-mins[1])/max(extent[1],1e-9)

    samples=[]
    weights=[]
    dirs=[]
    for name in VIEW_FILES:
        spec=views[name]
        u=(pos@spec["hvec"]-spec["pmin"])/max(spec["pmax"]-spec["pmin"],1e-9)
        v=1.0-yn
        c=bilinear_rgb(spec["image"],u,v)
        m=bilinear_mask(spec["mask"],u,v)
        facing=np.clip(nrm@spec["direction"],0.0,None)
        w=(facing**10.0)*(0.03+0.97*(m**2.0))
        samples.append(c); weights.append(w); dirs.append(spec["direction"])

    S=np.stack(samples,axis=1)
    W=np.stack(weights,axis=1)
    total=W.sum(1)
    color=(W[:,:,None]*S).sum(1)/np.maximum(total[:,None],1e-8)

    low=total<0.004
    if np.any(low):
        D=np.stack([np.clip(nrm[low]@d,0.0,None) for d in dirs],axis=1)
        choice=np.argmax(D,axis=1)
        color[low]=S[low][np.arange(len(choice)),choice]

    frontness=np.clip(nrm[:,2],0.0,1.0)
    backness=np.clip(-nrm[:,2],0.0,1.0)
    sideness=np.clip(np.abs(nrm[:,0]),0.0,1.0)

    overlays=[
        ("dress",(0.14,0.86,0.06,0.65),0.56,0.55*frontness+0.30*backness+0.22*sideness),
        ("hem",(0.05,0.95,0.00,0.20),0.68,0.42+0.45*np.maximum(frontness,backness)),
        ("torso",(0.20,0.80,0.43,0.77),0.40,frontness**1.2),
        ("rosary",(0.32,0.68,0.47,0.74),0.90,frontness**1.7),
        ("face",(0.28,0.72,0.76,0.995),0.94,frontness**1.8),
        ("hair",(0.20,0.80,0.58,0.995),0.30,np.maximum(frontness,backness)**1.2),
    ]
    for key,reg,strength,orient in overlays:
        x0,x1,y0,y1=reg
        inside=(xn>=x0)&(xn<=x1)&(yn>=y0)&(yn<=y1)
        sample,dm=detail_sample(key,xn,yn,reg)
        edge=feather_interval(xn,x0,x1)*feather_interval(yn,y0,y1)
        alpha=strength*edge*orient*dm*inside.astype(np.float64)
        color=color*(1.0-alpha[:,None])+sample*alpha[:,None]

    # Hand detail: apply near both lateral hand zones and mirror the UV mapping.
    him,hmask,_=details["hand"]
    hand_y0,hand_y1=0.28,0.63
    hand_band=feather_interval(yn,hand_y0,hand_y1,0.15)
    left_zone=np.clip((0.30-xn)/0.16,0.0,1.0)
    right_zone=np.clip((xn-0.70)/0.16,0.0,1.0)
    hand_side=np.maximum(left_zone,right_zone)*hand_band*sideness
    if np.any(hand_side>0):
        hu=np.where(xn<0.5,np.clip(xn/0.30,0,1),np.clip((1.0-xn)/0.30,0,1))
        hv=np.clip(1.0-(yn-hand_y0)/(hand_y1-hand_y0),0,1)
        hs=bilinear_rgb(him,hu,hv)
        hm=bilinear_mask(hmask,hu,hv)
        alpha=0.50*hand_side*hm
        color=color*(1-alpha[:,None])+hs*alpha[:,None]

    return np.clip(color,0,255).astype(np.float32)

print("V2_MESH",{"rawVertices":raw_vertices,"rawFaces":raw_faces,"cleanVertices":clean_vertices,"cleanFaces":clean_faces,"runtimeVertices":len(V),"runtimeFaces":len(F)})

vmapping, indices, uvs = xatlas.parametrize(
    np.ascontiguousarray(V.astype(np.float32)),
    np.ascontiguousarray(F.astype(np.uint32)),
)
vmapping=np.asarray(vmapping,dtype=np.int64)
Fuv=np.asarray(indices,dtype=np.int32)
UV=np.asarray(uvs,dtype=np.float32)
Vuv,Nuv=V[vmapping],N[vmapping]

tex=np.zeros((TEX_SIZE,TEX_SIZE,3),dtype=np.uint8)
mask=np.zeros((TEX_SIZE,TEX_SIZE),dtype=np.uint8)
uvpx=np.column_stack([UV[:,0]*(TEX_SIZE-1),(1.0-UV[:,1])*(TEX_SIZE-1)])

bx=[];by=[];bp=[];bn=[];queued=0;texel_writes=0

def flush():
    global queued,texel_writes
    if not bx:return
    xs,ys=np.concatenate(bx),np.concatenate(by)
    cols=project_color(np.concatenate(bp),np.concatenate(bn)).astype(np.uint8)
    tex[ys,xs]=cols
    mask[ys,xs]=255
    texel_writes+=len(xs)
    bx.clear();by.clear();bp.clear();bn.clear();queued=0

for fi,tri in enumerate(Fuv):
    p=uvpx[tri]
    minx=max(int(np.floor(p[:,0].min())),0);maxx=min(int(np.ceil(p[:,0].max())),TEX_SIZE-1)
    miny=max(int(np.floor(p[:,1].min())),0);maxy=min(int(np.ceil(p[:,1].max())),TEX_SIZE-1)
    if minx>maxx or miny>maxy:continue
    x0,y0=p[0];x1,y1=p[1];x2,y2=p[2]
    den=(y1-y2)*(x0-x2)+(x2-x1)*(y0-y2)
    if abs(float(den))<1e-10:continue
    gx,gy=np.meshgrid(np.arange(minx,maxx+1,dtype=np.int32),np.arange(miny,maxy+1,dtype=np.int32))
    sx,sy=gx+0.5,gy+0.5
    w0=((y1-y2)*(sx-x2)+(x2-x1)*(sy-y2))/den
    w1=((y2-y0)*(sx-x2)+(x0-x2)*(sy-y2))/den
    w2=1.0-w0-w1
    inside=(w0>=-1e-6)&(w1>=-1e-6)&(w2>=-1e-6)
    if not np.any(inside):continue
    xx,yy=gx[inside],gy[inside]
    a,b,c=w0[inside,None],w1[inside,None],w2[inside,None]
    pos=a*Vuv[tri[0]]+b*Vuv[tri[1]]+c*Vuv[tri[2]]
    nrm=a*Nuv[tri[0]]+b*Nuv[tri[1]]+c*Nuv[tri[2]]
    nrm/=np.maximum(np.linalg.norm(nrm,axis=1,keepdims=True),1e-9)
    bx.append(xx);by.append(yy);bp.append(pos);bn.append(nrm);queued+=len(xx)
    if queued>=CHUNK_TEXELS:flush()
    if fi and fi%50000==0:
        print("V2_8VIEW_BAKE",fi,"/",len(Fuv),"texels",texel_writes+queued)
flush()

valid=mask>0
if not np.any(valid):
    fail("V2 8-view atlas is empty")
coverage=float(valid.mean())
dist,inds=ndimage.distance_transform_edt(~valid,return_indices=True)
gutter=(~valid)&(dist<=12.0)
tex[gutter]=tex[inds[0][gutter],inds[1][gutter]]
tex_path=OUT/"llorona_v2_albedo_8view.png"
Image.fromarray(tex,"RGB").save(tex_path,optimize=True)

from trimesh.visual.material import PBRMaterial
from trimesh.visual.texture import TextureVisuals
material=PBRMaterial(
    name="Llorona_V2_8View_PBR",
    baseColorTexture=Image.fromarray(tex,"RGB"),
    baseColorFactor=[255,255,255,255],
    metallicFactor=0.0,
    roughnessFactor=0.82,
    doubleSided=True,
)
visual=TextureVisuals(uv=UV,material=material)
mesh=trimesh.Trimesh(vertices=Vuv,faces=Fuv,process=False,visual=visual)
glb_path=OUT/"llorona_v2_hayuya_8view_textured.glb"
glb_path.write_bytes(trimesh.exchange.gltf.export_glb(trimesh.Scene(mesh)))

check=trimesh.load(glb_path,force="scene")
if not check.geometry:
    fail("Exported V2 GLB has no geometry")
cg=max(check.geometry.values(),key=lambda g:len(g.faces))
has_uv=hasattr(cg.visual,"uv") and cg.visual.uv is not None and len(cg.visual.uv)>0
mat=getattr(cg.visual,"material",None)
has_tex=bool(getattr(mat,"baseColorTexture",None) is not None or getattr(mat,"image",None) is not None)
if not has_uv or not has_tex:
    fail(f"V2 texture validation failed uv={has_uv} texture={has_tex}")

manifest={
    "asset":"La Llorona V2",
    "pipeline":"new Hunyuan V2 geometry -> clean/optional 240k working mesh -> xatlas -> per-texel eight-view projection -> seven detail overlays",
    "sourceMesh":str(mesh_path),
    "rawVertices":raw_vertices,
    "rawFaces":raw_faces,
    "cleanVertices":clean_vertices,
    "cleanFaces":clean_faces,
    "runtimeVertices":len(V),
    "runtimeFaces":len(F),
    "uvVertices":len(Vuv),
    "uvFaces":len(Fuv),
    "targetFaces":TARGET_FACES,
    "heightMeters":TARGET_HEIGHT_M,
    "textureSize":TEX_SIZE,
    "atlasCoverage":coverage,
    "processedTexelWrites":texel_writes,
    "viewsUsed":[VIEW_FILES[k] for k in VIEW_FILES],
    "detailsUsed":[DETAIL_FILES[k] for k in DETAIL_FILES],
    "hasUV":bool(has_uv),
    "hasEmbeddedBaseColorTexture":bool(has_tex),
    "outputs":{"glb":glb_path.name,"albedo":tex_path.name},
}
(OUT/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
print(json.dumps(manifest,indent=2))
print("XZIEL_LLORONA_V2_8VIEW_TEXTURE_PASS")
