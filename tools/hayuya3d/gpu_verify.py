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
    rig_audit = gameprep.get("rig_audit") or {}
    has_skin = int(rig_audit.get("skin_count", 0)) > 0
    expected_lods = 1 if has_skin else 4
    if len(lods) != expected_lods:
        raise SystemExit(
            f"expected {expected_lods} LOD entries for "
            f"{'skinned' if has_skin else 'unrigged'} asset, found {len(lods)}"
        )
    for lod in lods:
        validate_glb(Path(lod["path"]))

    frames = [Path(p) for p in gameprep.get("turntable_frames", [])]
    if len(frames) != 24 or not all(p.is_file() for p in frames):
        raise SystemExit("expected 24 valid turntable frames")

    judge_v4 = data.get("judge_v4") or {}
    if judge_v4.get("passed") is not True:
        reasons = judge_v4.get("hard_fail_reasons") or []
        raise SystemExit(
            "Judge v4 did not pass final visual acceptance: "
            + ";".join(str(x) for x in reasons[:16])
        )

    aaa = data.get("aaa_acceptance") or {}
    visual_gate = next(
        (
            gate for gate in (aaa.get("gates") or [])
            if gate.get("id") == "character.visual_judge_v4"
        ),
        None,
    )
    if visual_gate is not None and visual_gate.get("ready") is not True:
        raise SystemExit("AAA visual Judge v4 gate is not ready")

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
        "rig_ready": bool(rig_audit.get("rig_ready")),
        "skin_count": int(rig_audit.get("skin_count", 0)),
        "lod_policy": gameprep.get("lod_policy"),
        "turntable_frames": len(frames),
        "judge_v4_passed": True,
        "judge_v4_hard_failures": len(judge_v4.get("hard_fail_reasons") or []),
        "aaa_visual_v4_ready": (
            bool(visual_gate.get("ready")) if visual_gate is not None else None
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
