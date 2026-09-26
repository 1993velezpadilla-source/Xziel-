#!/usr/bin/env python3
"""Export the compact verified Nacht runtime reference into an NZ:P overlay.

The generated overlay is intentionally honest about weapon readiness. It never
maps a BO3 firearm to an unrelated NZ:P gun just to make a wall-buy trigger
appear functional.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT_REFERENCE = Path("assets/nacht_reference/runtime_reference_v1.json")
DEFAULT_OUTPUT = Path("assets/nacht_reference/nzp_runtime_overlay.json")

WEAPON_MAP = {
    "frag_grenade": "W_GRENADE",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = ap.parse_args()

    ref = json.loads(args.reference.read_text(encoding="utf-8"))

    purchases = []
    for source in ref["purchases"]:
        item = dict(source)
        native = WEAPON_MAP.get(source["logicalItemId"])
        item["nzpWeaponConstant"] = native
        item["integrationStatus"] = (
            "native_ready" if native else "awaiting_native_weapon_definition"
        )
        item["replicationPolicy"] = "server_authoritative"
        item["notes"] = (
            "Use stock NZ:P W_GRENADE purchase path; fills primary grenades to four."
            if native == "W_GRENADE"
            else "Do not substitute an unrelated NZ:P firearm. Implement the BO3 weapon definition first."
        )
        purchases.append(item)

    barricades = []
    for source in ref["barricades"]:
        item = dict(source)
        item["repairable"] = True
        item["nzpEntityClass"] = "item_barricade"
        item["replicationPolicy"] = "server_authoritative"
        barricades.append(item)

    zombie_spawns = []
    for source in ref["zombieSpawns"]:
        item = dict(source)
        item["linkedBarricadeId"] = barricades[source["linkedBarricadeIndex"]]["id"]
        item["replicationPolicy"] = "server_authoritative"
        zombie_spawns.append(item)

    doors = []
    for source in ref["doors"]:
        item = dict(source)
        item["replicationPolicy"] = "server_authoritative"
        doors.append(item)

    output = {
        "schemaVersion": 1,
        "mapId": ref["mapId"],
        "source": ref["source"],
        "coordinateSystem": ref["coordinateSystem"],
        "runtimePolicy": ref["runtimePolicy"],
        "purchases": purchases,
        "doors": doors,
        "barricades": barricades,
        "zombieSpawns": zombie_spawns,
        "validation": {
            "purchaseCount": len(purchases),
            "nativeReadyPurchases": sum(
                p["integrationStatus"] == "native_ready" for p in purchases
            ),
            "blockedWeaponPurchases": sum(
                p["integrationStatus"] != "native_ready" for p in purchases
            ),
            "doorCount": len(doors),
            "barricadeCount": len(barricades),
            "zombieSpawnCount": len(zombie_spawns),
            "startSpawnCount": sum(
                s["zone"] == "start_zone" for s in zombie_spawns
            ),
            "boxSpawnCount": sum(
                s["zone"] == "box_zone" for s in zombie_spawns
            ),
            "upstairsSpawnCount": sum(
                s["zone"] == "upstairs_zone" for s in zombie_spawns
            ),
        },
    }

    expected = {
        "purchaseCount": 9,
        "nativeReadyPurchases": 1,
        "blockedWeaponPurchases": 8,
        "doorCount": 3,
        "barricadeCount": 12,
        "zombieSpawnCount": 21,
        "startSpawnCount": 10,
        "boxSpawnCount": 5,
        "upstairsSpawnCount": 6,
    }
    if output["validation"] != expected:
        raise SystemExit(
            f"overlay validation mismatch: {output['validation']} != {expected}"
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output["validation"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
