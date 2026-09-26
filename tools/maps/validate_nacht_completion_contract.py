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
GOBBLEGUM_CATALOG = ROOT / "assets/nacht_reference/bo3_gobblegum_catalog_v1.json"
SYSTEM_PLACEMENTS = ROOT / "assets/nacht_reference/bo3_system_placements_v1.json"
PERK_CATALOG = ROOT / "assets/nacht_reference/bo3_perk_catalog_v1.json"
POWERUP_CATALOG = ROOT / "assets/nacht_reference/bo3_powerup_catalog_v1.json"
WEAPON_ID_REGISTRY = ROOT / "assets/weapons/xziel_weapon_id_registry_v1.json"
RUNTIME_BOX_POOL = ROOT / "assets/weapons/xziel_mystery_box_runtime_pool_v1.json"
RUNTIME_CAPABILITIES = ROOT / "assets/nacht_reference/xziel_zombies_runtime_capabilities_v1.json"

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
    gobblegum_catalog = load(GOBBLEGUM_CATALOG)
    system_placements = load(SYSTEM_PLACEMENTS)
    perk_catalog = load(PERK_CATALOG)
    powerup_catalog = load(POWERUP_CATALOG)
    weapon_id_registry = load(WEAPON_ID_REGISTRY)
    runtime_box_pool = load(RUNTIME_BOX_POOL)
    runtime_capabilities = load(RUNTIME_CAPABILITIES)

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

    gum_entries = gobblegum_catalog.get("entries", [])
    if not isinstance(gum_entries, list):
        fail("GobbleGum catalog entries must be a list")
    gum_ids = [row.get("id") for row in gum_entries]
    if len(gum_entries) != 63 or len(gum_ids) != len(set(gum_ids)):
        fail("GobbleGum identity catalog must contain exactly 63 unique entries")
    if baseline.get("gobbleGumIdentityCount") != len(gum_entries):
        fail("gobbleGumIdentityCount drift")

    placement_rows = system_placements.get("entities", [])
    if not isinstance(placement_rows, list):
        fail("system placements entities must be a list")
    type_counts = {}
    for row in placement_rows:
        t = row.get("type")
        type_counts[t] = type_counts.get(t, 0) + 1
    if type_counts.get("gobblegum_machine", 0) != baseline.get("gobbleGumMachinePlacements"):
        fail("GobbleGum machine placement count drift")
    if type_counts.get("der_wunderfizz", 0) != baseline.get("wunderfizzMachinePlacements"):
        fail("Wunderfizz placement count drift")
    if type_counts.get("mystery_box", 0) != baseline.get("mysteryBoxAnchors"):
        fail("Mystery Box anchor count drift")

    perk_entries = perk_catalog.get("entries", [])
    if not isinstance(perk_entries, list):
        fail("perk catalog entries must be a list")
    perk_ids = [row.get("id") for row in perk_entries]
    if len(perk_entries) != 8 or len(perk_ids) != len(set(perk_ids)):
        fail("BO3 Nacht perk catalog must contain exactly 8 unique identities")
    if baseline.get("canonicalPerkIdentityCount") != len(perk_entries):
        fail("canonicalPerkIdentityCount drift")
    wf_pool = [row for row in perk_entries if row.get("wunderfizzEligible") is True]
    if len(wf_pool) != 7 or baseline.get("wunderfizzPoolIdentityCount") != len(wf_pool):
        fail("Wunderfizz perk pool identity count drift")

    power_entries = powerup_catalog.get("entries", [])
    if not isinstance(power_entries, list):
        fail("power-up catalog entries must be a list")
    power_ids = [row.get("id") for row in power_entries]
    if len(power_entries) != 9 or len(power_ids) != len(set(power_ids)):
        fail("BO3 core power-up catalog must contain exactly 9 unique identities")
    if baseline.get("corePowerupIdentityCount") != len(power_entries):
        fail("corePowerupIdentityCount drift")
    natural_power = [row for row in power_entries if row.get("nachtNaturalDrop") is True]
    if len(natural_power) != 6 or baseline.get("nachtNaturalPowerupIdentityCount") != len(natural_power):
        fail("Nacht natural power-up identity count drift")

    capability_perks = runtime_capabilities.get("perks", [])
    capability_powerups = runtime_capabilities.get("powerups", [])
    if len(capability_perks) != len(perk_entries):
        fail("runtime perk capability coverage drift")
    if len(capability_powerups) != len(power_entries):
        fail("runtime power-up capability coverage drift")

    reusable_perks = [row for row in capability_perks if row.get("primitiveAvailable") is True]
    reusable_powerups = [row for row in capability_powerups if row.get("primitiveAvailable") is True]
    missing_perks = sorted(row["id"] for row in capability_perks if row.get("primitiveAvailable") is not True)
    missing_powerups = sorted(row["id"] for row in capability_powerups if row.get("primitiveAvailable") is not True)

    if len(reusable_perks) != 7 or baseline.get("reusablePerkPrimitiveCount") != 7:
        fail("reusable perk primitive count drift")
    if len(reusable_powerups) != 7 or baseline.get("reusablePowerupPrimitiveCount") != 7:
        fail("reusable power-up primitive count drift")
    if missing_perks != ["widows_wine"]:
        fail(f"unexpected missing perk primitives: {missing_perks}")
    if missing_powerups != ["death_machine", "fire_sale"]:
        fail(f"unexpected missing power-up primitives: {missing_powerups}")

    perk_cap_by_id = {row["id"]: row for row in capability_perks}
    for row in perk_entries:
        primitive = row.get("runtimePrimitive", {})
        expected = perk_cap_by_id[row["id"]].get("primitiveAvailable") is True
        if primitive.get("available") is not expected:
            fail(f"perk runtime primitive drift for {row['id']}")

    power_cap_by_id = {row["id"]: row for row in capability_powerups}
    for row in power_entries:
        primitive = row.get("runtimePrimitive", {})
        expected = power_cap_by_id[row["id"]].get("primitiveAvailable") is True
        if primitive.get("available") is not expected:
            fail(f"power-up runtime primitive drift for {row['id']}")

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

        if wid in set(spec_ids):
            if lanes["behavior_spec"] not in {"cataloged", "ready"}:
                fail(
                    f"{wid}.behavior_spec={lanes['behavior_spec']!r} "
                    "but a structured BO3 behavior spec exists"
                )
        elif lanes["behavior_spec"] != "pending":
            fail(
                f"{wid}.behavior_spec={lanes['behavior_spec']!r} "
                "but no structured BO3 behavior spec exists"
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

    registry_entries = weapon_id_registry.get("entries", [])
    if not isinstance(registry_entries, list):
        fail("weapon ID registry entries must be a list")
    registry_ids = [row.get("weaponId") for row in registry_entries]
    quakec_ids = [row.get("quakecId") for row in registry_entries]
    mbox_tokens = [row.get("mboxToken") for row in registry_entries]
    if set(registry_ids) != catalog_set:
        fail("weapon ID registry must cover the complete weapon catalog")
    if len(quakec_ids) != len(set(quakec_ids)):
        fail("weapon ID registry contains duplicate QuakeC IDs")
    if len(mbox_tokens) != len(set(mbox_tokens)):
        fail("weapon ID registry contains duplicate Mystery Box tokens")
    registry_by_id = {row["weaponId"]: row for row in registry_entries}
    if registry_by_id.get("pistol_burst", {}).get("quakecId") != 70:
        fail("RK5 stable QuakeC ID must remain pinned to 70")
    if baseline.get("weaponIdRegistryCount") != len(registry_entries):
        fail("weaponIdRegistryCount drift")

    if runtime_box_pool.get("candidateCount") != len(pool_ids):
        fail("runtime Mystery Box candidateCount drift")
    if baseline.get("mysteryBoxCandidateCount") != len(pool_ids):
        fail("mysteryBoxCandidateCount baseline drift")
    capacity = baseline.get("mysteryBoxRuntimeCapacity")
    if not isinstance(capacity, int) or capacity < len(pool_ids) or capacity != 64:
        fail(f"invalid Mystery Box runtime capacity: {capacity!r}")

    active_rows = runtime_box_pool.get("active", [])
    blocked_rows = runtime_box_pool.get("blocked", [])
    if not isinstance(active_rows, list) or not isinstance(blocked_rows, list):
        fail("runtime Mystery Box active/blocked rows must be lists")
    active_ids = [row.get("weaponId") for row in active_rows]
    blocked_ids = [row.get("weaponId") for row in blocked_rows]
    if set(active_ids) & set(blocked_ids):
        fail("runtime Mystery Box weapon cannot be both active and blocked")
    if set(active_ids) | set(blocked_ids) != set(pool_ids):
        fail("runtime Mystery Box active+blocked coverage must equal identity pool")
    if runtime_box_pool.get("activeCount") != len(active_rows):
        fail("runtime Mystery Box activeCount drift")
    if runtime_box_pool.get("blockedCount") != len(blocked_rows):
        fail("runtime Mystery Box blockedCount drift")

    runtime_required_lanes = runtime_box_pool.get("requiredLanes", [])
    if not isinstance(runtime_required_lanes, list) or not runtime_required_lanes:
        fail("runtime Mystery Box requiredLanes must be a non-empty list")

    catalog_by_id = {w["weaponId"]: w for w in weapons}
    expected_active_ids = []
    for wid in pool_ids:
        weapon = catalog_by_id[wid]
        lane_states = tracked[wid]["lanes"]
        native_ready = weapon.get("nativeBindingStatus") == "ready"
        lanes_ready = all(
            lane_states.get(lane) in COMPLETE_STATES
            for lane in runtime_required_lanes
        )
        if native_ready and lanes_ready:
            expected_active_ids.append(wid)

    if active_ids != expected_active_ids:
        fail(
            "runtime Mystery Box active list does not match readiness gates: "
            f"expected={expected_active_ids} actual={active_ids}"
        )

    mystery_system = contract.get("requiredSystems", {}).get(
        "mystery_box_full_pool_and_teddy_flow", {}
    )
    if mystery_system.get("runtimeCapacity") != capacity:
        fail("Mystery Box system runtimeCapacity drift")
    if mystery_system.get("candidateWeaponIdentities") != len(pool_ids):
        fail("Mystery Box system candidate count drift")
    if mystery_system.get("runtimeReadyRewards") != len(active_ids):
        fail("Mystery Box system active reward count drift")

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
            "runtimeBoxActive": len(active_ids),
            "weaponIdRegistry": len(registry_entries),
            "weaponLaneStates": states,
            "systemStates": system_states,
            "releaseCandidate": contract["releaseCandidate"],
        },
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
