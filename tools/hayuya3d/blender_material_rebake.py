#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


SUPPORTED_CHANNELS={"normal","occlusion"}


def parse_args():
    argv=sys.argv
    argv=argv[argv.index("--")+1:] if "--" in argv else []
    p=argparse.ArgumentParser(description="HAYUYA topology-dependent material rebake.")
    p.add_argument("--source",required=True,type=Path)
    p.add_argument("--target",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--report",required=True,type=Path)
    p.add_argument("--channel",action="append",default=[])
    p.add_argument("--size",type=int,default=2048)
    return p.parse_args(argv)


def import_glb(path:Path):
    before=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path.resolve()))
    return [o for o in bpy.data.objects if o not in before]


def world_bounds(objects):
    pts=[]
    for obj in objects:
        if obj.type!="MESH":
            continue
        pts.extend(obj.matrix_world @ Vector(c) for c in obj.bound_box)
    if not pts:
        raise RuntimeError("no_mesh_bounds")
    mn=Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts)))
    mx=Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts)))
    return mn,mx


def select_only(objects,active=None):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active=active or (objects[-1] if objects else None)


def join_target(meshes):
    if not meshes:
        raise RuntimeError("target_has_no_mesh")
    if len(meshes)==1:
        return meshes[0]
    select_only(meshes,meshes[0])
    bpy.ops.object.join()
    return bpy.context.object


def target_materials(target):
    if not target.data.uv_layers:
        raise RuntimeError("target_has_no_uv")
    target.data.uv_layers.active_index=0

    if not target.material_slots:
        material=bpy.data.materials.new("HAYUYA_RebakeMaterial")
        material.use_nodes=True
        target.data.materials.append(material)

    materials=[]
    seen=set()
    for slot in target.material_slots:
        material=slot.material
        if material is None:
            material=bpy.data.materials.new("HAYUYA_RebakeMaterial")
            material.use_nodes=True
            slot.material=material
        material.use_nodes=True
        if material.as_pointer() not in seen:
            seen.add(material.as_pointer())
            materials.append(material)
    return materials


def active_image_node(material,image,name):
    nodes=material.node_tree.nodes
    for node in nodes:
        node.select=False
    tex=nodes.new("ShaderNodeTexImage")
    tex.name=name
    tex.label=name.replace("_"," ")
    tex.image=image
    tex.interpolation="Linear"
    tex.select=True
    nodes.active=tex
    return tex


def principled(material):
    nodes=material.node_tree.nodes
    node=next((n for n in nodes if n.type=="BSDF_PRINCIPLED"),None)
    if node is None:
        node=nodes.new("ShaderNodeBsdfPrincipled")
    return node


def configure_normal(materials,image):
    for material in materials:
        nodes=material.node_tree.nodes
        links=material.node_tree.links
        tex=active_image_node(material,image,"HAYUYA_REBAKED_NORMAL")
        normal=nodes.new("ShaderNodeNormalMap")
        normal.name="HAYUYA_REBAKED_NORMAL_MAP"
        normal.space="TANGENT"
        links.new(tex.outputs["Color"],normal.inputs["Color"])
        links.new(normal.outputs["Normal"],principled(material).inputs["Normal"])


def gltf_output_group():
    name="glTF Material Output"
    group=bpy.data.node_groups.get(name)
    if group is None:
        group=bpy.data.node_groups.new(name,"ShaderNodeTree")
        if hasattr(group,"interface"):
            group.interface.new_socket(
                name="Occlusion",
                in_out="INPUT",
                socket_type="NodeSocketFloat",
            )
        else:
            group.inputs.new("NodeSocketFloat","Occlusion")
    return group


def configure_occlusion(materials,image):
    group=gltf_output_group()
    for material in materials:
        nodes=material.node_tree.nodes
        links=material.node_tree.links
        tex=active_image_node(material,image,"HAYUYA_REBAKED_OCCLUSION")
        output=next(
            (
                n for n in nodes
                if n.type=="GROUP" and n.node_tree is not None
                and n.node_tree.name=="glTF Material Output"
            ),
            None,
        )
        if output is None:
            output=nodes.new("ShaderNodeGroup")
            output.name="HAYUYA_GLTF_MATERIAL_OUTPUT"
            output.node_tree=group
        socket=output.inputs.get("Occlusion")
        if socket is None:
            raise RuntimeError("gltf_occlusion_socket_missing")
        links.new(tex.outputs["Color"],socket)


def new_noncolor_image(name,size,fill):
    image=bpy.data.images.new(
        name,
        width=size,
        height=size,
        alpha=False,
        float_buffer=False,
    )
    image.generated_color=fill
    try:
        image.colorspace_settings.name="Non-Color"
    except Exception:
        pass
    return image


def main():
    a=parse_args()
    channels=sorted(set(a.channel or ["normal"]))
    unknown=sorted(set(channels)-SUPPORTED_CHANNELS)
    if unknown:
        raise RuntimeError("unsupported_channels:"+",".join(unknown))
    if a.size<64 or a.size>8192:
        raise RuntimeError(f"invalid_bake_size:{a.size}")

    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.report.parent.mkdir(parents=True,exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)

    source_objects=import_glb(a.source)
    source_meshes=[o for o in source_objects if o.type=="MESH"]
    if not source_meshes:
        raise RuntimeError("source_has_no_mesh")

    target_objects=import_glb(a.target)
    target_meshes=[o for o in target_objects if o.type=="MESH"]
    target=join_target(target_meshes)
    materials=target_materials(target)

    mn,mx=world_bounds([*source_meshes,target])
    diag=max((mx-mn).length,1e-6)

    scene=bpy.context.scene
    scene.render.engine="CYCLES"
    scene.cycles.device="CPU"
    scene.render.bake.use_clear=True
    scene.render.bake.margin=max(4,min(32,a.size//128))
    scene.render.bake.cage_extrusion=diag*0.003
    scene.render.bake.max_ray_distance=diag*0.04

    resolved=[]
    images={}

    if "normal" in channels:
        normal_image=new_noncolor_image(
            "HAYUYA_Rebaked_Normal",a.size,(0.5,0.5,1.0,1.0)
        )
        configure_normal(materials,normal_image)
        scene.render.bake.use_selected_to_active=True
        scene.render.bake.normal_space="TANGENT"
        select_only([*source_meshes,target],target)
        bpy.ops.object.bake(type="NORMAL")
        normal_image.pack()
        images["normal"]=normal_image.name
        resolved.append("normal")

    if "occlusion" in channels:
        ao_image=new_noncolor_image(
            "HAYUYA_Rebaked_Occlusion",a.size,(1.0,1.0,1.0,1.0)
        )
        configure_occlusion(materials,ao_image)
        scene.render.bake.use_selected_to_active=False
        select_only([target],target)
        bpy.ops.object.bake(type="AO")
        ao_image.pack()
        images["occlusion"]=ao_image.name
        resolved.append("occlusion")

    select_only([target],target)
    bpy.ops.export_scene.gltf(
        filepath=str(a.output.resolve()),
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_materials="EXPORT",
        export_image_format="AUTO",
    )
    if not a.output.is_file() or a.output.read_bytes()[:4]!=b"glTF":
        raise RuntimeError("material_rebake_export_invalid")

    report={
        "schema":2,
        "source":str(a.source),
        "target":str(a.target),
        "output":str(a.output),
        "size":a.size,
        "requested_channels":channels,
        "resolved_channels":resolved,
        "images":images,
        "material_count":len(materials),
        "method":"blender_cycles_topology_material_rebake_v2",
        "cage_extrusion":diag*0.003,
        "max_ray_distance":diag*0.04,
    }
    a.report.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("HAYUYA_MATERIAL_REBAKE_READY",a.output,a.size,",".join(resolved))


if __name__=="__main__":
    main()
