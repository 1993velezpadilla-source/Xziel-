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
    # MULTISCALE_EXTERIOR_DETAIL_V2
    # The source atlas is only 1K. A single high-pass band adds grain but
    # leaves broad stone surfaces mushy. Split the real CC0 stone candidate
    # into fine and medium bands while still removing its macro block layout.
    fine_low = np.asarray(
        det_luma_img.filter(ImageFilter.GaussianBlur(radius=4.0)),
        dtype=np.float32,
    )
    medium_low = np.asarray(
        det_luma_img.filter(ImageFilter.GaussianBlur(radius=24.0)),
        dtype=np.float32,
    )

    fine = det_luma - fine_low
    medium = fine_low - medium_low

    fine_scale = max(
        float(np.percentile(np.abs(fine), 95)),
        1.0,
    )
    medium_scale = max(
        float(np.percentile(np.abs(medium), 95)),
        1.0,
    )

    fine = np.clip(
        fine / fine_scale,
        -1.0,
        1.0,
    )
    medium = np.clip(
        medium / medium_scale,
        -1.0,
        1.0,
    )

    surface_height = np.clip(
        fine * 0.68 +
        medium * 0.32,
        -1.0,
        1.0,
    )

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

    # Add enough real mid-scale stone structure to survive the 1K source
    # upscale, while keeping St Giles' photographed color and large-scale
    # illumination authoritative.
    fine_strength = 20.0
    medium_strength = 14.0
    strength = fine_strength + medium_strength

    detail_delta = (
        fine * fine_strength +
        medium * medium_strength
    )
    delta = (
        detail_delta[..., None] *
        mask[..., None]
    )
    fused = np.clip(
        src + delta,
        0.0,
        255.0,
    ).astype(np.uint8)

    Image.fromarray(fused, "RGB").save(
        target,
        format="PNG",
        compress_level=3,
    )

    # Derive tangent-space relief from the same bounded multi-scale field.
    # The candidate's macro block/mortar layout never enters this height map.
    grad_v, grad_u = np.gradient(
        surface_height.astype(np.float32)
    )
    normal_strength = 1.55
    nx = -grad_u * normal_strength * mask
    ny = -grad_v * normal_strength * mask
    nz = np.ones_like(nx, dtype=np.float32)
    normal_length = np.maximum(
        np.sqrt(nx * nx + ny * ny + nz * nz),
        1.0e-6,
    )
    normal_rgb = np.stack(
        (
            nx / normal_length,
            ny / normal_length,
            nz / normal_length,
        ),
        axis=-1,
    )
    normal_u8 = np.round(
        np.clip(
            normal_rgb * 0.5 + 0.5,
            0.0,
            1.0,
        ) * 255.0
    ).astype(np.uint8)

    crevice = (
        np.maximum(-surface_height, 0.0) *
        mask
    )
    ao = np.clip(
        1.0 - crevice * 0.16,
        0.82,
        1.0,
    )
    roughness = np.clip(
        1.0 -
        mask * (
            0.18 -
            0.06 * np.abs(surface_height)
        ),
        0.76,
        1.0,
    )
    metallic = np.zeros_like(
        roughness,
        dtype=np.float32,
    )
    orm_u8 = np.round(
        np.stack(
            (ao, roughness, metallic),
            axis=-1,
        ) * 255.0
    ).astype(np.uint8)

    normal_rel = texture_rel.with_name(
        texture_rel.stem + "_normal.png"
    )
    orm_rel = texture_rel.with_name(
        texture_rel.stem + "_orm.png"
    )
    normal_target = root / normal_rel
    orm_target = root / orm_rel
    Image.fromarray(
        normal_u8,
        "RGB",
    ).save(
        normal_target,
        format="PNG",
        compress_level=3,
    )
    Image.fromarray(
        orm_u8,
        "RGB",
    ).save(
        orm_target,
        format="PNG",
        compress_level=3,
    )

    before = list(material.get("sourceSize", [1024, 1024]))
    material["microdetail"] = {
        "candidate": "polyhaven_medieval_blocks_03",
        "license": "CC0",
        "candidateResolution": [4096, 4096],
        "method": "multiscale_bandpass_stone_mask_v2",
        "strengthLuma8bit": strength,
        "fineStrengthLuma8bit": fine_strength,
        "mediumStrengthLuma8bit": medium_strength,
        "fineBandRadius": 4.0,
        "mediumBandRadius": 24.0,
        "maskMean": float(mask.mean()),
        "preservesSourceColor": True,
        "preservesMacroPattern": True,
    }
    material["runtimeSize"] = [4096, 4096]
    material["exactSourcePixels"] = False
    material["generatedPbr"] = {
        "normalTexturePath": str(normal_rel),
        "ormTexturePath": str(orm_rel),
        "normalScale": 0.55,
        "occlusionStrength": 0.35,
        "method": "matched_multiscale_heightfield_v2",
    }

    report["textureSourceMode"] = (
        "original_glb_embedded_pixels_plus_matched_exterior_microdetail"
    )
    report["microdetailApplied"] = True
    report["microdetailMaterial"] = target_key
    report["microdetailCandidate"] = "polyhaven_medieval_blocks_03"
    report["microdetailCandidateLicense"] = "CC0"
    report["originalExteriorResolution"] = before
    report["runtimeExteriorResolution"] = [4096, 4096]
    report["generatedPbrApplied"] = True
    report["generatedPbrMaterial"] = target_key
    report["generatedPbrNormalTexture"] = str(normal_rel)
    report["generatedPbrOrmTexture"] = str(orm_rel)
    report["generatedPbrResolution"] = [4096, 4096]
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
            "fineStrengthLuma8bit": fine_strength,
            "mediumStrengthLuma8bit": medium_strength,
            "fineBandRadius": 4.0,
            "mediumBandRadius": 24.0,
            "method": "multiscale_bandpass_stone_mask_v2",
            "generatedPbr": {
                "normalTexture": str(normal_target),
                "ormTexture": str(orm_target),
                "resolution": [4096, 4096],
                "normalScale": 0.55,
                "occlusionStrength": 0.35,
            },
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
