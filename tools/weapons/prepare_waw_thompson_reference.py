#!/usr/bin/env python3
"""Prepare and validate the public WaW Thompson golden-reference source pack.

Input is a checkout of CallOfDutyModding/call_of_duty_world_at_war_mod_tools.
The script validates Git blob identities and structural invariants before
copying the minimum reference set into a build/output directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import struct
from pathlib import Path


HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "waw_thompson_reference.json"


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(f"blob {len(data)}\0".encode("ascii"))
    h.update(data)
    return h.hexdigest()


def parse_tga_header(path: Path) -> dict:
    data = path.read_bytes()[:18]
    if len(data) != 18:
        raise RuntimeError(f"short TGA header: {path}")
    return {
        "image_type": data[2],
        "width": struct.unpack_from("<H", data, 12)[0],
        "height": struct.unpack_from("<H", data, 14)[0],
        "bpp": data[16],
    }


def xmodel_stats(text: str) -> dict:
    def one(pattern: str, label: str) -> int:
        m = re.search(pattern, text, re.MULTILINE)
        if not m:
            raise RuntimeError(f"missing {label}")
        return int(m.group(1))

    return {
        "version": one(r"^VERSION\s+(\d+)\s*$", "VERSION"),
        "bones": one(r"^NUMBONES\s+(\d+)\s*$", "NUMBONES"),
        "vertices": one(r"^NUMVERTS\s+(\d+)\s*$", "NUMVERTS"),
        "triangles": one(r"^NUMFACES\s+(\d+)\s*$", "NUMFACES"),
        "objects": one(r"^NUMOBJECTS\s+(\d+)\s*$", "NUMOBJECTS"),
        "materials": one(r"^NUMMATERIALS\s+(\d+)\s*$", "NUMMATERIALS"),
        "bone_names": re.findall(r'^BONE\s+\d+\s+-?\d+\s+"([^"]+)"\s*$', text, re.MULTILINE),
        "material_lines": re.findall(r'^MATERIAL\s+.*$', text, re.MULTILINE),
        "uv_lines": len(re.findall(r"^UV\s+", text, re.MULTILINE)),
        "normal_lines": len(re.findall(r"^NORMAL\s+", text, re.MULTILINE)),
    }


def validate_blob(path: Path, expected: str) -> None:
    actual = git_blob_sha1(path)
    if actual != expected:
        raise RuntimeError(
            f"Git blob mismatch for {path}: expected {expected}, got {actual}"
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("modtools_root", type=Path)
    ap.add_argument("output_dir", type=Path)
    args = ap.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    src = args.modtools_root.resolve()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)

    model_rec = manifest["model"]
    model_path = src / model_rec["path"]
    if not model_path.is_file():
        raise SystemExit(f"missing model: {model_path}")
    validate_blob(model_path, model_rec["sha1"])

    text = model_path.read_text(encoding="utf-8")
    stats = xmodel_stats(text)

    expected = {
        "version": model_rec["xmodel_version"],
        "bones": model_rec["bones"],
        "vertices": model_rec["vertices"],
        "triangles": model_rec["triangles"],
        "objects": model_rec["objects"],
        "materials": model_rec["materials"],
    }
    for key, value in expected.items():
        if stats[key] != value:
            raise RuntimeError(
                f"XMODEL {key} mismatch: expected {value}, got {stats[key]}"
            )

    missing_tags = [
        tag for tag in manifest["required_tags"] if tag not in stats["bone_names"]
    ]
    if missing_tags:
        raise RuntimeError(f"missing required XMODEL tags: {missing_tags}")

    # Each triangle contributes three UV and three NORMAL records in this
    # XMODEL_EXPORT. Failing this gate means the importer must not continue.
    expected_corner_records = stats["triangles"] * 3
    if stats["uv_lines"] != expected_corner_records:
        raise RuntimeError(
            f"UV record mismatch: expected {expected_corner_records}, "
            f"got {stats['uv_lines']}"
        )
    if stats["normal_lines"] != expected_corner_records:
        raise RuntimeError(
            f"NORMAL record mismatch: expected {expected_corner_records}, "
            f"got {stats['normal_lines']}"
        )

    copied = []
    model_dst = out / "model" / model_path.name
    model_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(model_path, model_dst)
    copied.append(str(model_dst.relative_to(out)))

    tga_report = []
    for rec in manifest["textures"]:
        path = src / rec["path"]
        if not path.is_file():
            raise RuntimeError(f"missing texture: {path}")
        validate_blob(path, rec["sha1"])
        hdr = parse_tga_header(path)

        if "width" in rec and hdr["width"] != rec["width"]:
            raise RuntimeError(
                f"texture width mismatch for {path}: "
                f"{hdr['width']} != {rec['width']}"
            )
        if "height" in rec and hdr["height"] != rec["height"]:
            raise RuntimeError(
                f"texture height mismatch for {path}: "
                f"{hdr['height']} != {rec['height']}"
            )
        if "expected_bytes" in rec and path.stat().st_size != rec["expected_bytes"]:
            raise RuntimeError(
                f"texture byte-size mismatch for {path}: "
                f"{path.stat().st_size} != {rec['expected_bytes']}"
            )

        dst = out / "textures" / path.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dst)
        copied.append(str(dst.relative_to(out)))
        tga_report.append({
            "name": path.name,
            "role": rec["role"],
            "bytes": path.stat().st_size,
            **hdr,
        })

    anim_root = src / manifest["animation_root"]
    anim_report = []
    for name in manifest["animations"]:
        path = anim_root / name
        if not path.is_file():
            raise RuntimeError(f"missing animation: {path}")
        body = path.read_text(encoding="utf-8")
        fr = re.search(r"^FRAMERATE\s+(\d+)\s*$", body, re.MULTILINE)
        nf = re.search(r"^NUMFRAMES\s+(\d+)\s*$", body, re.MULTILINE)
        np = re.search(r"^NUMPARTS\s+(\d+)\s*$", body, re.MULTILINE)
        if not (fr and nf and np):
            raise RuntimeError(f"invalid XANIM header: {path}")

        dst = out / "animations" / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dst)
        copied.append(str(dst.relative_to(out)))
        anim_report.append({
            "name": name,
            "framerate": int(fr.group(1)),
            "frames": int(nf.group(1)),
            "parts": int(np.group(1)),
        })

    report = {
        "name": manifest["name"],
        "model": {
            **expected,
            "bone_names": stats["bone_names"],
            "uv_records": stats["uv_lines"],
            "normal_records": stats["normal_lines"],
            "material_lines": stats["material_lines"],
        },
        "textures": tga_report,
        "animations": anim_report,
        "copied": copied,
        "status": "VALIDATED",
    }
    (out / "validation_report.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
