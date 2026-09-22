#!/usr/bin/env python3
"""Bake a rigged glTF zombie into deterministic OBJ vertex frames for Quake MDL."""
import argparse, json, math, struct, sys, zlib
from pathlib import Path
import bpy

def cli():
    argv=sys.argv
    extra=argv[argv.index("--")+1:] if "--" in argv else []
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--contract",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--target-height",type=float,default=64.0)
    p.add_argument("--max-source-verts",type=int,default=1200)
    p.add_argument("--max-source-tris",type=int,default=1600)
    return p.parse_args(extra)

args=cli()
src=Path(args.input).resolve()
contract=json.loads(Path(args.contract).read_text(encoding="utf-8"))
out=Path(args.output).resolve()
frames_dir=out/"frames"
frames_dir.mkdir(parents=True,exist_ok=True)

if contract["frame_count"]>256:
    raise SystemExit("contract exceeds Vril MAXALIASFRAMES=256")

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(src))
meshes=sorted([o for o in bpy.context.scene.objects if o.type=="MESH"],key=lambda o:o.name)
arms=sorted([o for o in bpy.context.scene.objects if o.type=="ARMATURE"],key=lambda o:o.name)
if not meshes: raise SystemExit("no mesh objects")
if not arms: raise SystemExit("no armature")

total_v=sum(len(o.data.vertices) for o in meshes)
total_t=sum(len(o.data.polygons) for o in meshes)
ratio=min(1.0,args.max_source_verts/max(1,total_v),args.max_source_tris/max(1,total_t))
if ratio<0.999:
    ratio*=0.94
    for obj in meshes:
        bpy.context.view_layer.objects.active=obj
        obj.select_set(True)
        mod=obj.modifiers.new(name="XZIEL_COMPAT_DECIMATE",type="DECIMATE")
        mod.ratio=max(0.05,ratio)
        while list(obj.modifiers).index(mod)>0:
            bpy.ops.object.modifier_move_up(modifier=mod.name)
        bpy.ops.object.modifier_apply(modifier=mod.name)
        obj.select_set(False)

actions={a.name:a for a in bpy.data.actions}
action_names=sorted(actions)

def action_match(name):
    if not name: return None
    if name in actions: return actions[name]
    needle=name.lower()
    for n,a in actions.items():
        low=n.lower()
        if low.endswith(needle) or needle in low:
            return a
    return None

def choose_action(group):
    for name in (
        group.get("action"), group.get("fallback_action"),
        "HitReact","Idle","Walk","Run","Death"
    ):
        a=action_match(name)
        if a is not None: return a
    raise SystemExit("no usable action; available="+repr(action_names))

def png(path,w=128,h=128,rgba=(92,88,78,255)):
    raw=b"".join(b"\x00"+bytes(rgba)*w for _ in range(h))
    def chunk(tag,data):
        return struct.pack(">I",len(data))+tag+data+struct.pack(">I",zlib.crc32(tag+data)&0xffffffff)
    data=b"\x89PNG\r\n\x1a\n"
    data+=chunk(b"IHDR",struct.pack(">IIBBBBB",w,h,8,6,0,0,0))
    data+=chunk(b"IDAT",zlib.compress(raw,9))
    data+=chunk(b"IEND",b"")
    path.write_bytes(data)

skin=out/"prototype_skin.png"
png(skin)

# Normalize overall height to Quake-like units while leaving animation authored in place.
from mathutils import Vector
points=[]
for obj in meshes:
    points += [obj.matrix_world@Vector(c) for c in obj.bound_box]
minz=min(v.z for v in points); maxz=max(v.z for v in points)
scale=args.target_height/max(0.0001,maxz-minz)
for obj in meshes+arms:
    obj.scale=tuple(v*scale for v in obj.scale)
bpy.context.view_layer.update()

scene=bpy.context.scene

def set_action(action,u,mode):
    for arm in arms:
        if arm.animation_data is None: arm.animation_data_create()
        arm.animation_data.action=action
    start,end=map(float,action.frame_range)
    if mode=="reverse": u=1.0-u
    elif mode=="hold_start": u=0.0
    u=max(0.0,min(1.0,u))
    value=start+u*max(0.0,end-start)
    base=math.floor(value)
    scene.frame_set(int(base),subframe=value-base)
    bpy.context.view_layer.update()

def export_obj(path):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in meshes: obj.select_set(True)
    bpy.context.view_layer.objects.active=meshes[0]

    # Blender <=3.x ships export_scene.obj; Blender 4.x moved OBJ export to wm.obj_export.
    if hasattr(bpy.ops.export_scene, "obj"):
        bpy.ops.export_scene.obj(
            filepath=str(path),
            use_selection=True,
            use_animation=False,
            use_mesh_modifiers=True,
            use_edges=False,
            use_normals=True,
            use_uvs=True,
            use_materials=False,
            keep_vertex_order=True,
            axis_forward="X",
            axis_up="Z"
        )
    else:
        bpy.ops.wm.obj_export(
            filepath=str(path),
            export_animation=False,
            export_selected_objects=True,
            apply_modifiers=True,
            export_uv=True,
            export_normals=True,
            export_materials=False,
            forward_axis="X",
            up_axis="Z"
        )

groups=[None]*contract["frame_count"]
for g in contract["groups"]:
    for idx in range(g["start"],g["end"]+1):
        if idx<0 or idx>=len(groups): raise SystemExit("frame out of range")
        if groups[idx] is not None: raise SystemExit("duplicate frame "+str(idx))
        groups[idx]=g
if any(g is None for g in groups):
    raise SystemExit("unmapped contract frames")

records=[]
for idx,g in enumerate(groups):
    action=choose_action(g)
    count=g["end"]-g["start"]+1
    local=idx-g["start"]
    u=0.0 if count<=1 else local/(count-1)
    phase=float(g.get("phase",0.0))
    mode=g.get("sampling","once")
    if mode=="loop": u=(u+phase)%1.0
    elif phase: u=min(1.0,max(0.0,phase+(1.0-phase)*u))
    set_action(action,u,mode)
    frame_name=f"{idx:03d}_{g['name']}"
    obj=frames_dir/(frame_name+".obj")
    export_obj(obj)
    records.append({"index":idx,"name":frame_name,"group":g["name"],"action":action.name,"mesh":obj.name})

mdl={
    "mesh":str(Path("frames")/records[0]["mesh"]),
    "skins":[{"image":skin.name}],
    "frames":[{"name":r["name"][:15],"mesh":str(Path("frames")/r["mesh"])} for r in records]
}
(out/"model.json").write_text(json.dumps(mdl,indent=2)+"\n",encoding="utf-8")
report={
    "source":str(src),
    "source_meshes":[o.name for o in meshes],
    "armatures":[o.name for o in arms],
    "actions":action_names,
    "source_vertices_before":total_v,
    "source_triangles_before":total_t,
    "decimation_ratio":ratio,
    "target_height":args.target_height,
    "frame_count":len(records)
}
(out/"bake_report.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2))
