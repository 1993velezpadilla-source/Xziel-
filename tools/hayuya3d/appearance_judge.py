#!/usr/bin/env python3
from __future__ import annotations

import math
import os
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path

from reference_pool import infer_view_hint
from visual_judge import SourceViewScore, _rotation_matrix, extract_source_mask


@dataclass
class AppearanceViewScore:
    source: str
    cosine_similarity: float
    score: float
    azimuth: float
    elevation: float
    up_axis: str
    candidate_render: str | None = None


@dataclass
class AppearanceScore:
    score: float
    views: list[AppearanceViewScore]
    method: str = "hayuya-dinov2-rgb-v3"


def _deps():
    import numpy as np
    from PIL import Image
    return np, Image


def project_vertices(vertices, azimuth: float, elevation: float, up_axis: str, size: int):
    np, _ = _deps()
    rot = _rotation_matrix(azimuth, elevation, up_axis)
    v = vertices @ rot.T
    xy = v[:, :2]
    min_xy = xy.min(axis=0)
    max_xy = xy.max(axis=0)
    span = np.maximum(max_xy - min_xy, 1e-7)
    uniform = float(max(span[0], span[1]))
    xy = (xy - (min_xy + max_xy) * 0.5) / uniform
    xy = xy * (size * 0.82) + size * 0.5

    # Positive depth wins. Camera convention only needs to be internally consistent.
    z = v[:, 2].astype(np.float32)
    return xy.astype(np.float32), z


def rasterize_rgb(
    xy,
    z,
    faces,
    vertex_colors,
    *,
    size: int = 224,
    background: tuple[int, int, int] = (127, 127, 127),
):
    """
    Tiny deterministic CPU z-buffer rasterizer.

    It is intentionally dependency-light and uses vertex colors. Trimesh texture
    visuals are converted to vertex colors before this stage, giving Judge v3 a
    useful appearance signal without requiring OpenGL or PyTorch3D.
    """
    np, Image = _deps()
    image = np.empty((size, size, 3), dtype=np.float32)
    image[:] = np.asarray(background, dtype=np.float32)
    depth = np.full((size, size), -np.inf, dtype=np.float32)

    eps = 1e-7
    for tri in faces:
        ids = np.asarray(tri, dtype=np.int64)
        pts = xy[ids]
        zs = z[ids]
        cols = vertex_colors[ids].astype(np.float32)

        min_x = max(0, int(math.floor(float(pts[:, 0].min()))))
        max_x = min(size - 1, int(math.ceil(float(pts[:, 0].max()))))
        min_y = max(0, int(math.floor(float((size - 1 - pts[:, 1]).min()))))
        max_y = min(size - 1, int(math.ceil(float((size - 1 - pts[:, 1]).max()))))
        if min_x > max_x or min_y > max_y:
            continue

        p0 = np.array([pts[0, 0], size - 1 - pts[0, 1]], dtype=np.float32)
        p1 = np.array([pts[1, 0], size - 1 - pts[1, 1]], dtype=np.float32)
        p2 = np.array([pts[2, 0], size - 1 - pts[2, 1]], dtype=np.float32)
        denom = (
            (p1[1] - p2[1]) * (p0[0] - p2[0])
            + (p2[0] - p1[0]) * (p0[1] - p2[1])
        )
        if abs(float(denom)) <= eps:
            continue

        yy, xx = np.mgrid[min_y:max_y + 1, min_x:max_x + 1]
        px = xx.astype(np.float32) + 0.5
        py = yy.astype(np.float32) + 0.5

        w0 = ((p1[1] - p2[1]) * (px - p2[0]) + (p2[0] - p1[0]) * (py - p2[1])) / denom
        w1 = ((p2[1] - p0[1]) * (px - p2[0]) + (p0[0] - p2[0]) * (py - p2[1])) / denom
        w2 = 1.0 - w0 - w1
        inside = (w0 >= -1e-5) & (w1 >= -1e-5) & (w2 >= -1e-5)
        if not inside.any():
            continue

        zz = w0 * zs[0] + w1 * zs[1] + w2 * zs[2]
        region_depth = depth[min_y:max_y + 1, min_x:max_x + 1]
        visible = inside & (zz > region_depth)
        if not visible.any():
            continue

        rgb = (
            w0[..., None] * cols[0]
            + w1[..., None] * cols[1]
            + w2[..., None] * cols[2]
        )
        region_img = image[min_y:max_y + 1, min_x:max_x + 1]
        region_img[visible] = rgb[visible]
        region_depth[visible] = zz[visible]

    return Image.fromarray(np.clip(image, 0, 255).astype(np.uint8), mode="RGB")


def _mesh_rgb_arrays(mesh_path: Path, max_faces: int = 12000):
    np, _ = _deps()
    import trimesh

    loaded = trimesh.load(mesh_path, force="scene", process=False)
    if hasattr(loaded, "dump"):
        try:
            geoms = list(loaded.dump(concatenate=False))
        except Exception:
            geoms = list(getattr(loaded, "geometry", {}).values())
    else:
        geoms = [loaded]

    vertices_parts = []
    faces_parts = []
    colors_parts = []
    offset = 0

    for mesh in geoms:
        if not hasattr(mesh, "faces") or not len(mesh.faces):
            continue
        vertices = np.asarray(mesh.vertices, dtype=np.float32)
        faces = np.asarray(mesh.faces, dtype=np.int64)

        colors = None
        visual = getattr(mesh, "visual", None)
        if visual is not None:
            try:
                converted = visual.to_color()
                vc = getattr(converted, "vertex_colors", None)
                if vc is not None and len(vc) == len(vertices):
                    colors = np.asarray(vc[:, :3], dtype=np.float32)
            except Exception:
                pass
            if colors is None:
                vc = getattr(visual, "vertex_colors", None)
                if vc is not None and len(vc) == len(vertices):
                    colors = np.asarray(vc[:, :3], dtype=np.float32)

        if colors is None:
            colors = np.full((len(vertices), 3), 190.0, dtype=np.float32)

        vertices_parts.append(vertices)
        faces_parts.append(faces + offset)
        colors_parts.append(colors)
        offset += len(vertices)

    if not vertices_parts:
        raise ValueError("no triangle mesh geometry")

    vertices = np.concatenate(vertices_parts, axis=0)
    faces = np.concatenate(faces_parts, axis=0)
    colors = np.concatenate(colors_parts, axis=0)

    if len(faces) > max_faces:
        ids = np.linspace(0, len(faces) - 1, max_faces, dtype=np.int64)
        faces = faces[ids]

    center = (vertices.min(axis=0) + vertices.max(axis=0)) * 0.5
    vertices = vertices - center
    scale = float(np.max(vertices.max(axis=0) - vertices.min(axis=0)))
    if not math.isfinite(scale) or scale <= 1e-9:
        raise ValueError("collapsed mesh bounds")
    vertices = vertices / scale
    return vertices, faces, colors


def render_candidate_rgb(
    mesh_path: Path,
    view: SourceViewScore,
    *,
    size: int = 224,
):
    vertices, faces, colors = _mesh_rgb_arrays(mesh_path)
    xy, z = project_vertices(
        vertices,
        view.best_azimuth,
        view.best_elevation,
        view.best_up_axis,
        size,
    )
    return rasterize_rgb(xy, z, faces, colors, size=size)


def preprocess_source_rgb(path: Path, *, size: int = 224):
    np, Image = _deps()
    image = Image.open(path).convert("RGB")
    arr = np.asarray(image)
    mask = extract_source_mask(path, size=max(image.size))

    # Rebuild the mask at native-ish dimensions through the same foreground heuristic.
    # If exact shape differs because the helper normalizes, fall back to a neutral crop.
    try:
        from visual_judge import _binary_bbox
        native_rgba = Image.open(path).convert("RGBA")
        native = np.asarray(native_rgba)
        alpha = native[:, :, 3]
        if int(alpha.min()) < 245:
            native_mask = alpha > 20
        else:
            rgb = native[:, :, :3].astype(np.float32)
            h, w, _ = rgb.shape
            patch = max(2, min(h, w) // 20)
            corners = np.concatenate([
                rgb[:patch, :patch].reshape(-1, 3),
                rgb[:patch, -patch:].reshape(-1, 3),
                rgb[-patch:, :patch].reshape(-1, 3),
                rgb[-patch:, -patch:].reshape(-1, 3),
            ], axis=0)
            bg = np.median(corners, axis=0)
            threshold = max(22.0, float(np.percentile(np.linalg.norm(corners - bg, axis=1), 95)) * 2.5 + 8.0)
            native_mask = np.linalg.norm(rgb - bg, axis=2) > threshold

        bbox = _binary_bbox(native_mask)
        if bbox is None:
            raise ValueError("empty foreground")
        x0, y0, x1, y1 = bbox
        crop = arr[y0:y1 + 1, x0:x1 + 1]
        crop_mask = native_mask[y0:y1 + 1, x0:x1 + 1]
        h, w = crop.shape[:2]
        canvas = np.full((max(h, w), max(h, w), 3), 127, dtype=np.uint8)
        mask_canvas = np.zeros((max(h, w), max(h, w)), dtype=bool)
        oy = (canvas.shape[0] - h) // 2
        ox = (canvas.shape[1] - w) // 2
        canvas[oy:oy + h, ox:ox + w] = crop
        mask_canvas[oy:oy + h, ox:ox + w] = crop_mask
        canvas[~mask_canvas] = 127
        return Image.fromarray(canvas, mode="RGB").resize((size, size), Image.Resampling.BICUBIC)
    except Exception:
        return image.resize((size, size), Image.Resampling.BICUBIC)


@lru_cache(maxsize=2)
def _load_dinov2(repo_path: str, device_name: str):
    import torch

    repo = Path(repo_path)
    if not repo.is_dir():
        raise FileNotFoundError(
            f"DINOv2 evaluator is not bootstrapped at {repo}. "
            "Run: python tools/hayuya3d/bootstrap.py --backend dinov2"
        )

    model = torch.hub.load(
        str(repo),
        "dinov2_vits14",
        source="local",
        pretrained=True,
    )
    model.eval().to(device_name)
    return model


def _encode_dinov2(image, *, repo_path: Path, device_name: str):
    import numpy as np
    import torch

    arr = np.asarray(image.convert("RGB").resize((224, 224)), dtype=np.float32) / 255.0
    tensor = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)
    mean = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
    std = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)
    tensor = ((tensor - mean) / std).to(device_name)

    model = _load_dinov2(str(repo_path.resolve()), device_name)
    with torch.inference_mode():
        feature = model(tensor)
    if isinstance(feature, dict):
        feature = feature.get("x_norm_clstoken") or next(iter(feature.values()))
    feature = feature.reshape(feature.shape[0], -1)
    feature = torch.nn.functional.normalize(feature, dim=-1)
    return feature[0].detach().cpu().numpy()


def cosine_similarity(a, b) -> float:
    import numpy as np

    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom <= 1e-12:
        return 0.0
    return float(np.dot(a, b) / denom)


def aggregate_appearance_scores(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(v) for v in values)
    mean = sum(ordered) / len(ordered)
    if len(ordered) <= 2:
        return 0.75 * mean + 0.25 * ordered[0]
    q_count = max(1, math.ceil(len(ordered) * 0.25))
    low = sum(ordered[:q_count]) / q_count
    return 0.72 * mean + 0.20 * low + 0.08 * ordered[0]


def score_candidate_appearance(
    mesh_path: Path,
    source_images: list[Path],
    matched_views: list[SourceViewScore],
    *,
    model_root: Path,
    render_dir: Path | None = None,
    device: str = "auto",
) -> AppearanceScore:
    import numpy as np

    if len(source_images) != len(matched_views):
        raise ValueError("source_images and matched_views must have equal length")

    if device == "auto":
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"

    repo_path = model_root / "dinov2"
    views: list[AppearanceViewScore] = []

    for index, (source, matched) in enumerate(zip(source_images, matched_views)):
        source_rgb = preprocess_source_rgb(source)
        candidate_rgb = render_candidate_rgb(mesh_path, matched)

        render_path = None
        if render_dir is not None:
            render_dir.mkdir(parents=True, exist_ok=True)
            render_path = render_dir / f"{index:03d}_{source.stem}.png"
            candidate_rgb.save(render_path)

        source_feature = _encode_dinov2(source_rgb, repo_path=repo_path, device_name=device)
        candidate_feature = _encode_dinov2(candidate_rgb, repo_path=repo_path, device_name=device)
        cosine = cosine_similarity(source_feature, candidate_feature)

        # DINO cosine is stored raw; ranking maps the bounded positive interval to 0-100.
        # Keep this monotonic rather than pretending an uncalibrated cosine is a probability.
        score = max(0.0, min(100.0, cosine * 100.0))
        views.append(
            AppearanceViewScore(
                source=str(source),
                cosine_similarity=round(cosine, 6),
                score=round(score, 3),
                azimuth=matched.best_azimuth,
                elevation=matched.best_elevation,
                up_axis=matched.best_up_axis,
                candidate_render=str(render_path) if render_path else None,
            )
        )

    final = aggregate_appearance_scores([v.score for v in views])
    return AppearanceScore(score=round(final, 3), views=views)


def main() -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="HAYUYA Judge v3 DINOv2 appearance scorer.")
    parser.add_argument("mesh", type=Path)
    parser.add_argument("--source", type=Path, action="append", required=True)
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--render-dir", type=Path)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()

    from visual_judge import score_candidate as score_visual

    visual = score_visual(args.mesh, args.source)
    result = score_candidate_appearance(
        args.mesh,
        args.source,
        visual.views,
        model_root=args.model_root,
        render_dir=args.render_dir,
        device=args.device,
    )
    print(json.dumps(asdict(result), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
