import bpy
import json
import os
import re
import shutil
import struct
import tempfile
import hashlib
import io
from pathlib import Path
from mathutils import Vector
from PIL import Image

SOURCE = Path(os.environ.get("CHURCH_SOURCE", "church/source/st-giles-cripplegate.glb"))
PLAN_PATH = Path(os.environ.get("CHURCH_PLAN", "church/seed/zombies_map_plan.json"))
RUNTIME_ROOT = Path(os.environ.get("XZIEL_STATIC_RUNTIME_ROOT", "church/out/clean/xziel_native_static"))
REPORT_PATH = Path(os.environ.get("XZIEL_STATIC_REPORT", "church/out/clean/xziel_native_static_mesh_report.json"))
NATIVE_FLOOR_Y = float(os.environ.get("XZIEL_STATIC_NATIVE_FLOOR_Y", "-1.58"))
MAX_TRIS_PER_BATCH = int(os.environ.get("XZIEL_STATIC_BATCH_TRIS", "18000"))
SOURCE_UID = "b92917ff83914adc8bc93959ba8b4399"

MODEL_DIR = RUNTIME_ROOT / "models" / "xziel" / "sanctum"
TEXTURE_DIR = RUNTIME_ROOT / "textures" / "xziel" / "sanctum"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
TEXTURE_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

if not SOURCE.is_file():
    raise RuntimeError(f"missing original church GLB: {SOURCE}")
if not PLAN_PATH.is_file():
    raise RuntimeError(f"missing validated gameplay plan: {PLAN_PATH}")

# Parse the original GLB texture payload before Blender touches it.
# Material -> embedded base-color image mapping comes from glTF JSON, not from
# Blender node names. Runtime pixels are decoded directly from the source GLB.
glb_bytes = SOURCE.read_bytes()
if glb_bytes[:4] != b"glTF":
    raise RuntimeError("source is not a GLB")
_, glb_version, glb_length = struct.unpack_from("<4sII", glb_bytes, 0)
if glb_version != 2 or glb_length != len(glb_bytes):
    raise RuntimeError("unexpected GLB header")

cursor = 12
glb_json = None
glb_bin = None
while cursor + 8 <= len(glb_bytes):
    chunk_length, chunk_type = struct.unpack_from("<II", glb_bytes, cursor)
    cursor += 8
    payload = glb_bytes[cursor:cursor + chunk_length]
    cursor += chunk_length
    if chunk_type == 0x4E4F534A:
        glb_json = payload.rstrip(b"\x00 \t\r\n")
    elif chunk_type == 0x004E4942:
        glb_bin = payload

if glb_json is None or glb_bin is None:
    raise RuntimeError("GLB missing JSON/BIN chunks")

glb_doc = json.loads(glb_json.decode("utf-8"))
glb_views = glb_doc.get("bufferViews", [])
glb_images = glb_doc.get("images", [])
glb_textures = glb_doc.get("textures", [])
glb_materials = glb_doc.get("materials", [])

embedded_by_material = {}
embedded_records = {}

for material_index, material in enumerate(glb_materials):
    pbr = material.get("pbrMetallicRoughness", {})
    texture_index = pbr.get("baseColorTexture", {}).get("index")
    if texture_index is None or texture_index >= len(glb_textures):
        continue
    image_index = glb_textures[texture_index].get("source")
    if image_index is None or image_index >= len(glb_images):
        continue
    image_info = glb_images[image_index]
    view_index = image_info.get("bufferView")
    if view_index is None or view_index >= len(glb_views):
        continue
    view = glb_views[view_index]
    offset = int(view.get("byteOffset", 0))
    size = int(view["byteLength"])
    encoded = glb_bin[offset:offset + size]
    if len(encoded) != size:
        raise RuntimeError(f"truncated embedded image {image_index}")

    with Image.open(io.BytesIO(encoded)) as decoded:
        rgba = decoded.convert("RGBA")
        raw = rgba.tobytes()
        record = {
            "imageIndex": image_index,
            "materialIndex": material_index,
            "materialName": material.get("name"),
            "imageName": image_info.get("name"),
            "mimeType": image_info.get("mimeType"),
            "dimensions": [rgba.width, rgba.height],
            "decodedSha256": hashlib.sha256(raw).hexdigest(),
            "encodedSha256": hashlib.sha256(encoded).hexdigest(),
            "rgba": rgba.copy(),
        }
    embedded_records[material_index] = record
    if material.get("name"):
        embedded_by_material[material["name"]] = record

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
scene = bpy.context.scene

# glTF import preserves material declaration order. Bind the imported Blender
# material datablocks to original glTF material indices once, so texture
# identity never depends on rewritten/suffixed material names.
blender_materials = list(bpy.data.materials)
if len(blender_materials) != len(glb_materials):
    raise RuntimeError(
        f"material count changed during import: glTF={len(glb_materials)} "
        f"Blender={len(blender_materials)}"
    )

embedded_by_blender_pointer = {}
gltf_index_by_blender_pointer = {}
for material_index, blender_material in enumerate(blender_materials):
    gltf_index_by_blender_pointer[
        blender_material.as_pointer()
    ] = material_index

    record = embedded_records.get(material_index)
    if record is not None:
        embedded_by_blender_pointer[
            blender_material.as_pointer()
        ] = record

objects = [obj for obj in scene.objects if obj.type == "MESH"]
if not objects:
    raise RuntimeError("original church GLB imported no mesh objects")

plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
zones = [value for key, value in plan["zones"].items() if key != "other"]
global_min = Vector((
    min(zone["min"][0] for zone in zones),
    min(zone["min"][1] for zone in zones),
    min(zone["min"][2] for zone in zones),
))
global_max = Vector((
    max(zone["max"][0] for zone in zones),
    max(zone["max"][1] for zone in zones),
    max(zone["max"][2] for zone in zones),
))
center = (global_min + global_max) * 0.5

def safe_name(value):
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", value or "material")
    return value[:48] or "material"

def linked_image(socket, visited=None):
    if socket is None or not getattr(socket, "is_linked", False):
        return None
    if visited is None:
        visited = set()
    for link in socket.links:
        node = link.from_node
        if node is None:
            continue
        pointer = node.as_pointer()
        if pointer in visited:
            continue
        visited.add(pointer)
        if getattr(node, "type", "") == "TEX_IMAGE" and node.image:
            return node
        for input_socket in getattr(node, "inputs", []):
            hit = linked_image(input_socket, visited)
            if hit is not None:
                return hit
    return None

def principled(mat):
    if mat is None or not mat.use_nodes or mat.node_tree is None:
        return None
    return mat.node_tree.nodes.get("Principled BSDF")

def base_color_node(mat):
    bsdf = principled(mat)
    if bsdf is not None:
        hit = linked_image(bsdf.inputs.get("Base Color"))
        if hit is not None:
            return hit
    if mat is not None and mat.use_nodes and mat.node_tree is not None:
        for node in mat.node_tree.nodes:
            if getattr(node, "type", "") == "TEX_IMAGE" and node.image:
                return node
    return None

def linked_uv_name(node):
    if node is None:
        return None
    socket = node.inputs.get("Vector")
    if socket is None or not socket.is_linked:
        return None
    pending = [link.from_node for link in socket.links]
    visited = set()
    while pending:
        current = pending.pop()
        if current is None:
            continue
        pointer = current.as_pointer()
        if pointer in visited:
            continue
        visited.add(pointer)
        kind = getattr(current, "type", "")
        if kind == "UVMAP":
            return (getattr(current, "uv_map", "") or "").strip() or "__ACTIVE_RENDER__"
        if kind == "TEX_COORD":
            return "__ACTIVE_RENDER__"
        for input_socket in getattr(current, "inputs", []):
            if getattr(input_socket, "is_linked", False):
                pending.extend(link.from_node for link in input_socket.links)
    return None

def resolve_uv_layer(mesh, mat):
    node = base_color_node(mat)
    requested = linked_uv_name(node)
    if requested and requested != "__ACTIVE_RENDER__":
        layer = mesh.uv_layers.get(requested)
        if layer is not None:
            return layer.data, layer.name, "material_uvmap"
    render_layer = next(
        (layer for layer in mesh.uv_layers if getattr(layer, "active_render", False)),
        None,
    )
    if render_layer is not None:
        return render_layer.data, render_layer.name, "active_render"
    if mesh.uv_layers.active is not None:
        layer = mesh.uv_layers.active
        return layer.data, layer.name, "active"
    if len(mesh.uv_layers):
        layer = mesh.uv_layers[0]
        return layer.data, layer.name, "first"
    return None, None, "none"

material_paths = {}
material_report = {}
missing_uv = set()
fallback_materials = set()
max_texture_dimension = 0

def save_material_texture(mat):
    global max_texture_dimension
    key = mat.name if mat is not None else "__fallback__"
    if key in material_paths:
        return material_paths[key]

    index = len(material_paths)
    stem = f"mat_{index:02d}_{safe_name(key)}"
    dst = TEXTURE_DIR / f"{stem}.png"
    rel = f"textures/xziel/sanctum/{stem}"

    # Source-of-truth path: decoded pixels come directly from the embedded GLB
    # baseColor image selected by the original glTF material. Blender is used
    # only for mesh/UV access and cannot color-manage/re-save these pixels.
    record = (
        embedded_by_blender_pointer.get(mat.as_pointer())
        if mat is not None
        else None
    )

    # Name matching remains diagnostic fallback only. The authoritative path
    # above is Blender-material pointer -> original glTF material index.
    if record is None:
        record = embedded_by_material.get(key)
    if record is None:
        for original_name, candidate in embedded_by_material.items():
            if key == original_name or key.startswith(original_name + "."):
                record = candidate
                break

    source_name = None
    source_size = [8, 8]
    decoded_sha = None
    source_mode = "fallback"

    if record is not None:
        rgba = record["rgba"]
        source_name = record.get("imageName")
        source_size = list(record["dimensions"])
        decoded_sha = record["decodedSha256"]
        max_texture_dimension = max(
            max_texture_dimension,
            source_size[0],
            source_size[1],
        )
        rgba.save(dst, format="PNG")
        source_mode = "original_glb_embedded_pixels"
    else:
        node = base_color_node(mat)
        image = node.image if node is not None else None
        if image is not None and image.size[0] > 0 and image.size[1] > 0:
            # Diagnostic fallback only. A clean build must not hit this path.
            source_name = image.name
            source_size = [int(image.size[0]), int(image.size[1])]
            max_texture_dimension = max(
                max_texture_dimension,
                source_size[0],
                source_size[1],
            )
            copy = image.copy()
            copy.file_format = "PNG"
            copy.filepath_raw = str(dst)
            try:
                copy.save()
            except Exception:
                copy.save_render(filepath=str(dst), scene=scene)
            bpy.data.images.remove(copy)
            source_mode = "blender_fallback"
        else:
            fallback_materials.add(key)
            rgba = (0.5, 0.5, 0.5, 1.0)
            if mat is not None:
                rgba = tuple(float(v) for v in mat.diffuse_color)
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

    # Verify the PNG we will package decodes to the exact source GLB pixels.
    runtime_sha = None
    if dst.is_file():
        with Image.open(dst) as runtime_image:
            runtime_rgba = runtime_image.convert("RGBA")
            runtime_sha = hashlib.sha256(runtime_rgba.tobytes()).hexdigest()

    if decoded_sha is not None and runtime_sha != decoded_sha:
        raise RuntimeError(
            f"source pixel fidelity lost for material {key}: "
            f"source={decoded_sha} runtime={runtime_sha}"
        )

    bsdf = principled(mat)
    pbr = {}
    if bsdf is not None:
        for label in ("Base Color", "Roughness", "Metallic", "Normal"):
            hit = linked_image(bsdf.inputs.get(label))
            pbr[label] = hit.image.name if hit is not None and hit.image else None

    material_paths[key] = rel
    material_report[key] = {
        "texturePath": rel + ".png",
        "sourceImage": source_name,
        "sourceSize": source_size,
        "sourceMode": source_mode,
        "sourceDecodedSha256": decoded_sha,
        "runtimeDecodedSha256": runtime_sha,
        "exactSourcePixels": (
            decoded_sha is not None and runtime_sha == decoded_sha
        ),
        "bytes": dst.stat().st_size,
        "linkedPbrImages": pbr,
    }
    return rel

def transform_position(world_position):
    delta = world_position - center
    return Vector((
        delta.x,
        (world_position.z - global_min.z) + NATIVE_FLOOR_Y,
        -delta.y,
    ))

def transform_normal(world_normal):
    result = Vector((world_normal.x, world_normal.z, -world_normal.y))
    if result.length > 1e-8:
        result.normalize()
    else:
        result = Vector((0.0, 1.0, 0.0))
    return result

source_triangles = 0
bounds_min = Vector((1e30, 1e30, 1e30))
bounds_max = Vector((-1e30, -1e30, -1e30))
batch_records = []
total_vertices = 0
total_indices = 0

with tempfile.TemporaryDirectory(prefix="xziel-clean-") as tmp:
    tmpdir = Path(tmp)

    def flush_batch(obj, material_index, triangles, batch_number):
        mesh = obj.data
        world = obj.matrix_world
        normal_matrix = world.to_3x3().inverted().transposed()
        mat = (
            obj.material_slots[material_index].material
            if material_index < len(obj.material_slots)
            else None
        )
        texture = save_material_texture(mat)

        gltf_material_index = (
            gltf_index_by_blender_pointer.get(mat.as_pointer())
            if mat is not None
            else None
        )

        gltf_material = (
            glb_materials[gltf_material_index]
            if gltf_material_index is not None
            else {}
        )

        gltf_double_sided = bool(
            gltf_material.get("doubleSided", False)
        )

        # This source is an open photogrammetry shell, not a watertight game
        # mesh. Its glTF material flags are not sufficient to guarantee that
        # interior-facing triangles have matching front faces. Runtime
        # backface culling visibly removes walls/floors when the player walks
        # inside the church. Keep this legacy scan two-sided while retaining
        # XZSM v4 material flags for future authored/watertight assets.
        double_sided = True

        # XZSM v4 batch flag bit 0 == double-sided.
        batch_flags = 1 if double_sided else 0

        uv_layer, uv_name, uv_source = resolve_uv_layer(mesh, mat)
        if base_color_node(mat) is not None and uv_layer is None:
            missing_uv.add(obj.name)

        vertices = []
        indices = []
        vertex_map = {}
        batch_min = Vector((1e30, 1e30, 1e30))
        batch_max = Vector((-1e30, -1e30, -1e30))

        for tri in triangles:
            for loop_index in tri.loops:
                vertex_index = mesh.loops[loop_index].vertex_index
                p = transform_position(world @ mesh.vertices[vertex_index].co)
                n = transform_normal(normal_matrix @ mesh.vertices[vertex_index].normal)
                if uv_layer is not None:
                    uv = uv_layer[loop_index].uv
                    u = float(uv.x)
                    v = 1.0 - float(uv.y)
                else:
                    u = 0.0
                    v = 0.0

                vertex = (
                    float(p.x), float(p.y), float(p.z),
                    float(n.x), float(n.y), float(n.z),
                    u, v,
                    255, 255, 255, 255,
                )
                index = vertex_map.get(vertex)
                if index is None:
                    index = len(vertices)
                    if index >= 65535:
                        raise RuntimeError(f"batch exceeded uint16 vertices: {obj.name}")
                    vertex_map[vertex] = index
                    vertices.append(vertex)
                    batch_min.x = min(batch_min.x, p.x)
                    batch_min.y = min(batch_min.y, p.y)
                    batch_min.z = min(batch_min.z, p.z)
                    batch_max.x = max(batch_max.x, p.x)
                    batch_max.y = max(batch_max.y, p.y)
                    batch_max.z = max(batch_max.z, p.z)
                indices.append(index)

        payload = tmpdir / f"batch_{batch_number:04d}.bin"
        with payload.open("wb") as handle:
            for vertex in vertices:
                handle.write(struct.pack("<8f4B", *vertex))
            handle.write(struct.pack("<" + "H" * len(indices), *indices))

        return {
            "object": obj.name,
            "material": mat.name if mat is not None else "__fallback__",
            "texture": texture,
            "uvLayer": uv_name,
            "uvSource": uv_source,
            "gltfDoubleSided": gltf_double_sided,
            "doubleSided": double_sided,
            "flags": batch_flags,
            "vertexCount": len(vertices),
            "indexCount": len(indices),
            "mins": batch_min,
            "maxs": batch_max,
            "payload": payload,
        }

    batch_number = 0
    for obj in objects:
        mesh = obj.data
        mesh.calc_loop_triangles()
        source_triangles += len(mesh.loop_triangles)

        chunks = {}
        for tri in mesh.loop_triangles:
            material_index = mesh.polygons[tri.polygon_index].material_index
            chunk = chunks.setdefault(material_index, [])
            chunk.append(tri)
            if len(chunk) >= MAX_TRIS_PER_BATCH:
                record = flush_batch(obj, material_index, chunk, batch_number)
                batch_number += 1
                batch_records.append(record)
                total_vertices += record["vertexCount"]
                total_indices += record["indexCount"]
                bounds_min.x = min(bounds_min.x, record["mins"].x)
                bounds_min.y = min(bounds_min.y, record["mins"].y)
                bounds_min.z = min(bounds_min.z, record["mins"].z)
                bounds_max.x = max(bounds_max.x, record["maxs"].x)
                bounds_max.y = max(bounds_max.y, record["maxs"].y)
                bounds_max.z = max(bounds_max.z, record["maxs"].z)
                chunks[material_index] = []

        for material_index, chunk in chunks.items():
            if not chunk:
                continue
            record = flush_batch(obj, material_index, chunk, batch_number)
            batch_number += 1
            batch_records.append(record)
            total_vertices += record["vertexCount"]
            total_indices += record["indexCount"]
            bounds_min.x = min(bounds_min.x, record["mins"].x)
            bounds_min.y = min(bounds_min.y, record["mins"].y)
            bounds_min.z = min(bounds_min.z, record["mins"].z)
            bounds_max.x = max(bounds_max.x, record["maxs"].x)
            bounds_max.y = max(bounds_max.y, record["maxs"].y)
            bounds_max.z = max(bounds_max.z, record["maxs"].z)

    if source_triangles < 2700000:
        raise RuntimeError(f"original church unexpectedly lost geometry: {source_triangles}")
    if missing_uv:
        raise RuntimeError("textured source meshes missing UVs: " + ", ".join(sorted(missing_uv)))

    model_path = MODEL_DIR / "sanctum.xzsm"
    with model_path.open("wb") as out:
        out.write(struct.pack(
            "<4sIIII",
            b"XZSM",
            4,
            len(batch_records),
            total_vertices,
            total_indices,
        ))
        for batch in batch_records:
            texture_bytes = batch["texture"].encode("utf-8")[:95]
            texture_field = texture_bytes + b"\0" * (96 - len(texture_bytes))
            out.write(struct.pack(
                "<II96sI6f",
                batch["vertexCount"],
                batch["indexCount"],
                texture_field,
                batch["flags"],
                batch["mins"].x, batch["mins"].y, batch["mins"].z,
                batch["maxs"].x, batch["maxs"].y, batch["maxs"].z,
            ))
            with batch["payload"].open("rb") as payload:
                shutil.copyfileobj(payload, out, length=1024 * 1024)

pbr_counts = {"baseColor": 0, "roughness": 0, "metallic": 0, "normal": 0}
for record in material_report.values():
    links = record["linkedPbrImages"]
    pbr_counts["baseColor"] += 1 if links.get("Base Color") else 0
    pbr_counts["roughness"] += 1 if links.get("Roughness") else 0
    pbr_counts["metallic"] += 1 if links.get("Metallic") else 0
    pbr_counts["normal"] += 1 if links.get("Normal") else 0

report = {
    "pipeline": "original_glb_direct",
    "sourceUid": SOURCE_UID,
    "sourcePath": str(SOURCE),
    "coordinateSpace": "native",
    "version": 4,
    "vertexStrideBytes": 36,
    "doubleSidedBatchCount": sum(
        1 for batch in batch_records
        if batch["doubleSided"]
    ),
    "backfaceCulledBatchCount": sum(
        1 for batch in batch_records
        if not batch["doubleSided"]
    ),
    "sourceCollection": "DIRECT_ORIGINAL_GLB",
    "legacyPhotogrammetryDoubleSided": True,
    "sourceTriangles": source_triangles,
    "runtimeTriangles": source_triangles,
    "dressingTriangles": 0,
    "runtimeTotalTriangles": source_triangles,
    "decimateRatio": 1.0,
    "scanCleanup": "disabled",
    "vertexLighting": "identity_white",
    "textureSourceMode": "original_glb_embedded_pixels",
    "exactSourcePixelTextures": sum(
        1 for value in material_report.values()
        if value.get("exactSourcePixels")
    ),
    "textureCount": len(material_paths),
    "originalMaxTextureDimension": max_texture_dimension,
    "fallbackMaterials": sorted(fallback_materials),
    "pbrLinkedMaterialCounts": pbr_counts,
    "materialReport": material_report,
    "batchCount": len(batch_records),
    "totalVertices": total_vertices,
    "totalIndices": total_indices,
    "modelBytes": model_path.stat().st_size,
    "nativeFloorY": NATIVE_FLOOR_Y,
    "centerMeters": list(center),
    "boundsMin": list(bounds_min),
    "boundsMax": list(bounds_max),
}
REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

(RUNTIME_ROOT / "ATTRIBUTION.txt").write_text(
    "St Giles Cripplegate by artfletch\n"
    "Original Sketchfab UID: b92917ff83914adc8bc93959ba8b4399\n"
    "License: Creative Commons Attribution (CC BY).\n"
    "Direct clean Xziel conversion of the original GLB.\n",
    encoding="utf-8",
)

print("XZIEL_CLEAN_SOURCE_READY", json.dumps({
    "sourceTriangles": source_triangles,
    "runtimeTriangles": source_triangles,
    "textures": len(material_paths),
    "maxTextureDimension": max_texture_dimension,
    "pbrLinkedMaterialCounts": pbr_counts,
    "batches": len(batch_records),
    "doubleSidedBatches": sum(
        1 for batch in batch_records
        if batch["doubleSided"]
    ),
    "culledBatches": sum(
        1 for batch in batch_records
        if not batch["doubleSided"]
    ),
    "modelBytes": model_path.stat().st_size,
}))
