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


def prepare_normal_bake(materials,image):
    for material in materials:
        active_image_node(material,image,"HAYUYA_NORMAL_BAKE_TARGET")


def configure_normal(materials,image):
    for material in materials:
        nodes=material.node_tree.nodes
        links=material.node_tree.links
        tex=next(
            (
                node for node in nodes
                if node.type=="TEX_IMAGE" and node.image is image
                and node.name=="HAYUYA_NORMAL_BAKE_TARGET"
            ),
            None,
        )
        if tex is None:
            tex=active_image_node(material,image,"HAYUYA_NORMAL_BAKE_TARGET")
        tex.name="HAYUYA_REBAKED_NORMAL"
        tex.label="HAYUYA Rebaked Normal"
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


def configure_ao_emission_bake(materials,image,distance):
    """Temporarily route explicit AO shader output through emission for baking."""
    restore=[]
    for material in materials:
        nodes=material.node_tree.nodes
        links=material.node_tree.links
        tex=active_image_node(material,image,"HAYUYA_REBAKED_OCCLUSION")

        output=next((n for n in nodes if n.type=="OUTPUT_MATERIAL" and n.is_active_output),None)
        if output is None:
            output=next((n for n in nodes if n.type=="OUTPUT_MATERIAL"),None)
        if output is None:
            output=nodes.new("ShaderNodeOutputMaterial")

        old_surface=None
        if output.inputs.get("Surface") and output.inputs["Surface"].is_linked:
            old_surface=output.inputs["Surface"].links[0].from_socket
            links.remove(output.inputs["Surface"].links[0])

        ao=nodes.new("ShaderNodeAmbientOcclusion")
        ao.name="HAYUYA_AO_BAKE"
        ao.inputs["Distance"].default_value=max(1e-6,float(distance))
        try:
            ao.samples=32
        except Exception:
            pass
        try:
            ao.only_local=True
        except Exception:
            pass

        emission=nodes.new("ShaderNodeEmission")
        emission.name="HAYUYA_AO_EMISSION_BAKE"
        links.new(ao.outputs["AO"],emission.inputs["Color"])
        links.new(emission.outputs["Emission"],output.inputs["Surface"])
        restore.append((material,output,old_surface,ao,emission,tex))
    return restore


def restore_after_ao_bake(restore):
    for material,output,old_surface,ao,emission,tex in restore:
        nodes=material.node_tree.nodes
        links=material.node_tree.links
        if output.inputs.get("Surface") and output.inputs["Surface"].is_linked:
            for link in list(output.inputs["Surface"].links):
                links.remove(link)
        if old_surface is not None:
            links.new(old_surface,output.inputs["Surface"])
        # Keep the image node; configure_occlusion will attach it to glTF output.
        # Blender 4 bpy_prop_collection.__contains__ accepts names, not node objects.
        if nodes.get(ao.name) is ao:
            nodes.remove(ao)
        if nodes.get(emission.name) is emission:
            nodes.remove(emission)


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


def image_signal_stats(image,channel_index=0,max_samples=65536):
    """Sample a baked image without materializing a multi-4K pixel list."""
    pixels=image.pixels
    pixel_count=max(0,len(pixels)//4)
    if pixel_count<=0:
        return {"samples":0,"min":None,"max":None,"mean":None,"stddev":None}
    stride=max(1,pixel_count//max_samples)
    count=0
    mean=0.0
    m2=0.0
    mn=float("inf")
    mx=float("-inf")
    for pixel_index in range(0,pixel_count,stride):
        value=float(pixels[pixel_index*4+channel_index])
        count+=1
        delta=value-mean
        mean+=delta/count
        m2+=delta*(value-mean)
        mn=min(mn,value)
        mx=max(mx,value)
    variance=m2/max(1,count-1)
    return {
        "samples":count,
        "min":round(mn,6),
        "max":round(mx,6),
        "mean":round(mean,6),
        "stddev":round(variance**0.5,6),
    }


def image_rgb_signal_stats(image,max_samples=65536):
    channels={
        name:image_signal_stats(image,index,max_samples)
        for index,name in enumerate(("r","g","b"))
    }
    stddevs=[
        float(stats["stddev"])
        for stats in channels.values()
        if stats.get("stddev") is not None
    ]
    return {
        "channels":channels,
        "combined_stddev":round(sum(stddevs)/len(stddevs),6) if stddevs else None,
        "combined_range":round(
            sum(
                max(0.0,float(stats["max"])-float(stats["min"]))
                for stats in channels.values()
                if stats.get("max") is not None and stats.get("min") is not None
            )/max(1,len(channels)),
            6,
        ),
    }


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
    if scene.world is None:
        scene.world=bpy.data.worlds.new("HAYUYA_RebakeWorld")
    light_settings=getattr(scene.world,"light_settings",None)
    if light_settings is not None:
        if hasattr(light_settings,"use_ambient_occlusion"):
            light_settings.use_ambient_occlusion=True
        if hasattr(light_settings,"ao_factor"):
            light_settings.ao_factor=1.0
        if hasattr(light_settings,"distance"):
            light_settings.distance=max(1e-6,diag*0.35)
    scene.render.bake.margin=max(4,min(32,a.size//128))
    scene.render.bake.cage_extrusion=diag*0.003
    scene.render.bake.max_ray_distance=diag*0.04

    resolved=[]
    images={}

    if "normal" in channels:
        normal_image=new_noncolor_image(
            "HAYUYA_Rebaked_Normal",a.size,(0.5,0.5,1.0,1.0)
        )
        prepare_normal_bake(materials,normal_image)
        scene.render.bake.use_selected_to_active=True
        scene.render.bake.normal_space="TANGENT"
        select_only([*source_meshes,target],target)
        bpy.ops.object.bake(type="NORMAL")
        configure_normal(materials,normal_image)
        normal_stats=image_rgb_signal_stats(normal_image)
        normal_image.pack()
        images["normal"]={"name":normal_image.name,"signal":normal_stats}
        print("HAYUYA_REBAKE_SIGNAL normal "+json.dumps(normal_stats,sort_keys=True))
        resolved.append("normal")

    if "occlusion" in channels:
        # AO is topology-dependent runtime shading. The high-poly/source meshes
        # are only normal-bake evidence and must not contaminate target AO.
        for source_obj in source_meshes:
            source_obj.hide_render=True
        scene.render.bake.use_selected_to_active=False
        if hasattr(scene.render.bake,"target"):
            scene.render.bake.target="IMAGE_TEXTURES"

        ao_attempts=[]
        ao_image=None
        ao_method=None

        # Attempt 1: native Cycles AO bake with explicit World AO settings.
        native_image=new_noncolor_image(
            "HAYUYA_Rebaked_Occlusion_cycles_native_ao_target_only_v6",
            a.size,
            (1.0,1.0,1.0,1.0),
        )
        for material in materials:
            active_image_node(
                material,
                native_image,
                "HAYUYA_AO_BAKE_TARGET_cycles_native_ao_target_only_v6",
            )
        select_only([target],target)
        bpy.ops.object.bake(type="AO")
        native_stats=image_signal_stats(native_image,0)
        native_range=(
            float(native_stats["max"])-float(native_stats["min"])
            if native_stats.get("max") is not None
            and native_stats.get("min") is not None
            else 0.0
        )
        native_attempt={
            "method":"cycles_native_ao_target_only_v6",
            "signal":native_stats,
            "signal_range":round(native_range,6),
            "signal_valid":native_range>1e-4,
        }
        ao_attempts.append(native_attempt)
        print(
            "HAYUYA_REBAKE_SIGNAL occlusion_attempt "
            + json.dumps(native_attempt,sort_keys=True)
        )
        if native_attempt["signal_valid"]:
            ao_image=native_image
            ao_method=native_attempt["method"]

        # Attempt 2: explicit AO shader -> emission, target-local only.
        if ao_image is None:
            shader_image=new_noncolor_image(
                "HAYUYA_Rebaked_Occlusion_shader_emit_v6",
                a.size,
                (1.0,1.0,1.0,1.0),
            )
            ao_restore=configure_ao_emission_bake(
                materials,
                shader_image,
                distance=max(1e-6,diag*0.35),
            )
            select_only([target],target)
            bpy.ops.object.bake(type="EMIT")
            restore_after_ao_bake(ao_restore)
            shader_stats=image_signal_stats(shader_image,0)
            shader_range=(
                float(shader_stats["max"])-float(shader_stats["min"])
                if shader_stats.get("max") is not None
                and shader_stats.get("min") is not None
                else 0.0
            )
            shader_attempt={
                "method":"ao_shader_emit_target_local_v6",
                "signal":shader_stats,
                "signal_range":round(shader_range,6),
                "signal_valid":shader_range>1e-4,
                "distance":max(1e-6,diag*0.35),
            }
            ao_attempts.append(shader_attempt)
            print(
                "HAYUYA_REBAKE_SIGNAL occlusion_attempt "
                + json.dumps(shader_attempt,sort_keys=True)
            )
            if shader_attempt["signal_valid"]:
                ao_image=shader_image
                ao_method=shader_attempt["method"]

        ao_signal_valid=ao_image is not None
        images["occlusion"]={
            "signal_valid":ao_signal_valid,
            "method":ao_method,
            "attempts":ao_attempts,
        }
        if ao_signal_valid:
            configure_occlusion(materials,ao_image)
            ao_image.pack()
            images["occlusion"]["name"]=ao_image.name
            resolved.append("occlusion")
        print(
            "HAYUYA_REBAKE_SIGNAL occlusion "
            + json.dumps(images["occlusion"],sort_keys=True)
        )

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
