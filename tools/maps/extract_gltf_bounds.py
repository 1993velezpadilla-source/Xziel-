#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math
from pathlib import Path

def transform_point(m, p):
    x,y,z=p
    return (
        m[0]*x+m[4]*y+m[8]*z+m[12],
        m[1]*x+m[5]*y+m[9]*z+m[13],
        m[2]*x+m[6]*y+m[10]*z+m[14],
    )

def trs_matrix(node):
    if "matrix" in node:
        return [float(x) for x in node["matrix"]]
    tx,ty,tz=node.get("translation",[0,0,0])
    sx,sy,sz=node.get("scale",[1,1,1])
    qx,qy,qz,qw=node.get("rotation",[0,0,0,1])
    xx,yy,zz=qx*qx,qy*qy,qz*qz
    xy,xz,yz=qx*qy,qx*qz,qy*qz
    wx,wy,wz=qw*qx,qw*qy,qw*qz
    r00=1-2*(yy+zz); r01=2*(xy-wz); r02=2*(xz+wy)
    r10=2*(xy+wz); r11=1-2*(xx+zz); r12=2*(yz-wx)
    r20=2*(xz-wy); r21=2*(yz+wx); r22=1-2*(xx+yy)
    return [
        r00*sx,r10*sx,r20*sx,0,
        r01*sy,r11*sy,r21*sy,0,
        r02*sz,r12*sz,r22*sz,0,
        tx,ty,tz,1,
    ]

def matmul(a,b):
    out=[0.0]*16
    for c in range(4):
        for r in range(4):
            out[c*4+r]=sum(a[k*4+r]*b[c*4+k] for k in range(4))
    return out

I=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]

def gltf_bounds(path: Path):
    d=json.loads(path.read_text(encoding="utf-8"))
    accessors=d.get("accessors",[])
    meshes=d.get("meshes",[])
    nodes=d.get("nodes",[])
    scenes=d.get("scenes",[])
    roots=[]
    scene_index=d.get("scene",0)
    if scenes and 0 <= scene_index < len(scenes):
        roots=scenes[scene_index].get("nodes",[])
    elif nodes:
        roots=list(range(len(nodes)))

    points=[]
    used=0
    def add_mesh(mesh_index, world):
        nonlocal used
        if not isinstance(mesh_index,int) or not (0 <= mesh_index < len(meshes)): return
        for prim in meshes[mesh_index].get("primitives",[]):
            pos=prim.get("attributes",{}).get("POSITION")
            if not isinstance(pos,int) or not (0 <= pos < len(accessors)): continue
            a=accessors[pos]
            mn=a.get("min"); mx=a.get("max")
            if not (isinstance(mn,list) and isinstance(mx,list) and len(mn)>=3 and len(mx)>=3): continue
            used += 1
            for x in (float(mn[0]),float(mx[0])):
                for y in (float(mn[1]),float(mx[1])):
                    for z in (float(mn[2]),float(mx[2])):
                        points.append(transform_point(world,(x,y,z)))

    seen=set()
    def visit(idx,parent):
        if not isinstance(idx,int) or not (0 <= idx < len(nodes)): return
        key=(idx,tuple(round(x,8) for x in parent))
        if key in seen: return
        seen.add(key)
        node=nodes[idx]
        world=matmul(parent,trs_matrix(node))
        if "mesh" in node: add_mesh(node["mesh"],world)
        for ch in node.get("children",[]): visit(ch,world)
    for idx in roots: visit(idx,I)

    if not points:
        # Fallback: accessor-space bounds if no scene nodes reference the mesh.
        for mesh in meshes:
            for prim in mesh.get("primitives",[]):
                pos=prim.get("attributes",{}).get("POSITION")
                if isinstance(pos,int) and 0 <= pos < len(accessors):
                    a=accessors[pos]
                    mn=a.get("min"); mx=a.get("max")
                    if isinstance(mn,list) and isinstance(mx,list) and len(mn)>=3 and len(mx)>=3:
                        used += 1
                        points.extend([
                            (float(mn[0]),float(mn[1]),float(mn[2])),
                            (float(mx[0]),float(mx[1]),float(mx[2])),
                        ])
    if not points:
        return {"file":str(path),"position_accessors":used,"bounds":None}

    mn=[min(p[i] for p in points) for i in range(3)]
    mx=[max(p[i] for p in points) for i in range(3)]
    center=[(mn[i]+mx[i])/2 for i in range(3)]
    extent=[(mx[i]-mn[i])/2 for i in range(3)]
    return {
        "file":str(path),
        "position_accessors":used,
        "bounds":{
            "min":{"x":mn[0],"y":mn[1],"z":mn[2]},
            "max":{"x":mx[0],"y":mx[1],"z":mx[2]},
            "center":{"x":center[0],"y":center[1],"z":center[2]},
            "extent":{"x":extent[0],"y":extent[1],"z":extent[2]},
        }
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("root",type=Path)
    ap.add_argument("output",type=Path)
    args=ap.parse_args()
    rows={}
    for p in sorted(args.root.rglob("*.gltf")):
        low=p.stem.lower()
        if "chalk_buy_" not in low: continue
        key=low.split("chalk_buy_",1)[1]
        rows[key]=gltf_bounds(p)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(rows,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(rows,indent=2))
    return 0 if len(rows)==9 and all(v.get("bounds") for v in rows.values()) else 3
if __name__=="__main__":
    raise SystemExit(main())
