#!/usr/bin/env python3
"""Export Nacht's status against the universal XZIEL map content contract.

This adapter intentionally separates runtime progress from payload inventory.
Nacht cannot become strict-ready while final visual/audio/source payload is not
mounted and inventoried, even if gameplay metadata compiles.
"""

from __future__ import annotations

import json
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[2]
UNIVERSAL = ROOT / "assets/map_package/xziel_map_content_contract_v1.json"
NACHT = ROOT / "assets/nacht_reference/bo3_nacht_completion_contract_v1.json"
OUT = Path(os.environ.get(
    "XZIEL_NACHT_PACKAGE_STATUS_OUT",
    ROOT / "assets/nacht_reference/xziel_map_package_status_v1.json",
))

universal = json.loads(UNIVERSAL.read_text(encoding="utf-8"))
nacht = json.loads(NACHT.read_text(encoding="utf-8"))
systems = nacht["requiredSystems"]

MAPPING = {
    "world_geometry": ["map_topology_and_collision", "android_visual_parity"],
    "collision": ["map_topology_and_collision"],
    "navigation_pathing": ["zombie_spawns_pathing_ai"],
    "materials_textures": ["android_visual_parity"],
    "static_models_props": ["android_visual_parity", "all_interactions_zero_dead_prompts"],
    "animated_models_rigs": ["weapon_models_audio_fx_animations"],
    "animations": ["weapon_models_audio_fx_animations"],
    "weapons_equipment": ["wall_buys_and_ammo_refills", "weapon_models_audio_fx_animations"],
    "pack_a_punch_variants": ["pack_a_punch_weapon_variants"],
    "audio_sfx": ["weapon_models_audio_fx_animations"],
    "ambient_music_vo": ["android_visual_parity"],
    "vfx_particles": ["weapon_models_audio_fx_animations", "android_visual_parity"],
    "lighting_postfx": ["android_visual_parity"],
    "gameplay_scripts": [
        "doors_and_zone_unlocks",
        "barricades_repair_points",
        "zombie_spawns_pathing_ai",
        "points_economy_scoring",
    ],
    "interactables": ["all_interactions_zero_dead_prompts"],
    "perks_wunderfizz": ["der_wunderfizz_and_perk_randomization", "mule_kick_and_weapon_slot_semantics"],
    "powerups": ["powerup_drop_pool_and_effects"],
    "gobblegum": ["gobblegum_machines_and_full_effect_runtime"],
    "mystery_box": ["mystery_box_full_pool_and_teddy_flow"],
    "spawns_rounds_ai": ["zombie_spawns_pathing_ai"],
    "hud_ui_prompts": ["android_touch_hud_and_controls", "all_interactions_zero_dead_prompts"],
    "multiplayer_replication": ["multiplayer_1_to_4_gameplay"],
    "platform_packaging": ["android_touch_hud_and_controls", "android_visual_parity", "crash_memory_leak_watch"],
    "soak_release_quality": ["horde_stress_and_round_100_soak", "crash_memory_leak_watch"],
}

# These families necessarily depend on final mounted content rather than metadata
# alone. The current repository intentionally does not commit original BO3 bytes.
PAYLOAD_REQUIRED = {
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
    "hud_ui_prompts",
    "platform_packaging",
}

def combine(states: list[str]) -> str:
    if states and all(s == "ready" for s in states):
        return "ready"
    if any(s == "partial" for s in states):
        return "partial"
    return "pending"

required_ids = [row["id"] for row in universal["requiredFamilies"]]
if set(required_ids) != set(MAPPING):
    raise SystemExit(
        f"Nacht package mapping drift missing={sorted(set(required_ids)-set(MAPPING))} "
        f"extra={sorted(set(MAPPING)-set(required_ids))}"
    )

families = []
for family_id in required_ids:
    source_keys = MAPPING[family_id]
    source_states = []
    for key in source_keys:
        if key not in systems:
            raise SystemExit(f"missing Nacht required system: {key}")
        source_states.append(systems[key]["state"])

    runtime_state = combine(source_states)
    inventory_state = "not_mounted" if family_id in PAYLOAD_REQUIRED else "not_applicable"
    blockers = []
    if runtime_state != "ready":
        blockers.append("runtime_family_not_ready")
    if inventory_state == "not_mounted":
        blockers.append("final_payload_inventory_not_mounted")

    families.append({
        "id": family_id,
        "runtimeState": runtime_state,
        "inventoryState": inventory_state,
        "sourceSystemKeys": source_keys,
        "strictReady": not blockers,
        "blockers": blockers,
    })

summary = {
    "requiredFamilyCount": len(families),
    "runtimeReadyFamilies": sum(f["runtimeState"] == "ready" for f in families),
    "runtimePartialFamilies": sum(f["runtimeState"] == "partial" for f in families),
    "runtimePendingFamilies": sum(f["runtimeState"] == "pending" for f in families),
    "payloadFamiliesNotMounted": sum(f["inventoryState"] == "not_mounted" for f in families),
    "strictReadyFamilies": sum(f["strictReady"] for f in families),
}
summary["strictReady"] = summary["strictReadyFamilies"] == len(families)

out = {
    "schemaVersion": 1,
    "mapId": "bo3_nacht_reference",
    "contractId": universal["contractId"],
    "policy": {
        "zeroOmission": True,
        "noSilentFallbacks": True,
        "thirdPartyPayloadCommittedToRepository": False,
        "payloadExpectation": "mount_user_owned_or_licensed_source_folder_or_zip_then_inventory",
    },
    "summary": summary,
    "families": families,
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
print("XZIEL_NACHT_PACKAGE_STATUS_OK", json.dumps(summary, sort_keys=True))
