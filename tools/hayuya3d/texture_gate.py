#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import json
import math
import struct
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image, ImageFilter, ImageStat

JSON_CHUNK=0x4E4F534A
BIN_CHUNK=0x004E4942

@dataclass
class TextureMetric:
    index:int
    mime_type:str
    width:int
    height:int
    megapixels:float
    edge_variance:float
    luminance_stddev:float
    entropy:float

@dataclass
class TextureReport:
    schema:int
    path:str
    image_count:int
    max_edge:int
    max_megapixels:float
    mean_edge_variance:float
    metrics:list[TextureMetric]
    warnings:list[str]
    passed:bool


def chunks(path:Path):
    blob=path.read_bytes()
    if len(blob)<20 or blob[:4]!=b"glTF":
        raise ValueError("not a GLB")
    version,total=struct.unpack_from("<II",blob,4)
    if version!=2 or total>len(blob):
        raise ValueError("invalid GLB")
    off=12
    doc=None
    bin_blob=b""
    while off+8<=total:
        ln,typ=struct.unpack_from("<II",blob,off);off+=8
        data=blob[off:off+ln];off+=ln
        if typ==JSON_CHUNK:
            doc=json.loads(data.rstrip(b"\x00 \t\r\n").decode("utf-8"))
        elif typ==BIN_CHUNK:
            bin_blob=data
    if doc is None:
        raise ValueError("missing JSON chunk")
    return doc,bin_blob


def embedded_images(path:Path):
    doc,bin_blob=chunks(path)
    views=doc.get("bufferViews") or []
    out=[]
    for idx,img in enumerate(doc.get("images") or []):
        bv=img.get("bufferView")
        if not isinstance(bv,int) or not (0<=bv<len(views)):
            continue
        view=views[bv]
        start=int(view.get("byteOffset",0))
        length=int(view.get("byteLength",0))
        data=bin_blob[start:start+length]
        if data:
            out.append((idx,str(img.get("mimeType") or "unknown"),data))
    return out


def metric(idx:int,mime:str,data:bytes)->TextureMetric:
    with Image.open(io.BytesIO(data)) as im:
        im.load()
        rgb=im.convert("RGB")
        w,h=rgb.size
        # Normalize to a stable analysis size so resolution alone cannot inflate
        # the detail score.
        g=rgb.convert("L")
        g.thumbnail((1024,1024),Image.Resampling.LANCZOS)
        edges=g.filter(ImageFilter.FIND_EDGES)
        edge_var=float(ImageStat.Stat(edges).var[0])
        lum_std=float(ImageStat.Stat(g).stddev[0])
        ent=float(g.entropy())
        return TextureMetric(
            index=idx,mime_type=mime,width=w,height=h,
            megapixels=round((w*h)/1_000_000,4),
            edge_variance=round(edge_var,4),
            luminance_stddev=round(lum_std,4),
            entropy=round(ent,4),
        )


def inspect(path:Path,min_edge:int=1024)->TextureReport:
    metrics=[metric(i,m,d) for i,m,d in embedded_images(path)]
    warnings=[]
    max_edge=max((max(x.width,x.height) for x in metrics),default=0)
    max_mp=max((x.megapixels for x in metrics),default=0.0)
    mean_edge=sum(x.edge_variance for x in metrics)/len(metrics) if metrics else 0.0
    if not metrics:
        warnings.append("no_embedded_texture_images")
    if max_edge and max_edge<min_edge:
        warnings.append(f"low_texture_resolution:{max_edge}<{min_edge}")
    # Calibration signal only. Do not hard-fail creative/stylized textures based
    # on an arbitrary sharpness threshold; the source-vs-render Judge owns fidelity.
    if metrics and mean_edge<25:
        warnings.append(f"low_high_frequency_detail:{mean_edge:.3f}")
    passed=bool(metrics) and max_edge>=min_edge
    return TextureReport(
        schema=1,path=str(path),image_count=len(metrics),max_edge=max_edge,
        max_megapixels=round(max_mp,4),mean_edge_variance=round(mean_edge,4),
        metrics=metrics,warnings=warnings,passed=passed
    )


def main()->int:
    p=argparse.ArgumentParser(description="Inspect embedded GLB texture resolution and clarity telemetry.")
    p.add_argument("glb",type=Path)
    p.add_argument("--min-edge",type=int,default=1024)
    p.add_argument("--json",type=Path)
    a=p.parse_args()
    try:
        report=inspect(a.glb,a.min_edge)
        payload=json.dumps(asdict(report),indent=2)
        print(payload)
        if a.json:
            a.json.parent.mkdir(parents=True,exist_ok=True)
            a.json.write_text(payload+"\n",encoding="utf-8")
        return 0 if report.passed else 2
    except Exception as exc:
        payload={"schema":1,"path":str(a.glb),"passed":False,"warnings":[f"{type(exc).__name__}:{exc}"]}
        print(json.dumps(payload,indent=2))
        if a.json:
            a.json.parent.mkdir(parents=True,exist_ok=True)
            a.json.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
        return 2

if __name__=="__main__":
    raise SystemExit(main())
