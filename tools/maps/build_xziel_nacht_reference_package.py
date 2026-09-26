#!/usr/bin/env python3
"""Build an XZIEL map-reference package from the Pavlov BO3 Nacht cooked-map audit.

This produces metadata and scene layout only.  It intentionally does not copy
third-party cooked asset payloads into the repository.

Authority is split explicitly:
- official_t7: facts taken from decompiled BO3/T7 map script structure;
- bo3_derived_geometry: geometry/layout from the Pavlov community port credited
  to BO1/BO3 geometry/models;
- pavlov_extension: gameplay actors added by the community port and not treated
  as canonical BO3 Nacht behavior.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def prop_map(export: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        p["Name"]: p
        for p in export.get("Data", [])
        if isinstance(p, dict) and isinstance(p.get("Name"), str)
    }


def struct_value(prop: dict[str, Any] | None) -> Any:
    if not prop:
        return None
    value = prop.get("Value")
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0].get("Value")
    return value


def clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: clean(v)
            for k, v in value.items()
            if k != "$type"
        }
    if isinstance(value, list):
        return [clean(v) for v in value]
    if value == "+0":
        return 0.0
    return value


def ue_vec_to_xziel_m(value: Any) -> dict[str, float] | None:
    """UE cm -> XZIEL/Blender-style meters: X, -Y, Z."""
    if not isinstance(value, dict):
        return None
    try:
        x = 0.0 if value.get("X") == "+0" else float(value.get("X", 0.0))
        y = 0.0 if value.get("Y") == "+0" else float(value.get("Y", 0.0))
        z = 0.0 if value.get("Z") == "+0" else float(value.get("Z", 0.0))
    except (TypeError, ValueError):
        return None
    return {"x": x / 100.0, "y": -y / 100.0, "z": z / 100.0}


def lower_vec_to_xziel_m(value: Any) -> dict[str, float] | None:
    if not isinstance(value, dict):
        return None
    try:
        return {
            "x": float(value.get("x", 0.0)) / 100.0,
            "y": -float(value.get("y", 0.0)) / 100.0,
            "z": float(value.get("z", 0.0)) / 100.0,
        }
    except (TypeError, ValueError):
        return None


def id_for(prefix: str, name: Any, index: int | None = None) -> str:
    base = str(name or (f"export_{index}" if index else "unknown"))
    safe = "".join(c.lower() if c.isalnum() else "_" for c in base).strip("_")
    while "__" in safe:
        safe = safe.replace("__", "_")
    return f"{prefix}_{safe}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("map_json", type=Path)
    ap.add_argument("wallbuy_plan", type=Path)
    ap.add_argument("out_dir", type=Path)
    args = ap.parse_args()

    doc = json.loads(args.map_json.read_text(encoding="utf-8-sig"))
    exports: list[dict[str, Any]] = doc["Exports"]
    imports: list[dict[str, Any]] = doc["Imports"]
    wallbuy = json.loads(args.wallbuy_plan.read_text(encoding="utf-8"))

    level_index = next(
        i + 1 for i, e in enumerate(exports)
        if "LevelExport" in str(e.get("$type", ""))
    )
    level = exports[level_index - 1]
    actor_indices = [
        x for x in level.get("Actors", [])
        if isinstance(x, int) and x > 0
    ]
    actor_set = set(actor_indices)

    def resolve_index(index: int) -> str | None:
        if not index:
            return None
        parts: list[str] = []
        seen: set[int] = set()
        while index and index not in seen:
            seen.add(index)
            obj = imports[-index - 1] if index < 0 else exports[index - 1]
            parts.append(str(obj.get("ObjectName", "?")))
            index = int(obj.get("OuterIndex", 0) or 0)
        return "/".join(reversed(parts))

    def actor_class(index: int) -> str:
        actor = exports[index - 1]
        return resolve_index(int(actor.get("ClassIndex", 0) or 0)) or "UNKNOWN"

    def root_component(index: int) -> tuple[int | None, dict[str, Any] | None]:
        actor = exports[index - 1]
        root = prop_map(actor).get("RootComponent", {}).get("Value")
        if not isinstance(root, int) or root <= 0:
            return None, None
        return root, exports[root - 1]

    def actor_transform(index: int) -> dict[str, Any]:
        root_index, component = root_component(index)
        if not component:
            return {
                "position": None,
                "sourceRotationUE": None,
                "sourceScale": None,
                "sourceRootComponent": root_index,
            }
        cp = prop_map(component)
        loc = clean(struct_value(cp.get("RelativeLocation")))
        return {
            "position": ue_vec_to_xziel_m(loc),
            "sourcePositionUEcm": loc,
            "sourceRotationUE": clean(struct_value(cp.get("RelativeRotation"))),
            "sourceScale": clean(struct_value(cp.get("RelativeScale3D"))),
            "sourceRootComponent": root_index,
        }

    def scalar(actor: dict[str, Any], name: str) -> Any:
        prop = prop_map(actor).get(name)
        return clean(prop.get("Value")) if prop else None

    def int_array(actor: dict[str, Any], name: str) -> list[int]:
        prop = prop_map(actor).get(name)
        if not prop or not isinstance(prop.get("Value"), list):
            return []
        out: list[int] = []
        for item in prop["Value"]:
            if isinstance(item, dict) and isinstance(item.get("Value"), int):
                out.append(item["Value"])
        return out

    def owner_actor_index(export_index: int) -> int | None:
        idx = export_index
        seen: set[int] = set()
        while idx > 0 and idx not in seen:
            if idx in actor_set:
                return idx
            seen.add(idx)
            idx = int(exports[idx - 1].get("OuterIndex", 0) or 0)
        return None

    # ------------------------------------------------------------------
    # Geometry scene-instance contract.
    # ------------------------------------------------------------------
    scene_instances: list[dict[str, Any]] = []
    for export_index, export in enumerate(exports, start=1):
        props = prop_map(export)
        sm = props.get("StaticMesh")
        if not sm or not isinstance(sm.get("Value"), int) or sm["Value"] == 0:
            continue
        owner = owner_actor_index(export_index)
        if not owner:
            continue
        mesh = resolve_index(sm["Value"])
        if not mesh or "/CoD_nacht/" not in mesh:
            continue
        loc = clean(struct_value(props.get("RelativeLocation")))
        scene_instances.append({
            "instanceId": f"mesh_{export_index}",
            "mesh": mesh,
            "actorExportIndex": owner,
            "actorName": exports[owner - 1].get("ObjectName"),
            "actorClass": actor_class(owner),
            "componentExportIndex": export_index,
            "componentName": export.get("ObjectName"),
            "transform": {
                "position": ue_vec_to_xziel_m(loc),
                "sourcePositionUEcm": loc,
                "sourceRotationUE": clean(struct_value(props.get("RelativeRotation"))),
                "sourceScale": clean(struct_value(props.get("RelativeScale3D"))),
            },
        })

    unique_meshes = sorted({
        row["mesh"] for row in scene_instances if row.get("mesh")
    })

    # ------------------------------------------------------------------
    # Gameplay: barricades + zombie spawns and their direct links.
    # ------------------------------------------------------------------
    barricades: list[dict[str, Any]] = []
    barricade_id_by_export: dict[int, str] = {}
    for ai in actor_indices:
        if not actor_class(ai).endswith("/Barricade_C"):
            continue
        actor = exports[ai - 1]
        eid = id_for("barricade", actor.get("ObjectName"), ai)
        barricade_id_by_export[ai] = eid
        barricades.append({
            "id": eid,
            "name": actor.get("ObjectName"),
            "type": "barricade",
            "transform": actor_transform(ai),
            "source": "bo3_derived_geometry",
            "enabledProfiles": ["bo3_chronicles", "pavlov_extended"],
            "properties": {
                "boardCount": 6,
                "repairable": True,
            },
            "replicationPolicy": "server_authoritative",
        })

    zombie_spawns: list[dict[str, Any]] = []
    hound_spawns: list[dict[str, Any]] = []
    for ai in actor_indices:
        cls = actor_class(ai)
        actor = exports[ai - 1]
        if cls.endswith("/ZombieSpawner_C"):
            p = prop_map(actor)
            bidx = p.get("Barricade", {}).get("Value")
            door_flag = p.get("DoorFlag", {}).get("Value")
            active_default = p.get("Active Default", {}).get("Value")
            riser = p.get("Riser?", {}).get("Value")
            # The flag->zone names are retained as an explicit inference.
            zone_hint = (
                "start_zone" if door_flag is None
                else ("box_zone" if door_flag == 1 else ("upstairs_zone" if door_flag == 2 else None))
            )
            zombie_spawns.append({
                "id": id_for("zspawn", actor.get("ObjectName"), ai),
                "name": actor.get("ObjectName"),
                "type": "zombie_spawn",
                "transform": actor_transform(ai),
                "source": "pavlov_port_spatial_reference",
                "enabledProfiles": ["bo3_chronicles", "pavlov_extended"],
                "properties": {
                    "linkedBarricade": barricade_id_by_export.get(bidx) if isinstance(bidx, int) else None,
                    "sourceBarricadeExportIndex": bidx,
                    "sourceDoorFlag": door_flag,
                    "activeDefault": True if active_default is None else bool(active_default),
                    "riser": bool(riser) if riser is not None else False,
                    "zoneHint": zone_hint,
                    "zoneHintAuthority": "inferred_from_pavlov_door_flag",
                },
                "replicationPolicy": "server_authoritative",
            })
        elif "Zombie_hounds_Spawner" in cls:
            hound_spawns.append({
                "id": id_for("hound_spawn", actor.get("ObjectName"), ai),
                "name": actor.get("ObjectName"),
                "type": "hound_spawn",
                "transform": actor_transform(ai),
                "source": "pavlov_extension",
                "enabledProfiles": ["pavlov_extended"],
                "properties": {},
                "replicationPolicy": "server_authoritative",
            })

    # ------------------------------------------------------------------
    # Purchase slots: all nine BO3 placements, including repaired six.
    # ------------------------------------------------------------------
    purchases: list[dict[str, Any]] = []
    for slot in wallbuy["purchase_slots"]:
        ue = slot["interaction_location_ue_cm"]
        purchases.append({
            "id": slot["id"],
            "name": slot["canonical"],
            "type": (
                "wall_buy"
                if slot["type"] in {"weapon", "wallbuy"}
                else ("weapon_cabinet" if slot["type"] == "sniper_cabinet" else "equipment_buy")
            ),
            "transform": {
                "position": lower_vec_to_xziel_m(ue),
                "sourcePositionUEcm": ue,
                "sourceRotationUE": None,
                "sourceScale": None,
            },
            "source": (
                "pavlov_functional_actor"
                if not slot["reconstructed"]
                else "bo3_derived_chalk_geometry_reconstruction"
            ),
            "enabledProfiles": ["bo3_chronicles", "pavlov_extended"],
            "properties": {
                "canonical": slot["canonical"],
                "bo3WeaponId": slot["bo3_weapon_id"],
                "pavlovWeaponId": slot["pavlov_weapon_id"],
                "price": slot["price"],
                "chalkAsset": slot["chalk_asset"],
                "interactionRadiusCm": slot["interaction_radius_cm"],
                "reconstructed": slot["reconstructed"],
                "functionalActor": slot["functional_actor"],
            },
            "replicationPolicy": "server_authoritative",
        })

    # ------------------------------------------------------------------
    # Doors and utility actors.
    # ------------------------------------------------------------------
    doors: list[dict[str, Any]] = []
    utility_entities: list[dict[str, Any]] = []
    player_spawns: list[dict[str, Any]] = []
    for ai in actor_indices:
        cls = actor_class(ai)
        actor = exports[ai - 1]
        p = prop_map(actor)
        if "/BuyableDoor/" in cls or "/BuyableDoor_Child/" in cls:
            doors.append({
                "id": id_for("door", actor.get("ObjectName"), ai),
                "name": actor.get("ObjectName"),
                "type": "buyable_door",
                "transform": actor_transform(ai),
                "source": "pavlov_port_spatial_reference",
                "enabledProfiles": ["bo3_chronicles", "pavlov_extended"],
                "properties": {
                    "price": scalar(actor, "Price"),
                    "zombieSpawnerFlags": int_array(actor, "ZombieSpawnerFlags"),
                    "moveToOpenUE": clean(struct_value(p.get("MoveToOpen"))),
                    "rotateToOpenUE": clean(struct_value(p.get("RotateToOpen"))),
                    "canonicalZoneEdgePending": True,
                },
                "replicationPolicy": "server_authoritative",
            })
        elif "MysteryBoxLocation" in cls:
            utility_entities.append({
                "id": id_for("mystery_box", actor.get("ObjectName"), ai),
                "name": actor.get("ObjectName"),
                "type": "mystery_box_anchor",
                "transform": actor_transform(ai),
                "source": "pavlov_port_spatial_reference",
                "enabledProfiles": ["bo3_chronicles", "pavlov_extended"],
                "properties": {"alwaysSpawnHereFirst": bool(scalar(actor, "AlwaySpawnHereFirst"))},
                "replicationPolicy": "server_authoritative",
            })
        elif "WonderFizz" in cls:
            utility_entities.append({
                "id": id_for("wunderfizz", actor.get("ObjectName"), ai),
                "name": actor.get("ObjectName"),
                "type": "wunderfizz",
                "transform": actor_transform(ai),
                "source": "pavlov_port_spatial_reference",
                "enabledProfiles": ["bo3_chronicles", "pavlov_extended"],
                "properties": {"price": scalar(actor, "Price")},
                "replicationPolicy": "server_authoritative",
            })
        elif "MachineGumball" in cls:
            utility_entities.append({
                "id": id_for("gobblegum", actor.get("ObjectName"), ai),
                "name": actor.get("ObjectName"),
                "type": "gobblegum_machine",
                "transform": actor_transform(ai),
                "source": "pavlov_port_spatial_reference",
                "enabledProfiles": ["bo3_chronicles", "pavlov_extended"],
                "properties": {},
                "replicationPolicy": "server_authoritative",
            })
        elif "PunchAPack" in cls:
            utility_entities.append({
                "id": id_for("pap", actor.get("ObjectName"), ai),
                "name": actor.get("ObjectName"),
                "type": "pack_a_punch",
                "transform": actor_transform(ai),
                "source": "pavlov_extension",
                "enabledProfiles": ["pavlov_extended"],
                "properties": {"canonicalBo3Nacht": False},
                "replicationPolicy": "server_authoritative",
            })
        elif "PerkMachine_QuickRevive" in cls:
            utility_entities.append({
                "id": id_for("quickrevive", actor.get("ObjectName"), ai),
                "name": actor.get("ObjectName"),
                "type": "perk_machine",
                "transform": actor_transform(ai),
                "source": "pavlov_extension",
                "enabledProfiles": ["pavlov_extended"],
                "properties": {
                    "perk": "specialty_quickrevive",
                    "canonicalBo3NachtStandaloneMachine": False,
                },
                "replicationPolicy": "server_authoritative",
            })
        elif cls.endswith("/Pavlov_Spawn"):
            player_spawns.append({
                "id": id_for("player_spawn", actor.get("ObjectName"), ai),
                "name": actor.get("ObjectName"),
                "type": "player_spawn_candidate",
                "transform": actor_transform(ai),
                "source": "pavlov_port_spatial_reference",
                "enabledProfiles": ["bo3_chronicles", "pavlov_extended"],
                "properties": {"maxCanonicalPlayers": 4},
                "replicationPolicy": "server_authoritative",
            })

    # ------------------------------------------------------------------
    # Environment and collision reference layers.
    # ------------------------------------------------------------------
    env_needles = (
        "/PointLight", "/SpotLight", "/DirectionalLight", "/SkyLight",
        "/ExponentialHeightFog", "/SphereReflectionCapture", "/Emitter",
        "FlickerLight", "Flickerfire", "BP_Sky_Sphere",
    )
    environment: list[dict[str, Any]] = []
    for ai in actor_indices:
        cls = actor_class(ai)
        if not any(n.lower() in cls.lower() for n in env_needles):
            continue
        root_idx, root = root_component(ai)
        rp = prop_map(root) if root else {}
        actor = exports[ai - 1]
        environment.append({
            "id": id_for("env", actor.get("ObjectName"), ai),
            "name": actor.get("ObjectName"),
            "class": cls,
            "transform": actor_transform(ai),
            "source": "pavlov_port_spatial_reference",
            "properties": {
                "intensity": clean(rp.get("Intensity", {}).get("Value")) if rp.get("Intensity") else None,
                "intensityUnits": clean(rp.get("IntensityUnits", {}).get("Value")) if rp.get("IntensityUnits") else None,
                "attenuationRadius": clean(rp.get("AttenuationRadius", {}).get("Value")) if rp.get("AttenuationRadius") else None,
                "lightColor": clean(struct_value(rp.get("LightColor"))),
            },
        })

    collision_needles = (
        "PlayerBlocker", "/BlockingVolume", "/NavMeshBoundsVolume",
        "/RecastNavMesh", "/PrecomputedVisibilityVolume",
    )
    collision: list[dict[str, Any]] = []
    for ai in actor_indices:
        cls = actor_class(ai)
        if not any(n.lower() in cls.lower() for n in collision_needles):
            continue
        actor = exports[ai - 1]
        collision.append({
            "id": id_for("collision", actor.get("ObjectName"), ai),
            "name": actor.get("ObjectName"),
            "class": cls,
            "transform": actor_transform(ai),
            "source": "pavlov_port_spatial_reference",
        })

    zones = [
        {
            "id": "start_zone",
            "name": "start_zone",
            "source": "official_t7_decompiled_script",
            "initiallyActive": True,
            "neighbors": [
                {"zone": "box_zone", "flag": "start_2_box"},
                {"zone": "upstairs_zone", "flag": "start_2_upstairs"},
            ],
        },
        {
            "id": "box_zone",
            "name": "box_zone",
            "source": "official_t7_decompiled_script",
            "initiallyActive": False,
            "neighbors": [
                {"zone": "start_zone", "flag": "start_2_box"},
                {"zone": "upstairs_zone", "flag": "box_2_upstairs"},
            ],
        },
        {
            "id": "upstairs_zone",
            "name": "upstairs_zone",
            "source": "official_t7_decompiled_script",
            "initiallyActive": False,
            "neighbors": [
                {"zone": "start_zone", "flag": "start_2_upstairs"},
                {"zone": "box_zone", "flag": "box_2_upstairs"},
            ],
        },
    ]

    profiles = {
        "bo3_chronicles": {
            "description": "BO3 Zombies Chronicles reference profile; Pavlov-only additions remain disabled.",
            "zombieAiLimit": 24,
            "maxPlayers": 4,
            "hellhoundSpawnersEnabled": False,
            "packAPunchMachineEnabled": False,
            "standaloneQuickReviveMachineEnabled": False,
            "wunderfizzEnabled": True,
            "gobblegumEnabled": True,
            "wallBuyCount": 9,
        },
        "pavlov_extended": {
            "description": "Full community-port actor layer retained for engine stress/feature testing.",
            "zombieAiLimit": 24,
            "maxPlayers": 4,
            "hellhoundSpawnersEnabled": True,
            "packAPunchMachineEnabled": True,
            "standaloneQuickReviveMachineEnabled": True,
            "wunderfizzEnabled": True,
            "gobblegumEnabled": True,
            "wallBuyCount": 9,
        },
    }

    entities = barricades + purchases + doors + utility_entities
    spawns = player_spawns + zombie_spawns + hound_spawns

    map_doc = {
        "schemaVersion": 1,
        "id": "nacht_bo3_reference",
        "displayName": "Nacht der Untoten — BO3 Reference",
        "coordinateSystem": {
            "units": "meters",
            "basis": "X, -Y, Z from Unreal centimeters",
            "source": "UE4.21 cooked map",
        },
        "sceneInstances": "scene_instances.json",
        "assets": "assets.json",
        "entities": "entities.json",
        "spawns": "spawns.json",
        "zones": "zones.json",
        "environment": "environment.json",
        "collision": "collision.json",
        "profiles": "profiles.json",
        "defaultProfile": "bo3_chronicles",
        "referenceOnly": True,
    }

    manifest = {
        "id": "nacht_bo3_reference",
        "schemaVersion": 1,
        "source": {
            "workshopId": "2755515831",
            "pavlovMap": "Nacht_de_Untoten.umap",
            "bo3InternalMapName": "zm_prototype",
            "officialT7Script": "scripts/zm/zm_prototype.gsc",
        },
        "authority": {
            "zonesAndAiLimit": "official_t7_decompiled_script",
            "purchaseIdentityAndPrices": "BO3 Chronicles references + baked purchase chalks",
            "geometryAndPlacements": "Pavlov community port credited to BO1/BO3 geometry/models",
            "pavlovGameplayActors": "reference_only_unless_enabled_by_profile",
        },
        "redistribution": {
            "thirdPartyAssetPayloadCommitted": False,
            "metadataOnly": True,
        },
    }

    assets = {
        "schemaVersion": 1,
        "uniqueMeshCount": len(unique_meshes),
        "meshes": [
            {"id": f"mesh_{i:04d}", "sourcePath": mesh}
            for i, mesh in enumerate(unique_meshes)
        ],
        "materialContract": {
            "sourceAudit": "Pavlov BO3 Nacht Material Channel Audit",
            "expectedChannels": ["Diffuse", "Normal"],
            "optionalChannels": ["SpecPower"],
            "note": "XZIEL renderer must preserve at least diffuse + normal for this reference.",
        },
    }

    preflight_errors: list[str] = []
    if len(scene_instances) < 10000:
        preflight_errors.append(f"scene instances unexpectedly low: {len(scene_instances)}")
    if len(unique_meshes) < 450:
        preflight_errors.append(f"unique meshes unexpectedly low: {len(unique_meshes)}")
    if len(barricades) != 12:
        preflight_errors.append(f"expected 12 barricades, got {len(barricades)}")
    if len(zombie_spawns) != 21:
        preflight_errors.append(f"expected 21 zombie spawns, got {len(zombie_spawns)}")
    if len(purchases) != 9:
        preflight_errors.append(f"expected 9 BO3 purchase slots, got {len(purchases)}")
    anchor_count = len(purchase_doc.get("anchors", []))
    if not anchor_count:
        anchor_count = int(
            purchase_doc.get("summary", {}).get("functional_actor_slots", 0)
        )
    if anchor_count != 3:
        preflight_errors.append(
            f"purchase calibration expected 3 functional anchors, got {anchor_count}"
        )
    calibration_error = purchase_doc.get("validation", {}).get(
        "max_anchor_error_cm"
    )
    if calibration_error is None:
        calibration_error = purchase_doc.get("summary", {}).get(
            "calibration_rmse_cm",
            purchase_doc.get("calibration", {}).get("rmse_cm"),
        )
    if calibration_error is None or float(calibration_error) > 10.0:
        preflight_errors.append(
            f"purchase anchor/calibration error exceeds 10 cm: {calibration_error}"
        )

    preflight = {
        "ok": not preflight_errors,
        "errors": preflight_errors,
        "counts": {
            "sceneInstances": len(scene_instances),
            "uniqueMeshes": len(unique_meshes),
            "barricades": len(barricades),
            "zombieSpawns": len(zombie_spawns),
            "houndSpawnsPavlovExtension": len(hound_spawns),
            "playerSpawnCandidates": len(player_spawns),
            "purchaseSlots": len(purchases),
            "doors": len(doors),
            "utilityEntities": len(utility_entities),
            "environmentActors": len(environment),
            "collisionActors": len(collision),
            "zones": len(zones),
        },
        "wallBuyValidation": purchase_doc.get("validation") or {
            "calibration": purchase_doc.get("calibration"),
            "summary": purchase_doc.get("summary"),
        },
    }

    files = {
        "map.json": map_doc,
        "manifest.json": manifest,
        "scene_instances.json": {"schemaVersion": 1, "instances": scene_instances},
        "assets.json": assets,
        "entities.json": {"schemaVersion": 1, "entities": entities},
        "spawns.json": {"schemaVersion": 1, "spawns": spawns},
        "zones.json": {"schemaVersion": 1, "zones": zones},
        "environment.json": {"schemaVersion": 1, "actors": environment},
        "collision.json": {"schemaVersion": 1, "actors": collision},
        "profiles.json": {"schemaVersion": 1, "profiles": profiles},
        "preflight.json": preflight,
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (args.out_dir / name).write_text(
            json.dumps(data, indent=2) + "\n",
            encoding="utf-8",
        )

    print(json.dumps(preflight, indent=2))
    return 0 if preflight["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())