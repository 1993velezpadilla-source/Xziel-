import bpy, json, math, os, random
from pathlib import Path
from mathutils import Vector

BLEND=os.environ["SANCTUM_BLEND"]
FITTED=Path(os.environ["SANCTUM_FITTED"])
OUT=Path(os.environ.get("SANCTUM_DRESS_OUT","dressing_out"))
OUT.mkdir(parents=True,exist_ok=True)
random.seed(317)

bpy.ops.wm.open_mainfile(filepath=BLEND)
fit=json.loads(FITTED.read_text(encoding="utf-8"))

old=bpy.data.collections.get("SANCTUM_DRESSING_V1")
if old:
    for o in list(old.objects): bpy.data.objects.remove(o,do_unlink=True)
    bpy.data.collections.remove(old)
col=bpy.data.collections.new("SANCTUM_DRESSING_V1")
bpy.context.scene.collection.children.link(col)

def move(o):
    for c in list(o.users_collection): c.objects.unlink(o)
    col.objects.link(o)

def mat_principled(name,base,rough=0.7,metal=0.0):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes=True
    bsdf=m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value=(*base,1)
    bsdf.inputs["Roughness"].default_value=rough
    bsdf.inputs["Metallic"].default_value=metal
    return m

wood=mat_principled("SOA_WOOD",(0.19,0.075,0.025),0.88,0.0)
wood2=mat_principled("SOA_WOOD_DARK",(0.095,0.035,0.012),0.92,0.0)
metal=mat_principled("SOA_NAIL",(0.06,0.055,0.05),0.46,0.82)
stone=mat_principled("SOA_RUBBLE",(0.14,0.13,0.12),0.93,0.0)
wax=mat_principled("SOA_WAX",(0.72,0.62,0.38),0.78,0.0)

def bevel(o,w=0.035,segments=3):
    mod=o.modifiers.new("edge_wear","BEVEL")
    mod.width=w; mod.segments=segments
    bpy.context.view_layer.objects.active=o
    o.select_set(True)
    try: bpy.ops.object.modifier_apply(modifier=mod.name)
    except: pass
    o.select_set(False)

def board(name,loc,normal,width,height,thick,roll,material):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    o=bpy.context.object; o.name=name
    o.dimensions=(width,thick,height)
    yaw=math.atan2(normal.y,normal.x)-math.pi/2
    o.rotation_euler=(0,0,yaw+roll)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    bevel(o,0.045,3); move(o); o.data.materials.append(material)
    return o

def nail(name,loc,normal):
    bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=0.025,depth=0.13,location=loc)
    o=bpy.context.object; o.name=name
    # Cylinder local Z points through wall normal.
    o.rotation_euler=Vector((0,0,1)).rotation_difference(normal.normalized()).to_euler()
    move(o); o.data.materials.append(metal)
    return o

def rubble_piece(name,loc,scale):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=0.35,location=loc)
    o=bpy.context.object; o.name=name
    o.scale=(scale*random.uniform(.7,1.3),scale*random.uniform(.45,.95),scale*random.uniform(.35,.8))
    o.rotation_euler=(random.random()*2,random.random()*2,random.random()*2)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    bevel(o,0.025,2); move(o); o.data.materials.append(stone)
    return o

created=[]
for bi,b in enumerate(fit.get("barricades",[])):
    loc=Vector(b["location"]); n=Vector(b["normal"])
    if n.length<.01: n=Vector((1,0,0))
    n.normalize()
    # tangent across opening, upright Z.
    tangent=Vector((-n.y,n.x,0))
    if tangent.length<.01: tangent=Vector((1,0,0))
    tangent.normalize()
    for j,zoff in enumerate((-0.78,-0.38,0.03,0.44,0.84)):
        center=loc+Vector((0,0,zoff))+tangent*random.uniform(-0.12,0.12)+n*0.03
        w=random.uniform(1.65,2.05)
        h=random.uniform(.16,.24)
        roll=random.uniform(-0.12,0.12)
        o=board(f"BAR_{bi:02d}_{j}",center,n,w,h,.085,roll,wood if j%2 else wood2)
        created.append(o)
        # Two nails per plank.
        for ni,s in enumerate((-0.33,0.33)):
            p=center+tangent*(w*s)+n*0.055
            created.append(nail(f"NAIL_{bi:02d}_{j}_{ni}",p,n))
    # rubble outside/inside threshold
    for k in range(9):
        side=(-1 if k<4 else 1)
        rp=loc+n*side*random.uniform(.25,1.0)+tangent*random.uniform(-.8,.8)
        rp.z-=random.uniform(.65,.95)
        created.append(rubble_piece(f"RUBBLE_BAR_{bi:02d}_{k}",rp,random.uniform(.18,.38)))

# Altar candles and rubble cluster use the gameplay anchor that has already
# been snapped to the dominant real nave floor. Never derive art placement from
# zone bbox min.z: photogrammetry can contain low basement/shard geometry.
plan_path=Path(os.environ["SANCTUM_PLAN"])
plan=json.loads(plan_path.read_text(encoding="utf-8"))
main=plan["zones"]["main_church"]
mc=Vector(main["center"]); ms=Vector(main["size"])
axis=Vector((1,0,0)) if ms.x>=ms.y else Vector((0,1,0))
side=Vector((-axis.y,axis.x,0))
upgrade=next((x for x in plan.get("interactives",[]) if x.get("name")=="UPGRADE_ALTAR"),None)
if upgrade:
    altar=Vector(upgrade["location"])
    altar_floor_z=altar.z-0.70
else:
    altar=mc+axis*max(ms.x,ms.y)*0.27
    altar_floor_z=float(plan.get("floor_levels",{}).get("main_church",main["min"][2]))
    altar.z=altar_floor_z+0.70

for i in range(14):
    h=random.uniform(.22,.55)
    p=altar+side*random.uniform(-2.2,2.2)-axis*random.uniform(-1.2,1.1)
    p.z=altar_floor_z+h*0.5
    bpy.ops.mesh.primitive_cylinder_add(vertices=20,radius=random.uniform(.035,.065),depth=h,location=p)
    o=bpy.context.object; o.name=f"ALTAR_CANDLE_{i:02d}"; move(o); o.data.materials.append(wax); created.append(o)
for i in range(22):
    p=altar+side*random.uniform(-3.0,3.0)+axis*random.uniform(-1.0,2.0)
    p.z=altar_floor_z+random.uniform(.05,.16)
    created.append(rubble_piece(f"ALTAR_RUBBLE_{i:02d}",p,random.uniform(.16,.42)))


# Clean preview renders with the real church visible behind the dressing.
for name in ["ZOMBIES_GAMEPLAY_V1","ZOMBIES_LABELS_V1","RUNTIME_COLLISION_V1","RUNTIME_NAV_V1",
             "RUNTIME_COLLISION_FITTED_V2","BARRICADES_FITTED_V2","NAV_FITTED_V2"]:
    cc=bpy.data.collections.get(name)
    if cc:
        cc.hide_render=True
        cc.hide_viewport=True
lod=bpy.data.collections.get("GAME_CHURCH_LOD0")
if lod:
    lod.hide_render=False
    lod.hide_viewport=False
src=bpy.data.collections.get("SOURCE_CHURCH_FULL")
if src:
    src.hide_render=True
    src.hide_viewport=True

scene=bpy.context.scene
scene.world.use_nodes=True
bg=scene.world.node_tree.nodes.get("Background")
if bg:
    bg.inputs["Color"].default_value=(0.006,0.01,0.022,1)
    bg.inputs["Strength"].default_value=0.05
try:
    scene.render.engine="BLENDER_EEVEE_NEXT"
except Exception:
    try: scene.render.engine="BLENDER_EEVEE"
    except Exception: pass
scene.render.resolution_x=1600
scene.render.resolution_y=900
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"

cam=scene.camera
if not cam:
    bpy.ops.object.camera_add()
    cam=bpy.context.object
    scene.camera=cam
cam.data.clip_end=5000

def look_at(o,t):
    d=Vector(t)-o.location
    o.rotation_euler=d.to_track_quat("-Z","Y").to_euler()

def add_preview_light(name,loc,target,color,energy,size):
    bpy.ops.object.light_add(type="AREA",location=loc)
    l=bpy.context.object
    l.name=name
    l.data.energy=energy
    l.data.color=color
    l.data.shape="DISK"
    l.data.size=size
    look_at(l,target)
    return l

# Barricade close-up.
if fit.get("barricades"):
    b0=fit["barricades"][0]
    bloc=Vector(b0["location"])
    bn=Vector(b0["normal"])
    if bn.length<0.01: bn=Vector((1,0,0))
    bn.normalize()
    tangent=Vector((-bn.y,bn.x,0))
    cam.location=bloc+bn*4.7+tangent*1.4+Vector((0,0,1.4))
    cam.data.lens=42
    look_at(cam,bloc+Vector((0,0,0.25)))
    add_preview_light("DRESS_KEY",bloc+bn*2.5+Vector((0,0,3.0)),bloc,(0.28,0.42,0.85),850,3.0)
    add_preview_light("DRESS_WARM",bloc-bn*1.5+Vector((0,0,2.0)),bloc,(1.0,0.26,0.08),500,2.0)
    scene.render.filepath=str(OUT/"dressing_barricade_preview.png")
    bpy.ops.render.render(write_still=True)

# Altar dressing.
cam.location=Vector((altar.x,altar.y,altar_floor_z))+(-axis*7)+(side*3)+Vector((0,0,1.8))
cam.data.lens=36
look_at(cam,Vector((altar.x,altar.y,altar_floor_z+1.0)))
add_preview_light("ALTAR_KEY",altar-axis*1.5+Vector((0,0,4.5)),altar,(1.0,0.22,0.06),780,4.0)
scene.render.filepath=str(OUT/"dressing_altar_preview.png")
bpy.ops.render.render(write_still=True)

# Export only dressing.
bpy.ops.object.select_all(action="DESELECT")
meshes=[o for o in col.objects if o.type=="MESH"]
for o in meshes:o.select_set(True)
if meshes:
    bpy.context.view_layer.objects.active=meshes[0]
    bpy.ops.export_scene.gltf(filepath=str(OUT/"sanctum_dressing_v1.glb"),export_format="GLB",use_selection=True,export_apply=True)

report={
  "version":1,
  "barricadeCount":len(fit.get("barricades",[])),
  "meshObjects":len(meshes),
  "purpose":"Non-destructive visual dressing overlay; church scan remains visual authority.",
  "runtimeAsset":"sanctum_dressing_v1.glb"
}
(OUT/"sanctum_dressing_v1.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"sanctum_dressing_v1.blend"))
print("SANCTUM_DRESSING_OK",json.dumps(report))
