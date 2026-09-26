#!/usr/bin/env python3
"""Derive a compact Nacht placement manifest from UAssetGUI JSON.

Input:
  UAssetGUI tojson Nacht_de_Untoten.umap Nacht_de_Untoten.json VER_UE4_21

The map is a cooked Pavlov UE4.21 port whose author credits BO3 map geometry.
This script does not copy mesh payloads. It resolves object references and
reconstructs SceneComponent world transforms from AttachParent chains.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from functools import lru_cache
from pathlib import Path


def number(v, default=0.0):
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.replace("+", ""))
        except ValueError:
            pass
    return default


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input_json", type=Path)
    ap.add_argument("output_dir", type=Path)
    args = ap.parse_args()

    doc = json.loads(args.input_json.read_text(encoding="utf-8-sig"))
    exports = doc["Exports"]
    imports = doc["Imports"]
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)

    def propmap(exp):
        return {
            p.get("Name"): p
            for p in exp.get("Data", [])
            if isinstance(p, dict) and p.get("Name")
        }

    def prop(exp, name):
        return propmap(exp).get(name)

    def unwrap_struct(p):
        if not p:
            return None
        value = p.get("Value")
        if isinstance(value, list) and value:
            inner = value[0]
            if isinstance(inner, dict) and "Value" in inner:
                return inner["Value"]
        return value

    def objref(exp, name):
        p = prop(exp, name)
        v = p.get("Value", 0) if p else 0
        return int(v) if isinstance(v, (int, float)) else 0

    def vector(exp, name, default):
        v = unwrap_struct(prop(exp, name))
        if not isinstance(v, dict):
            return default
        return (
            number(v.get("X"), default[0]),
            number(v.get("Y"), default[1]),
            number(v.get("Z"), default[2]),
        )

    def rotator(exp):
        v = unwrap_struct(prop(exp, "RelativeRotation"))
        if not isinstance(v, dict):
            return (0.0, 0.0, 0.0)
        return (
            number(v.get("Pitch")),
            number(v.get("Yaw")),
            number(v.get("Roll")),
        )

    @lru_cache(maxsize=None)
    def object_path(index):
        if not index:
            return ""
        if index > 0:
            obj = exports[index - 1]
        else:
            obj = imports[-index - 1]
        name = str(obj.get("ObjectName", "?"))
        outer = int(obj.get("OuterIndex", 0) or 0)
        parent = object_path(outer) if outer else ""
        return f"{parent}.{name}" if parent else name

    # Exact UE4 FRotator::Quaternion() convention.
    def rotator_quat(r):
        pitch, yaw, roll = map(math.radians, r)
        sp, cp = math.sin(pitch / 2.0), math.cos(pitch / 2.0)
        sy, cy = math.sin(yaw / 2.0), math.cos(yaw / 2.0)
        sr, cr = math.sin(roll / 2.0), math.cos(roll / 2.0)
        return (
            cr * sp * sy - sr * cp * cy,
            -cr * sp * cy - sr * cp * sy,
            cr * cp * sy - sr * sp * cy,
            cr * cp * cy + sr * sp * sy,
        )

    def qnorm(q):
        n = math.sqrt(sum(v * v for v in q))
        return tuple(v / n for v in q) if n else (0.0, 0.0, 0.0, 1.0)

    def qmul(a, b):
        ax, ay, az, aw = a
        bx, by, bz, bw = b
        return (
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz,
        )

    def qrotate(q, v):
        x, y, z, w = qnorm(q)
        vx, vy, vz = v
        tx = 2.0 * (y * vz - z * vy)
        ty = 2.0 * (z * vx - x * vz)
        tz = 2.0 * (x * vy - y * vx)
        return (
            vx + w * tx + (y * tz - z * ty),
            vy + w * ty + (z * tx - x * tz),
            vz + w * tz + (x * ty - y * tx),
        )

    def compose(parent, child):
        ploc, pq, ps = parent
        cloc, cq, cs = child
        scaled = tuple(cloc[i] * ps[i] for i in range(3))
        rotated = qrotate(pq, scaled)
        loc = tuple(ploc[i] + rotated[i] for i in range(3))
        quat = qnorm(qmul(pq, cq))
        scale = tuple(ps[i] * cs[i] for i in range(3))
        return loc, quat, scale

    identity = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0), (1.0, 1.0, 1.0))

    components = {}
    absolute_flags = Counter()
    for i, exp in enumerate(exports, 1):
        props = propmap(exp)
        for key in ("bAbsoluteLocation", "bAbsoluteRotation", "bAbsoluteScale"):
            if key in props and props[key].get("Value"):
                absolute_flags[key] += 1

        if not any(
            k in props
            for k in (
                "AttachParent",
                "RelativeLocation",
                "RelativeRotation",
                "RelativeScale3D",
                "StaticMesh",
            )
        ):
            continue

        loc = vector(exp, "RelativeLocation", (0.0, 0.0, 0.0))
        rot = rotator(exp)
        scale = vector(exp, "RelativeScale3D", (1.0, 1.0, 1.0))
        components[i] = {
            "name": exp.get("ObjectName"),
            "outer": int(exp.get("OuterIndex", 0) or 0),
            "parent": objref(exp, "AttachParent"),
            "mesh": objref(exp, "StaticMesh"),
            "local": (loc, rotator_quat(rot), scale),
        }

    world_cache = {}
    visiting = set()

    def world(index):
        if index in world_cache:
            return world_cache[index]
        if index in visiting:
            raise RuntimeError(f"AttachParent cycle at export {index}")
        rec = components.get(index)
        if rec is None:
            return identity
        visiting.add(index)
        parent = rec["parent"]
        if parent > 0 and parent in components:
            result = compose(world(parent), rec["local"])
        else:
            result = rec["local"]
        visiting.remove(index)
        world_cache[index] = result
        return result

    records = []
    for i, rec in components.items():
        if not rec["mesh"]:
            continue
        mesh_path = object_path(rec["mesh"])
        low = mesh_path.lower()
        if "zm_prototype_part" in low:
            category = "map_files"
        elif "p7_zm_nac_" in low:
            category = "nacht_unique"
        elif "p7_zm_gen_proto_" in low:
            category = "prototype_arch"
        elif "/cod_nacht/" in low:
            category = "cod_nacht_other"
        else:
            category = "shared_or_gameplay"

        loc, quat, scale = world(i)
        records.append(
            {
                "component_export": i,
                "component": object_path(i),
                "actor": object_path(rec["outer"]),
                "mesh": mesh_path,
                "parent_export": rec["parent"] if rec["parent"] > 0 else None,
                "world_location_cm": [round(v, 6) for v in loc],
                "world_quat_xyzw": [round(v, 8) for v in quat],
                "world_scale": [round(v, 6) for v in scale],
                "category": category,
            }
        )

    def bounds(rows):
        if not rows:
            return None
        xyz = [r["world_location_cm"] for r in rows]
        mins = [min(p[i] for p in xyz) for i in range(3)]
        maxs = [max(p[i] for p in xyz) for i in range(3)]
        span = [maxs[i] - mins[i] for i in range(3)]
        return {
            "min_cm": mins,
            "max_cm": maxs,
            "span_cm": span,
            "span_m": [round(v / 100.0, 6) for v in span],
            "note": "component-origin bounds only; mesh vertex extents are not included",
        }

    categories = {}
    for name in (
        "map_files",
        "nacht_unique",
        "prototype_arch",
        "cod_nacht_other",
        "shared_or_gameplay",
    ):
        rows = [r for r in records if r["category"] == name]
        categories[name] = {
            "instances": len(rows),
            "unique_meshes": len({r["mesh"] for r in rows}),
            "origin_bounds": bounds(rows),
        }

    focus = [
        r
        for r in records
        if r["category"] in ("map_files", "nacht_unique", "prototype_arch")
    ]

    summary = {
        "source": {
            "map": "Nacht_de_Untoten.umap",
            "exports": len(exports),
            "imports": len(imports),
            "name_map": len(doc.get("NameMap", [])),
        },
        "static_mesh_instances": {
            "total": len(records),
            "unique_meshes": len({r["mesh"] for r in records}),
            "categories": categories,
        },
        "absolute_transform_flags": dict(absolute_flags),
        "notes": [
            "MAP_FILES/zm_prototype_part* meshes are nearly origin-placed because their vertices carry baked map-space geometry.",
            "Export those meshes to reconstruct the large building/world geometry.",
        ],
    }

    (out / "layout_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    (out / "focus_placements.json").write_text(
        json.dumps(focus, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
