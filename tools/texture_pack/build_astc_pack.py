#!/usr/bin/env python3

import argparse
import json
import struct
import subprocess
from pathlib import Path


def classify_texture(path: Path):
    name = path.name.lower()

    normal_tokens = (
        "normal",
        "_n.",
        "_nrm.",
    )
    linear_tokens = (
        "orm",
        "rough",
        "metal",
        "occlusion",
        "_ao.",
        "_detail.",
    )

    if any(token in name for token in normal_tokens):
        return "ASTC_6x6_UNORM_BLOCK", ["--normalize"], "normal", "clamp"

    if "_detail." in name:
        return "ASTC_6x6_UNORM_BLOCK", [], "photo-detail", "repeat"

    if any(token in name for token in linear_tokens):
        return "ASTC_6x6_UNORM_BLOCK", [], "linear-data", "clamp"

    return "ASTC_6x6_SRGB_BLOCK", ["--astc-perceptual"], "color", "clamp"


def parse_ktx2(path: Path):
    data = path.read_bytes()

    if len(data) < 80:
        raise RuntimeError(f"truncated KTX2: {path}")

    identifier = bytes.fromhex("AB4B5458203230BB0D0A1A0A")
    if data[:12] != identifier:
        raise RuntimeError(f"bad KTX2 identifier: {path}")

    (
        vk_format,
        type_size,
        width,
        height,
        depth,
        layers,
        faces,
        levels,
        supercompression,
    ) = struct.unpack_from("<9I", data, 12)

    if not (157 <= vk_format <= 184):
        raise RuntimeError(f"non-ASTC VkFormat {vk_format}: {path}")

    if type_size != 1 or width <= 0 or height <= 0:
        raise RuntimeError(f"invalid ASTC dimensions/type: {path}")

    if depth != 0 or layers != 0 or faces != 1 or levels <= 0:
        raise RuntimeError(f"unsupported KTX2 texture shape: {path}")

    if supercompression != 0:
        raise RuntimeError(f"unexpected KTX2 supercompression: {path}")

    return {
        "bytes": len(data),
        "vkFormat": vk_format,
        "width": width,
        "height": height,
        "levels": levels,
        "srgb": bool((vk_format - 157) & 1),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--ktx", default="ktx")
    parser.add_argument("--quality", default="medium")
    args = parser.parse_args()

    root = Path(args.root)
    report_path = Path(args.report)

    if not root.is_dir():
        raise SystemExit(f"missing texture root: {root}")

    pngs = sorted(root.rglob("*.png"))
    if not pngs:
        raise SystemExit("no PNG source textures found")

    records = []
    png_bytes = 0
    ktx_bytes = 0

    for png in pngs:
        output = png.with_suffix(".ktx2")
        fmt, extra, semantic, mip_wrap = classify_texture(png)

        command = [
            args.ktx,
            "create",
            "--format",
            fmt,
            "--generate-mipmap",
            "--mipmap-filter",
            "lanczos4",
            "--mipmap-wrap",
            mip_wrap,
            "--astc-quality",
            args.quality,
            *extra,
            str(png),
            str(output),
        ]

        print(
            "XZIEL_ASTC_ENCODE",
            semantic,
            fmt,
            png,
            "->",
            output,
            flush=True,
        )

        subprocess.run(command, check=True)
        subprocess.run(
            [args.ktx, "validate", str(output)],
            check=True,
        )

        info = parse_ktx2(output)
        info.update({
            "source": str(png.relative_to(root)),
            "path": str(output.relative_to(root)),
            "semantic": semantic,
            "format": fmt,
            "mipWrap": mip_wrap,
        })

        png_bytes += png.stat().st_size
        ktx_bytes += output.stat().st_size
        records.append(info)

    report = {
        "schemaVersion": 1,
        "codec": "ASTC_LDR",
        "block": "6x6",
        "quality": args.quality,
        "mipFilter": "lanczos4",
        "supercompression": "none",
        "pngCount": len(pngs),
        "ktx2Count": len(records),
        "pngBytes": png_bytes,
        "ktx2Bytes": ktx_bytes,
        "ktx2ToPngRatio": (
            ktx_bytes / png_bytes
            if png_bytes
            else 0.0
        ),
        "textures": records,
    }

    if report["pngCount"] != report["ktx2Count"]:
        raise SystemExit("ASTC pack is missing textures")

    report_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    report_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print(
        "XZIEL_ASTC_PACK_READY",
        json.dumps({
            "textures": len(records),
            "pngBytes": png_bytes,
            "ktx2Bytes": ktx_bytes,
            "ratio": report["ktx2ToPngRatio"],
        }),
        flush=True,
    )


if __name__ == "__main__":
    main()
