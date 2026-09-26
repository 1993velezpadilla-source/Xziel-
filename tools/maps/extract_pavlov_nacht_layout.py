#!/usr/bin/env python3
"""Extract a reproducible spatial manifest from UAssetGUI JSON for the Pavlov BO3 Nacht port.

Input:
  UAssetGUI JSON generated from Nacht_de_Untoten.umap with UE4.21.

Output:
  JSON containing:
  - level actor inventory;
  - resolved actor classes;
  - static-mesh instance references;
  - root/component transforms;
  - gameplay actor placements.

This intentionally stores metadata/layout only, not third-party mesh/texture payloads.
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
from typing import Any


def property_map(export: dict[str, Any]) -> dict[str, dict[str, Any]]:
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


def clean_numeric_obj(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if k == "$type":
                continue
            out[k] = clean_numeric_obj(v)
        return out
    if isinstance(value, list):
        return [clean_numeric_obj(v) for v in value]
    if value == "+0":
        return 0.0
    return value


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("uasset_json", type=Path)
    ap.add_argument("output_json", type=Path)
    args = ap.parse_args()

    doc = json.loads(args.uasset_json.read_text(encoding="utf-8-sig"))
    exports: list[dict[str, Any]] = doc["Exports"]
    imports: list[dict[str, Any]] = doc["Imports"]

    level_index = next(
        i + 1 for i, e in enumerate(exports)
        if "LevelExport" in str(e.get("$type", ""))
    )
    level = exports[level_index - 1]
    actors = [
        x for x in level.get("Actors", [])
        if isinstance(x, int) and x > 0
    ]
    actor_set = set(actors)

    def resolve_index(index: int) -> str | None:
        if not index:
            return None
        seen: set[int] = set()
        parts: list[str] = []
        while index and index not in seen:
            seen.add(index)
            if index < 0:
                obj = imports[-index - 1]
            else:
                obj = exports[index - 1]
            parts.append(str(obj.get("ObjectName", "?")))
            index = int(obj.get("OuterIndex", 0) or 0)
        return "/".join(reversed(parts))

    def owner_actor_index(export_index: int) -> int | None:
        index = export_index
        seen: set[int] = set()
        while index > 0 and index not in seen:
            if index in actor_set:
                return index
            seen.add(index)
            index = int(exports[index - 1].get("OuterIndex", 0) or 0)
        return None

    def root_transform(actor: dict[str, Any]) -> dict[str, Any] | None:
        props = property_map(actor)
        root = props.get("RootComponent")
        if not root or not isinstance(root.get("Value"), int):
            return None
        root_index = root["Value"]
        if root_index <= 0:
            return None
        component = exports[root_index - 1]
        cp = property_map(component)
        return {
            "component_export_index": root_index,
            "component_name": component.get("ObjectName"),
            "location": clean_numeric_obj(struct_value(cp.get("RelativeLocation"))),
            "rotation": clean_numeric_obj(struct_value(cp.get("RelativeRotation"))),
            "scale": clean_numeric_obj(struct_value(cp.get("RelativeScale3D"))),
        }

    class_counts: collections.Counter[str] = collections.Counter()
    actor_rows: list[dict[str, Any]] = []
    for actor_index in actors:
        actor = exports[actor_index - 1]
        actor_class = resolve_index(int(actor.get("ClassIndex", 0) or 0)) or "UNKNOWN"
        class_counts[actor_class] += 1
        actor_rows.append({
            "export_index": actor_index,
            "name": actor.get("ObjectName"),
            "class": actor_class,
            "transform": root_transform(actor),
        })

    mesh_rows: list[dict[str, Any]] = []
    for export_index, export in enumerate(exports, start=1):
        props = property_map(export)
        static_mesh = props.get("StaticMesh")
        if not static_mesh:
            continue

        actor_index = owner_actor_index(export_index)
        if not actor_index:
            continue

        mesh_index = static_mesh.get("Value")
        if not isinstance(mesh_index, int) or mesh_index == 0:
            continue

        actor = exports[actor_index - 1]
        mesh_rows.append({
            "component_export_index": export_index,
            "component_name": export.get("ObjectName"),
            "actor_export_index": actor_index,
            "actor_name": actor.get("ObjectName"),
            "actor_class": resolve_index(int(actor.get("ClassIndex", 0) or 0)),
            "mesh": resolve_index(mesh_index),
            "relative_location": clean_numeric_obj(struct_value(props.get("RelativeLocation"))),
            "relative_rotation": clean_numeric_obj(struct_value(props.get("RelativeRotation"))),
            "relative_scale": clean_numeric_obj(struct_value(props.get("RelativeScale3D"))),
            "outer_path": resolve_index(int(export.get("OuterIndex", 0) or 0)),
        })

    gameplay_needles = (
        "ZombieSpawner",
        "Zombie_hounds_Spawner",
        "Barricade",
        "WallBuy",
        "MysteryBoxLocation",
        "BuyableDoor",
        "WonderFizz",
        "PerkMachine",
        "PunchAPack",
        "Pavlov_Spawn",
        "GameLogic",
    )
    gameplay = [
        row for row in actor_rows
        if any(needle.lower() in row["class"].lower() for needle in gameplay_needles)
    ]

    unique_meshes = sorted({row["mesh"] for row in mesh_rows if row["mesh"]})
    cod_nacht_rows = [
        row for row in mesh_rows
        if isinstance(row["mesh"], str) and "/CoD_nacht/" in row["mesh"]
    ]
    map_file_rows = [
        row for row in mesh_rows
        if isinstance(row["mesh"], str)
        and ("/MAP_FILES/" in row["mesh"] or "zm_prototype_part" in row["mesh"])
    ]

    map_file_decal_rows = [
        row for row in map_file_rows
        if isinstance(row["mesh"], str)
        and row["mesh"].rsplit("/", 1)[-1].lower().startswith("zm_prototype_part1_1_")
    ]
    map_file_structural_rows = [
        row for row in map_file_rows
        if row not in map_file_decal_rows
    ]

    # BO3 Zombies Chronicles Nacht purchase markers are preserved in imported
    # map geometry. The Pavlov port only instantiates three interactive
    # WallBuy_C actors, so that actor count is not authoritative for BO3.
    bo3_purchase_aliases = {
        # Internal asset marker -> canonical BO3 Zombies Chronicles purchase.
        # Prices are the Nacht Chronicles wall/cabinet/equipment prices.
        "arak": {"canonical": "KN-44", "kind": "weapon", "weapon_id": "kn44", "price": 1400},
        "argus": {"canonical": "Argus", "kind": "weapon", "weapon_id": "argus", "price": 1100},
        "frag": {"canonical": "Fragmentation Grenades", "kind": "equipment", "weapon_id": "frag", "price": 250},
        "krm": {"canonical": "KRM-262", "kind": "weapon", "weapon_id": "krm", "price": 750},
        "kuda": {"canonical": "Kuda", "kind": "weapon", "weapon_id": "kuda", "price": 1250},
        "locus_decal": {"canonical": "Locus", "kind": "sniper_cabinet", "weapon_id": "locus", "price": 5000},
        "pharaoh": {"canonical": "Pharo", "kind": "weapon", "weapon_id": "pharaoh", "price": 700},
        "shiva": {"canonical": "Sheiva", "kind": "weapon", "weapon_id": "shiva", "price": 500},
        "triton": {"canonical": "RK5", "kind": "weapon", "weapon_id": "triton", "price": 500},
    }
    bo3_purchase_markers = []
    for row in mesh_rows:
        mesh = row.get("mesh")
        if not isinstance(mesh, str):
            continue
        low = mesh.lower()
        marker_key = next(
            (
                key for key in bo3_purchase_aliases
                if f"chalk_buy_{key}" in low
            ),
            None,
        )
        if marker_key is None:
            continue
        meta = bo3_purchase_aliases[marker_key]
        bo3_purchase_markers.append({
            "source_marker": marker_key,
            "canonical": meta["canonical"],
            "kind": meta["kind"],
            "weapon_id": meta["weapon_id"],
            "price": meta["price"],
            "mesh": mesh,
            "actor_name": row.get("actor_name"),
            "relative_location": row.get("relative_location"),
            "relative_rotation": row.get("relative_rotation"),
            "relative_scale": row.get("relative_scale"),
            "note": (
                "Null/default transforms can mean placement is baked into the "
                "imported mesh vertices; resolve from mesh bounds during geometry export."
            ),
        })

    pavlov_wallbuy_actors = [
        row for row in actor_rows
        if row["class"].endswith("/WallBuy_C")
    ]

    # Preserve the real functional WallBuy_C instance data instead of treating
    # the three actor instances as the whole BO3 wall-buy set.
    functional_wallbuys = []
    for row in pavlov_wallbuy_actors:
        actor = exports[row["export_index"] - 1]
        props = property_map(actor)
        weapon_id = props.get("WeaponID", {}).get("Value")
        display_name_prop = props.get("DisplayName") or {}
        display_name = display_name_prop.get("CultureInvariantString")
        price = props.get("Price", {}).get("Value")
        canonical = next(
            (
                meta["canonical"]
                for meta in bo3_purchase_aliases.values()
                if meta["weapon_id"] == weapon_id
            ),
            display_name or str(weapon_id or "unknown"),
        )
        functional_wallbuys.append({
            **row,
            "weapon_id": weapon_id,
            "canonical": canonical,
            "display_name": display_name,
            "price": price,
        })

    functional_by_canonical = {
        row["canonical"]: row for row in functional_wallbuys
    }
    bo3_purchase_slots = []
    for marker in bo3_purchase_markers:
        functional = functional_by_canonical.get(marker["canonical"])
        transform = functional.get("transform") if functional else None
        marker_position = marker.get("relative_location")
        placement_source = (
            "functional_wallbuy_actor"
            if functional
            else ("marker_relative_transform" if marker_position else "mesh_bounds_pending")
        )
        bo3_purchase_slots.append({
            "id": "purchase_" + marker["source_marker"],
            "type": (
                "wallbuy"
                if marker["kind"] == "weapon"
                else marker["kind"]
            ),
            "canonical": marker["canonical"],
            "weapon_id": marker["weapon_id"],
            "price": marker["price"],
            "source_marker": marker["source_marker"],
            "marker_mesh": marker["mesh"],
            "functional_actor": functional["name"] if functional else None,
            "transform": transform,
            "marker_relative_location": marker_position,
            "placement_source": placement_source,
            "needs_geometry_resolution": not bool(functional),
            "replicationPolicy": "server_authoritative",
        })

    expected_functional = {
        "KN-44": 1400,
        "Kuda": 1250,
        "RK5": 500,
    }
    validation_errors = []
    if len(bo3_purchase_markers) != 9:
        validation_errors.append(
            f"expected 9 BO3 Nacht purchase markers, got {len(bo3_purchase_markers)}"
        )
    if sum(1 for r in bo3_purchase_markers if r["kind"] != "equipment") != 8:
        validation_errors.append("expected 8 BO3 Nacht weapon/cabinet purchase markers")
    if len(functional_wallbuys) != 3:
        validation_errors.append(
            f"expected 3 functional Pavlov WallBuy_C actors, got {len(functional_wallbuys)}"
        )
    for canonical, expected_price in expected_functional.items():
        row = functional_by_canonical.get(canonical)
        if row is None:
            validation_errors.append(f"missing functional WallBuy_C for {canonical}")
        elif row.get("price") != expected_price:
            validation_errors.append(
                f"{canonical} functional price {row.get('price')} != expected {expected_price}"
            )

    output = {
        "schema": 1,
        "source": {
            "map": "Nacht_de_Untoten.umap",
            "engine": "UE4.21",
            "workshop_id": "2755515831",
            "note": "Pavlov community port credited with BO1/BO3 map geometry/models; not Treyarch source.",
        },
        "summary": {
            "level_export_index": level_index,
            "level_actor_count": len(actor_rows),
            "actor_class_counts": dict(class_counts.most_common()),
            "static_mesh_instance_count": len(mesh_rows),
            "unique_static_mesh_count": len(unique_meshes),
            "cod_nacht_static_mesh_instance_count": len(cod_nacht_rows),
            "cod_nacht_unique_static_mesh_count": len({
                r["mesh"] for r in cod_nacht_rows if r["mesh"]
            }),
            "map_files_instance_count": len(map_file_rows),
            "map_files_unique_mesh_count": len({
                r["mesh"] for r in map_file_rows if r["mesh"]
            }),
            "map_files_structural_instance_count": len(map_file_structural_rows),
            "map_files_structural_unique_mesh_count": len({
                r["mesh"] for r in map_file_structural_rows if r["mesh"]
            }),
            "map_files_decal_instance_count": len(map_file_decal_rows),
            "map_files_decal_unique_mesh_count": len({
                r["mesh"] for r in map_file_decal_rows if r["mesh"]
            }),
            "bo3_purchase_marker_count": len(bo3_purchase_markers),
            "bo3_weapon_purchase_marker_count": sum(
                1 for r in bo3_purchase_markers if r["kind"] != "equipment"
            ),
            "pavlov_functional_wallbuy_actor_count": len(functional_wallbuys),
            "complete_purchase_slot_count": len(bo3_purchase_slots),
            "geometry_resolution_pending_purchase_slot_count": sum(
                1 for r in bo3_purchase_slots if r["needs_geometry_resolution"]
            ),
            "gameplay_actor_count": len(gameplay),
            "validation_error_count": len(validation_errors),
        },
        "bo3_reference_purchase_markers": bo3_purchase_markers,
        "bo3_purchase_slots": bo3_purchase_slots,
        "pavlov_functional_wallbuy_actors": functional_wallbuys,
        "validation_errors": validation_errors,
        "gameplay_actors": gameplay,
        "map_files_structural": map_file_structural_rows,
        "map_files_decals": map_file_decal_rows,
        "static_mesh_instances": mesh_rows,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(output, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output["summary"], indent=2))
    if validation_errors:
        for error in validation_errors:
            print("VALIDATION_ERROR:", error)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
