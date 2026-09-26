#!/usr/bin/env python3
"""Validate the XZIEL BO3 Nacht full-completion contract.

This is intentionally stricter than the current gameplay harness:
- every weapon in the global catalog must be tracked;
- every required weapon lane must be explicit;
- every required map/system lane must be explicit;
- releaseCandidate=true is forbidden until all required lanes are ready or
  explicitly not_applicable.

The validator does not pretend pending work is complete. It exists to make
silent omissions impossible.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "assets/nacht_reference/bo3_nacht_completion_contract_v1.json"
CATALOG = ROOT / "assets/weapons/xziel_weapon_catalog_v1.json"
BOX = ROOT / "assets/weapons/xziel_mystery_box_pool_v1.json"
RUNTIME = ROOT / "assets/nacht_reference/runtime_reference_v1.json"
BEHAVIOR_SPECS = ROOT / "assets/nacht_reference/bo3_weapon_specs_v1.json"

ALLOWED_STATES = {
    "pending",
    "partial",
    "cataloged",
    "logic_only",
    "ready",
    "not_applicable",
}
COMPLETE_STATES = {"ready", "not_applicable"}

REQUIRED_SYSTEMS = {
    "map_topology_and_collision",
    "doors_and_zone_unlocks",
    "barricades_repair_points",
    "zombie_spawns_pathing_ai",
    "wall_buys_and_ammo_refills",
    "mystery_box_full_pool_and_teddy_flow",
    "gobblegum_machines_and_full_effect_runtime",
    "der_wunderfizz_and_perk_randomization",
    "mule_kick_and_weapon_slot_semantics",
    "powerup_drop_pool_and_effects",
    "pack_a_punch_weapon_variants",
    "points_economy_scoring",
    "all_interactions_zero_dead_prompts",
    "weapon_models_audio_fx_animations",
    "multiplayer_1_to_4_gameplay",
    "android_touch_hud_and_controls",
    "android_visual_parity",
    "horde_stress_and_round_100_soak",
    "crash_memory_leak_watch",
}


def fail(message: str) -> None:
    raise SystemExit(f"NACHT_COMPLETION_CONTRACT_FAIL: {message}")


def load(path: Path):
    if not path.is_file():
        fail(f"missing required file: {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    contract = load(CONTRACT)
    catalog = load(CATALOG)
    box = load(BOX)
    runtime = load(RUNTIME)
    behavior_specs = load(BEHAVIOR_SPECS)

    if contract.get("schemaVersion") != 1:
        fail("schemaVersion must be 1")
    if contract.get("contractId") != "bo3_nacht_android_one_to_one_v1":
        fail("unexpected contractId")
    if not isinstance(contract.get("releaseCandidate"), bool):
        fail("releaseCandidate must be boolean")

    weapons = catalog.get("weapons")
    if not isinstance(weapons, list) or not weapons:
        fail("weapon catalog is empty or invalid")

    catalog_ids = [w.get("weaponId") for w in weapons]
    if any(not isinstance(x, str) or not x for x in catalog_ids):
        fail("catalog contains invalid weaponId")
    if len(catalog_ids) != len(set(catalog_ids)):
        fail("catalog contains duplicate weaponId values")

    tracked = contract.get("weapons")
    if not isinstance(tracked, dict):
        fail("contract weapons must be an object")

    tracked_ids = set(tracked)
    catalog_set = set(catalog_ids)
    missing = sorted(catalog_set - tracked_ids)
    extra = sorted(tracked_ids - catalog_set)
    if missing:
        fail(f"catalog weapons missing from completion contract: {missing}")
    if extra:
        fail(f"completion contract contains unknown weapons: {extra}")

    baseline = contract.get("baseline", {})
    spec_rows = behavior_specs.get("weapons", [])
    if not isinstance(spec_rows, list):
        fail("BO3 behavior specs weapons must be a list")
    spec_ids = [row.get("logicalItemId") for row in spec_rows]
    if any(not isinstance(x, str) or not x for x in spec_ids):
        fail("BO3 behavior specs contains invalid logicalItemId")
    if len(spec_ids) != len(set(spec_ids)):
        fail("BO3 behavior specs contains duplicate logicalItemId values")
    if not set(spec_ids).issubset(catalog_set):
        fail(f"BO3 behavior specs contains unknown catalog IDs: {sorted(set(spec_ids)-catalog_set)}")
    if baseline.get("bo3StructuredBehaviorSpecCount") != len(spec_rows):
        fail(
            f"bo3StructuredBehaviorSpecCount={baseline.get('bo3StructuredBehaviorSpecCount')} "
            f"does not match behavior specs={len(spec_rows)}"
        )

    if baseline.get("catalogWeaponCount") != len(weapons):
        fail(
            f"catalogWeaponCount={baseline.get('catalogWeaponCount')} "
            f"does not match catalog={len(weapons)}"
        )

    required_lanes = contract.get("requiredWeaponLanes")
    if not isinstance(required_lanes, list) or not required_lanes:
        fail("requiredWeaponLanes must be a non-empty list")
    if len(required_lanes) != len(set(required_lanes)):
        fail("requiredWeaponLanes contains duplicates")
    required_lane_set = set(required_lanes)

    for weapon in weapons:
        wid = weapon["weaponId"]
        row = tracked[wid]
        if row.get("displayName") != weapon.get("displayName"):
            fail(f"displayName drift for {wid}")

        lanes = row.get("lanes")
        if not isinstance(lanes, dict):
            fail(f"missing lanes object for {wid}")

        lane_keys = set(lanes)
        missing_lanes = sorted(required_lane_set - lane_keys)
        extra_lanes = sorted(lane_keys - required_lane_set)
        if missing_lanes:
            fail(f"{wid} missing lanes: {missing_lanes}")
        if extra_lanes:
            fail(f"{wid} has unknown lanes: {extra_lanes}")

        for lane, state in lanes.items():
            if state not in ALLOWED_STATES:
                fail(f"{wid}.{lane} has invalid state {state!r}")

        expected_behavior_state = "cataloged" if wid in set(spec_ids) else "pending"
        if lanes["behavior_spec"] != expected_behavior_state:
            fail(
                f"{wid}.behavior_spec={lanes['behavior_spec']!r} "
                f"but expected {expected_behavior_state!r} from structured spec coverage"
            )

        if weapon.get("mysteryBoxEligible") and lanes["mystery_box"] == "not_applicable":
            fail(f"{wid} is Mystery Box eligible but marked not_applicable")
        if weapon.get("nachtWallBuyId") and lanes["wall_buy"] == "not_applicable":
            fail(f"{wid} has a Nacht wall-buy id but wall_buy is not_applicable")

        catalog_native = weapon.get("nativeBindingStatus")
        contract_native = row.get("catalogNativeStatus")
        if catalog_native != contract_native:
            fail(
                f"{wid} native status drift: catalog={catalog_native!r} "
                f"contract={contract_native!r}"
            )

    pool_ids = box.get("weaponIds")
    if not isinstance(pool_ids, list):
        fail("global mystery box pool weaponIds must be a list")
    expected_box_ids = [w["weaponId"] for w in weapons if w.get("mysteryBoxEligible")]
    if set(pool_ids) != set(expected_box_ids):
        fail("Mystery Box pool no longer matches catalog eligibility")
    if len(pool_ids) != len(set(pool_ids)):
        fail("Mystery Box pool contains duplicate weapons")

    if baseline.get("runtimePurchases") != len(runtime.get("purchases", [])):
        fail("runtime purchase count drift")
    if baseline.get("doors") != len(runtime.get("doors", [])):
        fail("door count drift")
    if baseline.get("barricades") != len(runtime.get("barricades", [])):
        fail("barricade count drift")
    if baseline.get("zombieSpawns") != len(runtime.get("zombieSpawns", [])):
        fail("zombie spawn count drift")
    if baseline.get("playerSpawns") != len(runtime.get("playerSpawns", [])):
        fail("player spawn count drift")
    if baseline.get("maxPlayers") != runtime.get("runtimePolicy", {}).get("maximumPlayers"):
        fail("maximumPlayers drift")
    if baseline.get("roundSoakTarget") != 100:
        fail("roundSoakTarget must remain 100 for the engine acceptance target")

    systems = contract.get("requiredSystems")
    if not isinstance(systems, dict):
        fail("requiredSystems must be an object")
    if set(systems) != REQUIRED_SYSTEMS:
        missing_systems = sorted(REQUIRED_SYSTEMS - set(systems))
        extra_systems = sorted(set(systems) - REQUIRED_SYSTEMS)
        fail(
            f"requiredSystems mismatch missing={missing_systems} extra={extra_systems}"
        )
    for sid, row in systems.items():
        state = row.get("state") if isinstance(row, dict) else None
        if state not in ALLOWED_STATES:
            fail(f"system {sid} has invalid state {state!r}")

    feature_ref = contract.get("bo3ChroniclesFeatureReference", {})
    if feature_ref.get("mysteryBox") is not True:
        fail("BO3 Nacht must track the Mystery Box")
    if feature_ref.get("gobbleGumMachines") != 2:
        fail("BO3 Nacht contract must track both GobbleGum machines")
    if feature_ref.get("derWunderfizz") is not True:
        fail("BO3 Nacht contract must track Der Wunderfizz")
    if feature_ref.get("muleKick") is not True:
        fail("BO3 Nacht contract must track Mule Kick")
    if feature_ref.get("packAPunchMachinePresent") is not False:
        fail("Nacht must not invent a physical Pack-a-Punch machine")
    if feature_ref.get("packAPunchWeaponVariantsStillRequired") is not True:
        fail("Pack-a-Punch weapon variants must remain tracked")

    if contract["releaseCandidate"]:
        incomplete = []
        for sid, row in systems.items():
            if row["state"] not in COMPLETE_STATES:
                incomplete.append(f"system:{sid}={row['state']}")
        for wid, row in tracked.items():
            for lane, state in row["lanes"].items():
                if state not in COMPLETE_STATES:
                    incomplete.append(f"weapon:{wid}:{lane}={state}")
        if incomplete:
            preview = ", ".join(incomplete[:25])
            suffix = "" if len(incomplete) <= 25 else f" ... +{len(incomplete)-25} more"
            fail(
                "releaseCandidate=true while incomplete work remains: "
                + preview
                + suffix
            )

    states = {}
    for row in tracked.values():
        for state in row["lanes"].values():
            states[state] = states.get(state, 0) + 1

    system_states = {}
    for row in systems.values():
        state = row["state"]
        system_states[state] = system_states.get(state, 0) + 1

    print(
        "NACHT_COMPLETION_CONTRACT_OK",
        {
            "weapons": len(weapons),
            "box": len(pool_ids),
            "weaponLaneStates": states,
            "systemStates": system_states,
            "releaseCandidate": contract["releaseCandidate"],
        },
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
