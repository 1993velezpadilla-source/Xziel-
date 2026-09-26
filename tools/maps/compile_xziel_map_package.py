#!/usr/bin/env python3
"""Compile a folder or ZIP into a deterministic strict XZIEL .xzp package."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "tools/maps/build_xziel_map_package.py"

spec = importlib.util.spec_from_file_location("xziel_map_builder", BUILDER)
if spec is None or spec.loader is None:
    raise SystemExit("unable to load XZIEL map package builder")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

FIXED_ZIP_DT = (2000, 1, 1, 0, 0, 0)


def add_bytes(zf: zipfile.ZipFile, arcname: str, payload: bytes) -> None:
    info = zipfile.ZipInfo(arcname, FIXED_ZIP_DT)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    zf.writestr(info, payload)


def compile_package(src: Path, out: Path) -> dict:
    src = src.resolve()
    if not src.exists():
        raise SystemExit(f"input does not exist: {src}")

    temp = None
    if src.is_dir():
        root = src
        source_kind = "folder"
    elif src.is_file() and src.suffix.lower() == ".zip":
        temp = tempfile.TemporaryDirectory(prefix="xziel-pack-")
        root = Path(temp.name)
        builder.safe_extract_zip(src, root)
        source_kind = "zip"
    else:
        raise SystemExit("input must be a directory or ZIP")

    try:
        manifest = builder.build_manifest(root, source_kind, src.name)
        if not manifest["summary"]["strictReady"]:
            raise SystemExit(
                "XZIEL package rejected: zero-omission inventory has blockers: "
                + json.dumps(manifest["blockers"], sort_keys=True)
            )

        manifest["package"] = {
            "format": "xziel_xzp_v1",
            "payloadRoot": "payload/",
            "deterministic": True,
            "sourceBytesPreserved": True,
        }
        manifest_bytes = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")

        out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out, "w") as zf:
            add_bytes(zf, "xziel.package.json", manifest_bytes)
            for row in sorted(manifest["files"], key=lambda r: r["path"]):
                payload = (root / row["path"]).read_bytes()
                add_bytes(zf, "payload/" + row["path"], payload)

        return manifest
    finally:
        if temp is not None:
            temp.cleanup()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    manifest = compile_package(args.input, args.output)
    print(
        "XZIEL_XZP_BUILD_OK",
        json.dumps(
            {
                "output": str(args.output),
                "files": manifest["summary"]["fileCount"],
                "bytes": manifest["summary"]["totalBytes"],
            },
            sort_keys=True,
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
