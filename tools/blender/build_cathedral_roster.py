# SPDX-License-Identifier: MIT
# Cathedral of Absolution / Cripplegate
# Autonomous Blender production builder. Generates real .blend/.glb/.fbx assets
# from the approved character bible using MPFB2 + procedural production geometry.

import argparse, importlib, json, math, random, sys, traceback
from pathlib import Path
import bpy
from mathutils import Vector

random.seed(260921)

def args_after_dashes():
    return sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []

def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument("--assets-root", required=True)
    p.add_argument("--spec", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--only", default="")
    return p.parse_args(args_after_dashes())

def dynamic_import(suffix, key):
    try:
        importlib.import_module("bl_ext.user_default.mpfb")
    except Exception:
        pass
    for n in list(sys.modules):
        if n.endswith(suffix):
            m=importlib.import_module(n)
            if hasattr(m,key): return getattr(m,key)
    raise RuntimeError(f"MPFB symbol not found: {suffix}.{key}")

def clean_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.curves,bpy.data.cameras,bpy.data.lights):
        for b in list(datablocks):
            if b.users==0: datablocks.remove(b)

def find_asset(root, basename):
    hits=list(Path(root).rglob(basename))
    hits.sort(key=lambda p:(len(p.parts),len(str(p))))
    return str(hits[0]) if hits else None

def hexrgb(s):
    s=s.lstrip("#")
    return tuple(int(s[i:i+2],16)/255.0 for i in (0,2,4))

PALETTE={
 "spectral_ivory":"#E8E2D6","waterlogged_linen":"#C7C1B3","pale_corpse":"#D6D8E1",
 "pale_spirit":"#E8E6E2","pale_drowned":"#C9D6E0","bruise_blue":"#4A5A6B",
 "water_bruise":"#6E7A8F","wet_black":"#0B0B0C","tarnished_silver":"#7A7A7F",
 "mud_silt":"#4B463B","drowned_ivory":"#D8D5C9","drowned_blue":"#5B6B7A",
 "ash_blue":"#5F6772","dirty_ivory":"#C8BDAE","corpse_skin":"#B6A89D",
 "bruise":"#6A5966","rope":"#6F5843","tarnished_brass":"#7A664A","soot":"#2E2A28",
 "choir_red":"#7A4B45","gravecoat":"#2E2A28","iron":"#3B3C40","dark_iron":"#3B3C40",
 "old_wood":"#4F392D","burgundy":"#6A3B3A","oxidized_metal":"#5E6A57",
 "oxidized_brass":"#7A664A","wax":"#D8CEC1","glass_blue":"#3A66A8",
 "glass_cyan":"#5DA3C4","glass_magenta":"#824C86","amber":"#B6814A"
}

def mat(name, color, rough=0.72, metal=0.0, emission=None, alpha=1.0, noise=True):
    m=bpy.data.materials.new(name); m.use_nodes=True
    bsdf=m.node_tree.nodes.get("Principled BSDF")
    rgb=hexrgb(color) if isinstance(color,str) else color
    bsdf.inputs["Base Color"].default_value=(*rgb,1)
    if "Roughness" in bsdf.inputs: bsdf.inputs["Roughness"].default_value=rough
    if "Metallic" in bsdf.inputs: bsdf.inputs["Metallic"].default_value=metal
    if "Alpha" in bsdf.inputs: bsdf.inputs["Alpha"].default_value=alpha
    if emission:
        e=hexrgb(emission) if isinstance(emission,str) else emission
        if "Emission Color" in bsdf.inputs: bsdf.inputs["Emission Color"].default_value=(*e,1)
        elif "Emission" in bsdf.inputs: bsdf.inputs["Emission"].default_value=(*e,1)
        if "Emission Strength" in bsdf.inputs: bsdf.inputs["Emission Strength"].default_value=1.8
    if alpha<1.0:
        m.surface_render_method='DITHERED' if hasattr(m,'surface_render_method') else 'BLENDED'
    if noise:
        nodes=m.node_tree.nodes; links=m.node_tree.links
        tex=nodes.new("ShaderNodeTexNoise"); tex.inputs["Scale"].default_value=7.0; tex.inputs["Detail"].default_value=4.0
        ramp=nodes.new("ShaderNodeValToRGB")
        c0=tuple(max(0,c*0.55) for c in rgb)+(1,)
        c1=tuple(min(1,c*1.22) for c in rgb)+(1,)
        ramp.color_ramp.elements[0].color=c0; ramp.color_ramp.elements[1].color=c1
        links.new(tex.outputs["Fac"],ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"],bsdf.inputs["Base Color"])
        bump=nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value=.22; bump.inputs["Distance"].default_value=.012
        links.new(tex.outputs["Fac"],bump.inputs["Height"]); links.new(bump.outputs["Normal"],bsdf.inputs["Normal"])
    return m

def assign(o,m):
    if o.type=="MESH":
        o.data.materials.clear(); o.data.materials.append(m)
        for p in o.data.polygons: p.use_smooth=True

def local_bounds(o):
    pts=[Vector(c) for c in o.bound_box]
    lo=Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts)))
    hi=Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts)))
    return lo,hi

def apply_obj(o):
    bpy.context.view_layer.objects.active=o; o.select_set(True)
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True); o.select_set(False)

def exact_height(body,target):
    lo,hi=local_bounds(body); h=hi.z-lo.z
    if h>1e-5:
        s=target/h; body.scale=(s,s,s); apply_obj(body)

def frustum(name,z0,z1,rx0,ry0,rx1,ry1,material,segments=48,tattered=0.0,phase=0.0):
    vs=[]; fs=[]
    for ring,(z,rx,ry) in enumerate(((z0,rx0,ry0),(z1,rx1,ry1))):
        for i in range(segments):
            a=2*math.pi*i/segments
            zz=z
            if ring==0 and tattered:
                zz += tattered*(0.25+0.75*abs(math.sin(a*5+phase)))*(-1 if i%3 else -0.35)
            vs.append((rx*math.cos(a),ry*math.sin(a),zz))
    for i in range(segments):
        j=(i+1)%segments
        fs.append((i,j,segments+j,segments+i))
    mesh=bpy.data.meshes.new(name+"Mesh"); mesh.from_pydata(vs,[],fs); mesh.update()
    o=bpy.data.objects.new(name,mesh); bpy.context.collection.objects.link(o); assign(o,material)
    sol=o.modifiers.new("ClothThickness","SOLIDIFY"); sol.thickness=0.005; sol.offset=0
    bev=o.modifiers.new("FrayedEdgeSoft","BEVEL"); bev.width=0.0025; bev.segments=2
    return o

def cube(name,loc,scale,material,bevel=.01):
    bpy.ops.mesh.primitive_cube_add(location=loc); o=bpy.context.object; o.name=name; o.scale=scale; apply_obj(o); assign(o,material)
    if bevel:
        b=o.modifiers.new("EdgeWear","BEVEL"); b.width=bevel; b.segments=2
    return o

def cyl(name,loc,radius,depth,material,verts=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=radius,depth=depth,location=loc); o=bpy.context.object; o.name=name; assign(o,material)
    return o

def uv_sphere(name,loc,scale,material):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,location=loc); o=bpy.context.object; o.name=name; o.scale=scale; apply_obj(o); assign(o,material); return o

def torus(name,loc,major,minor,material,rot=(0,0,0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major,minor_radius=minor,major_segments=32,minor_segments=8,location=loc,rotation=rot)
    o=bpy.context.object; o.name=name; assign(o,material); return o

def cross_prop(name,loc,size,material):
    a=cube(name+"_V",loc,(size*.16,size*.08,size),material,size*.03)
    b=cube(name+"_H",(loc[0],loc[1],loc[2]+size*.22),(size*.58,size*.08,size*.14),material,size*.03)
    return [a,b]

def curve_chain(name,pts,material,bevel=.008):
    c=bpy.data.curves.new(name+"Curve","CURVE"); c.dimensions="3D"; c.bevel_depth=bevel; c.bevel_resolution=2
    sp=c.splines.new("BEZIER"); sp.bezier_points.add(len(pts)-1)
    for bp,p in zip(sp.bezier_points,pts):
        bp.co=p; bp.handle_left_type=bp.handle_right_type="AUTO"
    o=bpy.data.objects.new(name,c); bpy.context.collection.objects.link(o)
    o.data.materials.append(material)
    return o

def hair_strands(zhead,h,material,count=26,length=.62):
    objs=[]
    for i in range(count):
        a=2*math.pi*i/count
        x=.075*math.cos(a); y=.07*math.sin(a)
        pts=[(x,y,zhead),(x*1.2,y+.015,zhead-.18*h),(x*1.7,y+.04,zhead-length*h)]
        objs.append(curve_chain(f"Hair_{i:02}",pts,material,.0045))
    return objs

def add_eyes(z,front_y,eye_mat):
    return [uv_sphere("Eye_L",(-.032,front_y,z),(.014,.010,.014),eye_mat),
            uv_sphere("Eye_R",(.032,front_y,z),(.014,.010,.014),eye_mat)]

def add_damage_sockets(h):
    coll=bpy.data.collections.get("DAMAGE_SOCKETS") or bpy.data.collections.new("DAMAGE_SOCKETS")
    if coll.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(coll)
    pts={"HEAD":(0,0,.88*h),"WAIST":(0,0,.50*h),
         "L_SHOULDER":(-.20*h,0,.72*h),"R_SHOULDER":(.20*h,0,.72*h),
         "L_ELBOW":(-.31*h,0,.62*h),"R_ELBOW":(.31*h,0,.62*h),
         "L_HIP":(-.08*h,0,.48*h),"R_HIP":(.08*h,0,.48*h),
         "L_KNEE":(-.08*h,0,.26*h),"R_KNEE":(.08*h,0,.26*h)}
    for n,p in pts.items():
        e=bpy.data.objects.new("SOCKET_"+n,None); e.empty_display_type="SPHERE"; e.empty_display_size=.025*h; e.location=p
        coll.objects.link(e)

def robe_for_style(style,h,w,d,mats):
    objs=[]
    ivory=mats.get("dirty_ivory") or mats.get("spectral_ivory") or next(iter(mats.values()))
    blue=mats.get("ash_blue") or mats.get("drowned_blue") or ivory
    burg=mats.get("burgundy") or mats.get("choir_red") or blue
    soot=mats.get("soot") or mats.get("gravecoat") or blue
    if style in ("la_llorona","lost_child","waterbound_child"):
        outer=mats.get("spectral_ivory") or mats.get("drowned_ivory") or ivory
        objs.append(frustum("DressOuter",.08*h,.73*h,.30*w,.24*d,.18*w,.20*d,outer,56,.035*h,.4))
        objs.append(frustum("DressUpper",.58*h,.86*h,.19*w,.18*d,.18*w,.17*d,outer,48,.012*h,.9))
    elif style=="grave_sexton":
        objs.append(frustum("UnderRobe",.08*h,.70*h,.29*w,.24*d,.19*w,.18*d,ivory,48,.025*h,.2))
        objs.append(frustum("GraveCoat",.12*h,.86*h,.31*w,.27*d,.21*w,.20*d,soot,48,.035*h,1.2))
    elif style=="censer_brute":
        objs.append(frustum("HeavyUnder",.05*h,.72*h,.31*w,.27*d,.24*w,.22*d,ivory,48,.035*h,.5))
        objs.append(frustum("HeavyOuter",.10*h,.88*h,.35*w,.31*d,.26*w,.25*d,soot,48,.045*h,1.5))
        objs.append(frustum("BurgundyStole",.18*h,.84*h,.10*w,.255*d,.08*w,.22*d,burg,32,.025*h,.8))
    elif style=="reliquary_horror":
        objs.append(frustum("BossUnder",.04*h,.74*h,.34*w,.30*d,.25*w,.23*d,ivory,56,.045*h,.4))
        objs.append(frustum("BossOuter",.08*h,.90*h,.38*w,.34*d,.29*w,.27*d,soot,56,.055*h,1.5))
        objs.append(frustum("BossBurgundy",.10*h,.86*h,.16*w,.30*d,.11*w,.24*d,burg,40,.035*h,.2))
    else:
        objs.append(frustum("UnderRobe",.06*h,.70*h,.29*w,.24*d,.18*w,.18*d,ivory,48,.030*h,.3))
        objs.append(frustum("OuterRobe",.12*h,.84*h,.30*w,.26*d,.20*w,.20*d,blue if style in ("bell_ringer","stained_shade") else burg,48,.040*h,.9))
        if style in ("choir_wretch","penitent_deacon"):
            objs.append(frustum("Stole",.16*h,.84*h,.09*w,.265*d,.07*w,.21*d,burg,28,.025*h,.5))
    return objs

def veil(style,h,w,d,material):
    # rear/side veil sheet, face stays visible on -Y.
    ztop=.95*h; zbot=.58*h; y=.18*d
    vs=[(-.24*w,y,ztop),(.24*w,y,ztop),(.36*w,y*1.05,zbot),(-.36*w,y*1.05,zbot)]
    mesh=bpy.data.meshes.new("VeilMesh"); mesh.from_pydata(vs,[],[(0,1,2,3)]); mesh.update()
    o=bpy.data.objects.new("Veil",mesh); bpy.context.collection.objects.link(o); assign(o,material)
    sol=o.modifiers.new("VeilThickness","SOLIDIFY"); sol.thickness=.004
    return o

def bell_prop(h,material,rope_mat):
    z=.43*h
    chain=curve_chain("BellRope",[(-.10,0,.66*h),(-.13,-.02,.53*h),(-.13,-.03,z+.05)],rope_mat,.008)
    bpy.ops.mesh.primitive_cone_add(vertices=32,radius1=.065*h,radius2=.035*h,depth=.09*h,location=(-.13,-.03,z))
    b=bpy.context.object; b.name="Bell"; assign(b,material)
    return [chain,b]

def shovel_prop(h,metal,wood):
    handle=cyl("ShovelHandle",(-.28,0,.38*h),.012*h,.72*h,wood,16); handle.rotation_euler=(0,math.radians(-8),0)
    blade=cube("ShovelBlade",(-.31,0,.08*h),(.055*h,.012*h,.09*h),metal,.012*h)
    return [handle,blade]

def lantern_prop(h,metal,wax):
    x=.20; z=.48*h
    frame=cube("Lantern",(x,-.03,z),(.055,.055,.09),metal,.008)
    glow=uv_sphere("LanternGlow",(x,-.03,z),(.025,.025,.04),wax)
    return [frame,glow]

def censer_prop(h,metal,rope):
    x=-.22*h; z=.30*h
    chain=curve_chain("CenserChain",[(-.14*h,0,.72*h),(-.18*h,-.01,.52*h),(x,-.02,z+.10*h)],metal,.010*h)
    bowl=uv_sphere("Censer",(x,-.02,z),(.09*h,.09*h,.11*h),metal)
    ring=torus("CenserRing",(x,-.02,z+.05*h),.08*h,.009*h,metal)
    return [chain,bowl,ring]

def shrine_back(h,wood,metal,wax):
    objs=[]
    z=.72*h
    objs.append(cube("ShrineSpine",(0,.14*h,z),(.04*h,.025*h,.26*h),wood,.01*h))
    for i,x in enumerate((-.16*h,0,.16*h)):
        objs += cross_prop(f"ShrineCross{i}",(x,.14*h,.82*h+(i%2)*.08*h),.10*h,metal)
        candle=cyl(f"Candle{i}",(x,.12*h,.98*h+(i%2)*.05*h),.012*h,.06*h,wax,16); objs.append(candle)
    return objs

def glass_shards(h,materials):
    objs=[]; cols=[materials["glass_blue"],materials["glass_cyan"],materials["glass_magenta"],materials["amber"]]
    for i in range(18):
        a=2*math.pi*i/18
        z=(.25+.035*i)*h
        x=.18*h*math.cos(a); y=.10*h*math.sin(a)
        o=cube(f"GlassShard{i:02}",(x,y,z),(.012*h,.003*h,.035*h),cols[i%4],.003*h)
        o.rotation_euler=(random.random()*.8,random.random()*.5,a); objs.append(o)
    return objs

def setup_skin(body, mats, style):
    sm=mats.get("pale_corpse") or mats.get("corpse_skin") or mats.get("pale_spirit") or mats.get("pale_drowned")
    if sm:
        body.data.materials.clear(); body.data.materials.append(sm)

def create_actions(rig,names):
    def bone(name):
        return rig.pose.bones.get(name)
    keys=["pelvis","spine_01","spine_02","spine_03","neck_01","head","upperarm_l","lowerarm_l","upperarm_r","lowerarm_r","thigh_l","calf_l","thigh_r","calf_r"]
    def set_rot(n,xyz,frame,action):
        pb=bone(n)
        if not pb:return
        pb.rotation_mode="XYZ"; pb.rotation_euler=tuple(math.radians(v) for v in xyz)
        pb.keyframe_insert("rotation_euler",frame=frame,group=n)
    def set_loc(n,xyz,frame):
        pb=bone(n)
        if not pb:return
        pb.location=xyz; pb.keyframe_insert("location",frame=frame,group=n)
    for nm in names:
        act=bpy.data.actions.new("ANIM_"+nm.upper()); rig.animation_data_create(); rig.animation_data.action=act
        for k in keys:
            pb=bone(k)
            if pb:
                pb.rotation_mode="XYZ"; pb.rotation_euler=(0,0,0); pb.location=(0,0,0)
                pb.keyframe_insert("rotation_euler",frame=1,group=k)
        if nm in ("walk","float"):
            for f,s in ((1,1),(12,-1),(24,1)):
                set_rot("thigh_l",(22*s,0,0),f,act); set_rot("thigh_r",(-22*s,0,0),f,act)
                set_rot("upperarm_l",(-15*s,0,8),f,act); set_rot("upperarm_r",(15*s,0,-8),f,act)
                set_rot("spine_03",(2,0,2*s),f,act)
        elif nm in ("run","panic_run","enraged"):
            for f,s in ((1,1),(8,-1),(16,1)):
                set_rot("thigh_l",(35*s,0,0),f,act); set_rot("thigh_r",(-35*s,0,0),f,act)
                set_rot("upperarm_l",(-32*s,0,8),f,act); set_rot("upperarm_r",(32*s,0,-8),f,act)
                set_rot("spine_03",(10,0,3*s),f,act)
        elif nm in ("attack","heavy_attack","chain_swing","slam","lunge"):
            set_rot("spine_03",(12,0,0),6,act); set_rot("upperarm_r",(-65,0,-20),8,act); set_rot("lowerarm_r",(-35,0,0),8,act)
            set_rot("upperarm_r",(35,0,-10),16,act); set_rot("spine_03",(-5,0,0),16,act)
        elif nm in ("scream","warning"):
            set_rot("head",(-18,0,0),8,act); set_rot("spine_03",(-10,0,0),8,act); set_rot("upperarm_l",(-30,0,35),8,act); set_rot("upperarm_r",(-30,0,-35),8,act)
        elif nm in ("weep","cry","sob"):
            set_rot("head",(22,0,0),10,act); set_rot("spine_03",(18,0,0),10,act); set_rot("upperarm_l",(-70,0,30),10,act); set_rot("upperarm_r",(-70,0,-30),10,act)
        elif nm in ("beckon","guide","gift","false_comfort","prayer"):
            set_rot("upperarm_r",(-55,0,-20),10,act); set_rot("lowerarm_r",(-20,0,0),10,act); set_rot("head",(0,0,-8),10,act)
        elif nm in ("hit",):
            set_rot("spine_03",(0,0,18),4,act); set_rot("head",(0,0,15),4,act); set_rot("spine_03",(0,0,0),10,act)
        elif nm in ("death","collapse"):
            set_rot("spine_03",(55,0,12),18,act); set_rot("head",(28,0,20),18,act); set_loc("pelvis",(0,0,-.35),30)
        elif nm in ("vanish","dissipate"):
            set_rot("spine_03",(0,0,12),15,act); set_rot("head",(-10,0,-15),15,act)
        else:
            for f,a in ((1,-2),(20,2),(40,-2)):
                set_rot("spine_03",(a,0,0),f,act); set_rot("head",(-a*.5,0,a*.3),f,act)
        act.use_fake_user=True
    rig.animation_data.action=None

def select_only(objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        if o and o.name in bpy.context.view_layer.objects: o.select_set(True)
    if objs: bpy.context.view_layer.objects.active=objs[0]

def export_files(folder,objs):
    glb=folder/"model.glb"; fbx=folder/"model.fbx"
    select_only(objs)
    try:
        bpy.ops.export_scene.gltf(filepath=str(glb),export_format="GLB",use_selection=True,export_cameras=False,export_lights=False,export_animations=True,export_animation_mode="ACTIONS",export_apply=True)
    except Exception:
        bpy.ops.export_scene.gltf(filepath=str(glb),export_format="GLB",use_selection=True,export_cameras=False,export_lights=False,export_animations=True,export_apply=True)
    select_only(objs)
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=True,path_mode="AUTO")
    return glb,fbx

def look_at(o,target):
    o.rotation_euler=(Vector(target)-o.location).to_track_quat("-Z","Y").to_euler()

def preview(body,folder,style):
    scene=bpy.context.scene; scene.render.engine="BLENDER_EEVEE_NEXT"; scene.render.resolution_x=640; scene.render.resolution_y=800; scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"; scene.world.color=(.004,.004,.006)
    lo,hi=local_bounds(body); h=hi.z-lo.z; target=(0,0,lo.z+h*.52)
    bpy.ops.object.camera_add(location=(.72,-2.65,lo.z+h*.57)); cam=bpy.context.object; cam.data.lens=58; look_at(cam,target); scene.camera=cam
    for name,loc,en,size,col in [
      ("Key",(-1.8,-1.8,lo.z+h*.82),1050,2.0,(.58,.67,.80)),
      ("Rim",(1.8,1.0,lo.z+h*.70),1300,1.4,(.70,.13,.05)),
      ("Fill",(.2,-.8,lo.z+h*.35),250,1.3,(.28,.32,.28))]:
        bpy.ops.object.light_add(type="AREA",location=loc); L=bpy.context.object; L.name=name; L.data.energy=en; L.data.size=size; L.data.color=col; look_at(L,target)
    bpy.ops.mesh.primitive_plane_add(size=max(8,h*4),location=(0,0,lo.z-.01)); g=bpy.context.object
    assign(g,mat("M_PreviewGround","#101216",.82,0,noise=False))
    out=folder/"preview.png"; scene.render.filepath=str(out); bpy.ops.render.render(write_still=True)
    return out

def collect_character_objects():
    return [o for o in bpy.context.scene.objects if o.type in {"MESH","ARMATURE","CURVE","EMPTY"} and not o.name.startswith(("Camera","Key","Rim","Fill","PreviewGround"))]

def make_character(ch,assets_root,outroot,HumanService,ObjectService):
    clean_scene()
    macro=HumanService.get_default_macro_info_dict() if hasattr(HumanService,"get_default_macro_info_dict") else {}
    for k in ("gender","age","weight","muscle"):
        if k in macro: macro[k]=float(ch.get(k,macro[k]))
    body=HumanService.create_human(mask_helpers=True,detailed_helpers=False,extra_vertex_groups=True,feet_on_ground=True,scale=.1,macro_detail_dict=macro)
    body.name=ch["id"]+"_Body"
    exact_height(body,float(ch["height_m"]))
    # Apply a skin preset before our art-directed material.
    skin=find_asset(assets_root,"middleage_caucasian_male.mhmat") or find_asset(assets_root,"young_caucasian_male.mhmat")
    if skin:
        try: HumanService.set_character_skin(skin,body,skin_type="GAMEENGINE")
        except Exception: pass
    rig=HumanService.add_builtin_rig(body,"game_engine")
    if rig is None: raise RuntimeError("MPFB game_engine rig creation failed")
    rig.name=ch["id"]+"_Rig"
    # Bounds after rig fitting.
    lo,hi=local_bounds(body); h=hi.z-lo.z; w=hi.x-lo.x; d=hi.y-lo.y

    mats={}
    for key in set(ch["palette"]+["corpse_skin","dirty_ivory","ash_blue","burgundy","soot","rope","old_wood","oxidized_metal","wax","tarnished_brass","dark_iron","spectral_ivory","wet_black"]):
        if key not in PALETTE: continue
        rough=.72; metal=0; emission=None; alpha=1
        if key in ("wet_black",): rough=.20
        if key in ("tarnished_silver","tarnished_brass","oxidized_metal","oxidized_brass","iron","dark_iron"): rough=.48; metal=.70
        if key.startswith("glass_") or key=="amber": rough=.28; emission=PALETTE[key]
        if key=="spectral_ivory" and ch["style"]=="stained_shade": alpha=.82
        mats[key]=mat("M_"+ch["id"]+"_"+key,PALETTE[key],rough,metal,emission,alpha)
    setup_skin(body,mats,ch["style"])
    style=ch["style"]
    robe_for_style(style,h,w,d,mats)
    veilmat=mats.get("spectral_ivory") or mats.get("dirty_ivory")
    if style in ("la_llorona","lost_child","waterbound_child","bell_ringer","choir_wretch","penitent_deacon","stained_shade","censer_brute","reliquary_horror"):
        veil(style,h,w,d,veilmat)
    if style in ("la_llorona","lost_child","waterbound_child"):
        hair_strands(.96*h,h,mats["wet_black"],34 if style=="la_llorona" else 22,.55 if style=="la_llorona" else .28)
    eye_m=mat("M_"+ch["id"]+"_Eye","#D8DDE0",.18,0,emission="#AAB5B5",noise=False)
    add_eyes(.89*h,-.105*d,eye_m)
    if style=="bell_ringer": bell_prop(h,mats["tarnished_brass"],mats["rope"])
    if style=="grave_sexton": shovel_prop(h,mats.get("iron",mats["dark_iron"]),mats["old_wood"])
    if style=="penitent_deacon": lantern_prop(h,mats["oxidized_metal"],mats["wax"])
    if style=="censer_brute": censer_prop(h,mats.get("oxidized_brass",mats["tarnished_brass"]),mats["rope"])
    if style=="reliquary_horror":
        censer_prop(h,mats.get("oxidized_brass",mats["tarnished_brass"]),mats["rope"]); shrine_back(h,mats["old_wood"],mats["dark_iron"],mats["wax"])
    if style=="stained_shade": glass_shards(h,mats)
    if style in ("la_llorona","lost_child"):
        cross_prop("RosaryCross",(0,-.12*d,.53*h),.035*h,mats.get("tarnished_silver",mats["oxidized_metal"]))
    if style=="lost_child":
        uv_sphere("ClothDoll",(0.16,-.04,.34*h),(.05*h,.035*h,.09*h),mats["dirty_ivory"])
    add_damage_sockets(h) if ch["category"] not in ("random_encounter",) else None
    create_actions(rig,ch["animations"])
    folder=outroot/ch["id"]; folder.mkdir(parents=True,exist_ok=True)
    objs=collect_character_objects()
    glb,fbx=export_files(folder,objs)
    blend=folder/"model.blend"
    try: bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
    except Exception: bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    png=preview(body,folder,style)
    tri=sum(sum(max(1,len(p.vertices)-2) for p in o.data.polygons) for o in objs if o.type=="MESH")
    manifest={"id":ch["id"],"name":ch["name"],"category":ch["category"],"style":style,"height_m":ch["height_m"],"rig":"game_engine","bones":len(rig.data.bones),"triangles_estimate":tri,"animations":ch["animations"],"materials":ch["palette"],"outputs":[glb.name,fbx.name,blend.name,png.name],"production_status":"procedural production pass 1 — real rigged geometry, PBR materials, props, animation actions, damage sockets where applicable"}
    (folder/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return manifest

def main():
    args=parse_args(); spec=json.loads(Path(args.spec).read_text(encoding="utf-8")); out=Path(args.out_dir); out.mkdir(parents=True,exist_ok=True)
    HumanService=dynamic_import("mpfb.services.humanservice","HumanService")
    ObjectService=dynamic_import("mpfb.services.objectservice","ObjectService")
    only={x.strip() for x in args.only.split(",") if x.strip()}
    manifests=[]; errors={}
    for ch in spec["characters"]:
        if only and ch["id"] not in only: continue
        print("\\n=== BUILD",ch["id"],"===")
        try:
            manifests.append(make_character(ch,args.assets_root,out,HumanService,ObjectService))
        except Exception as e:
            errors[ch["id"]]=repr(e); traceback.print_exc()
    summary={"project":spec["project"],"built":[m["id"] for m in manifests],"errors":errors}
    (out/"roster_build_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    if errors: raise RuntimeError("Character build failures: "+json.dumps(errors))
    print(json.dumps(summary,indent=2))

if __name__=="__main__":
    main()
