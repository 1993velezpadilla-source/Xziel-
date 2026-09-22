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
    raw=[int(s[i:i+2],16)/255.0 for i in (0,2,4)]
    return tuple(c/12.92 if c<=0.04045 else ((c+0.055)/1.055)**2.4 for c in raw)

PALETTE={
 "spectral_ivory":"#BDB6AA","waterlogged_linen":"#9E978B","pale_corpse":"#96969A",
 "pale_spirit":"#E8E6E2","pale_drowned":"#C9D6E0","bruise_blue":"#4A5A6B",
 "water_bruise":"#6E7A8F","wet_black":"#0B0B0C","tarnished_silver":"#7A7A7F",
 "mud_silt":"#4B463B","drowned_ivory":"#D8D5C9","drowned_blue":"#5B6B7A",
 "ash_blue":"#46515F","dirty_ivory":"#9D9282","corpse_skin":"#8C8580",
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


def cone_between(name,p0,p1,r0,r1,material,verts=28):
    p0,p1=Vector(p0),Vector(p1)
    axis=p1-p0
    if axis.length < 1e-6:
        return None
    n=axis.normalized()
    helper=Vector((0,0,1)) if abs(n.z)<0.9 else Vector((0,1,0))
    u=n.cross(helper).normalized()
    v=n.cross(u).normalized()
    vs=[]; fs=[]
    for center,r in ((p0,r0),(p1,r1)):
        for i in range(verts):
            a=2*math.pi*i/verts
            q=center+r*(u*math.cos(a)+v*math.sin(a))
            vs.append(tuple(q))
    for i in range(verts):
        j=(i+1)%verts
        fs.append((i,j,verts+j,verts+i))
    mesh=bpy.data.meshes.new(name+"Mesh"); mesh.from_pydata(vs,[],fs); mesh.update()
    o=bpy.data.objects.new(name,mesh); bpy.context.collection.objects.link(o); assign(o,material)
    sol=o.modifiers.new("ClothThickness","SOLIDIFY"); sol.thickness=.004; sol.offset=0
    return o


def open_veil(name,h,material,outer=True,translucent=False):
    seg=42
    rings=5
    zs=[.982,.930,.855,.745,.645] if outer else [.968,.938,.895,.840,.785]
    rxs=[.076,.086,.100,.118,.137] if outer else [.067,.073,.080,.090,.100]
    rys=[.066,.072,.079,.086,.092] if outer else [.056,.060,.064,.068,.072]
    vs=[]; fs=[]
    for r in range(rings):
        z=zs[r]*h
        for i in range(seg):
            a=-2.03 + 4.06*i/(seg-1)
            x=rxs[r]*h*math.sin(a)
            y=rys[r]*h*math.cos(a)
            zz=z
            if r==rings-1:
                zz -= (.022 if outer else .009)*h*(.2+.8*abs(math.sin(i*1.73+0.4)))
            vs.append((x,y,zz))
    for r in range(rings-1):
        for i in range(seg-1):
            a=r*seg+i; b=a+1; c=(r+1)*seg+i+1; d=(r+1)*seg+i
            fs.append((a,b,c,d))
    mesh=bpy.data.meshes.new(name+"Mesh"); mesh.from_pydata(vs,[],fs); mesh.update()
    o=bpy.data.objects.new(name,mesh); bpy.context.collection.objects.link(o); assign(o,material)
    sol=o.modifiers.new("VeilThickness","SOLIDIFY"); sol.thickness=.0028; sol.offset=0
    sub=o.modifiers.new("VeilSmooth","SUBSURF"); sub.subdivision_type="SIMPLE"; sub.levels=1; sub.render_levels=1
    return o
def belt_loop(name,h,material,z=.555,scale_y=.72):
    o=torus(name,(0,0,z*h),.094*h,.0065*h,material)
    o.scale.y=scale_y; apply_obj(o)
    return o


def cloth_patches(prefix,h,material,count=5):
    out=[]
    placements=[(-.075,.385,8),(.075,.445,-6),(-.052,.515,-3),(.062,.575,7),(-.078,.635,4)]
    for i,(xf,zf,deg) in enumerate(placements[:count]):
        p=cube(f"{prefix}_{i:02}",(xf*h,-.119*h,zf*h),(.012*h,.002*h,.017*h),material,.0015*h)
        p.rotation_euler.z=math.radians(deg)
        out.append(p)
    return out

def sleeve_pair(h,material,ragged=False,cuff_material=None):
    out=[]
    for side,label in ((-1,"L"),(1,"R")):
        p0=(side*.145*h,-.006*h,.760*h)
        p1=(side*.245*h,-.018*h,.645*h)
        o=cone_between(f"Sleeve_{label}",p0,p1,.040*h,.030*h,material,36)
        if o: out.append(o)
        if ragged and o:
            cuffmat=cuff_material or material
            p2=(side*.305*h,-.020*h,.555*h)
            c=cone_between(f"CuffRag_{label}",p1,p2,.034*h,.040*h,cuffmat,30)
            if c: out.append(c)
    return out

def shoulder_bib(h,material,name="ShoulderBib",front_y=-.112):
    out=[]
    for front in (True,False):
        y=(front_y if front else .088)*h
        pts=[]
        for i in range(9):
            t=i/8; x=(-.16+.32*t)*h
            pts.append((x,y,.805*h))
        for i in reversed(range(9)):
            t=i/8; x=(-.18+.36*t)*h
            pts.append((x,y,(.695-.010*(i%2))*h))
        mesh=bpy.data.meshes.new(f"{name}{'Front' if front else 'Back'}Mesh")
        mesh.from_pydata(pts,[],[tuple(range(len(pts)))]); mesh.update()
        o=bpy.data.objects.new(f"{name}{'Front' if front else 'Back'}",mesh)
        bpy.context.collection.objects.link(o); assign(o,material)
        sol=o.modifiers.new("BibThickness","SOLIDIFY"); sol.thickness=.003; sol.offset=0
        out.append(o)
    return out


def front_panel(name,h,material,z0,z1,half_bottom,half_top,y=-.118,ragged=False):
    pts=[(-half_bottom*h,y*h,z0*h),(half_bottom*h,y*h,z0*h),(half_top*h,y*h,z1*h),(-half_top*h,y*h,z1*h)]
    if ragged:
        pts=[(-half_bottom*h,y*h,(z0+.016)*h),(-.045*h,y*h,(z0-.010)*h),(0,y*h,(z0+.005)*h),(.050*h,y*h,(z0-.012)*h),(half_bottom*h,y*h,(z0+.014)*h),(half_top*h,y*h,z1*h),(-half_top*h,y*h,z1*h)]
    mesh=bpy.data.meshes.new(name+"Mesh"); mesh.from_pydata(pts,[],[tuple(range(len(pts)))]); mesh.update()
    o=bpy.data.objects.new(name,mesh); bpy.context.collection.objects.link(o); assign(o,material)
    sol=o.modifiers.new("PanelThickness","SOLIDIFY"); sol.thickness=.0035; sol.offset=0
    bev=o.modifiers.new("PanelEdgeSoft","BEVEL"); bev.width=.0018*h; bev.segments=2
    return o

def head_wimple(body,h,mats,style):
    ivory=mats["spectral_ivory"] if style=="stained_shade" else mats["dirty_ivory"]
    fy=face_front_y(body,h)-.004*h
    out=[]
    out.append(cube("WimpleForehead",(0,fy,.955*h),(.066*h,.003*h,.014*h),ivory,.002*h))
    for side in (-1,1):
        strip=cube("WimpleSide_"+("L" if side<0 else "R"),(side*.060*h,fy,.905*h),(.012*h,.003*h,.052*h),ivory,.002*h)
        strip.rotation_euler.y=math.radians(side*5); out.append(strip)
    out.append(front_panel("WimpleChest",h,ivory,.742,.842,.135,.105,fy/h+.003,True))
    return out

def shoe_pair(h,material):
    out=[]
    for side,label in ((-1,"L"),(1,"R")):
        o=uv_sphere("Shoe_"+label,(side*.055*h,-.020*h,.040*h),(.070*h,.110*h,.038*h),material)
        o.rotation_euler.x=math.radians(4); out.append(o)
    return out

def llorona_tears(body,h,mats):
    fy=face_front_y(body,h)-.010*h
    dark=mats["wet_black"]; out=[]
    for side in (-1,1):
        x=side*.020*h
        pts=[(x,fy,.905*h),(x+side*.004*h,fy-.001*h,.885*h),(x+side*.007*h,fy-.001*h,.865*h)]
        out.append(curve_chain("TearTrail_"+("L" if side<0 else "R"),pts,dark,.0018*h))
    return out

def spectral_tatters(h,mats):
    out=[]; matl=mats["spectral_ivory"]
    for i in range(10):
        side=-1 if i%2==0 else 1
        x=side*(.11+.012*(i%3))*h
        z0=(.25+.045*i)*h
        pts=[(x,-.080*h,z0),(x+side*.018*h,-.075*h,z0-.10*h),(x+side*.028*h,-.068*h,z0-.17*h)]
        out.append(curve_chain("SpectralTatter_%02d"%i,pts,matl,.003*h))
    return out

def nun_outfit(h,mats,stained=False):
    ivory=mats["spectral_ivory"] if stained else mats["dirty_ivory"]
    blue=mats["ash_blue"]; rope=mats["rope"]
    metal=mats.get("oxidized_metal",mats.get("old_wood"))
    out=[]
    out.append(frustum("IvoryUnderSkirt",.025*h,.505*h,.150*h,.108*h,.108*h,.085*h,ivory,72,.040*h,.3))
    out.append(frustum("BlueOuterSkirt",.165*h,.695*h,.160*h,.114*h,.112*h,.088*h,blue,72,.052*h,1.1))
    out.append(frustum("BlueBodice",.545*h,.802*h,.108*h,.084*h,.128*h,.093*h,blue,64,.010*h,.6))
    out.append(frustum("IvoryShoulderCape",.690*h,.805*h,.140*h,.105*h,.105*h,.090*h,ivory,56,.020*h,.35))
    out.extend(sleeve_pair(h,blue,True,ivory))
    out.append(open_veil("OuterVeil",h,ivory if stained else blue,True))
    out.append(open_veil("InnerWimple",h,ivory,False))
    out.append(belt_loop("RopeBelt",h,rope,.557,.70))
    out.extend(cross_prop("NunCross",(0,-.132*h,.487*h),.039*h,metal))
    if not stained:
        out.extend(cloth_patches("RepairPatch",h,ivory,3))
    return out

def llorona_outfit(h,mats):
    ivory=mats["spectral_ivory"]; linen=mats.get("waterlogged_linen",ivory); rope=mats["rope"]
    out=[]
    out.append(frustum("LloronaUnderDress",.020*h,.585*h,.155*h,.108*h,.105*h,.083*h,linen,72,.055*h,.1))
    out.append(frustum("LloronaLayerA",.075*h,.730*h,.170*h,.116*h,.112*h,.088*h,ivory,72,.060*h,.8))
    out.append(frustum("LloronaLayerB",.205*h,.795*h,.151*h,.105*h,.118*h,.090*h,linen,64,.045*h,1.7))
    out.append(frustum("LloronaBodice",.545*h,.850*h,.132*h,.112*h,.145*h,.118*h,ivory,64,.012*h,.4))
    out.extend(sleeve_pair(h,ivory,True,linen))
    out.append(belt_loop("RosaryBelt",h,rope,.566,.70))
    mud=mats.get("mud_silt")
    if mud:
        out.append(frustum("MudHem",.022*h,.205*h,.174*h,.118*h,.165*h,.112*h,mud,72,.030*h,.5))
    return out
def stained_halo(h,mats):
    metal=mats["oxidized_metal"]
    out=[]
    halo=torus("StainedHalo",(0,.075*h,.895*h),.128*h,.006*h,metal,rot=(math.radians(90),0,0))
    out.append(halo)
    cols=[mats["glass_blue"],mats["glass_cyan"],mats["glass_magenta"],mats["amber"]]
    for i in range(16):
        a=2*math.pi*i/16
        x=.128*h*math.cos(a); z=.895*h+.128*h*math.sin(a); y=.070*h
        shard=cube(f"HaloGlass_{i:02}",(x,y,z),(.020*h,.003*h,.035*h),cols[i%4],.002*h)
        shard.rotation_euler.y=-a
        out.append(shard)
    return out

def parent_to_bone(obj,rig,bone):
    if bone not in rig.data.bones: return
    mw=obj.matrix_world.copy()
    obj.parent=rig; obj.parent_type="BONE"; obj.parent_bone=bone
    obj.matrix_world=mw

def bind_mesh_vertical(obj,rig,h):
    if obj.type!="MESH": return
    for g in ("pelvis","spine_01","spine_02","spine_03"):
        if g not in obj.vertex_groups: obj.vertex_groups.new(name=g)
    for v in obj.data.vertices:
        z=(obj.matrix_world @ v.co).z/max(h,1e-6)
        if z < .46: bone="pelvis"
        elif z < .59: bone="spine_01"
        elif z < .72: bone="spine_02"
        else: bone="spine_03"
        obj.vertex_groups[bone].add([v.index],1.0,"REPLACE")
    mod=obj.modifiers.new("GameRig","ARMATURE"); mod.object=rig
    obj.parent=rig

def bind_sleeve(obj,rig,h,left=True):
    if obj.type!="MESH": return
    a="upperarm_l" if left else "upperarm_r"; b="lowerarm_l" if left else "lowerarm_r"
    ga=obj.vertex_groups.get(a) or obj.vertex_groups.new(name=a)
    gb=obj.vertex_groups.get(b) or obj.vertex_groups.new(name=b)
    for v in obj.data.vertices:
        z=(obj.matrix_world @ v.co).z/max(h,1e-6)
        t=max(0,min(1,(.765-z)/.22))
        ga.add([v.index],1-t,"REPLACE"); gb.add([v.index],t,"REPLACE")
    mod=obj.modifiers.new("GameRig","ARMATURE"); mod.object=rig
    obj.parent=rig

def bind_generated_to_rig(body,rig,h):
    for o in list(bpy.context.scene.objects):
        if o==body or o==rig: continue
        n=o.name
        if o.type=="CURVE":
            if n.startswith("Hair"): parent_to_bone(o,rig,"head")
            continue
        if o.type!="MESH": continue
        if n.startswith("Eye") or n.startswith("HairRibbon") or n=="HairBack" or n in ("OuterVeil","InnerWimple","StainedHalo") or n.startswith("HaloGlass"):
            parent_to_bone(o,rig,"head"); continue
        if n.startswith("Sleeve_L") or n.startswith("CuffRag_L"):
            bind_sleeve(o,rig,h,True); continue
        if n.startswith("Sleeve_R") or n.startswith("CuffRag_R"):
            bind_sleeve(o,rig,h,False); continue
        if n.startswith(("WimpleForehead","WimpleSide","EyeSocket","MouthShadow","CheekDecay","TearTrail")):
            parent_to_bone(o,rig,"head"); continue
        if n.startswith(("NunCross","RosaryCross")):
            parent_to_bone(o,rig,"spine_02"); continue
        if n.startswith(("RopeBelt","RosaryBelt")):
            parent_to_bone(o,rig,"pelvis"); continue
        if n.startswith(("Dress","Llorona","Ivory","Blue","RepairPatch","OuterRobe","UnderRobe","Stole","ShoulderCape","TornShoulderBib","WimpleChest","SpectralTatter","GlassShard")):
            bind_mesh_vertical(o,rig,h)

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


def face_front_y(body,h):
    ys=[]
    for v in body.data.vertices:
        z=v.co.z/max(h,1e-6)
        if .84 < z < .95:
            ys.append(v.co.y)
    return min(ys) if ys else -.055*h

def add_face_details(body,h,mats,style):
    fy=face_front_y(body,h)
    bruise=mats.get("bruise") or mats.get("bruise_blue") or mats.get("water_bruise") or mats.get("corpse_skin")
    dark=mats.get("soot") or mats.get("wet_black") or bruise
    for side in (-1,1):
        sock=uv_sphere("EyeSocket_"+("L" if side<0 else "R"),(side*.020*h,fy-.004*h,.902*h),(.024*h,.0035*h,.018*h),bruise)
        sock.scale.z=.72
    if style=="stained_shade":
        eye_col="#A9C7D8"; emit="#7DA6C4"
    elif style=="la_llorona":
        eye_col="#8E8A86"; emit=None
    else:
        eye_col="#C5C8C3"; emit=None
    eye_mat=mat("M_FaceEyes_"+style,eye_col,.30,0,emission=emit,noise=False)
    for side in (-1,1):
        uv_sphere("Eye_"+("L" if side<0 else "R"),(side*.019*h,fy-.009*h,.903*h),(.0095*h,.0045*h,.0095*h),eye_mat)
    uv_sphere("MouthShadow",(0,fy-.005*h,.852*h),(.021*h,.003*h,.007*h),dark)
    uv_sphere("CheekDecay",(-.038*h,fy-.003*h,.872*h),(.025*h,.003*h,.022*h),bruise)
    return fy

def llorona_hair(h,mats):
    m=mats["wet_black"]; out=[]
    out.append(open_veil("HairCap",h,m,False))
    for i in range(34):
        side=-1 if i%2==0 else 1
        band=(i%17)/16
        x=side*(.028+.040*band)*h
        front=(i%5 in (0,1))
        y=(-.060 if front else .045)*h + .010*h*math.sin(i*.9)
        z0=(.955-.018*(i%4))*h
        length=(.40+.16*((i*7)%11)/10)*h
        pts=[(x,y,z0),(x*1.05,y+.010*h,z0-.13*h),(x*1.25,y+.020*h,z0-length)]
        out.append(curve_chain("HairClump_%02d"%i,pts,m,.0038*h))
    return out


def llorona_hair_ribbons(h,mats):
    m=mats["wet_black"]; out=[]
    # Back curtain.
    out.append(front_panel("HairBack",h,m,.54,.965,.105,.075,.060,True))
    # Front-side wet locks, intentionally asymmetric.
    for side,label in ((-1,"L"),(1,"R")):
        for j in range(5):
            x0=side*(.038+.010*j)*h
            y=-.074*h-.002*j*h
            ztop=(.955-.014*j)*h
            zbot=(.56+.025*j)*h
            pts=[
                (x0-.018*h,y,zbot),
                (x0+.018*h,y,zbot-.018*h*(j%2)),
                (x0+.013*h,y,ztop),
                (x0-.013*h,y,ztop)
            ]
            mesh=bpy.data.meshes.new(f"HairRibbon_{label}_{j}Mesh")
            mesh.from_pydata(pts,[],[(0,1,2,3)]); mesh.update()
            o=bpy.data.objects.new(f"HairRibbon_{label}_{j}",mesh); bpy.context.collection.objects.link(o); assign(o,m)
            sol=o.modifiers.new("HairThickness","SOLIDIFY"); sol.thickness=.0025; sol.offset=0
            out.append(o)
    return out

def llorona_rosary(h,mats):
    metal=mats.get("tarnished_silver") or mats.get("oxidized_metal")
    rope=mats.get("rope") or metal
    out=[]
    pts=[(-.015*h,-.136*h,.655*h),(.018*h,-.139*h,.585*h),(-.005*h,-.141*h,.515*h),(0,-.143*h,.455*h)]
    out.append(curve_chain("RosaryChain",pts,rope,.004*h))
    out.extend(cross_prop("RosaryCross",(0,-.145*h,.430*h),.032*h,metal))
    return out

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
    if style=="sister_of_ash":
        return nun_outfit(h,mats,False)
    if style=="stained_shade":
        return nun_outfit(h,mats,True)
    if style=="la_llorona":
        return llorona_outfit(h,mats)
    objs=[]
    ivory=mats.get("dirty_ivory") or mats.get("spectral_ivory") or next(iter(mats.values()))
    blue=mats.get("ash_blue") or mats.get("drowned_blue") or ivory
    burg=mats.get("burgundy") or mats.get("choir_red") or blue
    soot=mats.get("soot") or mats.get("gravecoat") or blue
    if style in ("lost_child","waterbound_child"):
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
        objs.append(frustum("OuterRobe",.12*h,.84*h,.30*w,.26*d,.20*w,.20*d,blue if style in ("bell_ringer",) else burg,48,.040*h,.9))
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
    pts=[(-.115,.31),(.108,.37),(-.105,.44),(.118,.50),(-.120,.57),(.110,.64),(-.095,.70),(.092,.75),(-.145,.53),(.142,.59)]
    for i,(xf,zf) in enumerate(pts):
        o=cube(f"GlassShard{i:02}",(xf*h,-.116*h,zf*h),(.006*h,.002*h,.020*h),cols[i%4],.0015*h)
        o.rotation_euler.z=math.radians((-14,10,-6,18)[i%4]); objs.append(o)
    return objs

def setup_skin(body,mats,style):
    tint_hex = "#8B8680" if style=="sister_of_ash" else ("#9CA2A7" if style=="la_llorona" else ("#9B9CA0" if style=="stained_shade" else "#9A928A"))
    tint=hexrgb(tint_hex)
    for m in body.data.materials:
        if not m: continue
        m.use_nodes=True
        bsdf=m.node_tree.nodes.get("Principled BSDF")
        if not bsdf: continue
        base=bsdf.inputs.get("Base Color")
        if base:
            if base.is_linked and base.links:
                old=base.links[0]; src=old.from_socket; m.node_tree.links.remove(old)
                mix=m.node_tree.nodes.new("ShaderNodeMixRGB"); mix.blend_type="MULTIPLY"; mix.inputs[0].default_value=.48
                m.node_tree.links.new(src,mix.inputs[1]); mix.inputs[2].default_value=(*tint,1)
                m.node_tree.links.new(mix.outputs["Color"],base)
            else:
                base.default_value=(*tint,1)
        if "Roughness" in bsdf.inputs: bsdf.inputs["Roughness"].default_value=.68
        if "Specular IOR Level" in bsdf.inputs: bsdf.inputs["Specular IOR Level"].default_value=.22
        elif "Specular" in bsdf.inputs: bsdf.inputs["Specular"].default_value=.22

def tint_asset(obj,hex_color,rough=.55,emission=None):
    if not obj or obj.type!="MESH": return
    tint=hexrgb(hex_color)
    for m in obj.data.materials:
        if not m: continue
        m.use_nodes=True
        bsdf=m.node_tree.nodes.get("Principled BSDF")
        if not bsdf: continue
        base=bsdf.inputs.get("Base Color")
        if base:
            if base.is_linked and base.links:
                old=base.links[0]; src=old.from_socket; m.node_tree.links.remove(old)
                mix=m.node_tree.nodes.new("ShaderNodeMixRGB"); mix.blend_type="MULTIPLY"; mix.inputs[0].default_value=.72
                m.node_tree.links.new(src,mix.inputs[1]); mix.inputs[2].default_value=(*tint,1)
                m.node_tree.links.new(mix.outputs["Color"],base)
            else: base.default_value=(*tint,1)
        if "Roughness" in bsdf.inputs: bsdf.inputs["Roughness"].default_value=rough
        if emission:
            ec=hexrgb(emission)
            if "Emission Color" in bsdf.inputs: bsdf.inputs["Emission Color"].default_value=(*ec,1)
            if "Emission Strength" in bsdf.inputs: bsdf.inputs["Emission Strength"].default_value=.45

def equip_priority_parts(body,style,assets_root,HumanService):
    made={}
    eye_path=find_asset(assets_root,"low-poly.mhclo")
    print("EYE_ASSET",eye_path)
    if eye_path:
        try:
            made["eyes"]=HumanService.add_mhclo_asset(eye_path,body,asset_type="Eyes",material_type="PROCEDURAL_EYES",subdiv_levels=1)
            tint_asset(made["eyes"],"#C8CAC5",.24,"#A9C3CC" if style=="stained_shade" else None)
        except Exception as exc: print("eye asset warning",repr(exc))
    teeth_path=find_asset(assets_root,"teeth_base.mhclo")
    print("TEETH_ASSET",teeth_path)
    if teeth_path:
        try:
            made["teeth"]=HumanService.add_mhclo_asset(teeth_path,body,asset_type="Teeth",material_type="GAMEENGINE",subdiv_levels=0)
            tint_asset(made["teeth"],"#9B8E6D",.70)
        except Exception as exc: print("teeth asset warning",repr(exc))
    if style=="la_llorona":
        hair_path=find_asset(assets_root,"long01.mhclo")
        print("HAIR_ASSET",hair_path)
        if hair_path:
            try:
                made["hair"]=HumanService.add_mhclo_asset(hair_path,body,asset_type="Hair",material_type="GAMEENGINE",subdiv_levels=1)
                tint_asset(made["hair"],"#08090A",.28)
            except Exception as exc: print("hair asset warning",repr(exc))
    return made

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


def pose_review(rig,style):
    def rot(n,xyz):
        pb=rig.pose.bones.get(n)
        if not pb: return
        pb.rotation_mode="XYZ"; pb.rotation_euler=tuple(math.radians(v) for v in xyz)
    if style=="la_llorona":
        rot("spine_03",(8,0,-3)); rot("head",(-6,0,7))
        rot("upperarm_l",(-22,-4,24)); rot("lowerarm_l",(-18,0,5))
        rot("upperarm_r",(-34,5,-18)); rot("lowerarm_r",(-18,0,-5))
    elif style=="stained_shade":
        rot("spine_03",(4,0,2)); rot("head",(-8,0,-8))
        rot("upperarm_l",(-20,0,18)); rot("upperarm_r",(-24,0,-18))
    else:
        rot("spine_03",(10,0,3)); rot("neck_01",(-5,0,-4)); rot("head",(-8,0,8))
        rot("upperarm_l",(-28,-4,20)); rot("lowerarm_l",(-18,0,4))
        rot("upperarm_r",(-22,4,-15)); rot("lowerarm_r",(-16,0,-4))
    bpy.context.view_layer.update()

def preview(body,folder,style):
    scene=bpy.context.scene
    scene.render.engine="BLENDER_EEVEE_NEXT"
    scene.render.resolution_x=720; scene.render.resolution_y=900; scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"; scene.world.color=(.006,.007,.009)
    try: scene.view_settings.exposure=-0.85
    except Exception: pass
    lo,hi=local_bounds(body); h=hi.z-lo.z; target=(0,0,lo.z+h*.52)
    dist=max(2.75,h*1.72)
    bpy.ops.object.camera_add(location=(.22*dist,-dist,lo.z+h*.55))
    cam=bpy.context.object; cam.name="PreviewCamera"; cam.data.lens=62; look_at(cam,target); scene.camera=cam
    for name,loc,en,size,col in [
      ("Key",(-.55*dist,-.62*dist,lo.z+h*.80),300,1.8,(.72,.78,.88)),
      ("Rim",(.58*dist,.30*dist,lo.z+h*.68),190,1.35,(.68,.20,.10)),
      ("Fill",(.05*dist,-.30*dist,lo.z+h*.35),95,1.5,(.38,.42,.48))]:
        bpy.ops.object.light_add(type="AREA",location=loc); L=bpy.context.object
        L.name=name; L.data.energy=en; L.data.size=size; L.data.color=col; look_at(L,target)
    bpy.ops.mesh.primitive_plane_add(size=max(8,h*4),location=(0,0,lo.z-.01)); g=bpy.context.object
    assign(g,mat("M_PreviewGround","#0C0E12",.86,0,noise=False))
    out=folder/"preview.png"; scene.render.filepath=str(out); bpy.ops.render.render(write_still=True)
    return out

def collect_character_objects():
    return [o for o in bpy.context.scene.objects if o.type in {"MESH","ARMATURE","CURVE","EMPTY"} and not o.name.startswith(("Camera","Key","Rim","Fill","PreviewGround"))]

def make_character(ch,assets_root,outroot,HumanService,ObjectService,TargetService):
    clean_scene()
    macro=TargetService.get_default_macro_info_dict()
    for k in ("gender","age","weight","muscle"):
        if k in macro: macro[k]=float(ch.get(k,macro[k]))
    body=HumanService.create_human(mask_helpers=True,detailed_helpers=False,extra_vertex_groups=True,feet_on_ground=True,scale=.1,macro_detail_dict=macro)
    body.name=ch["id"]+"_Body"
    exact_height(body,float(ch["height_m"]))
    # Apply a skin preset before our art-directed material.
    skin=(find_asset(assets_root,"young_caucasian_female.mhmat") if float(ch.get("gender",0.5))>=0.5 else find_asset(assets_root,"middleage_caucasian_male.mhmat")) or find_asset(assets_root,"young_caucasian_male.mhmat")
    if skin:
        try: HumanService.set_character_skin(skin,body,skin_type="GAMEENGINE")
        except Exception: pass
    rig=HumanService.add_builtin_rig(body,"game_engine")
    if rig is None: raise RuntimeError("MPFB game_engine rig creation failed")
    rig.name=ch["id"]+"_Rig"
    parts=equip_priority_parts(body,ch["style"],assets_root,HumanService)
    print("MPFB_PARTS",ch["id"],sorted(parts.keys()))
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
    if style in ("lost_child","waterbound_child","bell_ringer","choir_wretch","penitent_deacon","censer_brute","reliquary_horror"):
        veil(style,h,w,d,veilmat)
    if style=="la_llorona":
        if not parts.get("hair"): print("LA_LLORONA_HAIR_FALLBACK")
        llorona_hair_ribbons(h,mats)
    elif style in ("lost_child","waterbound_child"):
        hair_strands(.97*h,h,mats["wet_black"],22,.28)
    if style=="bell_ringer": bell_prop(h,mats["tarnished_brass"],mats["rope"])
    if style=="grave_sexton": shovel_prop(h,mats.get("iron",mats["dark_iron"]),mats["old_wood"])
    if style=="penitent_deacon": lantern_prop(h,mats["oxidized_metal"],mats["wax"])
    if style=="censer_brute": censer_prop(h,mats.get("oxidized_brass",mats["tarnished_brass"]),mats["rope"])
    if style=="reliquary_horror":
        censer_prop(h,mats.get("oxidized_brass",mats["tarnished_brass"]),mats["rope"]); shrine_back(h,mats["old_wood"],mats["dark_iron"],mats["wax"])
    if style=="stained_shade":
        glass_shards(h,mats); stained_halo(h,mats); spectral_tatters(h,mats)
    if style in ("sister_of_ash","stained_shade"):
        shoe_pair(h,mats["soot"])
    if style=="la_llorona":
        llorona_rosary(h,mats); llorona_tears(body,h,mats)
    if style=="lost_child":
        cross_prop("RosaryCross",(0,-.12*d,.53*h),.035*h,mats.get("tarnished_silver",mats["oxidized_metal"]))
    if style=="lost_child":
        uv_sphere("ClothDoll",(0.16,-.04,.34*h),(.05*h,.035*h,.09*h),mats["dirty_ivory"])
    add_damage_sockets(h) if ch["category"] not in ("random_encounter",) else None
    bind_generated_to_rig(body,rig,h)
    create_actions(rig,ch["animations"])
    folder=outroot/ch["id"]; folder.mkdir(parents=True,exist_ok=True)
    objs=collect_character_objects()
    glb,fbx=export_files(folder,objs)
    blend=folder/"model.blend"
    try: bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
    except Exception: bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    pose_review(rig,style)
    png=preview(body,folder,style)
    tri=sum(sum(max(1,len(p.vertices)-2) for p in o.data.polygons) for o in objs if o.type=="MESH")
    manifest={"id":ch["id"],"name":ch["name"],"category":ch["category"],"style":style,"height_m":ch["height_m"],"rig":"game_engine","bones":len(rig.data.bones),"triangles_estimate":tri,"animations":ch["animations"],"materials":ch["palette"],"outputs":[glb.name,fbx.name,blend.name,png.name],"production_status":"priority fidelity pass 7 — remove proxy geometry and restore character silhouette — MPFB rigged base, fitted body parts, layered church clothing, PBR materials, animation actions, modular damage sockets where applicable"}
    (folder/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return manifest

def main():
    args=parse_args(); spec=json.loads(Path(args.spec).read_text(encoding="utf-8")); out=Path(args.out_dir); out.mkdir(parents=True,exist_ok=True)
    HumanService=dynamic_import("mpfb.services.humanservice","HumanService")
    ObjectService=dynamic_import("mpfb.services.objectservice","ObjectService")
    TargetService=dynamic_import("mpfb.services.targetservice","TargetService")
    only={x.strip() for x in args.only.split(",") if x.strip()}
    manifests=[]; errors={}
    for ch in spec["characters"]:
        if only and ch["id"] not in only: continue
        print("\\n=== BUILD",ch["id"],"===")
        try:
            manifests.append(make_character(ch,args.assets_root,out,HumanService,ObjectService,TargetService))
        except Exception as e:
            errors[ch["id"]]=repr(e); traceback.print_exc()
    summary={"project":spec["project"],"built":[m["id"] for m in manifests],"errors":errors}
    (out/"roster_build_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    if errors: raise RuntimeError("Character build failures: "+json.dumps(errors))
    print(json.dumps(summary,indent=2))

if __name__=="__main__":
    main()
