#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STANDARD_PATH = ROOT / "hayuya" / "standards" / "hayuya_monetization_brain_v1.json"


def _read_standard() -> dict[str, Any]:
    return json.loads(STANDARD_PATH.read_text(encoding="utf-8"))


def _entity_tags(entity: dict[str, Any]) -> set[str]:
    tags: set[str] = set()
    for key in ("labels", "aliases", "capabilities"):
        for value in entity.get(key, []) or []:
            tags.add(str(value).casefold())

    props = entity.get("properties", {}) or {}
    for key, value in props.items():
        if isinstance(value, bool) and value:
            tags.add(str(key).casefold())
        elif isinstance(value, str):
            tags.add(str(value).casefold())
    return tags


def _is_excluded(entity: dict[str, Any], hard_exclusions: set[str]) -> bool:
    tags = _entity_tags(entity)
    if tags & hard_exclusions:
        return True
    props = entity.get("properties", {}) or {}
    if props.get("advertising_forbidden") is True:
        return True
    if props.get("gameplay_critical") is True:
        return True
    if props.get("navigation_critical") is True:
        return True
    if props.get("narrative_critical") is True:
        return True
    return False


def discover_diegetic_candidates(world_graph: dict[str, Any]) -> list[dict[str, Any]]:
    standard = _read_standard()
    capability_map = standard["diegeticCandidateCapabilities"]
    hard_exclusions = {value.casefold() for value in standard["hardExclusions"]}
    candidates: list[dict[str, Any]] = []

    for entity_id, entity in (world_graph.get("entities", {}) or {}).items():
        if _is_excluded(entity, hard_exclusions):
            continue

        capabilities = {str(value) for value in entity.get("capabilities", []) or []}
        accepted_formats: list[str] = []
        matched_capabilities: list[str] = []
        for capability, formats in capability_map.items():
            if capability in capabilities:
                matched_capabilities.append(capability)
                accepted_formats.extend(formats)

        accepted_formats = list(dict.fromkeys(accepted_formats))
        if not accepted_formats:
            continue

        candidates.append(
            {
                "slot_id": f"auto-{entity_id}",
                "entity_id": entity_id,
                "status": "semantic_candidate_geometry_fit_pending",
                "delivery_path": "DIRECT_DIEGETIC_SPONSOR",
                "accepted_formats": accepted_formats,
                "matched_capabilities": matched_capabilities,
                "gameplay_required": False,
                "network_required": False,
                "clickable": False,
                "fallback_required": True,
                "fallback": f"lore/auto/{entity_id}",
                "requires": [
                    "geometry_fit",
                    "player_route_capture",
                    "gameplay_obstruction_gate",
                    "navigation_confusion_gate",
                    "content_rating_gate",
                    "creative_validation",
                ],
            }
        )

    return candidates


def compile_monetization_intelligence(
    world_graph: dict[str, Any],
    *,
    enabled: bool = True,
) -> dict[str, Any]:
    standard = _read_standard()
    candidates = discover_diegetic_candidates(world_graph) if enabled else []

    return {
        "engine": "HAYUYA Monetization Brain",
        "schema": 1,
        "enabled": bool(enabled),
        "policy": {
            "gameplay_required": False,
            "network_required": False,
            "ads_disabled_path_required": True,
            "programmatic_world_space_texture_baking": False,
            "direct_diegetic_and_google_programmatic_are_separate": True,
        },
        "delivery_paths": standard["deliveryPaths"],
        "runtime_hooks": standard["runtimeHooks"],
        "frequency_defaults": standard["frequencyDefaults"],
        "hard_exclusions": standard["hardExclusions"],
        "auto_placement_scoring": standard["autoPlacementScoring"],
        "google_notes": standard["googleNotes"],
        "compatibility": standard["compatibility"],
        "diegetic_candidates": candidates,
        "candidate_count": len(candidates),
        "next_passes": [
            "wait_for_world_graph_semantic_entities",
            "discover_noncritical_brandable_hosts",
            "geometry_fit_candidates",
            "capture_actual_player_route_visibility",
            "reject_gameplay_or_navigation_conflicts",
            "bind_lore_fallbacks",
            "validate_provider_specific_format_contract",
            "emit_xziel_diegetic_slot_manifest",
        ],
    }
