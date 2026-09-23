#!/usr/bin/env python3
import argparse, json, math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def load_rgb(path):
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)

def stone_mask(rgb):
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    grad = cv2.magnitude(gx, gy)
    # Stone in St Giles is low-to-moderate saturation, mid/high luminance,
    # with enough local detail to exclude sky and empty atlas padding.
    mask = (
        (hsv[...,1] < 105) &
        (hsv[...,2] > 48) &
        (hsv[...,2] < 238) &
        (grad > 3.5)
    )
    if mask.mean() < 0.08:
        mask = (hsv[...,1] < 125) & (hsv[...,2] > 35) & (hsv[...,2] < 245)
    return mask

def hist1d(values, bins, lo, hi):
    h, _ = np.histogram(values, bins=bins, range=(lo, hi))
    h = h.astype(np.float64)
    return h / max(h.sum(), 1.0)

def features(rgb):
    mask = stone_mask(rgb)
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    pix = lab[mask]
    if pix.shape[0] < 100:
        raise RuntimeError("not enough stone-like pixels")

    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag, ang = cv2.cartToPolar(gx, gy, angleInDegrees=True)
    m = mask & (mag > 4.0)

    ori = ang[m] % 180.0
    weights = mag[m]
    oh, _ = np.histogram(ori, bins=12, range=(0,180), weights=weights)
    oh = oh.astype(np.float64)
    oh /= max(oh.sum(), 1.0)

    lap = cv2.Laplacian(gray, cv2.CV_32F)
    return {
        "mask_fraction": float(mask.mean()),
        "lab_mean": pix.mean(axis=0).tolist(),
        "lab_std": pix.std(axis=0).tolist(),
        "hist_l": hist1d(pix[:,0], 24, 0, 255).tolist(),
        "hist_a": hist1d(pix[:,1], 20, 70, 190).tolist(),
        "hist_b": hist1d(pix[:,2], 20, 70, 200).tolist(),
        "orientation": oh.tolist(),
        "gradient_mean": float(mag[mask].mean()),
        "gradient_p75": float(np.percentile(mag[mask], 75)),
        "lap_std": float(lap[mask].std()),
    }

def l1(a,b):
    a=np.asarray(a,dtype=np.float64); b=np.asarray(b,dtype=np.float64)
    return float(np.mean(np.abs(a-b)))

def rel(a,b):
    return abs(float(a)-float(b))/max(abs(float(a)),abs(float(b)),1e-6)

def distance(a,b):
    color_hist = (
        0.50*l1(a["hist_l"],b["hist_l"]) +
        0.25*l1(a["hist_a"],b["hist_a"]) +
        0.25*l1(a["hist_b"],b["hist_b"])
    )
    am=np.asarray(a["lab_mean"]); bm=np.asarray(b["lab_mean"])
    color_mean=float(np.linalg.norm(am-bm)/255.0)
    orient=l1(a["orientation"],b["orientation"])
    detail=(
        0.45*min(rel(a["gradient_mean"],b["gradient_mean"]),2.0)/2.0 +
        0.30*min(rel(a["gradient_p75"],b["gradient_p75"]),2.0)/2.0 +
        0.25*min(rel(a["lap_std"],b["lap_std"]),2.0)/2.0
    )
    score=0.40*color_hist+0.25*color_mean+0.20*orient+0.15*detail
    return {
        "score":float(score),
        "color_hist":float(color_hist),
        "color_mean":float(color_mean),
        "orientation":float(orient),
        "detail":float(detail),
    }

def thumb(path, size=(320,320)):
    im=Image.open(path).convert("RGB")
    im.thumbnail(size, Image.Resampling.LANCZOS)
    canvas=Image.new("RGB",size,(20,20,20))
    canvas.paste(im,((size[0]-im.width)//2,(size[1]-im.height)//2))
    return canvas

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--atlas",required=True)
    ap.add_argument("--photo",required=True)
    ap.add_argument("--candidates",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()

    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    atlas_f=features(load_rgb(args.atlas))
    photo_f=features(load_rgb(args.photo))

    rows=[]
    for p in sorted(Path(args.candidates).glob("*.jpg")):
        try:
            f=features(load_rgb(p))
            da=distance(f,atlas_f)
            dp=distance(f,photo_f)
            # Real 2025 church photo is the stronger authority; atlas keeps
            # continuity with the existing scan.
            total=0.62*dp["score"]+0.38*da["score"]
            rows.append({
                "name":p.stem,
                "path":str(p),
                "score":float(total),
                "vs_real_photo":dp,
                "vs_original_atlas":da,
                "features":f,
            })
        except Exception as e:
            rows.append({"name":p.stem,"path":str(p),"error":str(e),"score":999.0})

    rows.sort(key=lambda x:x["score"])
    valid=[r for r in rows if r["score"]<999]
    report={
        "method":"masked LAB hist + mean color + edge orientation + multiscale detail proxy",
        "weights":{"real_photo":0.62,"original_atlas":0.38},
        "atlas":str(args.atlas),
        "photo":str(args.photo),
        "atlas_features":atlas_f,
        "photo_features":photo_f,
        "ranking":rows,
        "winner":valid[0]["name"] if valid else None,
    }
    (out/"ranking.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    (out/"winner.txt").write_text((report["winner"] or "NONE")+"\n",encoding="utf-8")

    # Candidate-only contact sheet; the CC-BY-SA photo is reference-only and
    # deliberately not redistributed in this artifact.
    W,H=420,390
    sheet=Image.new("RGB",(W*2,H*math.ceil(max(len(valid),1)/2)),(12,12,12))
    draw=ImageDraw.Draw(sheet)
    for i,r in enumerate(valid):
        p=Path(r["path"])
        x=(i%2)*W; y=(i//2)*H
        sheet.paste(thumb(p,(380,300)),(x+20,y+10))
        draw.text((x+20,y+318),f"#{i+1} {r['name']}",fill=(255,255,255))
        draw.text((x+20,y+340),f"score {r['score']:.4f}",fill=(220,220,220))
    sheet.save(out/"candidate_contact_sheet.jpg",quality=92)

    print(json.dumps({
        "winner":report["winner"],
        "ranking":[{"name":r["name"],"score":round(r["score"],5)} for r in valid]
    },indent=2))

if __name__=="__main__":
    main()
