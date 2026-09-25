import bpy
import json
import math
import os
import re
import struct
from pathlib import Path
from mathutils import Vector

SOURCE = Path(os.environ.get("WEAPON_SOURCE", "church/source/weapons/akm_fps.glb"))
RUNTIME_ROOT = Path(os.environ.get("XZIEL_STATIC_RUNTIME_ROOT", "church/out/xziel_native_static"))
MODEL_DIR = RUNTIME_ROOT / "models" / "xziel" / "weapons"
TEXTURE_DIR = RUNTIME_ROOT / "textures" / "xziel" / "weapons" / "standard_rifle"
REPORT = RUNTIME_ROOT / "weapon_standard_rifle_report.json"
SOURCE_PAGE = os.environ.get(
    "WEAPON_SOURCE_PAGE",
    "https://sketchfab.com/3d-models/akm-fps-animation-a0e1e52051294bebb8a716df9e69434d",
)
SOURCE_LICENSE = os.environ.get("WEAPON_LICENSE", "CC-BY-4.0")
SOURCE_UID = os.environ.get("WEAPON_UID", "a0e1e52051294bebb8a716df9e69434d")

MODEL_DIR.mkdir(parents=True, exist_ok=True)
TEXTURE_DIR.mkdir(parents=True, exist_ok=True)

MAX_TRIS_PER_BATCH = 18000

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
scene = bpy.context.scene

actions = list(bpy.data.actions)
animations = sorted({action.name for action in actions})

# XZIEL currently renders this asset as a rigid first-person viewmodel.  Do
# not bake an arbitrary imported animation frame: on this Sketchfab GLB the
# animated armature evaluation collapses several rigid AKM pieces into the
# armature origin.  Force the skeleton to REST and export the original mesh
# data/object transforms instead.  Native skeletal animation can later use a
# separate skinned path without corrupting the static checkpoint.
pose_action = None
for obj in scene.objects:
    if obj.type == "ARMATURE":
        if obj.animation_data is not None:
            obj.animation_data.action = None
            obj.animation_data.use_nla = False
        obj.data.pose_position = "REST"

scene.frame_set(0)

mesh_objects = [o for o in scene.objects if o.type == "MESH"]
if not mesh_objects:
    raise RuntimeError("weapon GLB imported no mesh objects")

def safe_name(value):
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", value or "material")
    return value[:48] or "material"

# The source contains FPS arms in a generic material named TEXTURA.  The
# engine's current static viewmodel path should contain the rifle only; arms
# will get their own skinned animation path.  Keep all named AKM components
# and reject obvious arm/hand/glove materials.
def weapon_material_allowed(mat):
    if mat is None:
        return False
    name = mat.name.strip().lower()
    if name == "textura":
        return False
    if name in {"arm", "arms", "hand", "hands", "forearm", "forearms", "glove", "gloves"}:
        return False
    if name.startswith(("arm_", "arms_", "hand_", "hands_", "forearm_", "glove_")):
        return False
    return True

def material_color(mat):
    if mat and mat.use_nodes and mat.node_tree:
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf and bsdf.inputs.get("Base Color"):
            c = bsdf.inputs["Base Color"].default_value
            return tuple(max(0.0, min(1.0, float(v))) for v in c[:4])
    if mat:
        return tuple(max(0.0, min(1.0, float(v))) for v in mat.diffuse_color)
    return (0.55, 0.55, 0.55, 1.0)

def linked_image_node_from_socket(sock, visited=None):
    if not sock or not getattr(sock, "is_linked", False):
        return None
    if visited is None:
        visited = set()
    for link in sock.links:
        node = link.from_node
        if not node or node.as_pointer() in visited:
            continue
        visited.add(node.as_pointer())
        if getattr(node, "type", "") == "TEX_IMAGE" and node.image:
            return node
        for inp in getattr(node, "inputs", []):
            hit = linked_image_node_from_socket(inp, visited)
            if hit:
                return hit
    return None

def material_image_node(mat):
    if not mat or not mat.use_nodes or not mat.node_tree:
        return None
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        hit = linked_image_node_from_socket(bsdf.inputs.get("Base Color"))
        if hit:
            return hit
    candidates = [
        n for n in mat.node_tree.nodes
        if getattr(n, "type", "") == "TEX_IMAGE" and n.image
    ]
    for node in candidates:
        name = (node.image.name or "").lower()
        if any(tag in name for tag in ("basecolor", "base_color", "albedo", "diffuse", "color")):
            return node
    return candidates[0] if candidates else None

def linked_uv_map_name(sock, visited=None):
    if not sock or not getattr(sock, "is_linked", False):
        return None
    if visited is None:
        visited = set()
    for link in sock.links:
        node = link.from_node
        if not node or node.as_pointer() in visited:
            continue
        visited.add(node.as_pointer())
        kind = getattr(node, "type", "")
        if kind == "UVMAP":
            name = (getattr(node, "uv_map", "") or "").strip()
            return name or "__ACTIVE_RENDER__"
        if kind == "TEX_COORD":
            name = (getattr(link.from_socket, "name", "") or "").strip().lower()
            if name == "uv":
                return "__ACTIVE_RENDER__"
        for inp in getattr(node, "inputs", []):
            uv = linked_uv_map_name(inp, visited)
            if uv:
                return uv
    return None

def resolve_uv_layer(mesh, mat):
    requested = None
    node = material_image_node(mat)
    if node:
        requested = linked_uv_map_name(node.inputs.get("Vector"))

    if requested and requested != "__ACTIVE_RENDER__":
        layer = mesh.uv_layers.get(requested)
        if layer is not None:
            return layer.data, layer.name, "material_uvmap"

    render_layer = next(
        (candidate for candidate in mesh.uv_layers
         if getattr(candidate, "active_render", False)),
        None,
    )
    if render_layer is not None:
        return render_layer.data, render_layer.name, "active_render"
    if mesh.uv_layers.active is not None:
        return mesh.uv_layers.active.data, mesh.uv_layers.active.name, "active"
    if len(mesh.uv_layers):
        return mesh.uv_layers[0].data, mesh.uv_layers[0].name, "first"
    return None, None, "none"

material_paths = {}
material_records = {}
fallback_materials = set()
max_texture_dimension = 0

def save_material_texture(mat):
    global max_texture_dimension

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
        w, h = int(copy.size[0]), int(copy.size[1])
        max_texture_dimension = max(max_texture_dimension, w, h)
        copy.file_format = "PNG"
        try:
            copy.filepath_raw = str(dst)
            copy.save()
        except Exception:
            copy.save_render(filepath=str(dst), scene=scene)
        bpy.data.images.remove(copy)
        source_desc = image.name
    else:
        rgba = material_color(mat)
        image = bpy.data.images.new(
            stem,
            width=8,
            height=8,
            alpha=True,
            float_buffer=False,
        )
        image.pixels = list(rgba) * 64
        image.file_format = "PNG"
        image.filepath_raw = str(dst)
        image.save()
        bpy.data.images.remove(image)
        fallback_materials.add(key)

    material_paths[key] = rel
    material_records[key] = {
        "path": rel + ".png",
        "source": source_desc,
        "bytes": dst.stat().st_size,
        "baseColorFactor": list(material_color(mat)),
    }
    return rel

# Blender imports glTF +Y-up into Blender +Z-up. Xziel is +Y-up and camera
# forward is +Z, so convert back once during export.
def to_xziel(value):
    return Vector((value.x, value.z, -value.y))

# Export rigid weapon geometry from bind/rest mesh data.  Bounds are computed
# from included weapon triangles only so first-person arms cannot dominate the
# normalization scale.
static_sources = []
raw_min = Vector((1e30, 1e30, 1e30))
raw_max = Vector((-1e30, -1e30, -1e30))
source_triangles = 0
included_material_names = set()
excluded_material_names = set()

# Rigid first-person canonicalization landmarks.  The source GLB can arrive
# with any object/armature orientation, so derive weapon forward from its own
# semantic parts instead of compensating with runtime Euler angles.
barrel_sum = Vector((0.0, 0.0, 0.0))
barrel_count = 0
stock_sum = Vector((0.0, 0.0, 0.0))
stock_count = 0

for source_obj in mesh_objects:
    mesh = source_obj.data
    mesh.calc_loop_triangles()
    world = source_obj.matrix_world.copy()

    for tri in mesh.loop_triangles:
        poly = mesh.polygons[tri.polygon_index]
        mat = (
            source_obj.material_slots[poly.material_index].material
            if poly.material_index < len(source_obj.material_slots)
            else None
        )
        mat_name = mat.name if mat else "__fallback__"

        if not weapon_material_allowed(mat):
            excluded_material_names.add(mat_name)
            continue

        included_material_names.add(mat_name)
        source_triangles += 1

        material_lower = mat_name.lower()

        for loop_index in tri.loops:
            vertex_index = mesh.loops[loop_index].vertex_index
            p = to_xziel(world @ mesh.vertices[vertex_index].co)

            if "barrel" in material_lower:
                barrel_sum += p
                barrel_count += 1
            if "stock" in material_lower:
                stock_sum += p
                stock_count += 1

    static_sources.append((source_obj, mesh, world))

if source_triangles < 10000:
    raise RuntimeError(
        f"weapon-only mesh unexpectedly small: {source_triangles} triangles; "
        f"included={sorted(included_material_names)!r} "
        f"excluded={sorted(excluded_material_names)!r}"
    )

for required in ("body", "barrel", "stock", "magazine"):
    if not any(required in name.lower() for name in included_material_names):
        raise RuntimeError(
            f"weapon export missing required material family {required!r}: "
            f"{sorted(included_material_names)!r}"
        )

if barrel_count <= 0 or stock_count <= 0:
    raise RuntimeError(
        f"weapon canonicalization landmarks missing: "
        f"barrel_count={barrel_count} stock_count={stock_count}"
    )

barrel_center = barrel_sum / float(barrel_count)
stock_center = stock_sum / float(stock_count)
canonical_forward = barrel_center - stock_center
if canonical_forward.length <= 1e-6:
    raise RuntimeError("weapon stock-to-barrel forward axis collapsed")
canonical_forward.normalize()

# XZIEL source-space +Y is nominal up. Remove any component parallel to the
# rifle forward axis, then rebuild an orthonormal right/up/forward basis.
nominal_up = Vector((0.0, 1.0, 0.0))
canonical_up = nominal_up - canonical_forward * nominal_up.dot(canonical_forward)
if canonical_up.length <= 1e-5:
    nominal_up = Vector((0.0, 0.0, 1.0))
    canonical_up = nominal_up - canonical_forward * nominal_up.dot(canonical_forward)
if canonical_up.length <= 1e-5:
    raise RuntimeError("weapon canonical up axis is degenerate")
canonical_up.normalize()

canonical_right = canonical_up.cross(canonical_forward)
if canonical_right.length <= 1e-5:
    raise RuntimeError("weapon canonical right axis is degenerate")
canonical_right.normalize()
canonical_up = canonical_forward.cross(canonical_right)
canonical_up.normalize()

def canonicalize(value):
    return Vector((
        value.dot(canonical_right),
        value.dot(canonical_up),
        value.dot(canonical_forward),
    ))

# Recompute weapon-only bounds after semantic canonicalization.  This makes
# +Z point from stock toward muzzle regardless of imported GLB/armature axes.
raw_min = Vector((1e30, 1e30, 1e30))
raw_max = Vector((-1e30, -1e30, -1e30))
for source_obj, mesh, world in static_sources:
    mesh.calc_loop_triangles()
    for tri in mesh.loop_triangles:
        poly = mesh.polygons[tri.polygon_index]
        mat = (
            source_obj.material_slots[poly.material_index].material
            if poly.material_index < len(source_obj.material_slots)
            else None
        )
        if not weapon_material_allowed(mat):
            continue
        for loop_index in tri.loops:
            vertex_index = mesh.loops[loop_index].vertex_index
            p = canonicalize(
                to_xziel(world @ mesh.vertices[vertex_index].co)
            )
            raw_min.x = min(raw_min.x, p.x)
            raw_min.y = min(raw_min.y, p.y)
            raw_min.z = min(raw_min.z, p.z)
            raw_max.x = max(raw_max.x, p.x)
            raw_max.y = max(raw_max.y, p.y)
            raw_max.z = max(raw_max.z, p.z)

raw_dimensions = raw_max - raw_min
raw_longest = max(
    float(raw_dimensions.x),
    float(raw_dimensions.y),
    float(raw_dimensions.z),
    1e-6,
)

# Some Sketchfab/Objaverse FPS assets are authored in centimetres even when
# their glTF scene metadata does not expose an explicit unit scale. Normalize
# the complete ready-pose bounds to a real rifle-sized envelope instead of
# trusting source units. This keeps the static checkpoint deterministic and
# prevents a 50-metre viewmodel from entering the APK.
TARGET_LONGEST_METERS = 0.90
model_scale = TARGET_LONGEST_METERS / raw_longest

anchor = Vector((
    (raw_min.x + raw_max.x) * 0.5,
    (raw_min.y + raw_max.y) * 0.5,
    raw_min.z,
))

groups = {}
bounds_min = Vector((1e30, 1e30, 1e30))
bounds_max = Vector((-1e30, -1e30, -1e30))
uv_records = {}

for source_obj, mesh, world in static_sources:
    normal_matrix = world.to_3x3().inverted().transposed()
    mesh.calc_loop_triangles()

    for tri in mesh.loop_triangles:
        poly = mesh.polygons[tri.polygon_index]
        mat = (
            source_obj.material_slots[poly.material_index].material
            if poly.material_index < len(source_obj.material_slots)
            else None
        )
        if not weapon_material_allowed(mat):
            continue

        texture = save_material_texture(mat)
        uv_layer, uv_name, uv_source = resolve_uv_layer(mesh, mat)
        uv_records[f"{source_obj.name}:{mat.name if mat else '__fallback__'}"] = {
            "layer": uv_name,
            "source": uv_source,
        }
        group = groups.setdefault(texture, [])
        verts = []
        factor = material_color(mat)
        rgba = tuple(
            max(0, min(255, int(round(v * 255.0))))
            for v in factor
        )

        for loop_index in tri.loops:
            vertex_index = mesh.loops[loop_index].vertex_index
            p = (
                canonicalize(
                    to_xziel(
                        world @ mesh.vertices[vertex_index].co
                    )
                ) - anchor
            ) * model_scale
            n = canonicalize(
                to_xziel(
                    normal_matrix @ mesh.vertices[vertex_index].normal
                )
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
sorted_dimensions = sorted(
    [float(dimensions.x), float(dimensions.y), float(dimensions.z)],
    reverse=True,
)

# A valid AKM checkpoint must occupy a rifle-like 3D envelope, not a line or
# a tiny armature-origin cluster.  These gates intentionally fail the build
# before a malformed model can ever reach the Android APK.
if dimensions.z < 0.85 or dimensions.z > 0.95:
    raise RuntimeError(
        f"weapon canonical forward dimension invalid: "
        f"{[dimensions.x, dimensions.y, dimensions.z]}"
    )
if dimensions.y < 0.10 or dimensions.y > 0.45:
    raise RuntimeError(
        f"weapon canonical height invalid: "
        f"{[dimensions.x, dimensions.y, dimensions.z]}"
    )
if dimensions.x < 0.035 or dimensions.x > 0.20:
    raise RuntimeError(
        f"weapon canonical width invalid: "
        f"{[dimensions.x, dimensions.y, dimensions.z]}"
    )

meaningful_batches = 0
for batch in batches:
    extent = batch["maxs"] - batch["mins"]
    if max(float(extent.x), float(extent.y), float(extent.z)) >= 0.08:
        meaningful_batches += 1
if meaningful_batches < 4:
    raise RuntimeError(
        f"weapon batch layout collapsed: meaningful={meaningful_batches} "
        f"total={len(batches)}"
    )

textured_material_count = sum(
    1 for record in material_records.values()
    if record["source"] != "generated_base_color"
)

report = {
    "format": "XZSM",
    "version": 3,
    "source": str(SOURCE),
    "sourceUid": SOURCE_UID,
    "license": SOURCE_LICENSE,
    "sourcePage": SOURCE_PAGE,
    "coordinateSpace": "viewmodel_y_up_z_forward",
    "readyPoseAction": None,
    "exportMode": "rigid_weapon_rest_pose_canonical_xziel",
    "canonicalForwardSource": [
        float(canonical_forward.x),
        float(canonical_forward.y),
        float(canonical_forward.z),
    ],
    "canonicalUpSource": [
        float(canonical_up.x),
        float(canonical_up.y),
        float(canonical_up.z),
    ],
    "includedMaterials": sorted(included_material_names),
    "excludedMaterials": sorted(excluded_material_names),
    "meaningfulBatchCount": meaningful_batches,
    "sourceTriangles": source_triangles,
    "batchCount": len(batches),
    "materialCount": len(material_records),
    "texturedMaterialCount": textured_material_count,
    "fallbackMaterialCount": len(fallback_materials),
    "maximumTextureDimension": max_texture_dimension,
    "totalVertices": sum(len(b["vertices"]) for b in batches),
    "totalIndices": sum(len(b["indices"]) for b in batches),
    "modelBytes": model_path.stat().st_size,
    "boundsMin": list(bounds_min),
    "boundsMax": list(bounds_max),
    "dimensionsMeters": list(dimensions),
    "sourceBoundsDimensions": list(raw_dimensions),
    "unitNormalizationScale": model_scale,
    "targetLongestDimensionMeters": TARGET_LONGEST_METERS,
    "animations": animations,
    "materials": material_records,
    "uvBindings": uv_records,
}

REPORT.write_text(
    json.dumps(report, indent=2),
    encoding="utf-8",
)

print("XZIEL_WEAPON_XZSM_READY", json.dumps({
    "triangles": source_triangles,
    "batches": len(batches),
    "materials": len(material_records),
    "texturedMaterials": textured_material_count,
    "maximumTextureDimension": max_texture_dimension,
    "dimensionsMeters": list(dimensions),
    "unitNormalizationScale": model_scale,
    "animations": animations,
    "readyPose": None,
    "exportMode": "rigid_weapon_rest_pose_canonical_xziel",    "meaningfulBatches": meaningful_batches,
    "modelBytes": model_path.stat().st_size,
}))
