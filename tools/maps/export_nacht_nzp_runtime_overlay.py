#!/usr/bin/env python3
"""Export the verified BO3 Nacht gameplay reference into an NZ:P overlay manifest.

This generator deliberately does NOT substitute unrelated NZ:P firearms for BO3
weapons. Slots are marked native_ready only when a real QuakeC weapon mapping
exists. The output is therefore safe to consume incrementally while weapon
definitions are implemented.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT_PLAN = Path("experiments/bo3_nacht_reference/nacht_wallbuy_repair_plan_v2.json")
DEFAULT_ENTITIES = Path("experiments/bo3_nacht_reference/xziel_reference_package/entities.json")
DEFAULT_SPAWNS = Path("experiments/bo3_nacht_reference/xziel_reference_package/spawns.json")
DEFAULT_OUTPUT = Path("experiments/bo3_nacht_reference/nzp_runtime_overlay.json")

WEAPON_MAP = {
    # NZ:P already has dedicated primary-grenade purchase semantics for W_GRENADE.
    "frag_grenade": "W_GRENADE",
}

ROOM_TO_ZONE = {
    "spawn": "start_zone",
    "help_1f": "box_zone",
    "help_2f": "upstairs_zone",
    "grenade_room": "upstairs_zone",
}

CANONICAL_DOORS = [
    {
        "id": "door_start_to_box",
        "sourceActor": "BuyableDoor_2",
        "cost": 1000,
        "fromZone": "start_zone",
        "unlocksZone": "box_zone",
    },
    {
        "id": "door_start_to_upstairs",
        "sourceActor": "BuyableDoor_Child2",
        "cost": 1000,
        "fromZone": "start_zone",
        "unlocksZone": "upstairs_zone",
    },
    {
        "id": "door_box_to_upstairs",
        "sourceActor": "BuyableDoor_Child_2",
        "cost": 1000,
        "fromZone": "box_zone",
        "unlocksZone": "upstairs_zone",
    },
]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def actor_position(entity):
    pos = entity["transform"]["position"]
    return [float(pos["x"]), float(pos["y"]), float(pos["z"])]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wallbuy-plan", type=Path, default=DEFAULT_PLAN)
    ap.add_argument("--entities", type=Path, default=DEFAULT_ENTITIES)
    ap.add_argument("--spawns", type=Path, default=DEFAULT_SPAWNS)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = ap.parse_args()

    plan = load(args.wallbuy_plan)
    entities = load(args.entities)["entities"]
    spawns = load(args.spawns)["spawns"]

    by_name = {e.get("name"): e for e in entities}

    purchases = []
    for slot in plan["purchase_slots"]:
        logical = slot["bo3_weapon_id"]
        native = WEAPON_MAP.get(logical)
        p = slot["interaction_location_xziel_m"]
        purchases.append({
            "id": slot["id"],
            "displayName": slot["canonical"],
            "kind": slot["type"],
            "logicalItemId": logical,
            "nzpWeaponConstant": native,
            "integrationStatus": "native_ready" if native else "awaiting_native_weapon_definition",
            "cost": int(slot["price"]),
            "zone": ROOM_TO_ZONE[slot["room_group"]],
            "positionMeters": [float(p["x"]), float(p["y"]), float(p["z"])],
            "replicationPolicy": "server_authoritative",
            "notes": (
                "Use stock NZ:P W_GRENADE purchase path; fills primary grenades to four."
                if native == "W_GRENADE"
                else "Do not substitute an unrelated NZ:P firearm. Implement the BO3 weapon definition first."
            ),
        })

    doors = []
    for definition in CANONICAL_DOORS:
        actor = by_name.get(definition["sourceActor"])
        if actor is None:
            raise SystemExit(f"missing door actor {definition['sourceActor']}")
        door = dict(definition)
        door["positionMeters"] = actor_position(actor)
        door["replicationPolicy"] = "server_authoritative"
        door["transformAuthority"] = "pavlov_port_doorflag_topology"
        door["costAuthority"] = "canonical_nacht_1000_point_progression"
        doors.append(door)

    barricades = []
    barricade_index = {}
    for e in entities:
        if e.get("type") != "barricade":
            continue
        barricade_index[e["id"]] = len(barricades)
        barricades.append({
            "id": e["id"],
            "positionMeters": actor_position(e),
            "maximumBoards": int(e["properties"]["boardCount"]),
            "repairable": bool(e["properties"]["repairable"]),
            "replicationPolicy": e["replicationPolicy"],
            "nzpEntityClass": "item_barricade",
        })

    zombie_spawns = []
    for e in spawns:
        if e.get("type") != "zombie_spawn":
            continue
        linked = e["properties"].get("linkedBarricade")
        zombie_spawns.append({
            "id": e["id"],
            "positionMeters": actor_position(e),
            "zone": e["properties"]["zoneHint"],
            "activeDefault": bool(e["properties"]["activeDefault"]),
            "riser": bool(e["properties"]["riser"]),
            "linkedBarricadeId": linked,
            "linkedBarricadeIndex": barricade_index.get(linked),
            "replicationPolicy": e["replicationPolicy"],
        })

    output = {
        "schemaVersion": 1,
        "mapId": "bo3_nacht_reference",
        "sourceProfile": "bo3_chronicles",
        "coordinateSystem": {
            "units": "meters",
            "upAxis": "z",
            "note": "Matches persisted XZIEL package / Quake-style Z-up overlay.",
        },
        "runtimePolicy": {
            "serverAuthoritative": True,
            "maximumPlayers": 4,
            "maximumActiveZombies": 24,
            "startingPoints": 500,
            "initialZone": "start_zone",
        },
        "purchases": purchases,
        "doors": doors,
        "barricades": barricades,
        "zombieSpawns": zombie_spawns,
        "validation": {
            "purchaseCount": len(purchases),
            "nativeReadyPurchases": sum(p["integrationStatus"] == "native_ready" for p in purchases),
            "blockedWeaponPurchases": sum(p["integrationStatus"] != "native_ready" for p in purchases),
            "doorCount": len(doors),
            "barricadeCount": len(barricades),
            "zombieSpawnCount": len(zombie_spawns),
        },
    }

    expected = {
        "purchaseCount": 9,
        "nativeReadyPurchases": 1,
        "blockedWeaponPurchases": 8,
        "doorCount": 3,
        "barricadeCount": 12,
        "zombieSpawnCount": 21,
    }
    if output["validation"] != expected:
        raise SystemExit(f"overlay validation mismatch: {output['validation']} != {expected}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output["validation"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
