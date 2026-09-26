#!/usr/bin/env python3
"""Validate the universal XZIEL zero-omission map content contract."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "assets/map_package/xziel_map_content_contract_v1.json"

EXPECTED_FAMILIES = {
    "world_geometry",
    "collision",
    "navigation_pathing",
    "materials_textures",
    "static_models_props",
    "animated_models_rigs",
    "animations",
    "weapons_equipment",
    "pack_a_punch_variants",
    "audio_sfx",
    "ambient_music_vo",
    "vfx_particles",
    "lighting_postfx",
    "gameplay_scripts",
    "interactables",
    "perks_wunderfizz",
    "powerups",
    "gobblegum",
    "mystery_box",
    "spawns_rounds_ai",
    "hud_ui_prompts",
    "multiplayer_replication",
    "platform_packaging",
    "soak_release_quality",
}

def fail(msg: str) -> None:
    raise SystemExit(f"XZIEL_MAP_CONTENT_CONTRACT_FAIL: {msg}")

def main() -> int:
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    if data.get("schemaVersion") != 1:
        fail("schemaVersion drift")
    if data.get("contractId") != "xziel_map_content_contract_v1":
        fail("contractId drift")
    if data.get("completionRule") != (
        "all_required_families_ready_and_inventory_strictReady_and_runtime_validation_green"
    ):
        fail("completionRule drift")

    rows = data.get("requiredFamilies")
    if not isinstance(rows, list):
        fail("requiredFamilies must be a list")

    ids = [row.get("id") for row in rows]
    if len(ids) != len(set(ids)):
        fail("duplicate required family id")
    if set(ids) != EXPECTED_FAMILIES:
        missing = sorted(EXPECTED_FAMILIES - set(ids))
        extra = sorted(set(ids) - EXPECTED_FAMILIES)
        fail(f"family coverage drift missing={missing} extra={extra}")

    for row in rows:
        if row.get("required") is not True:
            fail(f"{row.get('id')} must remain required")
        if not row.get("scope"):
            fail(f"{row.get('id')} scope missing")
        if not row.get("readyRequires"):
            fail(f"{row.get('id')} readyRequires missing")

    policy = data.get("packagePolicy", {})
    for key in (
        "preserveSourceBytes",
        "deterministicInventory",
        "rejectUnsafeZipPaths",
        "rejectZeroByteFiles",
        "rejectCasePathCollisions",
        "rejectUnresolvedAssetReferences",
        "rejectAmbiguousAssetReferences",
        "noSilentFallbacks",
        "noUnrelatedAssetSubstitution",
    ):
        if policy.get(key) is not True:
            fail(f"packagePolicy.{key} must remain true")

    if sorted(policy.get("acceptedInputs", [])) != ["folder", "zip"]:
        fail("acceptedInputs must be folder + zip")
    if policy.get("contentHash") != "sha256":
        fail("contentHash must remain sha256")

    print(
        "XZIEL_MAP_CONTENT_CONTRACT_OK",
        {"requiredFamilies": len(rows), "acceptedInputs": policy["acceptedInputs"]},
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
