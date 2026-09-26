#!/usr/bin/env python3
"""Regenerate the global XZIEL Mystery Box pool from the weapon catalog."""

from __future__ import annotations

import json
from pathlib import Path

CATALOG = Path("assets/weapons/xziel_weapon_catalog_v1.json")
OUT = Path("assets/weapons/xziel_mystery_box_pool_v1.json")


def main() -> int:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    weapons = catalog.get("weapons", [])
    eligible = [
        w["weaponId"]
        for w in weapons
        if w.get("gameEnabled") is True and w.get("mysteryBoxEligible") is True
    ]

    pool = {
        "schemaVersion": 1,
        "poolId": "xziel_mystery_box_global_v1",
        "policy": "global_enabled_firearms",
        "catalog": str(CATALOG),
        "generated": True,
        "notes": [
            "Every globally enabled firearm marked mysteryBoxEligible is included automatically.",
            "Map profiles may exclude entries later without deleting them from the global catalog.",
            "A catalog entry still requires a native weapon binding before playable spawning is possible."
        ],
        "weaponIds": eligible,
        "validation": {
            "generatedEligibleCount": len(eligible)
        }
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(pool, indent=2) + "\n", encoding="utf-8")
    print(f"XZIEL_MYSTERY_BOX_POOL_OK count={len(eligible)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
