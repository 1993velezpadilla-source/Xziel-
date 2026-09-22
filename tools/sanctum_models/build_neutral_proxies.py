#!/usr/bin/env python3
"""
Generate DCC-neutral Sanctum character blockouts.

No Blender dependency. Standard library only.
Outputs ASCII OBJ + MTL + per-model JSON specs.

These are MODELING SCAFFOLDS, not production sculpts.
Replace geometry while preserving group names, scale and sockets.
"""
from pathlib import Path
import json, math

OUT = Path(__file__).resolve().parents[2] / "generated" / "sanctum_character_proxies"

MODELS = [
    ("choir_wretch",1.75,"slender_robed",["crosses","rope_belt"]),
    ("bell_ringer",1.80,"slender_robed",["bell","rope"]),
    ("censer_brute",2.80,"heavy_robed",["censer","chain","crosses"]),
    ("reliquary_horror",4.50,"boss_shrine",["shrine_back","chains","censers","candles","relics"]),
    ("grave_sexton",1.90,"heavy_worker",["shovel","grave_hook","key_ring"]),
    ("penitent_deacon",1.85,"robed_lantern",["lantern","chain","rope","crosses"]),
    ("stained_shade",1.85,"spectral_robed",["stained_glass_accents","crucifix","rope"]),
    ("waterbound_child",1.10,"child_dress",["mist_vfx"]),
    ("lost_child",1.10,"child_dress",["cloth_doll","rosary"]),
    ("la_llorona",1.70,"hero_dress",["rosary_cross","mist_vfx"]),
]

# normalized human proportions: z is up in OBJ.
PROFILE = {
    "slender_robed": dict(shoulder=.25, torso=.15, hip=.16, robe=.34, head=.105),
    "heavy_robed":   dict(shoulder=.31, torso=.23, hip=.23, robe=.39, head=.11),
    "boss_shrine":   dict(shoulder=.38, torso=.30, hip=.29, robe=.48, head=.095),
    "heavy_worker":  dict(shoulder=.29, torso=.21, hip=.20, robe=.34, head=.105),
    "robed_lantern": dict(shoulder=.26, torso=.17, hip=.18, robe=.36, head=.10),
    "spectral_robed":dict(shoulder=.24, torso=.15, hip=.17, robe=.40, head=.10),
    "child_dress":   dict(shoulder=.20, torso=.14, hip=.17, robe=.30, head=.13),
    "hero_dress":    dict(shoulder=.23, torso=.15, hip=.17, robe=.39, head=.105),
}

def box(verts, faces, name, cx,cy,cz,sx,sy,sz):
    base=len(verts)+1
    for x,y,z in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]:
        verts.append((cx+x*sx*.5,cy+y*sy*.5,cz+z*sz*.5))
    faces += [(name,(base,base+1,base+2,base+3)),(name,(base+4,base+7,base+6,base+5)),
              (name,(base,base+4,base+5,base+1)),(name,(base+1,base+5,base+6,base+2)),
              (name,(base+2,base+6,base+7,base+3)),(name,(base+4,base,base+3,base+7))]

def prism(verts, faces, name, z0,z1,r0,r1,n=10):
    base=len(verts)+1
    for z,r in [(z0,r0),(z1,r1)]:
        for i in range(n):
            a=2*math.pi*i/n
            verts.append((math.cos(a)*r,math.sin(a)*r,z))
    for i in range(n):
        j=(i+1)%n
        faces.append((name,(base+i,base+j,base+n+j,base+n+i)))
    faces.append((name,tuple(base+i for i in reversed(range(n)))))
    faces.append((name,tuple(base+n+i for i in range(n))))

def write_model(mid,height,profile,props):
    p=PROFILE[profile]
    v=[]; f=[]
    # Feet and legs.
    leg_top=height*.46
    box(v,f,"GEO_leg_L",-height*.075,0,leg_top*.48,height*.09,height*.10,leg_top*.92)
    box(v,f,"GEO_leg_R", height*.075,0,leg_top*.48,height*.09,height*.10,leg_top*.92)
    # Robe/skirt silhouette.
    prism(v,f,"GEO_robe",height*.05,height*.72,height*p["robe"],height*p["hip"],12)
    # Torso.
    box(v,f,"GEO_torso",0,0,height*.72,height*p["shoulder"]*2,height*p["torso"],height*.30)
    # Head.
    box(v,f,"GEO_head",0,0,height*.94,height*p["head"]*1.45,height*p["head"]*1.25,height*.12)
    # Arms.
    armz=height*.72
    box(v,f,"GEO_arm_L",-height*(p["shoulder"]+.08),0,armz,height*.10,height*.10,height*.42)
    box(v,f,"GEO_arm_R", height*(p["shoulder"]+.08),0,armz,height*.10,height*.10,height*.42)
    # Boss shrine proxy.
    if profile=="boss_shrine":
        box(v,f,"PROP_shrine_back",0,height*.12,height*.73,height*.62,height*.18,height*.58)
    # Simple prop placeholders.
    for idx,prop in enumerate(props):
        x=height*(.38 + .07*(idx%2)) * (-1 if idx%2==0 else 1)
        box(v,f,"PROP_"+prop,x,0,height*(.48+.06*(idx%3)),height*.06,height*.06,height*.18)

    obj=[]
    obj += [f"# SANCTUM proxy: {mid}",f"# height_m {height}","mtllib sanctum_proxy.mtl"]
    obj += [f"v {x:.6f} {y:.6f} {z:.6f}" for x,y,z in v]
    current=None
    for name,inds in f:
        if name!=current:
            obj.append("g "+name); obj.append("usemtl proxy"); current=name
        obj.append("f "+" ".join(map(str,inds)))

    d=OUT/mid; d.mkdir(parents=True,exist_ok=True)
    (d/(mid+".obj")).write_text("\n".join(obj)+"\n",encoding="utf-8")
    spec={
      "schemaVersion":1,
      "id":mid,
      "heightM":height,
      "profile":profile,
      "root":"ROOT",
      "units":"meters",
      "upAxis":"Z",
      "forwardAxis":"-Y",
      "groups":["GEO_torso","GEO_head","GEO_arm_L","GEO_arm_R","GEO_leg_L","GEO_leg_R","GEO_robe"],
      "props":props,
      "requiredSockets":["socket_head","socket_hand_l","socket_hand_r","socket_foot_l","socket_foot_r","socket_audio","socket_vfx"],
      "note":"Blockout only. Preserve names/scale when replacing with production geometry."
    }
    (d/"model_spec.json").write_text(json.dumps(spec,indent=2),encoding="utf-8")

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"sanctum_proxy.mtl").write_text(
      "newmtl proxy\nKd 0.55 0.55 0.55\nKa 0.05 0.05 0.05\nKs 0.05 0.05 0.05\nNs 20\n",
      encoding="utf-8")
    for row in MODELS: write_model(*row)
    (OUT/"README.txt").write_text(
      "SANCTUM neutral character proxies. Import OBJ in any DCC/engine. "
      "These are scale/segmentation scaffolds, not final art.\n",encoding="utf-8")
    print("SANCTUM_NEUTRAL_PROXIES_OK",len(MODELS),OUT)

if __name__=="__main__":
    main()
