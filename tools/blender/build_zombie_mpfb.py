# SPDX-License-Identifier: MIT
# Xziel / ZOMBIESSSSSSS PORTABLE
# MPFB-based autonomous zombie asset builder for Blender 4.2+.

import argparse
import importlib
import json
import math
import os
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

SEED = 7331
random.seed(SEED)


def args_after_dashes():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--assets-root", required=True)
    p.add_argument("--out-dir", required=True)
    return p.parse_args(args_after_dashes())


def dynamic_import(suffix, key):
    # Enabled Blender extensions live under bl_ext.<repo>.<id>.
    for name in list(sys.modules):
        if name.endswith(suffix):
            mod = importlib.import_module(name)
            if hasattr(mod, key):
                return getattr(mod, key)
    # Force-load the MPFB extension if Blender did not auto-load preferences.
    try:
        importlib.import_module("bl_ext.user_default.mpfb")
    except Exception as exc:
        print("MPFB force import:", repr(exc))
    for name in list(sys.modules):
        if name.endswith(suffix):
            mod = importlib.import_module(name)
            if hasattr(mod, key):
                return getattr(mod, key)
    raise RuntimeError(f"Could not resolve MPFB symbol {suffix}.{key}")


def clean_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def find_asset(root, basename):
    root = Path(root)
    hits = list(root.rglob(basename))
    if not hits:
        return None
    # Prefer exact system asset directory structures over thumbnails/meta copies.
    hits.sort(key=lambda p: (len(p.parts), len(str(p))))
    return str(hits[0])


def first_principled(mat):
    if not mat or not mat.use_nodes:
        return None
    for n in mat.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED":
            return n
    return None


def set_principled_input(bsdf, names, value):
    for name in names:
        if name in bsdf.inputs:
            bsdf.inputs[name].default_value = value
            return True
    return False


def corpse_overlay(mat):
    if not mat:
        return
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = first_principled(mat)
    if not bsdf:
        return

    base = bsdf.inputs.get("Base Color")
    if base:
        old_link = base.links[0] if base.is_linked and base.links else None
        old_socket = old_link.from_socket if old_link else None
        if old_link:
            links.remove(old_link)

        noise = nodes.new("ShaderNodeTexNoise")
        noise.name = "Zombie_MacroDecay"
        noise.inputs["Scale"].default_value = 3.7
        noise.inputs["Detail"].default_value = 7.0
        noise.inputs["Roughness"].default_value = 0.72

        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.name = "Zombie_CorpsePalette"
        ramp.color_ramp.elements[0].position = 0.18
        ramp.color_ramp.elements[0].color = (0.055, 0.060, 0.040, 1.0)
        ramp.color_ramp.elements[1].position = 0.83
        ramp.color_ramp.elements[1].color = (0.42, 0.50, 0.34, 1.0)
        bruise = ramp.color_ramp.elements.new(0.48)
        bruise.color = (0.13, 0.035, 0.065, 1.0)

        mix = nodes.new("ShaderNodeMixRGB")
        mix.blend_type = "MULTIPLY"
        mix.inputs[0].default_value = 0.88
        if old_socket:
            links.new(old_socket, mix.inputs[1])
        else:
            mix.inputs[1].default_value = base.default_value
        links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], mix.inputs[2])
        links.new(mix.outputs["Color"], base)

    set_principled_input(bsdf, ["Roughness"], 0.66)
    set_principled_input(bsdf, ["Specular IOR Level", "Specular"], 0.24)
    set_principled_input(bsdf, ["Subsurface Weight", "Subsurface"], 0.025)

    if "Normal" in bsdf.inputs and not bsdf.inputs["Normal"].is_linked:
        pore = nodes.new("ShaderNodeTexNoise")
        pore.inputs["Scale"].default_value = 38.0
        pore.inputs["Detail"].default_value = 5.0
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.22
        bump.inputs["Distance"].default_value = 0.015
        links.new(pore.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])


def grime_clothing(mat):
    if not mat:
        return
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = first_principled(mat)
    if not bsdf:
        return
    base = bsdf.inputs.get("Base Color")
    if base:
        old = base.links[0] if base.is_linked and base.links else None
        src = old.from_socket if old else None
        if old:
            links.remove(old)
        noise = nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 7.0
        noise.inputs["Detail"].default_value = 5.0
        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (0.035, 0.028, 0.022, 1.0)
        ramp.color_ramp.elements[1].color = (0.32, 0.28, 0.20, 1.0)
        mix = nodes.new("ShaderNodeMixRGB")
        mix.blend_type = "MULTIPLY"
        mix.inputs[0].default_value = 0.62
        if src:
            links.new(src, mix.inputs[1])
        else:
            mix.inputs[1].default_value = base.default_value
        links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], mix.inputs[2])
        links.new(mix.outputs["Color"], base)
    set_principled_input(bsdf, ["Roughness"], 0.82)


def blood_material(name="M_ZombieBlood"):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = first_principled(mat)
    set_principled_input(bsdf, ["Base Color"], (0.12, 0.0025, 0.004, 1.0))
    set_principled_input(bsdf, ["Roughness"], 0.44)
    set_principled_input(bsdf, ["Specular IOR Level", "Specular"], 0.3)
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 24.0
    noise.inputs["Detail"].default_value = 4.0
    if "Normal" in bsdf.inputs:
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.35
        bump.inputs["Distance"].default_value = 0.008
        links.new(noise.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def bruise_material():
    mat = bpy.data.materials.new("M_ZombieNecrosis")
    mat.use_nodes = True
    bsdf = first_principled(mat)
    set_principled_input(bsdf, ["Base Color"], (0.055, 0.018, 0.03, 1.0))
    set_principled_input(bsdf, ["Roughness"], 0.76)
    return mat


def local_bounds(obj):
    pts = [Vector(c) for c in obj.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def detect_front_sign(body):
    # MakeHuman/MPFB canonical characters face -Y in Blender. The earlier heuristic
    # could be fooled by helper/head extents and produced a back-facing review render.
    return -1.0


def corpse_deform(body, front_sign):
    """Topology-preserving decomposition before rig fitting."""
    lo, hi = local_bounds(body)
    h = max(hi.z - lo.z, 1e-6)
    mid_y = (lo.y + hi.y) * 0.5
    for v in body.data.vertices:
        co = v.co
        zf = (co.z - lo.z) / h
        is_front = front_sign * (co.y - mid_y) > 0.0

        # Very small global tissue irregularity: enough to break perfect CG symmetry.
        n = (((v.index * 1103515245 + 12345) & 0xFFFF) / 65535.0) - 0.5
        if 0.12 < zf < 0.96:
            co.x += n * 0.0017

        if not is_front:
            continue

        # Sunken right cheek and asymmetric lower face.
        if 0.835 < zf < 0.905 and 0.015 < co.x < 0.095:
            co.y -= front_sign * 0.010
            co.x *= 0.985
        if 0.800 < zf < 0.855 and -0.10 < co.x < -0.015:
            co.y -= front_sign * 0.005
            co.x *= 1.012

        # Slightly collapsed upper chest tissue.
        if 0.64 < zf < 0.76 and abs(co.x) < 0.18:
            co.y -= front_sign * 0.003

    body.data.update()


def paint_damage(obj, blood, bruise, front_sign, strength=1.0):
    if obj.type != "MESH":
        return
    if blood.name not in obj.data.materials:
        obj.data.materials.append(blood)
    if bruise.name not in obj.data.materials:
        obj.data.materials.append(bruise)
    blood_i = list(obj.data.materials).index(blood)
    bruise_i = list(obj.data.materials).index(bruise)

    lo, hi = local_bounds(obj)
    h = max(hi.z - lo.z, 1e-6)
    mid_y = (lo.y + hi.y) * 0.5
    # x(m), z fraction of character, x radius, z radius
    targets = [
        (-0.055, 0.885, 0.038, 0.055),
        ( 0.060, 0.845, 0.030, 0.042),
        (-0.125, 0.705, 0.075, 0.092),
        ( 0.110, 0.635, 0.055, 0.080),
        (-0.080, 0.535, 0.050, 0.072),
    ]

    for poly in obj.data.polygons:
        c = poly.center
        if front_sign * (c.y - mid_y) < -0.01:
            continue
        best = 99.0
        for x0, zf, rx, rz in targets:
            dz = c.z - (lo.z + h * zf)
            d = ((c.x - x0) / rx) ** 2 + (dz / rz) ** 2
            best = min(best, d)
        if best < 1.0 and random.random() < 0.80 * strength:
            poly.material_index = blood_i if best < 0.50 and random.random() < 0.72 else bruise_i


def make_eye_dead(eye_obj):
    for mat in eye_obj.data.materials:
        mat.use_nodes = True
        bsdf = first_principled(mat)
        if not bsdf:
            continue
        # Keep procedural eye structure but drain color into a cloudy corpse eye.
        base = bsdf.inputs.get("Base Color")
        if base and not base.is_linked:
            base.default_value = (0.56, 0.60, 0.49, 1.0)
        set_principled_input(bsdf, ["Roughness"], 0.22)
        set_principled_input(bsdf, ["Emission Color", "Emission"], (0.055, 0.08, 0.045, 1.0))
        set_principled_input(bsdf, ["Emission Strength"], 0.22)


def yellow_teeth(obj):
    for mat in obj.data.materials:
        mat.use_nodes = True
        bsdf = first_principled(mat)
        if bsdf:
            base = bsdf.inputs.get("Base Color")
            if base and not base.is_linked:
                base.default_value = (0.34, 0.26, 0.13, 1.0)
            set_principled_input(bsdf, ["Roughness"], 0.7)


def object_tree(root, ObjectService):
    objs = [root]
    try:
        objs.extend(ObjectService.get_list_of_children(root))
    except Exception:
        # recursive fallback
        stack = list(root.children)
        while stack:
            o = stack.pop()
            if o not in objs:
                objs.append(o)
                stack.extend(list(o.children))
    return objs


def select_only(objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        if o and o.name in bpy.context.view_layer.objects:
            o.select_set(True)
    if objs:
        bpy.context.view_layer.objects.active = objs[0]


def export_glb(path, objs):
    select_only(objs)
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        use_selection=True,
        export_cameras=False,
        export_lights=False,
        export_animations=False,
        export_morph=False,
    )


def export_fbx(path, objs):
    select_only(objs)
    bpy.ops.export_scene.fbx(
        filepath=str(path),
        use_selection=True,
        add_leaf_bones=False,
        bake_anim=False,
        path_mode="AUTO",
    )


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def preview_stage(body, front_sign, out_png):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 800
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.003, 0.004, 0.005)

    lo, hi = local_bounds(body)
    h = hi.z - lo.z
    target = (0.0, 0.0, lo.z + h * 0.50)

    bpy.ops.object.camera_add(location=(0.78, front_sign * 2.85, lo.z + h * 0.58))
    cam = bpy.context.object
    cam.name = "ZombiePreviewCamera"
    cam.data.lens = 58
    look_at(cam, target)
    scene.camera = cam

    def area(name, loc, energy, size, color):
        bpy.ops.object.light_add(type="AREA", location=loc)
        light = bpy.context.object
        light.name = name
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = size
        light.data.color = color
        look_at(light, target)
        return light

    area("ColdKey", (-2.0, front_sign * 2.2, lo.z + h * 0.85), 1050.0, 2.0, (0.48, 0.62, 0.82))
    area("BloodRim", (2.0, -front_sign * 1.0, lo.z + h * 0.72), 1450.0, 1.4, (0.75, 0.05, 0.025))
    area("LowFill", (-0.2, front_sign * 1.1, lo.z + h * 0.25), 260.0, 1.2, (0.24, 0.30, 0.25))

    bpy.ops.mesh.primitive_plane_add(size=10.0, location=(0, 0, lo.z - 0.006))
    ground = bpy.context.object
    ground.name = "PreviewGround"
    gmat = bpy.data.materials.new("M_WetConcrete")
    gmat.use_nodes = True
    gbsdf = first_principled(gmat)
    set_principled_input(gbsdf, ["Base Color"], (0.012, 0.014, 0.016, 1.0))
    set_principled_input(gbsdf, ["Roughness"], 0.28)
    ground.data.materials.append(gmat)

    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(out_png)
    bpy.ops.render.render(write_still=True)


def mesh_stats(objs):
    meshes = [o for o in objs if o.type == "MESH"]
    return {
        "mesh_objects": len(meshes),
        "vertices": sum(len(o.data.vertices) for o in meshes),
        "polygons": sum(len(o.data.polygons) for o in meshes),
        "triangles_estimate": sum(
            sum(max(1, len(p.vertices) - 2) for p in o.data.polygons) for o in meshes
        ),
    }


def main():
    args = parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    clean_scene()

    HumanService = dynamic_import("mpfb.services.humanservice", "HumanService")
    TargetService = dynamic_import("mpfb.services.targetservice", "TargetService")
    ExportService = dynamic_import("mpfb.services.exportservice", "ExportService")
    ObjectService = dynamic_import("mpfb.services.objectservice", "ObjectService")

    macro = TargetService.get_default_macro_info_dict()
    # Adult male baseline, lean enough to read as emaciated but not caricatured.
    if "gender" in macro:
        macro["gender"] = 0.16
    if "age" in macro:
        macro["age"] = 0.58
    if "weight" in macro:
        macro["weight"] = 0.36
    if "muscle" in macro:
        macro["muscle"] = 0.42

    body = HumanService.create_human(
        mask_helpers=True,
        detailed_helpers=False,
        extra_vertex_groups=True,
        feet_on_ground=True,
        scale=0.1,
        macro_detail_dict=macro,
    )
    body.name = "Zombie_MPFBBaseline"
    front_sign = detect_front_sign(body)
    corpse_deform(body, front_sign)

    # Real MakeHuman skin, then corpse it procedurally rather than throwing away
    # all the fine albedo detail.
    skin_path = find_asset(args.assets_root, "middleage_caucasian_male.mhmat")
    if not skin_path:
        skin_path = find_asset(args.assets_root, "young_caucasian_male.mhmat")
    if skin_path:
        HumanService.set_character_skin(skin_path, body, skin_type="GAMEENGINE")

    rig = HumanService.add_builtin_rig(body, "game_engine")
    if rig is None:
        raise RuntimeError("MPFB failed to create game_engine rig")
    rig.name = "Zombie_GameEngine_Rig"

    # System body parts are CC0 in the MakeHuman system asset pack.
    attached = []
    for fname, atype, material_type in [
        ("low-poly.mhclo", "Eyes", "PROCEDURAL_EYES"),
        ("teeth_base.mhclo", "Teeth", "GAMEENGINE"),
        ("male_casualsuit01.mhclo", "Clothes", "GAMEENGINE"),
        ("shoes06.mhclo", "Clothes", "GAMEENGINE"),
    ]:
        p = find_asset(args.assets_root, fname)
        if not p:
            print(f"Asset not found, skipping: {fname}")
            continue
        try:
            obj = HumanService.add_mhclo_asset(
                p,
                body,
                asset_type=atype,
                subdiv_levels=0,
                material_type=material_type,
                set_up_rigging=True,
                interpolate_weights=True,
            )
            if obj:
                attached.append((fname, obj))
        except Exception as exc:
            print(f"WARNING attach {fname}: {exc!r}")

    # Corpse skin + integrated material damage.
    for mat in body.data.materials:
        corpse_overlay(mat)

    blood = blood_material()
    bruise = bruise_material()
    paint_damage(body, blood, bruise, front_sign, 1.0)

    for fname, obj in attached:
        if "eye" in fname:
            make_eye_dead(obj)
        elif "teeth" in fname:
            yellow_teeth(obj)
        else:
            # Keep blood off whole clothing polygons; on coarse garments that reads as
            # rectangular stickers. Grime is continuous and the integrated skin wounds
            # remain organic on the denser basemesh.
            for mat in obj.data.materials:
                grime_clothing(mat)

    # Export a helper-free copy using MPFB's official game-export workflow.
    export_root = ExportService.create_character_copy(body, name_suffix="_export")
    export_body = ObjectService.find_object_of_type_amongst_nearest_relatives(export_root, "Basemesh")
    if export_body is None:
        raise RuntimeError("Could not locate MPFB export basemesh")
    ExportService.bake_modifiers_remove_helpers(
        export_body,
        bake_masks=True,
        bake_subdiv=False,
        remove_helpers=True,
        also_proxy=True,
    )
    export_objs = object_tree(export_root, ObjectService)

    glb_path = out / "zombie_mpfb_lod0.glb"
    fbx_path = out / "zombie_mpfb_lod0.fbx"
    export_glb(glb_path, export_objs)
    export_fbx(fbx_path, export_objs)

    # Remove export duplicate from the review render so we do not get doubled geometry.
    for o in export_objs:
        o.hide_render = True
        o.hide_viewport = True

    preview_path = out / "zombie_mpfb_preview.png"
    preview_stage(body, front_sign, preview_path)

    blend_path = out / "zombie_mpfb.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    original_objs = object_tree(body, ObjectService)
    manifest = {
        "pipeline": "MPFB2 + Blender autonomous zombie pipeline",
        "seed": SEED,
        "blender": bpy.app.version_string,
        "mpfb_rig": "game_engine",
        "source_assets": "MakeHuman system assets (CC0)",
        "front_axis_sign_y": front_sign,
        "outputs": {
            "glb": glb_path.name,
            "fbx": fbx_path.name,
            "blend": blend_path.name,
            "preview": preview_path.name,
        },
        "stats": mesh_stats(original_objs),
        "bones": len(rig.data.bones),
        "attached_assets": [fname for fname, _ in attached],
        "quality_gates": {
            "helpers_removed_from_export": True,
            "rig_present": len(rig.data.bones) > 0,
            "lod1_lod2": "deferred until rigged LOD reduction is validated",
            "animation_pack": "next stage",
        },
    }
    (out / "zombie_mpfb_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
