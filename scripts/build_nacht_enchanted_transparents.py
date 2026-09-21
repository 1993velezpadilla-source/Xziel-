#!/usr/bin/env python3
"""Polish Nacht transparent/masked surfaces without destroying alpha.

GoldSrc-style '{' textures are used for railings, barbed wire, boards and
chalk. Replacing them with opaque JPGs would turn their transparent regions
into ugly rectangles, so the Enchanted build derives high-resolution RGBA
overrides from the licensed NZ:P source PNGs and preserves their masks.
"""
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
import sys

if len(sys.argv) != 3:
    raise SystemExit(
        "usage: build_nacht_enchanted_transparents.py <nzp-assets-source> <nzp-root>"
    )

source = Path(sys.argv[1])
root = Path(sys.argv[2])
out = root / "textures/nacht_enhanced"
out.mkdir(parents=True, exist_ok=True)

entries = [
    ("source/textures/wad/Ju[s]tice_null2/{railling_ndu.png", ["{railling_ndu.png", "{RAILLING_NDU.png"]),
    ("source/textures/wad/Ju[s]tice_null2/{board_fe.png", ["{board_fe.png", "{BOARD_FE.png"]),
    ("source/textures/wad/Ju[s]tice_null2/{barbed_wire_V.png", ["{barbed_wire_v.png", "{BARBED_WIRE_V.png"]),
    ("source/textures/wad/Ju[s]tice_null2/{metal_rail7.png", ["{metal_rail7.png", "{METAL_RAIL7.png"]),
    ("source/textures/wad/Ju[s]tice_null2/{camo_2.png", ["{camo_2.png", "{CAMO_2.png"]),
    ("source/textures/wad/Ju[s]tice_null2/{clfND.png", ["{clfnd.png", "{CLFND.png"]),
]

for rel, names in entries:
    src = source / rel
    if not src.is_file():
        raise SystemExit(f"missing transparent source texture: {src}")

    im = Image.open(src).convert("RGBA")
    alpha = im.getchannel("A")
    rgb = im.convert("RGB")
    rgb = ImageEnhance.Contrast(rgb).enhance(1.18)
    rgb = ImageEnhance.Color(rgb).enhance(0.88)
    rgb = ImageEnhance.Brightness(rgb).enhance(0.90)

    w, h = rgb.size
    scale = min(4.0, 1024.0 / max(w, h))
    if scale > 1.0:
        new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
        rgb = rgb.resize(new_size, Image.Resampling.LANCZOS)
        alpha = alpha.resize(new_size, Image.Resampling.LANCZOS)

    rgb = rgb.filter(ImageFilter.UnsharpMask(radius=1.0, percent=140, threshold=3))
    result = rgb.convert("RGBA")
    result.putalpha(alpha)
    for name in names:
        dst = out / name
        result.save(dst, optimize=True)
        print(f"{rel} -> {dst.name} {result.size}")

print("Built case-safe alpha Enchanted railing, barricade, wire, camo and fence overrides.")
