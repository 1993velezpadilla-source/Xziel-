#!/usr/bin/env python3
"""HAYUYA Blender AutoRig prototype.

Run with:
  blender -b --python tools/hayuya3d/blender_autorig.py -- \
    --target static.glb --donor donor.glb --output rigged.glb --report report.json

P0 strategy:
- import the generated static humanoid
- import the CC0 Quaternius animated donor
- fit the donor armature to the target's overall height/center
- discard donor render meshes
- bind target meshes to the armature with Blender automatic weights
- preserve donor animation actions and export a skinned/animated GLB

This is intentionally a first-pass autorig stage. Later revisions can replace
bounds fitting with landmark/body-part fitting without changing the pipeline API.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree


def parse_args():
    argv=sys.argv
    if "--" in argv:
        argv=argv[argv.index("--")+1:]
    else:
        argv=[]
    p=argparse.ArgumentParser()
    p.add_argument("--target",required=True,type=Path)
    p.add_argument("--donor",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--report",required=True,type=Path)
    return p.parse_args(argv)


def world_bbox(objects):
    pts=[]
    for obj in objects:
        if obj.type!="MESH":
            continue
        for corner in obj.bound_box:
            pts.append(obj.matrix_world @ Vector(corner))
    if not pts:
        raise RuntimeError("no mesh bounds")
    mins=Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts)))
    maxs=Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts)))
    return mins,maxs


def height_axis(ext):
    vals=[abs(ext.x),abs(ext.y),abs(ext.z)]
    return max(range(3),key=lambda i:vals[i])


def axis_value(v,axis):
    return (v.x,v.y,v.z)[axis]


def import_glb(path):
    before=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path.resolve()))
    return [o for o in bpy.data.objects if o not in before]


def select_only(*objects):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    if objects:
        bpy.context.view_layer.objects.active=objects[-1]


def main():
    args=parse_args()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.report.parent.mkdir(parents=True,exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)

    target_objs=import_glb(args.target)
    target_meshes=[o for o in target_objs if o.type=="MESH"]
    if not target_meshes:
        raise RuntimeError("target GLB has no meshes")

    target_min,target_max=world_bbox(target_meshes)
    target_ext=target_max-target_min
    target_axis=height_axis(target_ext)
    target_height=axis_value(target_ext,target_axis)
    if target_height<=1e-6:
        raise RuntimeError("target height is degenerate")

    donor_objs=import_glb(args.donor)
    donor_meshes=[o for o in donor_objs if o.type=="MESH"]
    donor_arms=[o for o in donor_objs if o.type=="ARMATURE"]
    if len(donor_arms)!=1:
        raise RuntimeError(f"expected one donor armature, got {len(donor_arms)}")
    arm=donor_arms[0]

    donor_min,donor_max=world_bbox(donor_meshes)
    donor_ext=donor_max-donor_min
    donor_axis=height_axis(donor_ext)
    donor_height=axis_value(donor_ext,donor_axis)
    if donor_height<=1e-6:
        raise RuntimeError("donor height is degenerate")

    # Blender glTF import should normalize both sources to the same Z-up scene.
    # If the dominant axes differ, keep going but report it for the next fitting pass.
    scale=target_height/donor_height
    arm.scale=Vector((scale,scale,scale))
    bpy.context.view_layer.update()

    # Align donor mesh envelope center and floor with target envelope.
    # Compute donor envelope after scaling armature. Donor mesh objects may be children.
    dmin2,dmax2=world_bbox(donor_meshes)
    target_center=(target_min+target_max)*0.5
    donor_center=(dmin2+dmax2)*0.5
    offset=target_center-donor_center
    # Prefer floor alignment on the target dominant axis.
    current_floor=axis_value(dmin2,donor_axis)
    desired_floor=axis_value(target_min,target_axis)
    if donor_axis==0: offset.x += desired_floor-current_floor
    elif donor_axis==1: offset.y += desired_floor-current_floor
    else: offset.z += desired_floor-current_floor
    arm.location += offset
    bpy.context.view_layer.update()

    arm.name="HAYUYA_Armature"

    # Build a spatial weight donor from the already-rigged CC0 human.
    # This is much more robust for TRELLIS meshes than Blender's Bone Heat
    # solver, because generated characters often contain hundreds of disconnected
    # clothing/hair/candy islands that make ARMATURE_AUTO fail.
    arm_bones={b.name for b in arm.data.bones}
    samples=[]
    for donor in donor_meshes:
        for v in donor.data.vertices:
            weights=[]
            for g in v.groups:
                if g.group < len(donor.vertex_groups):
                    name=donor.vertex_groups[g.group].name
                    if name in arm_bones and g.weight > 1e-8:
                        weights.append((name,float(g.weight)))
            if not weights:
                continue
            weights.sort(key=lambda x:x[1],reverse=True)
            samples.append((donor.matrix_world @ v.co,weights[:4]))
    if not samples:
        raise RuntimeError("donor rig has no transferable vertex weights")

    kd=KDTree(len(samples))
    for i,(co,_) in enumerate(samples):
        kd.insert(co,i)
    kd.balance()

    bind_results=[]
    for mesh in target_meshes:
        # Remove stale skin state.
        for mod in list(mesh.modifiers):
            if mod.type=="ARMATURE":
                mesh.modifiers.remove(mod)
        mesh.parent=None
        mesh.vertex_groups.clear()

        transferred=0
        fallback_count=0
        group_cache={}
        for v in mesh.data.vertices:
            world=mesh.matrix_world @ v.co
            _,idx,_=kd.find(world)
            weights=samples[idx][1] if idx is not None else []
            total=sum(w for _,w in weights)
            if total <= 1e-8:
                weights=[("Hips",1.0)]
                total=1.0
                fallback_count += 1
            for name,weight in weights:
                group=group_cache.get(name)
                if group is None:
                    group=mesh.vertex_groups.new(name=name)
                    group_cache[name]=group
                group.add([v.index],float(weight/total),"REPLACE")
            transferred += 1

        mesh.parent=arm
        mod=mesh.modifiers.new(name="HAYUYA_Armature",type="ARMATURE")
        mod.object=arm
        mod.use_vertex_groups=True
        bind_results.append({
            "mesh":mesh.name,
            "ok":True,
            "groups":len(mesh.vertex_groups),
            "spatial_weight_vertices":transferred,
            "fallback_weighted_vertices":fallback_count,
            "donor_samples":len(samples)
        })

    # Donor meshes are no longer needed after the spatial weight transfer.
    for obj in list(donor_objs):
        if obj != arm and obj.name in bpy.data.objects:
            bpy.data.objects.remove(obj,do_unlink=True)

    # Make a sensible default preview action if imported animations exist.
    actions=sorted(bpy.data.actions,key=lambda a:a.name.lower())
    idle=next((a for a in actions if "idle" in a.name.lower()), actions[0] if actions else None)
    if idle:
        if arm.animation_data is None:
            arm.animation_data_create()
        arm.animation_data.action=idle

    args.output.unlink(missing_ok=True)
    # Export only the new target skin + donor armature. This deliberately
    # excludes source helper nodes/empties from both imported GLBs.
    select_only(*target_meshes,arm)
    bpy.ops.export_scene.gltf(
        filepath=str(args.output.resolve()),
        export_format="GLB",
        use_selection=True,
        export_animations=True,
        export_skins=True,
        export_def_bones=True,
        export_all_influences=True,
        export_nla_strips=True,
        export_yup=True,
    )

    report={
        "schema":1,
        "target":str(args.target),
        "donor":str(args.donor),
        "output":str(args.output),
        "target_meshes":[m.name for m in target_meshes],
        "target_bounds":{"min":list(target_min),"max":list(target_max),"height":target_height,"axis":target_axis},
        "donor_bounds":{"min":list(donor_min),"max":list(donor_max),"height":donor_height,"axis":donor_axis},
        "scale":scale,
        "armature":arm.name,
        "bones":[b.name for b in arm.data.bones],
        "actions":[a.name for a in actions],
        "bind_results":bind_results,
        "output_bytes":args.output.stat().st_size if args.output.exists() else 0,
    }
    args.report.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("HAYUYA_AUTORIG_PASS")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
