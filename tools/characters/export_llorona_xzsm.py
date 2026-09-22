#!/usr/bin/env python3
from __future__ import annotations
import json, math, os, shutil, struct
from pathlib import Path

import numpy as np
import trimesh

SOURCE_DIR=Path(os.environ.get("LLORONA_SOURCE_DIR","build/llorona-artifact"))
OUT=Path(os.environ.get("LLORONA_NATIVE_OUT","build/llorona-native"))
MODEL_DIR=OUT/"models/xziel/characters/llorona"
TEX_DIR=OUT/"textures/xziel/characters/llorona"
MODEL_DIR.mkdir(parents=True,exist_ok=True)
TEX_DIR.mkdir(parents=True,exist_ok=True)

def find(name):
    hits=list(SOURCE_DIR.rglob(name))
    if not hits:
        raise SystemExit(f"missing {name} under {SOURCE_DIR}")
    return hits[0]

glb=find("llorona_hq_textured.glb")
albedo=find("llorona_albedo_2k.png")
scene=trimesh.load(glb,force="scene")
if not scene.geometry:
    raise SystemExit("textured GLB has no geometry")
mesh=max(scene.geometry.values(),key=lambda g:len(g.faces)).copy()
mesh.remove_unreferenced_vertices()

V=np.asarray(mesh.vertices,dtype=np.float32)
F=np.asarray(mesh.faces,dtype=np.int64)
N=np.asarray(mesh.vertex_normals,dtype=np.float32)
uv=getattr(mesh.visual,"uv",None)
if uv is None or len(uv)!=len(V):
    raise SystemExit(f"GLB UV mismatch: verts={len(V)} uv={0 if uv is None else len(uv)}")
UV=np.asarray(uv,dtype=np.float32)

if len(F)<60000 or len(V)<10000:
    raise SystemExit(f"refusing collapsed Llorona mesh: verts={len(V)} faces={len(F)}")

# Android native static mesh batches use uint16 indices. 18k triangles keeps
# the worst-case 54k unique triangle vertices safely under 65535.
MAX_TRIS=18000
texture_name="textures/xziel/characters/llorona/llorona_albedo"
batches=[]
for start in range(0,len(F),MAX_TRIS):
    faces=F[start:start+MAX_TRIS]
    used=np.unique(faces.reshape(-1))
    if len(used)>65535:
        raise SystemExit(f"batch vertex overflow: {len(used)}")
    remap=np.full(len(V),-1,dtype=np.int64)
    remap[used]=np.arange(len(used),dtype=np.int64)
    idx=remap[faces].reshape(-1).astype(np.uint16)
    bv=V[used]; bn=N[used]; buv=UV[used]
    mn=bv.min(axis=0); mx=bv.max(axis=0)
    batches.append((used,idx,mn,mx))

total_vertices=sum(len(x[0]) for x in batches)
total_indices=sum(len(x[1]) for x in batches)
model=MODEL_DIR/"llorona.xzsm"
with model.open("wb") as f:
    f.write(struct.pack("<4sIIII",b"XZSM",3,len(batches),total_vertices,total_indices))
    for used,idx,mn,mx in batches:
        tex=texture_name.encode("utf-8")
        if len(tex)>=96:
            raise SystemExit("texture path too long")
        field=tex+b"\0"*(96-len(tex))
        f.write(struct.pack("<II96s6f",len(used),len(idx),field,
                            float(mn[0]),float(mn[1]),float(mn[2]),
                            float(mx[0]),float(mx[1]),float(mx[2])))
        for vi in used:
            n=N[vi]
            nl=float(np.linalg.norm(n))
            if not math.isfinite(nl) or nl<1e-8:
                n=np.array([0.0,1.0,0.0],dtype=np.float32)
            else:
                n=n/nl
            # XZSM's PNG sampler convention follows the existing native church
            # exporter: V is flipped from glTF/xatlas UV space.
            u=float(UV[vi,0])
            v=1.0-float(UV[vi,1])
            f.write(struct.pack("<8f4B",
                float(V[vi,0]),float(V[vi,1]),float(V[vi,2]),
                float(n[0]),float(n[1]),float(n[2]),
                u,v,255,255,255,255))
        f.write(idx.astype("<u2",copy=False).tobytes())

shutil.copy2(albedo,TEX_DIR/"llorona_albedo.png")
report={
    "format":"XZSM","version":3,"vertexStrideBytes":36,
    "sourceGlb":glb.name,"sourceVertices":int(len(V)),"sourceTriangles":int(len(F)),
    "batchCount":len(batches),"totalVertices":int(total_vertices),
    "totalIndices":int(total_indices),"runtimeTriangles":int(total_indices//3),
    "texture":"textures/xziel/characters/llorona/llorona_albedo.png",
    "textureBytes":int((TEX_DIR/"llorona_albedo.png").stat().st_size),
    "modelBytes":int(model.stat().st_size),
    "boundsMin":[float(x) for x in V.min(axis=0)],
    "boundsMax":[float(x) for x in V.max(axis=0)],
}
(OUT/"llorona_native_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print("XZIEL_LLORONA_XZSM_READY",json.dumps(report))
