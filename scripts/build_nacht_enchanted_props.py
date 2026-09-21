#!/usr/bin/env python3
"""Build high-detail runtime skins for Nacht: Enchanted Lab.

The Quake/Vril models stay authoritative for geometry/animation. This script
creates external TGA skins from the bundled NZ:P PCX artwork so Android can
render sharper, moodier practice-map assets without reducing them to legacy
palette resolution.
"""
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
import random
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: build_nacht_enchanted_props.py <nzp-root>")

root = Path(sys.argv[1])
rng = random.Random(0x58A17E)

def upscale(src: Path, max_size: int = 1024) -> Image.Image:
    im = Image.open(src).convert("RGB")
    w, h = im.size
    scale = min(4.0, max_size / max(w, h))
    if scale > 1.0:
        im = im.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.LANCZOS)
    return im

def finish(im: Image.Image) -> Image.Image:
    return im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=145, threshold=3))

def grade_box(im: Image.Image) -> Image.Image:
    im = ImageEnhance.Contrast(im).enhance(1.28)
    im = ImageEnhance.Color(im).enhance(0.86)
    im = ImageEnhance.Brightness(im).enhance(0.82)
    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    w, h = im.size
    # Fine scratches and old painted-metal wear. Kept subtle because the skin
    # atlas wraps several UV islands and shouldn't receive one giant decal.
    for _ in range(80):
        x = rng.randrange(w)
        y = rng.randrange(h)
        length = rng.randrange(max(4, w // 80), max(8, w // 18))
        shade = rng.choice([(180, 165, 130, 26), (20, 16, 12, 35), (95, 72, 50, 32)])
        d.line((x, y, min(w - 1, x + length), y + rng.randrange(-2, 3)), fill=shade, width=max(1, w // 512))
    # Cold occult patina over the original box art; not a copied COD emblem.
    d.rectangle((0, 0, w, h), fill=(20, 28, 38, 22))
    return finish(Image.alpha_composite(im.convert("RGBA"), overlay).convert("RGB"))

def grade_zombie(im: Image.Image, index: int) -> Image.Image:
    im = ImageEnhance.Contrast(im).enhance(1.22)
    im = ImageEnhance.Color(im).enhance(0.72)
    im = ImageEnhance.Brightness(im).enhance(0.86)
    base = im.convert("RGBA")
    w, h = base.size

    # Pore/grime layer retains the original UVs but breaks up the flat 8-bit
    # look. Each stock skin receives deterministic variation.
    noise = Image.effect_noise((w, h), 18.0).convert("L")
    noise = ImageEnhance.Contrast(noise).enhance(1.6)
    grime = Image.new("RGBA", (w, h), (34, 42, 36, 0))
    grime.putalpha(noise.point(lambda p: max(0, min(35, int((p - 96) * 0.22)))))
    base = Image.alpha_composite(base, grime)

    wound = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(wound)
    local = random.Random(0xC0FFEE + index * 31337)
    for _ in range(18):
        x = local.randrange(w)
        y = local.randrange(h)
        rw = local.randrange(max(5, w // 90), max(10, w // 28))
        rh = local.randrange(max(3, h // 120), max(7, h // 45))
        d.ellipse((x-rw, y-rh, x+rw, y+rh), fill=(72, 5, 8, local.randrange(45, 95)))
        if local.random() < 0.55:
            d.line((x, y, x + local.randrange(-rw*2, rw*2+1), y + local.randrange(rh, rh*4+1)),
                   fill=(92, 7, 9, local.randrange(45, 90)), width=max(1, w // 384))
    base = Image.alpha_composite(base, wound)

    # Slight individual cold/warm bias keeps hordes from reading as clones.
    tint = [(28, 38, 32, 20), (40, 30, 25, 18), (24, 33, 42, 18), (36, 24, 30, 18)][index % 4]
    tint_layer = Image.new("RGBA", (w, h), tint)
    return finish(Image.alpha_composite(base, tint_layer).convert("RGB"))

def write_override(src_rel: str, transform, dst_rel: str | None = None) -> None:
    src = root / src_rel
    if not src.is_file():
        raise SystemExit(f"missing bundled source skin: {src}")
    dst = root / (dst_rel or src_rel.rsplit(".", 1)[0] + ".tga")
    dst.parent.mkdir(parents=True, exist_ok=True)
    transform(upscale(src)).save(dst, format="TGA", rle=True)
    print(f"{src_rel} -> {dst.relative_to(root)} {dst.stat().st_size} bytes")

write_override("models/machines/mystery.mdl_0.pcx", grade_box)
write_override("models/props/mystery_debris.mdl_0.pcx", grade_box)

# Sandbags appear twenty times across both floors of Nacht, so leaving them at
# the old palette skin would make the upgraded walls/floors look inconsistent.
def grade_sandbag(im: Image.Image) -> Image.Image:
    im = ImageEnhance.Contrast(im).enhance(1.26)
    im = ImageEnhance.Color(im).enhance(0.78)
    im = ImageEnhance.Brightness(im).enhance(0.84)
    overlay = Image.new("RGBA", im.size, (0,0,0,0))
    d = ImageDraw.Draw(overlay)
    w, h = im.size
    local = random.Random(0x5A4DBA6)
    for _ in range(95):
        x = local.randrange(w); y = local.randrange(h)
        length = local.randrange(max(3,w//100), max(7,w//24))
        d.line(
            (x, y, min(w-1,x+length), y+local.randrange(-2,3)),
            fill=(75,58,39,local.randrange(18,44)),
            width=max(1,w//512),
        )
    return finish(Image.alpha_composite(im.convert("RGBA"), overlay).convert("RGB"))

write_override("models/props/sandbags.mdl_0.pcx", grade_sandbag)

for i in range(4):
    src = f"models/ai/zfull.mdl_{i}.pcx"
    write_override(src, lambda im, i=i: grade_zombie(im, i))

print("Built Enchanted Mystery Box/debris, sandbags and four high-detail zombie skin overrides.")
