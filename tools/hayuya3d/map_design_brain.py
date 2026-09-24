#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STANDARD_PATH = ROOT / "hayuya" / "standards" / "hayuya_map_design_brain_v1.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_repo_path(value: str) -> Path:
    return ROOT / value


def compile_design_intelligence(profile_id: str = "sanctum_classic") -> dict[str, Any]:
    standard = _read_json(STANDARD_PATH)
    knowledge = standard["knowledge"]
    profiles = knowledge["profiles"]
    if profile_id not in profiles:
        raise ValueError(
            f"unknown HAYUYA Map design profile {profile_id!r}; "
            f"available: {', '.join(sorted(profiles))}"
        )

    atlas_path = _resolve_repo_path(knowledge["atlas"])
    coverage_path = _resolve_repo_path(knowledge["coverage"])
    profile_path = _resolve_repo_path(profiles[profile_id])

    atlas = _read_json(atlas_path)
    coverage = _read_json(coverage_path)
    profile = _read_json(profile_path)

    atlas_by_id = {record["id"]: record for record in atlas["maps"]}
    source_ids = list(profile["sourceMaps"])
    missing = [map_id for map_id in source_ids if map_id not in atlas_by_id]
    if missing:
        raise ValueError("design profile references missing atlas ids: " + ", ".join(missing))

    required_ids = {
        map_id
        for group in coverage["groups"]
        for map_id in group["ids"]
    }
    coverage_missing = sorted(required_ids - set(atlas_by_id))
    if coverage_missing:
        raise ValueError(
            "zombies design atlas does not satisfy coverage contract: "
            + ", ".join(coverage_missing)
        )

    source_maps = [
        {
            "id": record["id"],
            "game": record["game"],
            "title": record["title"],
            "year": record["year"],
            "classification": record["classification"],
        }
        for record in (atlas_by_id[map_id] for map_id in source_ids)
    ]

    return {
        "engine": "HAYUYA Map Structure Brain",
        "schema": 1,
        "profile_id": profile_id,
        "knowledge": {
            "atlas": knowledge["atlas"],
            "coverage": knowledge["coverage"],
            "profile": profiles[profile_id],
            "atlas_map_count": len(atlas["maps"]),
            "coverage_required_count": len(required_ids),
        },
        "source_maps": source_maps,
        "constraints": profile["constraints"],
        "targets": profile.get("xzielTargets", {}),
        "required_reasoning_passes": standard["requiredReasoningPasses"],
        "world_judge_gates": standard["worldJudgeGates"],
        "transferable_lessons": profile["transferableLessons"],
        "principles": standard["principles"],
        "guardrails": list(dict.fromkeys(
            standard["guardrails"] + profile.get("guardrails", [])
        )),
        "generation_contract": {
            "copy_reference_layout": False,
            "copy_reference_assets": False,
            "copy_reference_scripts": False,
            "derive_abstract_design_principles": True,
            "author_original_geometry": True,
            "author_original_gameplay_graph": True,
        },
    }


def auto_design_profile(goal: str) -> str | None:
    value = goal.casefold()
    triggers = (
        "zombie",
        "undead",
        "round-based",
        "round based",
        "sanctum",
        "horror survival",
    )
    if any(token in value for token in triggers):
        return "sanctum_classic"
    return None
