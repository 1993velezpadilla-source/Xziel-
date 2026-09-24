#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STANDARD_PATH = ROOT / "hayuya" / "standards" / "hayuya_lighting_brain_v1.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compile_lighting_intelligence(profile_id: str = "zombies_horror") -> dict[str, Any]:
    standard = _read_json(STANDARD_PATH)
    profiles = standard["profiles"]
    if profile_id not in profiles:
        raise ValueError(
            f"unknown HAYUYA Lighting profile {profile_id!r}; "
            f"available: {', '.join(sorted(profiles))}"
        )

    profile = profiles[profile_id]
    return {
        "engine": "HAYUYA Lighting",
        "schema": 1,
        "profile_id": profile_id,
        "source_knowledge": standard["sourceKnowledge"],
        "intent": profile["intent"],
        "layers": profile["layers"],
        "states": profile["states"],
        "authored_metrics": profile["authoredMetrics"],
        "mobile_policy": profile["mobilePolicy"],
        "judge_gates": standard["judgeGates"],
        "guardrails": standard["guardrails"],
        "generation_passes": [
            "analyze_geometry_and_semantic_zones",
            "identify_critical_navigation_and_combat_surfaces",
            "identify_global_and_regional_landmarks",
            "propose_motivated_practical_sources",
            "compose_base_visibility",
            "compose_landmark_guidance",
            "reserve_negative_space_and_shadow",
            "author_power_off_and_power_on_states",
            "author_rare_event_lighting",
            "evaluate_enemy_silhouette_readability",
            "evaluate_material_response_and_depth",
            "bound_dynamic_cost_by_device_tier",
            "run_lighting_judge",
        ],
        "beauty_contract": {
            "goal": "cinematic, coherent, atmospheric and gameplay-readable rather than uniformly bright",
            "preserve_material_identity": True,
            "depth_layers_required": True,
            "landmark_composition_required": True,
            "color_temperature_relationship_required": True,
            "exposure_consistency_required": True,
            "black_crush_on_critical_path_allowed": False,
            "constant_random_flicker_allowed": False,
        },
    }


def auto_lighting_profile(goal: str) -> str | None:
    value = goal.casefold()
    triggers = (
        "zombie",
        "undead",
        "horror",
        "sanctum",
        "scary",
        "thriller",
    )
    if any(token in value for token in triggers):
        return "zombies_horror"
    return None
