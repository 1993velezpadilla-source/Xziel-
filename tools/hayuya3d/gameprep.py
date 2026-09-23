#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

from material_bridge import (
    _scene_meshes,
    build_source_color_cloud,
    transfer_base_color_from_cloud,
)
from visual_judge import SourceViewScore


@dataclass
class LODArtifact:
    name: str
    path: str
    target_faces: int
    actual_faces: int
    material_policy: str


@dataclass
class GamePrepResult:
    master: str
    lods: list[LODArtifact]
    collision: str | None
    turntable_frames: list[str]
    manifest: str
    source_faces: int
    target_lod0_faces: int


def _deps():
    import trimesh
    return trimesh


def load_combined_mesh(path: Path):
    trimesh = _deps()
    meshes = _scene_meshes(path)
    return trimesh.util.concatenate(meshes)


def export_glb(mesh, path: Path) -> Path:
    trimesh = _deps()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(trimesh.exchange.gltf.export_glb(trimesh.Scene(mesh)))
    if path.read_bytes()[:4] != b"glTF":
        raise RuntimeError(f"invalid GLB export: {path}")
    return path


def simplify_to_faces(mesh, target_faces: int):
    target_faces = max(4, int(target_faces))
    if len(mesh.faces) <= target_faces:
        return mesh.copy()
    simplified = mesh.simplify_quadric_decimation(
        face_count=target_faces,
        aggression=7,
    )
    if simplified is None or not len(simplified.faces):
        raise RuntimeError("quadric simplification returned empty mesh")
    return simplified


def build_turntable(
    master_glb: Path,
    out_dir: Path,
    *,
    anchor_view: SourceViewScore | None,
) -> list[str]:
    from appearance_judge import _mesh_rgb_arrays, render_candidate_rgb_arrays

    vertices, faces, colors, uvs, face_texture_ids, textures = _mesh_rgb_arrays(
        master_glb,
        max_faces=16000,
    )
    if anchor_view is None:
        anchor_view = SourceViewScore(
            source="gameprep",
            best_score=0.0,
            best_azimuth=0.0,
            best_elevation=0.0,
            best_up_axis="y",
            silhouette_iou=0.0,
            boundary_f1=0.0,
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    frames: list[str] = []
    for index, offset in enumerate(range(0, 360, 45)):
        view = SourceViewScore(
            source="gameprep",
            best_score=0.0,
            best_azimuth=(anchor_view.best_azimuth + offset) % 360.0,
            best_elevation=anchor_view.best_elevation,
            best_up_axis=anchor_view.best_up_axis,
            silhouette_iou=0.0,
            boundary_f1=0.0,
            projection=anchor_view.projection,
            camera_distance=anchor_view.camera_distance,
        )
        image = render_candidate_rgb_arrays(
            vertices,
            faces,
            colors,
            view,
            uvs=uvs,
            face_texture_ids=face_texture_ids,
            textures=textures,
            size=384,
        )
        frame = out_dir / f"{index:02d}_{offset:03d}.png"
        image.save(frame)
        frames.append(str(frame))
    return frames


def build_gameprep(
    master_glb: Path,
    out_dir: Path,
    *,
    target_faces: int,
    anchor_view: SourceViewScore | None = None,
    material_samples: int = 180_000,
) -> GamePrepResult:
    trimesh = _deps()
    out_dir.mkdir(parents=True, exist_ok=True)

    master_out = out_dir / "master.glb"
    shutil.copy2(master_glb, master_out)

    master_mesh = load_combined_mesh(master_glb)
    source_faces = int(len(master_mesh.faces))
    lod0_target = min(source_faces, max(4, int(target_faces)))
    ratios = [1.0, 0.55, 0.28, 0.12]

    # One source color cloud is shared across all simplified LODs.
    color_points, color_values = build_source_color_cloud(
        master_glb,
        total_samples=material_samples,
    )

    lods: list[LODArtifact] = []
    for index, ratio in enumerate(ratios):
        name = f"LOD{index}"
        target = max(4, min(source_faces, int(round(lod0_target * ratio))))
        final_path = out_dir / f"{name}.glb"

        if index == 0 and source_faces <= lod0_target:
            shutil.copy2(master_glb, final_path)
            actual = source_faces
            material_policy = "original master materials preserved"
        else:
            simplified = simplify_to_faces(master_mesh, target)
            raw_path = out_dir / "_raw" / f"{name}_geometry.glb"
            export_glb(simplified, raw_path)
            transfer_base_color_from_cloud(
                master_glb,
                color_points,
                color_values,
                raw_path,
                final_path,
            )
            reloaded = load_combined_mesh(final_path)
            actual = int(len(reloaded.faces))
            material_policy = "Material Bridge v1 base-color vertex projection"

        lods.append(
            LODArtifact(
                name=name,
                path=str(final_path),
                target_faces=target,
                actual_faces=actual,
                material_policy=material_policy,
            )
        )

    collision_path = None
    try:
        hull = master_mesh.convex_hull
        collision_file = out_dir / "collision_convex.glb"
        export_glb(hull, collision_file)
        collision_path = str(collision_file)
    except Exception:
        collision_path = None

    turntable_frames = build_turntable(
        master_glb,
        out_dir / "turntable",
        anchor_view=anchor_view,
    )

    manifest_path = out_dir / "gameprep_manifest.json"
    result = GamePrepResult(
        master=str(master_out),
        lods=lods,
        collision=collision_path,
        turntable_frames=turntable_frames,
        manifest=str(manifest_path),
        source_faces=source_faces,
        target_lod0_faces=lod0_target,
    )
    manifest_path.write_text(
        json.dumps(asdict(result), indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="HAYUYA GamePrep v1.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target-faces", type=int, required=True)
    args = parser.parse_args()

    result = build_gameprep(
        args.input,
        args.output,
        target_faces=args.target_faces,
    )
    print(json.dumps(asdict(result), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
