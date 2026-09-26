#!/usr/bin/env python3
"""Regenerate the exact BO3 Nacht (zm_prototype) Mystery Box pool from the global catalog."""

from __future__ import annotations

import json
from pathlib import Path

CATALOG = Path("assets/weapons/xziel_weapon_catalog_v1.json")
OUT = Path("assets/weapons/nacht_prototype_box_pool_v1.json")


def main() -> int:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    weapons = catalog.get("weapons", [])
    ids = [
        w["weaponId"]
        for w in weapons
        if w.get("nachtPrototype", {}).get("present") is True
        and w.get("nachtPrototype", {}).get("inBox") is True
    ]

    pool = {
        "schemaVersion": 1,
        "poolId": "nacht_prototype_box_pool_v1",
        "mapId": "xziel_nacht_bo3",
        "policy": "exact_zm_prototype_in_box_membership",
        "catalog": str(CATALOG),
        "generated": True,
        "sourceAuthority": catalog.get("sourceAuthority", {}).get("nachtPrototypeWeaponTable"),
        "weaponIds": ids,
        "validation": {
            "generatedEligibleCount": len(ids)
        }
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(pool, indent=2) + "\n", encoding="utf-8")
    print(f"NACHT_PROTOTYPE_BOX_POOL_OK count={len(ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
