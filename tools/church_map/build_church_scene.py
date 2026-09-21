import bpy
import json
import math
import os
import sys
from mathutils import Vector

SOURCE = os.environ.get("CHURCH_SOURCE", "church/source.glb")
OUTDIR = os.environ.get("CHURCH_OUT", "church/out")
TARGET_TRIS = int(os.environ.get("CHURCH_TARGET_TRIS", "650000"))
os.makedirs(OUTDIR, exist_ok=True)

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
        for c in obj.bound_box:
            pts.append(obj.matrix_world @ Vector(c))
    if not pts:
        return Vector((-1,-1,-1)), Vector((1,1,1))
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx

def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

# Reset.
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
    pass

# Import the complete church source.
bpy.ops.import_scene.gltf(filepath=SOURCE)
source_objects = [o for o in bpy.context.scene.objects if o.type == "MESH"]
if not source_objects:
    raise RuntimeError("Imported church contains no mesh objects")

# Put imported source in a dedicated collection.
source_col = bpy.data.collections.new("SOURCE_CHURCH_FULL")
bpy.context.scene.collection.children.link(source_col)
for obj in list(source_objects):
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    source_col.objects.link(obj)

total_tris = sum(tri_count(o) for o in source_objects)
mn, mx = world_bbox(source_objects)
center = (mn + mx) * 0.5
size = mx - mn
diag = max(size.length, 1e-3)

# Build a mobile LOD0 copy. Keep the untouched original in the .blend.
lod_col = bpy.data.collections.new("GAME_CHURCH_LOD0")
bpy.context.scene.collection.children.link(lod_col)
lod_objects = []
ratio = min(1.0, TARGET_TRIS / max(total_tris, 1))
for src in source_objects:
    dup = src.copy()
    dup.data = src.data.copy()
    lod_col.objects.link(dup)
    lod_objects.append(dup)
    if ratio < 0.999 and tri_count(dup) > 1000:
        mod = dup.modifiers.new(name="XZIEL_MOBILE_DECIMATE", type="DECIMATE")
        mod.ratio = max(0.05, ratio)
        mod.use_collapse_triangulate = True
        bpy.context.view_layer.objects.active = dup
        dup.select_set(True)
        try:
            bpy.ops.object.modifier_apply(modifier=mod.name)
        except Exception as exc:
            print("WARN decimate", dup.name, exc)
        dup.select_set(False)

# Hide raw source from render; it remains editable for later high-quality work.
for obj in source_objects:
    obj.hide_render = True
    obj.hide_set(True)

lod_tris = sum(tri_count(o) for o in lod_objects)
lmn, lmx = world_bbox(lod_objects)
lcenter = (lmn + lmx) * 0.5
lsize = lmx - lmn

# Gameplay marker collection -- map logic anchors, not final placements.
game_col = bpy.data.collections.new("GAMEPLAY_MARKERS")
bpy.context.scene.collection.children.link(game_col)

def add_marker(name, location, kind, notes=""):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "SPHERE"
    obj.empty_display_size = max(diag * 0.006, 0.15)
    obj.location = location
    obj["xziel_kind"] = kind
    obj["notes"] = notes
    game_col.objects.link(obj)
    return obj

floor_z = lmn.z + max(lsize.z * 0.01, 0.05)
add_marker("player_spawn", (lcenter.x, lcenter.y, floor_z), "player_spawn", "Initial anchor; refine after route inspection")
add_marker("power_anchor", (lcenter.x, lcenter.y + lsize.y * 0.12, floor_z), "power", "Candidate power-switch anchor")
add_marker("pap_anchor", (lcenter.x, lcenter.y - lsize.y * 0.18, floor_z), "pack_a_punch", "Candidate Pack-a-Punch anchor")
for name, x, y in [
    ("zombie_spawn_north", lcenter.x, lmx.y),
    ("zombie_spawn_south", lcenter.x, lmn.y),
    ("zombie_spawn_east", lmx.x, lcenter.y),
    ("zombie_spawn_west", lmn.x, lcenter.y),
]:
    add_marker(name, (x, y, floor_z), "zombie_spawn", "Exterior perimeter candidate")

# Basic scene lighting for inspection renders.
world = bpy.context.scene.world or bpy.data.worlds.new("World")
bpy.context.scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs["Color"].default_value = (0.012, 0.016, 0.025, 1)
    bg.inputs["Strength"].default_value = 0.18

bpy.ops.object.light_add(type="SUN", location=(lcenter.x, lcenter.y, lmx.z + diag))
sun = bpy.context.object
sun.name = "Moon_Key"
sun.data.energy = 2.2
sun.rotation_euler = (math.radians(35), math.radians(-20), math.radians(-35))

bpy.ops.object.light_add(type="AREA", location=(lcenter.x, lcenter.y, lmx.z + max(lsize.z, 1)))
area = bpy.context.object
area.name = "Interior_Fill"
area.data.energy = 1500
area.data.shape = "DISK"
area.data.size = max(lsize.x, lsize.y, 1) * 0.45
look_at(area, lcenter)

# Camera.
bpy.ops.object.camera_add()
cam = bpy.context.object
cam.name = "Church_Inspection_Camera"
bpy.context.scene.camera = cam
cam.data.lens = 42
cam.data.clip_end = max(10000.0, diag * 20)

scene = bpy.context.scene
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except Exception:
    scene.render.engine = "BLENDER_EEVEE"

views = [
    ("exterior_3q", Vector((1.25, -1.35, 0.65))),
    ("exterior_opposite", Vector((-1.25, 1.35, 0.55))),
    ("top_layout", Vector((0.02, -0.02, 2.2))),
    ("entry_axis", Vector((0.0, -1.0, 0.22))),
]
for name, offs in views:
    if name == "top_layout":
        cam.location = lcenter + Vector((0, 0, diag * offs.z))
    else:
        cam.location = lcenter + Vector((offs.x * diag, offs.y * diag, offs.z * diag))
    look_at(cam, lcenter)
    scene.render.filepath = os.path.join(OUTDIR, f"{name}.png")
    bpy.ops.render.render(write_still=True)

# Export mobile LOD only.
bpy.ops.object.select_all(action="DESELECT")
for obj in lod_objects:
    obj.hide_set(False)
    obj.select_set(True)
bpy.context.view_layer.objects.active = lod_objects[0]
bpy.ops.export_scene.gltf(
    filepath=os.path.join(OUTDIR, "church_map_mobile_lod0.glb"),
    export_format="GLB",
    use_selection=True,
    export_apply=True,
)

# Save editable Blender source with full original + LOD + markers.
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUTDIR, "church_map_master.blend"))

report = {
    "source": SOURCE,
    "source_meshes": len(source_objects),
    "source_triangles": total_tris,
    "mobile_lod0_triangles": lod_tris,
    "target_triangles": TARGET_TRIS,
    "decimate_ratio": ratio,
    "bounds_min": list(mn),
    "bounds_max": list(mx),
    "bounds_size": list(size),
    "center": list(center),
    "objects": [
        {
            "name": o.name,
            "triangles": tri_count(o),
            "materials": [m.name for m in o.data.materials if m],
        }
        for o in source_objects
    ],
    "gameplay_markers": [
        {"name": o.name, "kind": o.get("xziel_kind"), "location": list(o.location)}
        for o in game_col.objects
    ],
}
with open(os.path.join(OUTDIR, "church_scene_report.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)

with open(os.path.join(OUTDIR, "NEXT_PASS.md"), "w", encoding="utf-8") as f:
    f.write("# Xziel Church Map - next pass\n\n")
    f.write("This artifact is the automated ingest/inspection pass. The untouched source geometry is kept in SOURCE_CHURCH_FULL.\n\n")
    f.write(f"- Source triangles: {total_tris:,}\n")
    f.write(f"- Mobile LOD0 triangles: {lod_tris:,}\n")
    f.write("- Next: inspect renders/report, identify real interior floors/doors/rooms, then author collision, zombie windows, doors, buy-zones, nav routes, lighting and horror dressing against the actual geometry.\n")

print(json.dumps(report, indent=2))
