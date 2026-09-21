#!/usr/bin/env python3
"""Build a separate high-resolution storm-night skybox for Enchanted Nacht.

The practice build color-grades the licensed NZ:P Nacht sky rather than using
the stock sky directly, preserving cube-face continuity while giving the new
map its own colder, higher-resolution exterior atmosphere.
"""
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: build_nacht_enchanted_sky.py <nzp-root>")

root = Path(sys.argv[1])
env = root / "gfx/env"
faces = ["bk", "dn", "ft", "lf", "rt", "up"]

for face in faces:
    src = env / f"ndu{face}.tga"
    if not src.is_file():
        raise SystemExit(f"missing stock Nacht sky face: {src}")

    im = Image.open(src).convert("RGB")
    if max(im.size) < 1024:
        scale = 1024.0 / max(im.size)
        im = im.resize(
            (max(1, int(im.width*scale)), max(1, int(im.height*scale))),
            Image.Resampling.LANCZOS,
        )

    im = ImageEnhance.Contrast(im).enhance(1.22)
    im = ImageEnhance.Color(im).enhance(0.70)
    px = im.load()
    # Cold storm grade. This is applied per-pixel identically on every cube
    # face, so edges inherited from the source remain consistent.
    for y in range(im.height):
        for x in range(im.width):
            r, g, b = px[x, y]
            luminance = (r*0.2126 + g*0.7152 + b*0.0722)
            r2 = int(max(0, min(255, r*0.64 + luminance*0.05)))
            g2 = int(max(0, min(255, g*0.76 + luminance*0.06)))
            b2 = int(max(0, min(255, b*0.98 + luminance*0.10 + 5)))
            px[x, y] = (r2, g2, b2)

    im = im.filter(ImageFilter.UnsharpMask(radius=1.0, percent=125, threshold=4))
    dst = env / f"xziel_enchant{face}.tga"
    im.save(dst, format="TGA", rle=True)
    print(f"{src.name} -> {dst.name} {im.size}")

print("Built Enchanted storm-night skybox.")
