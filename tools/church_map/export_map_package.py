#!/usr/bin/env python3
import hashlib
import json
import os
from pathlib import Path

IN = Path(os.environ.get("CHURCH_PLAN", "church/out/zombies_map_plan.json"))
OUT = Path(os.environ.get("CHURCH_PACKAGE", "church/out/SanctumOfAsh"))
OUT.mkdir(parents=True, exist_ok=True)

plan = json.loads(IN.read_text(encoding="utf-8"))

def uid(text: str) -> str:
    return hashlib.sha1(("sanctum-of-ash:" + text).encode("utf-8")).hexdigest()[:16]

def vec(v):
    return {"x": round(v[0], 5), "y": round(v[1], 5), "z": round(v[2], 5)}

zones = []
zone_names = [z for z in plan["progression"] if z in plan["zones"]]
for name, info in plan["zones"].items():
    zones.append({
        "id": "zone_" + name,
        "type": "zone",
        "bounds": {
            "min": vec(info["min"]),
            "max": vec(info["max"]),
        },
        "neighbors": [],
        "spawnGroups": ["spawns_" + name] if name not in {"other"} else [],
        "environmentProfile": "church_interior" if name != "exterior" else "storm_courtyard",
    })

zone_by_id = {z["id"]: z for z in zones}

def link_zone(a, b):
    aa, bb = "zone_"+a, "zone_"+b
    if aa in zone_by_id and bb in zone_by_id:
        if bb not in zone_by_id[aa]["neighbors"]:
            zone_by_id[aa]["neighbors"].append(bb)
        if aa not in zone_by_id[bb]["neighbors"]:
            zone_by_id[bb]["neighbors"].append(aa)

for a, b in [
    ("exterior","main_church"),
    ("main_church","office_corridor"),
    ("office_corridor","office"),
    ("office_corridor","boiler"),
    ("main_church","tower_stairs"),
    ("tower_stairs","ringing_chamber"),
    ("ringing_chamber","clock_chamber"),
    ("clock_chamber","roof_chamber"),
    ("roof_chamber","tower_top"),
    ("tower_top","turret"),
]:
    link_zone(a,b)

ZONE_ALIASES = {
    "courtyard": "exterior",
    "nave": "main_church",
    "altar": "main_church",
}

def normalize_zone(name):
    name = str(name or "main_church")
    return ZONE_ALIASES.get(name, name)

entities = []
spawns = []
doors = []
box_anchors = []
for obj in plan["interactives"]:
    kind = obj["kind"]
    name = obj["name"]
    props = dict(obj.get("properties") or {})
    position = vec(obj["location"])

    if kind == "zombie_spawn":
        zone = normalize_zone(props.get("zone", "unassigned"))
        spawns.append({
            "id": uid(name),
            "type": "zombie_spawn",
            "transform": {"position": position, "rotation": {"pitch":0,"yaw":0,"roll":0}},
            "zone": "zone_" + zone,
            "tags": ["candidate", "church"],
            "properties": {
                "enabled": True,
                "spawnStyle": "ground_or_window",
                "startsInside": zone != "exterior",
                "weight": 1.0,
                "minRound": 1,
                "maxRound": None,
                "navEntry": None,
                "requiresPlacementValidation": True,
            },
            "links": [],
            "enabled": True,
            "replicationPolicy": "server_authoritative",
        })
        continue

    ent_type = {
        "player_spawn": "player_spawn",
        "door": "door",
        "power": "power_source",
        "box": "box_anchor",
        "pap": "upgrade_machine",
        "perk": "perk_machine",
        "trap": "trap",
        "quest": "quest_interact",
        "boss": "boss_spawn",
    }.get(kind, "generic_interact")

    ent = {
        "id": uid(name),
        "name": name,
        "type": ent_type,
        "transform": {"position": position, "rotation": {"pitch":0,"yaw":0,"roll":0}},
        "zone": "zone_" + normalize_zone(props.get("zone","main_church")),
        "tags": [kind, "sanctum_of_ash"],
        "properties": props,
        "links": [],
        "enabled": True,
        "replicationPolicy": "server_authoritative",
    }
    entities.append(ent)
    if kind == "door":
        doors.append(ent["id"])
    if kind == "box":
        box_anchors.append(ent["id"])

logic_nodes = [
    {
        "nodeId":"power_gate",
        "type":"AND",
        "settings":{"inputs":["fuse_a","fuse_b"]},
        "persistentState":True,
        "authority":"server",
    },
    {
        "nodeId":"power_on",
        "type":"PowerOn",
        "settings":{"circuit":"church_main"},
        "persistentState":True,
        "authority":"server",
    },
    {
        "nodeId":"relic_counter",
        "type":"Counter",
        "settings":{"required":3},
        "persistentState":True,
        "authority":"server",
    },
    {
        "nodeId":"bell_sequence",
        "type":"Sequence",
        "settings":{"length":4,"seedScope":"match","audiovisualAccessibility":True},
        "persistentState":True,
        "authority":"server",
    },
    {
        "nodeId":"clock_0317",
        "type":"Compare",
        "settings":{"expected":"03:17"},
        "persistentState":True,
        "authority":"server",
    },
    {
        "nodeId":"ash_sigil",
        "type":"SoulCollector",
        "settings":{"zone":"zone_main_church","requiredKills":24,"eligibleEnemyTags":["undead","special"]},
        "persistentState":True,
        "authority":"server",
    },
    {
        "nodeId":"start_bell_warden",
        "type":"StartBoss",
        "settings":{"bossId":"bell_warden"},
        "persistentState":True,
        "authority":"server",
    },
    {
        "nodeId":"unlock_altar_forge",
        "type":"SetQuestFlag",
        "settings":{"flag":"altar_forge_unlocked","value":True},
        "persistentState":True,
        "authority":"server",
    },
]

logic_edges = [
    {"sourceNode":"power_gate","sourcePort":"true","targetNode":"power_on","targetPort":"activate"},
    {"sourceNode":"relic_counter","sourcePort":"complete","targetNode":"bell_sequence","targetPort":"enable"},
    {"sourceNode":"bell_sequence","sourcePort":"complete","targetNode":"clock_0317","targetPort":"enable"},
    {"sourceNode":"clock_0317","sourcePort":"true","targetNode":"ash_sigil","targetPort":"enable"},
    {"sourceNode":"ash_sigil","sourcePort":"complete","targetNode":"start_bell_warden","targetPort":"activate"},
    {"sourceNode":"start_bell_warden","sourcePort":"bossKilled","targetNode":"unlock_altar_forge","targetPort":"activate"},
]

quests = {
    "schemaVersion":1,
    "quests":[{
        "id":"seven_bells",
        "scope":"team",
        "title":"Seven Bells",
        "stages":[
            {"id":"relics","description":"Recover the Torn Hymn, Iron Vestry Key and Blackened Censer"},
            {"id":"power","description":"Restore the boiler circuit with two fuses"},
            {"id":"bells","description":"Repeat the bell sequence in the ringing chamber"},
            {"id":"clock","description":"Set the clock to 03:17"},
            {"id":"sigil","description":"Charge the Ash Sigil in the nave"},
            {"id":"boss","description":"Defeat the Bell Warden"},
            {"id":"reward","description":"Unlock the Altar Forge and tower shortcut"},
        ],
    }],
}

manifest = {
    "id":"sanctum_of_ash",
    "version":"0.1.0-blockout",
    "schemaVersion":1,
    "engineMinVersion":"0.1",
    "authors":["Xziel project"],
    "sourceAttribution":["St Giles Cripplegate 3D scan by artfletch — CC BY"],
    "dependencies":[],
    "assetPacks":["st_giles_ccby_scan"],
    "entryScene":"geometry/church_map_mobile_lod0.glb",
    "commercialUseAllowed":True,
    "notes":"Development blockout. Final public release should use the fictionalized geometry pass described in SANCTUM_OF_ASH_MAP_BIBLE.md.",
}

assets = {
    "schemaVersion":1,
    "assets":[{
        "id":"st_giles_ccby_scan",
        "type":"geometry_source",
        "sourceUrl":"https://sketchfab.com/3d-models/st-giles-cripplegate-b92917ff83914adc8bc93959ba8b4399",
        "author":"artfletch",
        "license":"CC BY",
        "attribution":"St Giles Cripplegate by artfletch",
        "modified":True,
        "commercialUseAllowed":True,
    }],
}

map_json = {
    "schemaVersion":1,
    "id":"sanctum_of_ash",
    "displayName":"SANCTUM OF ASH",
    "geometry":"geometry/church_map_mobile_lod0.glb",
    "zones":"zones.json",
    "entities":"entities.json",
    "spawns":"spawns.json",
    "logic":"logic.json",
    "quests":"quests.json",
    "assets":"assets.json",
    "manifest":"manifest.json",
    "powerCircuits":[{
        "id":"church_main",
        "powered":False,
        "sourceNodes":["power_gate"],
        "consumers":["perk_machines","traps","clock_mechanism","altar_forge"],
        "prerequisites":["fuse_a","fuse_b"],
    }],
}

files = {
    "map.json": map_json,
    "zones.json": {"schemaVersion":1, "zones":zones},
    "entities.json": {"schemaVersion":1, "entities":entities},
    "spawns.json": {"schemaVersion":1, "spawns":spawns},
    "logic.json": {"schemaVersion":1, "nodes":logic_nodes, "edges":logic_edges},
    "quests.json": quests,
    "assets.json": assets,
    "manifest.json": manifest,
}
for name, data in files.items():
    (OUT/name).write_text(json.dumps(data, indent=2), encoding="utf-8")

# Portable preflight checks following the project's map contracts.
errors = []
ids = []
for e in entities:
    ids.append(e["id"])
for s in spawns:
    ids.append(s["id"])
if len(ids) != len(set(ids)):
    errors.append("duplicate entity IDs")
if not any(e["type"] == "player_spawn" for e in entities):
    errors.append("missing player spawn")
if not spawns:
    errors.append("missing zombie spawns")
for s in spawns:
    if s["zone"] not in zone_by_id:
        errors.append(f"spawn {s['id']} references missing zone {s['zone']}")
for e in entities:
    if e["zone"] not in zone_by_id and e["type"] not in {"player_spawn"}:
        errors.append(f"entity {e['id']} references missing zone {e['zone']}")
node_ids = {n["nodeId"] for n in logic_nodes}
for edge in logic_edges:
    if edge["sourceNode"] not in node_ids or edge["targetNode"] not in node_ids:
        errors.append(f"bad logic edge {edge}")

preflight = {
    "ok": not errors,
    "errors": errors,
    "counts": {
        "zones": len(zones),
        "entities": len(entities),
        "spawns": len(spawns),
        "doors": len(doors),
        "logicNodes": len(logic_nodes),
        "logicEdges": len(logic_edges),
    },
    "warnings": [
        "Zombie spawn coordinates are geometry-derived candidates and still require nav/window placement validation.",
        "Door transforms are topology blockout anchors, not final collision-fitted doors.",
        "Final release geometry requires fictionalization and optimized collision/LOD passes.",
    ],
}
(OUT/"preflight.json").write_text(json.dumps(preflight, indent=2), encoding="utf-8")

if errors:
    raise SystemExit("MAP_PACKAGE_PREFLIGHT_FAILED: " + "; ".join(errors))
print("MAP_PACKAGE_PREFLIGHT_OK")
print(json.dumps(preflight, indent=2))
