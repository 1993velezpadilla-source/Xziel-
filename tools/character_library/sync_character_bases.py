#!/usr/bin/env python3
"""Sync a redistribution-safe humanoid/ragdoll base library into the repo.

The generated library is intended to be the dimensional authority for future
creature concepts. Every base gets:
  - model.glb: exact source model
  - preview.png: screenshot/preview of that exact model
  - measurements.json: geometry, skeleton and normalized dimensions
  - measurement_front.svg / measurement_side.svg: visual measurement templates
  - LICENSE.txt and SOURCE.txt: provenance

Only sources with redistribution-compatible licenses belong here.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import struct
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "character_bases"
GENERATED_DOC = ROOT / "docs" / "CHARACTER_BASE_LIBRARY.generated.md"

DEFAULT_WORLD_HEIGHT_M = 1.75
UA = "Xziel-Character-Base-Library/1.0 (+https://github.com/1993velezpadilla-source/config-old-3)"

KENNEY_BASE = (
    "https://raw.githubusercontent.com/Mathis-14/mantra-raise-hackathon/main/"
    "game/assets/models/mini-characters"
)
KENNEY_LICENSE = KENNEY_BASE + "/License.txt"

SOURCES: list[dict[str, Any]] = [
    {
        "id": "quaternius-human-rigged",
        "display_name": "Quaternius Human — rigged",
        "author": "Quaternius; prepared mirror by UMRAM-Bilkent",
        "license": "CC0-1.0",
        "source_page": "https://github.com/UMRAM-Bilkent/supine-human-model",
        "model_url": "https://raw.githubusercontent.com/UMRAM-Bilkent/supine-human-model/main/assets/human.glb",
        "preview_url": "https://raw.githubusercontent.com/UMRAM-Bilkent/supine-human-model/main/assets/human_preview.png",
        "license_url": "https://raw.githubusercontent.com/UMRAM-Bilkent/supine-human-model/main/LICENSE",
        "default_world_height_m": 1.75,
        "tags": ["humanoid", "adult", "rigged", "animated", "cc0", "quaternius"],
    },
]

for sex in ("male", "female"):
    for variant in "abcdef":
        stem = f"character-{sex}-{variant}"
        SOURCES.append(
            {
                "id": f"kenney-mini-{sex}-{variant}",
                "display_name": f"Kenney Mini Character {sex.title()} {variant.upper()}",
                "author": "Kenney",
                "license": "CC0-1.0",
                "source_page": "https://kenney.nl/assets/mini-characters",
                "mirror_page": "https://github.com/Mathis-14/mantra-raise-hackathon",
                "model_url": KENNEY_BASE + f"/Models/GLB%20format/{stem}.glb",
                "preview_url": KENNEY_BASE + f"/Previews/{stem}.png",
                "license_url": KENNEY_LICENSE,
                "default_world_height_m": 1.75,
                "tags": ["humanoid", "stylized", "rigged", "animated", "cc0", "kenney"],
            }
        )

COMPONENTS = {
    5120: ("b", 1),
    5121: ("B", 1),
    5122: ("h", 2),
    5123: ("H", 2),
    5125: ("I", 4),
    5126: ("f", 4),
}
TYPE_N = {
    "SCALAR": 1,
    "VEC2": 2,
    "VEC3": 3,
    "VEC4": 4,
    "MAT2": 4,
    "MAT3": 9,
    "MAT4": 16,
}


def download(url: str, dest: Path) -> bytes:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as response:
        data = response.read()
    dest.write_bytes(data)
    return data


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_glb(data: bytes) -> tuple[dict[str, Any], bytes]:
    if len(data) < 20:
        raise ValueError("GLB too small")
    magic, version, declared = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2:
        raise ValueError(f"Unsupported GLB header: magic={magic!r}, version={version}")
    if declared > len(data):
        raise ValueError("GLB declared length exceeds file size")

    gltf: dict[str, Any] | None = None
    bin_chunk = b""
    offset = 12
    while offset + 8 <= declared:
        chunk_len, chunk_type = struct.unpack_from("<II", data, offset)
        offset += 8
        payload = data[offset : offset + chunk_len]
        offset += chunk_len
        if chunk_type == 0x4E4F534A:  # JSON
            gltf = json.loads(payload.decode("utf-8").rstrip("\x00 \t\r\n"))
        elif chunk_type == 0x004E4942 and not bin_chunk:  # BIN
            bin_chunk = payload
    if gltf is None:
        raise ValueError("GLB missing JSON chunk")
    return gltf, bin_chunk


def accessor_values(gltf: dict[str, Any], bin_chunk: bytes, accessor_index: int) -> list[tuple[float, ...]]:
    a = gltf["accessors"][accessor_index]
    if "bufferView" not in a:
        return []
    bv = gltf["bufferViews"][a["bufferView"]]
    component_type = int(a["componentType"])
    if component_type not in COMPONENTS:
        raise ValueError(f"Unsupported componentType {component_type}")
    fmt_char, component_size = COMPONENTS[component_type]
    count = int(a["count"])
    ncomp = TYPE_N[a["type"]]
    element_size = component_size * ncomp
    stride = int(bv.get("byteStride", element_size))
    base = int(bv.get("byteOffset", 0)) + int(a.get("byteOffset", 0))
    fmt = "<" + (fmt_char * ncomp)
    vals: list[tuple[float, ...]] = []
    for i in range(count):
        pos = base + i * stride
        vals.append(tuple(struct.unpack_from(fmt, bin_chunk, pos)))
    return vals


def mat_identity() -> list[list[float]]:
    return [[1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0]]


def mat_mul(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    return [[sum(a[r][k] * b[k][c] for k in range(4)) for c in range(4)] for r in range(4)]


def node_local_matrix(node: dict[str, Any]) -> list[list[float]]:
    if "matrix" in node:
        m = node["matrix"]
        return [[float(m[c * 4 + r]) for c in range(4)] for r in range(4)]

    tx, ty, tz = [float(x) for x in node.get("translation", [0, 0, 0])]
    sx, sy, sz = [float(x) for x in node.get("scale", [1, 1, 1])]
    x, y, z, w = [float(v) for v in node.get("rotation", [0, 0, 0, 1])]

    xx, yy, zz = x * x, y * y, z * z
    xy, xz, yz = x * y, x * z, y * z
    wx, wy, wz = w * x, w * y, w * z

    r = [
        [1 - 2 * (yy + zz), 2 * (xy - wz), 2 * (xz + wy), 0],
        [2 * (xy + wz), 1 - 2 * (xx + zz), 2 * (yz - wx), 0],
        [2 * (xz - wy), 2 * (yz + wx), 1 - 2 * (xx + yy), 0],
        [0, 0, 0, 1],
    ]
    s = [[sx, 0, 0, 0], [0, sy, 0, 0], [0, 0, sz, 0], [0, 0, 0, 1]]
    t = mat_identity()
    t[0][3], t[1][3], t[2][3] = tx, ty, tz
    return mat_mul(t, mat_mul(r, s))


def transform_point(m: list[list[float]], p: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = p
    v = [x, y, z, 1.0]
    out = [sum(m[r][c] * v[c] for c in range(4)) for r in range(4)]
    w = out[3] if abs(out[3]) > 1e-12 else 1.0
    return out[0] / w, out[1] / w, out[2] / w


def world_matrices(gltf: dict[str, Any]) -> list[list[list[float]]]:
    nodes = gltf.get("nodes", [])
    parents: dict[int, int] = {}
    for i, node in enumerate(nodes):
        for child in node.get("children", []):
            parents[int(child)] = i

    cache: dict[int, list[list[float]]] = {}

    def world(i: int) -> list[list[float]]:
        if i in cache:
            return cache[i]
        local = node_local_matrix(nodes[i])
        p = parents.get(i)
        cache[i] = local if p is None else mat_mul(world(p), local)
        return cache[i]

    return [world(i) for i in range(len(nodes))]


def empty_bounds() -> list[list[float]]:
    return [[math.inf, math.inf, math.inf], [-math.inf, -math.inf, -math.inf]]


def add_point(bounds: list[list[float]], p: tuple[float, float, float]) -> None:
    for axis in range(3):
        bounds[0][axis] = min(bounds[0][axis], float(p[axis]))
        bounds[1][axis] = max(bounds[1][axis], float(p[axis]))


def merge_bounds(dst: list[list[float]], src: list[list[float]]) -> None:
    if math.isinf(src[0][0]):
        return
    add_point(dst, tuple(src[0]))
    add_point(dst, tuple(src[1]))


def bounds_dict(bounds: list[list[float]]) -> dict[str, Any] | None:
    if math.isinf(bounds[0][0]):
        return None
    mn = bounds[0]
    mx = bounds[1]
    size = [mx[i] - mn[i] for i in range(3)]
    return {
        "min": [round(v, 8) for v in mn],
        "max": [round(v, 8) for v in mx],
        "size_xyz": [round(v, 8) for v in size],
        "width_x": round(size[0], 8),
        "height_y": round(size[1], 8),
        "depth_z": round(size[2], 8),
    }


def animation_summary(gltf: dict[str, Any], bin_chunk: bytes) -> list[dict[str, Any]]:
    out = []
    for idx, anim in enumerate(gltf.get("animations", [])):
        duration = 0.0
        for sampler in anim.get("samplers", []):
            vals = accessor_values(gltf, bin_chunk, int(sampler["input"]))
            if vals:
                duration = max(duration, max(float(v[0]) for v in vals))
        out.append({
            "index": idx,
            "name": anim.get("name") or f"animation_{idx}",
            "duration_seconds": round(duration, 6),
            "channels": len(anim.get("channels", [])),
        })
    return out


def inspect_model(data: bytes, default_world_height_m: float) -> dict[str, Any]:
    gltf, bin_chunk = parse_glb(data)
    worlds = world_matrices(gltf)
    nodes = gltf.get("nodes", [])
    meshes = gltf.get("meshes", [])
    materials = gltf.get("materials", [])

    scene_bounds = empty_bounds()
    mesh_summaries = []
    total_vertices = 0
    total_triangles = 0

    for node_index, node in enumerate(nodes):
        if "mesh" not in node:
            continue
        mesh_index = int(node["mesh"])
        mesh = meshes[mesh_index]
        mb = empty_bounds()
        vertex_count = 0
        triangle_count = 0
        for prim in mesh.get("primitives", []):
            attrs = prim.get("attributes", {})
            if "POSITION" not in attrs:
                continue
            positions = accessor_values(gltf, bin_chunk, int(attrs["POSITION"]))
            vertex_count += len(positions)
            for p in positions:
                if len(p) >= 3:
                    wp = transform_point(worlds[node_index], (float(p[0]), float(p[1]), float(p[2])))
                    add_point(mb, wp)
                    add_point(scene_bounds, wp)
            mode = int(prim.get("mode", 4))
            if mode == 4:
                if "indices" in prim:
                    triangle_count += int(gltf["accessors"][int(prim["indices"])]["count"]) // 3
                else:
                    triangle_count += len(positions) // 3
        total_vertices += vertex_count
        total_triangles += triangle_count
        mesh_summaries.append({
            "node_index": node_index,
            "node_name": node.get("name", f"node_{node_index}"),
            "mesh_index": mesh_index,
            "mesh_name": mesh.get("name", f"mesh_{mesh_index}"),
            "vertex_count": vertex_count,
            "triangle_count": triangle_count,
            "bounds_native": bounds_dict(mb),
        })

    sb = bounds_dict(scene_bounds)
    if not sb:
        raise ValueError("No POSITION data found in model")

    native_height = float(sb["height_y"])
    if native_height <= 1e-12:
        native_height = max(float(v) for v in sb["size_xyz"])
    world_scale = default_world_height_m / native_height

    joint_indices = sorted({int(j) for skin in gltf.get("skins", []) for j in skin.get("joints", [])})
    joint_set = set(joint_indices)
    segments = []
    joints = []
    for j in joint_indices:
        name = nodes[j].get("name", f"joint_{j}")
        pos = transform_point(worlds[j], (0.0, 0.0, 0.0))
        joints.append({
            "index": j,
            "name": name,
            "rest_position_native": [round(v, 8) for v in pos],
            "rest_position_world_m": [round(v * world_scale, 6) for v in pos],
        })
        for child in nodes[j].get("children", []):
            child = int(child)
            if child not in joint_set:
                continue
            cp = transform_point(worlds[child], (0.0, 0.0, 0.0))
            d = math.dist(pos, cp)
            segments.append({
                "parent_index": j,
                "parent_name": name,
                "child_index": child,
                "child_name": nodes[child].get("name", f"joint_{child}"),
                "length_native": round(d, 8),
                "length_world_m": round(d * world_scale, 6),
            })

    def has_tokens(name: str, tokens: tuple[str, ...]) -> bool:
        n = name.lower().replace("-", "_").replace(" ", "_")
        return any(t in n for t in tokens)

    categories = {
        "head_neck": ("head", "neck"),
        "arms_hands": ("arm", "shoulder", "clav", "hand", "wrist", "elbow"),
        "legs_feet": ("leg", "thigh", "upleg", "calf", "shin", "knee", "foot", "ankle", "toe"),
        "torso_spine": ("spine", "torso", "chest", "hips", "pelvis"),
    }
    category_lengths: dict[str, dict[str, float]] = {}
    for category, tokens in categories.items():
        native = sum(
            float(s["length_native"])
            for s in segments
            if has_tokens(s["parent_name"], tokens) or has_tokens(s["child_name"], tokens)
        )
        category_lengths[category] = {
            "sum_segment_lengths_native": round(native, 8),
            "sum_segment_lengths_world_m": round(native * world_scale, 6),
        }

    head_bounds = empty_bounds()
    for m in mesh_summaries:
        combined = (m["node_name"] + " " + m["mesh_name"]).lower()
        if "head" in combined and m["bounds_native"]:
            b = m["bounds_native"]
            merge_bounds(head_bounds, [list(b["min"]), list(b["max"])])

    head_b = bounds_dict(head_bounds)
    dims_world = {
        "width_m": round(float(sb["width_x"]) * world_scale, 6),
        "height_m": round(float(sb["height_y"]) * world_scale, 6),
        "depth_m": round(float(sb["depth_z"]) * world_scale, 6),
    }

    return {
        "format": "glTF 2.0 / GLB",
        "generator": gltf.get("asset", {}).get("generator"),
        "native_scene_bounds": sb,
        "normalized_dimensions_height_1": {
            "width": round(float(sb["width_x"]) / native_height, 8),
            "height": round(float(sb["height_y"]) / native_height, 8),
            "depth": round(float(sb["depth_z"]) / native_height, 8),
        },
        "default_world_height_m": default_world_height_m,
        "native_to_default_world_scale": round(world_scale, 10),
        "default_world_dimensions": dims_world,
        "head_bounds_native": head_b,
        "head_bounds_default_world_m": (
            {
                "width_m": round(float(head_b["width_x"]) * world_scale, 6),
                "height_m": round(float(head_b["height_y"]) * world_scale, 6),
                "depth_m": round(float(head_b["depth_z"]) * world_scale, 6),
            }
            if head_b
            else None
        ),
        "mesh_count": len(meshes),
        "material_count": len(materials),
        "skin_count": len(gltf.get("skins", [])),
        "joint_count": len(joint_indices),
        "vertex_count": total_vertices,
        "triangle_count": total_triangles,
        "meshes": mesh_summaries,
        "joints": joints,
        "joint_segments": segments,
        "semantic_segment_totals": category_lengths,
        "animations": animation_summary(gltf, bin_chunk),
        "animation_count": len(gltf.get("animations", [])),
        "measurement_notes": [
            "Native GLB coordinates and geometry are the dimensional authority.",
            "Default world metres are a convenience scale derived from the configured default height.",
            "Future creature concepts must preserve the selected base model's normalized ratios unless an explicit deformation is requested.",
            "Joint segment measurements are rest-pose distances. Mesh bounds are exact geometry bounds in the stored GLB rest pose.",
        ],
    }


def svg_template(measurements: dict[str, Any], projection: str, title: str) -> str:
    b = measurements["native_scene_bounds"]
    mn = b["min"]
    mx = b["max"]
    joints = measurements["joints"]
    segments = measurements["joint_segments"]

    if projection == "front":
        ax_h, ax_v = 0, 1
        h_label = "X / width"
        h_size = b["width_x"]
        v_size = b["height_y"]
    else:
        ax_h, ax_v = 2, 1
        h_label = "Z / depth"
        h_size = b["depth_z"]
        v_size = b["height_y"]

    min_h, max_h = mn[ax_h], mx[ax_h]
    min_v, max_v = mn[ax_v], mx[ax_v]
    pad = 120
    W, H = 1200, 1600
    draw_w, draw_h = W - 2 * pad, H - 2 * pad
    span_h = max(max_h - min_h, 1e-9)
    span_v = max(max_v - min_v, 1e-9)
    scale = min(draw_w / span_h, draw_h / span_v)

    def xy(p: list[float]) -> tuple[float, float]:
        x = W / 2 + (p[ax_h] - (min_h + max_h) / 2) * scale
        y = H / 2 - (p[ax_v] - (min_v + max_v) / 2) * scale
        return x, y

    joint_by_index = {j["index"]: j for j in joints}
    lines = []
    for s in segments:
        a = joint_by_index.get(s["parent_index"])
        c = joint_by_index.get(s["child_index"])
        if not a or not c:
            continue
        x1, y1 = xy(a["rest_position_native"])
        x2, y2 = xy(c["rest_position_native"])
        lines.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="#111" stroke-width="5" stroke-linecap="round"/>'
        )

    circles = []
    for j in joints:
        x, y = xy(j["rest_position_native"])
        circles.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="6" fill="#fff" stroke="#111" stroke-width="3"/>')

    top_y = H / 2 - (max_v - (min_v + max_v) / 2) * scale
    bot_y = H / 2 - (min_v - (min_v + max_v) / 2) * scale
    left_x = W / 2 + (min_h - (min_h + max_h) / 2) * scale
    right_x = W / 2 + (max_h - (min_h + max_h) / 2) * scale

    height_m = measurements["default_world_dimensions"]["height_m"]
    horiz_m = (
        measurements["default_world_dimensions"]["width_m"]
        if projection == "front"
        else measurements["default_world_dimensions"]["depth_m"]
    )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<rect width="100%" height="100%" fill="#ffffff"/>
<text x="60" y="64" font-family="sans-serif" font-size="34" font-weight="700">{title}</text>
<text x="60" y="104" font-family="sans-serif" font-size="19">Exact rest-pose proportions from model.glb · {projection} projection</text>
<rect x="{left_x:.2f}" y="{top_y:.2f}" width="{right_x-left_x:.2f}" height="{bot_y-top_y:.2f}" fill="none" stroke="#777" stroke-width="2" stroke-dasharray="8 8"/>
{''.join(lines)}
{''.join(circles)}
<line x1="70" y1="{top_y:.2f}" x2="70" y2="{bot_y:.2f}" stroke="#111" stroke-width="2"/>
<line x1="55" y1="{top_y:.2f}" x2="85" y2="{top_y:.2f}" stroke="#111" stroke-width="2"/>
<line x1="55" y1="{bot_y:.2f}" x2="85" y2="{bot_y:.2f}" stroke="#111" stroke-width="2"/>
<text x="92" y="{(top_y+bot_y)/2:.2f}" font-family="sans-serif" font-size="22">height {height_m:.3f} m default</text>
<line x1="{left_x:.2f}" y1="{H-70}" x2="{right_x:.2f}" y2="{H-70}" stroke="#111" stroke-width="2"/>
<line x1="{left_x:.2f}" y1="{H-85}" x2="{left_x:.2f}" y2="{H-55}" stroke="#111" stroke-width="2"/>
<line x1="{right_x:.2f}" y1="{H-85}" x2="{right_x:.2f}" y2="{H-55}" stroke="#111" stroke-width="2"/>
<text x="{W/2:.2f}" y="{H-28}" text-anchor="middle" font-family="sans-serif" font-size="22">{h_label}: {horiz_m:.3f} m default</text>
</svg>'''


def source_text(src: dict[str, Any], model_sha: str, preview_sha: str) -> str:
    fields = [
        f"ID: {src['id']}",
        f"Display name: {src['display_name']}",
        f"Author: {src['author']}",
        f"License: {src['license']}",
        f"Source page: {src['source_page']}",
    ]
    if src.get("mirror_page"):
        fields.append(f"Mirror page: {src['mirror_page']}")
    fields.extend([
        f"Model URL: {src['model_url']}",
        f"Preview URL: {src['preview_url']}",
        f"License URL: {src['license_url']}",
        f"model.glb SHA256: {model_sha}",
        f"preview.png SHA256: {preview_sha}",
        "",
        "Policy: the downloaded GLB is the dimensional authority for all future texture/reference generation.",
    ])
    return "\n".join(fields) + "\n"


def sync_one(src: dict[str, Any]) -> dict[str, Any]:
    d = OUT / src["id"]
    d.mkdir(parents=True, exist_ok=True)

    model_data = download(src["model_url"], d / "model.glb")
    preview_data = download(src["preview_url"], d / "preview.png")
    license_data = download(src["license_url"], d / "LICENSE.txt")

    measurements = inspect_model(model_data, float(src.get("default_world_height_m", DEFAULT_WORLD_HEIGHT_M)))
    measurements["id"] = src["id"]
    measurements["display_name"] = src["display_name"]
    measurements["license"] = src["license"]
    measurements["author"] = src["author"]
    measurements["tags"] = src.get("tags", [])
    measurements["model_sha256"] = sha256(model_data)
    measurements["preview_sha256"] = sha256(preview_data)

    (d / "measurements.json").write_text(json.dumps(measurements, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (d / "measurement_front.svg").write_text(
        svg_template(measurements, "front", src["display_name"] + " — FRONT"), encoding="utf-8"
    )
    (d / "measurement_side.svg").write_text(
        svg_template(measurements, "side", src["display_name"] + " — SIDE"), encoding="utf-8"
    )
    (d / "SOURCE.txt").write_text(
        source_text(src, measurements["model_sha256"], measurements["preview_sha256"]), encoding="utf-8"
    )

    return {
        "id": src["id"],
        "display_name": src["display_name"],
        "author": src["author"],
        "license": src["license"],
        "tags": src.get("tags", []),
        "model": f"{src['id']}/model.glb",
        "preview": f"{src['id']}/preview.png",
        "measurements": f"{src['id']}/measurements.json",
        "front_template": f"{src['id']}/measurement_front.svg",
        "side_template": f"{src['id']}/measurement_side.svg",
        "default_world_dimensions": measurements["default_world_dimensions"],
        "joint_count": measurements["joint_count"],
        "animation_count": measurements["animation_count"],
        "triangle_count": measurements["triangle_count"],
        "model_sha256": measurements["model_sha256"],
    }


def write_gallery(catalog: list[dict[str, Any]]) -> None:
    lines = [
        "# Character Base Library — Generated Catalog",
        "",
        "This catalog is generated from the exact GLBs stored beside each preview.",
        "Choose a base by screenshot first; its measurement JSON and SVG templates then become the dimensional authority.",
        "",
    ]
    for item in catalog:
        dims = item["default_world_dimensions"]
        lines.extend([
            f"## {item['display_name']}",
            "",
            f"![{item['display_name']}](../assets/character_bases/{item['preview']})",
            "",
            f"- ID: `{item['id']}`",
            f"- License: {item['license']}",
            f"- Stored model: `assets/character_bases/{item['model']}`",
            f"- Default scaled envelope: {dims['width_m']:.3f} m W × {dims['height_m']:.3f} m H × {dims['depth_m']:.3f} m D",
            f"- Rig joints: {item['joint_count']} · animations: {item['animation_count']} · triangles: {item['triangle_count']}",
            f"- Exact measurements: `assets/character_bases/{item['measurements']}`",
            f"- Visual templates: `assets/character_bases/{item['front_template']}`, `assets/character_bases/{item['side_template']}`",
            "",
        ])
    GENERATED_DOC.parent.mkdir(parents=True, exist_ok=True)
    GENERATED_DOC.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    catalog = []
    failures = []
    for src in SOURCES:
        try:
            print(f"[sync] {src['id']}")
            catalog.append(sync_one(src))
        except Exception as exc:
            failures.append({"id": src["id"], "error": repr(exc)})
            print(f"[ERROR] {src['id']}: {exc}")

    (OUT / "catalog.json").write_text(
        json.dumps({"version": 1, "models": catalog, "failures": failures}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_gallery(catalog)

    if failures:
        raise SystemExit("One or more sources failed: " + json.dumps(failures))


if __name__ == "__main__":
    main()
