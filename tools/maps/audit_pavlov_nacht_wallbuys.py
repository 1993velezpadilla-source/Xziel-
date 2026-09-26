#!/usr/bin/env python3
"""Audit and reconstruct the complete BO3 Zombies Chronicles Nacht purchase set.

The Pavlov Nacht port preserves all nine BO3 purchase chalk meshes but only
instantiates three functional WallBuy_C actors.  This tool uses those three
functional instances as anchors and the baked world-space bounds of all nine
chalk meshes to build a reproducible repair plan for XZIEL.

It writes metadata only; it does not copy third-party mesh/texture payloads.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


PURCHASES = {
    "arak": {
        "canonical": "KN-44",
        "kind": "weapon",
        "bo3_weapon_id": "ar_standard",
        "pavlov_weapon_id": "kn44",
        "price": 1400,
    },
    "argus": {
        "canonical": "Argus",
        "kind": "weapon",
        "bo3_weapon_id": "shotgun_precision",
        "pavlov_weapon_id": "argus",
        "price": 1100,
    },
    "frag": {
        "canonical": "Fragmentation Grenades",
        "kind": "equipment",
        "bo3_weapon_id": "frag_grenade",
        "pavlov_weapon_id": "frag",
        "price": 250,
    },
    "krm": {
        "canonical": "KRM-262",
        "kind": "weapon",
        "bo3_weapon_id": "shotgun_pump",
        "pavlov_weapon_id": "krm",
        "price": 750,
    },
    "kuda": {
        "canonical": "Kuda",
        "kind": "weapon",
        "bo3_weapon_id": "smg_standard",
        "pavlov_weapon_id": "kuda",
        "price": 1250,
    },
    "locus_decal": {
        "canonical": "Locus",
        "kind": "sniper_cabinet",
        "bo3_weapon_id": "sniper_fastbolt",
        "pavlov_weapon_id": "locus",
        "price": 5000,
    },
    "pharaoh": {
        "canonical": "Pharo",
        "kind": "weapon",
        "bo3_weapon_id": "smg_burst",
        "pavlov_weapon_id": "pharaoh",
        "price": 700,
    },
    "shiva": {
        "canonical": "Sheiva",
        "kind": "weapon",
        "bo3_weapon_id": "ar_marksman",
        "pavlov_weapon_id": "shiva",
        "price": 500,
    },
    "triton": {
        "canonical": "RK5",
        "kind": "weapon",
        "bo3_weapon_id": "pistol_burst",
        "pavlov_weapon_id": "triton",
        "price": 500,
    },
}

# The three actual WallBuy_C instances present in the Pavlov port.
ANCHOR_BY_PAVLOV_ID = {
    "kn44": "arak",
    "kuda": "kuda",
    "triton": "triton",
}


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


def clean_vector(value: Any) -> dict[str, float] | None:
    if not isinstance(value, dict):
        return None
    try:
        return {
            "x": float(0 if value.get("X") == "+0" else value.get("X", 0)),
            "y": float(0 if value.get("Y") == "+0" else value.get("Y", 0)),
            "z": float(0 if value.get("Z") == "+0" else value.get("Z", 0)),
        }
    except (TypeError, ValueError):
        return None


def vector_distance(a: dict[str, float], b: dict[str, float]) -> float:
    return math.sqrt(
        (a["x"] - b["x"]) ** 2
        + (a["y"] - b["y"]) ** 2
        + (a["z"] - b["z"]) ** 2
    )


def iter_bounds_candidates(node: Any, path: str = ""):
    """Yield any JSON object shaped like an Unreal FBoxSphereBounds."""
    if isinstance(node, dict):
        keys = {str(k).lower(): k for k in node}
        if "origin" in keys and ("boxextent" in keys or "box_extent" in keys):
            origin = clean_vector(node[keys["origin"]])
            extent_key = keys.get("boxextent", keys.get("box_extent"))
            extent = clean_vector(node[extent_key]) if extent_key else None
            if origin is not None and extent is not None:
                yield {
                    "path": path or "/",
                    "origin": origin,
                    "box_extent": extent,
                    "sphere_radius": node.get(
                        keys.get("sphereradius", "SphereRadius")
                    ),
                }
        for k, v in node.items():
            yield from iter_bounds_candidates(v, f"{path}/{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from iter_bounds_candidates(v, f"{path}[{i}]")


def choose_bounds(doc: dict[str, Any]) -> dict[str, Any] | None:
    candidates = list(iter_bounds_candidates(doc))
    if not candidates:
        return None

    # Prefer serialized export bounds over incidental nested/physics bounds.
    def score(c: dict[str, Any]) -> tuple[int, float]:
        p = c["path"].lower()
        s = 0
        if "/bounds" in p:
            s += 10
        if "export" in p:
            s += 4
        if "bodysetup" in p or "agggeom" in p or "collision" in p:
            s -= 8
        e = c["box_extent"]
        volume_hint = abs(e["x"] * e["y"] * e["z"])
        return (s, volume_hint)

    return max(candidates, key=score)


def load_map_wallbuys(map_json: Path) -> list[dict[str, Any]]:
    doc = json.loads(map_json.read_text(encoding="utf-8-sig"))
    exports: list[dict[str, Any]] = doc["Exports"]
    imports: list[dict[str, Any]] = doc["Imports"]

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

    level_index = next(
        i + 1 for i, e in enumerate(exports)
        if "LevelExport" in str(e.get("$type", ""))
    )
    actor_indices = [
        x for x in exports[level_index - 1].get("Actors", [])
        if isinstance(x, int) and x > 0
    ]

    rows: list[dict[str, Any]] = []
    for actor_index in actor_indices:
        actor = exports[actor_index - 1]
        actor_class = resolve_index(int(actor.get("ClassIndex", 0) or 0)) or ""
        if not actor_class.endswith("/WallBuy_C"):
            continue
        props = property_map(actor)
        root = props.get("RootComponent", {}).get("Value")
        location = rotation = scale = None
        if isinstance(root, int) and root > 0:
            cp = property_map(exports[root - 1])
            location = clean_vector(struct_value(cp.get("RelativeLocation")))
            rotation = struct_value(cp.get("RelativeRotation"))
            scale = clean_vector(struct_value(cp.get("RelativeScale3D")))

        weapon_id = props.get("WeaponID", {}).get("Value")
        rows.append({
            "actor_export_index": actor_index,
            "actor_name": actor.get("ObjectName"),
            "actor_class": actor_class,
            "pavlov_weapon_id": weapon_id,
            "canonical": PURCHASES[
                ANCHOR_BY_PAVLOV_ID[weapon_id]
            ]["canonical"] if weapon_id in ANCHOR_BY_PAVLOV_ID else None,
            "price": props.get("Price", {}).get("Value"),
            "location": location,
            "rotation": rotation,
            "scale": scale,
        })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("map_json", type=Path)
    ap.add_argument("chalk_json_dir", type=Path)
    ap.add_argument("output_json", type=Path)
    args = ap.parse_args()

    functional = load_map_wallbuys(args.map_json)
    functional_by_id = {
        row["pavlov_weapon_id"]: row
        for row in functional
        if row.get("pavlov_weapon_id")
    }

    chalks: dict[str, dict[str, Any]] = {}
    for key in PURCHASES:
        p = args.chalk_json_dir / f"{key}.json"
        if not p.exists():
            raise SystemExit(f"missing chalk JSON: {p}")
        doc = json.loads(p.read_text(encoding="utf-8-sig"))
        bounds = choose_bounds(doc)
        chalks[key] = {
            "asset": f"zm_prototype_part4_t7_zm_chalk_buy_{key}",
            "bounds": bounds,
        }

    anchor_rows: list[dict[str, Any]] = []
    for pavlov_id, chalk_key in ANCHOR_BY_PAVLOV_ID.items():
        actor = functional_by_id.get(pavlov_id)
        bounds = chalks[chalk_key].get("bounds")
        row = {
            "chalk": chalk_key,
            "actor": actor,
            "bounds": bounds,
            "distance_actor_to_bounds_origin": None,
        }
        if actor and actor.get("location") and bounds:
            row["distance_actor_to_bounds_origin"] = vector_distance(
                actor["location"], bounds["origin"]
            )
        anchor_rows.append(row)

    valid_anchor_distances = [
        r["distance_actor_to_bounds_origin"]
        for r in anchor_rows
        if isinstance(r.get("distance_actor_to_bounds_origin"), (int, float))
    ]

    # A chalk's baked bounds origin is the best available ground truth for the
    # six omitted Pavlov triggers.  The three existing functional actors are
    # retained as validation anchors; no position is guessed from screenshots.
    slots: list[dict[str, Any]] = []
    for key, meta in PURCHASES.items():
        functional_actor = functional_by_id.get(meta["pavlov_weapon_id"])
        bounds = chalks[key].get("bounds")
        if functional_actor is not None:
            location = functional_actor.get("location")
            placement_source = "functional_wallbuy_actor"
            reconstructed = False
        elif bounds is not None:
            location = bounds["origin"]
            placement_source = "chalk_mesh_baked_bounds_origin"
            reconstructed = True
        else:
            location = None
            placement_source = "unresolved"
            reconstructed = True

        slots.append({
            "id": f"purchase_{key}",
            **meta,
            "chalk_key": key,
            "chalk_asset": chalks[key]["asset"],
            "chalk_bounds": bounds,
            "functional_actor": functional_actor,
            "interaction_location": location,
            "placement_source": placement_source,
            "reconstructed": reconstructed,
            "interaction_radius": 150.0,
            "replication_policy": "server_authoritative",
        })

    validation_errors: list[str] = []
    if len(functional) != 3:
        validation_errors.append(
            f"expected exactly 3 functional Pavlov WallBuy_C actors, got {len(functional)}"
        )
    if len(chalks) != 9:
        validation_errors.append(f"expected 9 chalk assets, got {len(chalks)}")
    missing_bounds = [k for k, v in chalks.items() if not v.get("bounds")]
    if missing_bounds:
        validation_errors.append(
            "no serialized bounds found for chalk assets: " + ", ".join(missing_bounds)
        )
    unresolved = [r["id"] for r in slots if r["interaction_location"] is None]
    if unresolved:
        validation_errors.append(
            "unresolved interaction locations: " + ", ".join(unresolved)
        )

    report = {
        "schema": 1,
        "source": {
            "map": "Nacht_de_Untoten.umap",
            "engine": "UE4.21",
            "workshop_id": "2755515831",
            "note": (
                "Pavlov community port. All nine BO3 Chronicles chalk markers are "
                "present; only three WallBuy_C interactions were implemented."
            ),
        },
        "summary": {
            "expected_bo3_purchase_slots": 9,
            "functional_pavlov_wallbuys": len(functional),
            "reconstructed_slots": sum(1 for r in slots if r["reconstructed"]),
            "resolved_interaction_locations": sum(
                1 for r in slots if r["interaction_location"] is not None
            ),
            "anchor_distance_count": len(valid_anchor_distances),
            "anchor_distance_min": min(valid_anchor_distances) if valid_anchor_distances else None,
            "anchor_distance_max": max(valid_anchor_distances) if valid_anchor_distances else None,
            "anchor_distance_mean": (
                sum(valid_anchor_distances) / len(valid_anchor_distances)
                if valid_anchor_distances else None
            ),
            "validation_error_count": len(validation_errors),
        },
        "functional_wallbuys": functional,
        "anchor_validation": anchor_rows,
        "purchase_slots": slots,
        "validation_errors": validation_errors,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(report["summary"], indent=2))
    for row in slots:
        print(
            f'{row["canonical"]:24s} '
            f'price={row["price"]:4d} '
            f'source={row["placement_source"]} '
            f'location={row["interaction_location"]}'
        )
    if validation_errors:
        for e in validation_errors:
            print("VALIDATION_ERROR:", e)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
