#!/usr/bin/env python3
"""Audit and reconstruct the incomplete wall-buy layer in the Pavlov BO3 Nacht port.

The port keeps BO3/Zombies-Chronicles chalk meshes for the wall purchases but
only instantiates three WallBuy blueprints.  This tool treats those three as
calibration anchors and emits metadata for all expected purchase surfaces.

It emits metadata only; no third-party asset payloads are copied.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

EXPECTED = {
    "triton": {
        "kind": "weapon",
        "weapon_id": "rk5",
        "display_name": "RK5",
        "price": 500,
        "room": "spawn",
    },
    "shiva": {
        "kind": "weapon",
        "weapon_id": "sheiva",
        "display_name": "Sheiva",
        "price": 500,
        "room": "spawn",
    },
    "kuda": {
        "kind": "weapon",
        "weapon_id": "kuda",
        "display_name": "Kuda",
        "price": 1250,
        "room": "help_1f",
    },
    "krm": {
        "kind": "weapon",
        "weapon_id": "krm262",
        "display_name": "KRM-262",
        "price": 750,
        "room": "help_1f",
    },
    "arak": {
        "kind": "weapon",
        "weapon_id": "kn44",
        "display_name": "KN-44",
        "price": 1400,
        "room": "help_2f",
    },
    "argus": {
        "kind": "weapon",
        "weapon_id": "argus",
        "display_name": "Argus",
        "price": 1100,
        "room": "help_2f",
    },
    "locus_decal": {
        "kind": "sniper_cabinet",
        "weapon_id": "locus",
        "display_name": "Locus",
        "price": 5000,
        "room": "help_2f",
    },
    "pharaoh": {
        "kind": "weapon",
        "weapon_id": "pharo",
        "display_name": "Pharo",
        "price": 700,
        "room": "grenade_room",
    },
    "frag": {
        "kind": "grenade",
        "weapon_id": "frag",
        "display_name": "Fragmentation Grenades",
        "price": 250,
        "room": "grenade_room",
    },
}

# The community port uses internal Treyarch codenames for several wall weapons.
EXISTING_ID_TO_CHALK = {
    "triton": "triton",
    "rk5": "triton",
    "kuda": "kuda",
    "arak": "arak",
    "kn44": "arak",
}


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
        return {k: clean(v) for k, v in value.items() if k != "$type"}
    if isinstance(value, list):
        return [clean(v) for v in value]
    if value == "+0":
        return 0.0
    return value


def xyz(value: Any) -> list[float] | None:
    value = clean(value)
    if not isinstance(value, dict):
        return None
    if not all(k in value for k in ("X", "Y", "Z")):
        return None
    try:
        return [float(value["X"]), float(value["Y"]), float(value["Z"])]
    except Exception:
        return None


def distance(a: list[float] | None, b: list[float] | None) -> float | None:
    if a is None or b is None:
        return None
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def find_bounds_candidates(doc: Any) -> list[dict[str, Any]]:
    """Collect likely local/world bounds from a UAssetAPI StaticMesh JSON."""
    rows: list[dict[str, Any]] = []

    def walk(node: Any, path: str = "") -> None:
        if isinstance(node, dict):
            lower = {str(k).lower(): k for k in node}
            # FBoxSphereBounds-like object
            if "origin" in lower and "boxextent" in lower:
                origin = xyz(node[lower["origin"]])
                extent = xyz(node[lower["boxextent"]])
                if origin and extent:
                    rows.append({
                        "path": path,
                        "type": "box_sphere_bounds",
                        "origin": origin,
                        "extent": extent,
                    })
            # FBox-like object
            if "min" in lower and "max" in lower:
                mn = xyz(node[lower["min"]])
                mx = xyz(node[lower["max"]])
                if mn and mx:
                    rows.append({
                        "path": path,
                        "type": "box",
                        "min": mn,
                        "max": mx,
                        "origin": [(a + b) / 2.0 for a, b in zip(mn, mx)],
                        "extent": [(b - a) / 2.0 for a, b in zip(mn, mx)],
                    })
            for k, v in node.items():
                walk(v, f"{path}/{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")

    walk(doc)
    # Prefer nonzero finite candidates and de-duplicate by rounded geometry.
    out = []
    seen = set()
    for r in rows:
        o = r.get("origin")
        e = r.get("extent")
        if not o or not e:
            continue
        if not all(math.isfinite(v) for v in o + e):
            continue
        key = tuple(round(v, 4) for v in o + e)
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def choose_bounds(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not candidates:
        return None
    # Chalk surfaces should be relatively small. Prefer the smallest nonzero
    # AABB by volume; world-space imported map pieces often carry absolute origins.
    def score(r: dict[str, Any]) -> tuple[float, float]:
        e = r["extent"]
        vol = max(e[0], 1e-6) * max(e[1], 1e-6) * max(e[2], 1e-6)
        span = sum(abs(v) for v in e)
        return (vol, span)
    return min(candidates, key=score)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("map_json", type=Path)
    ap.add_argument("chalk_json_dir", type=Path)
    ap.add_argument("output_json", type=Path)
    args = ap.parse_args()

    doc = json.loads(args.map_json.read_text(encoding="utf-8-sig"))
    exports: list[dict[str, Any]] = doc["Exports"]
    imports: list[dict[str, Any]] = doc["Imports"]

    def resolve(index: int) -> str | None:
        if not index:
            return None
        seen: set[int] = set()
        parts: list[str] = []
        while index and index not in seen:
            seen.add(index)
            obj = imports[-index - 1] if index < 0 else exports[index - 1]
            parts.append(str(obj.get("ObjectName", "?")))
            index = int(obj.get("OuterIndex", 0) or 0)
        return "/".join(reversed(parts))

    def class_name(export: dict[str, Any]) -> str:
        return resolve(int(export.get("ClassIndex", 0) or 0)) or ""

    level = next(e for e in exports if "LevelExport" in str(e.get("$type", "")))
    actor_indices = [x for x in level.get("Actors", []) if isinstance(x, int) and x > 0]

    def root_transform(actor: dict[str, Any]) -> dict[str, Any]:
        p = prop_map(actor)
        root = p.get("RootComponent", {}).get("Value")
        if not isinstance(root, int) or root <= 0:
            return {}
        comp = exports[root - 1]
        cp = prop_map(comp)
        return {
            "location": clean(struct_value(cp.get("RelativeLocation"))),
            "rotation": clean(struct_value(cp.get("RelativeRotation"))),
            "scale": clean(struct_value(cp.get("RelativeScale3D"))),
        }

    existing: list[dict[str, Any]] = []
    for idx in actor_indices:
        actor = exports[idx - 1]
        if not class_name(actor).endswith("/WallBuy_C"):
            continue
        p = prop_map(actor)
        weapon_id = p.get("WeaponID", {}).get("Value")
        display = p.get("DisplayName", {}).get("CultureInvariantString")
        price = p.get("Price", {}).get("Value")
        key = EXISTING_ID_TO_CHALK.get(str(weapon_id).lower())
        existing.append({
            "actor_export_index": idx,
            "actor_name": actor.get("ObjectName"),
            "weapon_id": weapon_id,
            "display_name": display,
            "price": price,
            "chalk_key": key,
            "transform": root_transform(actor),
        })

    chalk: dict[str, dict[str, Any]] = {}
    for key, spec in EXPECTED.items():
        path = args.chalk_json_dir / f"{key}.json"
        if not path.exists():
            chalk[key] = {"error": "missing_chalk_json"}
            continue
        mesh_doc = json.loads(path.read_text(encoding="utf-8-sig"))
        candidates = find_bounds_candidates(mesh_doc)
        chosen = choose_bounds(candidates)
        chalk[key] = {
            "bounds": chosen,
            "bounds_candidate_count": len(candidates),
        }

    existing_by_key = {r["chalk_key"]: r for r in existing if r.get("chalk_key")}

    purchases = []
    calibration = []
    for key, spec in EXPECTED.items():
        ex = existing_by_key.get(key)
        bounds = chalk.get(key, {}).get("bounds")
        center = bounds.get("origin") if bounds else None
        active_loc = xyz(ex.get("transform", {}).get("location")) if ex else None
        err = distance(center, active_loc)
        if ex and center and active_loc:
            calibration.append({
                "chalk_key": key,
                "chalk_center": center,
                "active_wallbuy_location": active_loc,
                "distance": err,
                "delta": [active_loc[i] - center[i] for i in range(3)],
            })

        purchases.append({
            "chalk_key": key,
            **spec,
            "existing_active_wallbuy": ex,
            "chalk_bounds": bounds,
            "suggested_trigger_location": (
                active_loc if active_loc is not None else center
            ),
            "repair_needed": ex is None,
            "position_source": (
                "existing_wallbuy_actor" if active_loc is not None
                else "chalk_mesh_bounds_center" if center is not None
                else "unresolved"
            ),
        })

    output = {
        "schema": 1,
        "source": {
            "map": "Nacht_de_Untoten.umap",
            "workshop_id": "2755515831",
            "engine": "UE4.21",
            "note": "Pavlov community port; use as reconstruction/reference evidence, not Treyarch source.",
        },
        "summary": {
            "expected_purchase_surfaces": len(EXPECTED),
            "expected_direct_weapon_wallbuys": 7,
            "existing_wallbuy_blueprints": len(existing),
            "missing_direct_or_special_purchase_surfaces": sum(1 for p in purchases if p["repair_needed"]),
            "calibration_pair_count": len(calibration),
        },
        "existing_wallbuys": existing,
        "calibration": calibration,
        "purchases": purchases,
        "repair_rule": {
            "template": "Clone behavior/schema from existing WallBuy_C actors.",
            "position": "Use exact active actor transform when present; otherwise seed trigger from the corresponding chalk mesh bounds center.",
            "orientation": "Derive wall-facing normal from the thinnest chalk AABB axis during XZIEL mesh conversion, then offset the interaction volume toward playable space.",
            "validation": "The three surviving RK5/Kuda/KN-44 actors are calibration anchors for trigger offset/radius and UI behavior.",
        },
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(output["summary"], indent=2))
    print("existing:")
    for r in existing:
        print(r["weapon_id"], r["price"], r["transform"])
    print("calibration:")
    for r in calibration:
        print(r)
    print("repair:")
    for p in purchases:
        if p["repair_needed"]:
            print(p["chalk_key"], p["display_name"], p["price"], p["position_source"], p["suggested_trigger_location"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
