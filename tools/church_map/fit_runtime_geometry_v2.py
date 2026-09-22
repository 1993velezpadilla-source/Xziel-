import bpy
import json
import math
import os
from pathlib import Path
from mathutils import Vector

MASTER = os.environ.get("CHURCH_GAMEPLAY_BLEND", "church/out/church_zombies_gameplay_v1.blend")
PLAN_PATH = Path(os.environ.get("CHURCH_PLAN", "church/out/zombies_map_plan.json"))
OUTDIR = Path(os.environ.get("CHURCH_OUT", "church/out"))
OUTDIR.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=MASTER)
scene = bpy.context.scene
depsgraph = bpy.context.evaluated_depsgraph_get()
plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))

for name in ["RUNTIME_COLLISION_FITTED_V2", "BARRICADES_FITTED_V2", "NAV_FITTED_V2"]:
    col = bpy.data.collections.get(name)
    if col:
        for obj in list(col.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(col)

collision_col = bpy.data.collections.new("RUNTIME_COLLISION_FITTED_V2")
barricade_col = bpy.data.collections.new("BARRICADES_FITTED_V2")
nav_col = bpy.data.collections.new("NAV_FITTED_V2")
scene.collection.children.link(collision_col)
scene.collection.children.link(barricade_col)
scene.collection.children.link(nav_col)

def make_mat(name, rgba):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = rgba
    return m

COL_MAT = make_mat("COLLISION_FITTED_V2", (0.08,0.7,1.0,0.35))
BAR_MAT = make_mat("BARRICADE_FITTED_V2", (0.95,0.28,0.08,1.0))
NAV_MAT = make_mat("NAV_FITTED_V2", (0.15,1.0,0.3,1.0))

aliases={"courtyard":"exterior","nave":"main_church","altar":"main_church"}
def norm_zone(z): return aliases.get(str(z or "main_church"), str(z or "main_church"))

def move_to(obj, col):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)

def classify(obj):
    mats=" ".join(m.name.lower() for m in getattr(obj.data,"materials",[]) if m)
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

# Use LOD0 as the raycast/render source. It is much lighter than the original scan.
lod_col = bpy.data.collections.get("GAME_CHURCH_LOD0")
if not lod_col:
    raise RuntimeError("GAME_CHURCH_LOD0 missing from gameplay master")
lod_objects = [o for o in lod_col.objects if o.type=="MESH"]
for o in lod_objects:
    o.hide_set(False)
    o.hide_render = False

# Raycasts must see only the architectural render mesh. Gameplay proxy meshes,
# marker spheres, old collision and later-created barricades can otherwise
# intercept the ray before it reaches the church surface.
hidden_for_fit=[]
for o in list(scene.objects):
    if o.type=="MESH" and o not in lod_objects:
        hidden_for_fit.append((o, o.hide_get()))
        o.hide_set(True)

# Build fitted collision by duplicating each zone's actual LOD mesh, then reducing.
zone_colliders={}
for src in lod_objects:
    zone=classify(src)
    if zone=="other":
        continue
    dup=src.copy()
    dup.data=src.data.copy()
    dup.name=f"COLV2_{zone}_{src.name}"
    collision_col.objects.link(dup)
    # Keep collision faithful but much lighter than render mesh.
    tri_count=len(dup.data.polygons)
    if tri_count > 800:
        mod=dup.modifiers.new("COLLISION_DECIMATE","DECIMATE")
        # Small rooms keep more detail; huge church/exterior become aggressive.
        target = 8000 if zone in {"main_church","exterior"} else 3000
        mod.ratio=max(0.015,min(0.22,target/max(tri_count,1)))
        mod.use_collapse_triangulate=True
        bpy.context.view_layer.objects.active=dup
        dup.select_set(True)
        try:
            bpy.ops.object.modifier_apply(modifier=mod.name)
        except Exception as exc:
            print("WARN decimate",dup.name,exc)
        dup.select_set(False)

    # Remove tiny disconnected floating fragments by keeping all geometry for now;
    # scan cleanup will be a later authored pass. Collision gets project metadata.
    dup["xziel_collision"]="fitted_scan_proxy_v2"
    dup["zone"]=zone
    dup["source_object"]=src.name
    dup.data.materials.clear()
    dup.data.materials.append(COL_MAT)
    zone_colliders.setdefault(zone,[]).append(dup)

# Hide fitted collision from raycast so rays only hit the visual church.
for c in collision_col.objects:
    c.hide_set(True)

player = next((x for x in plan["interactives"] if x["kind"]=="player_spawn"),None)
player_pos=Vector(player["location"]) if player else Vector((0,0,0))

def zone_center(zone):
    info=plan["zones"].get(zone)
    if not info:
        return player_pos
    return Vector(info["center"])

# Raycast helper: try several heights and slight fan angles. This tends to land
# on the actual wall surface separating an outside spawn from the playable room.
def find_surface(spawn, zone):
    target=zone_center(zone)
    base_dir=target-spawn
    if base_dir.length<0.01:
        base_dir=player_pos-spawn
    if base_dir.length<0.01:
        base_dir=Vector((1,0,0))
    base_dir.normalize()

    best=None
    # horizontal fan around the target direction
    yaw0=math.atan2(base_dir.y,base_dir.x)
    for zoff in (0.5,1.0,1.5,2.0,2.5):
        origin=spawn+Vector((0,0,zoff))
        for deg in (0,-8,8,-16,16,-28,28):
            yaw=yaw0+math.radians(deg)
            d=Vector((math.cos(yaw),math.sin(yaw),base_dir.z))
            d.normalize()
            hit,loc,norm,face,obj,matrix = scene.ray_cast(depsgraph, origin, d, distance=40.0)
            original=getattr(obj,"original",None) if obj else None
            hit_name=(original.name if original else obj.name) if obj else ""
            if hit and hit_name in {x.name for x in lod_objects}:
                dist=(loc-origin).length
                if best is None or dist<best["distance"]:
                    best={"location":loc.copy(),"normal":norm.copy(),"object":obj,"distance":dist}
    return best

def create_barricade(name, loc, normal, zone, source_spawn, source_obj=None, confidence="raycast"):
    # Board frame: 1.8m wide, 2.2m tall, 0.12m thick.
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    o=bpy.context.object
    o.name=name
    o.dimensions=(1.8,0.12,2.2)
    # local Y points through wall normal, Z stays upright
    yaw=math.atan2(normal.y,normal.x)-math.pi/2
    o.rotation_euler=(0,0,yaw)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    move_to(o,barricade_col)
    o.data.materials.append(BAR_MAT)
    o["xziel_kind"]="barricade"
    o["zone"]=zone
    o["source_spawn"]=source_spawn
    o["fit_method"]=confidence
    if source_obj: o["surface_object"]=source_obj
    # Keep fitted barricades out of subsequent surface raycasts.
    o.hide_set(True)
    return o

def add_nav(name, loc, zone, kind, props=None):
    o=bpy.data.objects.new(name,None)
    o.empty_display_type="SPHERE"
    o.empty_display_size=0.35
    o.location=loc
    o["zone"]=zone
    o["xziel_nav_kind"]=kind
    if props:
        for k,v in props.items(): o[k]=v
    nav_col.objects.link(o)
    return o

fitted=[]
misses=[]
for e in plan["interactives"]:
    if e["kind"]!="zombie_spawn":
        continue
    props=e.get("properties") or {}
    zone=norm_zone(props.get("zone","main_church"))
    spawn=Vector(e["location"])
    hit=find_surface(spawn,zone)
    if hit:
        # Offset slightly toward the spawn so the barricade doesn't z-fight.
        n=hit["normal"]
        if n.length<0.01: n=(zone_center(zone)-spawn).normalized()
        # Ensure normal points generally toward spawn side.
        if n.dot(spawn-hit["location"])<0: n=-n
        loc=hit["location"]+n*0.07
        loc.z=max(loc.z, plan["zones"][zone]["min"][2]+1.1 if zone in plan["zones"] else loc.z)
        b=create_barricade(
            "BARV2_"+e["name"],loc,n,zone,e["name"],hit["object"].name,"raycast"
        )
        inside=loc-n*1.5
        outside=loc+n*1.5
        add_nav("NAV_IN_"+e["name"],inside,zone,"barricade_inside",{"barricade":b.name})
        add_nav("NAV_OUT_"+e["name"],outside,zone,"barricade_outside",{"barricade":b.name})
        fitted.append({
            "spawn":e["name"],"zone":zone,
            "barricade":b.name,
            "location":list(loc),"normal":list(n),
            "surfaceObject":hit["object"].name,
            "distanceFromSpawn":hit["distance"],
            "inside":list(inside),"outside":list(outside),
            "fitMethod":"raycast",
        })
    else:
        # Conservative fallback so every spawn remains connected in data.
        d=zone_center(zone)-spawn
        if d.length<0.01: d=Vector((1,0,0))
        d.normalize()
        loc=spawn+d*1.5+Vector((0,0,1.1))
        n=-d
        b=create_barricade("BARV2_"+e["name"],loc,n,zone,e["name"],None,"fallback")
        inside=loc-n*1.5
        outside=loc+n*1.5
        add_nav("NAV_IN_"+e["name"],inside,zone,"barricade_inside",{"barricade":b.name})
        add_nav("NAV_OUT_"+e["name"],outside,zone,"barricade_outside",{"barricade":b.name})
        misses.append(e["name"])
        fitted.append({
            "spawn":e["name"],"zone":zone,"barricade":b.name,
            "location":list(loc),"normal":list(n),
            "inside":list(inside),"outside":list(outside),
            "fitMethod":"fallback",
        })

# Add zone center nav graph and connect to nearest inside barricade node.
zone_nodes={}
for zone,info in plan["zones"].items():
    if zone=="other": continue
    c=Vector(info["center"])
    c.z=info["min"][2]+0.25
    zone_nodes[zone]=add_nav("NAV_ZONE_"+zone.upper(),c,zone,"zone_center")

links=[
    ("exterior","main_church"),
    ("main_church","office_corridor"),
    ("office_corridor","office"),
    ("office_corridor","boiler"),
    ("main_church","tower_stairs"),
    ("tower_stairs","ringing_chamber"),
    ("ringing_chamber","clock_chamber"),
    ("clock_chamber","roof_chamber"),
    ("roof_chamber","tower_top"),
    ("tower_top","turret"),
]
edges=[]
for a,b in links:
    if a in zone_nodes and b in zone_nodes:
        edges.append({"a":zone_nodes[a].name,"b":zone_nodes[b].name,"kind":"zone_link"})

for rec in fitted:
    zn=zone_nodes.get(rec["zone"])
    if zn:
        edges.append({"a":zn.name,"b":"NAV_IN_"+rec["spawn"],"kind":"barricade_link"})
        edges.append({"a":"NAV_IN_"+rec["spawn"],"b":"NAV_OUT_"+rec["spawn"],"kind":"breach_link"})

# Restore scene visibility and unhide generated runtime geometry for export.
for o,was_hidden in hidden_for_fit:
    if o.name in bpy.data.objects:
        o.hide_set(was_hidden)
for c in collision_col.objects:
    c.hide_set(False)
for b in barricade_col.objects:
    b.hide_set(False)

def export_collection(col, path):
    bpy.ops.object.select_all(action="DESELECT")
    meshes=[o for o in col.objects if o.type=="MESH"]
    for o in meshes:
        o.select_set(True)
    if meshes:
        bpy.context.view_layer.objects.active=meshes[0]
        bpy.ops.export_scene.gltf(
            filepath=str(path),
            export_format="GLB",
            use_selection=True,
            export_apply=True,
        )

export_collection(collision_col, OUTDIR/"church_collision_fitted_v2.glb")
export_collection(barricade_col, OUTDIR/"church_barricades_fitted_v2.glb")

report={
    "schemaVersion":2,
    "fittedCollisionZones":{k:len(v) for k,v in zone_colliders.items()},
    "barricades":fitted,
    "fallbackBarricades":misses,
    "navEdges":edges,
    "counts":{
        "collisionMeshes":sum(len(v) for v in zone_colliders.values()),
        "barricades":len(fitted),
        "raycastFitted":len(fitted)-len(misses),
        "fallback":len(misses),
        "navNodes":len(nav_col.objects),
        "navEdges":len(edges),
    },
}
(OUTDIR/"church_runtime_fitted_v2.json").write_text(json.dumps(report,indent=2),encoding="utf-8")

bpy.ops.wm.save_as_mainfile(filepath=str(OUTDIR/"church_zombies_runtime_fitted_v2.blend"))
print("RUNTIME_FITTED_V2_OK",json.dumps(report["counts"]))
