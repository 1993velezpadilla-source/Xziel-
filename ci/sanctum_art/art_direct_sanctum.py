import bpy
import json
import math
import os
from pathlib import Path
from mathutils import Vector

BLEND = os.environ["SANCTUM_BLEND"]
PLAN = Path(os.environ["SANCTUM_PLAN"])
OUT = Path(os.environ.get("SANCTUM_ART_OUT","art_out"))
OUT.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=BLEND)
scene=bpy.context.scene
plan=json.loads(PLAN.read_text(encoding="utf-8"))

# Hide all blockout/debug collections from final presentation.
for name in [
    "ZOMBIES_GAMEPLAY_V1","ZOMBIES_LABELS_V1",
    "RUNTIME_COLLISION_V1","RUNTIME_NAV_V1",
    "RUNTIME_COLLISION_FITTED_V2","BARRICADES_FITTED_V2","NAV_FITTED_V2",
]:
    col=bpy.data.collections.get(name)
    if col:
        col.hide_render=True
        col.hide_viewport=True

# Visual source stays authoritative.
for name in ["GAME_CHURCH_LOD0","SOURCE_CHURCH_FULL"]:
    col=bpy.data.collections.get(name)
    if col:
        col.hide_render=(name!="GAME_CHURCH_LOD0")
        col.hide_viewport=(name!="GAME_CHURCH_LOD0")

# Remove old inspection lights/camera helpers.
for o in list(scene.objects):
    if o.type=="LIGHT" and ("Gameplay_" in o.name or "Moon" in o.name or "Fill" in o.name):
        bpy.data.objects.remove(o, do_unlink=True)

def zone(name):
    return plan["zones"].get(name)

def v3(a): return Vector((float(a[0]),float(a[1]),float(a[2])))

# World: deep blue-black night.
scene.world.use_nodes=True
bg=scene.world.node_tree.nodes.get("Background")
bg.inputs["Color"].default_value=(0.004,0.008,0.018,1)
bg.inputs["Strength"].default_value=0.035

# Slight atmospheric volume for depth.
nodes=scene.world.node_tree.nodes
links=scene.world.node_tree.links
vol=nodes.get("SANCTUM_VOLUME")
if not vol:
    vol=nodes.new("ShaderNodeVolumePrincipled")
    vol.name="SANCTUM_VOLUME"
vol.inputs["Density"].default_value=0.007
vol.inputs["Color"].default_value=(0.03,0.04,0.065,1)
out=nodes.get("World Output")
if out:
    for link in list(out.inputs["Volume"].links):
        links.remove(link)
    links.new(vol.outputs["Volume"],out.inputs["Volume"])

def add_area(name,loc,energy,size,color):
    bpy.ops.object.light_add(type="AREA", location=loc)
    o=bpy.context.object
    o.name=name
    o.data.energy=energy
    o.data.shape="DISK"
    o.data.size=size
    o.data.color=color
    return o

def add_point(name,loc,energy,radius,color):
    bpy.ops.object.light_add(type="POINT", location=loc)
    o=bpy.context.object
    o.name=name
    o.data.energy=energy
    o.data.shadow_soft_size=radius
    o.data.color=color
    return o

def look_at(obj,target):
    d=Vector(target)-obj.location
    obj.rotation_euler=d.to_track_quat("-Z","Y").to_euler()

# Cool moon key from exterior/tower direction.
ext=zone("exterior") or zone("main_church")
main=zone("main_church")
tower=zone("tower_top") or zone("ringing_chamber")
boiler=zone("boiler")
ring=zone("ringing_chamber")
clock=zone("clock_chamber")

main_c=v3(main["center"])
main_size=v3(main["size"])
top_z=max(v["max"][2] for k,v in plan["zones"].items() if k!="other")
moon_loc=main_c+Vector((-main_size.x*0.7,main_size.y*0.9,top_z-main_c.z+20))
moon=add_area("SANCTUM_MOON_KEY",moon_loc,1300,max(main_size.x,main_size.y)*0.65,(0.18,0.28,0.52))
look_at(moon,main_c)

# Warm practicals — subtle, localized.
for zn,energy,radius,color in [
    ("main_church",480,3.5,(1.0,0.36,0.12)),
    ("boiler",650,2.5,(1.0,0.22,0.07)),
    ("ringing_chamber",420,2.0,(1.0,0.42,0.16)),
    ("clock_chamber",260,1.8,(0.32,0.48,0.95)),
]:
    info=zone(zn)
    if not info: continue
    p=v3(info["center"])
    p.z=info["min"][2]+min(2.8,max(1.5,info["size"][2]*0.25))
    add_point("SANCTUM_"+zn.upper(),p,energy,radius,color)

# Altar emphasis, still warm/dim.
altar=main_c.copy()
# Derive long-axis forward end.
axis=Vector((1,0,0)) if main_size.x>=main_size.y else Vector((0,1,0))
altar += axis*max(main_size.x,main_size.y)*0.27
altar.z=main["min"][2]+2.4
altar_light=add_area("SANCTUM_ALTAR_GLOW",altar+Vector((0,0,2.8)),620,4.0,(0.95,0.18,0.08))
look_at(altar_light,altar)

# Camera.
cam=scene.camera
if not cam:
    bpy.ops.object.camera_add()
    cam=bpy.context.object
    scene.camera=cam
cam.data.lens=35
cam.data.sensor_width=36
cam.data.clip_end=5000

scene.render.resolution_x=1920
scene.render.resolution_y=1080
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"

try:
    scene.render.engine="BLENDER_EEVEE_NEXT"
except Exception:
    try: scene.render.engine="BLENDER_EEVEE"
    except Exception: pass

# Eevee tuning when available.
if hasattr(scene,"eevee"):
    try:
        scene.eevee.use_gtao=True
        scene.eevee.gtao_distance=5
        scene.eevee.gtao_factor=1.5
        scene.eevee.use_soft_shadows=True
        scene.eevee.use_volumetric_lights=True
    except Exception:
        pass

def render(name,pos,target,lens=35):
    cam.location=Vector(pos)
    cam.data.lens=lens
    look_at(cam,target)
    scene.render.filepath=str(OUT/f"{name}.png")
    bpy.ops.render.render(write_still=True)

# Exterior hero: from courtyard side, low angle.
extc=v3(ext["center"])
extmin=v3(ext["min"]); extmax=v3(ext["max"])
approach=extc+Vector((-max(18,main_size.x*0.65),-max(12,main_size.y*0.35),2.1))
render("sanctum_exterior_night",approach,main_c+Vector((0,0,6)),32)

# Nave gameplay eye-level shot.
entry=main_c-axis*max(main_size.x,main_size.y)*0.32
entry.z=main["min"][2]+1.65
render("sanctum_nave_night",entry,altar+Vector((0,0,0.8)),28)

# Altar reverse dramatic.
altar_cam=altar+axis*8+Vector((0,0,1.6))
render("sanctum_altar_night",altar_cam,main_c+Vector((0,0,2.0)),38)

# Tower mood.
if ring:
    rc=v3(ring["center"])
    rmin=v3(ring["min"]); rmax=v3(ring["max"])
    pos=rc+Vector((max(3.0,(rmax.x-rmin.x)*0.4),-max(3.0,(rmax.y-rmin.y)*0.5),1.8))
    render("sanctum_tower_night",pos,rc+Vector((0,0,1.5)),30)

profile={
    "name":"SANCTUM_OF_ASH_ART_DIRECTION_V1",
    "visualAuthority":"GAME_CHURCH_LOD0 / XZSM v2, never BSP",
    "night":{
        "worldColor":[0.004,0.008,0.018],
        "worldStrength":0.035,
        "fogDensity":0.007,
        "moonColor":[0.18,0.28,0.52],
        "moonEnergy":1300,
    },
    "practicals":{
        "main_church":{"energy":480,"color":[1.0,0.36,0.12]},
        "boiler":{"energy":650,"color":[1.0,0.22,0.07]},
        "ringing_chamber":{"energy":420,"color":[1.0,0.42,0.16]},
        "clock_chamber":{"energy":260,"color":[0.32,0.48,0.95]},
        "altar":{"energy":620,"color":[0.95,0.18,0.08]},
    },
    "goals":[
        "cold exterior moonlight versus warm interior practicals",
        "altar visible as objective without overlighting the nave",
        "tower remains readable but threatening",
        "photogrammetry texture authority preserved",
        "no BSP architectural visuals",
    ],
}
(OUT/"sanctum_art_direction_v1.json").write_text(json.dumps(profile,indent=2),encoding="utf-8")
print("SANCTUM_ART_PASS_OK",json.dumps(profile["night"]))
