# SPDX-License-Identifier: MIT
# Automated Blender zombie builder for Xziel / ZOMBIESSSSSSS PORTABLE.
# Source humanoid geometry is expected to be MakeHuman core base mesh (CC0).

import argparse
import json
import math
import os
import random
import sys
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector


SEED = 1337
random.seed(SEED)


def argv_after_dashes():
    if "--" not in sys.argv:
        return []
    return sys.argv[sys.argv.index("--") + 1:]


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--base", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--preview", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--lod-dir", required=True)
    return p.parse_args(argv_after_dashes())


def clean_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                       bpy.data.cameras, bpy.data.lights):
        # Do not aggressively remove materials after creation; this is only called at startup.
        if datablocks == bpy.data.materials:
            continue
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)


def import_obj(path):
    before = set(bpy.data.objects)
    if hasattr(bpy.ops.wm, "obj_import"):
        bpy.ops.wm.obj_import(filepath=str(path))
    else:
        bpy.ops.import_scene.obj(filepath=str(path))
    imported = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    if not imported:
        raise RuntimeError(f"No mesh objects imported from {path}")
    bpy.ops.object.select_all(action="DESELECT")
    for o in imported:
        o.select_set(True)
    bpy.context.view_layer.objects.active = imported[0]
    if len(imported) > 1:
        bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = "Zombie_LOD0_Body"
    return obj


def apply_all(obj):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def bounds(obj):
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def normalize_human(obj, target_height=1.78):
    apply_all(obj)
    lo, hi = bounds(obj)
    ext = hi - lo

    # Make the longest body axis Z. MakeHuman usually arrives already sensible,
    # but this keeps the pipeline robust across OBJ export conventions.
    longest = max(range(3), key=lambda i: ext[i])
    if longest == 0:
        obj.rotation_euler[1] = -math.pi / 2
        apply_all(obj)
    elif longest == 1:
        obj.rotation_euler[0] = math.pi / 2
        apply_all(obj)

    lo, hi = bounds(obj)
    h = hi.z - lo.z
    if h <= 1e-6:
        raise RuntimeError("Imported human mesh has invalid height")

    s = target_height / h
    obj.scale = (s, s, s)
    apply_all(obj)

    lo, hi = bounds(obj)
    center_xy = Vector(((lo.x + hi.x) * 0.5, (lo.y + hi.y) * 0.5, 0.0))
    obj.location -= center_xy
    obj.location.z -= lo.z
    apply_all(obj)
    return bounds(obj)


def hash01(i, salt=0):
    n = (i * 1103515245 + 12345 + salt * 2654435761) & 0xFFFFFFFF
    return (n / 0xFFFFFFFF)


def corpse_deform(obj):
    me = obj.data
    lo, hi = bounds(obj)
    h = hi.z - lo.z
    for v in me.vertices:
        co = v.co
        z01 = (co.z - lo.z) / max(h, 1e-6)

        # Whole-body decomposition/asymmetry: small enough to keep animation-friendly topology.
        n = hash01(v.index, 7) - 0.5
        co.x += n * 0.006 * (0.3 + z01)
        co.y += (hash01(v.index, 19) - 0.5) * 0.004

        # Face/head asymmetry: collapsed cheek/jaw feel without destroying topology.
        if z01 > 0.82:
            side = -1.0 if co.x < 0.0 else 1.0
            asym = (z01 - 0.82) / 0.18
            if side > 0:
                co.x *= 0.985 - 0.025 * asym
                co.y += 0.008 * asym
            else:
                co.x *= 1.008
        # Slight hunched shoulder/upper torso silhouette.
        elif 0.60 < z01 < 0.82:
            co.y += 0.006 * math.sin((z01 - 0.60) * math.pi / 0.22)

    me.update()
    for p in me.polygons:
        p.use_smooth = True


def new_principled_material(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat, nodes, links, bsdf


def set_input(node, names, value):
    for name in names:
        if name in node.inputs:
            node.inputs[name].default_value = value
            return True
    return False


def corpse_skin_material():
    mat, nodes, links, bsdf = new_principled_material("M_CorpseSkin")

    noise_macro = nodes.new("ShaderNodeTexNoise")
    noise_macro.inputs["Scale"].default_value = 5.0
    noise_macro.inputs["Detail"].default_value = 7.0
    noise_macro.inputs["Roughness"].default_value = 0.72

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.18
    ramp.color_ramp.elements[0].color = (0.035, 0.048, 0.030, 1.0)
    ramp.color_ramp.elements[1].position = 0.72
    ramp.color_ramp.elements[1].color = (0.25, 0.31, 0.22, 1.0)
    bruise = ramp.color_ramp.elements.new(0.48)
    bruise.color = (0.11, 0.055, 0.075, 1.0)

    noise_pore = nodes.new("ShaderNodeTexNoise")
    noise_pore.inputs["Scale"].default_value = 44.0
    noise_pore.inputs["Detail"].default_value = 5.0
    noise_pore.inputs["Roughness"].default_value = 0.78
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.34
    bump.inputs["Distance"].default_value = 0.018

    links.new(noise_macro.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(noise_pore.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    set_input(bsdf, ["Roughness"], 0.72)
    set_input(bsdf, ["Metallic"], 0.0)
    set_input(bsdf, ["Subsurface Weight", "Subsurface"], 0.035)
    set_input(bsdf, ["IOR"], 1.38)
    set_input(bsdf, ["Specular IOR Level", "Specular"], 0.28)
    return mat


def cloth_material(name, base_rgb):
    mat, nodes, links, bsdf = new_principled_material(name)
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 22.0
    noise.inputs["Detail"].default_value = 3.5
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = tuple(max(0.0, c * 0.35) for c in base_rgb) + (1.0,)
    ramp.color_ramp.elements[1].color = tuple(min(1.0, c * 1.25) for c in base_rgb) + (1.0,)
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    set_input(bsdf, ["Roughness"], 0.9)
    return mat


def blood_material():
    mat, nodes, links, bsdf = new_principled_material("M_DriedBlood")
    set_input(bsdf, ["Base Color"], (0.13, 0.003, 0.006, 1.0))
    set_input(bsdf, ["Roughness"], 0.48)
    set_input(bsdf, ["Specular IOR Level", "Specular"], 0.22)
    return mat


def eye_material():
    mat, nodes, links, bsdf = new_principled_material("M_DeadEye")
    set_input(bsdf, ["Base Color"], (0.52, 0.57, 0.48, 1.0))
    set_input(bsdf, ["Roughness"], 0.24)
    set_input(bsdf, ["IOR"], 1.4)
    set_input(bsdf, ["Transmission Weight", "Transmission"], 0.12)
    return mat


def subset_shell(src_obj, name, zmin, zmax, mat, tear_seed):
    dup = src_obj.copy()
    dup.data = src_obj.data.copy()
    dup.name = name
    bpy.context.collection.objects.link(dup)

    bm = bmesh.new()
    bm.from_mesh(dup.data)
    verts_to_delete = []
    span = max(zmax - zmin, 1e-6)
    for v in bm.verts:
        if v.co.z < zmin or v.co.z > zmax:
            verts_to_delete.append(v)
            continue
        # Ragged hem/cuffs: deterministic holes near boundaries.
        edge_band = min((v.co.z - zmin) / span, (zmax - v.co.z) / span)
        if edge_band < 0.11 and hash01(v.index, tear_seed) > 0.76:
            verts_to_delete.append(v)
    bmesh.ops.delete(bm, geom=verts_to_delete, context="VERTS")
    bm.to_mesh(dup.data)
    bm.free()

    solid = dup.modifiers.new("ClothThickness", "SOLIDIFY")
    solid.thickness = 0.006
    solid.offset = 1.0
    if len(dup.data.materials) == 0:
        dup.data.materials.append(mat)
    else:
        dup.data.materials[0] = mat
    for p in dup.data.polygons:
        p.use_smooth = True
    return dup


def create_clothes(body):
    shirt_mat = cloth_material("M_TornShirt", (0.085, 0.075, 0.060))
    pants_mat = cloth_material("M_TornPants", (0.035, 0.040, 0.044))
    shirt = subset_shell(body, "Zombie_TornShirt", 0.88, 1.43, shirt_mat, 31)
    pants = subset_shell(body, "Zombie_TornPants", 0.18, 0.94, pants_mat, 47)
    return [shirt, pants]


def add_uv_sphere(name, loc, scale, mat, segments=32, rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=rings,
        location=loc
    )
    o = bpy.context.object
    o.name = name
    o.scale = scale
    apply_all(o)
    if mat:
        o.data.materials.append(mat)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def add_face_and_wounds():
    blood = blood_material()
    eye = eye_material()
    objs = []

    # Milky dead eyes. Front is treated as -Y for the normalized MakeHuman base.
    objs.append(add_uv_sphere("Zombie_Eye_L", (-0.035, -0.105, 1.665), (0.017, 0.012, 0.017), eye, 24, 12))
    objs.append(add_uv_sphere("Zombie_Eye_R", (0.035, -0.105, 1.665), (0.017, 0.012, 0.017), eye, 24, 12))

    wound_specs = [
        (-0.16, -0.145, 1.18, 0.065, 0.012, 0.045),
        (0.18, -0.142, 1.32, 0.045, 0.010, 0.085),
        (-0.09, -0.125, 1.57, 0.033, 0.009, 0.052),
        (0.04, -0.130, 1.53, 0.025, 0.008, 0.040),
        (-0.12, -0.110, 0.74, 0.040, 0.009, 0.090),
        (0.10, -0.110, 0.52, 0.032, 0.008, 0.070),
    ]
    for i, (x, y, z, sx, sy, sz) in enumerate(wound_specs):
        w = add_uv_sphere(f"Zombie_Wound_{i:02d}", (x, y, z), (sx, sy, sz), blood, 20, 10)
        w.rotation_euler[1] = (i * 0.37) % math.pi
        objs.append(w)
    return objs


def add_teeth_hint():
    mat, nodes, links, bsdf = new_principled_material("M_Bone")
    set_input(bsdf, ["Base Color"], (0.37, 0.32, 0.22, 1.0))
    set_input(bsdf, ["Roughness"], 0.76)
    bpy.ops.mesh.primitive_cube_add(location=(0.0, -0.119, 1.617), scale=(0.028, 0.006, 0.010))
    o = bpy.context.object
    o.name = "Zombie_ExposedTeethHint"
    o.data.materials.append(mat)
    bevel = o.modifiers.new("TeethBevel", "BEVEL")
    bevel.width = 0.004
    bevel.segments = 3
    return o


def make_ground():
    bpy.ops.mesh.primitive_plane_add(size=12.0, location=(0, 0, 0))
    g = bpy.context.object
    g.name = "Preview_Ground"
    mat, nodes, links, bsdf = new_principled_material("M_PreviewGround")
    set_input(bsdf, ["Base Color"], (0.015, 0.017, 0.018, 1.0))
    set_input(bsdf, ["Roughness"], 0.94)
    g.data.materials.append(mat)
    return g


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def setup_preview_camera_and_lights():
    scene = bpy.context.scene
    scene.render.resolution_x = 720
    scene.render.resolution_y = 960
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"

    # Prefer Eevee Next where available.
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "BLENDER_WORKBENCH"):
        try:
            scene.render.engine = engine
            break
        except Exception:
            pass

    scene.world.color = (0.004, 0.004, 0.006)

    bpy.ops.object.camera_add(location=(2.25, -3.35, 1.42))
    cam = bpy.context.object
    cam.name = "Preview_Camera"
    cam.data.lens = 68
    look_at(cam, (0.0, 0.0, 0.98))
    scene.camera = cam

    def area(name, loc, energy, size, rgb):
        bpy.ops.object.light_add(type="AREA", location=loc)
        l = bpy.context.object
        l.name = name
        l.data.energy = energy
        l.data.shape = "DISK"
        l.data.size = size
        l.data.color = rgb
        look_at(l, (0, 0, 1.0))
        return l

    area("Key", (-2.2, -2.0, 2.9), 780.0, 2.2, (0.72, 0.82, 1.0))
    area("Rim", (2.0, 0.9, 2.2), 1050.0, 1.4, (0.55, 0.08, 0.06))
    area("Fill", (0.2, -0.8, 0.7), 280.0, 1.7, (0.35, 0.45, 0.42))
    return cam


def mesh_stats(obj):
    me = obj.data
    return {
        "vertices": len(me.vertices),
        "polygons": len(me.polygons),
        "triangles_estimate": sum(max(1, len(p.vertices) - 2) for p in me.polygons),
    }


def export_selected(path, objects):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objects:
        if o and o.name in bpy.context.view_layer.objects:
            o.select_set(True)
    if objects:
        bpy.context.view_layer.objects.active = objects[0]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        use_selection=True,
        export_cameras=False,
        export_lights=False,
        export_apply=True,
    )


def create_lod(body, ratio, name):
    lod = body.copy()
    lod.data = body.data.copy()
    lod.name = name
    bpy.context.collection.objects.link(lod)
    dec = lod.modifiers.new(f"Decimate_{ratio}", "DECIMATE")
    dec.ratio = ratio
    bpy.context.view_layer.objects.active = lod
    bpy.ops.object.select_all(action="DESELECT")
    lod.select_set(True)
    bpy.ops.object.modifier_apply(modifier=dec.name)
    return lod


def main():
    args = parse_args()
    base = Path(args.base)
    if not base.is_file() or base.stat().st_size < 1024:
        raise RuntimeError(f"Base mesh missing or too small: {base}")

    clean_scene()
    body = import_obj(base)
    normalize_human(body)
    corpse_deform(body)

    skin = corpse_skin_material()
    body.data.materials.clear()
    body.data.materials.append(skin)

    clothes = create_clothes(body)
    gore = add_face_and_wounds()
    teeth = add_teeth_hint()

    lod_dir = Path(args.lod_dir)
    lod_dir.mkdir(parents=True, exist_ok=True)

    # Export production mesh before adding preview-only geometry.
    production_objs = [body] + clothes + gore + [teeth]
    export_selected(args.out, production_objs)

    lod1 = create_lod(body, 0.52, "Zombie_LOD1_Body")
    lod2 = create_lod(body, 0.22, "Zombie_LOD2_Body")
    export_selected(lod_dir / "zombie_lod1.glb", [lod1])
    export_selected(lod_dir / "zombie_lod2.glb", [lod2])

    ground = make_ground()
    setup_preview_camera_and_lights()
    bpy.context.scene.render.filepath = str(Path(args.preview))
    Path(args.preview).parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)

    manifest = {
        "generator": "Xziel Blender Zombie Pipeline",
        "seed": SEED,
        "source_base": "MakeHuman core base mesh (CC0)",
        "units": "meters",
        "target_height_m": 1.78,
        "outputs": {
            "lod0": str(args.out),
            "lod1": str(lod_dir / "zombie_lod1.glb"),
            "lod2": str(lod_dir / "zombie_lod2.glb"),
            "preview": str(args.preview),
        },
        "body_stats": mesh_stats(body),
        "lod1_stats": mesh_stats(lod1),
        "lod2_stats": mesh_stats(lod2),
        "notes": [
            "Phase 1 visual prototype; rig/animations are intentionally deferred.",
            "Topology-preserving corpse deformation keeps future rigging practical.",
            "Next phase upgrades to MPFB2/Blender >=4.2 for automated humanoid rig generation."
        ],
    }
    Path(args.manifest).parent.mkdir(parents=True, exist_ok=True)
    Path(args.manifest).write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # Save a .blend working copy in the same dist directory.
    blend_path = Path(args.out).with_suffix(".blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
