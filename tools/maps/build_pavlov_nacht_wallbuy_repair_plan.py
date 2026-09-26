#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math
from pathlib import Path
from typing import Any

PURCHASES={
 "arak":("KN-44","weapon","ar_standard","kn44",1400),
 "argus":("Argus","weapon","shotgun_precision","argus",1100),
 "frag":("Fragmentation Grenades","equipment","frag_grenade","frag",250),
 "krm":("KRM-262","weapon","shotgun_pump","krm",750),
 "kuda":("Kuda","weapon","smg_standard","kuda",1250),
 "locus_decal":("Locus","sniper_cabinet","sniper_fastbolt","locus",5000),
 "pharaoh":("Pharo","weapon","smg_burst","pharaoh",700),
 "shiva":("Sheiva","weapon","ar_marksman","shiva",500),
 "triton":("RK5","weapon","pistol_burst","triton",500),
}
ANCHORS={"kn44":"arak","kuda":"kuda","triton":"triton"}

def pmap(e:dict[str,Any]):
 return {p["Name"]:p for p in e.get("Data",[]) if isinstance(p,dict) and isinstance(p.get("Name"),str)}
def structv(p):
 if not p:return None
 v=p.get("Value")
 if isinstance(v,list) and v and isinstance(v[0],dict): return v[0].get("Value")
 return v
def vec(v):
 if not isinstance(v,dict):return None
 def f(k):
  x=v.get(k,0)
  return 0.0 if x=="+0" else float(x)
 return {"x":f("X"),"y":f("Y"),"z":f("Z")}
def dist(a,b):
 return math.sqrt(sum((a[k]-b[k])**2 for k in ("x","y","z")))

def map_wallbuys(path:Path):
 d=json.loads(path.read_text(encoding="utf-8-sig")); ex=d["Exports"]; im=d["Imports"]
 def resolve(i):
  if not i:return ""
  out=[]; seen=set()
  while i and i not in seen:
   seen.add(i); o=im[-i-1] if i<0 else ex[i-1]
   out.append(str(o.get("ObjectName","?"))); i=int(o.get("OuterIndex",0) or 0)
  return "/".join(reversed(out))
 li=next(i+1 for i,e in enumerate(ex) if "LevelExport" in str(e.get("$type","")))
 rows=[]
 for ai in [x for x in ex[li-1].get("Actors",[]) if isinstance(x,int) and x>0]:
  a=ex[ai-1]; cls=resolve(int(a.get("ClassIndex",0) or 0))
  if not cls.endswith("/WallBuy_C"): continue
  ap=pmap(a); root=ap.get("RootComponent",{}).get("Value"); loc=None; rot=None
  if isinstance(root,int) and root>0:
   cp=pmap(ex[root-1]); loc=vec(structv(cp.get("RelativeLocation"))); rot=structv(cp.get("RelativeRotation"))
  wid=ap.get("WeaponID",{}).get("Value")
  rows.append({"actor":a.get("ObjectName"),"weapon_id":wid,"price":ap.get("Price",{}).get("Value"),"location":loc,"rotation":rot})
 return rows

def gltf_to_ue(c):
 x,y,z=[float(v) for v in c]
 return {"x":x*100.0,"y":z*100.0,"z":y*100.0}

def main():
 ap=argparse.ArgumentParser(); ap.add_argument("map_json",type=Path); ap.add_argument("bounds_json",type=Path); ap.add_argument("out_json",type=Path); a=ap.parse_args()
 wall=map_wallbuys(a.map_json); byid={r["weapon_id"]:r for r in wall}
 b=json.loads(a.bounds_json.read_text())["chalks"]
 anchors=[]
 for wid,key in ANCHORS.items():
  expected=gltf_to_ue(b[key]["center"]); actual=byid[wid]["location"]; anchors.append({"weapon_id":wid,"chalk":key,"chalk_center_ue_cm":expected,"functional_actor_location_ue_cm":actual,"distance_cm":dist(expected,actual),"delta_cm":{k:actual[k]-expected[k] for k in expected}})
 slots=[]
 for key,(name,kind,bo3id,pavid,price) in PURCHASES.items():
  center=gltf_to_ue(b[key]["center"]); existing=byid.get(pavid)
  slots.append({
   "id":"purchase_"+key,"canonical":name,"type":kind,"bo3_weapon_id":bo3id,"pavlov_weapon_id":pavid,"price":price,
   "chalk_asset":"zm_prototype_part4_t7_zm_chalk_buy_"+key,
   "chalk_center_ue_cm":center,
   "interaction_location_ue_cm": existing["location"] if existing else center,
   "functional_actor":existing["actor"] if existing else None,
   "functional_actor_price":existing["price"] if existing else None,
   "placement_source":"functional_wallbuy_actor" if existing else "verified_chalk_geometry_center",
   "reconstructed": existing is None,
   "replicationPolicy":"server_authoritative","interaction_radius_cm":150.0
  })
 errs=[]
 if len(wall)!=3: errs.append(f"expected 3 functional WallBuy_C actors, got {len(wall)}")
 if len(b)!=9: errs.append(f"expected 9 chalks, got {len(b)}")
 for x in anchors:
  if x["distance_cm"]>10.0: errs.append(f'anchor {x["weapon_id"]} center mismatch {x["distance_cm"]:.3f} cm > 10 cm')
 for s in slots:
  if s["functional_actor"] and s["functional_actor_price"]!=s["price"]: errs.append(f'{s["canonical"]} price mismatch')
 out={"schema":1,"source":{"map":"Nacht_de_Untoten.umap","workshop_id":"2755515831","note":"Six missing Pavlov interactions reconstructed from verified baked BO3 chalk geometry centers; three existing WallBuy_C actors retained as anchors."},"summary":{"purchase_slot_count":len(slots),"functional_count":sum(not s["reconstructed"] for s in slots),"reconstructed_count":sum(s["reconstructed"] for s in slots),"anchor_max_error_cm":max(x["distance_cm"] for x in anchors),"anchor_mean_error_cm":sum(x["distance_cm"] for x in anchors)/len(anchors),"validation_error_count":len(errs)},"anchors":anchors,"purchase_slots":slots,"validation_errors":errs}
 a.out_json.parent.mkdir(parents=True,exist_ok=True); a.out_json.write_text(json.dumps(out,indent=2)+"\n")
 print(json.dumps(out["summary"],indent=2))
 for s in slots: print(f'{s["canonical"]:24s} {s["price"]:4d} {s["placement_source"]:30s} {s["interaction_location_ue_cm"]}')
 if errs:
  for e in errs: print("VALIDATION_ERROR:",e)
  return 3
 return 0
if __name__=="__main__": raise SystemExit(main())
