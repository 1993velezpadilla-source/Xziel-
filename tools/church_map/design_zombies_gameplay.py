import bpy
import json
import math
import os
from pathlib import Path
from mathutils import Vector

MASTER = os.environ.get("CHURCH_MASTER", "church/out/church_map_master.blend")
OUTDIR = Path(os.environ.get("CHURCH_OUT", "church/out"))
OUTDIR.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=MASTER)
scene = bpy.context.scene

# -----------------------------
# Helpers
# -----------------------------
def bbox_for(objects):
    pts = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        for c in obj.bound_box:
            pts.append(obj.matrix_world @ Vector(c))
    if not pts:
        return None
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx

def center_of(objects):
    bb = bbox_for(objects)
    if not bb:
        return None
    return (bb[0] + bb[1]) * 0.5

def material_names(obj):
    if obj.type != "MESH":
        return []
    return [m.name.lower() for m in obj.data.materials if m]

def classify(obj):
    mats = " ".join(material_names(obj))
    if "boiler" in mats: return "boiler"
    if "clockchamber" in mats: return "clock_chamber"
    if "officecorridor" in mats: return "office_corridor"
    if "office" in mats: return "office"
    if "ringingchamber" in mats: return "ringing_chamber"
    if "roofchamber" in mats: return "roof_chamber"
    if "towerstairs" in mats: return "tower_stairs"
    if "towertop" in mats: return "tower_top"
    if "turret" in mats: return "turret"
    if "exterior" in mats: return "exterior"
    if "stgilescripplegate11" in mats: return "main_church"
    return "other"

source_col = bpy.data.collections.get("SOURCE_CHURCH_FULL")
source_objs = list(source_col.objects) if source_col else [o for o in scene.objects if o.type == "MESH"]
zones = {}
for obj in source_objs:
    zones.setdefault(classify(obj), []).append(obj)

zone_info = {}
for name, objs in zones.items():
    bb = bbox_for(objs)
    if not bb:
        continue
    mn, mx = bb
    zone_info[name] = {
        "center": (mn + mx) * 0.5,
        "min": mn,
        "max": mx,
        "size": mx - mn,
        "objects": [o.name for o in objs],
    }

overall = bbox_for(source_objs)
overall_min, overall_max = overall
overall_center = (overall_min + overall_max) * 0.5
overall_size = overall_max - overall_min
marker_scale = max(overall_size.x, overall_size.y, overall_size.z) * 0.008

# -----------------------------
# Replace prior gameplay-pass collections
# -----------------------------
for col_name in ["ZOMBIES_GAMEPLAY_V1", "ZOMBIES_LABELS_V1"]:
    old = bpy.data.collections.get(col_name)
    if old:
        for obj in list(old.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(old)

game_col = bpy.data.collections.new("ZOMBIES_GAMEPLAY_V1")
label_col = bpy.data.collections.new("ZOMBIES_LABELS_V1")
scene.collection.children.link(game_col)
scene.collection.children.link(label_col)

# -----------------------------
# Visual materials for gameplay blockout
# -----------------------------
def mat(name, color, emission=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1.0)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.35
        if "Emission" in bsdf.inputs:
            bsdf.inputs["Emission"].default_value = (*color, 1.0)
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = emission
    return m

MATS = {
    "player_spawn": mat("GM_PlayerSpawn", (0.1, 0.7, 1.0), 2.0),
    "zombie_spawn": mat("GM_ZombieSpawn", (0.9, 0.08, 0.06), 1.5),
    "door": mat("GM_Door", (1.0, 0.55, 0.05), 1.0),
    "power": mat("GM_Power", (0.95, 0.9, 0.15), 2.0),
    "box": mat("GM_Box", (0.45, 0.12, 0.8), 1.5),
    "pap": mat("GM_Upgrade", (1.0, 0.05, 0.6), 2.0),
    "perk": mat("GM_Perk", (0.1, 0.9, 0.45), 1.5),
    "trap": mat("GM_Trap", (0.1, 0.85, 0.9), 1.5),
    "quest": mat("GM_Quest", (0.95, 0.95, 0.95), 2.0),
    "boss": mat("GM_Boss", (0.8, 0.05, 0.05), 2.5),
}

created = []

def add_proxy(name, kind, loc, scale=1.0, shape="sphere", props=None):
    if shape == "cube":
        bpy.ops.mesh.primitive_cube_add(size=marker_scale * 2.3 * scale, location=loc)
    elif shape == "cylinder":
        bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=marker_scale * 1.2 * scale, depth=marker_scale * 3.0 * scale, location=loc)
    else:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=10, radius=marker_scale * scale, location=loc)
    obj = bpy.context.object
    obj.name = name
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    game_col.objects.link(obj)
    obj.data.materials.append(MATS[kind])
    obj["xziel_kind"] = kind
    if props:
        for k, v in props.items():
            obj[k] = v
    created.append(obj)
    return obj

def add_label(text, loc, size=1.0):
    curve = bpy.data.curves.new(text[:50], type="FONT")
    curve.body = text
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.size = marker_scale * 1.6 * size
    curve.extrude = marker_scale * 0.015
    obj = bpy.data.objects.new("LABEL_" + text.replace(" ", "_"), curve)
    obj.location = loc
    obj.rotation_euler = (0, 0, 0)
    label_col.objects.link(obj)
    return obj

# -----------------------------
# Actual zone anchors derived from scan groups
# -----------------------------
def zc(name, fallback=None):
    info = zone_info.get(name)
    return info["center"].copy() if info else Vector(fallback or overall_center)

main = zc("main_church")
boiler = zc("boiler", main)
office = zc("office", main)
corridor = zc("office_corridor", office)
ringing = zc("ringing_chamber", main)
clock = zc("clock_chamber", ringing)
stairs = zc("tower_stairs", ringing)
roof = zc("roof_chamber", clock)
top = zc("tower_top", roof)
exterior = zc("exterior", overall_center)

# Estimate the dominant playable floor plane from real church geometry instead
# of trusting bbox min.z. Photogrammetry zones can contain basement fragments,
# gutters or disconnected shards far below the actual walkable room.
floor_lod_col = bpy.data.collections.get("GAME_CHURCH_LOD0")
floor_source_objs = list(floor_lod_col.objects) if floor_lod_col else source_objs
floor_zone_objs = {}
for _obj in floor_source_objs:
    floor_zone_objs.setdefault(classify(_obj), []).append(_obj)

floor_levels = {}
def dominant_floor_z(zone_name):
    if zone_name in floor_levels:
        return floor_levels[zone_name]
    info = zone_info.get(zone_name)
    if not info:
        return 0.0

    buckets = {}
    for obj in floor_zone_objs.get(zone_name, []):
        if obj.type != "MESH":
            continue
        mesh = obj.data
        if not mesh.polygons:
            continue
        # Cap sampling cost on dense photogrammetry while preserving area trends.
        stride = max(1, len(mesh.polygons) // 25000)
        world = obj.matrix_world
        normal_matrix = world.to_3x3().inverted().transposed()
        for i in range(0, len(mesh.polygons), stride):
            poly = mesh.polygons[i]
            n = normal_matrix @ poly.normal
            if n.length <= 1e-8:
                continue
            n.normalize()
            if n.z < 0.58:
                continue
            p = world @ poly.center
            zbin = round(float(p.z) * 4.0) / 4.0
            buckets[zbin] = buckets.get(zbin, 0.0) + float(poly.area) * stride

    if buckets:
        # Prefer the largest upward-facing horizontal surface band. This rejects
        # tiny low scan fragments and usually selects the nave/room floor.
        z = max(buckets.items(), key=lambda kv: kv[1])[0]
    else:
        z = float(info["min"].z)
    floor_levels[zone_name] = z
    print("FLOOR_LEVEL", zone_name, z)
    return z

def floorish(zone_name, point, lift=0.45):
    info = zone_info.get(zone_name)
    if not info:
        return point
    p = point.copy()
    p.z = dominant_floor_z(zone_name) + lift
    return p

# Long axis of main church becomes entrance -> altar progression.
main_info = zone_info.get("main_church")
if main_info:
    sx, sy = main_info["size"].x, main_info["size"].y
    axis = Vector((1,0,0)) if sx >= sy else Vector((0,1,0))
    half = max(sx, sy) * 0.28
else:
    axis = Vector((0,1,0))
    half = 8.0

nave_entry = floorish("main_church", main - axis * half)
nave_mid = floorish("main_church", main)
altar = floorish("main_church", main + axis * half)

# Pick a clean exterior spawn instead of using the center of the exterior scan.
# The old center point could land the camera inside photogrammetry walls/roof.
def choose_clear_exterior_spawn():
    main_i = zone_info.get("main_church")
    ext_i = zone_info.get("exterior")
    if not main_i or not ext_i:
        return floorish("exterior", exterior, 1.1)

    mmn, mmx = main_i["min"], main_i["max"]
    emn, emx = ext_i["min"], ext_i["max"]
    mc = main_i["center"]
    sides = [
        ("west",  max(0.0, mmn.x-emn.x), Vector((-1,0,0)), Vector((mmn.x,mc.y,0))),
        ("east",  max(0.0, emx.x-mmx.x), Vector(( 1,0,0)), Vector((mmx.x,mc.y,0))),
        ("south", max(0.0, mmn.y-emn.y), Vector((0,-1,0)), Vector((mc.x,mmn.y,0))),
        ("north", max(0.0, emx.y-mmx.y), Vector((0, 1,0)), Vector((mc.x,mmx.y,0))),
    ]
    side, clearance, outward, edge = max(sides, key=lambda x:x[1])
    distance = min(10.0, max(4.5, clearance*0.45))
    p = edge + outward*distance

    # Keep a safe margin inside the captured exterior bounds.
    p.x = min(max(p.x, emn.x+1.0), emx.x-1.0)
    p.y = min(max(p.y, emn.y+1.0), emx.y-1.0)

    # Ray down from a few metres above the expected ground so roofs/tree tops
    # cannot become the player floor. Fall back to the scan floor if necessary.
    deps = bpy.context.evaluated_depsgraph_get()
    expected_floor = max(emn.z, mmn.z)
    origin = Vector((p.x,p.y,expected_floor+4.0))
    hit, loc, normal, face, obj, matrix = scene.ray_cast(
        deps, origin, Vector((0,0,-1)), distance=12.0
    )
    p.z = (loc.z+1.05) if hit else (expected_floor+1.05)
    return p

player_start = choose_clear_exterior_spawn()

# Spawn and interactives.
add_proxy("P1_START_COURTYARD", "player_spawn", player_start, 1.35, "cylinder",
          {"zone":"courtyard", "phase":"start", "look_at":"main_church"})
add_proxy("POWER_BOILER", "power", floorish("boiler", boiler), 1.4, "cube",
          {"zone":"boiler", "requires":"fuse_a+fuse_b"})
add_proxy("UPGRADE_ALTAR", "pap", altar + Vector((0,0,0.25)), 1.5, "cube",
          {"zone":"altar", "unlock":"seven_bells_ritual"})
add_proxy("MYSTERY_RELIQUARY", "box", nave_mid + Vector((0,0,0.25)), 1.25, "cube",
          {"zone":"nave", "relocates":True, "relocation_pool":"box_locations"})

# Doors / progression edges use midpoints between real zone centers.
door_edges = [
    ("DOOR_COURTYARD_NAVE", player_start, nave_entry, 750),
    ("DOOR_NAVE_OFFICE", nave_mid, corridor, 1000),
    ("DOOR_OFFICE_BOILER", corridor, boiler, 1000),
    ("DOOR_NAVE_TOWER", nave_mid, stairs, 1250),
    ("DOOR_STAIRS_RINGING", stairs, ringing, 1250),
    ("DOOR_RINGING_CLOCK", ringing, clock, 1500),
    ("DOOR_CLOCK_ROOF", clock, roof, 1500),
]
for name, a, b, cost in door_edges:
    p=(a+b)*0.5
    add_proxy(name, "door", p, 0.9, "cube", {"cost":cost, "edge":name})

# Perk-like stations. Original names for this project, not COD labels.
perk_specs = [
    ("PERK_SECOND_WIND", nave_entry, "main_church", "Second Wind"),
    ("PERK_IRON_VEINS", office, "office", "Iron Veins"),
    ("PERK_RAPID_HANDS", ringing, "ringing_chamber", "Rapid Hands"),
    ("PERK_DEADEYE", clock, "clock_chamber", "Deadeye"),
    ("PERK_SPRINT_SURGE", roof, "roof_chamber", "Sprint Surge"),
]
for name, p, zone, label in perk_specs:
    add_proxy(name, "perk", floorish(zone, p) + Vector((0,0,0.25)), 0.9, "cylinder",
              {"perk":label, "zone":zone})

# Traps.
add_proxy("TRAP_NAVE_CHANDELIER", "trap", nave_mid + Vector((0,0,max(4.0, marker_scale*10))), 1.0, "sphere",
          {"type":"falling_chandelier", "cooldown":45})
add_proxy("TRAP_BELL_SHOCKWAVE", "trap", ringing, 1.0, "cylinder",
          {"type":"bell_shockwave", "cooldown":60, "requires_power":True})
add_proxy("TRAP_BOILER_STEAM", "trap", floorish("boiler", boiler), 1.0, "cylinder",
          {"type":"steam_burst", "cooldown":35, "requires_power":True})

# Quest anchors: Seven Bells.
quest_specs = [
    ("QUEST_RELIC_HYMN", office, "office", "Torn Hymn"),
    ("QUEST_RELIC_IRON_KEY", boiler, "boiler", "Iron Vestry Key"),
    ("QUEST_RELIC_CENSER", altar, "main_church", "Blackened Censer"),
    ("QUEST_BELL_1", ringing, "ringing_chamber", "Bell I"),
    ("QUEST_CLOCK", clock, "clock_chamber", "Set 03:17"),
    ("QUEST_FINAL_SIGIL", altar + axis * (half * 0.2), "main_church", "Ash Sigil"),
]
for name, p, zone, label in quest_specs:
    add_proxy(name, "quest", floorish(zone, p) + Vector((0,0,0.45)), 0.65, "sphere",
              {"quest":"seven_bells", "label":label})

# Boss arena at tower / ringing chamber.
boss_pos = floorish("ringing_chamber", ringing) + Vector((0,0,0.6))
add_proxy("BOSS_BELL_WARDEN", "boss", boss_pos, 1.8, "cylinder",
          {"boss":"Bell Warden", "trigger":"seven_bells_finale"})

# Zombie spawn candidates: derive from real bounds.
spawn_points = []
for zone_name in ["exterior", "main_church", "office", "office_corridor", "boiler", "tower_stairs", "ringing_chamber"]:
    info = zone_info.get(zone_name)
    if not info:
        continue
    mn, mx, c = info["min"], info["max"], info["center"]
    z = mn.z + 0.45
    candidates = [
        Vector((mn.x + (mx.x-mn.x)*0.12, c.y, z)),
        Vector((mx.x - (mx.x-mn.x)*0.12, c.y, z)),
        Vector((c.x, mn.y + (mx.y-mn.y)*0.12, z)),
        Vector((c.x, mx.y - (mx.y-mn.y)*0.12, z)),
    ]
    for i,p in enumerate(candidates):
        o=add_proxy(f"ZSP_{zone_name.upper()}_{i+1:02d}", "zombie_spawn", p, 0.55, "sphere",
                    {"zone":zone_name, "candidate":True})
        spawn_points.append(o)

# Labels at real zone centers.
for zone_name, info in zone_info.items():
    if zone_name == "other":
        continue
    p = info["center"].copy()
    p.z = info["max"].z + marker_scale * 2.0
    add_label(zone_name.replace("_"," ").upper(), p, 0.8)

# -----------------------------
# Camera plan renders
# -----------------------------
world = scene.world
if world and world.use_nodes:
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Strength"].default_value = 0.35

# Stronger neutral inspection light.
bpy.ops.object.light_add(type="AREA", location=(overall_center.x, overall_center.y, overall_max.z + overall_size.z*0.6))
area = bpy.context.object
area.name = "Gameplay_Plan_Area"
area.data.energy = 2200
area.data.size = max(overall_size.x, overall_size.y) * 0.8

cam = scene.camera
if not cam:
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    scene.camera = cam
cam.data.clip_end = max(5000, overall_size.length*20)

def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z","Y").to_euler()

scene.render.resolution_x = 1600
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except Exception:
    try:
        scene.render.engine = "BLENDER_EEVEE"
    except Exception:
        pass

# Top plan
cam.location = overall_center + Vector((0, 0, overall_size.z * 2.5 + 40))
cam.data.lens = 52
look_at(cam, overall_center)
scene.render.filepath = str(OUTDIR / "zombies_gameplay_top.png")
bpy.ops.render.render(write_still=True)

# Isometric plan
cam.location = overall_center + Vector((overall_size.x*1.15, -overall_size.y*1.4, overall_size.z*1.2))
cam.data.lens = 48
look_at(cam, overall_center)
scene.render.filepath = str(OUTDIR / "zombies_gameplay_iso.png")
bpy.ops.render.render(write_still=True)

# Tower-focused quest view
cam.location = top + Vector((overall_size.x*0.5, -overall_size.y*0.55, overall_size.z*0.4))
cam.data.lens = 52
look_at(cam, (ringing + clock + top) / 3.0)
scene.render.filepath = str(OUTDIR / "zombies_tower_quest.png")
bpy.ops.render.render(write_still=True)

# -----------------------------
# Persist map data and blend
# -----------------------------
plan = {
    "working_title": "SANCTUM OF ASH",
    "source_building": "St Giles-without-Cripplegate scan by artfletch (CC BY)",
    "design_pass": "gameplay-blockout-v1",
    "floor_levels": {k: dominant_floor_z(k) for k in zone_info if k != "other"},
    "zones": {
        k: {
            "center": list(v["center"]),
            "min": list(v["min"]),
            "max": list(v["max"]),
            "size": list(v["size"]),
            "mesh_count": len(v["objects"]),
        } for k,v in zone_info.items()
    },
    "progression": [
        "courtyard",
        "nave",
        "office_corridor",
        "boiler_power",
        "tower_stairs",
        "ringing_chamber",
        "clock_chamber",
        "roof_chamber",
        "tower_top",
    ],
    "quest": {
        "id": "seven_bells",
        "steps": [
            "recover Torn Hymn, Iron Vestry Key and Blackened Censer",
            "restore boiler power with two fuse components",
            "activate the ringing chamber and reproduce the bell sequence",
            "set the clock chamber mechanism to 03:17",
            "charge the Ash Sigil with kills in the nave",
            "summon and defeat the Bell Warden",
            "unlock the altar upgrade machine and permanent tower shortcut",
        ],
    },
    "interactives": [
        {
            "name": o.name,
            "kind": o.get("xziel_kind"),
            "location": list(o.location),
            "properties": {k:o[k] for k in o.keys() if k not in {"xziel_kind"}},
        }
        for o in created
    ],
}
(OUTDIR / "zombies_map_plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")

bpy.ops.wm.save_as_mainfile(filepath=str(OUTDIR / "church_zombies_gameplay_v1.blend"))

print("GAMEPLAY_PASS_OK")
print("ZONES", sorted(zone_info))
print("INTERACTIVES", len(created))
print("ZOMBIE_SPAWNS", len(spawn_points))
