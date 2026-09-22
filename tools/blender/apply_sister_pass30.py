from pathlib import Path
p=Path('tools/blender/build_cathedral_roster.py')
s=p.read_text()
start=s.index('def sister_closed_shoes(')
end=s.index('\ndef sister_face_scars', start)
shoes='''def sister_closed_shoes(body,h,mats):
    """Pass 30: fitted low-profile closed shoes, no sphere/toe proxies."""
    leather=mat("M_SisterClosedShoes","#171516",.82,0,noise=True)
    sole_mat=mat("M_SisterSole","#0D0C0D",.90,0,noise=True)
    out=[]
    for sign,label in ((-1,"L"),(1,"R")):
        # Build a shallow closed upper from the actual foot surface so scale follows anatomy.
        upper=body_region_shell(body,"SisterShoeUpper_"+label,leather,
            lambda q,sign=sign: q.x*sign>.012*h and q.z/h<.075,.0045*h)
        if upper: out.append(upper)
        pts=[v.co for v in body.data.vertices if v.co.x*sign>.012*h and v.co.z/h<.075]
        if pts:
            minx,maxx=min(q.x for q in pts),max(q.x for q in pts)
            miny,maxy=min(q.y for q in pts),max(q.y for q in pts)
            minz=min(q.z for q in pts)
            sole=cube("SisterSole_"+label,((minx+maxx)/2,(miny+maxy)/2,minz+.004*h),
                ((maxx-minx)*.54,(maxy-miny)*.54,.005*h),sole_mat,.002*h)
            out.append(sole)
    return out
'''
s=s[:start]+shoes+s[end:]
start=s.index('def priority_head_cover(')
end=s.index('\ndef eye_socket_rings', start)
head='''def priority_head_cover(body,h,style,mats):
    out=[]
    if style=="sister_of_ash":
        ivory=mats["dirty_ivory"]; blue=mats["ash_blue"]
        # Closed crown + fitted open-face hood. Crown coverage is mandatory.
        out.append(nun_coif_cap("NunInnerCoif",h,ivory,.070,.060,.109,.898,.11))
        out.append(nun_coif_cap("NunOuterHood",h,blue,.079,.068,.120,.897,.63))
        # Remove the forehead patch look: a narrow continuous frame hugs the face perimeter.
        out.append(sister_wimple_frame(body,h,ivory))
        out.append(drape_open("NunBackVeil",h,blue,[
            (.946,.066,.056),(.916,.073,.062),(.882,.081,.068),(.846,.090,.075),
            (.810,.101,.083),(.776,.113,.091),(.744,.126,.099),(.714,.137,.106)
        ],segments=112,theta_max=2.58,tatter=.055,phase=.64,subdiv=2))
    elif style=="stained_shade":
        out.append(nun_coif_cap("ShadeHood",h,mats["spectral_ivory"],.080,.070,.120,.894,.55))
    elif style=="la_llorona":
        out.append(nun_coif_cap("HairCap",h,mats["wet_black"],.079,.069,.118,.894,.3))
    return out
'''
s=s[:start]+head+s[end:]
# Pass 29 face still had a pasted rectangular forehead cloth. Make the frame substantially narrower.
s=s.replace('inner_rx=.047*h; inner_rz=.071*h\n    outer_rx=.057*h; outer_rz=.083*h','inner_rx=.050*h; inner_rz=.078*h\n    outer_rx=.055*h; outer_rz=.085*h')
# Remove facial scar curves: pass 29 showed them as straight painted lines rather than skin damage.
s=s.replace('        sister_face_scars(body,h,mats)','        # Pass 30: scars stay in skin shading/displacement; no floating curve marks.')
# Retain full sleeves but remove ivory shoulder/chest fragments that read as disconnected geometry.
s=s.replace('Sister of Ash pass 29 fitted realism','Sister of Ash pass 30 fitted cloth, anatomical shoes, clean face')
p.write_text(s)
print('SISTER_PASS30_PATCH_OK')
