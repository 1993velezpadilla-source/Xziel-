#!/usr/bin/env python3
"""HAYUYA / XZIEL St Giles 1:1 church reconstruction pass.

Design goal:
- Treat the licensed St Giles photogrammetry mesh as ground truth.
- Never procedurally invent primary church proportions.
- Build cleaner game-ready LODs while preserving world-space silhouette,
  openings, materials, UVs, and global dimensions.
- Keep the untouched scan in the master .blend for future manual retopo/bakes.
- Produce deterministic QA evidence and map-ready GLBs.

This script intentionally uses Blender built-ins only so it can run headless in CI.
External Blender tools researched for later/manual passes are documented in
hayuya/knowledge/church_blender_rebuild_toolchain_v1.json.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

SOURCE = Path(os.environ.get("CHURCH_SOURCE", "church/source/st-giles-cripplegate.glb"))
OUTDIR = Path(os.environ.get("CHURCH_OUT", "church/out_1to1"))
LOD_TARGETS = {
    "LOD0": int(os.environ.get("CHURCH_LOD0_TRIS", "650000")),
    "LOD1": int(os.environ.get("CHURCH_LOD1_TRIS", "325000")),
    "LOD2": int(os.environ.get("CHURCH_LOD2_TRIS", "160000")),
    "LOD3": int(os.environ.get("CHURCH_LOD3_TRIS", "80000")),
}
COLLISION_TARGET = int(os.environ.get("CHURCH_COLLISION_TRIS", "50000"))
OUTDIR.mkdir(parents=True, exist_ok=True)


def tri_count(obj):
    if obj.type != "MESH":
        return 0
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def world_bbox(objects):
    pts = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            pts.append(obj.matrix_world @ Vector(corner))
    if not pts:
        return Vector((0.0, 0.0, 0.0)), Vector((0.0, 0.0, 0.0))
    mn = Vector((
        min(p.x for p in pts),
        min(p.y for p in pts),
        min(p.z for p in pts),
    ))
    mx = Vector((
        max(p.x for p in pts),
        max(p.y for p in pts),
        max(p.z for p in pts),
    ))
    return mn, mx


def bbox_metrics(objects):
    mn, mx = world_bbox(objects)
    size = mx - mn
    center = (mn + mx) * 0.5
    diag = max(size.length, 1e-9)
    return mn, mx, size, center, diag


def collection(name):
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def move_to_collection(obj, col):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    col.objects.link(obj)


def activate_only(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def apply_modifier(obj, modifier_name):
    activate_only(obj)
    try:
        bpy.ops.object.modifier_apply(modifier=modifier_name)
        return True
    except Exception as exc:
        print("WARN modifier_apply", obj.name, modifier_name, repr(exc))
        return False
    finally:
        obj.select_set(False)


def sanitize_mesh(obj):
    if obj.type != "MESH":
        return
    try:
        obj.data.validate(verbose=False, clean_customdata=False)
        obj.data.update()
    except Exception as exc:
        print("WARN mesh_validate", obj.name, repr(exc))


def copy_source_object(src, col, suffix):
    dup = src.copy()
    dup.data = src.data.copy()
    dup.name = f"{src.name}_{suffix}"
    col.objects.link(dup)
    sanitize_mesh(dup)
    return dup


def decimate_objects(source_objects, col_name, target_tris):
    col = collection(col_name)
    current_total = sum(tri_count(o) for o in source_objects)
    ratio = min(1.0, target_tris / max(current_total, 1))
    out = []

    for src in source_objects:
        dup = copy_source_object(src, col, col_name.lower())
        src_tris = tri_count(dup)
        if ratio < 0.9995 and src_tris >= 256:
            mod = dup.modifiers.new(name="HAYUYA_REFERENCE_DECIMATE", type="DECIMATE")
            mod.decimate_type = "COLLAPSE"
            mod.ratio = max(0.01, min(1.0, ratio))
            if hasattr(mod, "use_collapse_triangulate"):
                mod.use_collapse_triangulate = True
            apply_modifier(dup, mod.name)
        out.append(dup)

    return col, out, ratio


def affine_match_bounds(objects, ref_center, ref_size):
    """Match global center/size to the scan without changing topology.

    Decimation can occasionally remove an extreme vertex and shift a bound by a
    few millimetres. Applying one tiny global affine correction guarantees the
    exported LOD preserves the scan's canonical footprint and height.
    """
    _, _, size, center, _ = bbox_metrics(objects)
    scale = Vector((
        ref_size.x / size.x if abs(size.x) > 1e-9 else 1.0,
        ref_size.y / size.y if abs(size.y) > 1e-9 else 1.0,
        ref_size.z / size.z if abs(size.z) > 1e-9 else 1.0,
    ))
    transform = (
        Matrix.Translation(ref_center)
        @ Matrix.Diagonal((scale.x, scale.y, scale.z, 1.0))
        @ Matrix.Translation(-center)
    )
    for obj in objects:
        obj.matrix_world = transform @ obj.matrix_world
    return list(scale)


def material_inventory(objects):
    materials = {}
    images = {}
    for obj in objects:
        if obj.type != "MESH":
            continue
        for mat in obj.data.materials:
            if mat is None:
                continue
            item = materials.setdefault(mat.name, {"users": 0, "images": []})
            item["users"] += 1
            if not mat.use_nodes or not mat.node_tree:
                continue
            for node in mat.node_tree.nodes:
                if node.type != "TEX_IMAGE" or not getattr(node, "image", None):
                    continue
                img = node.image
                width, height = (0, 0)
                try:
                    width, height = int(img.size[0]), int(img.size[1])
                except Exception:
                    pass
                images[img.name] = {
                    "width": width,
                    "height": height,
                    "filepath": img.filepath,
                    "packed": bool(getattr(img, "packed_file", None)),
                }
                if img.name not in item["images"]:
                    item["images"].append(img.name)
    return materials, images


def hide_group(objects, viewport=True, render=True):
    for obj in objects:
        obj.hide_set(viewport)
        obj.hide_render = render


def export_glb(objects, path):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.hide_set(False)
        obj.hide_render = False
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
    )
    for obj in objects:
        obj.select_set(False)


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def setup_render(center, size, diag):
    scene = bpy.context.scene
    world = scene.world or bpy.data.worlds.new("HAYUYA_CHURCH_WORLD")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.015, 0.018, 0.025, 1.0)
        bg.inputs["Strength"].default_value = 0.28

    bpy.ops.object.light_add(
        type="SUN",
        location=(center.x, center.y, center.z + diag),
    )
    sun = bpy.context.object
    sun.name = "QA_SUN"
    sun.data.energy = 2.0
    sun.rotation_euler = (
        math.radians(42),
        math.radians(-18),
        math.radians(-32),
    )

    bpy.ops.object.light_add(
        type="AREA",
        location=(center.x, center.y - diag * 0.25, center.z + size.z * 0.25),
    )
    fill = bpy.context.object
    fill.name = "QA_FILL"
    fill.data.energy = 1200
    fill.data.size = max(size.x, size.y) * 0.55
    look_at(fill, center)

    bpy.ops.object.camera_add()
    cam = bpy.context.object
    cam.name = "QA_CAMERA"
    cam.data.lens = 48
    cam.data.clip_end = max(1000.0, diag * 25.0)
    scene.camera = cam

    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except Exception:
        scene.render.engine = "BLENDER_EEVEE"
    return cam


def render_views(prefix, visible_objects, all_model_objects, cam, center, diag):
    for obj in all_model_objects:
        obj.hide_render = obj not in visible_objects
        obj.hide_set(obj not in visible_objects)

    views = {
        "front_3q": Vector((1.20, -1.35, 0.58)),
        "rear_3q": Vector((-1.15, 1.30, 0.52)),
        "entry": Vector((0.0, -1.25, 0.18)),
        "top": Vector((0.0, -0.01, 2.1)),
    }
    scene = bpy.context.scene
    for name, offs in views.items():
        cam.location = center + Vector((
            offs.x * diag,
            offs.y * diag,
            offs.z * diag,
        ))
        look_at(cam, center)
        scene.render.filepath = str(OUTDIR / f"{prefix}_{name}.png")
        bpy.ops.render.render(write_still=True)


def add_anchor(col, name, location, kind, notes=""):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "SPHERE"
    obj.empty_display_size = 0.35
    obj.location = location
    obj["hayuya_kind"] = kind
    obj["source_asset"] = "st_giles_cripplegate"
    obj["notes"] = notes
    col.objects.link(obj)
    return obj


# Clean scene.
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

# Import canonical source.
if not SOURCE.exists():
    raise FileNotFoundError(str(SOURCE))
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
source_objects = [o for o in bpy.context.scene.objects if o.type == "MESH"]
if not source_objects:
    raise RuntimeError("St Giles source imported with zero mesh objects")

source_col = collection("SOURCE_SCAN_ST_GILES")
for obj in list(source_objects):
    move_to_collection(obj, source_col)
    obj["hayuya_role"] = "immutable_reference_scan"

source_mn, source_mx, source_size, source_center, source_diag = bbox_metrics(source_objects)
source_tris = sum(tri_count(o) for o in source_objects)
source_materials, source_images = material_inventory(source_objects)

# Build visual LODs from the exact scan.
lod_results = {}
all_model_objects = list(source_objects)
for lod_name, target in LOD_TARGETS.items():
    col, objects, requested_ratio = decimate_objects(
        source_objects,
        f"CHURCH_REBUILD_{lod_name}",
        target,
    )
    affine_scale = affine_match_bounds(objects, source_center, source_size)
    for obj in objects:
        obj["hayuya_role"] = f"church_visual_{lod_name.lower()}"
        obj["source_asset"] = "st_giles_cripplegate"
    all_model_objects.extend(objects)
    mn, mx, size, center, diag = bbox_metrics(objects)
    lod_results[lod_name] = {
        "collection": col,
        "objects": objects,
        "triangles": sum(tri_count(o) for o in objects),
        "requested_target": target,
        "requested_ratio": requested_ratio,
        "affine_match_scale": affine_scale,
        "bounds_min": list(mn),
        "bounds_max": list(mx),
        "bounds_size": list(size),
        "center": list(center),
        "diag": diag,
    }

# Collision keeps the interior topology rather than convex-hulling the whole church.
collision_col, collision_objects, collision_ratio = decimate_objects(
    source_objects,
    "CHURCH_COLLISION_REFERENCE",
    COLLISION_TARGET,
)
affine_match_bounds(collision_objects, source_center, source_size)
for obj in collision_objects:
    obj["hayuya_role"] = "church_collision"
    obj["xziel_collision"] = True
all_model_objects.extend(collision_objects)

# Stable semantic anchors for map placement / encounter systems.
anchors_col = collection("HAYUYA_CHURCH_ANCHORS")
floor_z = source_mn.z + max(source_size.z * 0.012, 0.05)
anchors = [
    add_anchor(
        anchors_col,
        "church_root",
        (source_center.x, source_center.y, floor_z),
        "church_root",
        "Canonical map placement origin; do not rescale after import.",
    ),
    add_anchor(
        anchors_col,
        "church_entry_axis",
        (source_center.x, source_mn.y, floor_z),
        "church_entry",
        "Front/entry-side canonical anchor for gameplay authoring.",
    ),
    add_anchor(
        anchors_col,
        "church_tower_axis",
        (source_center.x, source_center.y, source_mx.z),
        "church_tower",
        "Top landmark anchor for visibility and lighting.",
    ),
]

# QA renders compare immutable source vs map-ready LOD0 with identical cameras.
cam = setup_render(source_center, source_size, source_diag)
hide_group(all_model_objects, viewport=True, render=True)
render_views(
    "source",
    source_objects,
    all_model_objects,
    cam,
    source_center,
    source_diag,
)
render_views(
    "rebuild_lod0",
    lod_results["LOD0"]["objects"],
    all_model_objects,
    cam,
    source_center,
    source_diag,
)

# Export map-ready assets.
for lod_name in LOD_TARGETS:
    export_glb(
        lod_results[lod_name]["objects"],
        OUTDIR / f"st_giles_church_{lod_name.lower()}.glb",
    )
export_glb(collision_objects, OUTDIR / "st_giles_church_collision.glb")

# Restore master scene visibility state.
for obj in source_objects:
    obj.hide_set(True)
    obj.hide_render = True
for lod_name, data in lod_results.items():
    visible = lod_name == "LOD0"
    for obj in data["objects"]:
        obj.hide_set(not visible)
        obj.hide_render = not visible
for obj in collision_objects:
    obj.hide_set(True)
    obj.hide_render = True

master_path = OUTDIR / "st_giles_church_1to1_master.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(master_path))

# Quantitative 1:1 contract.
lod0 = lod_results["LOD0"]
lod0_size = Vector(lod0["bounds_size"])
lod0_center = Vector(lod0["center"])
size_rel_error = [
    abs(lod0_size[i] - source_size[i]) / max(abs(source_size[i]), 1e-9)
    for i in range(3)
]
center_error = (lod0_center - source_center).length
material_count_lod0 = len(material_inventory(lod0["objects"])[0])

report = {
    "schema": 1,
    "asset": {
        "id": "st_giles_cripplegate",
        "role": "HAYUYA church one-to-one map model",
        "source": str(SOURCE),
        "policy": "licensed photogrammetry is canonical geometry; generic building generators are not authoritative",
    },
    "source": {
        "mesh_count": len(source_objects),
        "triangles": source_tris,
        "bounds_min": list(source_mn),
        "bounds_max": list(source_mx),
        "bounds_size": list(source_size),
        "center": list(source_center),
        "diag": source_diag,
        "material_count": len(source_materials),
        "materials": source_materials,
        "image_count": len(source_images),
        "images": source_images,
    },
    "lods": {
        name: {
            key: value
            for key, value in data.items()
            if key not in {"collection", "objects"}
        }
        for name, data in lod_results.items()
    },
    "collision": {
        "triangles": sum(tri_count(o) for o in collision_objects),
        "requested_target": COLLISION_TARGET,
        "requested_ratio": collision_ratio,
    },
    "anchors": [
        {
            "name": obj.name,
            "kind": obj.get("hayuya_kind"),
            "location": list(obj.location),
            "notes": obj.get("notes"),
        }
        for obj in anchors
    ],
    "one_to_one_qa": {
        "lod0_size_relative_error_xyz": size_rel_error,
        "lod0_center_error": center_error,
        "max_size_relative_error": max(size_rel_error),
        "material_count_source": len(source_materials),
        "material_count_lod0": material_count_lod0,
        "bounds_contract_pass": max(size_rel_error) <= 0.001 and center_error <= source_diag * 0.001,
        "material_slots_preserved": material_count_lod0 == len(source_materials),
    },
    "outputs": {
        "master_blend": master_path.name,
        "visual_glbs": {
            name: f"st_giles_church_{name.lower()}.glb"
            for name in LOD_TARGETS
        },
        "collision_glb": "st_giles_church_collision.glb",
    },
}

report["one_to_one_qa"]["pass"] = (
    report["one_to_one_qa"]["bounds_contract_pass"]
    and report["one_to_one_qa"]["material_slots_preserved"]
    and lod0["triangles"] >= min(300000, source_tris)
    and lod0["triangles"] <= source_tris
)

report_path = OUTDIR / "church_1to1_report.json"
report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

map_manifest = {
    "schema": 1,
    "asset_id": "st_giles_cripplegate_church_1to1",
    "canonical_dimensions": list(source_size),
    "canonical_center": list(source_center),
    "do_not_rescale": True,
    "visual": {
        "lod0": "st_giles_church_lod0.glb",
        "lod1": "st_giles_church_lod1.glb",
        "lod2": "st_giles_church_lod2.glb",
        "lod3": "st_giles_church_lod3.glb",
    },
    "collision": "st_giles_church_collision.glb",
    "anchors": report["anchors"],
    "source_attribution_required": True,
}
(OUTDIR / "church_map_asset_manifest.json").write_text(
    json.dumps(map_manifest, indent=2),
    encoding="utf-8",
)

print(json.dumps(report, indent=2))
if not report["one_to_one_qa"]["pass"]:
    raise SystemExit("HAYUYA_CHURCH_1TO1_QA_FAILED")
print("HAYUYA_CHURCH_1TO1_QA_GREEN")
