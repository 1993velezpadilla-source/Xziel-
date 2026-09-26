#!/usr/bin/env python3
"""Build a non-shipping XZIEL reference package from the Pavlov Nacht audit.

This turns extracted metadata into the same portable map-package family used by
XZIEL map tooling. It intentionally does NOT embed third-party geometry,
textures, audio, or other copyrighted payloads.

Inputs:
  - nacht-spatial-manifest.json
  - nacht-purchase-slots-resolved.json

Output directory:
  map.json
  entities.json
  spawns.json
  purchases.json
  environment.json
  collision.json
  zones.json
  manifest.json
  preflight.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def uid(prefix: str, text: str) -> str:
    return prefix + "_" + hashlib.sha1(
        ("nacht-reference:" + text).encode("utf-8")
    ).hexdigest()[:16]


def ue_cm_to_xziel_m(value: dict[str, Any] | None) -> dict[str, float] | None:
    if not isinstance(value, dict):
        return None
    try:
        x = float(value.get("X", value.get("x", 0.0))) / 100.0
        y = -float(value.get("Y", value.get("y", 0.0))) / 100.0
        z = float(value.get("Z", value.get("z", 0.0))) / 100.0
        return {"x": round(x, 6), "y": round(y, 6), "z": round(z, 6)}
    except (TypeError, ValueError):
        return None


def source_transform(actor: dict[str, Any]) -> dict[str, Any]:
    transform = actor.get("transform") or {}
    return {
        "position": ue_cm_to_xziel_m(transform.get("location")),
        "sourceRotationUE": transform.get("rotation"),
        "sourceScaleUE": transform.get("scale"),
        "coordinateConversion": "XZIEL.x=UE.x; XZIEL.y=-UE.y; XZIEL.z=UE.z; cm_to_m",
    }


def actor_kind(class_name: str) -> tuple[str, str, bool]:
    table = (
        ("Zombie_hounds_Spawner", "hound_spawn", "pavlov_port_extension", False),
        ("ZombieSpawner", "zombie_spawn", "layout_reference", True),
        ("Barricade", "barricade_window", "bo3_layout_reference", True),
        ("Pavlov_Spawn", "player_spawn", "layout_reference", True),
        ("BuyableDoor_Child", "buyable_door_child", "layout_reference", True),
        ("BuyableDoor", "buyable_door", "layout_reference", True),
        ("MysteryBoxLocation", "mystery_box_anchor", "bo3_layout_reference", True),
        ("PunchAPack", "pack_a_punch", "pavlov_port_extension", False),
        ("WonderFizz", "wunderfizz", "bo3_chronicles_feature_reference", True),
        ("PerkMachine_QuickRevive", "quick_revive_machine", "pavlov_port_extension", False),
        ("MachineGumball", "gobblegum_machine", "bo3_chronicles_feature_reference", True),
        ("ZombieGameLogic", "zombie_game_logic", "pavlov_port_logic", False),
        ("Pavlov_Codz_GameLogic", "pavlov_codz_game_logic", "pavlov_port_logic", False),
    )
    for needle, kind, authority, enabled in table:
        if needle.lower() in class_name.lower():
            return kind, authority, enabled
    return "reference_actor", "pavlov_port_reference", False


def normalize_purchase(slot: dict[str, Any]) -> dict[str, Any]:
    pos = (slot.get("transform") or {}).get("position")
    xziel_pos = ue_cm_to_xziel_m(pos)

    yaw_candidates = slot.get("yaw_candidates")
    xziel_yaw_candidates = None
    if isinstance(yaw_candidates, list):
        xziel_yaw_candidates = [
            round((-float(yaw)) % 360.0, 6)
            for yaw in yaw_candidates
        ]

    source_rotation = (slot.get("transform") or {}).get("rotation")
    return {
        "id": uid("purchase", slot["source_marker"]),
        "name": slot["canonical"],
        "type": slot["type"],
        "transform": {
            "position": xziel_pos,
            "rotation": None,
            "sourceRotationUE": source_rotation,
            "yawCandidates": xziel_yaw_candidates,
            "orientationPolicy": slot.get("runtime_orientation_policy"),
        },
        "enabled": True,
        "replicationPolicy": "server_authoritative",
        "properties": {
            "weaponId": slot["weapon_id"],
            "displayName": slot["canonical"],
            "price": slot["price"],
            "sourceMarker": slot["source_marker"],
            "markerMeshReference": slot.get("marker_mesh"),
            "placementSource": slot.get("placement_source"),
            "placementConfidence": slot.get("placement_confidence"),
            "functionalActor": slot.get("functional_actor"),
            "sourceAuthority": "bo3_chronicles_purchase_reference",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("spatial_manifest", type=Path)
    ap.add_argument("resolved_purchases", type=Path)
    ap.add_argument("output_dir", type=Path)
    args = ap.parse_args()

    spatial = json.loads(args.spatial_manifest.read_text(encoding="utf-8"))
    purchase_doc = json.loads(args.resolved_purchases.read_text(encoding="utf-8"))
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)

    gameplay = spatial.get("gameplay_actors") or []
    environment = spatial.get("environment_actors") or []
    collision = spatial.get("collision_actors") or []

    entities: list[dict[str, Any]] = []
    spawns: list[dict[str, Any]] = []
    port_extensions: list[dict[str, Any]] = []

    for actor in gameplay:
        class_name = actor["class"]
        if class_name.endswith("/WallBuy_C"):
            # Superseded by the complete nine-slot purchase inventory.
            continue

        kind, authority, enabled = actor_kind(class_name)
        row = {
            "id": uid(kind, f"{actor['export_index']}:{actor['name']}"),
            "name": actor["name"],
            "type": kind,
            "transform": source_transform(actor),
            "enabled": enabled,
            "replicationPolicy": "server_authoritative",
            "properties": {
                "sourceClass": class_name,
                "sourceExportIndex": actor["export_index"],
                "sourceAuthority": authority,
            },
        }

        if kind in {"zombie_spawn", "hound_spawn", "player_spawn"}:
            row["properties"].update({
                "spawnGroup": kind,
                "requiresNavValidation": True,
            })
            spawns.append(row)
        elif authority == "pavlov_port_extension" or authority == "pavlov_port_logic":
            port_extensions.append(row)
        else:
            entities.append(row)

    purchases = [
        normalize_purchase(slot)
        for slot in purchase_doc.get("purchase_slots", [])
    ]
    entities.extend(purchases)

    env_rows = []
    for actor in environment:
        env_rows.append({
            "id": uid("env", f"{actor['export_index']}:{actor['name']}"),
            "name": actor["name"],
            "class": actor["class"],
            "transform": source_transform(actor),
            "sourceAuthority": "pavlov_port_environment_reference",
        })

    collision_rows = []
    for actor in collision:
        collision_rows.append({
            "id": uid("collision", f"{actor['export_index']}:{actor['name']}"),
            "name": actor["name"],
            "class": actor["class"],
            "transform": source_transform(actor),
            "sourceAuthority": "pavlov_port_collision_reference",
        })

    zones = [
        {
            "id": "zone_nacht_reference",
            "type": "reference_root",
            "bounds": None,
            "neighbors": [],
            "spawnGroups": ["zombie_spawn", "player_spawn"],
            "notes": (
                "Temporary coarse zone. BO3 logical zones start_zone, box_zone "
                "and upstairs_zone will be classified in a later topology pass."
            ),
        }
    ]

    manifest = {
        "id": "nacht_bo3_reference",
        "version": "0.1.0-audit",
        "schemaVersion": 1,
        "engineMinVersion": "0.1",
        "authors": ["XZIEL project audit tooling"],
        "sourceAttribution": [
            "Pavlov Workshop 2755515831 community Nacht port",
            "Community port credits Treyarch for Call of Duty BO1/BO3 map geometry/models",
        ],
        "nonShippingReference": True,
        "commercialUseAllowed": False,
        "containsThirdPartyPayload": False,
        "assetPayloadPolicy": (
            "Metadata/provenance only. Do not ship extracted Call of Duty or "
            "community-port assets without explicit redistribution rights."
        ),
        "geometry": {
            "externalReference": "Pavlov Workshop 2755515831",
            "runtimeGeometryPending": True,
            "coordinateSystem": "XZIEL meters, Z-up; source UE Y reflected",
        },
        "profile": {
            "authoritativePurchaseSlots": True,
            "layoutSource": "community_port",
            "bo3ChroniclesMode": True,
            "portExtensionsDefaultEnabled": False,
        },
    }

    map_json = {
        "schemaVersion": 1,
        "id": "nacht_bo3_reference",
        "displayName": "Nacht der Untoten — BO3 Reference",
        "geometry": None,
        "zones": "zones.json",
        "entities": "entities.json",
        "spawns": "spawns.json",
        "purchases": "purchases.json",
        "environment": "environment.json",
        "collision": "collision.json",
        "portExtensions": "port_extensions.json",
        "manifest": "manifest.json",
    }

    docs = {
        "map.json": map_json,
        "zones.json": {"schemaVersion": 1, "zones": zones},
        "entities.json": {"schemaVersion": 1, "entities": entities},
        "spawns.json": {"schemaVersion": 1, "spawns": spawns},
        "purchases.json": {"schemaVersion": 1, "purchases": purchases},
        "environment.json": {"schemaVersion": 1, "actors": env_rows},
        "collision.json": {"schemaVersion": 1, "actors": collision_rows},
        "port_extensions.json": {"schemaVersion": 1, "entities": port_extensions},
        "manifest.json": manifest,
    }
    for name, payload in docs.items():
        (out / name).write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )

    counts = {
        "purchases": len(purchases),
        "wall_or_cabinet_purchases": sum(
            1 for p in purchases if p["type"] in {"wallbuy", "sniper_cabinet"}
        ),
        "equipment_purchases": sum(
            1 for p in purchases if p["type"] == "equipment"
        ),
        "barricades": sum(1 for e in entities if e["type"] == "barricade_window"),
        "mystery_box_anchors": sum(
            1 for e in entities if e["type"] == "mystery_box_anchor"
        ),
        "zombie_spawns": sum(1 for s in spawns if s["type"] == "zombie_spawn"),
        "hound_spawns_disabled": sum(1 for s in spawns if s["type"] == "hound_spawn"),
        "player_spawns": sum(1 for s in spawns if s["type"] == "player_spawn"),
        "gobblegum_machines": sum(
            1 for e in entities if e["type"] == "gobblegum_machine"
        ),
        "environment_actors": len(env_rows),
        "collision_actors": len(collision_rows),
        "port_extensions": len(port_extensions),
    }

    errors = []
    if counts["purchases"] != 9:
        errors.append(f"expected 9 purchase slots, got {counts['purchases']}")
    if counts["wall_or_cabinet_purchases"] != 8:
        errors.append(
            f"expected 8 weapon/cabinet slots, got {counts['wall_or_cabinet_purchases']}"
        )
    if counts["equipment_purchases"] != 1:
        errors.append(
            f"expected 1 equipment slot, got {counts['equipment_purchases']}"
        )
    if counts["barricades"] != 12:
        errors.append(f"expected 12 barricades, got {counts['barricades']}")
    if counts["zombie_spawns"] != 21:
        errors.append(f"expected 21 port zombie spawns, got {counts['zombie_spawns']}")
    if counts["player_spawns"] != 10:
        errors.append(f"expected 10 port player spawns, got {counts['player_spawns']}")
    if counts["mystery_box_anchors"] != 1:
        errors.append(
            f"expected 1 mystery box anchor, got {counts['mystery_box_anchors']}"
        )

    preflight = {
        "ok": not errors,
        "errors": errors,
        "counts": counts,
        "warnings": [
            "This is a non-shipping reverse-engineering reference package.",
            "Spawn and door positions are community-port layout references, not Treyarch source.",
            "Hound spawns, Pack-a-Punch and fixed Quick Revive are disabled as Pavlov-port extensions.",
            "Logical room-zone classification is still pending.",
            "Runtime geometry/material conversion is still pending.",
        ],
    }
    (out / "preflight.json").write_text(
        json.dumps(preflight, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(preflight, indent=2))
    return 0 if not errors else 3


if __name__ == "__main__":
    raise SystemExit(main())
