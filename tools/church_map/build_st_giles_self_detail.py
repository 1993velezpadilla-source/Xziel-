#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def patch_score(rgb: np.ndarray) -> tuple[float, dict]:
    r=rgb[...,0].astype(np.float32)
    g=rgb[...,1].astype(np.float32)
    b=rgb[...,2].astype(np.float32)
    mx=np.maximum(np.maximum(r,g),b)
    mn=np.minimum(np.minimum(r,g),b)
    sat=(mx-mn)/np.maximum(mx,1.0)
    luma=0.2126*r+0.7152*g+0.0722*b

    dark=float(np.mean(luma < 45.0))
    bright=float(np.mean(luma > 238.0))
    high_sat=float(np.mean(sat > 0.32))

    gray=Image.fromarray(np.clip(luma,0,255).astype(np.uint8),"L")
    low=np.asarray(gray.filter(ImageFilter.GaussianBlur(radius=5.0)),dtype=np.float32)
    hf=luma-low
    hf_rms=float(np.sqrt(np.mean(hf*hf)))

    # Favor mid-bright, low-saturation masonry with useful microstructure,
    # strongly rejecting dark windows, sky/void and colored vegetation.
    score=(
        hf_rms*1.6
        - dark*110.0
        - bright*50.0
        - high_sat*80.0
        - abs(float(np.mean(luma))-145.0)*0.08
    )
    return score,{
        "meanLuma":float(np.mean(luma)),
        "darkFraction":dark,
        "brightFraction":bright,
        "highSaturationFraction":high_sat,
        "highFrequencyRms":hf_rms,
    }


def periodic_detail_from_patch(patch: Image.Image, out_size: int) -> Image.Image:
    # ST_GILES_SELF_DERIVED_DETAIL_V1
    # Mirror the real St Giles patch before extracting high frequencies. Mirror
    # symmetry makes opposite borders continuous without importing any pixels
    # from another building.
    p=patch.convert("RGB")
    mirror_x=p.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    top=Image.new("RGB",(p.width*2,p.height))
    top.paste(p,(0,0)); top.paste(mirror_x,(p.width,0))
    mirror_y=top.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    tiled=Image.new("RGB",(top.width,top.height*2))
    tiled.paste(top,(0,0)); tiled.paste(mirror_y,(0,top.height))
    tiled=tiled.resize((out_size,out_size),Image.Resampling.LANCZOS)

    arr=np.asarray(tiled,dtype=np.float32)
    luma=0.2126*arr[...,0]+0.7152*arr[...,1]+0.0722*arr[...,2]
    low=np.asarray(
        Image.fromarray(np.clip(luma,0,255).astype(np.uint8),"L").filter(
            ImageFilter.GaussianBlur(radius=7.0)
        ),
        dtype=np.float32,
    )
    hf=luma-low
    scale=max(float(np.percentile(np.abs(hf),96)),1.0)
    hf=np.clip(hf/scale,-1.0,1.0)
    detail=np.clip(0.5+hf*0.34,0.08,0.92)
    u8=np.round(detail*255.0).astype(np.uint8)
    return Image.fromarray(np.repeat(u8[...,None],3,axis=2),"RGB")


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",required=True)
    ap.add_argument("--out-dir",required=True)
    ap.add_argument("--report",required=True)
    ap.add_argument("--patch-size",type=int,default=192)
    ap.add_argument("--stride",type=int,default=48)
    ap.add_argument("--count",type=int,default=8)
    ap.add_argument("--detail-size",type=int,default=1024)
    args=ap.parse_args()

    src=Image.open(args.source).convert("RGB")
    arr=np.asarray(src)
    out=Path(args.out_dir); out.mkdir(parents=True,exist_ok=True)

    candidates=[]
    ps=args.patch_size
    for y in range(0,src.height-ps+1,args.stride):
        for x in range(0,src.width-ps+1,args.stride):
            patch=arr[y:y+ps,x:x+ps]
            score,metrics=patch_score(patch)
            candidates.append((score,x,y,metrics))

    candidates.sort(reverse=True,key=lambda v:v[0])
    selected=[]
    min_sep=ps*0.65
    for score,x,y,metrics in candidates:
        cx=x+ps*0.5; cy=y+ps*0.5
        if any((cx-s["cx"])**2+(cy-s["cy"])**2 < min_sep**2 for s in selected):
            continue
        selected.append({"score":score,"x":x,"y":y,"cx":cx,"cy":cy,**metrics})
        if len(selected)>=args.count:
            break

    if len(selected)<3:
        raise RuntimeError("not enough source-derived stone patch candidates")

    cards=[]
    for i,s in enumerate(selected):
        patch=src.crop((s["x"],s["y"],s["x"]+ps,s["y"]+ps))
        patch_path=out/f"candidate_{i:02d}_source.png"
        detail_path=out/f"candidate_{i:02d}_detail.png"
        patch.save(patch_path)
        periodic_detail_from_patch(patch,args.detail_size).save(detail_path)
        s["sourcePatch"]=patch_path.name
        s["detailTile"]=detail_path.name
        cards.append((patch,Image.open(detail_path).convert("RGB")))

    card_w=384; card_h=384; label_h=46
    sheet=Image.new("RGB",(card_w*4,(card_h*2+label_h)*2),(18,18,18))
    draw=ImageDraw.Draw(sheet)
    for i,(patch,detail) in enumerate(cards[:8]):
        row=i//4; col=i%4
        x=col*card_w; y=row*(card_h*2+label_h)
        p=patch.resize((card_w,card_h),Image.Resampling.NEAREST)
        d=detail.resize((card_w,card_h),Image.Resampling.LANCZOS)
        sheet.paste(p,(x,y+label_h))
        sheet.paste(d,(x,y+label_h+card_h))
        draw.text((x+8,y+12),f"#{i} score={selected[i]['score']:.2f}",fill=(240,240,240))
    sheet_path=out/"st-giles-self-detail-candidates.jpg"
    sheet.save(sheet_path,quality=95)

    report={
        "schemaVersion":1,
        "method":"ST_GILES_SELF_DERIVED_DETAIL_V1",
        "sourceAuthority":str(args.source),
        "sourceSize":[src.width,src.height],
        "patchSize":ps,
        "detailSize":args.detail_size,
        "externalTexturePixelsUsed":False,
        "candidates":selected,
        "contactSheet":sheet_path.name,
        "runtimeApproved":False,
    }
    Path(args.report).parent.mkdir(parents=True,exist_ok=True)
    Path(args.report).write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("XZIEL_ST_GILES_SELF_DETAIL_READY",json.dumps({
        "count":len(selected),
        "topScore":round(selected[0]["score"],3),
        "externalPixels":False,
        "runtimeApproved":False,
    },separators=(",",":")))


if __name__=="__main__":
    main()
