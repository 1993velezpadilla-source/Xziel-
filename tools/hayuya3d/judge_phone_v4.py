#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from gameprep import build_turntable
from judge_v4 import run_judge_v4


IMAGE_EXTS={".png",".jpg",".jpeg",".webp"}


def _images(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return [
        path for path in sorted(root.rglob("*"))
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS
    ]


def _is_character(manifest: dict) -> bool:
    values=[
        manifest.get("asset_profile"),
        (manifest.get("asset") or {}).get("profile"),
        manifest.get("mode"),
    ]
    text=" ".join(str(x or "").lower() for x in values)
    return any(token in text for token in (
        "character","humanoid","creature","monster","zombie","undead","human"
    ))


def main()->int:
    p=argparse.ArgumentParser(
        description=(
            "Mandatory CPU-capable HAYUYA visual pre-approval. "
            "Uses Judge v4 core tier before Hub persistence."
        )
    )
    p.add_argument("--output-root",type=Path,required=True)
    p.add_argument("--python",default=sys.executable)
    p.add_argument("--force-character",action="store_true")
    a=p.parse_args()

    root=a.output_root
    manifest_path=root/"manifest.json"
    final_glb=root/"hayuya_final.glb"
    if not manifest_path.is_file():
        raise SystemExit("manifest missing before Judge v4 core")
    if not final_glb.is_file():
        raise SystemExit("final GLB missing before Judge v4 core")

    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    character=a.force_character or _is_character(manifest)
    if not character:
        manifest["judge_v4_core"]={
            "schema":4,
            "applicable":False,
            "passed":True,
            "reason":"non-character asset",
        }
        manifest_path.write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
        print("HAYUYA_JUDGE_V4_CORE_SKIPPED non-character")
        return 0

    source_images=_images(root/"prepared_views")
    detail_images=_images(root/"prepared_details")
    if not source_images:
        raise SystemExit("Judge v4 core requires prepared source images")

    turntable_dir=root/"judge_v4_core"/"turntable"
    turntable=[
        Path(path) for path in build_turntable(
            final_glb,
            turntable_dir,
            anchor_view=None,
        )
    ]
    report=run_judge_v4(
        final_glb=final_glb,
        source_images=source_images,
        detail_images=detail_images,
        turntable_frames=turntable,
        out_dir=root/"judge_v4_core",
        policy="required",
        python_executable=a.python,
        tier="core",
    )
    manifest["judge_v4_core"]=asdict(report)
    manifest["visual_approval"]={
        "schema":1,
        "state":"core_pass" if report.passed else "rejected",
        "production_approved":False,
        "core_passed":bool(report.passed),
        "pro_required":True,
        "hard_fail_reasons":list(report.hard_fail_reasons),
        "note":(
            "Core is the mandatory CPU pre-screen. Monster/Ultra production "
            "approval still requires Judge v4 Pro on the HAYUYA GPU worker."
        ),
    }
    manifest_path.write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print(
        "HAYUYA_JUDGE_V4_CORE "
        f"passed={str(bool(report.passed)).lower()} "
        f"hard_failures={len(report.hard_fail_reasons)}"
    )
    if not report.passed:
        print("\n".join(report.hard_fail_reasons[:32]),file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    raise SystemExit(main())
