#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args():
    argv=sys.argv
    if "--" in argv:
        argv=argv[argv.index("--")+1:]
    else:
        argv=[]
    p=argparse.ArgumentParser(description="Sample HAYUYA character animations and reject catastrophic deformation.")
    p.add_argument("--model",required=True,type=Path)
    p.add_argument("--json",required=True,type=Path)
    p.add_argument("--samples",type=int,default=5)
    p.add_argument("--max-diagonal-ratio",type=float,default=3.5)
    p.add_argument("--min-diagonal-ratio",type=float,default=0.25)
    return p.parse_args(argv)


def evaluated_bounds(meshes):
    deps=bpy.context.evaluated_depsgraph_get()
    pts=[]
    for obj in meshes:
        ev=obj.evaluated_get(deps)
        mesh=ev.to_mesh()
        try:
            mat=ev.matrix_world
            for v in mesh.vertices:
                co=mat @ v.co
                if not all(math.isfinite(x) for x in co):
                    raise RuntimeError(f"non_finite_vertex:{obj.name}")
                pts.append(co.copy())
        finally:
            ev.to_mesh_clear()
    if not pts:
        raise RuntimeError("no_evaluated_vertices")
    mn=Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts)))
    mx=Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts)))
    ext=mx-mn
    diag=ext.length
    center=(mn+mx)*0.5
    return {
        "min":[float(x) for x in mn],
        "max":[float(x) for x in mx],
        "extents":[float(x) for x in ext],
        "diagonal":float(diag),
        "center":[float(x) for x in center],
        "vertex_samples":len(pts)
    }


def main():
    args=parse_args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(args.model.resolve()))
    meshes=[o for o in bpy.context.scene.objects if o.type=="MESH"]
    arms=[o for o in bpy.context.scene.objects if o.type=="ARMATURE"]
    if not meshes:
        raise RuntimeError("model_has_no_mesh")
    if not arms:
        raise RuntimeError("model_has_no_armature")
    arm=arms[0]

    if arm.animation_data is None:
        arm.animation_data_create()
    arm.animation_data.action=None
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()
    rest=evaluated_bounds(meshes)
    if rest["diagonal"]<=1e-8:
        raise RuntimeError("rest_bounds_degenerate")

    actions=sorted(bpy.data.actions,key=lambda a:a.name.lower())
    failures=[]
    warnings=[]
    clips=[]
    sample_count=max(3,args.samples)

    for action in actions:
        arm.animation_data.action=action
        start,end=action.frame_range
        if not math.isfinite(start) or not math.isfinite(end):
            failures.append(f"{action.name}:invalid_frame_range")
            continue
        if end < start:
            start,end=end,start
        frames=[]
        if abs(end-start)<1e-6:
            frames=[start]
        else:
            for i in range(sample_count):
                t=i/(sample_count-1)
                frames.append(start+(end-start)*t)

        clip={"name":action.name,"frame_range":[float(start),float(end)],"samples":[],"passed":True,"reasons":[]}
        for fr in frames:
            bpy.context.scene.frame_set(int(round(fr)))
            bpy.context.view_layer.update()
            b=evaluated_bounds(meshes)
            ratio=b["diagonal"]/rest["diagonal"]
            rec={"frame":float(fr),"diagonal_ratio":float(ratio),"bounds":b}
            clip["samples"].append(rec)
            if ratio > args.max_diagonal_ratio:
                reason=f"exploded_bounds:frame={fr:.2f},ratio={ratio:.3f}"
                clip["reasons"].append(reason)
            if ratio < args.min_diagonal_ratio:
                reason=f"collapsed_bounds:frame={fr:.2f},ratio={ratio:.3f}"
                clip["reasons"].append(reason)

        clip["reasons"]=sorted(set(clip["reasons"]))
        clip["passed"]=not clip["reasons"]
        if not clip["passed"]:
            failures.extend(f"{action.name}:{r}" for r in clip["reasons"])
        clips.append(clip)

    if not actions:
        failures.append("no_animation_actions")

    passed=not failures
    report={
        "schema":1,
        "model":str(args.model),
        "passed":passed,
        "armature":arm.name,
        "mesh_count":len(meshes),
        "action_count":len(actions),
        "rest_bounds":rest,
        "thresholds":{
            "min_diagonal_ratio":args.min_diagonal_ratio,
            "max_diagonal_ratio":args.max_diagonal_ratio,
            "samples_per_action":sample_count
        },
        "clips":clips,
        "failures":failures,
        "warnings":warnings
    }
    args.json.parent.mkdir(parents=True,exist_ok=True)
    args.json.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("HAYUYA_ANIMATION_GATE",json.dumps({
        "passed":passed,
        "actions":len(actions),
        "failures":len(failures)
    },separators=(",",":")))
    print(json.dumps(report,indent=2))
    return 0 if passed else 2


if __name__=="__main__":
    raise SystemExit(main())
