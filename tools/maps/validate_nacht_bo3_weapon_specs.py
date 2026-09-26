#!/usr/bin/env python3
"""Validate clean-room BO3 Nacht wall-weapon behavior specs against runtime truth."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT_REFERENCE = Path("assets/nacht_reference/runtime_reference_v1.json")
DEFAULT_SPECS = Path("assets/nacht_reference/bo3_weapon_specs_v1.json")

ALLOWED_REFILL_AUTHORITIES = {
    "direct_nacht_reference",
    "direct_bo3_wall_reference",
    "derived_half_wall_cost_policy",
}


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE)
    ap.add_argument("--specs", type=Path, default=DEFAULT_SPECS)
    args = ap.parse_args()

    ref = json.loads(args.reference.read_text(encoding="utf-8"))
    specs = json.loads(args.specs.read_text(encoding="utf-8"))

    if specs.get("schemaVersion") != 1:
        fail("weapon spec schemaVersion must be 1")
    if specs.get("scope") != "clean_room_behavior_reference_only":
        fail("weapon specs must remain clean-room behavior reference only")
    if specs.get("assetPolicy", {}).get("rawProprietaryAssetsAllowed") is not False:
        fail("raw proprietary assets must remain prohibited")

    blocked = {
        p["logicalItemId"]: p
        for p in ref["purchases"]
        if p["logicalItemId"] != "frag_grenade"
    }
    weapons = specs.get("weapons", [])
    by_id = {w["logicalItemId"]: w for w in weapons}

    if len(weapons) != 8 or len(by_id) != 8:
        fail(f"expected 8 unique BO3 firearm specs, got {len(weapons)} / {len(by_id)}")
    if set(by_id) != set(blocked):
        fail(f"weapon spec logical IDs do not match blocked Nacht purchases: {set(by_id)} != {set(blocked)}")

    seen_specs: set[str] = set()
    direct_refills = 0
    derived_refills = 0

    for logical_id, spec in by_id.items():
        purchase = blocked[logical_id]

        spec_id = spec.get("specId", "")
        if not spec_id or spec_id in seen_specs:
            fail(f"missing/duplicate specId for {logical_id}: {spec_id!r}")
        seen_specs.add(spec_id)

        if spec.get("displayName") != purchase["displayName"]:
            fail(f"display name mismatch for {logical_id}")
        if spec.get("wallCost") != purchase["cost"]:
            fail(f"wall cost mismatch for {logical_id}")

        readiness = spec.get("readiness", {})
        if readiness != {
            "behaviorSpec": "ready",
            "nativeImplementation": "pending",
            "art": "pending",
            "audio": "pending",
        }:
            fail(f"unsafe/incorrect readiness for {logical_id}: {readiness}")

        fire = spec.get("fire", {})
        if not fire.get("mode"):
            fail(f"missing fire mode for {logical_id}")
        rates = [
            fire.get("rateRpm"),
            fire.get("rateRpmPerBurst"),
            fire.get("rateRpmOverall"),
        ]
        if not any(isinstance(v, (int, float)) and v > 0 for v in rates):
            fail(f"missing positive fire rate for {logical_id}")

        damage = spec.get("damage", {})
        if not damage.get("model"):
            fail(f"missing damage model for {logical_id}")
        falloff = spec.get("damageFalloff", {})
        if falloff.get("status") != "pending_verified_zombies_distance_curve":
            fail(f"unexpected falloff readiness for {logical_id}: {falloff}")
        if falloff.get("implementationAllowed") is not False:
            fail(f"native falloff implementation must remain blocked for {logical_id}")
        numeric_damage = [
            damage.get("base"),
            damage.get("max"),
            damage.get("min"),
        ]
        if not any(isinstance(v, (int, float)) and v > 0 for v in numeric_damage):
            fail(f"missing positive damage for {logical_id}")

        ammo = spec.get("ammo", {})
        if not isinstance(ammo.get("magazine"), int) or ammo["magazine"] <= 0:
            fail(f"invalid magazine for {logical_id}")
        if not isinstance(ammo.get("reserve"), int) or ammo["reserve"] < 0:
            fail(f"invalid reserve for {logical_id}")

        refill = ammo.get("wallRefillCost")
        authority = ammo.get("wallRefillCostAuthority")
        if authority not in ALLOWED_REFILL_AUTHORITIES:
            fail(f"unknown wall refill authority for {logical_id}: {authority}")
        if not isinstance(refill, int) or refill <= 0:
            fail(f"invalid wall refill cost for {logical_id}")
        if authority == "derived_half_wall_cost_policy":
            if refill * 2 != spec["wallCost"]:
                fail(f"derived refill must be exactly half wall cost for {logical_id}")
            derived_refills += 1
        else:
            direct_refills += 1

        source_authority = spec.get("sourceAuthority", {})
        if not source_authority:
            fail(f"missing source authority for {logical_id}")
        for key, value in source_authority.items():
            if key == "wallPlacementAndCost":
                if value != "assets/nacht_reference/runtime_reference_v1.json":
                    fail(f"unexpected internal placement authority for {logical_id}")
            elif not isinstance(value, str) or not value.startswith("https://"):
                fail(f"external source must be an https URL for {logical_id}:{key}")

    # Semantic weapon-shape guards: these prevent accidental flattening while
    # the native weapon implementation is still pending.
    if by_id["pistol_burst"]["fire"].get("burstSize") != 3:
        fail("RK5 must remain a 3-round burst")
    if by_id["smg_burst"]["fire"].get("burstSize") != 4:
        fail("Pharo must remain a 4-round auto-burst")
    if by_id["shotgun_precision"]["damage"].get("model") != "single_slug_range":
        fail("Argus Zombies behavior must remain single-slug")
    if by_id["shotgun_precision"]["damage"].get("projectilesPerShot") != 1:
        fail("Argus must emit one slug per shot")
    if by_id["shotgun_pump"]["damage"].get("model") != "pellet_range":
        fail("KRM-262 must remain pellet-based")
    if by_id["shotgun_pump"]["damage"].get("projectilesPerShot") != 4:
        fail("KRM-262 Zombies behavior must retain four projectiles")
    if by_id["sniper_fastbolt"]["ammo"].get("wallRefillCost") != 2500:
        fail("Locus Nacht cabinet ammo cost must remain 2500")

    expected = specs.get("validation", {})
    if expected.get("expectedWeaponCount") != 8:
        fail("validation.expectedWeaponCount must be 8")
    if set(expected.get("expectedLogicalItemIds", [])) != set(blocked):
        fail("validation expectedLogicalItemIds mismatch")
    if expected.get("nativeReadyWeaponCount") != 0:
        fail("no BO3 firearm may be marked native-ready yet")
    if expected.get("behaviorSpecReadyWeaponCount") != 8:
        fail("all eight behavior specs must be ready")

    if expected.get("damageFalloffReadyWeaponCount") != 0:
        fail("no BO3 firearm may claim a verified Zombies falloff curve yet")
    if expected.get("nativeEnablementAllowed") is not False:
        fail("native wall-buy enablement must remain blocked")

    result = {
        "weaponSpecs": len(weapons),
        "blockedPurchasesMatched": len(blocked),
        "directAmmoRefillCosts": direct_refills,
        "derivedAmmoRefillCosts": derived_refills,
        "nativeReadyWeapons": 0,
        "status": "PASS",
    }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
