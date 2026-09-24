#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

from hayuya_ads import compile_monetization_intelligence
from hayuya_lighting import auto_lighting_profile, compile_lighting_intelligence
from map_design_brain import auto_design_profile, compile_design_intelligence
from universal_game_design import compile_universal_design_intelligence
from map_source_registry import default_providers, readiness_report
from world_semantics import SourceRecord, WorldGraph


WORLD_STAGES = (
    "source_intake",
    "provenance_and_rights",
    "geo_registration",
    "open_vocabulary_perception",
    "segmentation_and_tracking",
    "metric_camera_depth_geometry",
    "world_graph_fusion",
    "conflict_and_uncertainty_resolution",
    "missing_space_inference",
    "world_synthesis",
    "world_judge",
    "xziel_compile",
    "runtime_acceptance",
)


def source_id_for(index: int, uri: str) -> str:
    token = hashlib.sha256(uri.encode("utf-8")).hexdigest()[:10]
    return f"source-{index:03d}-{token}"


def infer_source_kind(uri: str) -> str:
    parsed = urlparse(uri)
    suffix = Path(parsed.path).suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".heic", ".avif"}:
        return "image"
    if suffix in {".mp4", ".mov", ".mkv", ".webm"}:
        return "video"
    if suffix in {".glb", ".gltf", ".obj", ".ply", ".fbx", ".usd", ".usdz"}:
        return "geometry"
    if suffix in {".las", ".laz", ".e57"}:
        return "point_cloud"
    if parsed.scheme in {"http", "https"}:
        return "remote_reference"
    return "reference"


def parse_bounds(value: str | None) -> list[float] | None:
    if not value:
        return None
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 4:
        raise ValueError("--bounds expects west,south,east,north")
    bounds = [float(part) for part in parts]
    west, south, east, north = bounds
    if not -180.0 <= west <= 180.0 or not -180.0 <= east <= 180.0:
        raise ValueError("longitude bounds must be within [-180, 180]")
    if not -90.0 <= south <= 90.0 or not -90.0 <= north <= 90.0:
        raise ValueError("latitude bounds must be within [-90, 90]")
    if east <= west or north <= south:
        raise ValueError("bounds must have east>west and north>south")
    return bounds


def make_plan(
    *,
    job_id: str,
    sources: list[str],
    goal: str,
    provider_ids: list[str],
    bounds: list[float] | None = None,
    center: tuple[float, float, float] | None = None,
    env: dict[str, str] | None = None,
    design_profile: str | None = "auto",
    lighting_profile: str | None = "auto",
    universal_design_mode: str = "auto",
    monetization_mode: str = "auto",
) -> dict:
    registry = default_providers()
    unknown = [provider_id for provider_id in provider_ids if provider_id not in registry]
    if unknown:
        raise ValueError(f"unknown providers: {', '.join(unknown)}")

    graph = WorldGraph(
        graph_id=job_id,
        metadata={
            "goal": goal,
            "ontology_policy": "open_world_freeform",
            "unknown_entities_allowed": True,
        },
    )
    for index, uri in enumerate(sources, start=1):
        graph.add_source(
            SourceRecord(
                source_id=source_id_for(index, uri),
                uri=uri,
                provider="user_capture" if "://" not in uri else "external_reference",
                kind=infer_source_kind(uri),
                usage="unresolved_until_provenance_gate",
            )
        )

    resolved_design_profile = design_profile
    if resolved_design_profile == "auto":
        resolved_design_profile = auto_design_profile(goal)

    resolved_lighting_profile = lighting_profile
    if resolved_lighting_profile == "auto":
        resolved_lighting_profile = auto_lighting_profile(goal)

    design_intelligence = (
        compile_design_intelligence(resolved_design_profile)
        if resolved_design_profile
        else None
    )
    lighting_horror_identities = (
        [
            item["value"]
            for item in design_intelligence["constraints"].get("horror", [])
        ]
        if design_intelligence
        else []
    )
    lighting_intelligence = (
        compile_lighting_intelligence(
            resolved_lighting_profile,
            horror_identities=lighting_horror_identities,
        )
        if resolved_lighting_profile
        else None
    )

    universal_design_intelligence = (
        compile_universal_design_intelligence(goal)
        if universal_design_mode != "off"
        else None
    )
    world_graph_dict = graph.to_dict()
    monetization_intelligence = compile_monetization_intelligence(
        world_graph_dict,
        enabled=(monetization_mode != "off"),
    )

    geo = {
        "bounds_wsen": bounds,
        "center": (
            {"latitude": center[0], "longitude": center[1], "radius_m": center[2]}
            if center
            else None
        ),
        "coordinate_pipeline": ["WGS84", "ECEF", "ENU", "HAYUYA_LOCAL_METERS", "XZIEL_WORLD"],
    }

    return {
        "engine": "HAYUYA MAP",
        "schema": 1,
        "job_id": job_id,
        "goal": goal,
        "world_graph": world_graph_dict,
        "geospatial": geo,
        "providers": readiness_report(provider_ids, env=env),
        "knowledge_library": {
            "zombies_map_dna_atlas": "docs/zombies-map-dna-atlas.v1.json",
            "zombies_map_dna_coverage": "docs/zombies-map-dna-coverage.v1.json",
            "sanctum_zombies_dna_profile": "docs/sanctum-zombies-dna-profile.v1.json",
            "waw_horror_dna": "docs/WAW_ZOMBIES_HORROR_DNA.md",
            "waw_horror_checklist": "docs/waw-zombies-horror-checklist.json",
            "map_design_standard": "hayuya/standards/hayuya_map_design_brain_v1.json",
            "lighting_standard": "hayuya/standards/hayuya_lighting_brain_v1.json",
            "zombies_design_pattern_library": "hayuya/knowledge/zombies_design_pattern_library_v1.json",
            "zombies_lighting_pattern_library": "hayuya/knowledge/zombies_lighting_pattern_library_v1.json",
            "universal_game_design_standard": "hayuya/standards/hayuya_universal_game_design_brain_v1.json",
            "world_generation_ai_atlas": "hayuya/knowledge/world_generation_ai_atlas_v1.json",
            "monetization_standard": "hayuya/standards/hayuya_monetization_brain_v1.json",
        },
        "map_design_intelligence": design_intelligence,
        "universal_game_design_intelligence": universal_design_intelligence,
        "lighting_intelligence": lighting_intelligence,
        "monetization_intelligence": monetization_intelligence,
        "stages": list(WORLD_STAGES),
        "perception_policy": {
            "closed_class_detector_is_authoritative": False,
            "freeform_labels": True,
            "freeform_relations": True,
            "unknown_is_valid": True,
            "ensemble_required": True,
            "suggested_layers": [
                "vision_language_scene_reasoner",
                "open_vocabulary_detector",
                "promptable_segmenter",
                "ocr",
                "metric_geometry_reconstructor",
                "earth_observation_foundation_model",
            ],
        },
        "truth_layers": {
            "observed": "direct source evidence",
            "inferred": "plausible completion supported by evidence/priors",
            "generated": "intentional authored content",
            "policy": "never collapse inferred/generated content into observed truth",
        },
        "delegation": {
            "isolated_hero_assets": "HAYUYA Monster arena",
            "large_environment_geometry": "HAYUYA Map world reconstruction pipeline",
            "runtime": "Xziel XZSM/XMAP compiler",
        },
        "outputs": [
            "world_graph.json",
            "source_provenance.json",
            "coordinate_manifest.json",
            "world_judge.json",
            "hero_world_master",
            "XZSM",
            "XMAP",
            "nav_and_collision",
            "streaming_cells",
            "qa_package",
            "universal_game_design.json",
            "monetization.json",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HAYUYA MAP open-world planning foundation; no fixed object taxonomy."
    )
    parser.add_argument("--job-id", default="hayuya-map-job")
    parser.add_argument("--goal", default="reconstruct and author a playable world")
    parser.add_argument("--source", action="append", default=[], help="repeatable local path or URL")
    parser.add_argument(
        "--provider",
        action="append",
        default=[],
        help="repeatable provider id; use --list-providers to inspect",
    )
    parser.add_argument("--bounds", help="west,south,east,north")
    parser.add_argument("--latitude", type=float)
    parser.add_argument("--longitude", type=float)
    parser.add_argument("--radius-m", type=float, default=500.0)
    parser.add_argument("--output-root", type=Path, default=ROOT / "out" / "hayuya-map")
    parser.add_argument(
        "--design-profile",
        default="auto",
        help="HAYUYA Map Structure Brain profile; auto enables Zombies DNA for zombie/horror goals",
    )
    parser.add_argument(
        "--lighting-profile",
        default="auto",
        help="HAYUYA Lighting profile; auto enables horror lighting for zombie/horror goals",
    )
    parser.add_argument(
        "--universal-design",
        choices=["off", "auto", "required"],
        default="auto",
        help="cross-genre game-space reasoning and solver planning",
    )
    parser.add_argument(
        "--monetization",
        choices=["off", "auto", "required"],
        default="auto",
        help="pre-author safe diegetic inventory plus Google AdMob UI hooks",
    )
    parser.add_argument("--list-providers", action="store_true")
    args = parser.parse_args()

    registry = default_providers()
    if args.list_providers:
        print(json.dumps(readiness_report(), indent=2))
        return 0

    providers = args.provider or ["user_capture", "overture_maps", "openstreetmap_overpass"]
    center = None
    if args.latitude is not None or args.longitude is not None:
        if args.latitude is None or args.longitude is None:
            parser.error("--latitude and --longitude must be provided together")
        if not -90.0 <= args.latitude <= 90.0:
            parser.error("--latitude must be within [-90, 90]")
        if not -180.0 <= args.longitude <= 180.0:
            parser.error("--longitude must be within [-180, 180]")
        if args.radius_m <= 0:
            parser.error("--radius-m must be > 0")
        center = (args.latitude, args.longitude, args.radius_m)

    try:
        bounds = parse_bounds(args.bounds)
        plan = make_plan(
            job_id=args.job_id,
            sources=args.source,
            goal=args.goal,
            provider_ids=providers,
            bounds=bounds,
            center=center,
            design_profile=args.design_profile,
            lighting_profile=args.lighting_profile,
            universal_design_mode=args.universal_design,
            monetization_mode=args.monetization,
        )
    except ValueError as exc:
        parser.error(str(exc))

    job_dir = args.output_root / args.job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    output = job_dir / "plan.json"
    output.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")

    intelligence_dir = job_dir / "intelligence"
    intelligence_dir.mkdir(parents=True, exist_ok=True)
    if plan["map_design_intelligence"] is not None:
        (intelligence_dir / "map_design.json").write_text(
            json.dumps(plan["map_design_intelligence"], indent=2) + "\n",
            encoding="utf-8",
        )
    if plan["lighting_intelligence"] is not None:
        (intelligence_dir / "lighting.json").write_text(
            json.dumps(plan["lighting_intelligence"], indent=2) + "\n",
            encoding="utf-8",
        )
    if plan["universal_game_design_intelligence"] is not None:
        (intelligence_dir / "universal_game_design.json").write_text(
            json.dumps(plan["universal_game_design_intelligence"], indent=2) + "\n",
            encoding="utf-8",
        )
    if plan["monetization_intelligence"] is not None:
        (intelligence_dir / "monetization.json").write_text(
            json.dumps(plan["monetization_intelligence"], indent=2) + "\n",
            encoding="utf-8",
        )

    knowledge_manifest = {
        "schema": 1,
        "job_id": args.job_id,
        "knowledge_library": plan["knowledge_library"],
        "design_profile": (
            plan["map_design_intelligence"]["profile_id"]
            if plan["map_design_intelligence"]
            else None
        ),
        "lighting_profile": (
            plan["lighting_intelligence"]["profile_id"]
            if plan["lighting_intelligence"]
            else None
        ),
        "universal_design_enabled": plan["universal_game_design_intelligence"] is not None,
        "universal_design_domains": (
            plan["universal_game_design_intelligence"]["selected_domains"]
            if plan["universal_game_design_intelligence"]
            else []
        ),
        "monetization_enabled": plan["monetization_intelligence"]["enabled"],
        "monetization_candidate_count": plan["monetization_intelligence"]["candidate_count"],
    }
    (intelligence_dir / "knowledge_manifest.json").write_text(
        json.dumps(knowledge_manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(plan, indent=2))
    print(f"HAYUYA_MAP_PLAN_READY {output}")
    print(f"HAYUYA_MAP_INTELLIGENCE_READY {intelligence_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
