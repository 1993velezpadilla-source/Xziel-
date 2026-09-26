#!/usr/bin/env python3
"""Build the complete calibrated BO3 Nacht purchase manifest.

The Pavlov community port contains nine BO3 purchase chalk meshes but only
three functional WallBuy_C actors.  We use those three real actors as spatial
anchors, fit the glTF->UE transform, and resolve the six omitted interactions.

Metadata only: no third-party mesh, texture, audio, or other payload is copied.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

PURCHASES = {
    "arak": ("KN-44", "wallbuy", "ar_standard", "kn44", 1400, "spawn"),
    "argus": ("Argus", "wallbuy", "shotgun_precision", "argus", 1100, "help_2f"),
    "frag": ("Fragmentation Grenades", "equipment", "frag_grenade", "frag", 250, "grenade_room"),
    "krm": ("KRM-262", "wallbuy", "shotgun_pump", "krm", 750, "help_1f"),
    "kuda": ("Kuda", "wallbuy", "smg_standard", "kuda", 1250, "help_1f"),
    "locus_decal": ("Locus", "sniper_cabinet", "sniper_fastbolt", "locus", 5000, "help_2f"),
    "pharaoh": ("Pharo", "wallbuy", "smg_burst", "pharaoh", 700, "grenade_room"),
    "shiva": ("Sheiva", "wallbuy", "ar_marksman", "shiva", 500, "spawn"),
    "triton": ("RK5", "wallbuy", "pistol_burst", "triton", 500, "spawn"),
}

ANCHORS = {"kn44": "arak", "kuda": "kuda", "triton": "triton"}


def pmap(export: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        p["Name"]: p
        for p in export.get("Data", [])
        if isinstance(p, dict) and isinstance(p.get("Name"), str)
    }


def structv(prop: dict[str, Any] | None) -> Any:
    if not prop:
        return None
    value = prop.get("Value")
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0].get("Value")
    return value


def vec(value: Any) -> dict[str, float] | None:
    if not isinstance(value, dict):
        return None

    def f(key: str) -> float:
        raw = value.get(key, 0)
        return 0.0 if raw == "+0" else float(raw)

    return {"x": f("X"), "y": f("Y"), "z": f("Z")}


def map_wallbuys(path: Path) -> list[dict[str, Any]]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    exports = doc["Exports"]
    imports = doc["Imports"]

    def resolve(index: int) -> str:
        if not index:
            return ""
        out: list[str] = []
        seen: set[int] = set()
        while index and index not in seen:
            seen.add(index)
            obj = imports[-index - 1] if index < 0 else exports[index - 1]
            out.append(str(obj.get("ObjectName", "?")))
            index = int(obj.get("OuterIndex", 0) or 0)
        return "/".join(reversed(out))

    level_index = next(
        i + 1
        for i, export in enumerate(exports)
        if "LevelExport" in str(export.get("$type", ""))
    )

    rows: list[dict[str, Any]] = []
    for actor_index in [
        x for x in exports[level_index - 1].get("Actors", [])
        if isinstance(x, int) and x > 0
    ]:
        actor = exports[actor_index - 1]
        actor_class = resolve(int(actor.get("ClassIndex", 0) or 0))
        if not actor_class.endswith("/WallBuy_C"):
            continue

        props = pmap(actor)
        root = props.get("RootComponent", {}).get("Value")
        location = rotation = None
        if isinstance(root, int) and root > 0:
            component_props = pmap(exports[root - 1])
            location = vec(structv(component_props.get("RelativeLocation")))
            rotation = structv(component_props.get("RelativeRotation"))

        rows.append({
            "actor": actor.get("ObjectName"),
            "weapon_id": props.get("WeaponID", {}).get("Value"),
            "price": props.get("Price", {}).get("Value"),
            "location": location,
            "rotation": rotation,
        })

    return rows


def source_basis(center: list[float]) -> list[float]:
    """UModel glTF -> UE axis order before fitted scale/translation."""
    x, y, z = [float(v) for v in center]
    return [x, z, y]


def fit_similarity(
    source_points: list[list[float]],
    target_points: list[list[float]],
) -> tuple[float, list[float], float, list[list[float]]]:
    """Fit target ~= uniform_scale * source + translation."""
    count = len(source_points)
    source_mean = [
        sum(p[axis] for p in source_points) / count
        for axis in range(3)
    ]
    target_mean = [
        sum(p[axis] for p in target_points) / count
        for axis in range(3)
    ]

    numerator = 0.0
    denominator = 0.0
    for source, target in zip(source_points, target_points):
        for axis in range(3):
            ds = source[axis] - source_mean[axis]
            dt = target[axis] - target_mean[axis]
            numerator += ds * dt
            denominator += ds * ds

    if denominator <= 0.0:
        raise ValueError("degenerate anchor geometry")

    scale = numerator / denominator
    translation = [
        target_mean[axis] - scale * source_mean[axis]
        for axis in range(3)
    ]
    predicted = [
        [
            scale * source[axis] + translation[axis]
            for axis in range(3)
        ]
        for source in source_points
    ]
    rmse = math.sqrt(
        sum(
            sum((pred[axis] - target[axis]) ** 2 for axis in range(3))
            for pred, target in zip(predicted, target_points)
        ) / count
    )
    return scale, translation, rmse, predicted


def calibrated_position(
    center: list[float],
    scale: float,
    translation: list[float],
) -> dict[str, float]:
    basis = source_basis(center)
    return {
        axis: scale * basis[i] + translation[i]
        for i, axis in enumerate(("x", "y", "z"))
    }


def ue_to_xziel(position: dict[str, float]) -> dict[str, float]:
    return {
        "x": round(position["x"] / 100.0, 6),
        "y": round(-position["y"] / 100.0, 6),
        "z": round(position["z"] / 100.0, 6),
    }


def surface_normal(thin_axis: str | None) -> dict[str, float]:
    # source basis is [gltf.x, gltf.z, gltf.y] -> UE [x,y,z].
    axis = {"x": "x", "z": "y", "y": "z"}.get(str(thin_axis).lower(), "x")
    return {
        "x": 1.0 if axis == "x" else 0.0,
        "y": 1.0 if axis == "y" else 0.0,
        "z": 1.0 if axis == "z" else 0.0,
    }


def yaw_candidates(normal: dict[str, float]) -> list[float]:
    if abs(normal["y"]) > abs(normal["x"]):
        return [90.0, 270.0]
    return [0.0, 180.0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("map_json", type=Path)
    ap.add_argument("bounds_json", type=Path)
    ap.add_argument("out_json", type=Path)
    args = ap.parse_args()

    wallbuys = map_wallbuys(args.map_json)
    by_id = {
        row["weapon_id"]: row
        for row in wallbuys
        if row.get("weapon_id")
    }
    bounds_doc = json.loads(args.bounds_json.read_text(encoding="utf-8"))
    bounds = bounds_doc["chalks"]

    missing_anchors = [wid for wid in ANCHORS if wid not in by_id]
    if missing_anchors:
        raise SystemExit("missing functional anchors: " + ", ".join(missing_anchors))

    source_points: list[list[float]] = []
    target_points: list[list[float]] = []
    anchor_keys: list[str] = []
    for weapon_id, chalk_key in ANCHORS.items():
        source_points.append(source_basis(bounds[chalk_key]["center"]))
        actual = by_id[weapon_id]["location"]
        target_points.append([actual["x"], actual["y"], actual["z"]])
        anchor_keys.append(chalk_key)

    scale, translation, rmse, predicted = fit_similarity(
        source_points,
        target_points,
    )

    anchors: list[dict[str, Any]] = []
    for i, (weapon_id, chalk_key) in enumerate(ANCHORS.items()):
        actual = by_id[weapon_id]["location"]
        pred = {
            "x": predicted[i][0],
            "y": predicted[i][1],
            "z": predicted[i][2],
        }
        target = [actual["x"], actual["y"], actual["z"]]
        error = math.sqrt(
            sum((predicted[i][axis] - target[axis]) ** 2 for axis in range(3))
        )
        anchors.append({
            "weapon_id": weapon_id,
            "chalk": chalk_key,
            "predicted_location_ue_cm": pred,
            "functional_actor_location_ue_cm": actual,
            "error_cm": error,
        })

    slots: list[dict[str, Any]] = []
    for key, (name, kind, bo3_id, pavlov_id, price, room_group) in PURCHASES.items():
        predicted_position = calibrated_position(
            bounds[key]["center"],
            scale,
            translation,
        )
        existing = by_id.get(pavlov_id)
        interaction_position = existing["location"] if existing else predicted_position
        normal = surface_normal(bounds[key].get("thin_axis"))
        yaws = yaw_candidates(normal)

        slots.append({
            "id": "purchase_" + key,
            "canonical": name,
            "type": kind,
            "bo3_weapon_id": bo3_id,
            "pavlov_weapon_id": pavlov_id,
            "price": price,
            "room_group": room_group,
            "source_marker": key,
            "chalk_asset": "zm_prototype_part4_t7_zm_chalk_buy_" + key,
            "functional_actor": existing["actor"] if existing else None,
            "functional_actor_price": existing["price"] if existing else None,
            "interaction_location_ue_cm": interaction_position,
            "interaction_location_xziel_m": ue_to_xziel(interaction_position),
            "authored_rotation_ue": existing["rotation"] if existing else None,
            "surface_normal_ue": normal,
            "yaw_candidates_ue_deg": yaws,
            "orientation_policy": (
                "use authored actor rotation"
                if existing and existing.get("rotation")
                else "choose yaw candidate facing reachable/navmesh free space"
            ),
            "placement_source": (
                "functional_wallbuy_actor"
                if existing
                else "calibrated_marker_mesh_bounds"
            ),
            "placement_confidence": (
                "authoritative_port_actor"
                if existing
                else "geometry_derived"
            ),
            "reconstructed": existing is None,
            "needs_geometry_resolution": False,
            "interaction_radius_cm": 150.0,
            "replicationPolicy": "server_authoritative",
        })

    errors: list[str] = []
    if len(wallbuys) != 3:
        errors.append(f"expected 3 functional WallBuy_C actors, got {len(wallbuys)}")
    if len(bounds) != 9:
        errors.append(f"expected 9 chalks, got {len(bounds)}")
    if len(slots) != 9:
        errors.append(f"expected 9 purchase slots, got {len(slots)}")
    if rmse > 10.0:
        errors.append(f"calibration RMSE {rmse:.3f} cm > 10 cm")

    for slot in slots:
        if slot["functional_actor"] and slot["functional_actor_price"] != slot["price"]:
            errors.append(f'{slot["canonical"]} functional price mismatch')
        if slot["needs_geometry_resolution"]:
            errors.append(f'{slot["canonical"]} is unresolved')

    output = {
        "schema": 2,
        "authority": (
            "BO3 Zombies Chronicles purchase layout reconstructed from Pavlov "
            "Workshop 2755515831 metadata and preserved chalk geometry. Three "
            "functional WallBuy_C actors are authoritative anchors; six omitted "
            "interactions are derived by calibrated marker geometry. This is not "
            "Treyarch source data."
        ),
        "source": {
            "map": "Nacht_de_Untoten.umap",
            "workshop_id": "2755515831",
            "engine": "UE4.21",
            "bounds_source": args.bounds_json.as_posix(),
        },
        "coordinate_system": {
            "source": "UModel glTF meters calibrated against UE actor centimeters",
            "xziel": "meters, Z-up, source UE Y reflected",
            "conversion": "XZIEL=(UE.x/100,-UE.y/100,UE.z/100)",
        },
        "calibration": {
            "perm": [0, 2, 1],
            "signs": [1, 1, 1],
            "scale": scale,
            "translation": translation,
            "rmse_cm": rmse,
            "anchors": anchor_keys,
            "anchor_diagnostics": anchors,
        },
        "validation": {
            "slot_count": len(slots),
            "functional_actor_slots": sum(
                1 for slot in slots
                if slot["placement_source"] == "functional_wallbuy_actor"
            ),
            "geometry_derived_slots": sum(
                1 for slot in slots
                if slot["placement_source"] == "calibrated_marker_mesh_bounds"
            ),
            "weapon_or_cabinet_slots": sum(
                1 for slot in slots
                if slot["type"] in {"wallbuy", "sniper_cabinet"}
            ),
            "equipment_slots": sum(
                1 for slot in slots
                if slot["type"] == "equipment"
            ),
            "unresolved_slot_count": sum(
                1 for slot in slots
                if slot["needs_geometry_resolution"]
            ),
            "validation_error_count": len(errors),
            "gate": "PASS" if not errors else "FAIL",
        },
        "purchase_slots": slots,
        "validation_errors": errors,
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(output, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(output["validation"], indent=2))
    print(json.dumps({
        "scale": scale,
        "translation": translation,
        "rmse_cm": rmse,
    }, indent=2))
    for slot in slots:
        print(
            f'{slot["canonical"]:24s} '
            f'{slot["price"]:4d} '
            f'{slot["placement_source"]:30s} '
            f'{slot["interaction_location_ue_cm"]}'
        )

    if errors:
        for error in errors:
            print("VALIDATION_ERROR:", error)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
