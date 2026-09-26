#!/usr/bin/env python3
"""Add one future weapon identity to the global XZIEL catalog.

This command intentionally manages identity/availability only. It never writes
damage, falloff, recoil, animation, art, audio, or native implementation data.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

CATALOG = Path("assets/weapons/xziel_weapon_catalog_v1.json")
EXPORT_GLOBAL_POOL = Path("tools/weapons/export_xziel_mystery_box_pool.py")
VALIDATE = Path("tools/weapons/validate_xziel_weapon_catalog.py")

CATEGORIES = (
    "ar",
    "smg",
    "lmg",
    "sniper",
    "shotgun",
    "pistol",
    "launcher",
    "special",
    "equipment",
    "melee",
)
KINDS = ("firearm", "wonder_weapon", "equipment", "melee")
ORIGINS = ("xziel_original", "licensed_external", "bo3_reference_identity")


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weapon-id", required=True)
    ap.add_argument("--display-name", required=True)
    ap.add_argument("--category", required=True, choices=CATEGORIES)
    ap.add_argument("--kind", required=True, choices=KINDS)
    ap.add_argument("--origin", default="xziel_original", choices=ORIGINS)
    ap.add_argument("--source-weapon-file")
    ap.add_argument("--zombies-stats-available", action="store_true")
    box = ap.add_mutually_exclusive_group()
    box.add_argument("--box", dest="box", action="store_true")
    box.add_argument("--no-box", dest="box", action="store_false")
    ap.set_defaults(box=True)
    args = ap.parse_args()

    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    weapons = data.get("weapons", [])

    if any(w.get("weaponId") == args.weapon_id for w in weapons):
        fail(f"weaponId already exists: {args.weapon_id}")
    if any(w.get("displayName") == args.display_name for w in weapons):
        fail(f"displayName already exists: {args.display_name}")

    entry = {
        "weaponId": args.weapon_id,
        "displayName": args.display_name,
        "category": args.category,
        "sourceWeaponFile": args.source_weapon_file,
        "zombiesStatsAvailable": args.zombies_stats_available,
        "gameEnabled": True,
        "mysteryBoxEligible": args.box,
        "nativeBindingStatus": "pending",
        "origin": args.origin,
        "nachtWallBuyId": None,
        "kind": args.kind,
        "nachtPrototype": {
            "present": False
        }
    }

    weapons.append(entry)
    weapons.sort(key=lambda w: w["weaponId"])
    data["weapons"] = weapons

    # Deliberately preserve validation.baselineWeaponIds and minimumWeaponCount:
    # they protect the existing corpus while allowing future additions.
    CATALOG.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    subprocess.run([sys.executable, str(EXPORT_GLOBAL_POOL)], check=True)
    subprocess.run([sys.executable, str(VALIDATE)], check=True)

    print(
        "XZIEL_WEAPON_ADDED "
        f"id={args.weapon_id} name={args.display_name!r} "
        f"box={args.box} nativeBindingStatus=pending"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
