#!/usr/bin/env python3
"""Bake a CC0 Quaternius glTF zombie into a Vril/Quake MDL v6 Lab model.

The output deliberately mirrors NZ:P's existing zombie frame numbers so the
server AI, hitboxes, damage timing, windows and melee logic remain authoritative.
Only the intact standing zombie presentation changes on ndu_enchanted.
"""
from __future__ import annotations

import base64
import io
import json
import math
import re
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image

if len(sys.argv) != 4:
    raise SystemExit(
        "usage: build_nacht_lab_zombie.py <Zombie_Basic.gltf> <nzp-root> <vril-anorms.h>"
    )

gltf_path = Path(sys.argv[1])
root = Path(sys.argv[2])
anorms_path = Path(sys.argv[3])
doc = json.loads(gltf_path.read_text(encoding="utf-8"))

COMPONENT_DTYPES = {
    5120: np.dtype("<i1"),
    5121: np.dtype("<u1"),
    5122: np.dtype("<i2"),
    5123: np.dtype("<u2"),
    5125: np.dtype("<u4"),
    5126: np.dtype("<f4"),
}
TYPE_COUNTS = {
    "SCALAR": 1,
    "VEC2": 2,
    "VEC3": 3,
    "VEC4": 4,
    "MAT2": 4,
    "MAT3": 9,
    "MAT4": 16,
}

buffers: list[bytes] = []
for buf in doc["buffers"]:
    uri = buf.get("uri", "")
    if not uri.startswith("data:"):
        raise SystemExit("Lab zombie glTF must use embedded data buffers")
    payload = uri.split(",", 1)[1]
    buffers.append(base64.b64decode(payload))


def accessor(index: int) -> np.ndarray:
    a = doc["accessors"][index]
    if "sparse" in a:
        raise SystemExit("Sparse accessors are not supported by the Lab baker")
    bv = doc["bufferViews"][a["bufferView"]]
    dtype = COMPONENT_DTYPES[a["componentType"]]
    comps = TYPE_COUNTS[a["type"]]
    count = a["count"]
    offset = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    stride = bv.get("byteStride", dtype.itemsize * comps)
    raw = buffers[bv.get("buffer", 0)]
    arr = np.ndarray(
        shape=(count, comps),
        dtype=dtype,
        buffer=raw,
        offset=offset,
        strides=(stride, dtype.itemsize),
    ).copy()
    if comps == 1:
        return arr[:, 0]
    return arr


def quat_matrix(q: np.ndarray) -> np.ndarray:
    x, y, z, w = [float(v) for v in q]
    n = math.sqrt(x*x + y*y + z*z + w*w)
    if n <= 1e-12:
        return np.eye(4, dtype=np.float64)
    x, y, z, w = x/n, y/n, z/n, w/n
    xx, yy, zz = x*x, y*y, z*z
    xy, xz, yz = x*y, x*z, y*z
    wx, wy, wz = w*x, w*y, w*z
    m = np.eye(4, dtype=np.float64)
    m[:3, :3] = [
        [1 - 2*(yy+zz), 2*(xy-wz), 2*(xz+wy)],
        [2*(xy+wz), 1 - 2*(xx+zz), 2*(yz-wx)],
        [2*(xz-wy), 2*(yz+wx), 1 - 2*(xx+yy)],
    ]
    return m


def trs_matrix(t: np.ndarray, r: np.ndarray, scale: np.ndarray) -> np.ndarray:
    m = quat_matrix(r)
    m[:3, :3] = m[:3, :3] @ np.diag(scale.astype(np.float64))
    m[:3, 3] = t
    return m


nodes = doc["nodes"]
parents = [-1] * len(nodes)
for parent, node in enumerate(nodes):
    for child in node.get("children", []):
        parents[child] = parent

base_t: list[np.ndarray] = []
base_r: list[np.ndarray] = []
base_s: list[np.ndarray] = []
base_matrix: list[np.ndarray | None] = []
for node in nodes:
    base_t.append(np.asarray(node.get("translation", [0, 0, 0]), dtype=np.float64))
    base_r.append(np.asarray(node.get("rotation", [0, 0, 0, 1]), dtype=np.float64))
    base_s.append(np.asarray(node.get("scale", [1, 1, 1]), dtype=np.float64))
    if "matrix" in node:
        base_matrix.append(np.asarray(node["matrix"], dtype=np.float64).reshape(4, 4).T)
    else:
        base_matrix.append(None)


def build_animation(anim: dict) -> dict[int, dict[str, tuple[np.ndarray, np.ndarray, str]]]:
    channels: dict[int, dict[str, tuple[np.ndarray, np.ndarray, str]]] = {}
    for ch in anim.get("channels", []):
        target = ch["target"]
        node = target.get("node")
        path = target.get("path")
        if node is None or path not in ("translation", "rotation", "scale"):
            continue
        samp = anim["samplers"][ch["sampler"]]
        times = accessor(samp["input"]).astype(np.float64)
        values = accessor(samp["output"]).astype(np.float64)
        interpolation = samp.get("interpolation", "LINEAR")
        if interpolation == "CUBICSPLINE":
            values = values.reshape(len(times), 3, -1)[:, 1, :]
            interpolation = "LINEAR"
        channels.setdefault(node, {})[path] = (times, values, interpolation)
    return channels


animations = {a.get("name", f"anim_{i}"): (a, build_animation(a))
              for i, a in enumerate(doc.get("animations", []))}
required_anims = {
    "Crawl", "Death", "HitReact", "Idle", "Idle_Attack",
    "Jump", "Jump_Idle", "Jump_Land", "Punch", "Run", "Walk",
}
missing = required_anims - set(animations)
if missing:
    raise SystemExit("Zombie source is missing required animations: " + ", ".join(sorted(missing)))


def animation_duration(name: str) -> float:
    _, channels = animations[name]
    mx = 0.0
    for paths in channels.values():
        for times, _, _ in paths.values():
            if len(times):
                mx = max(mx, float(times[-1]))
    return max(mx, 1.0 / 30.0)


def sample_track(times: np.ndarray, values: np.ndarray, t: float,
                 interpolation: str, rotation: bool) -> np.ndarray:
    if len(times) == 1 or t <= times[0]:
        return values[0].copy()
    if t >= times[-1]:
        return values[-1].copy()
    hi = int(np.searchsorted(times, t, side="right"))
    lo = max(0, hi - 1)
    if interpolation == "STEP" or times[hi] <= times[lo]:
        return values[lo].copy()
    alpha = (t - times[lo]) / (times[hi] - times[lo])
    a = values[lo].astype(np.float64)
    b = values[hi].astype(np.float64)
    if rotation:
        if float(np.dot(a, b)) < 0:
            b = -b
        out = a * (1.0 - alpha) + b * alpha
        n = np.linalg.norm(out)
        return out / n if n > 1e-12 else a
    return a * (1.0 - alpha) + b * alpha


def world_matrices(anim_name: str, t: float) -> list[np.ndarray]:
    _, channels = animations[anim_name]
    locals_: list[np.ndarray] = []
    for i in range(len(nodes)):
        tr = base_t[i].copy()
        ro = base_r[i].copy()
        sc = base_s[i].copy()
        paths = channels.get(i, {})
        if "translation" in paths:
            times, vals, interp = paths["translation"]
            tr = sample_track(times, vals, t, interp, False)
        if "rotation" in paths:
            times, vals, interp = paths["rotation"]
            ro = sample_track(times, vals, t, interp, True)
        if "scale" in paths:
            times, vals, interp = paths["scale"]
            sc = sample_track(times, vals, t, interp, False)
        if base_matrix[i] is not None and not paths:
            locals_.append(base_matrix[i].copy())
        else:
            locals_.append(trs_matrix(tr, ro, sc))

    worlds: list[np.ndarray | None] = [None] * len(nodes)

    def resolve(i: int) -> np.ndarray:
        if worlds[i] is not None:
            return worlds[i]  # type: ignore[return-value]
        p = parents[i]
        worlds[i] = locals_[i] if p < 0 else resolve(p) @ locals_[i]
        return worlds[i]  # type: ignore[return-value]

    for i in range(len(nodes)):
        resolve(i)
    return [m for m in worlds if m is not None]


skin = doc["skins"][0]
joints = skin["joints"]
ibm = accessor(skin["inverseBindMatrices"]).astype(np.float64).reshape(-1, 4, 4)
ibm = np.transpose(ibm, (0, 2, 1))

mesh_records = []
vertex_base = 0
all_uv = []
all_indices = []
all_dominant_joint_names: list[str] = []
for node_index, node in enumerate(nodes):
    if "mesh" not in node or node.get("skin") != 0:
        continue
    mesh = doc["meshes"][node["mesh"]]
    for prim in mesh["primitives"]:
        attrs = prim["attributes"]
        pos = accessor(attrs["POSITION"]).astype(np.float64)
        nrm = accessor(attrs["NORMAL"]).astype(np.float64)
        uv = accessor(attrs["TEXCOORD_0"]).astype(np.float64)
        jnt = accessor(attrs["JOINTS_0"]).astype(np.int32)
        wgt = accessor(attrs["WEIGHTS_0"]).astype(np.float64)
        idx = accessor(prim["indices"]).astype(np.int32)
        if len(idx) % 3:
            raise SystemExit("Zombie primitive index count is not divisible by 3")
        mesh_records.append((node_index, pos, nrm, jnt, wgt))
        all_uv.append(uv)
        all_indices.append(idx.reshape(-1, 3) + vertex_base)

        # Keep the dominant skeleton joint for each rendered vertex. We later
        # use this to bake real no-head/no-arm mesh variants while retaining
        # NZ:P's proven invisible damage entities and gameplay rules.
        dominant_slots = np.argmax(wgt, axis=1)
        for vi, slot in enumerate(dominant_slots):
            skin_joint = int(jnt[vi, int(slot)])
            node_id = int(joints[skin_joint])
            all_dominant_joint_names.append(nodes[node_id].get("name", ""))

        vertex_base += len(pos)

uvs = np.concatenate(all_uv, axis=0)
triangles = np.concatenate(all_indices, axis=0)
numverts = len(uvs)
numtris = len(triangles)
if len(all_dominant_joint_names) != numverts:
    raise SystemExit("Dominant-joint table does not match Lab zombie vertex count")
if numverts > 8192 or numtris > 8192:
    raise SystemExit(f"Lab zombie exceeds Android alias budget: {numverts} verts / {numtris} tris")


def bake_pose(anim_name: str, t: float) -> tuple[np.ndarray, np.ndarray]:
    worlds = world_matrices(anim_name, t)
    joint_mats = [worlds[joint] @ ibm[k] for k, joint in enumerate(joints)]
    out_pos = []
    out_nrm = []
    for _, pos, nrm, jnt, wgt in mesh_records:
        hp = np.concatenate([pos, np.ones((len(pos), 1), dtype=np.float64)], axis=1)
        p_acc = np.zeros((len(pos), 3), dtype=np.float64)
        n_acc = np.zeros((len(pos), 3), dtype=np.float64)
        for slot in range(4):
            weights = wgt[:, slot]
            active = weights > 1e-8
            if not np.any(active):
                continue
            for joint_slot in np.unique(jnt[active, slot]):
                mask = active & (jnt[:, slot] == joint_slot)
                mat = joint_mats[int(joint_slot)]
                p = (mat @ hp[mask].T).T[:, :3]
                nn = (mat[:3, :3] @ nrm[mask].T).T
                p_acc[mask] += p * weights[mask, None]
                n_acc[mask] += nn * weights[mask, None]
        lengths = np.linalg.norm(n_acc, axis=1)
        lengths[lengths < 1e-12] = 1.0
        n_acc /= lengths[:, None]
        out_pos.append(p_acc)
        out_nrm.append(n_acc)
    return np.concatenate(out_pos), np.concatenate(out_nrm)


# glTF is Y-up and conventionally faces +Z. Map +Z to Quake +X
# (forward), +X to Quake +Y (left), and +Y to Quake +Z (up).
# The previous -Z mapping mirrored the character 180 degrees, which is why
# some Lab zombies visibly walked toward the player while looking backward.
AXIS = np.array([[0.0, 0.0, 1.0],
                 [1.0, 0.0, 0.0],
                 [0.0, 1.0, 0.0]], dtype=np.float64)
MODEL_SCALE = 52.0
# Preserve NZ:P's standing height but tighten the cartoon-wide source mesh.
# Forward depth and shoulder width are tuned separately so the presentation
# tracks the legacy damage proxies without changing the movement hull.
MODEL_FORWARD_SCALE = 0.78
MODEL_LATERAL_SCALE = 0.60


def convert_axes(pos: np.ndarray, normals: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    p = (pos @ AXIS.T) * MODEL_SCALE
    p[:, 0] *= MODEL_FORWARD_SCALE
    p[:, 1] *= MODEL_LATERAL_SCALE
    n = normals @ AXIS.T
    lengths = np.linalg.norm(n, axis=1)
    lengths[lengths < 1e-12] = 1.0
    return p, n / lengths[:, None]


def sample_times(name: str, count: int, phase: float = 0.0,
                 loop: bool = True) -> list[float]:
    duration = animation_duration(name)
    if count <= 1:
        return [phase * duration]
    if loop:
        return [((i / count + phase) % 1.0) * duration for i in range(count)]
    return [(i / (count - 1)) * duration for i in range(count)]


layout: list[tuple[int, int, str, float, bool]] = [
    (0, 12, "Idle", 0.0, True),
    (13, 24, "HitReact", 0.0, False),
    (25, 36, "Idle", 0.45, True),
    (37, 52, "Walk", 0.0, True),
    (53, 66, "Walk", 0.33, True),
    (67, 82, "Walk", 0.66, True),
    (83, 90, "Run", 0.0, True),
    (91, 101, "Run", 0.35, True),
    (102, 112, "Punch", 0.0, False),
    (113, 116, "Jump", 0.0, False),
    (117, 118, "Jump_Idle", 0.0, True),
    (119, 122, "Jump_Land", 0.0, False),
    (123, 133, "Death", 0.0, False),
    (134, 138, "Death", 0.0, False),
    (139, 148, "Death", 0.0, False),
    (149, 152, "Jump_Idle", 0.0, True),
    (153, 159, "Jump_Land", 0.0, False),
    (160, 180, "HitReact", 0.0, False),
    (181, 191, "Idle_Attack", 0.0, False),
    (192, 201, "Idle_Attack", 0.25, False),
    (202, 210, "Punch", 0.0, False),
]
if layout[0][0] != 0 or layout[-1][1] != 210:
    raise SystemExit("Frame layout must cover 0..210")

frames_pos: list[np.ndarray] = [None] * 211  # type: ignore[list-item]
frames_nrm: list[np.ndarray] = [None] * 211  # type: ignore[list-item]
for start, end, anim, phase, loop in layout:
    count = end - start + 1
    for out_idx, t in enumerate(sample_times(anim, count, phase, loop), start=start):
        p, n = bake_pose(anim, t)
        p, n = convert_axes(p, n)
        frames_pos[out_idx] = p
        frames_nrm[out_idx] = n

# Match NZ:P's standing entity convention: idle feet at roughly Z=-32.
idle_min_z = float(frames_pos[0][:, 2].min())
z_offset = -32.0 - idle_min_z
for p in frames_pos:
    p[:, 2] += z_offset

# Classify the animated surface into removable anatomical regions. The source
# skeleton names are preferred; a conservative rest-pose fallback catches
# clothing/skin vertices weighted mostly to torso joints at the seams.
def joint_part(name: str) -> str:
    raw = name.lower()
    compact = re.sub(r"[^a-z0-9]", "", raw)
    if "head" in compact or "neck" in compact:
        return "head"

    armish = any(token in compact for token in ("arm", "forearm", "hand", "shoulder"))
    if armish:
        if "left" in compact or compact.endswith(("l", "01l", "02l")):
            return "larm"
        if "right" in compact or compact.endswith(("r", "01r", "02r")):
            return "rarm"
    return "body"


vertex_parts = np.asarray([joint_part(name) for name in all_dominant_joint_names], dtype=object)
rest = frames_pos[0]
body_mask = vertex_parts == "body"

# Head fallback: upper central portion of the standing character.
head_fallback = body_mask & (rest[:, 2] > 14.0) & (np.abs(rest[:, 1]) < 17.0)
vertex_parts[head_fallback] = "head"

# Arm fallback: lateral upper/mid-body geometry. With the corrected axis map,
# anatomical left is +Y and anatomical right is -Y in Quake coordinates.
body_mask = vertex_parts == "body"
left_fallback = body_mask & (rest[:, 1] > 8.0) & (rest[:, 2] > -13.0) & (rest[:, 2] < 24.0)
vertex_parts[left_fallback] = "larm"
body_mask = vertex_parts == "body"
right_fallback = body_mask & (rest[:, 1] < -8.0) & (rest[:, 2] > -13.0) & (rest[:, 2] < 24.0)
vertex_parts[right_fallback] = "rarm"

triangle_parts: list[str] = []
for tri in triangles:
    labels = [str(vertex_parts[int(v)]) for v in tri]
    counts = {part: labels.count(part) for part in ("head", "larm", "rarm")}
    part = max(counts, key=counts.get)
    triangle_parts.append(part if counts[part] >= 2 else "body")
triangle_parts_np = np.asarray(triangle_parts, dtype=object)

# Parse Quake's canonical 162 normal directions and map each baked vertex.
norm_text = anorms_path.read_text(encoding="utf-8")
normal_rows = re.findall(
    r"\{\s*([-+0-9.eE]+)\s*,\s*([-+0-9.eE]+)\s*,\s*([-+0-9.eE]+)\s*\}",
    norm_text,
)
quake_normals = np.asarray([[float(x), float(y), float(z)] for x, y, z in normal_rows],
                           dtype=np.float64)
if len(quake_normals) != 162:
    raise SystemExit(f"Expected 162 Quake alias normals, found {len(quake_normals)}")
quake_normals /= np.linalg.norm(quake_normals, axis=1)[:, None]

normal_indices: list[np.ndarray] = []
for n in frames_nrm:
    # Chunk the dot product so CI memory remains bounded.
    ids = np.empty(len(n), dtype=np.uint8)
    for begin in range(0, len(n), 1024):
        block = n[begin:begin+1024]
        ids[begin:begin+len(block)] = np.argmax(block @ quake_normals.T, axis=1).astype(np.uint8)
    normal_indices.append(ids)

stack = np.concatenate(frames_pos, axis=0)
mins = stack.min(axis=0)
maxs = stack.max(axis=0)
scale = (maxs - mins) / 255.0
scale[scale < 1e-7] = 1.0
origin = mins

# Extract the embedded atlas. The original Quaternius material is intentionally
# low-poly/stylized, so build four higher-resolution horror treatments instead
# of stretching the same flat 512px look over every zombie.
image = doc["images"][0]
if "bufferView" not in image:
    raise SystemExit("Zombie atlas must be embedded in the glTF")
bv = doc["bufferViews"][image["bufferView"]]
raw = buffers[bv.get("buffer", 0)]
bo = bv.get("byteOffset", 0)
atlas_bytes = raw[bo:bo + bv["byteLength"]]
source_atlas = Image.open(io.BytesIO(atlas_bytes)).convert("RGBA")
source_skinw, source_skinh = source_atlas.size
if source_skinw <= 0 or source_skinh <= 0 or source_skinw > 4096 or source_skinh > 4096:
    raise SystemExit(f"Unexpected zombie atlas size: {source_atlas.size}")

external_skinw = min(1024, source_skinw * 2)
external_skinh = min(1024, source_skinh * 2)

# Quake MDL's legacy loader caps the embedded skin height at 480. The embedded
# indexed skins are crash-safe fallbacks; Vril renders the external TGAs.
fallback_scale = min(1.0, 480.0 / max(external_skinw, external_skinh))
skinw = max(16, int(round(external_skinw * fallback_scale / 4.0)) * 4)
skinh = max(16, int(round(external_skinh * fallback_scale / 4.0)) * 4)
skinw = min(skinw, 480)
skinh = min(skinh, 480)
SKIN_COUNT = 4

out_dir = root / "models" / "xziel_lab"
out_dir.mkdir(parents=True, exist_ok=True)


def make_horror_skin(source: Image.Image, variant: int) -> Image.Image:
    im = source.resize((external_skinw, external_skinh), Image.Resampling.LANCZOS)
    arr = np.asarray(im).astype(np.float32)
    rgb = arr[:, :, :3]
    alpha = arr[:, :, 3:4]

    gray = (
        rgb[:, :, 0] * 0.299
        + rgb[:, :, 1] * 0.587
        + rgb[:, :, 2] * 0.114
    )
    saturations = (0.58, 0.46, 0.54, 0.40)
    saturation = saturations[variant]
    rgb = gray[:, :, None] * (1.0 - saturation) + rgb * saturation

    # Four corpse palettes: sickly, ashen, bruised, and decayed. Keep values
    # lifted enough to read under Nacht's dark lighting.
    tints = (
        (0.88, 1.00, 0.76),
        (0.86, 0.91, 0.88),
        (0.96, 0.79, 0.77),
        (0.76, 0.88, 0.71),
    )
    rgb *= np.asarray(tints[variant], dtype=np.float32)[None, None, :]

    rng = np.random.default_rng(7319 + variant * 101)
    noise = rng.normal(0.0, 5.5, (external_skinh, external_skinw, 1)).astype(np.float32)
    rgb += noise

    # Broad deterministic mottling adds readable skin breakup without changing
    # UVs or requiring another runtime material system.
    small_h = max(8, external_skinh // 32)
    small_w = max(8, external_skinw // 32)
    m = rng.uniform(0.0, 255.0, (small_h, small_w)).astype(np.uint8)
    mimg = Image.fromarray(m, mode="L").resize(
        (external_skinw, external_skinh), Image.Resampling.BILINEAR
    ).filter(Image.Filter.GaussianBlur(5.0)) if False else None

    # PIL exposes filters in ImageFilter; import locally to keep startup simple.
    from PIL import ImageEnhance, ImageFilter, ImageDraw
    mimg = Image.fromarray(m, mode="L").resize(
        (external_skinw, external_skinh), Image.Resampling.BILINEAR
    ).filter(ImageFilter.GaussianBlur(5.0))
    mottling = (np.asarray(mimg).astype(np.float32) / 255.0 - 0.5)[:, :, None] * 24.0
    rgb += mottling

    rgb = np.clip(rgb, 0.0, 255.0) / 255.0
    rgb = np.power(rgb, 0.90) * 255.0
    rgba = np.concatenate([np.clip(rgb, 0.0, 255.0), alpha], axis=2).astype(np.uint8)
    out = Image.fromarray(rgba, mode="RGBA")

    # Procedural dried-blood/grime streaks. These are deliberately irregular,
    # subtle, and deterministic so each of the four stock skin slots reads as
    # a different corpse rather than a flat recolor.
    overlay = Image.new("RGBA", out.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    stain_palette = (
        (70, 7, 6, 62),
        (92, 15, 10, 48),
        (45, 18, 12, 52),
        (28, 22, 14, 42),
    )
    for i in range(30):
        x = int(rng.integers(0, external_skinw))
        y = int(rng.integers(0, external_skinh))
        length = int(rng.integers(max(8, external_skinh // 80), max(20, external_skinh // 18)))
        width = int(rng.integers(2, max(3, external_skinw // 140)))
        col = stain_palette[(i + variant) % len(stain_palette)]
        draw.line((x, y, x + int(rng.integers(-10, 11)), min(external_skinh - 1, y + length)),
                  fill=col, width=width)

    out = Image.alpha_composite(out, overlay)
    out = ImageEnhance.Contrast(out).enhance(1.16)
    out = ImageEnhance.Sharpness(out).enhance(1.45)
    return out


horror_skins = [make_horror_skin(source_atlas, i) for i in range(SKIN_COUNT)]

# Prepare quantized frame payload once; every dismemberment variant shares the
# same skeleton, frame indices and vertices. Only the triangle list differs.
stack = np.concatenate(frames_pos, axis=0)
mins = stack.min(axis=0)
maxs = stack.max(axis=0)
scale = (maxs - mins) / 255.0
scale[scale < 1e-7] = 1.0
origin = mins
boundingradius = float(
    np.max(np.linalg.norm(stack - np.array([0.0, 0.0, 0.0]), axis=1))
)

packed_frames: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
for p, nidx in zip(frames_pos, normal_indices):
    q = np.rint((p - origin) / scale).clip(0, 255).astype(np.uint8)
    packed = np.empty((numverts, 4), dtype=np.uint8)
    packed[:, :3] = q
    packed[:, 3] = nidx
    packed_frames.append((q.min(axis=0), q.max(axis=0), packed))

variant_removals = {
    "zombie_basic.mdl": frozenset(),
    "zombie_basic_nohead.mdl": frozenset(("head",)),
    "zombie_basic_nolarm.mdl": frozenset(("larm",)),
    "zombie_basic_normarm.mdl": frozenset(("rarm",)),
    "zombie_basic_nohead_nolarm.mdl": frozenset(("head", "larm")),
    "zombie_basic_nohead_normarm.mdl": frozenset(("head", "rarm")),
    "zombie_basic_noarms.mdl": frozenset(("larm", "rarm")),
    "zombie_basic_nohead_noarms.mdl": frozenset(("head", "larm", "rarm")),
}
variant_triangle_counts: dict[str, int] = {}


def write_variant(filename: str, removed: frozenset[str]) -> None:
    keep = np.asarray([part not in removed for part in triangle_parts_np], dtype=bool)
    variant_triangles = triangles[keep]
    if len(variant_triangles) <= 0:
        raise SystemExit(f"Lab variant {filename} removed every triangle")
    if len(variant_triangles) > 8192:
        raise SystemExit(f"Lab variant {filename} exceeds triangle budget")
    variant_triangle_counts[filename] = int(len(variant_triangles))

    mdl_path = out_dir / filename
    header = struct.pack(
        "<4si3f3ff3f8if",
        b"IDPO", 6,
        *[float(v) for v in scale],
        *[float(v) for v in origin],
        boundingradius,
        0.0, 0.0, 0.0,
        SKIN_COUNT, skinw, skinh, numverts, len(variant_triangles), 211, 0, 0,
        0.0,
    )

    with mdl_path.open("wb") as f:
        f.write(header)

        # Four tiny indexed fallbacks matching the four external horror skins.
        for _ in range(SKIN_COUNT):
            f.write(struct.pack("<i", 0))
            f.write(bytes(skinw * skinh))

        for uv in uvs:
            u = float(uv[0] % 1.0)
            v = float(uv[1] % 1.0)
            ss = int(round(u * (skinw - 1)))
            tt = int(round((1.0 - v) * (skinh - 1)))
            f.write(struct.pack("<3i", 0, ss, tt))

        for tri in variant_triangles:
            f.write(struct.pack("<4i", 1, int(tri[0]), int(tri[1]), int(tri[2])))

        for frame_index, (qmin, qmax, packed) in enumerate(packed_frames):
            f.write(struct.pack("<i", 0))
            f.write(bytes([int(qmin[0]), int(qmin[1]), int(qmin[2]), 0]))
            f.write(bytes([int(qmax[0]), int(qmax[1]), int(qmax[2]), 0]))
            name = f"xz{frame_index:03d}".encode("ascii")[:15]
            f.write(name + bytes(16 - len(name)))
            f.write(packed.tobytes())

    for skin_index, skin_image in enumerate(horror_skins):
        skin_image.save(out_dir / f"{filename}_{skin_index}.tga", format="TGA", rle=True)


for filename, removed in variant_removals.items():
    write_variant(filename, removed)

part_counts = {
    part: int(np.count_nonzero(triangle_parts_np == part))
    for part in ("body", "head", "larm", "rarm")
}

# Machine-readable metadata makes CI/review catch accidental source/model drift.
meta = {
    "source": "agentkaerf/FreeModels / Quaternius Zombie Apocalypse Kit",
    "source_commit": "db3df04d1e4714298a09510b26fb6de6645138a2",
    "source_asset": "Zombie_Basic.gltf",
    "license": "CC0-1.0",
    "format": "Quake MDL v6",
    "vertices": numverts,
    "triangles": numtris,
    "frames": 211,
    "skins": SKIN_COUNT,
    "source_skin": [source_skinw, source_skinh],
    "mdl_skin": [skinw, skinh],
    "external_skin": [external_skinw, external_skinh],
    "model_scale": MODEL_SCALE,
    "model_forward_scale": MODEL_FORWARD_SCALE,
    "model_lateral_scale": MODEL_LATERAL_SCALE,
    "idle_z_offset": z_offset,
    "triangle_parts": part_counts,
    "variants": variant_triangle_counts,
    "animations": sorted(animations.keys()),
}
(out_dir / "zombie_basic.json").write_text(
    json.dumps(meta, indent=2) + "\n", encoding="utf-8"
)

print(
    f"Built Lab zombie family: {numverts} verts / {numtris} source tris / "
    f"211 frames / {SKIN_COUNT} horror skins / {external_skinw}x{external_skinh}; "
    f"parts={part_counts}; variants={variant_triangle_counts}"
)
