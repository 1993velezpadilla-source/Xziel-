#!/usr/bin/env python3
"""Inspect a first-person weapon asset inside Blender and emit a machine-readable report.

This is deliberately a probe, not a production exporter. It answers whether an
asset is genuinely FPS-ready before XZIEL adopts it: separate weapon/hands
geometry, armature/bones, authored actions, bounds, materials, and a canonical
GLB snapshot preserving animation when Blender can export it.
"""

import json
import math
import os
from pathlib import Path

import bpy
from mathutils import Vector


def require_env(name: str) -> Path:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"missing environment variable: {name}")
    return Path(value)


source = require_env("FPS_SOURCE")
report_path = require_env("FPS_REPORT")
glb_path = require_env("FPS_CANONICAL_GLB")

if not source.is_file():
    raise RuntimeError(f"FPS source does not exist: {source}")

# Start from a predictable empty scene unless opening a .blend directly.
if source.suffix.lower() == ".blend":
    bpy.ops.wm.open_mainfile(filepath=str(source.resolve()))
else:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    suffix = source.suffix.lower()
    if suffix in {".gltf", ".glb"}:
        bpy.ops.import_scene.gltf(filepath=str(source.resolve()))
    elif suffix == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(source.resolve()))
    elif suffix == ".obj":
        bpy.ops.import_scene.obj(filepath=str(source.resolve()))
    else:
        raise RuntimeError(f"unsupported FPS source format: {suffix}")

scene = bpy.context.scene
objects = list(scene.objects)
mesh_objects = [obj for obj in objects if obj.type == "MESH"]
armatures = [obj for obj in objects if obj.type == "ARMATURE"]

if not mesh_objects:
    raise RuntimeError("FPS asset contains no mesh objects")

world_min = Vector((math.inf, math.inf, math.inf))
world_max = Vector((-math.inf, -math.inf, -math.inf))
mesh_entries = []

for obj in mesh_objects:
    # Evaluate object-space bounding box through the world transform.
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    for p in corners:
        for axis in range(3):
            world_min[axis] = min(world_min[axis], p[axis])
            world_max[axis] = max(world_max[axis], p[axis])

    materials = []
    for slot in obj.material_slots:
        if slot.material is not None:
            materials.append(slot.material.name)

    modifiers = [
        {
            "name": mod.name,
            "type": mod.type,
            "object": getattr(getattr(mod, "object", None), "name", None),
        }
        for mod in obj.modifiers
    ]

    mesh_entries.append(
        {
            "name": obj.name,
            "vertices": len(obj.data.vertices),
            "polygons": len(obj.data.polygons),
            "materials": sorted(set(materials)),
            "modifiers": modifiers,
            "parent": obj.parent.name if obj.parent else None,
        }
    )

armature_entries = []
for obj in armatures:
    armature_entries.append(
        {
            "name": obj.name,
            "bones": [bone.name for bone in obj.data.bones],
            "boneCount": len(obj.data.bones),
            "parent": obj.parent.name if obj.parent else None,
        }
    )

actions = []
for action in bpy.data.actions:
    frame_range = [float(action.frame_range[0]), float(action.frame_range[1])]
    actions.append(
        {
            "name": action.name,
            "frameRange": frame_range,
            "fcurveCount": len(action.fcurves),
        }
    )

nla = []
for obj in objects:
    animation_data = getattr(obj, "animation_data", None)
    if animation_data is None:
        continue
    for track in animation_data.nla_tracks:
        strips = []
        for strip in track.strips:
            strips.append(
                {
                    "name": strip.name,
                    "action": strip.action.name if strip.action else None,
                    "frameStart": float(strip.frame_start),
                    "frameEnd": float(strip.frame_end),
                }
            )
        if strips:
            nla.append({"object": obj.name, "track": track.name, "strips": strips})

lower_names = [obj.name.lower() for obj in mesh_objects]
action_names = [entry["name"].lower() for entry in actions]

has_hands = any(
    any(token in name for token in ("hand", "hands", "arm", "arms", "glove"))
    for name in lower_names
)
has_weapon = any(
    any(token in name for token in ("rifle", "gun", "weapon", "ak", "barrel"))
    for name in lower_names
)
has_shoot_action = any(
    any(token in name for token in ("shoot", "fire", "shot"))
    for name in action_names
)
has_reload_action = any("reload" in name for name in action_names)

dimensions = world_max - world_min

# Export a normalized interchange snapshot preserving the original rig/actions.
glb_path.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(
    filepath=str(glb_path.resolve()),
    export_format="GLB",
    export_animations=True,
    export_skins=True,
    export_morph=True,
)

report = {
    "source": str(source),
    "meshCount": len(mesh_objects),
    "armatureCount": len(armatures),
    "actionCount": len(actions),
    "nlaTrackCount": len(nla),
    "objectCount": len(objects),
    "bounds": {
        "min": [float(v) for v in world_min],
        "max": [float(v) for v in world_max],
        "dimensions": [float(v) for v in dimensions],
    },
    "meshes": mesh_entries,
    "armatures": armature_entries,
    "actions": actions,
    "nla": nla,
    "fpsReadiness": {
        "hasHandsLikeMesh": has_hands,
        "hasWeaponLikeMesh": has_weapon,
        "hasArmature": bool(armatures),
        "hasAuthoredAnimation": bool(actions or nla),
        "hasShootLikeAction": has_shoot_action,
        "hasReloadLikeAction": has_reload_action,
    },
    "canonicalGlb": str(glb_path),
}

report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

print(
    "XZIEL_FPS_VIEWMODEL_PROBE_READY",
    f"meshes={len(mesh_objects)}",
    f"armatures={len(armatures)}",
    f"actions={len(actions)}",
    f"hands={int(has_hands)}",
    f"weapon={int(has_weapon)}",
    f"shoot={int(has_shoot_action)}",
)
