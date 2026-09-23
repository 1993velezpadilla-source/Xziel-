#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def validate_glb(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.read_bytes()[:4] != b"glTF":
        raise ValueError(f"invalid GLB magic: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify HAYUYA GPU E2E output package.")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifests = list(args.root.rglob("manifest.json"))
    if not manifests:
        raise SystemExit("GPU E2E produced no HAYUYA manifest")

    manifest_path = max(manifests, key=lambda p: p.stat().st_mtime)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))

    final_glb = Path(data["final_glb"])
    validate_glb(final_glb)

    gameprep = data.get("gameprep")
    if not gameprep:
        raise SystemExit("GamePrep required but missing from manifest")

    lods = gameprep.get("lods", [])
    if len(lods) != 4:
        raise SystemExit(f"expected 4 LODs, found {len(lods)}")
    for lod in lods:
        validate_glb(Path(lod["path"]))

    frames = [Path(p) for p in gameprep.get("turntable_frames", [])]
    if len(frames) != 8 or not all(p.is_file() for p in frames):
        raise SystemExit("expected 8 valid turntable frames")

    report = {
        "status": "PASS",
        "manifest": str(manifest_path),
        "final_glb": str(final_glb),
        "champion": data.get("champion", {}).get("backend"),
        "score": data.get("champion", {}).get("score"),
        "viewforge": bool(data.get("viewforge")),
        "geometry_refinement": data.get("geometry_refinement"),
        "material_bridge": data.get("material_bridge"),
        "gameprep_lods": len(lods),
        "turntable_frames": len(frames),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
