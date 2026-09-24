#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STANDARD_PATH = ROOT / "hayuya" / "standards" / "hayuya_encounter_director_v1.json"
PROFILES = {
    "church_giants": ROOT / "hayuya" / "knowledge" / "church_giant_encounters_v1.json",
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compile_encounter_intelligence(profile_id: str = "church_giants") -> dict[str, Any]:
    if profile_id not in PROFILES:
        raise ValueError(
            f"unknown HAYUYA encounter profile {profile_id!r}; "
            f"available: {', '.join(sorted(PROFILES))}"
        )

    standard = _read_json(STANDARD_PATH)
    profile = _read_json(PROFILES[profile_id])

    actors = profile.get("actors", [])
    actor_ids = [str(actor.get("id", "")).strip() for actor in actors]
    if not actors or any(not actor_id for actor_id in actor_ids):
        raise ValueError("encounter profile must define actors with non-empty ids")
    if len(set(actor_ids)) != len(actor_ids):
        raise ValueError("encounter profile contains duplicate actor ids")

    templates = profile.get("encounterTemplates", [])
    if not templates:
        raise ValueError("encounter profile must define at least one encounter template")

    known_actor_ids = set(actor_ids)
    for template in templates:
        referenced = []
        if template.get("actor"):
            referenced.append(template["actor"])
        referenced.extend(template.get("actors", []))
        missing = sorted(set(referenced) - known_actor_ids)
        if missing:
            raise ValueError(
                f"encounter template {template.get('id', '<unknown>')!r} "
                f"references missing actors: {', '.join(missing)}"
            )

    return {
        "engine": "HAYUYA Encounter Director",
        "schema": 1,
        "profile_id": profile_id,
        "knowledge": {
            "standard": "hayuya/standards/hayuya_encounter_director_v1.json",
            "profile": "hayuya/knowledge/church_giant_encounters_v1.json",
        },
        "principles": standard["principles"],
        "phases": standard["phases"],
        "channels": standard["channels"],
        "animation_contract": standard["animationContract"],
        "placement_contract": standard["placementContract"],
        "runtime_contract": standard["runtimeContract"],
        "judge_gates": standard["judgeGates"],
        "mobile_policy": standard["mobilePolicy"],
        "design_intent": profile["designIntent"],
        "actors": actors,
        "encounter_templates": templates,
        "variant_system": profile["variantSystem"],
        "world_integration": profile["worldIntegration"],
        "content_policy": profile["contentPolicy"],
        "generation_contract": {
            "long_bespoke_cinematic_required": False,
            "visible_major_presence_pop_in_allowed": False,
            "data_driven_composition": True,
            "story_context_required": True,
            "combat_required_for_every_appearance": False,
            "seed_reproducible_variants": True,
            "coop_authoritative_state": True,
        },
    }


def auto_encounter_profile(goal: str) -> str | None:
    value = goal.casefold()
    if "sanctum" in value:
        return "church_giants"

    place_tokens = ("church", "chapel", "cathedral", "abbey", "monastery")
    horror_tokens = ("zombie", "undead", "horror", "round-based", "round based")
    if any(token in value for token in place_tokens) and any(
        token in value for token in horror_tokens
    ):
        return "church_giants"
    return None
