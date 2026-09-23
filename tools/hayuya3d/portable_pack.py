#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

from gameprep import GamePrepResult, build_gameprep
from mobile_portability import build_portability_plan
from visual_judge import SourceViewScore

TIERS = ("flagship", "high", "balanced", "compatibility")


@dataclass
class PortableTierArtifact:
    tier: str
    directory: str
    portability_plan: dict
    gameprep: dict


@dataclass
class PortablePackResult:
    hero_master: str
    tiers: list[PortableTierArtifact]
    manifest: str
    asset_mode: str
    profile_name: str
    complete_lod_chain: bool
    notes: list[str]


def _tier_dir_name(tier: str) -> str:
    return {
        "flagship": "Flagship",
        "high": "High",
        "balanced": "Balanced",
        "compatibility": "Compatibility",
    }[tier]


def build_portable_pack(
    hero_glb: Path,
    out_dir: Path,
    *,
    mode: str,
    profile_name: str,
    anchor_view: SourceViewScore | None = None,
    material_samples: int = 180_000,
    tiers: tuple[str, ...] = TIERS,
) -> PortablePackResult:
    hero_glb = hero_glb.resolve()
    if not hero_glb.is_file():
        raise FileNotFoundError(hero_glb)

    out_dir.mkdir(parents=True, exist_ok=True)
    hero_dir = out_dir / "HeroMaster"
    hero_dir.mkdir(parents=True, exist_ok=True)
    hero_out = hero_dir / "master.glb"
    shutil.copy2(hero_glb, hero_out)

    artifacts: list[PortableTierArtifact] = []
    complete_lod_chain = True
    notes: list[str] = [
        "HeroMaster/master.glb is an exact preserved copy and is never capped by a mobile runtime tier.",
        "Each runtime tier is independently derived from HeroMaster rather than from a lower-quality tier.",
    ]

    for tier in tiers:
        plan = build_portability_plan(
            mode=mode,
            tier=tier,
            profile_name=profile_name,
        )
        runtime = plan["runtime_target"]
        target_faces = int(runtime["lod0_triangles"][1])
        max_texture_size = int(runtime["exceptional_texture_edge_px"])

        tier_dir = out_dir / _tier_dir_name(tier)
        result: GamePrepResult = build_gameprep(
            hero_glb,
            tier_dir,
            target_faces=target_faces,
            anchor_view=anchor_view,
            material_samples=material_samples,
            max_texture_size=max_texture_size,
        )
        if len(result.lods) < 4:
            complete_lod_chain = False

        tier_manifest = {
            "tier": tier,
            "portability_plan": plan,
            "gameprep": asdict(result),
        }
        (tier_dir / "tier_manifest.json").write_text(
            json.dumps(tier_manifest, indent=2) + "\n",
            encoding="utf-8",
        )
        artifacts.append(
            PortableTierArtifact(
                tier=tier,
                directory=str(tier_dir),
                portability_plan=plan,
                gameprep=asdict(result),
            )
        )

    if not complete_lod_chain:
        notes.append(
            "One or more tiers could not emit LOD1-LOD3 because the accepted GLB is skinned. "
            "HAYUYA preserves JOINTS/WEIGHTS instead of destructively simplifying rigged geometry."
        )

    manifest = out_dir / "portable_pack_manifest.json"
    result = PortablePackResult(
        hero_master=str(hero_out),
        tiers=artifacts,
        manifest=str(manifest),
        asset_mode=mode,
        profile_name=profile_name,
        complete_lod_chain=complete_lod_chain,
        notes=notes,
    )
    manifest.write_text(json.dumps(asdict(result), indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build all HAYUYA mobile portability tiers from one preserved Hero Master."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=["prop", "character", "architecture"], required=True)
    parser.add_argument(
        "--profile",
        choices=["preview", "mobile", "game", "monster", "ultra"],
        default="ultra",
    )
    parser.add_argument("--material-samples", type=int, default=180000)
    args = parser.parse_args()

    result = build_portable_pack(
        args.input,
        args.output,
        mode=args.mode,
        profile_name=args.profile,
        material_samples=args.material_samples,
    )
    print(json.dumps(asdict(result), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
