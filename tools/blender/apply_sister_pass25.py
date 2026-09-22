from pathlib import Path
import re

p=Path('tools/blender/build_cathedral_roster.py')
s=p.read_text(encoding='utf-8')

def repl(name, body):
    global s
    pat=rf'def {name}\([^\n]*\):\n.*?(?=\ndef [A-Za-z_][A-Za-z0-9_]*\(|\Z)'
    ns,n=re.subn(pat,body.rstrip()+'\n',s,flags=re.S)
    if n!=1: raise SystemExit(f'expected one {name}, got {n}')
    s=ns

repl('priority_head_cover', '''def priority_head_cover(body,h,style,mats):
    out=[]
    if style=="sister_of_ash":
        ivory=mats["dirty_ivory"]; blue=mats["ash_blue"]; fy=face_front_y(body,h)
        # Closed fitted crown layers; aperture stays tight to the actual hairline.
        out.append(nun_coif_cap("NunInnerCoif",h,ivory,.070,.060,.108,.899,.10))
        out.append(nun_coif_cap("NunOuterHood",h,blue,.080,.069,.121,.898,.62))
        # Narrow forehead/temple wimple instead of the broad scalp patch seen in pass 24.
        faceband=body_region_shell(body,"NunFaceWimple",ivory,
            lambda q: (
                (.954<q.z/h<.979 and abs(q.x/h)<.064 and q.y<fy+.032*h) or
                (.850<q.z/h<.951 and .058<abs(q.x/h)<.075 and q.y<fy+.036*h)
            ),.0034*h)
        if faceband: out.append(faceband)
        neck=body_region_shell(body,"NunNeckWimple",ivory,
            lambda q:.748<q.z/h<.835 and abs(q.x/h)<.124 and q.y/h<.140,.0032*h)
        if neck: out.append(neck)
        out.append(drape_open("NunBackVeil",h,blue,[
            (.952,.067,.057),(.920,.074,.063),(.885,.082,.069),(.848,.092,.076),
            (.810,.103,.084),(.774,.116,.092),(.740,.129,.100),(.712,.141,.107)
        ],segments=108,theta_max=2.68,tatter=.060,phase=.62,subdiv=1))
    elif style=="stained_shade":
        out.append(nun_coif_cap("ShadeHood",h,mats["spectral_ivory"],.080,.070,.120,.894,.55))
    elif style=="la_llorona":
        out.append(nun_coif_cap("HairCap",h,mats["wet_black"],.079,.069,.118,.894,.3))
    return out
''')

repl('nun_outfit', '''def nun_outfit(h,mats,stained=False):
    ivory=mats["spectral_ivory"] if stained else mats["dirty_ivory"]
    blue=mats["ash_blue"]; rope=mats["rope"]; metal=mats.get("oxidized_metal",mats.get("old_wood"))
    out=[]
    # Continuous ivory under-habit. Only the lower section should read from outside.
    out.append(garment_shell("IvoryUnderSkirt",h,ivory,[
        (.012,.122,.084,0),(.065,.130,.089,0),(.145,.133,.091,0),(.235,.132,.091,0),
        (.335,.126,.088,0),(.455,.115,.083,0),(.575,.105,.078,0),(.700,.099,.074,0)
    ],112,.070,.34,1))
    # Blue outer habit has a controlled torn hem instead of the giant white camouflage holes from pass 24.
    out.append(garment_shell("BlueOuterSkirt",h,blue,[
        (.205,.125,.088,-.002),(.265,.130,.091,-.002),(.345,.132,.092,-.003),
        (.435,.127,.090,-.003),(.525,.119,.085,-.004),(.610,.109,.080,-.004),
        (.678,.102,.076,-.004),(.720,.100,.074,-.004)
    ],112,.055,1.34,1))
    out.append(drape_open("ShoulderCape",h,ivory,[
        (.838,.077,.064),(.817,.088,.070),(.794,.099,.077),(.770,.112,.085),
        (.746,.125,.093),(.723,.138,.101)
    ],104,2.46,.060,1.55,1))
    out.append(drape_open("OuterVeil",h,blue,[
        (.973,.053,.048),(.946,.058,.052),(.915,.064,.056),(.881,.072,.061),
        (.845,.081,.068),(.810,.091,.075),(.777,.102,.083),(.747,.113,.090),(.719,.125,.097)
    ],108,2.64,.072,.82,1))
    out.append(drape_open("InnerWimple",h,ivory,[
        (.950,.043,.038),(.927,.047,.041),(.902,.051,.044),(.877,.056,.048),
        (.852,.062,.052),(.827,.068,.057),(.803,.076,.062),(.781,.084,.067)
    ],96,2.42,.032,1.12,1))
    out.extend(rope_belt_with_tails(h,rope,metal,"RopeBelt"))
    return out
''')

repl('sister_boot_pair', '''def sister_boot_pair(rig,h,mats):
    # Closed low shoes: broad toe box sits in front of the anatomical toes and fully hides them.
    leather=mat("M_SisterBootLeather","#171516",.72,0,noise=True)
    out=[]
    for side,label in (("l","L"),("r","R")):
        p0,p1=bone_points(rig,"foot_"+side)
        if p0 is None or p1 is None: continue
        axis=p1-p0
        if axis.length<1e-6: continue
        n=axis.normalized()
        center=p0+n*.060*h+Vector((0,-.020*h,.025*h))
        shoe=uv_sphere("SisterShoe_"+label,tuple(center),(.057*h,.125*h,.043*h),leather)
        shoe.rotation_mode="QUATERNION"; shoe.rotation_quaternion=n.to_track_quat("Y","Z")
        out.append(shoe)
        shaft=cone_between("SisterAnkle_"+label,p0+Vector((0,0,.008*h)),p0+Vector((0,0,.082*h)),.048*h,.039*h,leather,48)
        if shaft: out.append(shaft)
    return out
''')

# Paint the underlying foot dark before adding the closed shoe, eliminating skin-colored toe leaks.
s=s.replace('        sister_mouth_cavity(body,h,mats)\n        sister_boot_pair(rig,h,mats)',
            '        sister_mouth_cavity(body,h,mats)\n        sister_paint_footwear(body,h)\n        sister_boot_pair(rig,h,mats)')
# Ensure generated shoes follow the foot bones.
s=s.replace('("SisterShoe_L","SisterAnkle_L","SisterSole_L")','("SisterShoe_L","SisterAnkle_L","SisterSole_L","SisterToeCap_L")')
s=s.replace('("SisterShoe_R","SisterAnkle_R","SisterSole_R")','("SisterShoe_R","SisterAnkle_R","SisterSole_R","SisterToeCap_R")')
s=s.replace('Sister of Ash pass 24 — fitted face wimple, layered ragged underskirt, corpse mouth slit, fitted cuffs, closed shoes, stronger cloth aging',
            'Sister of Ash pass 25 — narrow fitted wimple, controlled layered hem, closed dark shoes, reduced veil geometry, corpse face refinement')
p.write_text(s,encoding='utf-8')
print('APPLIED_SISTER_PASS25')
