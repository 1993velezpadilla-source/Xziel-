#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class MaterialBridgeResult:
    source_mesh: str
    refined_mesh: str
    output_glb: str
    sample_count: int
    refined_vertices: int
    method: str = "surface-sample nearest-color projection"
    preserves: str = "base color via vertex colors"
    future: str = "UV/PBR rebake for normal/roughness/metallic/AO"


def _deps():
    import numpy as np
    import trimesh
    return np, trimesh


def _scene_meshes(path: Path):
    _, trimesh = _deps()
    scene = trimesh.load(path, force="scene", process=False)
    meshes = []

    if hasattr(scene, "graph") and hasattr(scene, "geometry"):
        for node_name in scene.graph.nodes_geometry:
            transform, geom_name = scene.graph[node_name]
            geom = scene.geometry[geom_name]
            if not hasattr(geom, "faces") or not len(geom.faces):
                continue
            mesh = geom.copy()
            mesh.apply_transform(transform)
            meshes.append(mesh)
    elif hasattr(scene, "faces") and len(scene.faces):
        meshes.append(scene.copy())

    if not meshes:
        raise ValueError(f"no triangle geometry in {path}")
    return meshes


def sample_texture_nearest(texture, uv):
    np, _ = _deps()
    texture = np.asarray(texture)
    if texture.ndim == 2:
        texture = np.repeat(texture[..., None], 3, axis=2)
    texture = texture[..., :3]
    h, w = texture.shape[:2]
    u = np.mod(uv[:, 0], 1.0)
    v = np.mod(uv[:, 1], 1.0)
    x = np.clip(np.rint(u * (w - 1)).astype(np.int64), 0, w - 1)
    y = np.clip(np.rint((1.0 - v) * (h - 1)).astype(np.int64), 0, h - 1)
    return texture[y, x, :3].astype(np.float32)


def _material_image(material):
    if material is None:
        return None
    image = getattr(material, "image", None)
    if image is None:
        image = getattr(material, "baseColorTexture", None)
    if image is None:
        return None

    np, _ = _deps()
    try:
        from PIL import Image
        if isinstance(image, Image.Image):
            return np.asarray(image.convert("RGB"), dtype=np.uint8)
        arr = np.asarray(image)
        if arr.ndim == 2:
            arr = np.repeat(arr[..., None], 3, axis=2)
        return np.clip(arr[..., :3], 0, 255).astype(np.uint8)
    except Exception:
        return None


def _surface_samples_with_color(mesh, count: int):
    np, trimesh = _deps()
    points, face_ids = trimesh.sample.sample_surface(mesh, count)
    face_ids = np.asarray(face_ids, dtype=np.int64)
    triangles = np.asarray(mesh.triangles[face_ids], dtype=np.float64)
    bary = trimesh.triangles.points_to_barycentric(
        triangles,
        np.asarray(points, dtype=np.float64),
    )

    visual = getattr(mesh, "visual", None)
    uv = getattr(visual, "uv", None) if visual is not None else None
    material = getattr(visual, "material", None) if visual is not None else None
    texture = _material_image(material)

    colors = None
    if uv is not None and len(uv) == len(mesh.vertices) and texture is not None:
        uv_arr = np.asarray(uv, dtype=np.float64)
        uv_tri = uv_arr[np.asarray(mesh.faces, dtype=np.int64)[face_ids]]
        sample_uv = np.sum(uv_tri * bary[..., None], axis=1)
        colors = sample_texture_nearest(texture, sample_uv)

    if colors is None and visual is not None:
        try:
            converted = visual.to_color()
            vertex_colors = np.asarray(converted.vertex_colors[:, :3], dtype=np.float32)
            if len(vertex_colors) == len(mesh.vertices):
                color_tri = vertex_colors[
                    np.asarray(mesh.faces, dtype=np.int64)[face_ids]
                ]
                colors = np.sum(color_tri * bary[..., None], axis=1)
        except Exception:
            colors = None

    if colors is None:
        colors = np.full((len(points), 3), 190.0, dtype=np.float32)

    return np.asarray(points, dtype=np.float32), np.asarray(colors, dtype=np.float32)


def build_source_color_cloud(source_mesh: Path, total_samples: int = 250_000):
    np, _ = _deps()
    meshes = _scene_meshes(source_mesh)
    areas = np.asarray([max(float(m.area), 1e-9) for m in meshes], dtype=np.float64)
    weights = areas / areas.sum()

    points_all = []
    colors_all = []
    remaining = total_samples
    for index, (mesh, weight) in enumerate(zip(meshes, weights)):
        if index == len(meshes) - 1:
            count = max(1000, remaining)
        else:
            count = max(1000, int(round(total_samples * float(weight))))
            remaining -= count
        points, colors = _surface_samples_with_color(mesh, count)
        points_all.append(points)
        colors_all.append(colors)

    return np.concatenate(points_all, axis=0), np.concatenate(colors_all, axis=0)


def transfer_base_color(
    source_mesh: Path,
    refined_mesh: Path,
    output_glb: Path,
    *,
    total_samples: int = 250_000,
) -> MaterialBridgeResult:
    np, trimesh = _deps()
    from scipy.spatial import cKDTree

    points, colors = build_source_color_cloud(
        source_mesh,
        total_samples=total_samples,
    )
    tree = cKDTree(points)

    refined_meshes = _scene_meshes(refined_mesh)
    refined = trimesh.util.concatenate(refined_meshes)
    vertices = np.asarray(refined.vertices, dtype=np.float32)

    projected = np.empty((len(vertices), 3), dtype=np.uint8)
    chunk = 200_000
    for start in range(0, len(vertices), chunk):
        end = min(len(vertices), start + chunk)
        _, ids = tree.query(vertices[start:end], k=1, workers=-1)
        projected[start:end] = np.clip(colors[ids], 0, 255).astype(np.uint8)

    alpha = np.full((len(vertices), 1), 255, dtype=np.uint8)
    rgba = np.concatenate([projected, alpha], axis=1)
    refined.visual = trimesh.visual.ColorVisuals(
        refined,
        vertex_colors=rgba,
    )

    output_glb.parent.mkdir(parents=True, exist_ok=True)
    output_glb.write_bytes(
        trimesh.exchange.gltf.export_glb(trimesh.Scene(refined))
    )
    if output_glb.read_bytes()[:4] != b"glTF":
        raise RuntimeError("Material Bridge produced invalid GLB")

    return MaterialBridgeResult(
        source_mesh=str(source_mesh),
        refined_mesh=str(refined_mesh),
        output_glb=str(output_glb),
        sample_count=len(points),
        refined_vertices=len(vertices),
    )


def main() -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="HAYUYA Material Bridge v1 base-color transfer.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--refined", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=250000)
    args = parser.parse_args()

    result = transfer_base_color(
        args.source,
        args.refined,
        args.output,
        total_samples=args.samples,
    )
    print(json.dumps(asdict(result), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
