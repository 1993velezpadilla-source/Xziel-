#!/usr/bin/env python3
"""Resolve BO3 Nacht purchase-marker geometry into XZIEL-ready gameplay slots.

The Pavlov port keeps only three functional WallBuy_C actors, but the imported
Zombies Chronicles geometry preserves nine purchase markers. This tool uses the
three functional wall buys as calibration anchors and the baked marker meshes
as spatial evidence for the remaining slots.

Input:
  1. nacht-spatial-manifest.json from extract_pavlov_nacht_layout.py
  2. directory containing glTF/GLB exports of the nine chalk marker meshes

Output:
  resolved JSON with all nine purchase slots, source geometry bounds,
  calibration diagnostics, and XZIEL-friendly transforms.

No third-party mesh or texture payload is embedded in the output.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np
import trimesh

MARKER_RE = re.compile(r"chalk_buy_([a-z0-9_]+)", re.I)


def vector_xyz(value: dict[str, Any] | None) -> np.ndarray | None:
    if not isinstance(value, dict):
        return None
    try:
        return np.array(
            [
                float(value.get("X", value.get("x", 0.0))),
                float(value.get("Y", value.get("y", 0.0))),
                float(value.get("Z", value.get("z", 0.0))),
            ],
            dtype=float,
        )
    except (TypeError, ValueError):
        return None


def find_marker(path: Path) -> str | None:
    m = MARKER_RE.search(path.stem.lower())
    if m:
        return m.group(1)
    m = MARKER_RE.search(path.as_posix().lower())
    return m.group(1) if m else None


def load_scene_vertices(path: Path) -> np.ndarray:
    loaded = trimesh.load(path, force="scene", process=False)
    if isinstance(loaded, trimesh.Trimesh):
        return np.asarray(loaded.vertices, dtype=float)
    verts: list[np.ndarray] = []
    for node_name in loaded.graph.nodes_geometry:
        transform, geom_name = loaded.graph[node_name]
        geom = loaded.geometry[geom_name]
        if not isinstance(geom, trimesh.Trimesh) or len(geom.vertices) == 0:
            continue
        verts.append(
            trimesh.transform_points(
                np.asarray(geom.vertices, dtype=float),
                np.asarray(transform, dtype=float),
            )
        )
    if not verts:
        raise ValueError(f"no mesh vertices in {path}")
    return np.vstack(verts)


def geometry_info(path: Path) -> dict[str, Any]:
    verts = load_scene_vertices(path)
    bmin = verts.min(axis=0)
    bmax = verts.max(axis=0)
    center = (bmin + bmax) * 0.5
    mean = verts.mean(axis=0)

    centered = verts - mean
    covariance = np.cov(centered, rowvar=False)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    normal = eigenvectors[:, int(np.argmin(eigenvalues))]
    normal = normal / max(np.linalg.norm(normal), 1e-12)

    return {
        "file": path.name,
        "vertex_count": int(len(verts)),
        "bounds_min": bmin.tolist(),
        "bounds_max": bmax.tolist(),
        "bounds_center": center.tolist(),
        "centroid": mean.tolist(),
        "plane_normal": normal.tolist(),
        "plane_eigenvalues": eigenvalues.tolist(),
    }


def transform_axis(v: np.ndarray, perm: tuple[int, int, int], signs: tuple[int, int, int]) -> np.ndarray:
    return np.array(
        [v[perm[i]] * signs[i] for i in range(3)],
        dtype=float,
    )


def calibrate(
    source: dict[str, np.ndarray],
    target: dict[str, np.ndarray],
) -> dict[str, Any]:
    common = sorted(set(source) & set(target))
    if len(common) < 3:
        raise ValueError(f"need 3 calibration anchors, got {common}")

    best: dict[str, Any] | None = None
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((-1, 1), repeat=3):
            xs = np.stack([transform_axis(source[k], perm, signs) for k in common])
            ys = np.stack([target[k] for k in common])
            xm = xs.mean(axis=0)
            ym = ys.mean(axis=0)
            xd = xs - xm
            yd = ys - ym
            denom = float(np.sum(xd * xd))
            if denom <= 1e-12:
                continue
            scale = float(np.sum(xd * yd) / denom)
            if scale <= 0:
                continue
            translation = ym - scale * xm
            predicted = xs * scale + translation
            error = predicted - ys
            rmse = float(np.sqrt(np.mean(np.sum(error * error, axis=1))))
            candidate = {
                "perm": list(perm),
                "signs": list(signs),
                "scale": scale,
                "translation": translation.tolist(),
                "rmse_cm": rmse,
                "anchors": common,
                "predicted": {k: predicted[i].tolist() for i, k in enumerate(common)},
                "target": {k: ys[i].tolist() for i, k in enumerate(common)},
            }
            if best is None or rmse < best["rmse_cm"]:
                best = candidate
    if best is None:
        raise ValueError("could not solve axis calibration")
    return best


def apply_calibration(v: np.ndarray, calibration: dict[str, Any]) -> np.ndarray:
    perm = tuple(int(x) for x in calibration["perm"])
    signs = tuple(int(x) for x in calibration["signs"])
    axis = transform_axis(v, perm, signs)
    return axis * float(calibration["scale"]) + np.asarray(calibration["translation"], dtype=float)


def apply_direction(v: np.ndarray, calibration: dict[str, Any]) -> np.ndarray:
    perm = tuple(int(x) for x in calibration["perm"])
    signs = tuple(int(x) for x in calibration["signs"])
    axis = transform_axis(v, perm, signs)
    axis = axis / max(np.linalg.norm(axis), 1e-12)
    return axis


def xyz_dict(v: np.ndarray) -> dict[str, float]:
    return {"x": float(v[0]), "y": float(v[1]), "z": float(v[2])}


def yaw_from_normal(normal: np.ndarray) -> float | None:
    xy = np.array([normal[0], normal[1]], dtype=float)
    n = np.linalg.norm(xy)
    if n < 1e-8:
        return None
    xy /= n
    return float(math.degrees(math.atan2(xy[1], xy[0])))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("spatial_manifest", type=Path)
    ap.add_argument("marker_glb_dir", type=Path)
    ap.add_argument("output_json", type=Path)
    args = ap.parse_args()

    spatial = json.loads(args.spatial_manifest.read_text(encoding="utf-8"))
    slots = spatial.get("bo3_purchase_slots") or []
    if len(slots) != 9:
        raise SystemExit(f"expected 9 purchase slots, got {len(slots)}")

    glbs = list(args.marker_glb_dir.rglob("*.glb"))
    geometry: dict[str, dict[str, Any]] = {}
    duplicates: dict[str, list[str]] = {}
    for path in glbs:
        marker = find_marker(path)
        if not marker:
            continue
        info = geometry_info(path)
        if marker in geometry:
            duplicates.setdefault(marker, [geometry[marker]["file"]]).append(path.name)
            continue
        geometry[marker] = info

    expected = {slot["source_marker"] for slot in slots}
    missing = sorted(expected - set(geometry))
    if missing:
        raise SystemExit(f"missing marker GLBs: {missing}")

    functional_sources: dict[str, np.ndarray] = {}
    functional_targets: dict[str, np.ndarray] = {}
    for slot in slots:
        if not slot.get("functional_actor"):
            continue
        marker = slot["source_marker"]
        source_center = np.asarray(geometry[marker]["bounds_center"], dtype=float)
        transform = slot.get("transform") or {}
        pos = vector_xyz(transform.get("location"))
        if pos is None:
            continue
        functional_sources[marker] = source_center
        functional_targets[marker] = pos

    calibration = calibrate(functional_sources, functional_targets)

    resolved = []
    for slot in slots:
        marker = slot["source_marker"]
        info = geometry[marker]
        source_center = np.asarray(info["bounds_center"], dtype=float)
        estimated_position = apply_calibration(source_center, calibration)
        source_normal = np.asarray(info["plane_normal"], dtype=float)
        ue_normal = apply_direction(source_normal, calibration)
        yaw = yaw_from_normal(ue_normal)

        existing_transform = slot.get("transform")
        if existing_transform and vector_xyz(existing_transform.get("location")) is not None:
            position = vector_xyz(existing_transform["location"])
            placement_source = "functional_wallbuy_actor"
            rotation = existing_transform.get("rotation")
            confidence = "authoritative_port_actor"
        else:
            position = estimated_position
            placement_source = "calibrated_marker_mesh_bounds"
            rotation = None
            confidence = "geometry_derived"

        yaw_candidates = None
        if yaw is not None:
            yaw_candidates = [yaw, (yaw + 180.0) % 360.0]

        resolved.append({
            **slot,
            "transform": {
                "position": xyz_dict(position),
                "rotation": rotation,
                "scale": None,
            },
            "placement_source": placement_source,
            "needs_geometry_resolution": False,
            "placement_confidence": confidence,
            "marker_geometry": info,
            "surface_normal_ue": xyz_dict(ue_normal),
            "yaw_candidates": yaw_candidates,
            "runtime_orientation_policy": (
                "use authored actor rotation"
                if rotation
                else "choose yaw candidate facing reachable/navmesh free space"
            ),
        })

    output = {
        "schemaVersion": 1,
        "source": spatial.get("source"),
        "calibration": calibration,
        "duplicate_marker_exports": duplicates,
        "summary": {
            "slot_count": len(resolved),
            "functional_actor_slots": sum(
                1 for r in resolved if r["placement_source"] == "functional_wallbuy_actor"
            ),
            "geometry_derived_slots": sum(
                1 for r in resolved if r["placement_source"] == "calibrated_marker_mesh_bounds"
            ),
            "weapon_or_cabinet_slots": sum(
                1 for r in resolved if r["type"] in {"wallbuy", "sniper_cabinet"}
            ),
            "equipment_slots": sum(1 for r in resolved if r["type"] == "equipment"),
            "calibration_rmse_cm": calibration["rmse_cm"],
        },
        "purchase_slots": resolved,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output["summary"], indent=2))

    # Hard gates: complete slot inventory and a sane calibration. The latter is
    # intentionally generous because actor roots and chalk-mesh centers are not
    # required to coincide exactly.
    if len(resolved) != 9:
        return 3
    if calibration["rmse_cm"] > 250.0:
        print("CALIBRATION_RMSE_TOO_HIGH", calibration["rmse_cm"])
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
