#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STANDARD_PATH = ROOT / "hayuya" / "standards" / "hayuya_universal_game_design_brain_v1.json"
AI_ATLAS_PATH = ROOT / "hayuya" / "knowledge" / "world_generation_ai_atlas_v1.json"


DOMAIN_HINTS = {
    "navigation": ("map", "level", "world", "route", "explore", "exploration"),
    "combat": ("combat", "shooter", "fps", "enemy", "boss", "zombie", "arena"),
    "stealth": ("stealth", "sneak", "guard", "infiltration", "assassin"),
    "survival_horror": ("horror", "survival", "zombie", "undead", "scary", "thriller"),
    "roguelike": ("roguelike", "roguelite", "procedural run", "runs"),
    "metroidvania": ("metroidvania", "ability gate", "backtrack"),
    "puzzle": ("puzzle", "riddle", "logic", "escape room"),
    "platforming": ("platformer", "platforming", "jump", "parkour"),
    "racing": ("racing", "race", "racetrack", "drift", "vehicle course"),
    "open_world": ("open world", "city", "large world", "region", "district"),
    "extraction": ("extraction", "extract", "loot run"),
    "tactical": ("tactical", "breach", "room clearing", "swat"),
    "arena_pvp": ("pvp", "deathmatch", "arena shooter", "competitive multiplayer"),
    "coop": ("co-op", "coop", "cooperative", "multiplayer", "four players", "4 players"),
    "social_sandbox": ("social", "sandbox", "hangout", "creator"),
    "narrative": ("story", "narrative", "campaign", "cinematic", "quest"),
    "immersive_sim": ("immersive sim", "systemic", "multiple solutions", "simulation"),
    "technical": ("mobile", "android", "streaming", "performance", "xziel", "optimization"),
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def infer_domains(goal: str) -> list[str]:
    value = goal.casefold()
    hits: list[str] = []
    for domain, needles in DOMAIN_HINTS.items():
        if any(needle in value for needle in needles):
            hits.append(domain)

    # A game-space plan always needs navigation + technical sanity even when the
    # user's creative description does not name those concerns explicitly.
    for required in ("navigation", "technical"):
        if required not in hits:
            hits.append(required)
    return hits


def compile_universal_design_intelligence(
    goal: str,
    *,
    domains: Iterable[str] | None = None,
    custom_constraints: Iterable[str] | None = None,
) -> dict[str, Any]:
    standard = _read_json(STANDARD_PATH)
    atlas = _read_json(AI_ATLAS_PATH)

    selected = list(dict.fromkeys(domains or infer_domains(goal)))
    unknown = [domain for domain in selected if domain not in standard["designDomains"]]
    if unknown:
        raise ValueError(
            "unknown universal design domains: " + ", ".join(sorted(unknown))
        )

    return {
        "engine": "HAYUYA Universal Game Design Brain",
        "schema": 1,
        "goal": goal,
        "selected_domains": selected,
        "domain_patterns": {
            domain: standard["designDomains"][domain]
            for domain in selected
        },
        "custom_constraints": [
            value.strip()
            for value in (custom_constraints or ())
            if value.strip()
        ],
        "principles": standard["principles"],
        "cross_genre_reasoning": standard["crossGenreReasoning"],
        "required_passes": standard["requiredPasses"],
        "solver_agents": standard["solverAgents"],
        "judge_gates": standard["judgeGates"],
        "clean_room_guardrails": standard["cleanRoomGuardrails"],
        "ai_world_research": {
            "atlas": str(AI_ATLAS_PATH.relative_to(ROOT)),
            "system_count": len(atlas["systems"]),
            "architecture_lessons": atlas["crossSystemArchitectureLessons"],
        },
        "generation_contract": {
            "domain_library_is_not_ontology": True,
            "freeform_gameplay_constraints_allowed": True,
            "generate_multiple_layout_hypotheses": True,
            "solve_before_expensive_art": True,
            "human_editable_intent_required": True,
            "original_geometry_required": True,
        },
    }
