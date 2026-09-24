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
        "world_graph": graph.to_dict(),
        "geospatial": geo,
        "providers": readiness_report(provider_ids, env=env),
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
        )
    except ValueError as exc:
        parser.error(str(exc))

    job_dir = args.output_root / args.job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    output = job_dir / "plan.json"
    output.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(plan, indent=2))
    print(f"HAYUYA_MAP_PLAN_READY {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
