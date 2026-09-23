#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class MeshScore:
    path: str
    backend: str
    score: float
    valid: bool
    vertices: int = 0
    faces: int = 0
    components: int = 0
    watertight: bool = False
    degenerate_ratio: float = 1.0
    has_uv: bool = False
    textured: bool = False
    bbox: list[float] | None = None
    notes: list[str] | None = None


def _import_trimesh():
    try:
        import numpy as np
        import trimesh
        return np, trimesh
    except Exception:
        return None, None


def _basic_valid(path: Path) -> tuple[bool, list[str]]:
    notes: list[str] = []
    if not path.is_file():
        return False, ["missing file"]
    size = path.stat().st_size
    if size < 256:
        return False, [f"file too small: {size} bytes"]
    if path.suffix.lower() == ".glb":
        if path.read_bytes()[:4] != b"glTF":
            return False, ["bad GLB magic"]
    elif path.suffix.lower() not in {".obj", ".gltf", ".ply", ".stl"}:
        notes.append(f"unrecognized mesh extension: {path.suffix}")
    return True, notes


def inspect_mesh(
    path: Path,
    *,
    backend: str = "unknown",
    mode: str = "prop",
    target_faces: int = 100_000,
) -> MeshScore:
    valid, notes = _basic_valid(path)
    result = MeshScore(
        path=str(path),
        backend=backend,
        score=0.0,
        valid=valid,
        notes=notes,
    )
    if not valid:
        return result

    np, trimesh = _import_trimesh()
    if trimesh is None:
        # File-level fallback keeps Hayuya usable in lightweight CI.
        size_mb = path.stat().st_size / (1024 * 1024)
        result.score = round(min(45.0, 20.0 + math.log2(max(size_mb, 0.01) + 1) * 8.0), 3)
        result.notes.append("trimesh unavailable: file-level score only")
        return result

    try:
        loaded = trimesh.load(path, force="scene", process=False)
        geometries = list(loaded.geometry.values()) if hasattr(loaded, "geometry") else [loaded]
        meshes = [g for g in geometries if hasattr(g, "faces") and len(g.faces)]
        if not meshes:
            result.valid = False
            result.notes.append("no triangle mesh geometry")
            return result

        mesh = trimesh.util.concatenate(meshes)
        result.vertices = int(len(mesh.vertices))
        result.faces = int(len(mesh.faces))
        result.components = len(mesh.split(only_watertight=False))
        result.watertight = bool(mesh.is_watertight)

        areas = np.asarray(mesh.area_faces)
        if len(areas):
            finite = areas[np.isfinite(areas)]
            if len(finite):
                scale = max(float(np.median(finite)), 1e-15)
                result.degenerate_ratio = float(np.mean(areas <= scale * 1e-6))
            else:
                result.degenerate_ratio = 1.0

        extents = np.asarray(mesh.extents, dtype=float)
        result.bbox = [round(float(x), 8) for x in extents.tolist()]

        has_uv = False
        textured = False
        for g in meshes:
            visual = getattr(g, "visual", None)
            uv = getattr(visual, "uv", None)
            if uv is not None and len(uv):
                has_uv = True
            kind = str(getattr(visual, "kind", "")).lower()
            material = getattr(visual, "material", None)
            if "texture" in kind or material is not None:
                textured = True
        result.has_uv = has_uv
        result.textured = textured

        if result.faces < 50:
            result.notes.append("extremely low face count")
        if result.components > 12:
            result.notes.append(f"many disconnected components: {result.components}")
        if result.degenerate_ratio > 0.02:
            result.notes.append(f"high degenerate ratio: {result.degenerate_ratio:.4f}")
        if not np.all(np.isfinite(mesh.vertices)):
            result.valid = False
            result.notes.append("non-finite vertices")
            return result

        # Hayuya Judge v1: geometry capacity + topology health + production readiness.
        face_ratio = min(1.0, result.faces / max(1, target_faces))
        face_floor = min(1.0, result.faces / 5000.0)
        geometry = 0.70 * face_ratio + 0.30 * face_floor

        comp_penalty = min(0.45, max(0, result.components - 1) * 0.04)
        degen_penalty = min(0.55, result.degenerate_ratio * 12.0)
        health = max(0.0, 1.0 - comp_penalty - degen_penalty)

        # Closed meshes matter more for props/architecture; cloth/characters may intentionally be open.
        if mode in {"prop", "architecture"}:
            health = min(1.0, health + (0.10 if result.watertight else -0.05))
        elif result.watertight:
            health = min(1.0, health + 0.03)

        material = 0.0
        if result.has_uv:
            material += 0.45
        if result.textured:
            material += 0.55

        bbox_health = 1.0
        if result.bbox:
            positive = [x for x in result.bbox if x > 1e-9]
            if len(positive) != 3:
                bbox_health = 0.0
                result.notes.append("collapsed bounding box axis")
            else:
                ratio = max(positive) / min(positive)
                if ratio > 100:
                    bbox_health = 0.55
                    result.notes.append(f"extreme bbox aspect ratio: {ratio:.1f}")

        raw = (
            geometry * 0.42
            + health * 0.33
            + material * 0.18
            + bbox_health * 0.07
        )
        result.score = round(max(0.0, min(100.0, raw * 100.0)), 3)
        return result
    except Exception as exc:
        result.valid = False
        result.notes.append(f"mesh inspection failed: {type(exc).__name__}: {exc}")
        return result


def rank_candidates(
    candidates: Iterable[tuple[str, Path]],
    *,
    mode: str,
    target_faces: int,
) -> list[MeshScore]:
    scores = [
        inspect_mesh(path, backend=backend, mode=mode, target_faces=target_faces)
        for backend, path in candidates
    ]
    return sorted(scores, key=lambda x: (x.valid, x.score), reverse=True)


def export_glb(src: Path, dst: Path) -> Path:
    if src.suffix.lower() == ".glb":
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
        return dst

    np, trimesh = _import_trimesh()
    if trimesh is None:
        raise RuntimeError("trimesh is required to normalize non-GLB candidates")

    scene = trimesh.load(src, force="scene", process=False)
    dst.parent.mkdir(parents=True, exist_ok=True)
    blob = trimesh.exchange.gltf.export_glb(scene)
    dst.write_bytes(blob)
    if dst.read_bytes()[:4] != b"glTF":
        raise RuntimeError("normalized GLB failed magic check")
    return dst


def main() -> int:
    parser = argparse.ArgumentParser(description="Score Hayuya candidate meshes.")
    parser.add_argument("mesh", type=Path, nargs="+")
    parser.add_argument("--mode", choices=["auto", "prop", "character", "architecture"], default="prop")
    parser.add_argument("--target-faces", type=int, default=100000)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()

    ranked = rank_candidates(
        [(p.stem, p) for p in args.mesh],
        mode="prop" if args.mode == "auto" else args.mode,
        target_faces=args.target_faces,
    )
    data = [asdict(x) for x in ranked]
    print(json.dumps(data, indent=2))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return 0 if ranked and ranked[0].valid else 2


if __name__ == "__main__":
    raise SystemExit(main())
