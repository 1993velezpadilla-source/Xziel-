#!/usr/bin/env python3
"""Retarget a CMU human mocap walk onto the official NZ:P ZombieRig.

The stock 211-frame Zombie action is copied intact. Only standing walk ranges
37-82 in QuakeC terms (Blender action frames 38-83) are overwritten.
"""
import argparse, json, math, shutil, sys
from pathlib import Path
import bpy

def parse():
    extra=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    p=argparse.ArgumentParser()
    p.add_argument("--mocap",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--name",required=True)
    p.add_argument("--skin-dir",required=True)
    return p.parse_args(extra)

args=parse()
out=Path(args.output).resolve()
out.mkdir(parents=True,exist_ok=True)
frames_root=out/"frames"
frames_root.mkdir(exist_ok=True)

target=bpy.data.objects.get("ZombieRig")
if target is None or target.type!="ARMATURE":
    raise SystemExit("official ZombieRig not found")
base=bpy.data.actions.get("Zombie")
if base is None:
    raise SystemExit("stock 211-frame Zombie action not found")
if target.animation_data is None:
    target.animation_data_create()

# Import CMU FBX into the official source scene.
before_objects=set(o.name for o in bpy.data.objects)
before_armatures=set(o.name for o in bpy.data.objects if o.type=="ARMATURE")
bpy.ops.import_scene.fbx(filepath=str(Path(args.mocap).resolve()))
sources=[o for o in bpy.data.objects if o.type=="ARMATURE" and o.name not in before_armatures and o!=target]
if len(sources)!=1:
    raise SystemExit("expected exactly one imported CMU armature, got "+repr([o.name for o in sources]))
source=sources[0]
source_name=source.name
if source.animation_data is None or source.animation_data.action is None:
    # FBX importer can leave the action datablock present but detached.
    candidates=[a for a in bpy.data.actions if a!=base and source.name.lower() in a.name.lower()]
    if not candidates:
        raise SystemExit("CMU action not found")
    source.animation_data_create()
    source.animation_data.action=max(candidates,key=lambda a:a.frame_range[1]-a.frame_range[0])
src_action=source.animation_data.action

variant=base.copy()
variant.name="XZIEL_"+args.name
target.animation_data.action=variant

# CMU -> official NZ:P ZombieRig. The CMU skeleton has one hip root while NZ:P
# intentionally splits torso and leg roots, so hip rotation feeds both pelvis roots
# while abdomen/chest feed the two spine bones.
bone_map={
    "spine1":"abdomen",
    "spine2":"chest",
    "shoulder_L":"lCollar",
    "u_arm_L":"lShldr",
    "l_arm_L":"lForeArm",
    "hand_L":"lHand",
    "shoulder_r":"rCollar",
    "u_arm_R":"rShldr",
    "l_arm_R":"rForeArm",
    "hand_R":"rHand",
    "head":"head",
    "pelvis_L":"hip",
    "thigh_L":"lThigh",
    "shin_L":"lShin",
    "foot_L":"lFoot",
    "pelvis_R":"hip",
    "thigh_R":"rThigh",
    "shin_R":"rShin",
    "foot_R":"rFoot",
}
missing=[(t,s) for t,s in bone_map.items() if t not in target.pose.bones or s not in source.pose.bones]
if missing:
    raise SystemExit("missing retarget bones: "+repr(missing))

# Convert source local animation rotations through each bone's rest orientation so
# different local bone axes do not get copied as raw quaternion components.
def retarget_quat(tname,sname):
    sb=source.data.bones[sname]
    tb=target.data.bones[tname]
    sp=source.pose.bones[sname]
    srest=sb.matrix_local.to_quaternion()
    trest=tb.matrix_local.to_quaternion()
    qlocal=sp.matrix_basis.to_quaternion()
    delta_arm=srest @ qlocal @ srest.inverted()
    return (trest.inverted() @ delta_arm @ trest).normalized()

src_start,src_end=map(float,src_action.frame_range)
scene=bpy.context.scene

# QuakeC uses 0-based body frames. Blender stock action uses 1..211, hence +1.
walk_groups=[
    (38,53,0.00), # QC 37-52
    (54,67,0.33), # QC 53-66
    (68,83,0.66), # QC 67-82
]
samples=[]
for start,end,phase in walk_groups:
    count=end-start+1
    for frame in range(start,end+1):
        u=0.0 if count<=1 else (frame-start)/(count-1)
        u=(u+phase)%1.0
        sf=src_start+u*max(0.0,src_end-src_start)
        whole=math.floor(sf)
        source.animation_data.action=src_action
        scene.frame_set(int(whole),subframe=sf-whole)
        bpy.context.view_layer.update()

        # Target remains on copied stock action. Overwrite only mapped bone rotations.
        target.animation_data.action=variant
        for tname,sname in bone_map.items():
            pb=target.pose.bones[tname]
            pb.rotation_mode="QUATERNION"
            pb.rotation_quaternion=retarget_quat(tname,sname)
            pb.keyframe_insert(
                data_path="rotation_quaternion",
                frame=frame,
                group=tname,
                options={"INSERTKEY_REPLACE","INSERTKEY_NEEDED"},
            )
        samples.append({"target_frame":frame,"source_frame":sf})

# Remove imported CMU objects before exporting the NZ:P model.
for obj in list(bpy.data.objects):
    if obj.name not in before_objects and obj!=target and obj.type in {"MESH","ARMATURE","EMPTY"}:
        try: bpy.data.objects.remove(obj,do_unlink=True)
        except Exception: pass

target.animation_data.action=variant
scene.frame_start=1
scene.frame_end=211

# Copy the original four stock skins; all generated segmented MDLs keep the stock UVs.
skin_dir=Path(args.skin_dir).resolve()
skins=[]
for i in range(4):
    src=skin_dir/f"texture_{i}.png"
    if not src.exists(): raise SystemExit("missing stock skin "+str(src))
    dst=out/f"texture_{i}.png"
    shutil.copy2(src,dst)
    skins.append(dst.name)

parts={
    "body":"ZombieBody",
    "head":"ZombieHead",
    "larm":"ZombieLarm",
    "rarm":"ZombieRarm",
    "full":"FullZombie",
}
for label,obj_name in parts.items():
    if bpy.data.objects.get(obj_name) is None:
        raise SystemExit("missing stock export mesh "+obj_name)
    (frames_root/label).mkdir(parents=True,exist_ok=True)

def export_selected(obj,path):
    """Write a stable OBJ without Blender's animation-dependent normal splitting.

    Every face references:
      - the original mesh vertex index for position,
      - a stable UV-table index derived from the authored UV coordinate,
      - the same mesh vertex index for its animated vertex normal.

    quake-export unifies those three OBJ indices. Because their *indices* are
    stable across frames, the MDL topology stays stable while positions and
    normal vectors are free to animate.
    """
    depsgraph=bpy.context.evaluated_depsgraph_get()
    eval_obj=obj.evaluated_get(depsgraph)
    mesh=eval_obj.to_mesh(preserve_all_data_layers=True,depsgraph=depsgraph)
    try:
        mesh.calc_loop_triangles()
        uv_layer=mesh.uv_layers.active
        if uv_layer is None:
            raise RuntimeError("mesh has no active UV layer: "+obj.name)

        # Stable UV table: UV data is authored/static even while the armature
        # deforms positions. Rounding only normalizes floating serialization.
        uv_to_index={}
        uv_values=[]
        loop_uv_index={}
        for li,loop in enumerate(mesh.loops):
            uv=uv_layer.data[li].uv
            key=(round(float(uv.x),8),round(float(uv.y),8))
            if key not in uv_to_index:
                uv_to_index[key]=len(uv_values)+1
                uv_values.append(key)
            loop_uv_index[li]=uv_to_index[key]

        # Match the previous Quake-oriented exporter: Blender -Y forward ->
        # Quake +X forward, Blender +X right -> Quake +Y.
        def axis(v):
            return (-float(v.y),float(v.x),float(v.z))

        normal_matrix=eval_obj.matrix_world.to_3x3().inverted().transposed()
        world_matrix=eval_obj.matrix_world

        with open(path,"w",encoding="ascii",newline="\n") as fh:
            fh.write("g xziel_zombie\n")
            for v in mesh.vertices:
                p=world_matrix@v.co
                x,y,z=axis(p)
                fh.write(f"v {x:.9f} {y:.9f} {z:.9f}\n")
            for u,v in uv_values:
                fh.write(f"vt {u:.9f} {v:.9f}\n")
            for vert in mesh.vertices:
                n=(normal_matrix@vert.normal).normalized()
                x,y,z=axis(n)
                fh.write(f"vn {x:.9f} {y:.9f} {z:.9f}\n")
            for tri in mesh.loop_triangles:
                corners=[]
                for vi,li in zip(tri.vertices,tri.loops):
                    pidx=int(vi)+1
                    tidx=loop_uv_index[int(li)]
                    nidx=pidx
                    corners.append(f"{pidx}/{tidx}/{nidx}")
                fh.write("f "+" ".join(corners)+"\n")
    finally:
        eval_obj.to_mesh_clear()

for quake_index in range(211):
    scene.frame_set(quake_index+1)
    bpy.context.view_layer.update()
    for label,obj_name in parts.items():
        export_selected(bpy.data.objects[obj_name],frames_root/label/f"{quake_index:03d}.obj")

for label in parts:
    frames=[{"name":f"{i:03d}","mesh":str(Path("frames")/label/f"{i:03d}.obj")} for i in range(211)]
    cfg={
        "mesh":frames[0]["mesh"],
        "skins":[{"image":s} for s in skins],
        "frames":frames,
    }
    (out/f"{label}.json").write_text(json.dumps(cfg,indent=2)+"\n",encoding="utf-8")

report={
    "name":args.name,
    "mocap":args.mocap,
    "source_armature":source_name,
    "source_action":src_action.name,
    "source_frame_range":[src_start,src_end],
    "target_action":variant.name,
    "target_frame_range":[1,211],
    "overwritten_qc_walk_ranges":[[37,52],[53,66],[67,82]],
    "bone_map":bone_map,
    "samples":samples,
    "parts":parts,
}
(out/"retarget_report.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
bpy.ops.wm.save_as_mainfile(filepath=str(out/(args.name+".blend")))
print("XZIEL_RETARGET_OK",json.dumps({k:report[k] for k in ("name","source_action","source_frame_range","overwritten_qc_walk_ranges")}))
