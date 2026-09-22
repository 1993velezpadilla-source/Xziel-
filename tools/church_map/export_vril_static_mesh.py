import bpy
import bmesh
import json
import math
import os
import re
import struct
from pathlib import Path
from mathutils import Vector

MASTER = os.environ.get("CHURCH_GAMEPLAY_BLEND", "church/out/church_zombies_gameplay_v1.blend")
PLAN_PATH = Path(os.environ.get("CHURCH_PLAN", "church/out/zombies_map_plan.json"))
OUTDIR = Path(os.environ.get("CHURCH_OUT", "church/out"))
RUNTIME_ROOT = OUTDIR / "vril_static"
MODEL_DIR = RUNTIME_ROOT / "models" / "xziel" / "sanctum"
TEXTURE_DIR = RUNTIME_ROOT / "textures" / "xziel" / "sanctum"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
TEXTURE_DIR.mkdir(parents=True, exist_ok=True)

TARGET_TRIS = int(os.environ.get("XZIEL_STATIC_TARGET_TRIS", "600000"))
TEXTURE_MAX = int(os.environ.get("XZIEL_STATIC_TEXTURE_MAX", "2048"))
MAX_TRIS_PER_BATCH = 18000
QUAKE_SCALE = 39.3700787402

# Cleanup is deliberately conservative. The scan is the visual authority, so
# disconnected photogrammetry is not assumed to be junk merely because it is
# small in face count. Only centimeter-scale micro-shards may be removed, and
# even those are subject to a hard global face budget.
TINY_ISLAND_MAX_FACES = int(os.environ.get("XZIEL_SCAN_TINY_MAX_FACES", "4"))
TINY_ISLAND_MAX_DIAGONAL_M = float(os.environ.get("XZIEL_SCAN_TINY_MAX_DIAGONAL_M", "0.03"))
MAX_CLEANUP_FRACTION = float(os.environ.get("XZIEL_SCAN_MAX_CLEANUP_FRACTION", "0.0025"))

bpy.ops.wm.open_mainfile(filepath=MASTER)
scene = bpy.context.scene
plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))

lod_col = bpy.data.collections.get("GAME_CHURCH_LOD0")
if not lod_col:
    raise RuntimeError("GAME_CHURCH_LOD0 missing")
source_objects = [o for o in lod_col.objects if o.type == "MESH"]
if not source_objects:
    raise RuntimeError("GAME_CHURCH_LOD0 contains no meshes")

# Match the exact origin transform used by export_nzp_harness.py.
zones = [v for k,v in plan["zones"].items() if k != "other"]
global_min = Vector((
    min(v["min"][0] for v in zones),
    min(v["min"][1] for v in zones),
    min(v["min"][2] for v in zones),
))
global_max = Vector((
    max(v["max"][0] for v in zones),
    max(v["max"][1] for v in zones),
    max(v["max"][2] for v in zones),
))
center = (global_min + global_max) * 0.5

def mesh_triangles(obj):
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)

source_tris = sum(mesh_triangles(o) for o in source_objects)

runtime_col = bpy.data.collections.get("VRIL_STATIC_RUNTIME")
if runtime_col:
    for o in list(runtime_col.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(runtime_col)
runtime_col = bpy.data.collections.new("VRIL_STATIC_RUNTIME")
scene.collection.children.link(runtime_col)

cleanup_face_budget = max(32, int(source_tris * MAX_CLEANUP_FRACTION))
cleanup_stats = {
    "removedIslands": 0,
    "removedFaces": 0,
    "candidateIslands": 0,
    "faceBudget": cleanup_face_budget,
    "maxFacesPerIsland": TINY_ISLAND_MAX_FACES,
    "maxDiagonalMeters": TINY_ISLAND_MAX_DIAGONAL_M,
}

def component_world_diagonal(obj, comp):
    mn = Vector((1e30, 1e30, 1e30))
    mx = Vector((-1e30, -1e30, -1e30))
    seen = set()
    for face in comp:
        for vert in face.verts:
            if vert.index in seen:
                continue
            seen.add(vert.index)
            p = obj.matrix_world @ vert.co
            mn.x = min(mn.x, p.x); mn.y = min(mn.y, p.y); mn.z = min(mn.z, p.z)
            mx.x = max(mx.x, p.x); mx.y = max(mx.y, p.y); mx.z = max(mx.z, p.z)
    return (mx - mn).length if seen else 0.0

def remove_tiny_scan_islands(obj):
    # The photogrammetry scan is authoritative visual geometry. Never classify
    # a component as debris solely from a percentage-of-object threshold: that
    # deleted real architecture on fragmented scans. A removable shard must be
    # BOTH <= a few faces AND centimeter-scale in world space, with a hard
    # global cap on total deleted faces.
    remaining_budget = cleanup_face_budget - cleanup_stats["removedFaces"]
    if remaining_budget <= 0:
        return

    mesh = obj.data
    if len(mesh.polygons) < 300:
        return

    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()

    unseen = set(bm.faces)
    components = []
    while unseen:
        seed = unseen.pop()
        comp = [seed]
        stack = [seed]
        while stack:
            face = stack.pop()
            for edge in face.edges:
                for other in edge.link_faces:
                    if other in unseen:
                        unseen.remove(other)
                        stack.append(other)
                        comp.append(other)
        components.append(comp)

    if len(components) <= 1:
        bm.free()
        return

    # Examine the smallest connected components first. Large but disconnected
    # architectural pieces (stairs, trim, roof/tower fragments) are untouched.
    components.sort(key=len)
    to_delete = []
    removed_islands = 0
    for comp in components:
        if len(comp) > TINY_ISLAND_MAX_FACES:
            break
        if len(to_delete) + len(comp) > remaining_budget:
            break
        if component_world_diagonal(obj, comp) > TINY_ISLAND_MAX_DIAGONAL_M:
            continue
        cleanup_stats["candidateIslands"] += 1
        to_delete.extend(comp)
        removed_islands += 1

    if to_delete:
        bmesh.ops.delete(bm, geom=to_delete, context="FACES")
        bm.to_mesh(mesh)
        mesh.update()
        cleanup_stats["removedIslands"] += removed_islands
        cleanup_stats["removedFaces"] += len(to_delete)
    bm.free()

# Work only on derived copies; the GAME_CHURCH_LOD0 source and Blender master
# are never modified by runtime cleanup/decimation.
runtime_objects = []
for src in source_objects:
    dup = src.copy()
    dup.data = src.data.copy()
    dup.name = "XZSM_" + src.name
    runtime_col.objects.link(dup)
    remove_tiny_scan_islands(dup)
    runtime_objects.append(dup)

cleaned_tris = sum(mesh_triangles(o) for o in runtime_objects)
if source_tris >= TARGET_TRIS and cleaned_tris < TARGET_TRIS:
    raise RuntimeError(
        f"Sanctum cleanup removed authoritative geometry below target: "
        f"source={source_tris} cleaned={cleaned_tris} target={TARGET_TRIS} "
        f"cleanup={cleanup_stats}"
    )

# Decimation is calculated AFTER cleanup. The old order used the pre-cleanup
# ratio and then applied it to an already-reduced mesh, compounding the loss.
ratio = min(1.0, TARGET_TRIS / max(cleaned_tris, 1))
if ratio < 0.995:
    for dup in runtime_objects:
        if mesh_triangles(dup) <= 500:
            continue
        mod = dup.modifiers.new("XZSM_MOBILE_DECIMATE", "DECIMATE")
        mod.ratio = max(0.025, ratio)
        mod.use_collapse_triangulate = True
        bpy.context.view_layer.objects.active = dup
        dup.select_set(True)
        try:
            bpy.ops.object.modifier_apply(modifier=mod.name)
        except Exception as exc:
            print("WARN decimate", dup.name, exc)
        dup.select_set(False)

runtime_tris = sum(mesh_triangles(o) for o in runtime_objects)
runtime_floor = min(source_tris, int(TARGET_TRIS * 0.95))
if runtime_tris < runtime_floor:
    raise RuntimeError(
        f"Sanctum runtime geometry regressed: runtime={runtime_tris} "
        f"floor={runtime_floor} source={source_tris} target={TARGET_TRIS}"
    )

def safe_name(s):
    s = re.sub(r"[^A-Za-z0-9_-]+", "_", s or "material")
    return s[:40] or "material"

def material_image(mat):
    if not mat or not mat.use_nodes or not mat.node_tree:
        return None
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        sock = bsdf.inputs.get("Base Color")
        if sock and sock.is_linked:
            node = sock.links[0].from_node
            if getattr(node, "type", "") == "TEX_IMAGE" and node.image:
                return node.image
    for node in mat.node_tree.nodes:
        if getattr(node, "type", "") == "TEX_IMAGE" and node.image:
            return node.image
    return None

def material_color(mat):
    if mat and mat.use_nodes and mat.node_tree:
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf and bsdf.inputs.get("Base Color"):
            c = bsdf.inputs["Base Color"].default_value
            return tuple(float(x) for x in c[:4])
    if mat:
        return tuple(float(x) for x in mat.diffuse_color)
    return (0.55, 0.55, 0.55, 1.0)

texture_records = {}
texture_paths = {}

def save_material_texture(mat):
    key = mat.name if mat else "__fallback__"
    if key in texture_paths:
        return texture_paths[key]

    idx = len(texture_paths)
    stem = f"tex_{idx:03d}_{safe_name(key)}"
    rel_no_ext = f"textures/xziel/sanctum/{stem}"
    dst = TEXTURE_DIR / f"{stem}.png"

    img = material_image(mat)
    if img and img.size[0] > 0 and img.size[1] > 0:
        copy = img.copy()
        max_dim = TEXTURE_MAX
        w, h = int(copy.size[0]), int(copy.size[1])
        if max(w,h) > max_dim:
            s = max_dim / float(max(w,h))
            copy.scale(max(1,int(round(w*s))), max(1,int(round(h*s))))
        copy.file_format = "PNG"
        try:
            copy.save_render(filepath=str(dst), scene=scene)
        except Exception:
            copy.filepath_raw = str(dst)
            copy.save()
        bpy.data.images.remove(copy)
        source_desc = img.name
    else:
        # Blender-generated 8x8 flat-color fallback, still saved through the
        # same PNG path expected by Vril.
        rgba = material_color(mat)
        gen = bpy.data.images.new(stem, width=8, height=8, alpha=True, float_buffer=False)
        gen.pixels = list(rgba) * 64
        gen.file_format = "PNG"
        gen.save_render(filepath=str(dst), scene=scene)
        bpy.data.images.remove(gen)
        source_desc = "generated_base_color"

    texture_paths[key] = rel_no_ext
    texture_records[key] = {
        "path": rel_no_ext + ".png",
        "source": source_desc,
        "bytes": dst.stat().st_size if dst.exists() else 0,
    }
    return rel_no_ext

# Gather triangles by (object, material) instead of by material globally.
# This keeps batch bounds spatially local so Vril frustum culling can reject
# entire church rooms/tower sections that are not visible, while preserving
# the high-detail mobile mesh.
groups = {}
bounds_min = Vector((1e30,1e30,1e30))
bounds_max = Vector((-1e30,-1e30,-1e30))

for obj in runtime_objects:
    mesh = obj.data
    mesh.calc_loop_triangles()
    uv_layer = mesh.uv_layers.active.data if mesh.uv_layers.active else None
    world = obj.matrix_world
    for tri in mesh.loop_triangles:
        poly = mesh.polygons[tri.polygon_index]
        mat = obj.material_slots[poly.material_index].material if poly.material_index < len(obj.material_slots) else None
        tex = save_material_texture(mat)
        group_key = (obj.name, tex)
        group = groups.setdefault(group_key, [])
        verts = []
        for loop_index in tri.loops:
            vi = mesh.loops[loop_index].vertex_index
            p = world @ mesh.vertices[vi].co
            p = (p - center) * QUAKE_SCALE
            if uv_layer:
                uv = uv_layer[loop_index].uv
                u = float(uv.x)
                v = 1.0 - float(uv.y)
            else:
                u = v = 0.0
            verts.append((float(p.x), float(p.y), float(p.z), u, v))
            bounds_min.x=min(bounds_min.x,p.x); bounds_min.y=min(bounds_min.y,p.y); bounds_min.z=min(bounds_min.z,p.z)
            bounds_max.x=max(bounds_max.x,p.x); bounds_max.y=max(bounds_max.y,p.y); bounds_max.z=max(bounds_max.z,p.z)
        group.append(verts)

# Split each texture group into <= 54k vertices so uint16 indices are safe.
batches = []
for (object_name, tex), tris in groups.items():
    for start in range(0, len(tris), MAX_TRIS_PER_BATCH):
        chunk = tris[start:start+MAX_TRIS_PER_BATCH]
        vertices = [v for tri in chunk for v in tri]
        indices = list(range(len(vertices)))
        mn = Vector((1e30,1e30,1e30)); mx = Vector((-1e30,-1e30,-1e30))
        for x,y,z,u,v in vertices:
            mn.x=min(mn.x,x); mn.y=min(mn.y,y); mn.z=min(mn.z,z)
            mx.x=max(mx.x,x); mx.y=max(mx.y,y); mx.z=max(mx.z,z)
        batches.append({
            "object": object_name,
            "texture": tex,
            "vertices": vertices,
            "indices": indices,
            "mins": mn,
            "maxs": mx,
        })

model_path = MODEL_DIR / "sanctum.xzsm"
with model_path.open("wb") as f:
    f.write(struct.pack("<4sIIII", b"XZSM", 1, len(batches),
                        sum(len(b["vertices"]) for b in batches),
                        sum(len(b["indices"]) for b in batches)))
    for b in batches:
        tex_bytes = b["texture"].encode("utf-8")[:95]
        tex_field = tex_bytes + b"\0" * (96-len(tex_bytes))
        f.write(struct.pack(
            "<II96s6f",
            len(b["vertices"]), len(b["indices"]), tex_field,
            b["mins"].x,b["mins"].y,b["mins"].z,
            b["maxs"].x,b["maxs"].y,b["maxs"].z,
        ))
        for vert in b["vertices"]:
            f.write(struct.pack("<5f", *vert))
        f.write(struct.pack("<" + "H"*len(b["indices"]), *b["indices"]))

report = {
    "format":"XZSM",
    "version":1,
    "sourceTriangles":source_tris,
    "cleanedTriangles":cleaned_tris,
    "runtimeTriangles":runtime_tris,
    "targetTriangles":TARGET_TRIS,
    "textureMaxDimension":TEXTURE_MAX,
    "decimateRatio":ratio,
    "batching":"object_material_spatial",
    "scanCleanup":cleanup_stats,
    "batchCount":len(batches),
    "textureCount":len(texture_records),
    "totalVertices":sum(len(b["vertices"]) for b in batches),
    "totalIndices":sum(len(b["indices"]) for b in batches),
    "modelBytes":model_path.stat().st_size,
    "boundsMin":list(bounds_min),
    "boundsMax":list(bounds_max),
    "quakeScale":QUAKE_SCALE,
    "centerMeters":list(center),
    "textures":texture_records,
}
(OUTDIR/"vril_static_mesh_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
(RUNTIME_ROOT/"ATTRIBUTION.txt").write_text(
    "SANCTUM OF ASH development visual mesh\n"
    "St Giles Cripplegate scan by artfletch — Creative Commons Attribution (CC BY).\n"
    "Runtime mesh/textures are transformed derivatives generated by Xziel's Blender pipeline.\n",
    encoding="utf-8"
)

print("XZSM_EXPORT_OK", json.dumps({
    "sourceTriangles":source_tris,
    "runtimeTriangles":runtime_tris,
    "batchCount":len(batches),
    "textureCount":len(texture_records),
    "modelBytes":model_path.stat().st_size,
    "textureMaxDimension":TEXTURE_MAX,
    "scanCleanup":cleanup_stats,
}))
