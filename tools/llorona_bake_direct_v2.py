#!/usr/bin/env python3
from __future__ import annotations
import json, math, os, sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
from scipy import ndimage
import trimesh
import xatlas

SRC=Path(os.environ.get("LLORONA_HUNYUAN_DIR","in/hunyuan"))
OUT=Path(os.environ.get("LLORONA_V2_OUT","out/llorona-hq-v2"))
TEX=int(os.environ.get("LLORONA_TEXTURE_SIZE","4096"))
FACES=int(os.environ.get("LLORONA_TARGET_FACES","120000"))
HEIGHT=float(os.environ.get("LLORONA_HEIGHT_M","1.72"))
OUT.mkdir(parents=True,exist_ok=True)

def fail(msg):
    print(f"::error::{msg}")
    raise SystemExit(1)

def find(name):
    hits=list(SRC.rglob(name))
    if not hits: fail(f"missing {name}")
    return hits[0]

mesh_path=find("llorona_hunyuan_mv_hq.glb")
refs={n:find(f"{n}.png") for n in ("front","back","left","right")}

scene=trimesh.load(mesh_path,force="scene")
if not scene.geometry: fail("source GLB has no geometry")
mesh=max(scene.geometry.values(),key=lambda g:len(g.faces)).copy()
mesh.remove_unreferenced_vertices()
raw=(len(mesh.vertices),len(mesh.faces))

keep=np.asarray(mesh.unique_faces(),dtype=bool)&np.asarray(mesh.nondegenerate_faces(),dtype=bool)
mesh.update_faces(keep); mesh.remove_unreferenced_vertices()
clean=(len(mesh.vertices),len(mesh.faces))

if len(mesh.faces)>FACES:
    cand=mesh.simplify_quadric_decimation(face_count=FACES,aggression=5)
    cand.remove_unreferenced_vertices()
    k=np.asarray(cand.unique_faces(),dtype=bool)&np.asarray(cand.nondegenerate_faces(),dtype=bool)
    cand.update_faces(k); cand.remove_unreferenced_vertices()
    if len(cand.vertices)>=10000 and len(cand.faces)>=60000:
        mesh=cand
print("TOPOLOGY",raw,"->",clean,"->",(len(mesh.vertices),len(mesh.faces)))
if len(mesh.faces)<60000: fail("mesh collapsed")

V=np.asarray(mesh.vertices,dtype=np.float64)
mins=V.min(0); maxs=V.max(0)
scale=HEIGHT/max(maxs[1]-mins[1],1e-9)
V=(V-np.array([0.0,mins[1],0.0]))*scale
mins=V.min(0); maxs=V.max(0); extent=maxs-mins
F=np.asarray(mesh.faces,dtype=np.int32)

# UV unwrap.
vmapping,uvfaces,uv=xatlas.parametrize(
    np.ascontiguousarray(V.astype(np.float32)),
    np.ascontiguousarray(F.astype(np.uint32)),
)
vmapping=np.asarray(vmapping,dtype=np.int64)
UF=np.asarray(uvfaces,dtype=np.int32)
UV=np.asarray(uv,dtype=np.float32)
VU=V[vmapping]
print("XATLAS",len(VU),len(UF),UV.min(0).tolist(),UV.max(0).tolist())

# Prepare references. Keep actual pixels, only modest contrast/sharpness.
images={}
bboxes={}
for name,p in refs.items():
    im=Image.open(p).convert("RGB")
    im=ImageEnhance.Contrast(im).enhance(1.06)
    im=ImageEnhance.Sharpness(im).enhance(1.12)
    arr=np.asarray(im,dtype=np.uint8)
    # Estimate background from border and find subject relative to it.
    border=np.concatenate([arr[:10].reshape(-1,3),arr[-10:].reshape(-1,3),arr[:, :10].reshape(-1,3),arr[:, -10:].reshape(-1,3)])
    bg=np.median(border,axis=0)
    diff=np.linalg.norm(arr.astype(np.float32)-bg.astype(np.float32),axis=2)
    lum=cv2.cvtColor(arr,cv2.COLOR_RGB2GRAY)
    m=((diff>12)|(lum>18)).astype(np.uint8)
    # Largest useful silhouette region, then generous padding.
    ys,xs=np.where(m>0)
    if len(xs)==0: fail(f"empty ref {name}")
    x0,x1=int(xs.min()),int(xs.max()); y0,y1=int(ys.min()),int(ys.max())
    pad_x=max(2,int((x1-x0)*0.025)); pad_y=max(2,int((y1-y0)*0.015))
    x0=max(0,x0-pad_x); x1=min(arr.shape[1]-1,x1+pad_x)
    y0=max(0,y0-pad_y); y1=min(arr.shape[0]-1,y1+pad_y)
    images[name]=arr
    bboxes[name]=(x0,y0,x1,y1)
    print("REF",name,arr.shape,"bbox",bboxes[name])

# View directions in Hunyuan Y-up coordinates.
cfg={
    "front":(np.array([0.,0.,1.]),"x",False),
    "back": (np.array([0.,0.,-1.]),"x",True),
    "left": (np.array([1.,0.,0.]),"z",True),
    "right":(np.array([-1.,0.,0.]),"z",False),
}
view_names=("front","back","left","right")
dirs=np.stack([cfg[n][0] for n in view_names],axis=0)

# UV canvas.
tex=np.zeros((TEX,TEX,3),dtype=np.uint8)
conf=np.zeros((TEX,TEX),dtype=np.float32)
occ=np.zeros((TEX,TEX),dtype=np.uint8)
uvpx=np.empty_like(UV,dtype=np.float64)
uvpx[:,0]=UV[:,0]*(TEX-1)
uvpx[:,1]=(1.0-UV[:,1])*(TEX-1)

def bilinear(arr,x,y):
    h,w=arr.shape[:2]
    x=np.clip(x,0,w-1.001); y=np.clip(y,0,h-1.001)
    x0=np.floor(x).astype(np.int32); y0=np.floor(y).astype(np.int32)
    x1=np.minimum(x0+1,w-1); y1=np.minimum(y0+1,h-1)
    dx=(x-x0)[:,None]; dy=(y-y0)[:,None]
    c00=arr[y0,x0].astype(np.float32); c10=arr[y0,x1].astype(np.float32)
    c01=arr[y1,x0].astype(np.float32); c11=arr[y1,x1].astype(np.float32)
    return c00*(1-dx)*(1-dy)+c10*dx*(1-dy)+c01*(1-dx)*dy

def project(P,name):
    x0,y0,x1,y1=bboxes[name]
    _,axis,flip=cfg[name]
    if axis=="x":
        u=(P[:,0]-mins[0])/max(extent[0],1e-9)
    else:
        u=(P[:,2]-mins[2])/max(extent[2],1e-9)
    if flip: u=1.0-u
    vv=1.0-(P[:,1]-mins[1])/max(extent[1],1e-9)
    x=x0+u*(x1-x0); y=y0+vv*(y1-y0)
    return x,y

# Per-pixel barycentric bake. Unlike v1, no triangle-average color.
for fi,tri in enumerate(UF):
    p2=uvpx[tri]
    minx=max(0,int(math.floor(p2[:,0].min()))); maxx=min(TEX-1,int(math.ceil(p2[:,0].max())))
    miny=max(0,int(math.floor(p2[:,1].min()))); maxy=min(TEX-1,int(math.ceil(p2[:,1].max())))
    if maxx<minx or maxy<miny: continue
    x0,y0=p2[0]; x1,y1=p2[1]; x2,y2=p2[2]
    den=(y1-y2)*(x0-x2)+(x2-x1)*(y0-y2)
    if abs(den)<1e-8: continue
    yy,xx=np.mgrid[miny:maxy+1,minx:maxx+1]
    X=xx.ravel()+0.5; Y=yy.ravel()+0.5
    a=((y1-y2)*(X-x2)+(x2-x1)*(Y-y2))/den
    b=((y2-y0)*(X-x2)+(x0-x2)*(Y-y2))/den
    c=1.0-a-b
    inside=(a>=-1e-4)&(b>=-1e-4)&(c>=-1e-4)
    if not np.any(inside): continue
    a=a[inside]; b=b[inside]; c=c[inside]
    PX=xx.ravel()[inside]; PY=yy.ravel()[inside]
    P=a[:,None]*VU[tri[0]]+b[:,None]*VU[tri[1]]+c[:,None]*VU[tri[2]]

    e1=VU[tri[1]]-VU[tri[0]]; e2=VU[tri[2]]-VU[tri[0]]
    n=np.cross(e1,e2); nl=np.linalg.norm(n)
    if nl<1e-10: continue
    n=n/nl
    weights=np.maximum(dirs@n,0.0)**5
    order=np.argsort(weights)[::-1]

    out=np.zeros((len(P),3),dtype=np.float32)
    best=np.zeros(len(P),dtype=np.float32)
    # Prefer dominant view. Near silhouettes allow secondary views only if the
    # dominant sample lands on background.
    for oi in order:
        if weights[oi]<=1e-5: continue
        name=view_names[oi]; arr=images[name]
        sx,sy=project(P,name)
        col=bilinear(arr,sx,sy)
        # Reject near-background samples.
        gray=0.2126*col[:,0]+0.7152*col[:,1]+0.0722*col[:,2]
        valid=gray>9
        take=(best==0)&valid
        if np.any(take):
            out[take]=col[take]; best[take]=weights[oi]
    good=best>0
    if np.any(good):
        tex[PY[good],PX[good]]=np.clip(out[good],0,255).astype(np.uint8)
        conf[PY[good],PX[good]]=best[good]
    occ[PY,PX]=255
    if fi and fi%20000==0:
        print("BAKE",fi,"/",len(UF))

occupied=occ>0
direct=(conf>0)&occupied
direct_ratio=float(direct.sum()/max(1,occupied.sum()))
print("DIRECT_COVERAGE",direct_ratio)

# Fill only UV-chart holes from the nearest valid projected texel.
if direct.any():
    dist,inds=ndimage.distance_transform_edt(~direct,return_indices=True)
    holes=occupied&(~direct)
    tex[holes]=tex[inds[0][holes],inds[1][holes]]

# Small dilation gutter outside charts for bilinear filtering.
dist,inds=ndimage.distance_transform_edt(~occupied,return_indices=True)
gutter=(~occupied)&(dist<=8)
tex[gutter]=tex[inds[0][gutter],inds[1][gutter]]

# Very restrained final texture enhancement: preserve detail, don't paint it.
pil=Image.fromarray(tex,"RGB")
pil=pil.filter(ImageFilter.UnsharpMask(radius=0.8,percent=65,threshold=4))
pil.save(OUT/"llorona_albedo_4k.png",optimize=True)

# Quality metrics inside occupied UVs.
gray=cv2.cvtColor(np.asarray(pil),cv2.COLOR_RGB2GRAY)
lap=cv2.Laplacian(gray,cv2.CV_64F)
sharp=float(lap[occupied].var()) if occupied.any() else 0.0
black=float(((gray<5)&occupied).sum()/max(1,occupied.sum()))
print("QUALITY sharpness",sharp,"black_ratio",black)
if direct_ratio<0.50: fail(f"projection coverage too low: {direct_ratio:.3f}")
if black>0.015: fail(f"too many black UV holes: {black:.4f}")
if sharp<18.0: fail(f"texture too blurry: {sharp:.2f}")

# PBR GLB.
from trimesh.visual.material import PBRMaterial
from trimesh.visual.texture import TextureVisuals
mat=PBRMaterial(
    name="Llorona_HQ_v2",
    baseColorTexture=pil,
    baseColorFactor=[255,255,255,255],
    metallicFactor=0.0,
    roughnessFactor=0.82,
    doubleSided=True,
)
visual=TextureVisuals(uv=UV,material=mat)
outmesh=trimesh.Trimesh(vertices=VU,faces=UF,process=False,visual=visual)
glb=OUT/"llorona_hq_v2.glb"
glb.write_bytes(trimesh.exchange.gltf.export_glb(trimesh.Scene(outmesh)))

# Reload gate.
chk=trimesh.load(glb,force="scene")
g=max(chk.geometry.values(),key=lambda x:len(x.faces))
has_uv=hasattr(g.visual,"uv") and g.visual.uv is not None and len(g.visual.uv)>0
m=getattr(g.visual,"material",None)
has_tex=bool(getattr(m,"baseColorTexture",None) is not None or getattr(m,"image",None) is not None)
if not has_uv or not has_tex: fail(f"GLB reload failed uv={has_uv} tex={has_tex}")

# Preview using UV-vertex samples from final atlas.
arr=np.asarray(pil)
tx=np.clip(np.rint(UV[:,0]*(TEX-1)).astype(int),0,TEX-1)
ty=np.clip(np.rint((1-UV[:,1])*(TEX-1)).astype(int),0,TEX-1)
VC=arr[ty,tx]

def render(angle,name,size=900):
    a=math.radians(angle)
    R=np.array([[math.cos(a),0,math.sin(a)],[0,1,0],[-math.sin(a),0,math.cos(a)]])
    C=(VU.min(0)+VU.max(0))/2
    vr=(VU-C)@R.T
    sx,sy,depth=vr[:,0],vr[:,1],vr[:,2]
    sc=(size-110)/max(np.ptp(sx),np.ptp(sy),1e-8)
    px=(sx-(sx.min()+sx.max())/2)*sc+size/2
    py=size/2-(sy-(sy.min()+sy.max())/2)*sc
    tri=vr[UF]
    fn=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]); fn/=np.maximum(np.linalg.norm(fn,axis=1,keepdims=True),1e-9)
    light=np.array([.3,.55,1.]); light/=np.linalg.norm(light)
    shade=.52+.55*np.clip(fn@light,0,1)
    fc=np.clip(VC[UF].mean(1)*shade[:,None]*1.12,0,255).astype(np.uint8)
    order=np.argsort(depth[UF].mean(1))
    im=Image.new("RGB",(size,size),(12,12,15)); d=ImageDraw.Draw(im)
    for k in order:
        d.polygon([(float(px[v]),float(py[v])) for v in UF[k]],fill=tuple(int(x) for x in fc[k]))
    d.text((22,18),f"La Llorona HQ v2 — {name}",fill=(245,245,245))
    im.save(OUT/f"preview_{name.lower().replace(' ','_')}.png")

for a,n in ((0,"Front"),(45,"Three Quarter"),(90,"Side"),(180,"Back")): render(a,n)

manifest={
    "asset":"La Llorona",
    "pipeline":"Hunyuan HQ clean topology -> xatlas -> per-pixel 4-view projection",
    "sourceRunId":35772555593,
    "textureSize":TEX,
    "faces":int(len(UF)),
    "uvVertices":int(len(VU)),
    "directCoverage":direct_ratio,
    "sharpnessLaplacianVariance":sharp,
    "blackUvRatio":black,
    "hasUV":bool(has_uv),
    "hasEmbeddedTexture":bool(has_tex),
    "masterVisualReference":"assets/characters/llorona/reference/master/llorona_haunted_waters_master.jpg",
}
(OUT/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
print("XZIEL_LLORONA_HQ_V2_READY")
print(json.dumps(manifest,indent=2))
