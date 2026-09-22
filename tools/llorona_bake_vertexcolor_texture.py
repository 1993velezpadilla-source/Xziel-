#!/usr/bin/env python3
from __future__ import annotations
import json, math, os, sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
import trimesh
import xatlas

SRC_DIR = Path(os.environ.get("LLORONA_HUNYUAN_DIR", "in/hunyuan"))
OUT = Path(os.environ.get("LLORONA_BAKE_OUT", "out/llorona-baked"))
TARGET_FACES = int(os.environ.get("LLORONA_TARGET_FACES", "120000"))
TEX_SIZE = int(os.environ.get("LLORONA_TEXTURE_SIZE", "2048"))
TARGET_HEIGHT_M = float(os.environ.get("LLORONA_HEIGHT_M", "1.72"))

OUT.mkdir(parents=True, exist_ok=True)

def fail(msg: str):
    print(f"::error::{msg}")
    raise SystemExit(1)

def find_file(name: str) -> Path:
    hits=list(SRC_DIR.rglob(name))
    if not hits:
        fail(f"Missing source file {name} under {SRC_DIR}")
    return hits[0]

mesh_path=find_file("llorona_hunyuan_mv_hq.glb")
view_paths={n:find_file(f"{n}.png") for n in ("front","back","left","right")}

scene=trimesh.load(mesh_path, force="scene")
if not scene.geometry:
    fail("Hunyuan GLB has no geometry")
src=max(scene.geometry.values(), key=lambda g: len(g.faces)).copy()
src.remove_unreferenced_vertices()
print("SOURCE",len(src.vertices),len(src.faces),src.bounds.tolist())

# Keep Hunyuan silhouette but reduce the extremely dense generated surface to a
# practical game-asset master before UV unwrapping.
if len(src.faces) > TARGET_FACES:
    print("DECIMATE",len(src.faces),"->",TARGET_FACES)
    src=src.simplify_quadric_decimation(face_count=TARGET_FACES, aggression=5)
    src.remove_unreferenced_vertices()
print("DECIMATED",len(src.vertices),len(src.faces))

V=np.asarray(src.vertices,dtype=np.float64)
F=np.asarray(src.faces,dtype=np.uint32)
N=np.asarray(src.vertex_normals,dtype=np.float64)
mins=V.min(axis=0); maxs=V.max(axis=0)
extent=maxs-mins

# Hunyuan output is Y-up. Normalize to a deterministic real-world character height
# and put feet on Y=0.
height=float(extent[1])
if height <= 1e-6:
    fail("Degenerate Hunyuan bounds")
scale=TARGET_HEIGHT_M/height
V=(V-np.array([0.0,mins[1],0.0]))*scale
mins=V.min(axis=0); maxs=V.max(axis=0); extent=maxs-mins

images={}
for name,p in view_paths.items():
    im=np.asarray(Image.open(p).convert("RGB"),dtype=np.float32)
    images[name]=im
    print("VIEW",name,p,im.shape)

# Calibrated against the successful Hunyuan multiview asset:
# front camera +Z, back -Z (horizontally mirrored), left +X (mirrored), right -X.
view_cfg={
    "front": (np.array([0.0,0.0, 1.0]), "x", False),
    "back":  (np.array([0.0,0.0,-1.0]), "x", True),
    "left":  (np.array([1.0,0.0, 0.0]), "z", True),
    "right": (np.array([-1.0,0.0,0.0]), "z", False),
}

samples={}
weights={}
for name,(direction,axis,flip) in view_cfg.items():
    im=images[name]; h,w=im.shape[:2]
    if axis=="x":
        u=(V[:,0]-mins[0])/max(extent[0],1e-9)
    else:
        u=(V[:,2]-mins[2])/max(extent[2],1e-9)
    if flip:
        u=1.0-u
    vv=1.0-(V[:,1]-mins[1])/max(extent[1],1e-9)
    px=np.clip(np.rint(u*(w-1)).astype(np.int32),0,w-1)
    py=np.clip(np.rint(vv*(h-1)).astype(np.int32),0,h-1)
    samples[name]=im[py,px]
    weights[name]=np.clip(N@direction,0.0,None)**3.0

names=("front","back","left","right")
W=np.stack([weights[n] for n in names],axis=1)
S=W.sum(axis=1)
C=sum(W[:,i,None]*samples[n] for i,n in enumerate(names))/np.maximum(S[:,None],1e-8)

# Fill tangent/ambiguous vertices from the dominant axis-facing view.
small=np.where(S < 0.04)[0]
for idx in small:
    nx,nz=N[idx,0],N[idx,2]
    if abs(nx) > abs(nz):
        n="left" if nx>=0 else "right"
    else:
        n="front" if nz>=0 else "back"
    C[idx]=samples[n][idx]

# Slight contrast lift; preserve the intentionally dark wet hair.
C=np.clip((C-128.0)*1.06+128.0,0,255).astype(np.uint8)

# Save a vertex-color master too: useful fallback/debug and retains all projected
# information even if a future runtime wants COLOR_0 directly.
vc=trimesh.Trimesh(vertices=V,faces=F,process=False)
vc.visual.vertex_colors=np.column_stack([C,np.full(len(C),255,dtype=np.uint8)])
vc_path=OUT/"llorona_hunyuan_vertexcolor.glb"
vc_path.write_bytes(trimesh.exchange.gltf.export_glb(trimesh.Scene(vc)))

print("XATLAS_BEGIN")
vmapping, indices, uvs=xatlas.parametrize(
    np.ascontiguousarray(V.astype(np.float32)),
    np.ascontiguousarray(F.astype(np.uint32)),
)
vmapping=np.asarray(vmapping,dtype=np.int64)
Fuv=np.asarray(indices,dtype=np.int32)
UV=np.asarray(uvs,dtype=np.float32)
Vuv=V[vmapping]
Cuv=C[vmapping]
print("XATLAS_DONE",len(Vuv),len(Fuv),UV.min(axis=0).tolist(),UV.max(axis=0).tolist())

# CPU bake projected vertex colors into the UV atlas. The Hunyuan surface is dense
# enough that per-triangle mean color produces a surprisingly detailed stable bake.
tex=np.zeros((TEX_SIZE,TEX_SIZE,3),dtype=np.uint8)
mask=np.zeros((TEX_SIZE,TEX_SIZE),dtype=np.uint8)
px=np.empty_like(UV)
px[:,0]=UV[:,0]*(TEX_SIZE-1)
px[:,1]=(1.0-UV[:,1])*(TEX_SIZE-1)

for i,tri in enumerate(Fuv):
    pts=np.rint(px[tri]).astype(np.int32)
    color=tuple(int(x) for x in np.mean(Cuv[tri],axis=0))
    cv2.fillConvexPoly(tex,pts,color,lineType=cv2.LINE_8)
    cv2.fillConvexPoly(mask,pts,255,lineType=cv2.LINE_8)
    if i and i%25000==0:
        print("BAKE",i,"/",len(Fuv))

# Four-pixel nearest-color gutter prevents black chart edges under bilinear filtering.
valid=mask>0
if not np.any(valid):
    fail("Texture bake produced an empty atlas")
dist, inds=ndimage.distance_transform_edt(~valid,return_indices=True)
gutter=(~valid)&(dist<=6.0)
tex[gutter]=tex[inds[0][gutter],inds[1][gutter]]
Image.fromarray(tex,"RGB").save(OUT/"llorona_albedo_2k.png",optimize=True)

from trimesh.visual.material import PBRMaterial
from trimesh.visual.texture import TextureVisuals

img=Image.fromarray(tex,"RGB")
mat=PBRMaterial(
    name="Llorona_PBR",
    baseColorTexture=img,
    baseColorFactor=[255,255,255,255],
    metallicFactor=0.0,
    roughnessFactor=0.82,
    doubleSided=True,
)
visual=TextureVisuals(uv=UV,material=mat)
textured=trimesh.Trimesh(vertices=Vuv,faces=Fuv,process=False,visual=visual)
glb_path=OUT/"llorona_hq_textured.glb"
glb_path.write_bytes(trimesh.exchange.gltf.export_glb(trimesh.Scene(textured)))

# Reload exported GLB and enforce that it actually contains texture UVs.
check=trimesh.load(glb_path,force="scene")
if not check.geometry:
    fail("Exported textured GLB reload has no geometry")
g=max(check.geometry.values(),key=lambda x:len(x.faces))
has_uv=hasattr(g.visual,"uv") and g.visual.uv is not None and len(g.visual.uv)>0
material=getattr(g.visual,"material",None)
has_tex=bool(getattr(material,"baseColorTexture",None) is not None or getattr(material,"image",None) is not None)
if not has_uv or not has_tex:
    fail(f"Textured GLB validation failed: uv={has_uv} texture={has_tex} visual={type(g.visual).__name__}")

# Software review renders from the projected COLOR_0 master.
def render(angle_deg:int,name:str,size:int=768):
    a=math.radians(angle_deg)
    R=np.array([[math.cos(a),0,math.sin(a)],[0,1,0],[-math.sin(a),0,math.cos(a)]])
    Vr=(V-(V.min(0)+V.max(0))/2.0)@R.T
    sx,sy,depth=Vr[:,0],Vr[:,1],Vr[:,2]
    sc=(size-90)/max(np.ptp(sx),np.ptp(sy),1e-6)
    xx=(sx-(sx.min()+sx.max())/2)*sc+size/2
    yy=size/2-(sy-(sy.min()+sy.max())/2)*sc
    tri=Vr[F]
    normals=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
    normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-9)
    light=np.array([0.3,0.55,1.0]); light/=np.linalg.norm(light)
    shade=.48+.65*np.clip(normals@light,0,1)
    fc=np.clip(C[F].mean(axis=1)*shade[:,None]*1.35+4,0,255).astype(np.uint8)
    order=np.argsort(depth[F].mean(axis=1))
    out=Image.new("RGB",(size,size),(13,13,16)); d=ImageDraw.Draw(out)
    for fi in order:
        d.polygon([(float(xx[v]),float(yy[v])) for v in F[fi]],fill=tuple(int(v) for v in fc[fi]))
    d.text((20,18),f"La Llorona baked — {name}",fill=(245,245,245))
    out.save(OUT/f"preview_{name.lower().replace(' ','_')}.png")

for a,n in ((0,"Front"),(45,"Three Quarter"),(90,"Side"),(180,"Back")):
    render(a,n)

manifest={
    "asset":"La Llorona",
    "pipeline":"Hunyuan3D multiview geometry -> Xziel CPU 4-view color projection -> xatlas -> 2K PBR bake",
    "sourceRunId":35772555593,
    "sourceVertices":int(len(scene.geometry[max(scene.geometry,key=lambda k:len(scene.geometry[k].faces))].vertices)) if scene.geometry else None,
    "sourceFaces":int(sum(len(x.faces) for x in scene.geometry.values())),
    "runtimeVertices":int(len(Vuv)),
    "runtimeFaces":int(len(Fuv)),
    "targetFaces":TARGET_FACES,
    "heightMeters":TARGET_HEIGHT_M,
    "textureSize":TEX_SIZE,
    "hasUV":bool(has_uv),
    "hasEmbeddedBaseColorTexture":bool(has_tex),
    "outputs":{
        "texturedGLB":glb_path.name,
        "vertexColorGLB":vc_path.name,
        "albedo":"llorona_albedo_2k.png",
    }
}
(OUT/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
print("XZIEL_LLORONA_TEXTURED_GLB_READY")
print(json.dumps(manifest,indent=2))
