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


def choose_pow2(value: float, maximum: int) -> int:
    target=max(256, int(math.ceil(value)))
    power=1
    while power < target:
        power <<= 1
    return min(power, maximum)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--xzsm", required=True)
    ap.add_argument("--source-size", type=int, default=1024)
    ap.add_argument("--target-tpm", type=float, default=128.0)
    ap.add_argument("--max-tile-size", type=int, default=2048)
    ap.add_argument("--match", default="Exterior04")
    ap.add_argument("--padding-pixels", type=int, default=12)
    ap.add_argument("--report", required=True)
    args=ap.parse_args()

    data=Path(args.xzsm).read_bytes()
    magic,version,batch_count,total_vertices,total_indices=HEADER.unpack_from(data,0)
    if magic != b"XZSM" or version != 5:
        raise RuntimeError("expected XZSM v5")

    offset=HEADER.size
    batches=[]
    total_astc_bytes=0
    total_source_crop_pixels=0

    for batch_index in range(batch_count):
        vertex_count,index_count,texture_raw,flags=BATCH_PREFIX.unpack_from(data,offset)
        offset += BATCH_PREFIX.size
        texture=cstr(texture_raw)
        normal=cstr(data[offset:offset+FIXED]); offset += FIXED
        orm=cstr(data[offset:offset+FIXED]); offset += FIXED
        emissive=cstr(data[offset:offset+FIXED]); offset += FIXED
        offset += BASE_COLOR.size + METAL_ROUGH.size + EMISSIVE.size + NORMAL_OCCL.size
        bounds=BOUNDS.unpack_from(data,offset); offset += BOUNDS.size

        verts=[]
        for i in range(vertex_count):
            vals=VERTEX.unpack_from(data,offset+i*VERTEX.size)
            verts.append(((vals[0],vals[1],vals[2]),(vals[6],vals[7])))
        offset += vertex_count*VERTEX.size

        indices=struct.unpack_from("<"+"H"*index_count,data,offset)
        offset += index_count*2

        if args.match not in texture:
            continue

        us=[v[1][0] for v in verts]
        vs=[v[1][1] for v in verts]
        u0=max(0.0,min(us)); u1=min(1.0,max(us))
        v0=max(0.0,min(vs)); v1=min(1.0,max(vs))
        uv_w=max(1.0e-6,u1-u0)
        uv_h=max(1.0e-6,v1-v0)

        world_area=0.0
        uv_area=0.0
        tri_count=0
        for i in range(0,index_count,3):
            if i+2 >= index_count:
                break
            i0,i1,i2=indices[i:i+3]
            p0,t0=verts[i0]; p1,t1=verts[i1]; p2,t2=verts[i2]
            wa=tri_area_3d(p0,p1,p2)
            ua=tri_area_uv(t0,t1,t2)
            if wa <= 1.0e-12 or ua <= 1.0e-14:
                continue
            world_area += wa
            uv_area += ua
            tri_count += 1

        if world_area <= 0 or uv_area <= 0:
            continue

        source_texels=uv_area*args.source_size*args.source_size
        source_tpm=math.sqrt(source_texels/world_area)
        required_linear_scale=args.target_tpm/max(source_tpm,1.0e-6)

        # For a cropped tile, preserve aspect ratio of the batch UV bounding box.
        crop_w=max(1.0,uv_w*args.source_size)
        crop_h=max(1.0,uv_h*args.source_size)
        long_source=max(crop_w,crop_h)
        target_long=long_source*required_linear_scale
        tile_long=choose_pow2(target_long,args.max_tile_size)
        aspect=crop_w/crop_h
        if aspect >= 1.0:
            tile_w=tile_long
            tile_h=choose_pow2(tile_long/aspect,args.max_tile_size)
        else:
            tile_h=tile_long
            tile_w=choose_pow2(tile_long*aspect,args.max_tile_size)

        # ASTC 6x6 stores one 16-byte block. Include ~4/3 mip-chain overhead.
        blocks_x=math.ceil(tile_w/6)
        blocks_y=math.ceil(tile_h/6)
        astc_bytes=int(blocks_x*blocks_y*16*(4.0/3.0))
        total_astc_bytes += astc_bytes
        total_source_crop_pixels += int(crop_w*crop_h)

        achieved_scale=min(tile_w/crop_w,tile_h/crop_h)
        achieved_tpm=source_tpm*achieved_scale

        batches.append({
            "batchIndex":batch_index,
            "texture":texture,
            "triangles":tri_count,
            "worldAreaM2":world_area,
            "uvArea":uv_area,
            "uvBounds":[u0,v0,u1,v1],
            "sourceCropPixels":[crop_w,crop_h],
            "sourceTexelsPerMeter":source_tpm,
            "requiredLinearScaleForTarget":required_linear_scale,
            "plannedTileSize":[tile_w,tile_h],
            "plannedAchievedTexelsPerMeter":achieved_tpm,
            "meetsTarget":achieved_tpm >= args.target_tpm,
            "estimatedAstc6x6BytesWithMips":astc_bytes,
            "bounds":[*bounds],
        })

    if not batches:
        raise RuntimeError("no exterior batches found")

    meets=sum(1 for b in batches if b["meetsTarget"])
    report={
        "schemaVersion":1,
        "method":"PER_BATCH_UV_CROP_STREAMING_PLAN_V1",
        "sourceAtlasSize":[args.source_size,args.source_size],
        "targetTexelsPerMeter":args.target_tpm,
        "maxTileSize":args.max_tile_size,
        "exteriorBatchCount":len(batches),
        "batchesMeetingTargetAtMaxTile":meets,
        "allBatchesMeetTarget":meets == len(batches),
        "estimatedResidentIfAllTilesAstc6x6MiB":total_astc_bytes/(1024*1024),
        "sourceCropPixelSum":total_source_crop_pixels,
        "recommendation":(
            "STREAM_BATCH_TILES"
            if meets >= int(len(batches)*0.85)
            else "NEEDS_MULTI_TILE_OR_HIGHER_SOURCE"
        ),
        "batches":batches,
    }
    Path(args.report).parent.mkdir(parents=True,exist_ok=True)
    Path(args.report).write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("XZIEL_ST_GILES_UV_TILE_PLAN",json.dumps({
        "batches":len(batches),
        "meetsTarget":meets,
        "allMeet":report["allBatchesMeetTarget"],
        "allResidentAstcMiB":round(report["estimatedResidentIfAllTilesAstc6x6MiB"],2),
        "recommendation":report["recommendation"],
    },separators=(",",":")))


if __name__=="__main__":
    main()
