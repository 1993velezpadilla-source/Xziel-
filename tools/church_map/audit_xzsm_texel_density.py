#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import struct
from pathlib import Path

import numpy as np

HEADER = struct.Struct("<4sIIII")
BATCH_PREFIX = struct.Struct("<II96sI")
FIXED = 96
BASE_COLOR = struct.Struct("<4f")
METAL_ROUGH = struct.Struct("<2f")
EMISSIVE = struct.Struct("<3f")
NORMAL_OCCL = struct.Struct("<2f")
BOUNDS = struct.Struct("<6f")
VERTEX = struct.Struct("<8f4B")


def cstr(raw: bytes) -> str:
    return raw.split(b"\0", 1)[0].decode("utf-8", errors="replace")


def tri_area_3d(a, b, c):
    ab = np.asarray(b, dtype=np.float64) - np.asarray(a, dtype=np.float64)
    ac = np.asarray(c, dtype=np.float64) - np.asarray(a, dtype=np.float64)
    return 0.5 * float(np.linalg.norm(np.cross(ab, ac)))


def tri_area_uv(a, b, c):
    ax, ay = a
    bx, by = b
    cx, cy = c
    return 0.5 * abs((bx-ax)*(cy-ay) - (by-ay)*(cx-ax))


def weighted_percentile(values, weights, percentile):
    order = np.argsort(values)
    v = np.asarray(values, dtype=np.float64)[order]
    w = np.asarray(weights, dtype=np.float64)[order]
    c = np.cumsum(w)
    if c[-1] <= 0:
        return 0.0
    target = c[-1] * percentile
    idx = int(np.searchsorted(c, target, side="left"))
    return float(v[min(idx, len(v)-1)])


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--xzsm", required=True)
    ap.add_argument("--texture-width", type=int, default=1024)
    ap.add_argument("--texture-height", type=int, default=1024)
    ap.add_argument("--match", default="Exterior04")
    ap.add_argument("--report", required=True)
    args=ap.parse_args()

    data=Path(args.xzsm).read_bytes()
    if len(data) < HEADER.size:
        raise RuntimeError("XZSM truncated")
    magic, version, batch_count, total_vertices, total_indices = HEADER.unpack_from(data,0)
    if magic != b"XZSM":
        raise RuntimeError(f"bad magic {magic!r}")
    if version != 5:
        raise RuntimeError(f"expected XZSM v5, got {version}")

    offset=HEADER.size
    densities=[]
    weights=[]
    matched_batches=0
    matched_triangles=0
    matched_world_area=0.0
    matched_uv_area=0.0
    matched_vertices=0

    for batch_index in range(batch_count):
        if offset + BATCH_PREFIX.size > len(data):
            raise RuntimeError("truncated batch prefix")
        vertex_count,index_count,texture_raw,flags=BATCH_PREFIX.unpack_from(data,offset)
        offset += BATCH_PREFIX.size

        texture=cstr(texture_raw)
        normal=cstr(data[offset:offset+FIXED]); offset += FIXED
        orm=cstr(data[offset:offset+FIXED]); offset += FIXED
        emissive=cstr(data[offset:offset+FIXED]); offset += FIXED

        offset += BASE_COLOR.size
        offset += METAL_ROUGH.size
        offset += EMISSIVE.size
        offset += NORMAL_OCCL.size
        offset += BOUNDS.size

        vertex_bytes=vertex_count*VERTEX.size
        index_bytes=index_count*2
        if offset + vertex_bytes + index_bytes > len(data):
            raise RuntimeError(f"truncated payload at batch {batch_index}")

        verts=[]
        for i in range(vertex_count):
            vals=VERTEX.unpack_from(data,offset+i*VERTEX.size)
            verts.append(((vals[0],vals[1],vals[2]),(vals[6],vals[7])))
        offset += vertex_bytes

        indices=struct.unpack_from("<"+"H"*index_count,data,offset)
        offset += index_bytes

        if args.match not in texture:
            continue

        matched_batches += 1
        matched_vertices += vertex_count

        for i in range(0,index_count,3):
            if i+2 >= index_count:
                break
            i0,i1,i2=indices[i:i+3]
            p0,uv0=verts[i0]
            p1,uv1=verts[i1]
            p2,uv2=verts[i2]
            world=tri_area_3d(p0,p1,p2)
            uv=tri_area_uv(uv0,uv1,uv2)
            if world <= 1.0e-12 or uv <= 1.0e-14:
                continue
            texels=uv*args.texture_width*args.texture_height
            density=math.sqrt(texels/world)
            if not math.isfinite(density):
                continue
            densities.append(density)
            weights.append(world)
            matched_triangles += 1
            matched_world_area += world
            matched_uv_area += uv

    if not densities:
        raise RuntimeError(f"no triangles matched texture token {args.match!r}")

    arr=np.asarray(densities,dtype=np.float64)
    w=np.asarray(weights,dtype=np.float64)

    report={
        "schemaVersion":1,
        "xzsmVersion":version,
        "textureMatch":args.match,
        "textureSize":[args.texture_width,args.texture_height],
        "matchedBatches":matched_batches,
        "matchedVertices":matched_vertices,
        "matchedTriangles":matched_triangles,
        "matchedWorldAreaM2":matched_world_area,
        "matchedUvArea":matched_uv_area,
        "texelsPerMeter":{
            "areaWeightedP10":weighted_percentile(arr,w,0.10),
            "areaWeightedP25":weighted_percentile(arr,w,0.25),
            "areaWeightedMedian":weighted_percentile(arr,w,0.50),
            "areaWeightedP75":weighted_percentile(arr,w,0.75),
            "areaWeightedP90":weighted_percentile(arr,w,0.90),
            "min":float(arr.min()),
            "max":float(arr.max()),
        },
        "diagnosis":{
            "closeFpsCameraAt1080p":(
                "UNDERRESOLVED"
                if weighted_percentile(arr,w,0.50) < 128.0
                else "ADEQUATE"
            ),
            "note":"This measures source texel density from exported UVs and world-space triangle area. It does not infer visual quality from screenshot sharpness."
        }
    }
    Path(args.report).parent.mkdir(parents=True,exist_ok=True)
    Path(args.report).write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("XZIEL_ST_GILES_TEXEL_DENSITY",json.dumps(report,separators=(",",":")))


if __name__=="__main__":
    main()
