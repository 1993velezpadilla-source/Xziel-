import bpy
import json
import math
import os
import re
import struct
from pathlib import Path
from mathutils import Vector

SOURCE = Path(os.environ.get("WEAPON_SOURCE", "church/source/weapons/standard_rifle.glb"))
RUNTIME_ROOT = Path(os.environ.get("XZIEL_STATIC_RUNTIME_ROOT", "church/out/xziel_native_static"))
MODEL_DIR = RUNTIME_ROOT / "models" / "xziel" / "weapons"
TEXTURE_DIR = RUNTIME_ROOT / "textures" / "xziel" / "weapons" / "standard_rifle"
REPORT = RUNTIME_ROOT / "weapon_standard_rifle_report.json"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
TEXTURE_DIR.mkdir(parents=True, exist_ok=True)

MAX_TRIS_PER_BATCH = 18000

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
scene = bpy.context.scene
scene.frame_set(0)

# Freeze the GLB's default pose for checkpoint A while retaining the source
# animation names in the report. Checkpoint B consumes those rigid-node clips.
for obj in scene.objects:
    if obj.animation_data is not None:
        obj.animation_data.action = None

mesh_objects = [o for o in scene.objects if o.type == "MESH"]
if not mesh_objects:
    raise RuntimeError("weapon GLB imported no mesh objects")

def safe_name(value):
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", value or "material")
    return value[:48] or "material"

def material_color(mat):
    if mat and mat.use_nodes and mat.node_tree:
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf and bsdf.inputs.get("Base Color"):
            c = bsdf.inputs["Base Color"].default_value
            return tuple(max(0.0, min(1.0, float(v))) for v in c[:4])
    if mat:
        return tuple(max(0.0, min(1.0, float(v))) for v in mat.diffuse_color)
    return (0.24, 0.25, 0.27, 1.0)

material_paths = {}
material_records = {}

def save_material_texture(mat):
    key = mat.name if mat else "__fallback__"
    if key in material_paths:
        return material_paths[key]

    index = len(material_paths)
    stem = f"mat_{index:02d}_{safe_name(key)}"
    dst = TEXTURE_DIR / f"{stem}.png"
    rgba = material_color(mat)

    img = bpy.data.images.new(stem, width=8, height=8, alpha=True, float_buffer=False)
    img.pixels = list(rgba) * 64
    img.file_format = "PNG"
    img.filepath_raw = str(dst)
    img.save()
    bpy.data.images.remove(img)

    rel = f"textures/xziel/weapons/standard_rifle/{stem}"
    material_paths[key] = rel
    material_records[key] = {
        "path": rel + ".png",
        "rgba": list(rgba),
        "bytes": dst.stat().st_size,
    }
    return rel

# First pass: world-space bounds from the imported GLB. 3dassets.dev models are
# +Y up and +Z muzzle-forward, matching Xziel's camera-local convention.
raw_min = Vector((1e30, 1e30, 1e30))
raw_max = Vector((-1e30, -1e30, -1e30))
source_triangles = 0
for obj in mesh_objects:
    mesh = obj.data
    mesh.calc_loop_triangles()
    source_triangles += len(mesh.loop_triangles)
    world = obj.matrix_world
    for vertex in mesh.vertices:
        p = world @ vertex.co
        raw_min.x = min(raw_min.x, p.x)
        raw_min.y = min(raw_min.y, p.y)
        raw_min.z = min(raw_min.z, p.z)
        raw_max.x = max(raw_max.x, p.x)
        raw_max.y = max(raw_max.y, p.y)
        raw_max.z = max(raw_max.z, p.z)

if source_triangles < 1000:
    raise RuntimeError(f"weapon mesh unexpectedly small: {source_triangles} triangles")

# Center left/right and vertically, but anchor the rear of the rifle at z=0.
# Runtime placement therefore stays stable even if the vendor GLB origin moves.
anchor = Vector((
    (raw_min.x + raw_max.x) * 0.5,
    (raw_min.y + raw_max.y) * 0.5,
    raw_min.z,
))

groups = {}
bounds_min = Vector((1e30, 1e30, 1e30))
bounds_max = Vector((-1e30, -1e30, -1e30))

for obj in mesh_objects:
    mesh = obj.data
    mesh.calc_loop_triangles()
    world = obj.matrix_world
    normal_matrix = world.to_3x3().inverted().transposed()

    for tri in mesh.loop_triangles:
        poly = mesh.polygons[tri.polygon_index]
        mat = obj.material_slots[poly.material_index].material if poly.material_index < len(obj.material_slots) else None
        texture = save_material_texture(mat)
        group = groups.setdefault(texture, [])
        verts = []

        for loop_index in tri.loops:
            vertex_index = mesh.loops[loop_index].vertex_index
            p = (world @ mesh.vertices[vertex_index].co) - anchor
            n = normal_matrix @ mesh.vertices[vertex_index].normal
            if n.length > 1e-8:
                n.normalize()
            else:
                n = Vector((0.0, 1.0, 0.0))

            bounds_min.x = min(bounds_min.x, p.x)
            bounds_min.y = min(bounds_min.y, p.y)
            bounds_min.z = min(bounds_min.z, p.z)
            bounds_max.x = max(bounds_max.x, p.x)
            bounds_max.y = max(bounds_max.y, p.y)
            bounds_max.z = max(bounds_max.z, p.z)

            verts.append((
                float(p.x), float(p.y), float(p.z),
                float(n.x), float(n.y), float(n.z),
                0.5, 0.5,
                255, 255, 255, 255,
            ))
        group.append(verts)

batches = []
for texture, triangles in groups.items():
    for start in range(0, len(triangles), MAX_TRIS_PER_BATCH):
        chunk = triangles[start:start + MAX_TRIS_PER_BATCH]
        vertices = []
        indices = []
        mn = Vector((1e30, 1e30, 1e30))
        mx = Vector((-1e30, -1e30, -1e30))
        for tri in chunk:
            for vertex in tri:
                idx = len(vertices)
                if idx >= 65535:
                    raise RuntimeError("weapon XZSM batch exceeded uint16 vertex limit")
                vertices.append(vertex)
                indices.append(idx)
                x, y, z = vertex[:3]
                mn.x = min(mn.x, x); mn.y = min(mn.y, y); mn.z = min(mn.z, z)
                mx.x = max(mx.x, x); mx.y = max(mx.y, y); mx.z = max(mx.z, z)
        batches.append({
            "texture": texture,
            "vertices": vertices,
            "indices": indices,
            "mins": mn,
            "maxs": mx,
        })

model_path = MODEL_DIR / "standard_rifle.xzsm"
with model_path.open("wb") as handle:
    handle.write(struct.pack(
        "<4sIIII",
        b"XZSM",
        3,
        len(batches),
        sum(len(b["vertices"]) for b in batches),
        sum(len(b["indices"]) for b in batches),
    ))
    for batch in batches:
        name = batch["texture"].encode("utf-8")[:95]
        texture_field = name + b"\0" * (96 - len(name))
        handle.write(struct.pack(
            "<II96s6f",
            len(batch["vertices"]),
            len(batch["indices"]),
            texture_field,
            batch["mins"].x, batch["mins"].y, batch["mins"].z,
            batch["maxs"].x, batch["maxs"].y, batch["maxs"].z,
        ))
        for vertex in batch["vertices"]:
            handle.write(struct.pack("<8f4B", *vertex))
        handle.write(struct.pack("<" + "H" * len(batch["indices"]), *batch["indices"]))

animations = sorted({action.name for action in bpy.data.actions})
dimensions = bounds_max - bounds_min
report = {
    "format": "XZSM",
    "version": 3,
    "source": str(SOURCE),
    "license": "CC0-1.0",
    "sourcePage": "https://3dassets.dev/assets/mega-weapon-pack-standard-rifle-94762172",
    "sourceDownload": "https://cdn.3dassets.dev/assets/33318/v1/model.glb",
    "coordinateSpace": "viewmodel_y_up_z_forward",
    "sourceTriangles": source_triangles,
    "batchCount": len(batches),
    "materialCount": len(material_records),
    "totalVertices": sum(len(b["vertices"]) for b in batches),
    "totalIndices": sum(len(b["indices"]) for b in batches),
    "modelBytes": model_path.stat().st_size,
    "boundsMin": list(bounds_min),
    "boundsMax": list(bounds_max),
    "dimensionsMeters": list(dimensions),
    "animations": animations,
    "materials": material_records,
}
REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

print("XZIEL_WEAPON_XZSM_READY", json.dumps({
    "triangles": source_triangles,
    "batches": len(batches),
    "materials": len(material_records),
    "dimensionsMeters": list(dimensions),
    "animations": animations,
    "modelBytes": model_path.stat().st_size,
}))
