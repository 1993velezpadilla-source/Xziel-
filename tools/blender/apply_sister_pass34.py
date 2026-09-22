from pathlib import Path

p=Path('tools/blender/build_cathedral_roster.py')
s=p.read_text(encoding='utf-8')

start=s.index('def sister_wimple_frame(body,h,material):')
end=s.index('\ndef sister_mouth_slit(',start)
new_wimple='''def sister_wimple_frame(body,h,material):
    """Pass 34: one continuous fitted U-shaped cloth ribbon from jaw to jaw over the brow."""
    fy=face_front_y(body,h)
    n=72; center_z=.895*h; rx=.055*h; rz=.072*h
    inner=[]; outer=[]
    # Front-facing upper/side arc only: left jaw -> brow -> right jaw. No floating vertical bars.
    for i in range(n):
        t=i/(n-1)
        a=math.pi*(1.08-1.16*t)  # slightly below left temple across brow to right temple
        x=rx*math.cos(a)
        z=center_z+rz*math.sin(a)
        # Pull cloth close to facial surface; subtle depth/fold variation only.
        y=fy+(.0035+.0020*math.cos(a*2.0))*h
        nx=math.cos(a); nz=math.sin(a)
        half=.0042*h
        inner.append((x-half*nx,y,z-half*nz))
        outer.append((x+half*nx,y,z+half*nz))
    vs=inner+outer; fs=[]
    for i in range(n-1): fs.append((i,i+1,n+i+1,n+i))
    mesh=bpy.data.meshes.new('SisterWimpleFrameMesh'); mesh.from_pydata(vs,[],fs); mesh.update()
    o=bpy.data.objects.new('SisterWimpleFrame',mesh); bpy.context.collection.objects.link(o); assign(o,material)
    sol=o.modifiers.new('WimpleThickness','SOLIDIFY'); sol.thickness=.0014*h; sol.offset=0
    bev=o.modifiers.new('WimpleSoft','BEVEL'); bev.width=.0007*h; bev.segments=3
    sub=o.modifiers.new('WimpleSmooth','SUBSURF'); sub.subdivision_type='CATMULL_CLARK'; sub.levels=2; sub.render_levels=2
    return o
'''
s=s[:start]+new_wimple+s[end:]

start=s.index('def sister_boot_pair(body,rig,h,mats):')
end=s.index('\ndef nun_coif_cap(',start)
new_shoes='''def sister_boot_pair(body,rig,h,mats):
    """Pass 34: compact closed low shoes; one upper + thin sole, no spherical toe proxies."""
    leather=mat('M_SisterBootLeather','#171516',.80,0,noise=True)
    sole_mat=mat('M_SisterBootSole','#0C0B0C',.90,0,noise=True)
    out=[]
    for sign,label,bone in ((-1,'L','foot_l'),(1,'R','foot_r')):
        pts=[v.co for v in body.data.vertices if v.co.z/h<.090 and v.co.x*sign>.010*h]
        if pts:
            cx=sum(p.x for p in pts)/len(pts); cy=sum(p.y for p in pts)/len(pts)
        else:
            cx=sign*.045*h; cy=-.015*h
        # Fixed human-scale half-extents prevent body-bbox inflation and hide all toes.
        upper=cube('SisterShoe_'+label,(cx,cy-.014*h,.026*h),(.034*h,.061*h,.022*h),leather,.011*h)
        out.append(upper)
        sol=cube('SisterSole_'+label,(cx,cy-.016*h,.008*h),(.036*h,.064*h,.0055*h),sole_mat,.0035*h)
        out.append(sol)
    return out
'''
s=s[:start]+new_shoes+s[end:]

s=s.replace('Sister of Ash pass 33 — compact closed shoes hiding toes, tighter fitted wimple, full crown coverage, corpse face and layered habit retained','Sister of Ash pass 34 — continuous fitted U-wimple, compact closed shoes without toe spheres, full crown coverage and layered habit retained')
p.write_text(s,encoding='utf-8')
print('Applied Sister of Ash fidelity pass 34 patch')
