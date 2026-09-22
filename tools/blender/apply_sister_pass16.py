from pathlib import Path
import re

p=Path('tools/blender/build_cathedral_roster.py')
s=p.read_text()

def replace_func(name, body):
    global s
    pat=rf'def {name}\(.*?(?=\ndef [A-Za-z_][A-Za-z0-9_]*\()'
    s2,n=re.subn(pat,body.rstrip()+'\n\n',s,count=1,flags=re.S)
    if n!=1: raise SystemExit(f'failed replacing {name}: {n}')
    s=s2

replace_func('priority_head_cover', '''def priority_head_cover(body,h,style,mats):
    out=[]
    if style=="sister_of_ash":
        # Pass 16: keep cloth off the visible face. The previous fitted shell crossed
        # cheeks/jaw and produced white polygon fragments. Crown/back coverage stays
        # complete while the outer veil/wimple supplies the visible framing.
        fy=face_front_y(body,h)
        blue=mats["ash_blue"]
        crown=body_region_shell(body,"NunHoodCrown",blue,
            lambda q: q.z/h>.872 and (q.y>fy+.032*h or abs(q.x/h)>.070 or q.z/h>.972),.0065*h)
        if crown: out.append(crown)
    elif style=="stained_shade":
        fy=face_front_y(body,h)
        inner=mats["spectral_ivory"]
        a=body_region_shell(body,"ShadeCoif",inner,
            lambda q: q.z/h>.865 and (q.y>fy+.030*h or abs(q.x/h)>.070 or q.z/h>.970),.005*h)
        if a: out.append(a)
    elif style=="la_llorona":
        fy=face_front_y(body,h)
        cap=body_region_shell(body,"HairCap",mats["wet_black"],
            lambda q: q.z/h>.855 and (q.y>fy+.020*h or abs(q.x/h)>.050 or q.z/h>.948),.0045*h)
        if cap: out.append(cap)
    return out''')

replace_func('fitted_priority_clothes', '''def fitted_priority_clothes(body,h,style,mats):
    out=[]
    if style=="sister_of_ash":
        main=mats["ash_blue"]; ivory=mats["dirty_ivory"]
        bod=body_region_shell(body,"FittedBodice",main,
            lambda q:.555<q.z/h<.805 and abs(q.x/h)<.145 and q.y/h<.132,.0030*h)
        if bod: out.append(bod)
        for name,groups in [("FittedSleeve_L",["upperarm_l","lowerarm_l"]),("FittedSleeve_R",["upperarm_r","lowerarm_r"])]:
            o=body_group_shell(body,name,main,groups,.040,.0030*h)
            if o: out.append(o)
        yoke=body_region_shell(body,"FittedShoulderYoke",ivory,
            lambda q:.742<q.z/h<.825 and abs(q.x/h)<.190 and q.y/h<.135,.0035*h)
        if yoke: out.append(yoke)
        # Game-ready footwear is a close shell of the actual foot/ankle. No primitive
        # spheres or oversized proxy shoes are created in this pass.
        bootmat=mats["soot"]
        for side,label in [(-1,"L"),(1,"R")]:
            o=body_region_shell(body,"NunBoot_"+label,bootmat,
                lambda q,side=side: q.z/h<.105 and q.x*side>0,.0038*h)
            if o: out.append(o)
    elif style=="stained_shade":
        main=mats["ash_blue"]
        o=body_region_shell(body,"FittedBodice",main,lambda q:.515<q.z/h<.795 and abs(q.x/h)<.160 and q.y/h<.140,.0045*h)
        if o: out.append(o)
    elif style=="la_llorona":
        main=mats["spectral_ivory"]
        o=body_region_shell(body,"LloronaFittedBodice",main,lambda q:.510<q.z/h<.830 and abs(q.x/h)<.165 and q.y/h<.140,.0045*h)
        if o: out.append(o)
    return out''')

# Pass 16 deliberately reduces procedural micro-noise on the skin. Primary and
# secondary facial forms should read before tertiary pore breakup.
s=s.replace('tex.inputs["Scale"].default_value=55.0 if any(k in lname for k in cloth_keys) else (13.0 if any(k in lname for k in skin_keys) else 7.0)',
            'tex.inputs["Scale"].default_value=55.0 if any(k in lname for k in cloth_keys) else (22.0 if any(k in lname for k in skin_keys) else 7.0)')
s=s.replace('bump.inputs["Strength"].default_value=.22; bump.inputs["Distance"].default_value=.012',
            'bump.inputs["Strength"].default_value=.16; bump.inputs["Distance"].default_value=.006')
s=s.replace('Sister of Ash pass 15 — continuous slim habit, full coif/hood, shader-based corpse bruising, covered boots, no face proxy blocks',
            'Sister of Ash pass 16 — clean face opening, crown-safe hood, reduced skin noise, close-fit footwear, slimmer upper habit')
p.write_text(s)
print('Applied Sister of Ash fidelity pass 16 patch')
