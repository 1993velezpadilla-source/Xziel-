#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
AI_ATLAS_PATH = ROOT / "hayuya" / "knowledge" / "world_generation_ai_atlas_v1.json"
RESEARCH_STACK_PATH = ROOT / "hayuya" / "standards" / "hayuya_map_research_stack_v1.json"


STAGE_ROUTING = {
    "open_vocabulary_perception": [
        {"id": "grounding_dino", "mode": "candidate"},
        {"id": "sam2", "mode": "candidate"},
    ],
    "metric_geometry_arena": [
        {"id": "meta_mapanything", "mode": "candidate"},
        {"id": "meta_vggt", "mode": "challenger"},
    ],
    "earth_observation": [
        {"id": "clay", "mode": "candidate"},
    ],
    "world_generation_research": [
        {"id": "hy_world_2", "mode": "license_gated_candidate"},
        {"id": "worldgen_scene_pipeline", "mode": "research_candidate"},
    ],
    "missing_space_extension": [
        {"id": "hunyuanworld_voyager", "mode": "research_candidate"},
    ],
    "interactive_world_simulation": [
        {"id": "hy_worldplay", "mode": "research_candidate"},
        {"id": "google_genie_3", "mode": "product_benchmark"},
    ],
    "world_editing_product_benchmark": [
        {"id": "world_labs_marble", "mode": "product_benchmark"},
    ],
    "scene_layout_architecture_reference": [
        {"id": "nvidia_edify_scene_composition", "mode": "research_reference"},
        {"id": "promethean_ai", "mode": "product_benchmark"},
        {"id": "ludo_ai", "mode": "product_benchmark"},
        {"id": "unreal_pcg", "mode": "engine_architecture_reference"},
    ],
}


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compile_world_model_broker() -> dict[str, Any]:
    atlas = _read(AI_ATLAS_PATH)
    research = _read(RESEARCH_STACK_PATH)
    systems = {item["id"]: item for item in atlas["systems"]}
    model_research = {
        item["id"]: item
        for item in research.get("models", [])
    }

    stages: dict[str, list[dict[str, Any]]] = {}
    missing: list[str] = []
    for stage, entries in STAGE_ROUTING.items():
        stages[stage] = []
        for entry in entries:
            system = systems.get(entry["id"])
            research_entry = model_research.get(entry["id"])
            if system is None and research_entry is None:
                missing.append(entry["id"])
                continue

            public = system or research_entry
            stages[stage].append(
                {
                    "id": entry["id"],
                    "mode": entry["mode"],
                    "source": public.get("source") or public.get("url"),
                    "integration_role": public.get("integrationRole"),
                    "commercial_candidate": (
                        research_entry.get("commercial_candidate")
                        if research_entry
                        else None
                    ),
                    "execution": {
                        "wired_in_hayuya_map": False,
                        "reason": (
                            "research/selection contract only until a pinned backend, "
                            "environment, license gate and executable adapter are added"
                        ),
                    },
                }
            )

    if missing:
        raise ValueError(
            "World Model Broker routing references unknown systems: "
            + ", ".join(sorted(set(missing)))
        )

    return {
        "engine": "HAYUYA World Model Broker",
        "schema": 1,
        "stages": stages,
        "policies": {
            "research_is_not_execution": True,
            "no_private_api_reverse_engineering": True,
            "backend_requires_pinned_version": True,
            "backend_requires_license_review": True,
            "backend_requires_environment_lock": True,
            "backend_requires_adapter_tests": True,
            "independent_challengers_for_uncertain_geometry": True,
            "product_benchmarks_never_claim_local_execution": True,
        },
        "promotion_contract": [
            "public_or_authorized_access",
            "license_and_terms_review",
            "pinned_revision_or_api_version",
            "reproducible_environment",
            "adapter",
            "smoke_test",
            "source_evidence_judge",
            "resource_budget",
        ],
        "knowledge": {
            "ai_atlas": str(AI_ATLAS_PATH.relative_to(ROOT)),
            "research_stack": str(RESEARCH_STACK_PATH.relative_to(ROOT)),
            "studied_system_count": len(systems),
        },
    }
