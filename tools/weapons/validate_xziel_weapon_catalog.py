#!/usr/bin/env python3
"""Validate XZIEL global weapon identity and map-specific Mystery Box pools."""

from __future__ import annotations

import json
from pathlib import Path

CATALOG = Path("assets/weapons/xziel_weapon_catalog_v1.json")
GLOBAL_POOL = Path("assets/weapons/xziel_mystery_box_pool_v1.json")
NACHT_POOL = Path("assets/weapons/nacht_prototype_box_pool_v1.json")
NACHT = Path("assets/nacht_reference/runtime_reference_v1.json")

FORBIDDEN_BALLISTIC_KEYS = {
    "damage",
    "damageFalloff",
    "damageMin",
    "damageMax",
    "minDamage",
    "maxDamage",
    "range",
    "ranges",
    "falloff",
    "headMultiplier",
}


def fail(message: str) -> None:
    raise SystemExit(message)


def walk_forbidden(value, path="root"):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_BALLISTIC_KEYS:
                fail(f"identity catalog must not carry ballistic key {path}.{key}")
            walk_forbidden(child, f"{path}.{key}")
    elif isinstance(value, list):
        for i, child in enumerate(value):
            walk_forbidden(child, f"{path}[{i}]")


def main() -> int:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    global_pool = json.loads(GLOBAL_POOL.read_text(encoding="utf-8"))
    nacht_pool = json.loads(NACHT_POOL.read_text(encoding="utf-8"))
    nacht = json.loads(NACHT.read_text(encoding="utf-8"))

    if catalog.get("schemaVersion") != 1:
        fail("catalog schemaVersion must be 1")
    if catalog.get("scope") != "gameplay_weapon_identity_catalog":
        fail("catalog scope mismatch")

    walk_forbidden(catalog)

    weapons = catalog.get("weapons", [])
    validation = catalog.get("validation", {})
    minimum = validation.get("minimumWeaponCount", 0)
    if len(weapons) < minimum:
        fail(f"weapon catalog shrank below baseline: {len(weapons)} < {minimum}")

    ids = [w.get("weaponId") for w in weapons]
    names = [w.get("displayName") for w in weapons]
    if any(not x for x in ids) or len(ids) != len(set(ids)):
        fail("weaponId values must be non-empty and unique")
    if any(not x for x in names) or len(names) != len(set(names)):
        fail("displayName values must be non-empty and unique")

    baseline = set(validation.get("baselineWeaponIds", []))
    missing_baseline = baseline - set(ids)
    if missing_baseline:
        fail(f"baseline weapons removed: {sorted(missing_baseline)}")

    zm_count = sum(w.get("zombiesStatsAvailable") is True for w in weapons)
    if zm_count < validation.get("minimumZombiesStatsAvailableCount", 0):
        fail(f"Zombies-source coverage shrank: {zm_count}")

    for w in weapons:
        if w.get("gameEnabled") is not True:
            fail(f"global catalog weapon disabled unexpectedly: {w.get('weaponId')}")
        if w.get("origin") not in {"bo3_reference_identity", "xziel_original", "licensed_external"}:
            fail(f"unsupported weapon origin for {w.get('weaponId')}: {w.get('origin')}")
        if not isinstance(w.get("mysteryBoxEligible"), bool):
            fail(f"mysteryBoxEligible must be boolean for {w.get('weaponId')}")
        if w.get("nativeBindingStatus") not in {"pending", "ready"}:
            fail(f"invalid nativeBindingStatus for {w.get('weaponId')}")
        if w.get("kind") not in {"firearm", "wonder_weapon", "equipment", "melee"}:
            fail(f"invalid kind for {w.get('weaponId')}: {w.get('kind')}")

    by_id = {w["weaponId"]: w for w in weapons}

    prototype = [
        w for w in weapons
        if w.get("nachtPrototype", {}).get("present") is True
    ]
    expected_prototype_count = validation.get("requiredNachtPrototypeTableCount")
    if len(prototype) != expected_prototype_count:
        fail(f"Nacht prototype table coverage mismatch: {len(prototype)} != {expected_prototype_count}")

    prototype_box = [
        w["weaponId"]
        for w in weapons
        if w.get("nachtPrototype", {}).get("present") is True
        and w.get("nachtPrototype", {}).get("inBox") is True
    ]
    expected_box_count = validation.get("requiredNachtPrototypeBoxCount")
    if len(prototype_box) != expected_box_count:
        fail(f"Nacht prototype box coverage mismatch: {len(prototype_box)} != {expected_box_count}")

    firearm_wall_buys = [
        p for p in nacht.get("purchases", [])
        if p.get("logicalItemId") != "frag_grenade"
    ]
    if len(firearm_wall_buys) != validation.get("requiredNachtWallBuyFirearmCount"):
        fail(f"expected 8 Nacht firearm wall buys, got {len(firearm_wall_buys)}")

    seen_wall_ids = set()
    for purchase in firearm_wall_buys:
        weapon_id = purchase["logicalItemId"]
        if weapon_id not in by_id:
            fail(f"Nacht wall-buy weapon absent from global catalog: {weapon_id}")
        entry = by_id[weapon_id]
        if entry.get("displayName") != purchase.get("displayName"):
            fail(f"Nacht displayName mismatch for {weapon_id}")
        if entry.get("nachtWallBuyId") != purchase.get("id"):
            fail(f"Nacht wall-buy linkage mismatch for {weapon_id}")
        if purchase["id"] in seen_wall_ids:
            fail(f"duplicate Nacht wall-buy id: {purchase['id']}")
        seen_wall_ids.add(purchase["id"])

    expected_global_pool = [
        w["weaponId"]
        for w in weapons
        if w.get("gameEnabled") is True and w.get("mysteryBoxEligible") is True
    ]
    global_ids = global_pool.get("weaponIds", [])
    if global_ids != expected_global_pool:
        fail("global Mystery Box pool is stale; regenerate it from the catalog")
    if len(global_ids) != len(set(global_ids)):
        fail("global Mystery Box pool contains duplicate weapon IDs")
    if any(wid not in by_id for wid in global_ids):
        fail("global Mystery Box pool contains orphan weapon IDs")

    nacht_ids = nacht_pool.get("weaponIds", [])
    if nacht_ids != prototype_box:
        fail("Nacht Mystery Box pool is stale; regenerate it from the catalog")
    if len(nacht_ids) != len(set(nacht_ids)):
        fail("Nacht Mystery Box pool contains duplicate weapon IDs")
    if nacht_pool.get("mapId") != "xziel_nacht_bo3":
        fail("Nacht Mystery Box pool mapId mismatch")

    weapon_runtime = nacht.get("weaponRuntime", {})
    expected_paths = {
        "globalCatalog": str(CATALOG),
        "globalMysteryBoxPool": str(GLOBAL_POOL),
        "nachtMysteryBoxPool": str(NACHT_POOL),
    }
    for key, expected_path in expected_paths.items():
        if weapon_runtime.get(key) != expected_path:
            fail(f"Nacht weapon runtime path mismatch for {key}: {weapon_runtime.get(key)!r}")

    if weapon_runtime.get("scope") != "identity_and_availability_only":
        fail("Nacht weapon runtime must remain identity/availability-only")
    if weapon_runtime.get("ballisticTuning") != "unchanged":
        fail("weapon catalog work must not alter ballistic tuning")

    catalog_minimum = weapon_runtime.get("globalCatalogMinimumCount")
    if not isinstance(catalog_minimum, int) or catalog_minimum < 51:
        fail(f"invalid global catalog baseline: {catalog_minimum!r}")
    if len(weapons) < catalog_minimum:
        fail(f"global catalog below runtime baseline: {len(weapons)} < {catalog_minimum}")

    box_minimum = weapon_runtime.get("globalMysteryBoxMinimumCount")
    if not isinstance(box_minimum, int) or box_minimum < 46:
        fail(f"invalid global box baseline: {box_minimum!r}")
    if len(global_ids) < box_minimum:
        fail(f"global box below runtime baseline: {len(global_ids)} < {box_minimum}")

    if weapon_runtime.get("nachtPrototypeWeaponTableCount") != len(prototype):
        fail("Nacht runtime weapon-table count is stale")
    if weapon_runtime.get("nachtPrototypeMysteryBoxCount") != len(nacht_ids):
        fail("Nacht runtime Mystery Box count is stale")

    print(
        "XZIEL_WEAPON_CATALOG_OK "
        f"weapons={len(weapons)} zmSource={zm_count} "
        f"globalBox={len(global_ids)} nachtTable={len(prototype)} "
        f"nachtBox={len(nacht_ids)} nachtFirearms={len(firearm_wall_buys)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
