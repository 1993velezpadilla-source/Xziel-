#!/usr/bin/env python3
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SourceViewScore:
    source: str
    best_score: float
    best_azimuth: float
    best_elevation: float
    best_up_axis: str
    silhouette_iou: float
    boundary_f1: float


@dataclass
class VisualScore:
    score: float
    views: list[SourceViewScore]
    method: str = "hayuya-silhouette-camera-search-v2"


def _deps():
    import numpy as np
    from PIL import Image, ImageDraw
    return np, Image, ImageDraw


def _trimesh():
    import trimesh
    return trimesh


def _binary_bbox(mask):
    np, _, _ = _deps()
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def _normalize_mask(mask, size: int = 192, margin: int = 10):
    np, Image, _ = _deps()
    bbox = _binary_bbox(mask)
    if bbox is None:
        return np.zeros((size, size), dtype=bool)
    x0, y0, x1, y1 = bbox
    crop = mask[y0:y1 + 1, x0:x1 + 1].astype(np.uint8) * 255
    h, w = crop.shape
    if h <= 0 or w <= 0:
        return np.zeros((size, size), dtype=bool)
    scale = min((size - 2 * margin) / w, (size - 2 * margin) / h)
    nw = max(1, int(round(w * scale)))
    nh = max(1, int(round(h * scale)))
    im = Image.fromarray(crop, mode="L").resize((nw, nh), Image.Resampling.NEAREST)
    canvas = Image.new("L", (size, size), 0)
    canvas.paste(im, ((size - nw) // 2, (size - nh) // 2))
    return np.asarray(canvas) > 127


def extract_source_mask(path: Path, size: int = 192):
    np, Image, _ = _deps()
    im = Image.open(path).convert("RGBA")
    arr = np.asarray(im)
    alpha = arr[:, :, 3]

    # Best case: user supplied a transparent cutout.
    if int(alpha.min()) < 245:
        mask = alpha > 20
        return _normalize_mask(mask, size=size)

    rgb = arr[:, :, :3].astype(np.float32)
    h, w, _ = rgb.shape
    patch = max(2, min(h, w) // 20)
    corners = np.concatenate([
        rgb[:patch, :patch].reshape(-1, 3),
        rgb[:patch, -patch:].reshape(-1, 3),
        rgb[-patch:, :patch].reshape(-1, 3),
        rgb[-patch:, -patch:].reshape(-1, 3),
    ], axis=0)
    bg = np.median(corners, axis=0)
    corner_dist = np.linalg.norm(corners - bg, axis=1)
    threshold = max(22.0, float(np.percentile(corner_dist, 95)) * 2.5 + 8.0)
    dist = np.linalg.norm(rgb - bg, axis=2)
    mask = dist > threshold

    # If corner-background segmentation is implausible, use luminance contrast.
    occupancy = float(mask.mean())
    if occupancy < 0.03 or occupancy > 0.92:
        lum = rgb.mean(axis=2)
        bg_lum = float(bg.mean())
        lum_threshold = max(18.0, float(np.std(corners.mean(axis=1))) * 3.0 + 8.0)
        mask = np.abs(lum - bg_lum) > lum_threshold

    return _normalize_mask(mask, size=size)


def _rotation_matrix(azimuth_deg: float, elevation_deg: float, up_axis: str):
    np, _, _ = _deps()
    a = math.radians(azimuth_deg)
    e = math.radians(elevation_deg)

    if up_axis == "y":
        yaw = np.array([
            [math.cos(a), 0.0, math.sin(a)],
            [0.0, 1.0, 0.0],
            [-math.sin(a), 0.0, math.cos(a)],
        ], dtype=np.float32)
        pitch = np.array([
            [1.0, 0.0, 0.0],
            [0.0, math.cos(e), -math.sin(e)],
            [0.0, math.sin(e), math.cos(e)],
        ], dtype=np.float32)
    else:
        yaw = np.array([
            [math.cos(a), -math.sin(a), 0.0],
            [math.sin(a), math.cos(a), 0.0],
            [0.0, 0.0, 1.0],
        ], dtype=np.float32)
        pitch = np.array([
            [1.0, 0.0, 0.0],
            [0.0, math.cos(e), -math.sin(e)],
            [0.0, math.sin(e), math.cos(e)],
        ], dtype=np.float32)
    return pitch @ yaw


def _load_mesh_arrays(path: Path, max_faces: int = 9000):
    np, _, _ = _deps()
    trimesh = _trimesh()
    loaded = trimesh.load(path, force="scene", process=False)
    geoms = list(loaded.geometry.values()) if hasattr(loaded, "geometry") else [loaded]
    meshes = [g for g in geoms if hasattr(g, "faces") and len(g.faces)]
    if not meshes:
        raise ValueError("no triangle mesh geometry")
    mesh = trimesh.util.concatenate(meshes)
    vertices = np.asarray(mesh.vertices, dtype=np.float32)
    faces = np.asarray(mesh.faces, dtype=np.int64)
    if len(faces) > max_faces:
        # Deterministic coverage across the complete face array.
        ids = np.linspace(0, len(faces) - 1, max_faces, dtype=np.int64)
        faces = faces[ids]

    center = (vertices.min(axis=0) + vertices.max(axis=0)) * 0.5
    vertices = vertices - center
    scale = float(np.max(vertices.max(axis=0) - vertices.min(axis=0)))
    if not math.isfinite(scale) or scale <= 1e-9:
        raise ValueError("collapsed mesh bounds")
    vertices = vertices / scale
    return vertices, faces


def render_silhouette(vertices, faces, azimuth: float, elevation: float, up_axis: str, size: int = 192):
    np, Image, ImageDraw = _deps()
    rot = _rotation_matrix(azimuth, elevation, up_axis)
    v = vertices @ rot.T

    # Camera looks down the third axis after rotation. Normalize only in image plane.
    xy = v[:, :2]
    min_xy = xy.min(axis=0)
    max_xy = xy.max(axis=0)
    span = np.maximum(max_xy - min_xy, 1e-7)
    uniform = float(max(span[0], span[1]))
    xy = (xy - (min_xy + max_xy) * 0.5) / uniform
    xy = xy * (size * 0.82) + size * 0.5

    canvas = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(canvas)
    for tri in faces:
        pts = [
            (float(xy[int(tri[0]), 0]), float(size - 1 - xy[int(tri[0]), 1])),
            (float(xy[int(tri[1]), 0]), float(size - 1 - xy[int(tri[1]), 1])),
            (float(xy[int(tri[2]), 0]), float(size - 1 - xy[int(tri[2]), 1])),
        ]
        draw.polygon(pts, fill=255)
    return _normalize_mask(np.asarray(canvas) > 127, size=size)


def _erode(mask):
    np, _, _ = _deps()
    p = np.pad(mask, 1, constant_values=False)
    out = np.ones_like(mask, dtype=bool)
    for dy in range(3):
        for dx in range(3):
            out &= p[dy:dy + mask.shape[0], dx:dx + mask.shape[1]]
    return out


def _boundary(mask):
    return mask & ~_erode(mask)


def _iou(a, b) -> float:
    np, _, _ = _deps()
    inter = int(np.logical_and(a, b).sum())
    union = int(np.logical_or(a, b).sum())
    return float(inter / union) if union else 0.0


def _dilate(mask, radius: int = 2):
    np, _, _ = _deps()
    p = np.pad(mask, radius, constant_values=False)
    out = np.zeros_like(mask, dtype=bool)
    for dy in range(radius * 2 + 1):
        for dx in range(radius * 2 + 1):
            out |= p[dy:dy + mask.shape[0], dx:dx + mask.shape[1]]
    return out


def _boundary_f1(a, b) -> float:
    np, _, _ = _deps()
    ea, eb = _boundary(a), _boundary(b)
    na, nb = int(ea.sum()), int(eb.sum())
    if na == 0 or nb == 0:
        return 0.0
    precision = float((ea & _dilate(eb)).sum() / na)
    recall = float((eb & _dilate(ea)).sum() / nb)
    return 2.0 * precision * recall / max(precision + recall, 1e-9)


def score_masks(source_mask, candidate_mask) -> tuple[float, float, float]:
    iou = _iou(source_mask, candidate_mask)
    edge = _boundary_f1(source_mask, candidate_mask)
    # IoU dominates; edge fidelity catches shape-specific contours.
    score = 100.0 * (0.72 * iou + 0.28 * edge)
    return score, iou, edge


def score_candidate(
    mesh_path: Path,
    source_images: list[Path],
    *,
    size: int = 192,
    azimuth_step: int = 30,
) -> VisualScore:
    vertices, faces = _load_mesh_arrays(mesh_path)
    source_masks = [extract_source_mask(p, size=size) for p in source_images]

    views: list[SourceViewScore] = []
    for source_path, source_mask in zip(source_images, source_masks):
        best = None
        for up_axis in ("y", "z"):
            for elevation in (-15.0, 0.0, 15.0):
                for azimuth in range(0, 360, azimuth_step):
                    candidate_mask = render_silhouette(
                        vertices, faces, float(azimuth), elevation, up_axis, size=size
                    )
                    score, iou, edge = score_masks(source_mask, candidate_mask)
                    if best is None or score > best.best_score:
                        best = SourceViewScore(
                            source=str(source_path),
                            best_score=round(score, 3),
                            best_azimuth=float(azimuth),
                            best_elevation=elevation,
                            best_up_axis=up_axis,
                            silhouette_iou=round(iou, 6),
                            boundary_f1=round(edge, 6),
                        )
        assert best is not None
        views.append(best)

    vals = [x.best_score for x in views]
    # Every real source matters: weak agreement with either anchor drags the score down.
    final = 0.70 * (sum(vals) / len(vals)) + 0.30 * min(vals)
    return VisualScore(score=round(final, 3), views=views)


def main() -> int:
    import argparse
    import json
    from dataclasses import asdict

    parser = argparse.ArgumentParser(description="HAYUYA Judge v2 source-image silhouette scorer.")
    parser.add_argument("mesh", type=Path)
    parser.add_argument("--source", type=Path, action="append", required=True)
    parser.add_argument("--size", type=int, default=192)
    parser.add_argument("--azimuth-step", type=int, default=30)
    args = parser.parse_args()

    result = score_candidate(
        args.mesh,
        args.source,
        size=args.size,
        azimuth_step=args.azimuth_step,
    )
    print(json.dumps(asdict(result), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
