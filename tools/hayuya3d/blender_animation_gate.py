#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
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
    p=argparse.ArgumentParser(description="Sample HAYUYA animations and reject visible mesh deformation failures.")
    p.add_argument("--model",required=True,type=Path)
    p.add_argument("--json",required=True,type=Path)
    p.add_argument("--samples",type=int,default=5)
    p.add_argument("--max-diagonal-ratio",type=float,default=2.25)
    p.add_argument("--min-diagonal-ratio",type=float,default=0.40)
    p.add_argument("--max-edge-ratio",type=float,default=2.50)
    p.add_argument("--min-edge-ratio",type=float,default=0.35)
    p.add_argument("--max-head-edge-ratio",type=float,default=1.80)
    p.add_argument("--min-head-edge-ratio",type=float,default=0.55)
    p.add_argument("--max-edges",type=int,default=6000)
    p.add_argument("--reference",type=Path)
    p.add_argument("--reference-min-diagonal-ratio",type=float,default=0.72)
    p.add_argument("--reference-max-diagonal-ratio",type=float,default=1.38)
    p.add_argument("--reference-max-center-offset",type=float,default=0.25)
    return p.parse_args(argv)


def percentile(values, q):
    if not values:
        return None
    vals=sorted(values)
    pos=(len(vals)-1)*q
    lo=int(math.floor(pos)); hi=int(math.ceil(pos))
    if lo==hi:
        return float(vals[lo])
    t=pos-lo
    return float(vals[lo]*(1-t)+vals[hi]*t)


def evaluated_positions(meshes):
    deps=bpy.context.evaluated_depsgraph_get()
    out={}
    pts=[]
    for obj in meshes:
        ev=obj.evaluated_get(deps)
        mesh=ev.to_mesh()
        try:
            mat=ev.matrix_world
            arr=[]
            for v in mesh.vertices:
                co=mat @ v.co
                if not all(math.isfinite(x) for x in co):
                    raise RuntimeError(f"non_finite_vertex:{obj.name}")
                arr.append(co.copy())
                pts.append(co.copy())
            out[obj.name]=arr
        finally:
            ev.to_mesh_clear()
    if not pts:
        raise RuntimeError("no_evaluated_vertices")
    mn=Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts)))
    mx=Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts)))
    ext=mx-mn
    triangle_count=0
    polygon_count=0
    for obj in meshes:
        polygon_count += len(obj.data.polygons)
        for poly in obj.data.polygons:
            triangle_count += max(1, len(poly.vertices)-2)
    return out,{
        "min":[float(x) for x in mn],
        "max":[float(x) for x in mx],
        "extents":[float(x) for x in ext],
        "diagonal":float(ext.length),
        "center":[float(x) for x in (mn+mx)*0.5],
        "vertex_samples":len(pts),
        "polygon_count":int(polygon_count),
        "triangle_count":int(triangle_count)
    }


def build_edge_samples(meshes, rest_positions, rest_bounds, max_edges):
    ext=rest_bounds["extents"]
    up_axis=max(range(3),key=lambda i:abs(ext[i]))
    body_min=rest_bounds["min"][up_axis]
    body_span=max(1e-8,ext[up_axis])
    candidates=[]
    for obj in meshes:
        pos=rest_positions.get(obj.name,[])
        for e in obj.data.edges:
            a,b=e.vertices
            if a>=len(pos) or b>=len(pos):
                continue
            length=(pos[a]-pos[b]).length
            if length<=1e-8 or not math.isfinite(length):
                continue
            mid=(pos[a][up_axis]+pos[b][up_axis])*0.5
            head=((mid-body_min)/body_span)>=0.78
            candidates.append((obj.name,int(a),int(b),float(length),bool(head)))
    if len(candidates)>max_edges:
        step=len(candidates)/float(max_edges)
        sampled=[]
        idx=0.0
        while len(sampled)<max_edges and int(idx)<len(candidates):
            sampled.append(candidates[int(idx)])
            idx+=step
        candidates=sampled
    return candidates,up_axis


def canonical_action_name(name):
    value=str(name or "").strip()
    # Blender/glTF can duplicate imported action names with .001 and append
    # the exported armature name, sometimes both at once:
    # Zombie_Walk_Fwd_Loop.001_HAYUYA_Armature.001
    # Collapse those exporter artifacts back to the stable library clip ID.
    for _ in range(4):
        before=value
        value=re.sub(r"\.\d{3}$","",value)
        value=re.sub(r"(?:_HAYUYA_Armature|\|HAYUYA_Armature|\.HAYUYA_Armature)$","",value)
        if value==before:
            break
    return value

def edge_metrics(edge_samples, positions):
    body=[]
    head=[]
    missing=0
    for name,a,b,rest_len,is_head in edge_samples:
        arr=positions.get(name)
        if not arr or a>=len(arr) or b>=len(arr):
            missing+=1
            continue
        cur=(arr[a]-arr[b]).length
        if rest_len<=1e-8 or not math.isfinite(cur):
            continue
        ratio=float(cur/rest_len)
        body.append(ratio)
        if is_head:
            head.append(ratio)
    return {
        "sample_count":len(body),
        "missing_edges":missing,
        "p01":percentile(body,0.01),
        "p50":percentile(body,0.50),
        "p99":percentile(body,0.99),
        "head_sample_count":len(head),
        "head_p01":percentile(head,0.01),
        "head_p99":percentile(head,0.99),
    }


def main():
    args=parse_args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(args.model.resolve()))
    all_model_meshes=[o for o in bpy.context.scene.objects if o.type=="MESH"]
    arms=[o for o in bpy.context.scene.objects if o.type=="ARMATURE"]
    if not all_model_meshes:
        raise RuntimeError("model_has_no_mesh")
    if not arms:
        raise RuntimeError("model_has_no_armature")
    arm=arms[0]
    arm_bones={b.name for b in arm.data.bones}

    def mesh_belongs_to_character(obj):
        # Deformation QA must measure ONLY the skinned render surface. Rigify
        # controllers/custom-shape meshes can be parented to the armature and
        # can even survive glTF dependency export, but they have no deform
        # groups. Requiring at least one vertex group that matches a real bone
        # cleanly excludes those helpers without relying on fragile names.
        deform_groups=[g.name for g in obj.vertex_groups if g.name in arm_bones]
        if not deform_groups:
            return False
        for mod in obj.modifiers:
            if mod.type=="ARMATURE" and (getattr(mod,"object",None) in (None,arm)):
                return True
        if obj.parent==arm or getattr(obj,"parent_type","")=="BONE":
            return True
        # Some importers reconstruct skinning without the original parenting
        # shape. Matching bone groups are still authoritative evidence that the
        # mesh belongs to the character.
        return True

    meshes=[o for o in all_model_meshes if mesh_belongs_to_character(o)]
    ignored_meshes=[o for o in all_model_meshes if o not in meshes]
    if not meshes:
        raise RuntimeError(
            "model_has_no_deformable_mesh:"
            + ",".join(sorted(o.name for o in all_model_meshes))
        )

    if arm.animation_data is None:
        arm.animation_data_create()

    # glTF import stashes clips on NLA tracks so they can be re-exported.
    # When QA assigns one action directly while those tracks remain active,
    # Blender blends the selected action WITH the imported NLA stack. That
    # produces fake multi-animation stretching and even corrupts the "rest"
    # measurement. Mute every imported NLA track and test exactly one action.
    nla_tracks=[]
    for track in arm.animation_data.nla_tracks:
        nla_tracks.append({
            "name":track.name,
            "mute_before":bool(track.mute),
            "strips":[s.name for s in track.strips],
        })
        track.mute=True

    arm.animation_data.action=None
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()
    rest_positions,rest=evaluated_positions(meshes)
    if rest["diagonal"]<=1e-8:
        raise RuntimeError("rest_bounds_degenerate")
    edge_samples,up_axis=build_edge_samples(meshes,rest_positions,rest,max(500,args.max_edges))
    if len(edge_samples)<100:
        raise RuntimeError(f"too_few_edge_samples:{len(edge_samples)}")

    reference_fidelity=None
    reference_failures=[]
    if args.reference:
        before=set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(args.reference.resolve()))
        ref_objs=[o for o in bpy.data.objects if o not in before]
        ref_meshes=[o for o in ref_objs if o.type=="MESH"]
        if not ref_meshes:
            raise RuntimeError("reference_model_has_no_mesh")
        ref_positions,ref_bounds=evaluated_positions(ref_meshes)
        ref_diag=max(1e-8,float(ref_bounds["diagonal"]))
        diag_ratio=float(rest["diagonal"])/ref_diag
        rc=Vector(ref_bounds["center"])
        ac=Vector(rest["center"])
        center_offset=float((ac-rc).length/ref_diag)
        vertex_ratio=float(rest["vertex_samples"])/max(1,int(ref_bounds["vertex_samples"]))
        triangle_ratio=float(rest.get("triangle_count",0))/max(1,int(ref_bounds.get("triangle_count",0)))
        if diag_ratio<args.reference_min_diagonal_ratio or diag_ratio>args.reference_max_diagonal_ratio:
            reference_failures.append(f"rest_vs_reference_diagonal:{diag_ratio:.4f}")
        if center_offset>args.reference_max_center_offset:
            reference_failures.append(f"rest_vs_reference_center:{center_offset:.4f}")
        # Skinned glTF export can legitimately split one source vertex into
        # several vertices because joints/weights/normals/UV seams differ.
        # Triangle count tracks actual surface growth and is the correct
        # topology invariant here.
        if triangle_ratio>1.35 or triangle_ratio<0.70:
            reference_failures.append(f"unexpected_export_triangle_growth:{triangle_ratio:.3f}")
        reference_fidelity={
            "reference":str(args.reference),
            "bounds":ref_bounds,
            "diagonal_ratio":diag_ratio,
            "center_offset_normalized":center_offset,
            "vertex_ratio_telemetry_only":vertex_ratio,
            "triangle_ratio":triangle_ratio,
            "passed":not reference_failures,
            "failures":reference_failures,
        }
        for obj in ref_objs:
            if obj.name in bpy.data.objects:
                bpy.data.objects.remove(obj,do_unlink=True)
        bpy.context.view_layer.update()

    # glTF reimport can materialize the same animation twice (for example
    # Foo_HAYUYA_Armature and Foo.001_HAYUYA_Armature.001).  QA is defined per
    # canonical gameplay clip, not per Blender datablock copy.  De-duplicate
    # before sampling so counts are truthful and expensive deformation checks
    # are not run twice.  Prefer the non-.001 datablock when both exist.
    raw_actions=sorted(bpy.data.actions,key=lambda a:a.name.lower())
    actions_by_name={}
    duplicate_actions_ignored=[]
    for action in raw_actions:
        key=canonical_action_name(action.name)
        current=actions_by_name.get(key)
        if current is None:
            actions_by_name[key]=action
            continue
        current_copy=".001" in current.name
        candidate_copy=".001" in action.name
        if current_copy and not candidate_copy:
            duplicate_actions_ignored.append(current.name)
            actions_by_name[key]=action
        else:
            duplicate_actions_ignored.append(action.name)
    actions=[actions_by_name[k] for k in sorted(actions_by_name,key=str.lower)]

    failures=list(reference_failures)
    warnings=[]
    clips=[]
    compatible=[]
    sample_count=max(3,args.samples)

    for action in actions:
        arm.animation_data.action=action
        action_name=canonical_action_name(action.name)
        start,end=action.frame_range
        if not math.isfinite(start) or not math.isfinite(end):
            failures.append(f"{action_name}:invalid_frame_range")
            continue
        if end < start:
            start,end=end,start
        if abs(end-start)<1e-6:
            frames=[start]
        else:
            frames=[start+(end-start)*(i/(sample_count-1)) for i in range(sample_count)]

        clip={"name":action_name,"raw_name":action.name,"frame_range":[float(start),float(end)],"samples":[],"passed":True,"reasons":[]}
        for fr in frames:
            bpy.context.scene.frame_set(int(round(fr)))
            bpy.context.view_layer.update()
            positions,b=evaluated_positions(meshes)
            ratio=b["diagonal"]/rest["diagonal"]
            em=edge_metrics(edge_samples,positions)
            rec={"frame":float(fr),"diagonal_ratio":float(ratio),"bounds":b,"edge_deformation":em}
            clip["samples"].append(rec)

            if ratio > args.max_diagonal_ratio:
                clip["reasons"].append(f"exploded_bounds:frame={fr:.2f},ratio={ratio:.3f}")
            if ratio < args.min_diagonal_ratio:
                clip["reasons"].append(f"collapsed_bounds:frame={fr:.2f},ratio={ratio:.3f}")

            p99=em.get("p99")
            p01=em.get("p01")
            hp99=em.get("head_p99")
            hp01=em.get("head_p01")
            if p99 is not None and p99>args.max_edge_ratio:
                clip["reasons"].append(f"local_edge_stretch:frame={fr:.2f},p99={p99:.3f}")
            if p01 is not None and p01<args.min_edge_ratio:
                clip["reasons"].append(f"local_edge_collapse:frame={fr:.2f},p01={p01:.3f}")
            if hp99 is not None and hp99>args.max_head_edge_ratio:
                clip["reasons"].append(f"head_face_stretch:frame={fr:.2f},p99={hp99:.3f}")
            if hp01 is not None and hp01<args.min_head_edge_ratio:
                clip["reasons"].append(f"head_face_collapse:frame={fr:.2f},p01={hp01:.3f}")

            rest_ext=rest["extents"]
            cur_ext=b["extents"]
            axis_ratios=[]
            for rv,cv in zip(rest_ext,cur_ext):
                axis_ratios.append(float(cv/rv) if rv>1e-8 else 1.0)
            if any(x>2.5 or x<0.25 for x in axis_ratios):
                clip["reasons"].append(
                    "axis_extent_failure:frame="+f"{fr:.2f},ratios="+",".join(f"{x:.3f}" for x in axis_ratios)
                )

        clip["reasons"]=sorted(set(clip["reasons"]))
        clip["passed"]=not clip["reasons"]
        if clip["passed"]:
            if action_name not in compatible:
                compatible.append(action_name)
        else:
            failures.extend(f"{action_name}:{r}" for r in clip["reasons"])
        clips.append(clip)

    if not actions:
        failures.append("no_animation_actions")

    passed=not failures
    report={
        "schema":2,
        "model":str(args.model),
        "passed":passed,
        "armature":arm.name,
        "nla_tracks_muted":nla_tracks,
        "mesh_count":len(meshes),
        "mesh_objects":[{"name":o.name,"vertices":len(o.data.vertices),"edges":len(o.data.edges),"polygons":len(o.data.polygons)} for o in meshes],
        "ignored_non_deforming_meshes":[{"name":o.name,"vertices":len(o.data.vertices),"polygons":len(o.data.polygons)} for o in ignored_meshes],
        "action_count":len(actions),
        "raw_action_count":len(raw_actions),
        "duplicate_action_count":len(duplicate_actions_ignored),
        "duplicate_actions_ignored":duplicate_actions_ignored,
        "compatible_clips":compatible,
        "rejected_clip_count":len(actions)-len(compatible),
        "rest_bounds":rest,
        "reference_fidelity":reference_fidelity,
        "up_axis":up_axis,
        "edge_sample_count":len(edge_samples),
        "thresholds":{
            "min_diagonal_ratio":args.min_diagonal_ratio,
            "max_diagonal_ratio":args.max_diagonal_ratio,
            "min_edge_ratio":args.min_edge_ratio,
            "max_edge_ratio":args.max_edge_ratio,
            "min_head_edge_ratio":args.min_head_edge_ratio,
            "max_head_edge_ratio":args.max_head_edge_ratio,
            "reference_min_diagonal_ratio":args.reference_min_diagonal_ratio,
            "reference_max_diagonal_ratio":args.reference_max_diagonal_ratio,
            "reference_max_center_offset":args.reference_max_center_offset,
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
        "compatible":len(compatible),
        "failures":len(failures)
    },separators=(",",":")))
    print(json.dumps(report,indent=2))
    return 0 if passed else 2


if __name__=="__main__":
    raise SystemExit(main())
