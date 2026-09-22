#!/usr/bin/env python3
"""Export Sanctum's fitted Blender gameplay data into Xziel native xmap v2.

The visual church stays the 1.1M-triangle XZSM v3. Gameplay collision is a
bounded set of simplified AABBs derived from authored zone bounds, real fitted
barricades, and progression links. No BSP/Quake runtime data is required.
"""

import json
import math
import os
from pathlib import Path

PLAN = Path(os.environ.get("CHURCH_PLAN", "church/out/zombies_map_plan.json"))
FITTED = Path(os.environ.get("CHURCH_FITTED", "church/out/church_runtime_fitted_v2.json"))
OUT = Path(os.environ.get("XZIEL_NATIVE_MAP_OUT", "church/out/xziel_native_map/sanctum.xmap"))
NATIVE_FLOOR_Y = float(os.environ.get("XZIEL_STATIC_NATIVE_FLOOR_Y", "-1.58"))
WORLD_SCALE = float(os.environ.get("XZIEL_STATIC_WORLD_SCALE", "1.0"))

plan = json.loads(PLAN.read_text(encoding="utf-8"))
fitted = json.loads(FITTED.read_text(encoding="utf-8"))
zones = {k: v for k, v in plan["zones"].items() if k != "other"}

mins = [v["min"] for v in zones.values()]
maxs = [v["max"] for v in zones.values()]
global_min = [min(v[i] for v in mins) for i in range(3)]
global_max = [max(v[i] for v in maxs) for i in range(3)]
center = [(global_min[i] + global_max[i]) * 0.5 for i in range(3)]

def native_point(p):
    return (
        (float(p[0]) - center[0]) * WORLD_SCALE,
        (float(p[2]) - global_min[2]) * WORLD_SCALE + NATIVE_FLOOR_Y,
        -(float(p[1]) - center[1]) * WORLD_SCALE,
    )

def native_aabb(src_min, src_max):
    # Blender Z-up -> Xziel Y-up, with source Y negated into native Z.
    a = native_point(src_min)
    b = native_point(src_max)
    return (
        (min(a[0], b[0]), min(a[1], b[1]), min(a[2], b[2])),
        (max(a[0], b[0]), max(a[1], b[1]), max(a[2], b[2])),
    )

aliases = {
    "courtyard": "exterior",
    "nave": "main_church",
    "altar": "main_church",
}
def norm_zone(name):
    return aliases.get(name, name)

links = [
    ("exterior", "main_church"),
    ("main_church", "office_corridor"),
    ("office_corridor", "office"),
    ("office_corridor", "boiler"),
    ("main_church", "tower_stairs"),
    ("tower_stairs", "ringing_chamber"),
    ("ringing_chamber", "clock_chamber"),
    ("clock_chamber", "roof_chamber"),
    ("roof_chamber", "tower_top"),
    ("tower_top", "turret"),
]

open_sides = {z: set() for z in zones}
for a, b in links:
    if a not in zones or b not in zones:
        continue
    ca = zones[a]["center"]
    cb = zones[b]["center"]
    dx = float(cb[0]) - float(ca[0])
    dy = float(cb[1]) - float(ca[1])
    if abs(dx) >= abs(dy):
        open_sides[a].add("E" if dx > 0 else "W")
        open_sides[b].add("W" if dx > 0 else "E")
    else:
        open_sides[a].add("N" if dy > 0 else "S")
        open_sides[b].add("S" if dy > 0 else "N")

lines = ["xziel_map 2"]
box_id = 1
box_count = 0
wall_height = 3.2
wall_thickness = 0.18
floor_thickness = 0.20

def emit_box(src_center, src_dims):
    global box_id, box_count
    mn = [
        src_center[0] - src_dims[0] * 0.5,
        src_center[1] - src_dims[1] * 0.5,
        src_center[2] - src_dims[2] * 0.5,
    ]
    mx = [
        src_center[0] + src_dims[0] * 0.5,
        src_center[1] + src_dims[1] * 0.5,
        src_center[2] + src_dims[2] * 0.5,
    ]
    nmin, nmax = native_aabb(mn, mx)
    c = tuple((nmin[i] + nmax[i]) * 0.5 for i in range(3))
    h = tuple((nmax[i] - nmin[i]) * 0.5 for i in range(3))
    lines.append(
        "box %d %.6f %.6f %.6f %.6f %.6f %.6f 0 0 1 1"
        % (box_id, c[0], c[1], c[2], h[0], h[1], h[2])
    )
    box_id += 1
    box_count += 1

# Conservative floor slabs + perimeter walls. Sides that connect to another
# authored zone are omitted; the progression door below becomes the blocker.
for zone, info in zones.items():
    mn = [float(x) for x in info["min"]]
    mx = [float(x) for x in info["max"]]
    floor_z = float(plan.get("floor_levels", {}).get(zone, mn[2]))
    sx = max(0.5, mx[0] - mn[0])
    sy = max(0.5, mx[1] - mn[1])
    cx = (mn[0] + mx[0]) * 0.5
    cy = (mn[1] + mx[1]) * 0.5

    emit_box((cx, cy, floor_z - floor_thickness * 0.5), (sx, sy, floor_thickness))

    wall_z = floor_z + wall_height * 0.5
    for side, c, d in (
        ("W", (mn[0] - wall_thickness * 0.5, cy, wall_z), (wall_thickness, sy, wall_height)),
        ("E", (mx[0] + wall_thickness * 0.5, cy, wall_z), (wall_thickness, sy, wall_height)),
        ("S", (cx, mn[1] - wall_thickness * 0.5, wall_z), (sx, wall_thickness, wall_height)),
        ("N", (cx, mx[1] + wall_thickness * 0.5, wall_z), (sx, wall_thickness, wall_height)),
    ):
        if side not in open_sides.get(zone, set()):
            emit_box(c, d)

# Player spawn: use the authored exterior XY but snap feet to the actual
# detected exterior floor, not to the marker cylinder center.
player = next((e for e in plan["interactives"] if e["kind"] == "player_spawn"), None)
if player is None:
    raise RuntimeError("Sanctum player_spawn missing")
src_spawn = list(player["location"])
src_spawn[2] = float(plan["floor_levels"].get("exterior", src_spawn[2]))
spawn = native_point(src_spawn)
main_center = native_point(zones["main_church"]["center"])
yaw = math.degrees(math.atan2(main_center[0] - spawn[0], main_center[2] - spawn[2]))
lines.append("player_spawn %.6f %.6f %.6f %.6f" % (*spawn, yaw))

# Arena clamp follows the captured church footprint with a small safety margin.
native_corners = [
    native_point((global_min[0], global_min[1], global_min[2])),
    native_point((global_max[0], global_max[1], global_max[2])),
]
min_x = min(p[0] for p in native_corners) - 0.5
max_x = max(p[0] for p in native_corners) + 0.5
min_z = min(p[2] for p in native_corners) - 0.5
max_z = max(p[2] for p in native_corners) + 0.5
lines.append("arena %.6f %.6f %.6f %.6f" % (min_x, max_x, min_z, max_z))

# Dynamic progression doors. Door orientation follows the dominant axis between
# the two connected zone centers.
door_links = {
    "DOOR_COURTYARD_NAVE": ("exterior", "main_church"),
    "DOOR_NAVE_OFFICE": ("main_church", "office_corridor"),
    "DOOR_OFFICE_BOILER": ("office_corridor", "boiler"),
    "DOOR_NAVE_TOWER": ("main_church", "tower_stairs"),
    "DOOR_STAIRS_RINGING": ("tower_stairs", "ringing_chamber"),
    "DOOR_RINGING_CLOCK": ("ringing_chamber", "clock_chamber"),
    "DOOR_CLOCK_ROOF": ("clock_chamber", "roof_chamber"),
}
door_id = 2000
for e in plan["interactives"]:
    if e["kind"] != "door":
        continue
    pair = door_links.get(e["name"])
    if pair is None or pair[0] not in zones or pair[1] not in zones:
        continue
    ca, cb = zones[pair[0]]["center"], zones[pair[1]]["center"]
    thin_x = abs(float(cb[0]) - float(ca[0])) >= abs(float(cb[1]) - float(ca[1]))
    p = list(e["location"])
    floor_z = min(
        float(plan["floor_levels"].get(pair[0], p[2])),
        float(plan["floor_levels"].get(pair[1], p[2])),
    )
    p[2] = floor_z + 1.25
    dims = (0.26, 2.2, 2.5) if thin_x else (2.2, 0.26, 2.5)
    mn = [p[i] - dims[i] * 0.5 for i in range(3)]
    mx = [p[i] + dims[i] * 0.5 for i in range(3)]
    nmin, nmax = native_aabb(mn, mx)
    ip = native_point((p[0], p[1], floor_z + 1.0))
    cost = int((e.get("properties") or {}).get("cost", 750))
    lines.append(
        "door %d %d 0 %.6f %.6f %.6f %.6f %.6f %.6f %.6f %.6f %.6f 2.0 0.05 1.25 0.15"
        % (door_id, cost, *nmin, *nmax, *ip)
    )
    door_id += 1

# Fitted barricades become native windows and also provide the real outside
# zombie spawn points. Keep all candidates; engine capacity is intentionally
# larger than the old eight-window prototype.
window_id = 3000
for rec in fitted.get("barricades", []):
    loc = [float(x) for x in rec["location"]]
    normal = [float(x) for x in rec["normal"]]
    thin_x = abs(normal[0]) >= abs(normal[1])
    dims = (0.18, 1.8, 2.2) if thin_x else (1.8, 0.18, 2.2)
    mn = [loc[i] - dims[i] * 0.5 for i in range(3)]
    mx = [loc[i] + dims[i] * 0.5 for i in range(3)]
    nmin, nmax = native_aabb(mn, mx)
    ip = native_point(loc)
    lines.append(
        "window %d %.6f %.6f %.6f %.6f %.6f %.6f 6 0.92 0.68 10 60 %.6f %.6f %.6f 1.65 0.08 1.30"
        % (window_id, *nmin, *nmax, *ip)
    )
    outside = rec.get("outside")
    if outside:
        sp = native_point(outside)
        lines.append("zombie_spawn %.6f %.6f %.6f" % sp)
    window_id += 1

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

report = {
    "schemaVersion": 2,
    "sourcePlan": str(PLAN),
    "sourceFitted": str(FITTED),
    "boxCount": box_count,
    "doorCount": door_id - 2000,
    "windowCount": window_id - 3000,
    "zombieSpawnCount": sum(1 for x in lines if x.startswith("zombie_spawn ")),
    "playerSpawn": spawn,
    "playerYawDegrees": yaw,
    "arena": [min_x, max_x, min_z, max_z],
    "nativeFloorY": NATIVE_FLOOR_Y,
    "worldScale": WORLD_SCALE,
}
(OUT.parent / "sanctum_native_map_report.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)
print("XZIEL_NATIVE_MAP_READY", json.dumps(report, sort_keys=True))
