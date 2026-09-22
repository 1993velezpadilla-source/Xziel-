#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import os
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFile
from scipy import ndimage
import trimesh
import xatlas

SRC_DIR = Path(os.environ.get("LLORONA_HUNYUAN_DIR", "in/hunyuan"))
REF_DIR = Path(os.environ.get("LLORONA_REF_DIR", "assets/characters/llorona/reference"))
OUT = Path(os.environ.get("LLORONA_BAKE_OUT", "out/llorona-perpixel"))
TARGET_FACES = int(os.environ.get("LLORONA_TARGET_FACES", "0"))
TEX_SIZE = int(os.environ.get("LLORONA_TEXTURE_SIZE", "2048"))
TARGET_HEIGHT_M = float(os.environ.get("LLORONA_HEIGHT_M", "1.72"))
REQUIRE_DETAILS = os.environ.get("LLORONA_REQUIRE_DETAILS", "1").lower() not in {"0", "false", "no"}
STRICT_QA = os.environ.get("LLORONA_STRICT_QA", "1").lower() not in {"0", "false", "no"}
CHUNK_TEXELS = int(os.environ.get("LLORONA_CHUNK_TEXELS", "180000"))

QA_FACE_RATIO_MIN = float(os.environ.get("LLORONA_QA_FACE_RATIO_MIN", "0.12"))
QA_FACE_LAP_MIN = float(os.environ.get("LLORONA_QA_FACE_LAP_MIN", "14.0"))
QA_ROSARY_RATIO_MIN = float(os.environ.get("LLORONA_QA_ROSARY_RATIO_MIN", "0.10"))
QA_ROSARY_LAP_MIN = float(os.environ.get("LLORONA_QA_ROSARY_LAP_MIN", "9.0"))
QA_DRESS_RATIO_MIN = float(os.environ.get("LLORONA_QA_DRESS_RATIO_MIN", "0.10"))
QA_DRESS_LAP_MIN = float(os.environ.get("LLORONA_QA_DRESS_LAP_MIN", "8.0"))
QA_DRESS_STD_RATIO_MIN = float(os.environ.get("LLORONA_QA_DRESS_STD_RATIO_MIN", "0.16"))
QA_SEAM_MEAN_MAX = float(os.environ.get("LLORONA_QA_SEAM_MEAN_MAX", "16.0"))
QA_SEAM_P95_MAX = float(os.environ.get("LLORONA_QA_SEAM_P95_MAX", "48.0"))

OUT.mkdir(parents=True, exist_ok=True)


def fail(msg: str) -> None:
    print(f"::error::{msg}")
    raise SystemExit(1)


def find_under(root: Path, names: tuple[str, ...], required: bool = True) -> Path | None:
    for name in names:
        p = root / name
        if p.is_file() and p.stat().st_size > 256:
            return p
    for name in names:
        for p in (root.rglob(name) if root.exists() else []):
            if p.is_file() and p.stat().st_size > 256:
                return p
    if required:
        fail(f"Missing input under {root}: one of {names}")
    return None


def image_names(stem: str) -> tuple[str, ...]:
    out = []
    for ext in ("png", "jpg", "jpeg"):
        out += [
            f"{stem}.{ext}",
            f"{stem}_detail.{ext}",
            f"detail_{stem}.{ext}",
            f"{stem}_closeup.{ext}",
            f"{stem}_close_up.{ext}",
        ]
    return tuple(out)


def find_detail(stem: str) -> Path | None:
    p = find_under(REF_DIR, image_names(stem), required=False)
    if p:
        return p
    if not REF_DIR.exists():
        return None
    ranked = []
    for candidate in REF_DIR.rglob("*"):
        if not candidate.is_file() or candidate.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            continue
        name = candidate.stem.lower().replace("-", "_")
        if stem not in name:
            continue
        score = 10 if any(tag in name for tag in ("detail", "close", "crop", "ref")) else 0
        ranked.append((score, candidate))
    return max(ranked, key=lambda x: x[0])[1] if ranked else None


def load_rgb(path: Path) -> np.ndarray:
    # Older repo JPEG refs can have recoverable truncated streams. Normalize them
    # exactly like the successful Hunyuan input pipeline instead of rejecting them.
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    im = Image.open(path)
    im.load()
    return np.asarray(im.convert("RGB"), dtype=np.float32)


def bilinear(im: np.ndarray, u: np.ndarray, v: np.ndarray) -> np.ndarray:
    h, w = im.shape[:2]
    x = np.clip(u, 0.0, 1.0) * (w - 1)
    y = np.clip(v, 0.0, 1.0) * (h - 1)
    x0, y0 = np.floor(x).astype(np.int32), np.floor(y).astype(np.int32)
    x1, y1 = np.minimum(x0 + 1, w - 1), np.minimum(y0 + 1, h - 1)
    fx, fy = (x - x0)[:, None], (y - y0)[:, None]
    a = im[y0, x0] * (1.0 - fx) + im[y0, x1] * fx
    b = im[y1, x0] * (1.0 - fx) + im[y1, x1] * fx
    return a * (1.0 - fy) + b * fy


def feather_interval(x: np.ndarray, lo: float, hi: float, amount: float) -> np.ndarray:
    f = max((hi - lo) * amount, 1e-6)
    return np.clip((x - lo) / f, 0.0, 1.0) * np.clip((hi - x) / f, 0.0, 1.0)


mesh_path = find_under(SRC_DIR, ("llorona_hunyuan_mv_hq.glb",))
base_paths = {}
for view in ("front", "back", "left", "right"):
    p = find_under(REF_DIR, image_names(view), required=False)
    if p is None:
        p = find_under(SRC_DIR, (f"{view}.png", f"{view}.jpg", f"{view}.jpeg"))
    base_paths[view] = p

detail_paths = {
    "face": find_detail("face"),
    "rosary": find_detail("rosary"),
    "dress": find_detail("dress"),
}
missing = [k for k, v in detail_paths.items() if v is None]
if REQUIRE_DETAILS and missing:
    fail("Refined HQ close-ups required; missing: " + ", ".join(missing))

scene = trimesh.load(mesh_path, force="scene")
if not scene.geometry:
    fail("Hunyuan GLB has no geometry")
src = max(scene.geometry.values(), key=lambda g: len(g.faces)).copy()
src.remove_unreferenced_vertices()
raw_vertices, raw_faces = len(src.vertices), len(src.faces)

keep = np.asarray(src.unique_faces(), dtype=bool) & np.asarray(src.nondegenerate_faces(), dtype=bool)
src.update_faces(keep)
src.remove_unreferenced_vertices()
clean_master = src.copy()
clean_vertices, clean_faces = len(src.vertices), len(src.faces)
clean_components = len(src.split(only_watertight=False))

if TARGET_FACES > 0 and len(src.faces) > TARGET_FACES:
    candidate = src.simplify_quadric_decimation(face_count=TARGET_FACES, aggression=5)
    candidate.remove_unreferenced_vertices()
    good = np.asarray(candidate.unique_faces(), dtype=bool) & np.asarray(candidate.nondegenerate_faces(), dtype=bool)
    candidate.update_faces(good)
    candidate.remove_unreferenced_vertices()
    sane = len(candidate.vertices) >= 10000 and len(candidate.faces) >= min(60000, int(TARGET_FACES * 0.60))
    src = candidate if sane else clean_master

if len(src.vertices) < 10000 or len(src.faces) < 60000:
    fail(f"Mesh topology collapsed: {len(src.vertices)} verts / {len(src.faces)} faces")

V = np.asarray(src.vertices, dtype=np.float64)
F = np.asarray(src.faces, dtype=np.uint32)
N = np.asarray(src.vertex_normals, dtype=np.float64)
mins0, maxs0 = V.min(0), V.max(0)
height0 = float((maxs0 - mins0)[1])
if height0 <= 1e-6:
    fail("Degenerate Hunyuan bounds")
V = (V - np.array([0.0, mins0[1], 0.0])) * (TARGET_HEIGHT_M / height0)
mins, maxs = V.min(0), V.max(0)
extent = maxs - mins

images = {k: load_rgb(v) for k, v in base_paths.items()}
detail_images = {k: load_rgb(v) for k, v in detail_paths.items() if v is not None}

# Ref preflight. The old back.jpg has a recoverable JPEG stream but a large flat
# truncated tail; a strict HQ run must reject that before spending minutes on 4K.
reference_quality = {}
bad_refs = []
for name, im in images.items():
    h = im.shape[0]
    row_std = im.reshape(h, -1).std(axis=1)
    tail = row_std[int(h * 0.65):]
    flat_tail = float(np.mean(tail < 2.0)) if len(tail) else 1.0
    reference_quality[name] = {
        "width": int(im.shape[1]),
        "height": int(im.shape[0]),
        "std": float(im.std()),
        "flatTailFraction": flat_tail,
    }
    if flat_tail > 0.18:
        bad_refs.append(f"{name}: flatTailFraction={flat_tail:.3f}")
(OUT / "reference_quality.json").write_text(json.dumps(reference_quality, indent=2), encoding="utf-8")
if STRICT_QA and bad_refs:
    fail("Refined base reference preflight rejected: " + " | ".join(bad_refs))

view_cfg = {
    "front": (np.array([0.0, 0.0, 1.0]), "x", False),
    "back": (np.array([0.0, 0.0, -1.0]), "x", True),
    "left": (np.array([1.0, 0.0, 0.0]), "z", True),
    "right": (np.array([-1.0, 0.0, 0.0]), "z", False),
}
view_names = ("front", "back", "left", "right")

detail_specs = {
    "dress": {"x": (0.14, 0.86), "y": (0.06, 0.67), "strength": 0.72, "feather": 0.10},
    "rosary": {"x": (0.32, 0.68), "y": (0.48, 0.75), "strength": 0.94, "feather": 0.13},
    "face": {"x": (0.27, 0.73), "y": (0.75, 0.995), "strength": 0.96, "feather": 0.12},
}
cfg_file = REF_DIR / "detail_regions.json"
if cfg_file.is_file():
    cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
    for key, values in cfg.items():
        if key not in detail_specs or not isinstance(values, dict):
            continue
        for field in ("strength", "feather"):
            if field in values:
                detail_specs[key][field] = float(values[field])
        for field in ("x", "y"):
            if field in values and len(values[field]) == 2:
                detail_specs[key][field] = tuple(float(x) for x in values[field])


def project_color(pos: np.ndarray, nrm: np.ndarray) -> np.ndarray:
    if len(pos) == 0:
        return np.empty((0, 3), dtype=np.float32)
    nrm = nrm / np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)
    xn = (pos[:, 0] - mins[0]) / max(extent[0], 1e-9)
    yn = (pos[:, 1] - mins[1]) / max(extent[1], 1e-9)
    zn = (pos[:, 2] - mins[2]) / max(extent[2], 1e-9)

    samples, weights = [], []
    for name in view_names:
        direction, axis, flip = view_cfg[name]
        u = xn if axis == "x" else zn
        if flip:
            u = 1.0 - u
        samples.append(bilinear(images[name], u, 1.0 - yn))
        weights.append(np.clip(nrm @ direction, 0.0, None) ** 8.0)

    W = np.stack(weights, axis=1)
    S = np.stack(samples, axis=1)
    frontness = np.clip(nrm[:, 2], 0.0, 1.0)
    backness = np.clip(-nrm[:, 2], 0.0, 1.0)
    face = np.clip((yn - 0.72) / 0.12, 0.0, 1.0)
    hair = feather_interval(yn, 0.70, 0.995, 0.10)
    torso = feather_interval(yn, 0.43, 0.78, 0.15)
    rosary = feather_interval(yn, 0.48, 0.75, 0.16) * feather_interval(xn, 0.30, 0.70, 0.18)
    dress = feather_interval(yn, 0.06, 0.69, 0.08)

    W[:, 0] *= 1.0 + frontness * (1.25 * face + 0.70 * hair + 0.55 * torso + 1.10 * rosary + 0.28 * dress)
    W[:, 1] *= 1.0 + backness * (0.95 * hair + 0.25 * dress)
    W[:, 2] *= 1.0 + 0.42 * hair + 0.10 * dress
    W[:, 3] *= 1.0 + 0.42 * hair + 0.10 * dress

    total = W.sum(1)
    color = (W[:, :, None] * S).sum(1) / np.maximum(total[:, None], 1e-8)

    low = total < 0.015
    if np.any(low):
        nx, nz = nrm[low, 0], nrm[low, 2]
        choice = np.where(np.abs(nx) > np.abs(nz), np.where(nx >= 0, 2, 3), np.where(nz >= 0, 0, 1))
        color[low] = S[low][np.arange(len(choice)), choice]

    for key in ("dress", "rosary", "face"):
        if key not in detail_images:
            continue
        spec = detail_specs[key]
        x0, x1 = spec["x"]
        y0, y1 = spec["y"]
        inside = (xn >= x0) & (xn <= x1) & (yn >= y0) & (yn <= y1)
        du = np.clip((xn - x0) / max(x1 - x0, 1e-9), 0.0, 1.0)
        dv = np.clip(1.0 - (yn - y0) / max(y1 - y0, 1e-9), 0.0, 1.0)
        detail = bilinear(detail_images[key], du, dv)
        edge = feather_interval(xn, x0, x1, spec["feather"]) * feather_interval(yn, y0, y1, spec["feather"])
        alpha = spec["strength"] * edge * (frontness ** 1.5) * inside.astype(np.float64)
        color = color * (1.0 - alpha[:, None]) + detail * alpha[:, None]

    return np.clip((color - 128.0) * 1.035 + 128.0, 0.0, 255.0).astype(np.float32)


# Debug fallback only; the HQ output below is baked at texel resolution.
vertex_color = project_color(V, N).astype(np.uint8)
dbg = trimesh.Trimesh(vertices=V, faces=F, process=False)
dbg.visual.vertex_colors = np.column_stack([vertex_color, np.full(len(vertex_color), 255, np.uint8)])
dbg_path = OUT / "llorona_hunyuan_vertexcolor_debug.glb"
dbg_path.write_bytes(trimesh.exchange.gltf.export_glb(trimesh.Scene(dbg)))

vmapping, indices, uvs = xatlas.parametrize(
    np.ascontiguousarray(V.astype(np.float32)),
    np.ascontiguousarray(F.astype(np.uint32)),
)
vmapping = np.asarray(vmapping, dtype=np.int64)
Fuv = np.asarray(indices, dtype=np.int32)
UV = np.asarray(uvs, dtype=np.float32)
Vuv, Nuv = V[vmapping], N[vmapping]

tex = np.zeros((TEX_SIZE, TEX_SIZE, 3), dtype=np.uint8)
mask = np.zeros((TEX_SIZE, TEX_SIZE), dtype=np.uint8)
uvpx = np.column_stack([UV[:, 0] * (TEX_SIZE - 1), (1.0 - UV[:, 1]) * (TEX_SIZE - 1)])

bx, by, bp, bn = [], [], [], []
queued = 0
texel_writes = 0


def flush() -> None:
    global queued, texel_writes
    if not bx:
        return
    xs, ys = np.concatenate(bx), np.concatenate(by)
    colors = project_color(np.concatenate(bp), np.concatenate(bn)).astype(np.uint8)
    tex[ys, xs] = colors
    mask[ys, xs] = 255
    texel_writes += len(xs)
    bx.clear(); by.clear(); bp.clear(); bn.clear()
    queued = 0


for fi, tri in enumerate(Fuv):
    p = uvpx[tri]
    minx = max(int(np.floor(p[:, 0].min())), 0)
    maxx = min(int(np.ceil(p[:, 0].max())), TEX_SIZE - 1)
    miny = max(int(np.floor(p[:, 1].min())), 0)
    maxy = min(int(np.ceil(p[:, 1].max())), TEX_SIZE - 1)
    if minx > maxx or miny > maxy:
        continue

    x0, y0 = p[0]; x1, y1 = p[1]; x2, y2 = p[2]
    den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
    if abs(float(den)) < 1e-10:
        continue

    gx, gy = np.meshgrid(np.arange(minx, maxx + 1, dtype=np.int32), np.arange(miny, maxy + 1, dtype=np.int32))
    sx, sy = gx + 0.5, gy + 0.5
    w0 = ((y1 - y2) * (sx - x2) + (x2 - x1) * (sy - y2)) / den
    w1 = ((y2 - y0) * (sx - x2) + (x0 - x2) * (sy - y2)) / den
    w2 = 1.0 - w0 - w1
    inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
    if not np.any(inside):
        continue

    xx, yy = gx[inside], gy[inside]
    a, b, c = w0[inside, None], w1[inside, None], w2[inside, None]
    pos = a * Vuv[tri[0]] + b * Vuv[tri[1]] + c * Vuv[tri[2]]
    nrm = a * Nuv[tri[0]] + b * Nuv[tri[1]] + c * Nuv[tri[2]]
    nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)

    bx.append(xx); by.append(yy); bp.append(pos); bn.append(nrm)
    queued += len(xx)
    if queued >= CHUNK_TEXELS:
        flush()
    if fi and fi % 20000 == 0:
        print("PER_PIXEL_BAKE", fi, "/", len(Fuv), "texels", texel_writes + queued)

flush()
valid = mask > 0
if not np.any(valid):
    fail("Per-pixel atlas is empty")

dist, inds = ndimage.distance_transform_edt(~valid, return_indices=True)
gutter = (~valid) & (dist <= 8.0)
tex[gutter] = tex[inds[0][gutter], inds[1][gutter]]
tex_path = OUT / "llorona_albedo_hq.png"
Image.fromarray(tex, "RGB").save(tex_path, optimize=True)

from trimesh.visual.material import PBRMaterial
from trimesh.visual.texture import TextureVisuals

material = PBRMaterial(
    name="Llorona_HQ_PerPixel_PBR",
    baseColorTexture=Image.fromarray(tex, "RGB"),
    baseColorFactor=[255, 255, 255, 255],
    metallicFactor=0.0,
    roughnessFactor=0.84,
    doubleSided=True,
)
visual = TextureVisuals(uv=UV, material=material)
mesh = trimesh.Trimesh(vertices=Vuv, faces=Fuv, process=False, visual=visual)
glb_path = OUT / "llorona_hq_perpixel_textured.glb"
glb_path.write_bytes(trimesh.exchange.gltf.export_glb(trimesh.Scene(mesh)))

check = trimesh.load(glb_path, force="scene")
if not check.geometry:
    fail("Exported GLB reload has no geometry")
cg = max(check.geometry.values(), key=lambda g: len(g.faces))
has_uv = hasattr(cg.visual, "uv") and cg.visual.uv is not None and len(cg.visual.uv) > 0
mat = getattr(cg.visual, "material", None)
has_tex = bool(getattr(mat, "baseColorTexture", None) is not None or getattr(mat, "image", None) is not None)
if not has_uv or not has_tex:
    fail(f"GLB texture validation failed: uv={has_uv} texture={has_tex}")


def sample_tex(uv: np.ndarray) -> np.ndarray:
    return bilinear(tex.astype(np.float32), uv[:, 0], 1.0 - uv[:, 1])


# Seam QA: duplicated xatlas UV vertices representing the same source vertex should
# agree in color. Large deltas are a reliable proxy for visible chart seams.
# Sample each UV duplicate slightly inside its own chart rather than exactly on
# the chart border. This measures the color a bilinear sampler will actually see
# from that chart and avoids false seam alarms caused by border-coordinate ambiguity.
face_centroids = UV[Fuv].mean(axis=1).astype(np.float64)
centroid_sum = np.zeros((len(UV), 2), dtype=np.float64)
centroid_count = np.zeros(len(UV), dtype=np.float64)
for corner in range(3):
    np.add.at(centroid_sum, Fuv[:, corner], face_centroids)
    np.add.at(centroid_count, Fuv[:, corner], 1.0)
inward_target = centroid_sum / np.maximum(centroid_count[:, None], 1.0)
direction = inward_target - UV
direction /= np.maximum(np.linalg.norm(direction, axis=1, keepdims=True), 1e-9)
inset_uv = np.clip(UV + direction * (2.0 / TEX_SIZE), 0.0, 1.0)
uvc = sample_tex(inset_uv)
order = np.argsort(vmapping)
ids, cols = vmapping[order], uvc[order]
errs = []
start = 0
while start < len(ids):
    end = start + 1
    while end < len(ids) and ids[end] == ids[start]:
        end += 1
    if end - start > 1:
        group = cols[start:end]
        errs.append(np.linalg.norm(group - group.mean(0), axis=1))
    start = end
if errs:
    seam = np.concatenate(errs)
    seam_mean, seam_p95 = float(seam.mean()), float(np.percentile(seam, 95))
else:
    seam_mean = seam_p95 = 0.0


def front_render(size: int = 640) -> tuple[np.ndarray, np.ndarray]:
    center = (Vuv.min(0) + Vuv.max(0)) * 0.5
    P = Vuv - center
    sx, sy, sz = P[:, 0], P[:, 1], P[:, 2]
    sc = (size - 64) / max(float(np.ptp(sx)), float(np.ptp(sy)), 1e-9)
    xx = (sx - (sx.min() + sx.max()) * 0.5) * sc + size * 0.5
    yy = size * 0.5 - (sy - (sy.min() + sy.max()) * 0.5) * sc
    screen = np.column_stack([xx, yy])
    out = np.full((size, size, 3), 13, np.uint8)
    hit = np.zeros((size, size), np.uint8)
    zbuf = np.full((size, size), -np.inf)

    for tri in Fuv:
        p = screen[tri]
        minx = max(int(np.floor(p[:, 0].min())), 0)
        maxx = min(int(np.ceil(p[:, 0].max())), size - 1)
        miny = max(int(np.floor(p[:, 1].min())), 0)
        maxy = min(int(np.ceil(p[:, 1].max())), size - 1)
        if minx > maxx or miny > maxy:
            continue
        x0, y0 = p[0]; x1, y1 = p[1]; x2, y2 = p[2]
        den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(float(den)) < 1e-10:
            continue
        gx, gy = np.meshgrid(np.arange(minx, maxx + 1), np.arange(miny, maxy + 1))
        px, py = gx + 0.5, gy + 0.5
        w0 = ((y1 - y2) * (px - x2) + (x2 - x1) * (py - y2)) / den
        w1 = ((y2 - y0) * (px - x2) + (x0 - x2) * (py - y2)) / den
        w2 = 1.0 - w0 - w1
        inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not np.any(inside):
            continue
        xi, yi = gx[inside], gy[inside]
        a, b, c = w0[inside], w1[inside], w2[inside]
        depth = a * sz[tri[0]] + b * sz[tri[1]] + c * sz[tri[2]]
        win = depth > zbuf[yi, xi]
        if not np.any(win):
            continue
        xi, yi = xi[win], yi[win]
        a, b, c, depth = a[win], b[win], c[win], depth[win]
        uv = a[:, None] * UV[tri[0]] + b[:, None] * UV[tri[1]] + c[:, None] * UV[tri[2]]
        out[yi, xi] = sample_tex(uv).astype(np.uint8)
        hit[yi, xi] = 255
        zbuf[yi, xi] = depth
    return out, hit


render, render_mask = front_render()
Image.fromarray(render, "RGB").save(OUT / "preview_front.png")


def quick_view(angle: int, name: str, size: int = 700) -> None:
    a = math.radians(angle)
    R = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
    P = (Vuv - (Vuv.min(0) + Vuv.max(0)) / 2.0) @ R.T
    sx, sy, depth = P[:, 0], P[:, 1], P[:, 2]
    sc = (size - 80) / max(float(np.ptp(sx)), float(np.ptp(sy)), 1e-9)
    xx = (sx - (sx.min() + sx.max()) / 2) * sc + size / 2
    yy = size / 2 - (sy - (sy.min() + sy.max()) / 2) * sc
    colors = sample_tex(UV[Fuv].mean(1)).astype(np.uint8)
    order_faces = np.argsort(depth[Fuv].mean(1))
    canvas = Image.new("RGB", (size, size), (13, 13, 16))
    draw = ImageDraw.Draw(canvas)
    for fi in order_faces:
        draw.polygon([(float(xx[v]), float(yy[v])) for v in Fuv[fi]], fill=tuple(int(x) for x in colors[fi]))
    canvas.save(OUT / f"preview_{name}.png")


quick_view(45, "three_quarter")
quick_view(90, "side")
quick_view(180, "back")


def aligned_front_reference(size: int = 640) -> np.ndarray:
    center = (Vuv.min(0) + Vuv.max(0)) * 0.5
    P = Vuv - center
    sx, sy = P[:, 0], P[:, 1]
    sc = (size - 64) / max(float(np.ptp(sx)), float(np.ptp(sy)), 1e-9)
    xmid, ymid = (sx.min() + sx.max()) * 0.5, (sy.min() + sy.max()) * 0.5
    gx, gy = np.meshgrid(np.arange(size, dtype=np.float64), np.arange(size, dtype=np.float64))
    wx = ((gx - size * 0.5) / sc + xmid) + center[0]
    wy = (-(gy - size * 0.5) / sc + ymid) + center[1]
    u = ((wx - mins[0]) / max(extent[0], 1e-9)).ravel()
    v = (1.0 - (wy - mins[1]) / max(extent[1], 1e-9)).ravel()
    return np.clip(bilinear(images["front"], u, v).reshape(size, size, 3), 0, 255).astype(np.uint8)


reference = aligned_front_reference()


def crop(arr: np.ndarray, x0: float, y0: float, x1: float, y1: float) -> np.ndarray:
    h, w = arr.shape[:2]
    return arr[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)]


def lap_var(img: np.ndarray, m: np.ndarray) -> float:
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    mm = cv2.erode((m > 0).astype(np.uint8), np.ones((5, 5), np.uint8), iterations=1) > 0
    values = lap[mm]
    return float(values.var()) if values.size >= 64 else 0.0


def rgb_std(img: np.ndarray, m: np.ndarray) -> float:
    mm = cv2.erode((m > 0).astype(np.uint8), np.ones((5, 5), np.uint8), iterations=1) > 0
    values = img[mm]
    return float(values.std()) if values.size >= 64 else 0.0


def detail_ref(key: str, base: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    if key not in detail_images:
        return base
    h, w = shape
    return cv2.resize(detail_images[key].astype(np.uint8), (w, h), interpolation=cv2.INTER_LANCZOS4)


regions = {
    "face": (0.35, 0.035, 0.65, 0.29),
    "rosary": (0.37, 0.25, 0.63, 0.54),
    "dress": (0.27, 0.40, 0.73, 0.92),
}
metrics = {}
for key, box in regions.items():
    out_crop = crop(render, *box)
    base_crop = crop(reference, *box)
    m = crop(render_mask, *box)
    ref_crop = detail_ref(key, base_crop, out_crop.shape[:2])
    out_lap = lap_var(out_crop, m)
    ref_lap = lap_var(ref_crop, m)
    metrics[key] = {
        "laplacianVariance": out_lap,
        "referenceLaplacianVariance": ref_lap,
        "detailRatio": out_lap / max(ref_lap, 1e-6),
    }
    Image.fromarray(out_crop, "RGB").save(OUT / f"qa_{key}_crop.png")

dress_box = regions["dress"]
dress_img = crop(render, *dress_box)
dress_base = crop(reference, *dress_box)
dress_m = crop(render_mask, *dress_box)
dress_ref = detail_ref("dress", dress_base, dress_img.shape[:2])
metrics["dress"]["rgbStd"] = rgb_std(dress_img, dress_m)
metrics["dress"]["referenceRgbStd"] = rgb_std(dress_ref, dress_m)
metrics["dress"]["rgbStdRatio"] = metrics["dress"]["rgbStd"] / max(metrics["dress"]["referenceRgbStd"], 1e-6)

metrics["seams"] = {"meanColorDelta": seam_mean, "p95ColorDelta": seam_p95}

failures = []
if metrics["face"]["laplacianVariance"] < QA_FACE_LAP_MIN or metrics["face"]["detailRatio"] < QA_FACE_RATIO_MIN:
    failures.append("face muddy")
if metrics["rosary"]["laplacianVariance"] < QA_ROSARY_LAP_MIN or metrics["rosary"]["detailRatio"] < QA_ROSARY_RATIO_MIN:
    failures.append("rosary/cross muddy")
if metrics["dress"]["laplacianVariance"] < QA_DRESS_LAP_MIN or metrics["dress"]["detailRatio"] < QA_DRESS_RATIO_MIN:
    failures.append("dress detail collapsed")
if metrics["dress"]["referenceRgbStd"] >= 8.0 and metrics["dress"]["rgbStdRatio"] < QA_DRESS_STD_RATIO_MIN:
    failures.append("dress stretched/blotchy/flat")
if seam_mean > QA_SEAM_MEAN_MAX or seam_p95 > QA_SEAM_P95_MAX:
    failures.append("UV seams too visible")

manifest = {
    "asset": "La Llorona",
    "pipeline": "locked Hunyuan HQ geometry -> clean-only topology -> xatlas -> per-texel barycentric 4-view projection -> refined detail overlays -> automatic HQ QA",
    "sourceRunId": 35772555593,
    "sourceVerticesRaw": raw_vertices,
    "sourceFacesRaw": raw_faces,
    "sourceVerticesClean": clean_vertices,
    "sourceFacesClean": clean_faces,
    "sourceComponentsClean": clean_components,
    "runtimeBaseVertices": len(V),
    "runtimeBaseFaces": len(F),
    "runtimeUvVertices": len(Vuv),
    "runtimeFaces": len(Fuv),
    "targetFaces": TARGET_FACES,
    "topologyMode": "clean-only" if TARGET_FACES <= 0 else "clean-plus-optional-decimation",
    "textureSize": TEX_SIZE,
    "heightMeters": TARGET_HEIGHT_M,
    "processedTexelWrites": texel_writes,
    "baseRefs": {k: str(v) for k, v in base_paths.items()},
    "detailRefs": {k: str(v) if v else None for k, v in detail_paths.items()},
    "detailsRequired": REQUIRE_DETAILS,
    "strictQA": STRICT_QA,
    "referenceQuality": reference_quality,
    "hasUV": bool(has_uv),
    "hasEmbeddedBaseColorTexture": bool(has_tex),
    "qa": metrics,
    "qaPassed": not failures,
    "qaFailures": failures,
    "outputs": {
        "hqGLB": glb_path.name,
        "albedo": tex_path.name,
        "vertexColorDebugGLB": dbg_path.name,
        "previewFront": "preview_front.png",
        "previewThreeQuarter": "preview_three_quarter.png",
        "previewSide": "preview_side.png",
        "previewBack": "preview_back.png",
    },
}
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
(OUT / "qa.json").write_text(json.dumps({"passed": not failures, "failures": failures, "metrics": metrics}, indent=2), encoding="utf-8")

print(json.dumps(manifest, indent=2))
if failures:
    fail("HQ texture rejected automatically: " + " | ".join(failures))
print("XZIEL_LLORONA_HQ_PERPIXEL_TEXTURE_PASS")
