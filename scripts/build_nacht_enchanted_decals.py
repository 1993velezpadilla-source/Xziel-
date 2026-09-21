#!/usr/bin/env python3
"""Generate original transparent occult/chalk overlays for Enchanted Nacht.

The glyphs are Xziel originals built from primitive geometry. They intentionally
do not copy Call of Duty symbols. They replace only existing transparent chalk
texture slots already authored into the practice map.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
import math
import random
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: build_nacht_enchanted_decals.py <nzp-root>")

root = Path(sys.argv[1])
out = root / "textures/nacht_enhanced"
out.mkdir(parents=True, exist_ok=True)
SIZE = 1024

def rough_line(draw, points, fill, width, rng):
    for _ in range(5):
        jittered = []
        for x, y in points:
            jittered.append((x + rng.randint(-4,4), y + rng.randint(-4,4)))
        draw.line(jittered, fill=fill, width=max(2, width + rng.randint(-3,3)), joint="curve")

def sigil(seed, variant):
    rng = random.Random(seed)
    layer = Image.new("RGBA", (SIZE, SIZE), (0,0,0,0))
    d = ImageDraw.Draw(layer)
    c = (226, 225, 206, 205)
    dim = (171, 171, 156, 125)
    blood = (118, 13, 20, 145)
    cx, cy = 512, 512

    # Broken outer ring.
    radius = 330
    for i in range(9):
        a0 = -80 + i*39 + rng.randint(-5,5)
        a1 = a0 + rng.randint(20,31)
        d.arc((cx-radius,cy-radius,cx+radius,cy+radius), a0, a1, fill=c, width=16)

    # One-eye / compass motif: original Xziel language rather than a copied rune.
    rough_line(d, [(220,512),(360,408),(512,372),(664,408),(804,512),(664,616),(512,652),(360,616),(220,512)], c, 18, rng)
    d.ellipse((445,445,579,579), outline=c, width=18)
    d.ellipse((493,493,531,531), fill=(242,238,209,225))
    rough_line(d, [(512,180),(512,344)], dim, 13, rng)
    rough_line(d, [(512,680),(512,844)], dim, 13, rng)
    rough_line(d, [(180,512),(344,512)], dim, 13, rng)
    rough_line(d, [(680,512),(844,512)], dim, 13, rng)

    if variant == 0:
        rough_line(d, [(350,760),(512,848),(674,760)], c, 18, rng)
        rough_line(d, [(512,848),(512,698)], c, 18, rng)
    elif variant == 1:
        rough_line(d, [(292,278),(512,166),(732,278)], blood, 22, rng)
        rough_line(d, [(350,280),(512,352),(674,280)], blood, 16, rng)
    else:
        rough_line(d, [(330,722),(512,810),(694,722),(512,632),(330,722)], blood, 18, rng)

    # Dusty/chalk breakup via sparse transparent eraser dots.
    for _ in range(650):
        x = rng.randrange(SIZE); y = rng.randrange(SIZE)
        if rng.random() < 0.65:
            r = rng.randrange(1,5)
            d.ellipse((x-r,y-r,x+r,y+r), fill=(0,0,0,0))

    blur = layer.filter(ImageFilter.GaussianBlur(0.55))
    return Image.alpha_composite(blur, layer)

names = [
    ("{CHK_ASCEND", 0xA51CE, 0),
    ("{CHK_SALVAT", 0x5A1A47, 1),
    ("{CHK_BOX", 0xB0B0B0, 2),
]
for name, seed, variant in names:
    path = out / f"{name}.png"
    sigil(seed, variant).save(path)
    print(f"generated {path.name} {path.stat().st_size} bytes")
