#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import struct
from pathlib import Path

HEADER=struct.Struct("<4sIIII")
BATCH_PREFIX=struct.Struct("<II96sI")
FIXED=96
BASE_COLOR=struct.Struct("<4f")
METAL_ROUGH=struct.Struct("<2f")
EMISSIVE=struct.Struct("<3f")
NORMAL_OCCL=struct.Struct("<2f")
BOUNDS=struct.Struct("<6f")
VERTEX=struct.Struct("<8f4B")


def cstr(raw: bytes)->str:
    return raw.split(b"\0",1)[0].decode("utf-8",errors="replace")


def astc6x6_mips_bytes(size:int)->int:
    blocks=math.ceil(size/6)
    return int(blocks*blocks*16*(4.0/3.0))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--xzsm",required=True)
    ap.add_argument("--match",default="Exterior04")
    ap.add_argument("--source-size",type=int,default=1024)
    ap.add_argument("--report",required=True)
    args=ap.parse_args()

    data=Path(args.xzsm).read_bytes()
    magic,version,batch_count,_,_=HEADER.unpack_from(data,0)
    if magic!=b"XZSM" or version!=5:
        raise RuntimeError("expected XZSM v5")

    offset=HEADER.size
    triangles=[]
    exterior_batches=0

    for batch_index in range(batch_count):
        vertex_count,index_count,texture_raw,flags=BATCH_PREFIX.unpack_from(data,offset)
        offset += BATCH_PREFIX.size
        texture=cstr(texture_raw)
        offset += FIXED*3
        offset += BASE_COLOR.size+METAL_ROUGH.size+EMISSIVE.size+NORMAL_OCCL.size+BOUNDS.size

        uvs=[]
        for i in range(vertex_count):
            vals=VERTEX.unpack_from(data,offset+i*VERTEX.size)
            uvs.append((float(vals[6]),float(vals[7])))
        offset += vertex_count*VERTEX.size
        indices=struct.unpack_from("<"+"H"*index_count,data,offset)
        offset += index_count*2

        if args.match not in texture:
            continue
        exterior_batches += 1
        for i in range(0,index_count,3):
            if i+2>=index_count:
                break
            tri=[uvs[indices[i]],uvs[indices[i+1]],uvs[indices[i+2]]]
            triangles.append((batch_index,tri))

    if not triangles:
        raise RuntimeError("no exterior triangles")

    configs=[]
    for grid in (4,8,16):
        cell=1.0/grid
        used=set()
        subgroup=set()
        cross=0
        max_span=0
        for batch_index,tri in triangles:
            us=[max(0.0,min(0.999999999,u)) for u,v in tri]
            vs=[max(0.0,min(0.999999999,v)) for u,v in tri]
            u0,u1=min(us),max(us)
            v0,v1=min(vs),max(vs)
            gx0=int(u0*grid); gx1=int(u1*grid)
            gy0=int(v0*grid); gy1=int(v1*grid)
            span=(gx1-gx0+1)*(gy1-gy0+1)
            max_span=max(max_span,span)
            if gx0!=gx1 or gy0!=gy1:
                cross += 1
            # For planning, centroid chooses the primary shared tile. Crossing
            # triangles are counted separately because implementation must
            # either add UV-border padding or split/duplicate them.
            uc=sum(us)/3.0; vc=sum(vs)/3.0
            gx=min(grid-1,int(uc*grid)); gy=min(grid-1,int(vc*grid))
            used.add((gx,gy))
            subgroup.add((batch_index,gx,gy))

        source_tile=args.source_size//grid
        cfg={
            "grid":[grid,grid],
            "sourceTilePixels":[source_tile,source_tile],
            "usedSharedTiles":len(used),
            "spatialUvSubBatches":len(subgroup),
            "triangleCount":len(triangles),
            "crossCellTriangles":cross,
            "crossCellTriangleFraction":cross/len(triangles),
            "maxCellsTouchedByOneTriangle":max_span,
            "variants":[]
        }
        for out_size in (1024,2048):
            linear=out_size/source_tile
            cfg["variants"].append({
                "tileOutputSize":[out_size,out_size],
                "linearScaleFromSourceTile":linear,
                "medianTpmIfBaseMedian12_634":12.63423052743717*linear,
                "allUsedTilesAstc6x6MiB":len(used)*astc6x6_mips_bytes(out_size)/(1024*1024),
            })
        configs.append(cfg)

    report={
        "schemaVersion":1,
        "method":"SPATIAL_X_UV_GRID_VIRTUALIZATION_AUDIT_V1",
        "sourceAtlasSize":[args.source_size,args.source_size],
        "exteriorSpatialBatchCount":exterior_batches,
        "exteriorTriangleCount":len(triangles),
        "configs":configs,
        "note":"No runtime geometry or UVs were changed. Crossing triangles must be handled with padded tile borders or exact triangle reassignment before implementation."
    }
    Path(args.report).parent.mkdir(parents=True,exist_ok=True)
    Path(args.report).write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("XZIEL_ST_GILES_UV_GRID_AUDIT",json.dumps({
        "triangles":len(triangles),
        "configs":[{
            "grid":c["grid"][0],
            "usedTiles":c["usedSharedTiles"],
            "subBatches":c["spatialUvSubBatches"],
            "crossFraction":round(c["crossCellTriangleFraction"],6),
            "tpm2k":round(c["variants"][1]["medianTpmIfBaseMedian12_634"],2),
            "astc2kMiB":round(c["variants"][1]["allUsedTilesAstc6x6MiB"],2),
        } for c in configs]
    },separators=(",",":")))


if __name__=="__main__":
    main()
