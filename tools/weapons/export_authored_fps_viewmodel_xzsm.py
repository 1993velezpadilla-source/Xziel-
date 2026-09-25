import bpy
import json
import math
import os
import re
import struct
from pathlib import Path
from mathutils import Vector

SOURCE = Path(os.environ["FPS_VIEWMODEL_SOURCE"])
RUNTIME_ROOT = Path(os.environ.get(
    "XZIEL_STATIC_RUNTIME_ROOT",
    "church/out/fps_ready/runtime",
))
MODEL_DIR = RUNTIME_ROOT / "models" / "xziel" / "weapons"
TEXTURE_DIR = RUNTIME_ROOT / "textures" / "xziel" / "weapons" / "standard_rifle"
REPORT = RUNTIME_ROOT / "fps_authored_viewmodel_report.json"

SOURCE_PAGE = os.environ.get(
    "FPS_SOURCE_PAGE",
    "https://opengameart.org/content/low-poly-fps-rifle-and-hands",
)
SOURCE_LICENSE = os.environ.get("FPS_SOURCE_LICENSE", "CC0")
SOURCE_AUTHOR = os.environ.get("FPS_SOURCE_AUTHOR", "Robin Lamb")

TARGET_GUN_LENGTH_METERS = 0.90
MAX_TRIS_PER_BATCH = 18000

MODEL_DIR.mkdir(parents=True, exist_ok=True)
TEXTURE_DIR.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE.resolve()))
scene = bpy.context.scene

mesh_objects = [obj for obj in scene.objects if obj.type == "MESH"]
armatures = [obj for obj in scene.objects if obj.type == "ARMATURE"]
actions = list(bpy.data.actions)

if not mesh_objects:
    raise RuntimeError("FPS viewmodel imported no mesh objects")

fire_action = next(
    (action for action in actions if "fire" in action.name.lower() or "shoot" in action.name.lower()),
    actions[0] if actions else None,
)

if fire_action is not None:
    for armature in armatures:
        armature.animation_data_create()
        armature.animation_data.action = fire_action
        armature.data.pose_position = "POSE"
    scene.frame_set(int(round(float(fire_action.frame_range[0]))))
else:
    scene.frame_set(1)

depsgraph = bpy.context.evaluated_depsgraph_get()
depsgraph.update()


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
    return (0.55, 0.55, 0.55, 1.0)


def material_image_node(mat):
    if not mat or not mat.use_nodes or not mat.node_tree:
        return None
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf and bsdf.inputs.get("Base Color"):
        sock = bsdf.inputs.get("Base Color")
        if sock and sock.is_linked:
            for link in sock.links:
                node = link.from_node
                if getattr(node, "type", "") == "TEX_IMAGE" and node.image:
                    return node
    for node in mat.node_tree.nodes:
        if getattr(node, "type", "") == "TEX_IMAGE" and node.image:
            return node
    return None


def resolve_uv_layer(mesh):
    render_layer = next(
        (candidate for candidate in mesh.uv_layers
         if getattr(candidate, "active_render", False)),
        None,
    )
    if render_layer is not None:
        return render_layer.data, render_layer.name
    if mesh.uv_layers.active is not None:
        return mesh.uv_layers.active.data, mesh.uv_layers.active.name
    if len(mesh.uv_layers):
        return mesh.uv_layers[0].data, mesh.uv_layers[0].name
    return None, None


material_paths = {}
material_records = {}
fallback_materials = set()


def save_material_texture(mat):
    key = mat.name if mat else "__fallback__"
    if key in material_paths:
        return material_paths[key]

    index = len(material_paths)
    stem = f"mat_{index:02d}_{safe_name(key)}"
    dst = TEXTURE_DIR / f"{stem}.png"
    rel = f"textures/xziel/weapons/standard_rifle/{stem}"

    node = material_image_node(mat)
    image = node.image if node and node.image else None
    source_desc = "generated_base_color"

    if image is not None and image.size[0] > 0 and image.size[1] > 0:
        copy = image.copy()
        copy.file_format = "PNG"
        try:
            copy.filepath_raw = str(dst)
            copy.save()
        except Exception:
            copy.save_render(filepath=str(dst), scene=scene)
        source_desc = image.name
        bpy.data.images.remove(copy)
    else:
        rgba = material_color(mat)
        generated = bpy.data.images.new(
            stem,
            width=8,
            height=8,
            alpha=True,
            float_buffer=False,
        )
        generated.pixels = list(rgba) * 64
        generated.file_format = "PNG"
        generated.filepath_raw = str(dst)
        generated.save()
        bpy.data.images.remove(generated)
        fallback_materials.add(key)

    material_paths[key] = rel
    material_records[key] = {
        "path": rel + ".png",
        "source": source_desc,
        "baseColorFactor": list(material_color(mat)),
        "bytes": dst.stat().st_size,
    }
    return rel


# Blender imports glTF +Y-up as Blender +Z-up. The source is an authored FPS
# scene looking toward glTF -Z. XZIEL viewmodels look toward +Z. Preserve the
# authored screen-space X/Y composition and flip only camera depth.
#
# Imported Blender coordinates are approximately:
#   bx = glTF x, by = -glTF z, bz = glTF y
# therefore XZIEL authored coordinates become:
#   x = bx, y = bz, z = by
#
# This reflection requires reversing triangle winding below.
def to_xziel_authored(value):
    return Vector((value.x, value.z, value.y))


baked_sources = []
source_mesh_names = []
gun_min = Vector((1e30, 1e30, 1e30))
gun_max = Vector((-1e30, -1e30, -1e30))
source_triangles = 0

for source_obj in mesh_objects:
    evaluated = source_obj.evaluated_get(depsgraph)
    mesh = bpy.data.meshes.new_from_object(
        evaluated,
        preserve_all_data_layers=True,
        depsgraph=depsgraph,
    )
    world = evaluated.matrix_world.copy()
    mesh.calc_loop_triangles()

    source_mesh_names.append(source_obj.name)
    source_triangles += len(mesh.loop_triangles)

    is_gun = "gun" in source_obj.name.lower() or "rifle" in source_obj.name.lower()
    if is_gun:
        for vertex in mesh.vertices:
            p = to_xziel_authored(world @ vertex.co)
            gun_min.x = min(gun_min.x, p.x)
            gun_min.y = min(gun_min.y, p.y)
            gun_min.z = min(gun_min.z, p.z)
            gun_max.x = max(gun_max.x, p.x)
            gun_max.y = max(gun_max.y, p.y)
            gun_max.z = max(gun_max.z, p.z)

    baked_sources.append((source_obj, mesh, world))

if gun_min.x > 1e20:
    raise RuntimeError(f"FPS viewmodel has no Gun/Rifle mesh: {source_mesh_names!r}")

gun_dimensions = gun_max - gun_min
gun_forward_length = float(gun_dimensions.z)

if not math.isfinite(gun_forward_length) or gun_forward_length <= 1e-5:
    raise RuntimeError(f"FPS gun forward length invalid: {list(gun_dimensions)!r}")

# The authored asset must actually be gun-like in the expected camera space.
if gun_forward_length < max(float(gun_dimensions.x), float(gun_dimensions.y)):
    raise RuntimeError(
        f"FPS gun is not longest along camera depth: {list(gun_dimensions)!r}"
    )

model_scale = TARGET_GUN_LENGTH_METERS / gun_forward_length

groups = {}
bounds_min = Vector((1e30, 1e30, 1e30))
bounds_max = Vector((-1e30, -1e30, -1e30))
mesh_triangle_counts = {}
uv_bindings = {}

for source_obj, mesh, world in baked_sources:
    normal_matrix = world.to_3x3().inverted().transposed()
    mesh.calc_loop_triangles()
    mesh_triangle_counts[source_obj.name] = len(mesh.loop_triangles)

    for tri in mesh.loop_triangles:
        poly = mesh.polygons[tri.polygon_index]
        mat = (
            source_obj.material_slots[poly.material_index].material
            if poly.material_index < len(source_obj.material_slots)
            else None
        )
        texture = save_material_texture(mat)
        uv_layer, uv_name = resolve_uv_layer(mesh)
        uv_bindings[f"{source_obj.name}:{mat.name if mat else '__fallback__'}"] = uv_name

        factor = material_color(mat)
        rgba = tuple(
            max(0, min(255, int(round(v * 255.0))))
            for v in factor
        )

        verts = []

        # authored depth conversion is reflective; reverse loop order so Vulkan
        # front-face winding remains consistent.
        loop_order = (tri.loops[0], tri.loops[2], tri.loops[1])

        for loop_index in loop_order:
            vertex_index = mesh.loops[loop_index].vertex_index

            p = to_xziel_authored(
                world @ mesh.vertices[vertex_index].co
            ) * model_scale

            n = to_xziel_authored(
                normal_matrix @ mesh.vertices[vertex_index].normal
            )
            if n.length > 1e-8:
                n.normalize()
            else:
                n = Vector((0.0, 1.0, 0.0))

            if uv_layer is not None:
                uv = uv_layer[loop_index].uv
                u = float(uv.x)
                v = float(uv.y)
            else:
                u = 0.5
                v = 0.5

            bounds_min.x = min(bounds_min.x, p.x)
            bounds_min.y = min(bounds_min.y, p.y)
            bounds_min.z = min(bounds_min.z, p.z)
            bounds_max.x = max(bounds_max.x, p.x)
            bounds_max.y = max(bounds_max.y, p.y)
            bounds_max.z = max(bounds_max.z, p.z)

            verts.append((
                float(p.x), float(p.y), float(p.z),
                float(n.x), float(n.y), float(n.z),
                u, v,
                rgba[0], rgba[1], rgba[2], rgba[3],
            ))

        groups.setdefault(texture, []).append(verts)


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
                    raise RuntimeError("FPS XZSM batch exceeded uint16 vertex limit")
                vertices.append(vertex)
                indices.append(idx)
                x, y, z = vertex[:3]
                mn.x = min(mn.x, x)
                mn.y = min(mn.y, y)
                mn.z = min(mn.z, z)
                mx.x = max(mx.x, x)
                mx.y = max(mx.y, y)
                mx.z = max(mx.z, z)

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
        sum(len(batch["vertices"]) for batch in batches),
        sum(len(batch["indices"]) for batch in batches),
    ))

    for batch in batches:
        name = batch["texture"].encode("utf-8")[:95]
        texture_field = name + b"\0" * (96 - len(name))
        handle.write(struct.pack(
            "<II96s6f",
            len(batch["vertices"]),
            len(batch["indices"]),
            texture_field,
            batch["mins"].x,
            batch["mins"].y,
            batch["mins"].z,
            batch["maxs"].x,
            batch["maxs"].y,
            batch["maxs"].z,
        ))

        for vertex in batch["vertices"]:
            handle.write(struct.pack("<8f4B", *vertex))

        handle.write(struct.pack(
            "<" + "H" * len(batch["indices"]),
            *batch["indices"],
        ))


dimensions = bounds_max - bounds_min
animations = sorted(action.name for action in actions)
has_hands = any("hand" in name.lower() or "arm" in name.lower() for name in source_mesh_names)
has_gun = any("gun" in name.lower() or "rifle" in name.lower() for name in source_mesh_names)

if not has_gun or not has_hands:
    raise RuntimeError(
        f"FPS authored export missing gun/hands: meshes={source_mesh_names!r}"
    )

if source_triangles < 150:
    raise RuntimeError(
        f"FPS authored export unexpectedly small: {source_triangles} triangles"
    )

if not (0.85 <= float(gun_dimensions.z) * model_scale <= 0.95):
    raise RuntimeError(
        f"FPS authored gun length normalization failed: "
        f"{float(gun_dimensions.z) * model_scale}"
    )

if bounds_max.z <= 0.45:
    raise RuntimeError(
        f"FPS authored barrel does not project forward enough: bounds={list(dimensions)!r}"
    )

report = {
    "format": "XZSM",
    "version": 3,
    "source": str(SOURCE),
    "sourcePage": SOURCE_PAGE,
    "sourceLicense": SOURCE_LICENSE,
    "sourceAuthor": SOURCE_AUTHOR,
    "exportMode": "authored_fps_viewmodel_rest_pose_v1",
    "coordinateSpace": "x_right_y_up_z_forward_authored_camera_pivot",
    "pivotSemantic": "source_armature_origin_preserved",
    "restFrame": int(round(float(fire_action.frame_range[0]))) if fire_action else 1,
    "fireAction": fire_action.name if fire_action else None,
    "animations": animations,
    "sourceMeshes": source_mesh_names,
    "meshTriangleCounts": mesh_triangle_counts,
    "sourceTriangles": source_triangles,
    "gunSourceDimensions": list(gun_dimensions),
    "targetGunLengthMeters": TARGET_GUN_LENGTH_METERS,
    "unitNormalizationScale": model_scale,
    "boundsMin": list(bounds_min),
    "boundsMax": list(bounds_max),
    "dimensionsMeters": list(dimensions),
    "batchCount": len(batches),
    "materialCount": len(material_records),
    "fallbackMaterialCount": len(fallback_materials),
    "totalVertices": sum(len(batch["vertices"]) for batch in batches),
    "totalIndices": sum(len(batch["indices"]) for batch in batches),
    "modelBytes": model_path.stat().st_size,
    "materials": material_records,
    "uvBindings": uv_bindings,
}

REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

print("XZIEL_AUTHORED_FPS_XZSM_READY", json.dumps({
    "meshes": source_mesh_names,
    "triangles": source_triangles,
    "batches": len(batches),
    "materials": len(material_records),
    "gunLengthMeters": float(gun_dimensions.z) * model_scale,
    "dimensionsMeters": list(dimensions),
    "modelScale": model_scale,
    "fireAction": fire_action.name if fire_action else None,
    "modelBytes": model_path.stat().st_size,
}))
