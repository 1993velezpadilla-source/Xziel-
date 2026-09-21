import bpy
import json
import math
import os
from pathlib import Path
from mathutils import Vector

MASTER = os.environ.get("CHURCH_GAMEPLAY_BLEND", "church/out/church_zombies_gameplay_v1.blend")
PLAN = Path(os.environ.get("CHURCH_PLAN", "church/out/zombies_map_plan.json"))
OUTDIR = Path(os.environ.get("CHURCH_OUT", "church/out"))
OUTDIR.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=MASTER)
plan = json.loads(PLAN.read_text(encoding="utf-8"))

for name in ["RUNTIME_COLLISION_V1", "RUNTIME_NAV_V1"]:
    col = bpy.data.collections.get(name)
    if col:
        for obj in list(col.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(col)

collision_col = bpy.data.collections.new("RUNTIME_COLLISION_V1")
nav_col = bpy.data.collections.new("RUNTIME_NAV_V1")
bpy.context.scene.collection.children.link(collision_col)
bpy.context.scene.collection.children.link(nav_col)

MAT = bpy.data.materials.get("COLLISION_PROXY") or bpy.data.materials.new("COLLISION_PROXY")
MAT.diffuse_color = (0.15, 0.75, 1.0, 0.35)
MAT.use_nodes = True
bsdf = MAT.node_tree.nodes.get("Principled BSDF")
if bsdf:
    bsdf.inputs["Base Color"].default_value = (0.15,0.75,1.0,1.0)
    bsdf.inputs["Roughness"].default_value = 0.8

NAVMAT = bpy.data.materials.get("NAV_PROXY") or bpy.data.materials.new("NAV_PROXY")
NAVMAT.diffuse_color = (0.2, 1.0, 0.25, 0.5)

def move_to_collection(obj, col):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)

def add_box(name, center, dims, col=collision_col, mat=MAT, props=None):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
    o=bpy.context.object
    o.name=name
    o.dimensions=dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to_collection(o,col)
    if mat:
        o.data.materials.append(mat)
    if props:
        for k,v in props.items(): o[k]=v
    return o

def add_ramp(name, a, b, width=2.2, thickness=0.35):
    a=Vector(a); b=Vector(b)
    mid=(a+b)*0.5
    d=b-a
    length=max(d.length,0.1)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=mid)
    o=bpy.context.object
    o.name=name
    o.dimensions=(width, length, thickness)
    # cube local Y points along route
    yaw=math.atan2(d.y,d.x)-math.pi/2
    horiz=max(math.hypot(d.x,d.y),0.001)
    pitch=math.atan2(d.z,horiz)
    o.rotation_euler=(pitch,0,yaw)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to_collection(o,collision_col)
    o.data.materials.append(MAT)
    o["xziel_collision"]="route_link"
    return o

def add_nav_node(name, p, zone, kind="zone_center"):
    o=bpy.data.objects.new(name,None)
    o.empty_display_type="SPHERE"
    o.empty_display_size=0.45
    o.location=p
    o["xziel_nav_kind"]=kind
    o["zone"]=zone
    nav_col.objects.link(o)
    return o

zones=plan["zones"]
aliases={"courtyard":"exterior","nave":"main_church","altar":"main_church"}
def nz(n): return aliases.get(n,n)

collision_objects=[]
nav_nodes={}

# Floor slabs and perimeter guard rails derived from actual zone bounds.
for zone, info in zones.items():
    if zone=="other":
        continue
    mn=Vector(info["min"]); mx=Vector(info["max"]); size=mx-mn
    c=(mn+mx)*0.5

    # Floor only: visual geometry remains the source scan. These proxies are
    # deliberately conservative and easy to replace with hand-authored hulls.
    floor_thick=0.28
    floor_center=Vector((c.x,c.y,mn.z-floor_thick*0.5))
    floor_dims=(max(size.x,0.5),max(size.y,0.5),floor_thick)
    o=add_box(f"COL_FLOOR_{zone.upper()}",floor_center,floor_dims,
              props={"xziel_collision":"floor","zone":zone})
    collision_objects.append(o)

    # Thin outer rails prevent the blockout player from falling through the
    # photogrammetry edge before final collision hulls are fitted.
    rail_h=min(max(size.z*0.12,1.4),3.2)
    t=0.18
    z=mn.z+rail_h*0.5
    for suffix, pos, dims in [
        ("W", (mn.x-t*0.5,c.y,z), (t,max(size.y,0.5),rail_h)),
        ("E", (mx.x+t*0.5,c.y,z), (t,max(size.y,0.5),rail_h)),
        ("S", (c.x,mn.y-t*0.5,z), (max(size.x,0.5),t,rail_h)),
        ("N", (c.x,mx.y+t*0.5,z), (max(size.x,0.5),t,rail_h)),
    ]:
        o=add_box(f"COL_RAIL_{zone.upper()}_{suffix}",pos,dims,
                  props={"xziel_collision":"guard","zone":zone})
        collision_objects.append(o)

    node=add_nav_node(f"NAV_{zone.upper()}_CENTER",(c.x,c.y,mn.z+0.15),zone)
    nav_nodes[zone]=node

# Topology links follow the map package progression graph.
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
route_objects=[]
for a,b in links:
    if a not in nav_nodes or b not in nav_nodes: continue
    pa=nav_nodes[a].location.copy()
    pb=nav_nodes[b].location.copy()
    ramp=add_ramp(f"COL_ROUTE_{a.upper()}__{b.upper()}",pa,pb)
    ramp["from_zone"]=a; ramp["to_zone"]=b
    route_objects.append(ramp)
    nav_nodes[a][f"link_{b}"]=nav_nodes[b].name
    nav_nodes[b][f"link_{a}"]=nav_nodes[a].name

# Barricade/nav candidates from zombie-spawn interactives. Put an approach
# node slightly toward the player start so a later fitter can snap it to the
# nearest real opening/window.
player = next((x for x in plan["interactives"] if x["kind"]=="player_spawn"),None)
player_pos=Vector(player["location"]) if player else Vector((0,0,0))
window_candidates=[]
for e in plan["interactives"]:
    if e["kind"]!="zombie_spawn": continue
    p=Vector(e["location"])
    zone=nz((e.get("properties") or {}).get("zone","main_church"))
    v=player_pos-p
    if v.length<0.1: v=Vector((1,0,0))
    v.normalize()
    w=p+v*1.2
    node=add_nav_node("APPROACH_"+e["name"],w,zone,"window_approach")
    node["spawn_name"]=e["name"]
    window_candidates.append({
        "spawn":e["name"],"zone":zone,
        "spawnPosition":list(p),"approachPosition":list(w)
    })

# Export collision GLB.
bpy.ops.object.select_all(action="DESELECT")
for o in list(collision_col.objects):
    if o.type=="MESH": o.select_set(True)
mesh_objs=[o for o in collision_col.objects if o.type=="MESH"]
if mesh_objs:
    bpy.context.view_layer.objects.active=mesh_objs[0]
    bpy.ops.export_scene.gltf(
        filepath=str(OUTDIR/"church_collision_proxy_v1.glb"),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
    )

nav_data={
    "schemaVersion":1,
    "nodes":[
        {
            "id":o.name,
            "position":[o.location.x,o.location.y,o.location.z],
            "zone":o.get("zone"),
            "kind":o.get("xziel_nav_kind"),
            "links":[v for k,v in o.items() if str(k).startswith("link_")],
        } for o in nav_col.objects
    ],
    "windowCandidates":window_candidates,
    "notes":[
        "Proxy collision is conservative blockout geometry; visual scan remains separate.",
        "Window candidates require final raycast/surface fitting before shipping.",
        "Route ramps validate vertical connectivity only; replace with authored stairs/nav links as geometry is fictionalized.",
    ],
}
(OUTDIR/"church_nav_proxy_v1.json").write_text(json.dumps(nav_data,indent=2),encoding="utf-8")
bpy.ops.wm.save_as_mainfile(filepath=str(OUTDIR/"church_zombies_collision_nav_v1.blend"))
print("COLLISION_NAV_PASS_OK",len(collision_objects),len(route_objects),len(nav_data["nodes"]),len(window_candidates))
