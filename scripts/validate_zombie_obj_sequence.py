#!/usr/bin/env python3
"""Validate an animated OBJ sequence before Quake MDL conversion."""
import argparse, hashlib, json
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument("directory")
p.add_argument("--frames",type=int,default=211)
p.add_argument("--max-verts",type=int,default=2048)
p.add_argument("--max-tris",type=int,default=2048)
args=p.parse_args()

root=Path(args.directory)
files=[root/f"{i:03d}.obj" for i in range(args.frames)]
missing=[str(x) for x in files if not x.is_file()]
if missing:
    raise SystemExit("missing OBJ frames: "+", ".join(missing[:10]))

def parse(path):
    counts={"v":0,"vt":0,"vn":0,"f":0}
    topology=[]
    unified=set()
    with path.open("r",encoding="ascii") as fh:
        for raw in fh:
            line=raw.strip()
            if not line or line.startswith("#") or line.startswith("g "):
                continue
            head=line.split(None,1)[0]
            if head in counts:
                counts[head]+=1
            if head=="vt":
                topology.append(line)
            elif head=="f":
                fields=line.split()[1:]
                if len(fields)!=3:
                    raise RuntimeError(f"{path}: non-triangle face: {line}")
                topology.append(line)
                unified.update(fields)
    digest=hashlib.sha256("\n".join(topology).encode()).hexdigest()
    return counts,digest,len(unified)

base_counts,base_topology,base_unified=parse(files[0])
if base_counts["v"]<=0 or base_counts["f"]<=0:
    raise SystemExit("empty base geometry")
if base_counts["vn"]!=base_counts["v"]:
    raise SystemExit(f"base normal/vertex mismatch: {base_counts}")
if base_unified>args.max_verts:
    raise SystemExit(f"unified vertex count {base_unified} exceeds {args.max_verts}")
if base_counts["f"]>args.max_tris:
    raise SystemExit(f"triangle count {base_counts['f']} exceeds {args.max_tris}")

for path in files[1:]:
    counts,digest,unified=parse(path)
    if counts!=base_counts:
        raise SystemExit(f"{path}: OBJ counts changed {counts} != {base_counts}")
    if digest!=base_topology:
        raise SystemExit(f"{path}: face/UV topology changed")
    if unified!=base_unified:
        raise SystemExit(f"{path}: unified vertex count changed {unified} != {base_unified}")

report={
    "directory":str(root),
    "frames":len(files),
    "counts_per_frame":base_counts,
    "unified_vertices":base_unified,
    "topology_sha256":base_topology,
    "limits":{"vertices":args.max_verts,"triangles":args.max_tris},
}
print(json.dumps(report,indent=2))
(root.parent/(root.name+"_topology_report.json")).write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
