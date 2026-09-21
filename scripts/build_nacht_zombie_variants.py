#!/usr/bin/env python3
"""Build dismemberment-safe Nacht Enhanced zombie body variants.

The shipping LibreQuake MDL stays the source of truth. This tool derives
presentation-only body variants by collapsing vertices that belong to the
removed head/arm region onto an animated neck/shoulder anchor. The NZ:P server
still owns hitboxes, limb state, AI, damage, scoring and round logic.

Quake MDL v6 simple-frame files are supported intentionally; fail closed on
other layouts so a future asset cannot silently corrupt the APK.
"""
from __future__ import annotations

from pathlib import Path
import math
import struct
import sys

IDPOLYHEADER = 0x4F504449
ALIAS_VERSION = 6

if len(sys.argv) != 3:
    raise SystemExit(
        "usage: build_nacht_zombie_variants.py <source-zombie.mdl> <output-dir>"
    )

src = Path(sys.argv[1])
out_dir = Path(sys.argv[2])
data = bytearray(src.read_bytes())

if len(data) < 84:
    raise SystemExit("source zombie MDL is truncated")

ident, version = struct.unpack_from("<II", data, 0)
if ident != IDPOLYHEADER or version != ALIAS_VERSION:
    raise SystemExit(f"unsupported MDL header ident=0x{ident:08x} version={version}")

scale = struct.unpack_from("<3f", data, 8)
origin = struct.unpack_from("<3f", data, 20)
numskins, skinwidth, skinheight, numverts, numtris, numframes = struct.unpack_from(
    "<6I", data, 48
)

if numskins < 1 or numverts < 1 or numtris < 1 or numframes < 1:
    raise SystemExit("invalid MDL dimensions")
if numverts > 2000:
    raise SystemExit(f"vertex budget exceeded: {numverts}")

offset = 84
for _ in range(numskins):
    (skin_type,) = struct.unpack_from("<I", data, offset)
    offset += 4
    if skin_type == 0:
        offset += skinwidth * skinheight
    else:
        (count,) = struct.unpack_from("<I", data, offset)
        offset += 4
        offset += count * 4
        offset += count * skinwidth * skinheight

offset += numverts * 12   # stverts
offset += numtris * 16    # triangles

frame_vertex_offsets: list[int] = []
for frame_index in range(numframes):
    (frame_type,) = struct.unpack_from("<I", data, offset)
    offset += 4
    if frame_type != 0:
        raise SystemExit(
            f"group frame {frame_index} is unsupported; refusing unsafe conversion"
        )
    # bboxmin trivertx + bboxmax trivertx + 16-byte name
    verts_offset = offset + 24
    frame_vertex_offsets.append(verts_offset)
    offset += 24 + numverts * 4

if offset != len(data):
    raise SystemExit(
        f"MDL parse did not consume file exactly: parsed={offset} bytes={len(data)}"
    )

ref_off = frame_vertex_offsets[0]

def world_pos(index: int) -> tuple[float, float, float]:
    qx, qy, qz = data[ref_off + index * 4 : ref_off + index * 4 + 3]
    return (
        qx * scale[0] + origin[0],
        qy * scale[1] + origin[1],
        qz * scale[2] + origin[2],
    )

points = [world_pos(i) for i in range(numverts)]

# LibreQuake zombie orientation is X forward, Y lateral, Z vertical.
# Keep the cuts conservative: shoulders/neck stay on the body so the generated
# silhouette has no large holes. Membership is chosen once from frame 0, then
# follows the same anatomical vertices through every animation frame.
HEAD_Z = 15.0
ARM_SIDE_Y = 4.0
ARM_MIN_Z = -6.0
ARM_MAX_Z = 15.5

head = {i for i, (_, _, z) in enumerate(points) if z >= HEAD_Z}
left_arm = {
    i for i, (_, y, z) in enumerate(points)
    if y >= ARM_SIDE_Y and ARM_MIN_Z <= z <= ARM_MAX_Z
}
right_arm = {
    i for i, (_, y, z) in enumerate(points)
    if y <= -ARM_SIDE_Y and ARM_MIN_Z <= z <= ARM_MAX_Z
}

if not (12 <= len(head) <= 120):
    raise SystemExit(f"head mask sanity check failed: {len(head)} vertices")
if not (8 <= len(left_arm) <= 100):
    raise SystemExit(f"left-arm mask sanity check failed: {len(left_arm)} vertices")
if not (8 <= len(right_arm) <= 100):
    raise SystemExit(f"right-arm mask sanity check failed: {len(right_arm)} vertices")

def nearest(target: tuple[float, float, float]) -> int:
    tx, ty, tz = target
    return min(
        range(numverts),
        key=lambda i: (
            (points[i][0] - tx) ** 2
            + (points[i][1] - ty) ** 2
            + (points[i][2] - tz) ** 2
        ),
    )

# Animated anchor vertices that stay with the torso/shoulders.
neck_anchor = nearest((4.0, 0.0, 13.0))
left_anchor = nearest((4.0, 3.0, 10.0))
right_anchor = nearest((4.0, -3.0, 10.0))

variants = {
    "h0": (head, neck_anchor),
    "l0": (left_arm, left_anchor),
    "r0": (right_arm, right_anchor),
    "h0_l0": (head | left_arm, neck_anchor),
    "h0_r0": (head | right_arm, neck_anchor),
    "l0_r0": (left_arm | right_arm, left_anchor),
    "h0_l0_r0": (head | left_arm | right_arm, neck_anchor),
}

out_dir.mkdir(parents=True, exist_ok=True)

for suffix, (mask, default_anchor) in variants.items():
    variant = bytearray(data)
    for verts_offset in frame_vertex_offsets:
        # For combination variants, choose the appropriate anchor per vertex so
        # an arm never collapses into the neck and stretches across the torso.
        for index in mask:
            if index in head:
                anchor = neck_anchor
            elif index in left_arm:
                anchor = left_anchor
            elif index in right_arm:
                anchor = right_anchor
            else:
                anchor = default_anchor
            src4 = verts_offset + anchor * 4
            dst4 = verts_offset + index * 4
            variant[dst4 : dst4 + 4] = variant[src4 : src4 + 4]

    out = out_dir / f"zombie_lq_{suffix}.mdl"
    out.write_bytes(variant)
    print(f"built {out.name}: collapsed={len(mask)} verts")

print(
    "Nacht zombie masks: "
    f"head={len(head)} left_arm={len(left_arm)} right_arm={len(right_arm)} "
    f"anchors=({neck_anchor},{left_anchor},{right_anchor})"
)
