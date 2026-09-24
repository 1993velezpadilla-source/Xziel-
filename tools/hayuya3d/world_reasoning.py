#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STANDARD_PATH = ROOT / "hayuya" / "standards" / "hayuya_world_reasoning_domains_v1.json"


PRIORITY_HINTS = {
    "architecture": ("building", "house", "church", "interior", "room", "facility"),
    "interiors": ("interior", "room", "office", "house", "church", "hospital"),
    "urbanism": ("city", "street", "urban", "town", "district", "road"),
    "infrastructure": ("power", "generator", "utility", "industrial", "city", "facility"),
    "terrain_and_hydrology": ("terrain", "mountain", "rain", "river", "outdoor", "island"),
    "ecology_and_vegetation": ("forest", "jungle", "vegetation", "plant", "swamp", "outdoor"),
    "materials_and_weathering": ("abandoned", "old", "ruin", "horror", "weathered"),
    "lighting_and_cinematography": ("horror", "cinematic", "night", "thriller", "lighting"),
    "acoustics": ("horror", "audio", "sound", "multiplayer", "interior"),
    "signage_and_wayfinding": ("map", "level", "world", "city", "maze"),
    "accessibility_and_comfort": ("mobile", "android", "game", "playable"),
    "environmental_storytelling": ("story", "narrative", "horror", "campaign", "quest"),
    "ai_navigation": ("enemy", "zombie", "npc", "combat", "multiplayer"),
    "multiplayer_networking": ("multiplayer", "coop", "co-op", "online", "4 players", "four players"),
    "mobile_rendering": ("mobile", "android", "xziel", "performance", "google play"),
    "monetization_and_policy": ("ads", "admob", "sponsor", "monetization", "google play"),
}


def _load() -> dict[str, Any]:
    return json.loads(STANDARD_PATH.read_text(encoding="utf-8"))


def compile_world_reasoning_intelligence(goal: str) -> dict[str, Any]:
    standard = _load()
    value = goal.casefold()
    prioritized = [
        domain
        for domain, needles in PRIORITY_HINTS.items()
        if any(needle in value for needle in needles)
    ]

    # All domains stay available because cross-discipline consistency is the point.
    # "prioritized" only controls reasoning order/cost, never visibility of knowledge.
    return {
        "engine": "HAYUYA World Reasoning Brain",
        "schema": 1,
        "goal": goal,
        "knowledge_scope": "all_domains_available",
        "priority_domains": prioritized,
        "domains": standard["domains"],
        "world_consistency_questions": standard["worldConsistencyQuestions"],
        "truth_policy": standard["truthPolicy"],
        "reasoning_contract": {
            "all_domains_remain_available": True,
            "priority_is_not_exclusion": True,
            "observed_inferred_generated_must_remain_distinct": True,
            "game_world_plausibility_not_professional_certification": True,
            "cross_domain_conflicts_must_be_reported": True,
        },
    }
