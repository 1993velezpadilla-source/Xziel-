#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SurfaceTransferRelation:
    triangle_vertex_ids: object
    barycentric: object
    surface_distance: object
    nearest_vertex_ids: object
    candidate_triangles: int
    fallback_vertices: int
    method: str = "hayuya-surface-transfer-barycentric-v1"


def _deps():
    import numpy as np
    from scipy.spatial import cKDTree
    return np, cKDTree


def _closest_point_barycentric(point, a, b, c):
    """Closest point on triangle using Ericson region tests.

    Returns (closest_point, barycentric). Degenerate triangles return None.
    """
    np, _ = _deps()
    p = np.asarray(point, dtype=np.float64)
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    c = np.asarray(c, dtype=np.float64)

    ab = b - a
    ac = c - a
    normal = np.cross(ab, ac)
    area2 = float(np.dot(normal, normal))
    if not np.isfinite(area2) or area2 <= 1e-24:
        return None

    ap = p - a
    d1 = float(np.dot(ab, ap))
    d2 = float(np.dot(ac, ap))
    if d1 <= 0.0 and d2 <= 0.0:
        return a, np.asarray([1.0, 0.0, 0.0], dtype=np.float64)

    bp = p - b
    d3 = float(np.dot(ab, bp))
    d4 = float(np.dot(ac, bp))
    if d3 >= 0.0 and d4 <= d3:
        return b, np.asarray([0.0, 1.0, 0.0], dtype=np.float64)

    vc = d1 * d4 - d3 * d2
    if vc <= 0.0 and d1 >= 0.0 and d3 <= 0.0:
        denom = d1 - d3
        v = 0.0 if abs(denom) <= 1e-24 else d1 / denom
        return a + v * ab, np.asarray([1.0 - v, v, 0.0], dtype=np.float64)

    cp = p - c
    d5 = float(np.dot(ab, cp))
    d6 = float(np.dot(ac, cp))
    if d6 >= 0.0 and d5 <= d6:
        return c, np.asarray([0.0, 0.0, 1.0], dtype=np.float64)

    vb = d5 * d2 - d1 * d6
    if vb <= 0.0 and d2 >= 0.0 and d6 <= 0.0:
        denom = d2 - d6
        w = 0.0 if abs(denom) <= 1e-24 else d2 / denom
        return a + w * ac, np.asarray([1.0 - w, 0.0, w], dtype=np.float64)

    va = d3 * d6 - d5 * d4
    if va <= 0.0 and (d4 - d3) >= 0.0 and (d5 - d6) >= 0.0:
        bc = c - b
        denom = (d4 - d3) + (d5 - d6)
        w = 0.0 if abs(denom) <= 1e-24 else (d4 - d3) / denom
        return b + w * bc, np.asarray([0.0, 1.0 - w, w], dtype=np.float64)

    denom = va + vb + vc
    if abs(denom) <= 1e-24:
        return None
    inv = 1.0 / denom
    v = vb * inv
    w = vc * inv
    u = 1.0 - v - w
    bary = np.asarray([u, v, w], dtype=np.float64)
    closest = u * a + v * b + w * c
    return closest, bary


def build_surface_transfer_relation(
    source_positions,
    source_faces,
    target_positions,
    *,
    candidate_triangles: int = 32,
) -> SurfaceTransferRelation:
    np, cKDTree = _deps()
    vertices = np.asarray(source_positions, dtype=np.float64)
    faces = np.asarray(source_faces, dtype=np.int64)
    targets = np.asarray(target_positions, dtype=np.float64)

    if vertices.ndim != 2 or vertices.shape[1] != 3 or not len(vertices):
        raise ValueError("surface-transfer source positions must be non-empty Nx3")
    if faces.ndim != 2 or faces.shape[1] != 3 or not len(faces):
        raise ValueError("surface-transfer source faces must be non-empty Mx3")
    if targets.ndim != 2 or targets.shape[1] != 3:
        raise ValueError("surface-transfer targets must be Nx3")
    if int(np.min(faces)) < 0 or int(np.max(faces)) >= len(vertices):
        raise ValueError("surface-transfer faces reference missing vertices")
    if not (
        np.isfinite(vertices).all()
        and np.isfinite(targets).all()
    ):
        raise ValueError("surface-transfer geometry contains non-finite values")

    triangles = vertices[faces]
    centroids = np.mean(triangles, axis=1)
    centroid_tree = cKDTree(centroids)
    vertex_tree = cKDTree(vertices)

    k = max(1, min(int(candidate_triangles), len(faces)))
    _, candidate_rows = centroid_tree.query(
        targets,
        k=k,
        workers=-1,
    )
    candidate_rows = np.asarray(candidate_rows, dtype=np.int64)
    if k == 1:
        candidate_rows = candidate_rows[:, None]

    _, nearest_vertices = vertex_tree.query(
        targets,
        k=1,
        workers=-1,
    )
    nearest_vertices = np.asarray(nearest_vertices, dtype=np.int64)

    triangle_vertex_ids = np.zeros((len(targets), 3), dtype=np.int64)
    barycentric = np.zeros((len(targets), 3), dtype=np.float64)
    distances = np.zeros(len(targets), dtype=np.float64)
    fallback_vertices = 0

    # Build vertex->triangle adjacency. This closes a centroid-KD blind spot
    # for long/slender triangles whose centroid can be farther away than the
    # nearest surface point.
    adjacency = [[] for _ in range(len(vertices))]
    for face_index, tri in enumerate(faces):
        for vertex_id in tri:
            adjacency[int(vertex_id)].append(int(face_index))

    for row, point in enumerate(targets):
        candidate_ids = set(int(x) for x in candidate_rows[row].tolist())
        candidate_ids.update(adjacency[int(nearest_vertices[row])])

        best = None
        for face_index in candidate_ids:
            tri_ids = faces[int(face_index)]
            result = _closest_point_barycentric(
                point,
                vertices[int(tri_ids[0])],
                vertices[int(tri_ids[1])],
                vertices[int(tri_ids[2])],
            )
            if result is None:
                continue
            closest, bary = result
            distance = float(np.linalg.norm(point - closest))
            if not np.isfinite(distance):
                continue
            if best is None or distance < best[0]:
                best = (
                    distance,
                    np.asarray(tri_ids, dtype=np.int64),
                    np.asarray(bary, dtype=np.float64),
                )

        if best is None:
            # Fail soft only for fully-degenerate local topology. This keeps
            # the relation defined while making the fallback count observable.
            vertex_id = int(nearest_vertices[row])
            triangle_vertex_ids[row] = [vertex_id, vertex_id, vertex_id]
            barycentric[row] = [1.0, 0.0, 0.0]
            distances[row] = float(
                np.linalg.norm(point - vertices[vertex_id])
            )
            fallback_vertices += 1
            continue

        distance, tri_ids, bary = best
        bary = np.maximum(bary, 0.0)
        total = float(np.sum(bary))
        if total <= 1e-12:
            raise RuntimeError(
                f"surface-transfer target {row} received invalid barycentrics"
            )
        bary /= total
        triangle_vertex_ids[row] = tri_ids
        barycentric[row] = bary
        distances[row] = distance

    return SurfaceTransferRelation(
        triangle_vertex_ids=triangle_vertex_ids,
        barycentric=barycentric,
        surface_distance=distances,
        nearest_vertex_ids=nearest_vertices,
        candidate_triangles=k,
        fallback_vertices=int(fallback_vertices),
    )


def blend_joint_weights_from_relation(
    source_joints,
    source_weights,
    relation: SurfaceTransferRelation,
):
    np, _ = _deps()
    joints = np.asarray(source_joints, dtype=np.int64)
    weights = np.asarray(source_weights, dtype=np.float64)
    triangles = np.asarray(
        relation.triangle_vertex_ids,
        dtype=np.int64,
    )
    bary = np.asarray(relation.barycentric, dtype=np.float64)

    out_joints = np.zeros((len(triangles), 4), dtype=np.int64)
    out_weights = np.zeros((len(triangles), 4), dtype=np.float64)

    for row, (tri_ids, tri_weights) in enumerate(zip(triangles, bary)):
        accumulated: dict[int, float] = {}
        for vertex_id, spatial_weight in zip(tri_ids, tri_weights):
            for joint, skin_weight in zip(
                joints[int(vertex_id)],
                weights[int(vertex_id)],
            ):
                contribution = float(spatial_weight) * float(skin_weight)
                if contribution <= 1e-12:
                    continue
                accumulated[int(joint)] = (
                    accumulated.get(int(joint), 0.0) + contribution
                )

        strongest = sorted(
            accumulated.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:4]
        total = sum(weight for _, weight in strongest)
        if total <= 1e-12:
            raise RuntimeError(
                f"surface-transfer target {row} received no skin influence"
            )
        for slot, (joint, weight) in enumerate(strongest):
            out_joints[row, slot] = int(joint)
            out_weights[row, slot] = float(weight / total)

    return out_joints, out_weights


def interpolate_vertex_values(values, relation: SurfaceTransferRelation):
    np, _ = _deps()
    source = np.asarray(values, dtype=np.float64)
    triangles = np.asarray(
        relation.triangle_vertex_ids,
        dtype=np.int64,
    )
    bary = np.asarray(relation.barycentric, dtype=np.float64)
    if source.ndim < 2 or len(source) <= int(np.max(triangles)):
        raise ValueError(
            "surface-transfer source values do not cover relation vertices"
        )
    gathered = source[triangles]
    shape = (len(bary), 3) + (1,) * (gathered.ndim - 2)
    return np.sum(gathered * bary.reshape(shape), axis=1)
