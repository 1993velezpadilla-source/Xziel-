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
    production_score: float | None = None
    visual_score: float | None = None
    visual_views: list[dict] | None = None
    appearance_score: float | None = None
    appearance_views: list[dict] | None = None
    normal_support_score: float | None = None
    normal_support_views: list[dict] | None = None
    vertices: int = 0
    faces: int = 0
    components: int = 0
    watertight: bool = False
    degenerate_ratio: float = 1.0
    has_uv: bool = False
    textured: bool = False
    pbr_channels: list[str] | None = None
    material_score: float = 0.0
    bbox: list[float] | None = None
    notes: list[str] | None = None


def _import_trimesh():
    try:
        import numpy as np
        import trimesh
        return np, trimesh
    except Exception:
        return None, None


def _material_channels(material) -> set[str]:
    channels: set[str] = set()
    if material is None:
        return channels

    if (
        getattr(material, "baseColorTexture", None) is not None
        or getattr(material, "image", None) is not None
        or getattr(material, "baseColorFactor", None) is not None
        or getattr(material, "diffuse", None) is not None
    ):
        channels.add("baseColor")

    if (
        getattr(material, "metallicRoughnessTexture", None) is not None
        or getattr(material, "metallicFactor", None) is not None
    ):
        channels.add("metallic")
    if (
        getattr(material, "metallicRoughnessTexture", None) is not None
        or getattr(material, "roughnessFactor", None) is not None
        or getattr(material, "glossiness", None) is not None
    ):
        channels.add("roughness")
    if getattr(material, "normalTexture", None) is not None:
        channels.add("normal")
    if getattr(material, "occlusionTexture", None) is not None:
        channels.add("occlusion")
    if (
        getattr(material, "emissiveTexture", None) is not None
        or getattr(material, "emissiveFactor", None) is not None
    ):
        channels.add("emissive")
    return channels


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

        # Build a geometry-only aggregate for topology metrics. Concatenating
        # textured/PBR visuals can invoke visual/material conversion paths and make
        # mesh health depend on material implementation details. Material evidence
        # is inspected separately on the original geometries below.
        metric_meshes = [
            trimesh.Trimesh(
                vertices=np.asarray(g.vertices),
                faces=np.asarray(g.faces),
                process=False,
            )
            for g in meshes
        ]
        mesh = trimesh.util.concatenate(metric_meshes)
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
        pbr_channels: set[str] = set()
        for g in meshes:
            visual = getattr(g, "visual", None)
            uv = getattr(visual, "uv", None)
            if uv is not None and len(uv):
                has_uv = True
            kind = str(getattr(visual, "kind", "")).lower()
            material = getattr(visual, "material", None)
            if "texture" in kind or material is not None:
                textured = True
            pbr_channels.update(_material_channels(material))
        result.has_uv = has_uv
        result.textured = textured
        result.pbr_channels = sorted(pbr_channels)

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

        # Material readiness is channel-aware. This remains only 18% of
        # production score, so PBR completeness can improve a close call but cannot
        # override contradictory real-source visual evidence.
        material = 0.0
        channels = set(result.pbr_channels or [])
        if result.has_uv:
            material += 0.25
        if "baseColor" in channels:
            material += 0.45
        elif result.textured:
            # Unknown/legacy texture still gets partial credit.
            material += 0.30
        if "normal" in channels:
            material += 0.10
        if "roughness" in channels:
            material += 0.10
        if "metallic" in channels:
            material += 0.05
        if "occlusion" in channels:
            material += 0.05
        material = min(1.0, material)
        result.material_score = round(material * 100.0, 3)
        if channels:
            result.notes.append("material channels: " + ",".join(sorted(channels)))

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
        result.production_score = result.score
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
    source_images: list[Path] | None = None,
    detail_images: list[Path] | None = None,
    visual_weight: float = 0.55,
    appearance_mode: str = "off",
    appearance_model_root: Path | None = None,
    appearance_render_root: Path | None = None,
    appearance_weight: float = 0.25,
    normal_support_images: dict[str, Path] | None = None,
    normal_support_weight: float = 0.06,
) -> list[MeshScore]:
    scores = [
        inspect_mesh(path, backend=backend, mode=mode, target_faces=target_faces)
        for backend, path in candidates
    ]

    if source_images:
        try:
            from visual_judge import score_candidate as score_visual
            from dataclasses import asdict as _asdict
        except Exception:
            score_visual = None
            _asdict = None

        if score_visual is not None:
            for item in scores:
                if not item.valid:
                    continue
                try:
                    visual = score_visual(Path(item.path), source_images)
                    item.production_score = item.production_score if item.production_score is not None else item.score
                    item.visual_score = visual.score
                    item.visual_views = [_asdict(v) for v in visual.views]
                    item.score = round(
                        item.production_score * (1.0 - visual_weight)
                        + item.visual_score * visual_weight,
                        3,
                    )
                    item.notes.append(
                        f"Judge v2 combined production={item.production_score:.3f} "
                        f"visual={item.visual_score:.3f} visual_weight={visual_weight:.2f}"
                    )

                    should_try_appearance = appearance_mode in {"auto", "required"}
                    if should_try_appearance:
                        model_root = appearance_model_root
                        dino_ready = bool(model_root and (model_root / "dinov2").is_dir())
                        if not dino_ready and appearance_mode == "required":
                            raise RuntimeError(
                                "Judge v3 required but DINOv2 is not bootstrapped under model_root"
                            )
                        if dino_ready:
                            try:
                                from appearance_judge import score_candidate_appearance
                                render_dir = (
                                    appearance_render_root / item.backend
                                    if appearance_render_root is not None
                                    else None
                                )
                                appearance = score_candidate_appearance(
                                    Path(item.path),
                                    source_images,
                                    visual.views,
                                    model_root=model_root,
                                    detail_images=detail_images or [],
                                    render_dir=render_dir,
                                )
                                item.appearance_score = appearance.score
                                item.appearance_views = [_asdict(v) for v in appearance.views]

                                # Preserve the proven v2 production:silhouette ratio inside
                                # the non-appearance share, then add DINO appearance evidence.
                                remaining = 1.0 - appearance_weight
                                production_w = (1.0 - visual_weight) * remaining
                                silhouette_w = visual_weight * remaining
                                item.score = round(
                                    item.production_score * production_w
                                    + item.visual_score * silhouette_w
                                    + item.appearance_score * appearance_weight,
                                    3,
                                )
                                item.notes.append(
                                    f"Judge v3 combined production={item.production_score:.3f} "
                                    f"silhouette={item.visual_score:.3f} "
                                    f"appearance={item.appearance_score:.3f} "
                                    f"weights={production_w:.4f}/{silhouette_w:.4f}/{appearance_weight:.4f}"
                                )
                            except Exception as exc:
                                item.notes.append(
                                    f"Judge v3 appearance unavailable: {type(exc).__name__}: {exc}"
                                )
                                if appearance_mode == "required":
                                    raise
                        else:
                            item.notes.append(
                                "Judge v3 auto skipped: DINOv2 evaluator not bootstrapped"
                            )
                except Exception as exc:
                    item.notes.append(
                        f"Judge v2/v3 score unavailable: {type(exc).__name__}: {exc}"
                    )
                    if appearance_mode == "required":
                        raise

                # Wonder3D normals are synthetic support evidence only. They never
                # replace real-source silhouette/appearance evidence and carry a
                # deliberately small final weight.
                if normal_support_images and item.valid and item.visual_views:
                    try:
                        from normal_judge import score_candidate_normals
                        from visual_judge import SourceViewScore

                        first = item.visual_views[0]
                        anchor = SourceViewScore(**first)
                        normal_support = score_candidate_normals(
                            Path(item.path),
                            normal_support_images,
                            anchor,
                        )
                        item.normal_support_score = normal_support.score
                        item.normal_support_views = [_asdict(v) for v in normal_support.views]
                        prior = item.score
                        item.score = round(
                            prior * (1.0 - normal_support_weight)
                            + item.normal_support_score * normal_support_weight,
                            3,
                        )
                        item.notes.append(
                            f"synthetic normal support={item.normal_support_score:.3f} "
                            f"weight={normal_support_weight:.3f}"
                        )
                    except Exception as exc:
                        item.notes.append(
                            f"synthetic normal support unavailable: {type(exc).__name__}: {exc}"
                        )

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
    parser.add_argument("--source", type=Path, action="append", help="real geometry source image; repeatable")
    parser.add_argument("--detail", type=Path, action="append", help="detail/close-up reference image; repeatable")
    parser.add_argument("--visual-weight", type=float, default=0.55)
    parser.add_argument("--appearance-mode", choices=["off", "auto", "required"], default="off")
    parser.add_argument("--appearance-model-root", type=Path)
    parser.add_argument("--appearance-render-root", type=Path)
    parser.add_argument("--appearance-weight", type=float, default=0.25)
    parser.add_argument("--normal-support", type=Path, action="append", default=[], help="view=path")
    parser.add_argument("--normal-support-weight", type=float, default=0.06)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()

    normal_support_images = {}
    for item in args.normal_support:
        view, raw = str(item).split("=", 1)
        normal_support_images[view] = Path(raw)

    ranked = rank_candidates(
        [(p.stem, p) for p in args.mesh],
        mode="prop" if args.mode == "auto" else args.mode,
        target_faces=args.target_faces,
        source_images=args.source,
        detail_images=args.detail,
        visual_weight=args.visual_weight,
        appearance_mode=args.appearance_mode,
        appearance_model_root=args.appearance_model_root,
        appearance_render_root=args.appearance_render_root,
        appearance_weight=args.appearance_weight,
        normal_support_images=normal_support_images or None,
        normal_support_weight=args.normal_support_weight,
    )
    data = [asdict(x) for x in ranked]
    print(json.dumps(data, indent=2))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return 0 if ranked and ranked[0].valid else 2


if __name__ == "__main__":
    raise SystemExit(main())
