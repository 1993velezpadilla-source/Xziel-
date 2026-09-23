#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

def resize_rgb(path, size):
    return Image.open(path).convert("RGB").resize(
        size,
        Image.Resampling.LANCZOS,
    )

def rgb_to_hsv_np(rgb):
    # PIL gives robust HSV conversion without adding another CI dependency.
    hsv = Image.fromarray(rgb.astype(np.uint8), "RGB").convert("HSV")
    return np.asarray(hsv, dtype=np.float32)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--runtime-root", required=True)
    ap.add_argument("--detail", required=True)
    ap.add_argument("--out-report", required=True)
    args = ap.parse_args()

    report_path = Path(args.report)
    root = Path(args.runtime_root)
    detail_path = Path(args.detail)
    report = json.loads(report_path.read_text(encoding="utf-8"))

    target_key = next(
        (key for key in report["materialReport"] if "Exterior04" in key),
        None,
    )
    if target_key is None:
        raise RuntimeError("Exterior04 material not found")

    material = report["materialReport"][target_key]
    texture_rel = Path(material["texturePath"])
    target = root / texture_rel
    if not target.is_file():
        raise RuntimeError(f"runtime exterior texture missing: {target}")

    source = Image.open(target).convert("RGB")
    target_size = (4096, 4096)
    source_up = source.resize(target_size, Image.Resampling.LANCZOS)
    src = np.asarray(source_up, dtype=np.float32)

    detail = resize_rgb(detail_path, target_size)
    # Offset/rotate the candidate so the A/B does not accidentally line up
    # with atlas seams or repeat the exact same patch orientation everywhere.
    detail = detail.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    det = np.asarray(detail, dtype=np.float32)

    # Extract only microstructure from the selected real-stone candidate.
    # Large mortar/block layout is intentionally removed: we preserve St
    # Giles' own photographed architecture and add only missing high-frequency
    # surface information.
    det_luma = (
        det[..., 0] * 0.2126 +
        det[..., 1] * 0.7152 +
        det[..., 2] * 0.0722
    )
    det_luma_img = Image.fromarray(
        np.clip(det_luma, 0, 255).astype(np.uint8),
        "L",
    )
    low = np.asarray(
        det_luma_img.filter(ImageFilter.GaussianBlur(radius=10.0)),
        dtype=np.float32,
    )
    micro = det_luma - low
    scale = max(float(np.percentile(np.abs(micro), 95)), 1.0)
    micro = np.clip(micro / scale, -1.0, 1.0)

    hsv = rgb_to_hsv_np(src)
    saturation = hsv[..., 1]
    value = hsv[..., 2]

    # Stone-only gate. This deliberately excludes the dark window interiors,
    # most wood, sky/void padding and very saturated vegetation.
    stone = (
        (saturation < 105.0) &
        (value > 52.0) &
        (value < 238.0)
    ).astype(np.float32)

    # Soften the mask to avoid a hard edge around windows/wood.
    stone_mask_img = Image.fromarray(
        np.clip(stone * 255.0, 0, 255).astype(np.uint8),
        "L",
    ).filter(ImageFilter.GaussianBlur(radius=2.2))
    mask = np.asarray(stone_mask_img, dtype=np.float32) / 255.0

    # Conservative A/B: ±9% luminance micro-detail at full mask. The source
    # color/large-scale lighting remain authoritative.
    strength = 23.0
    delta = micro[..., None] * strength * mask[..., None]
    fused = np.clip(src + delta, 0.0, 255.0).astype(np.uint8)

    Image.fromarray(fused, "RGB").save(
        target,
        format="PNG",
        compress_level=3,
    )

    before = list(material.get("sourceSize", [1024, 1024]))
    material["microdetail"] = {
        "candidate": "polyhaven_medieval_blocks_03",
        "license": "CC0",
        "candidateResolution": [4096, 4096],
        "method": "high_frequency_luma_only_stone_mask",
        "strengthLuma8bit": strength,
        "maskMean": float(mask.mean()),
        "preservesSourceColor": True,
        "preservesMacroPattern": True,
    }
    material["runtimeSize"] = [4096, 4096]
    material["exactSourcePixels"] = False

    report["textureSourceMode"] = (
        "original_glb_embedded_pixels_plus_matched_exterior_microdetail"
    )
    report["microdetailApplied"] = True
    report["microdetailMaterial"] = target_key
    report["microdetailCandidate"] = "polyhaven_medieval_blocks_03"
    report["microdetailCandidateLicense"] = "CC0"
    report["originalExteriorResolution"] = before
    report["runtimeExteriorResolution"] = [4096, 4096]
    report["exactSourcePixelTextures"] = sum(
        1 for value in report["materialReport"].values()
        if value.get("exactSourcePixels")
    )

    report_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )
    Path(args.out_report).write_text(
        json.dumps({
            "material": target_key,
            "texture": str(target),
            "candidate": str(detail_path),
            "candidateName": "medieval_blocks_03",
            "candidateLicense": "CC0",
            "originalResolution": before,
            "runtimeResolution": [4096, 4096],
            "maskMean": float(mask.mean()),
            "strengthLuma8bit": strength,
            "method": "high_frequency_luma_only_stone_mask",
        }, indent=2),
        encoding="utf-8",
    )

    print(
        "XZIEL_EXTERIOR_DETAIL_AB_READY",
        json.dumps({
            "material": target_key,
            "runtimeResolution": [4096, 4096],
            "maskMean": round(float(mask.mean()), 4),
            "candidate": "medieval_blocks_03",
        }),
    )

if __name__ == "__main__":
    main()
