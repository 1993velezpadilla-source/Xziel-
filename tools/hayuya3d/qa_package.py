#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from gltf_audit import audit_glb
from mesh_doctor import audit_mesh as audit_mesh_structure
from qa import inspect_mesh
from reference_pool import infer_detail_region_hint


@dataclass
class QAPackageResult:
    report: str
    contact_sheet: str | None
    turntable_report: str | None
    turntable_contact_sheet: str | None
    part_map: str | None
    geometry_ready: bool
    material_ready: bool
    material_rebake_ready: bool
    material_rebaked_channels: list[str]
    material_rebake_pending_channels: list[str]
    rig_ready: bool
    animation_ready: bool
    turntable_ready: bool
    turntable_score: float | None
    face_evidence_ready: bool
    face_evidence_score: float | None
    head_density_score: float | None
    head_texel_density_score: float | None
    production_ready: bool
    warnings: list[str]


def _champion_dict(champion: Any) -> dict:
    if isinstance(champion, dict):
        return dict(champion)
    try:
        return asdict(champion)
    except Exception:
        return {}


def unresolved_material_rebakes(gameprep_data: dict | None) -> list[dict]:
    unresolved: list[dict] = []
    for lod in (gameprep_data or {}).get("lods", []) or []:
        channels = sorted({str(x) for x in (lod.get("rebake_required") or []) if x})
        if channels:
            unresolved.append({
                "lod": str(lod.get("name") or lod.get("path") or "unknown"),
                "channels": channels,
            })
    return unresolved


def material_rebake_channel_summary(gameprep_data: dict | None) -> tuple[list[str], list[str]]:
    resolved:set[str]=set()
    pending:set[str]=set()
    for lod in (gameprep_data or {}).get("lods", []) or []:
        resolved.update(str(x) for x in (lod.get("rebaked_channels") or []) if x)
        pending.update(str(x) for x in (lod.get("rebake_required") or []) if x)
    # A channel still pending on any runtime LOD is not globally complete.
    return sorted(resolved-pending),sorted(pending)


def _thumbnail(path: Path, size: tuple[int, int]):
    from PIL import Image, ImageOps

    image = Image.open(path).convert("RGB")
    return ImageOps.fit(image, size, method=Image.Resampling.LANCZOS)


def build_contact_sheet(
    *,
    source_images: list[Path],
    turntable_frames: list[Path],
    output: Path,
) -> Path | None:
    from PIL import Image, ImageDraw

    sources = [p for p in source_images if p.is_file()][:8]
    turns = [p for p in turntable_frames if p.is_file()][:8]
    if not sources and not turns:
        return None

    cell = (240, 240)
    columns = 4
    items: list[tuple[str, Path]] = [
        *[(f"SOURCE {i + 1}", p) for i, p in enumerate(sources)],
        *[(f"TURN {i * 45:03d}", p) for i, p in enumerate(turns)],
    ]
    rows = (len(items) + columns - 1) // columns
    header = 30
    sheet = Image.new("RGB", (columns * cell[0], rows * (cell[1] + header)), (24, 24, 24))
    draw = ImageDraw.Draw(sheet)

    for index, (label, path) in enumerate(items):
        col = index % columns
        row = index // columns
        x = col * cell[0]
        y = row * (cell[1] + header)
        thumb = _thumbnail(path, cell)
        sheet.paste(thumb, (x, y + header))
        draw.text((x + 8, y + 7), label, fill=(235, 235, 235))

    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, format="PNG")
    return output


def build_qa_package(
    final_glb: Path,
    out_dir: Path,
    *,
    champion: Any,
    mode: str,
    profile: str,
    source_images: list[Path],
    detail_images: list[Path],
    gameprep: Any = None,
    target_faces: int,
    target_texture_size: int | None = None,
) -> QAPackageResult:
    out_dir.mkdir(parents=True, exist_ok=True)
    champion_data = _champion_dict(champion)
    mesh = inspect_mesh(
        final_glb,
        backend=str(champion_data.get("backend", "final")),
        mode=mode,
        target_faces=target_faces,
        target_texture_size=target_texture_size,
    )
    rig = audit_glb(final_glb)
    structure = audit_mesh_structure(final_glb)

    gameprep_data = asdict(gameprep) if gameprep is not None else None

    part_map_result = None
    part_map_path = None
    try:
        from part_map import build_part_map, write_part_map

        visual_views_for_axis = champion_data.get("visual_views") or []
        recovered_up_axis = (
            visual_views_for_axis[0].get("best_up_axis", "y")
            if visual_views_for_axis
            else "y"
        )
        part_map_result = build_part_map(
            final_glb,
            mode=mode,
            up_axis=recovered_up_axis,
        )
        part_map_path = write_part_map(
            part_map_result,
            out_dir / "part_map.json",
        )
    except Exception:
        part_map_result = None
        part_map_path = None

    lods = (gameprep_data or {}).get("lods", [])
    turntable = [Path(p) for p in (gameprep_data or {}).get("turntable_frames", [])]
    collision = (gameprep_data or {}).get("collision")

    warnings: list[str] = []
    warnings.extend(mesh.notes or [])
    warnings.extend(rig.warnings)
    warnings.extend(rig.errors)
    if part_map_result is not None and part_map_result.accessory_component_ids:
        warnings.append(
            "Part Map identified preserved accessory-candidate components: "
            + ",".join(str(x) for x in part_map_result.accessory_component_ids)
        )

    unresolved_structural_defects = bool(
        not structure.valid
        or not structure.finite_vertices
        or structure.duplicate_faces > 0
        or structure.degenerate_faces > 0
        or structure.nonmanifold_edges > 0
        or not structure.winding_consistent
    )

    geometry_ready = bool(
        mesh.valid
        and mesh.faces >= 50
        and mesh.degenerate_ratio <= 0.02
        and mesh.bbox
        and all(x > 1e-9 for x in mesh.bbox)
        and not unresolved_structural_defects
    )

    if unresolved_structural_defects:
        warnings.append(
            "Mesh Doctor reports unresolved structural defects; production-ready geometry is false"
        )
    if structure.boundary_edges > 0 and not structure.watertight:
        warnings.append(
            f"open boundary edges remain: {structure.boundary_edges} "
            "(warning only; may be intentional open geometry)"
        )
    if structure.tiny_components > 0:
        warnings.append(
            f"tiny disconnected components retained intentionally: {structure.tiny_components}"
        )

    base_material_ready = bool(
        mesh.material_score >= 55.0
        or ("baseColor" in set(mesh.pbr_channels or []) and mesh.has_uv)
    )
    texture_resolution_ready = (
        True
        if target_texture_size is None
        else bool(
            mesh.base_color_min_edge
            and mesh.base_color_min_edge >= int(target_texture_size)
        )
    )
    material_ready = bool(base_material_ready and texture_resolution_ready)
    if base_material_ready and not texture_resolution_ready:
        warnings.append(
            f"weakest visible baseColor resolution {mesh.base_color_min_edge}px "
            f"(strongest {mesh.base_color_max_edge}px) is below profile target "
            f"{int(target_texture_size)}px; asset remains inspectable but is not production-ready"
        )

    rig_required = mode == "character"
    rig_ready = bool(rig.rig_ready)
    animation_ready = bool(rig.animation_ready)

    if rig_required and not rig_ready:
        warnings.append(
            "character asset is geometrically usable but unrigged; animation/gameplay-ready status is false"
        )
    if rig_ready and not animation_ready:
        warnings.append(
            "rig is valid but no glTF animation clips are embedded; character production-ready status is false"
        )
    if mode != "character" and not rig_ready:
        pass

    expected_sources = len(source_images)
    judged_views = champion_data.get("visual_views") or []
    source_coverage = len(judged_views)

    if expected_sources and source_coverage < expected_sources:
        warnings.append(
            f"Judge source coverage {source_coverage}/{expected_sources}; not every geometry reference has a recorded visual view"
        )

    face_detail_refs=[
        p for p in detail_images
        if infer_detail_region_hint(p)=="head"
    ]
    face_evidence_required=bool(face_detail_refs)
    face_evidence_score=champion_data.get("appearance_face_detail_score")
    face_evidence_ready=bool(
        not face_evidence_required
        or face_evidence_score is not None
    )
    if face_evidence_required and not face_evidence_ready:
        warnings.append(
            "face references were supplied but no face-detail identity Judge score "
            "was recorded; asset remains inspectable but is not production-ready"
        )

    turntable_qa = None
    turntable_report_path = None
    turntable_contact_path = None
    turntable_ready = expected_sources == 0
    turntable_score = None
    if expected_sources:
        if turntable and source_coverage >= expected_sources:
            try:
                from turntable_qa import (
                    build_turntable_comparison_sheet,
                    score_source_to_turntable,
                    write_turntable_report,
                )

                turntable_qa = score_source_to_turntable(
                    source_images,
                    judged_views[:expected_sources],
                    turntable,
                )
                turntable_ready = bool(turntable_qa.ready)
                turntable_score = float(turntable_qa.score)
                turntable_report_path = write_turntable_report(
                    turntable_qa,
                    out_dir / "source_vs_turntable.json",
                )
                turntable_contact_path = build_turntable_comparison_sheet(
                    turntable_qa,
                    out_dir / "source_vs_turntable.png",
                )
                if not turntable_ready:
                    warnings.append(
                        f"source-vs-turntable QA failed: score={turntable_qa.score:.3f}, "
                        f"catastrophic_mismatches={turntable_qa.catastrophic_mismatches}"
                    )
            except Exception as exc:
                turntable_ready = False
                warnings.append(
                    f"source-vs-turntable QA unavailable: {type(exc).__name__}: {exc}"
                )
        else:
            turntable_ready = False
            warnings.append(
                "source-vs-turntable QA unavailable: turntable or complete Judge orientation evidence missing"
            )

    gameprep_ready = bool(gameprep_data and lods)
    if not gameprep_ready:
        warnings.append("GamePrep package missing")
    if gameprep_data and not collision:
        warnings.append("convex collision proxy unavailable")

    unresolved_rebakes = unresolved_material_rebakes(gameprep_data)
    material_rebaked_channels,material_rebake_pending_channels = (
        material_rebake_channel_summary(gameprep_data)
    )
    material_rebake_ready = not unresolved_rebakes
    if unresolved_rebakes:
        summary = "; ".join(
            f"{item['lod']}:{','.join(item['channels'])}"
            for item in unresolved_rebakes
        )
        warnings.append(
            "runtime LOD material rebake is incomplete: "
            + summary
            + "; asset remains inspectable but is not production-ready"
        )

    production_ready = bool(
        geometry_ready
        and material_ready
        and material_rebake_ready
        and source_coverage >= expected_sources
        and gameprep_ready
        and turntable_ready
        and face_evidence_ready
        and (rig_ready if rig_required else True)
        and (animation_ready if rig_required else True)
    )

    contact_path = build_contact_sheet(
        source_images=source_images,
        turntable_frames=turntable,
        output=out_dir / "qa_contact_sheet.png",
    )

    report = {
        "engine": "HAYUYA QA Package v1",
        "final_glb": str(final_glb),
        "mode": mode,
        "profile": profile,
        "champion": champion_data,
        "geometry": {
            "ready": geometry_ready,
            "vertices": mesh.vertices,
            "faces": mesh.faces,
            "components": mesh.components,
            "watertight": mesh.watertight,
            "degenerate_ratio": mesh.degenerate_ratio,
            "bbox": mesh.bbox,
            "production_score": mesh.production_score,
            "head_region_faces": mesh.head_region_faces,
            "head_region_vertices": mesh.head_region_vertices,
            "head_region_face_fraction": mesh.head_region_face_fraction,
            "global_median_edge_normalized": mesh.global_median_edge_normalized,
            "head_region_median_edge_normalized": mesh.head_region_median_edge_normalized,
            "head_region_density_ratio": mesh.head_region_density_ratio,
            "head_density_score": mesh.head_density_score,
            "head_texel_density_ratio": mesh.head_texel_density_ratio,
            "head_texel_density_score": mesh.head_texel_density_score,
        },
        "structure": asdict(structure),
        "material": {
            "ready": material_ready,
            "base_material_ready": base_material_ready,
            "texture_resolution_ready": texture_resolution_ready,
            "material_score": mesh.material_score,
            "has_uv": mesh.has_uv,
            "textured": mesh.textured,
            "channels": mesh.pbr_channels,
            "texture_max_edge": mesh.texture_max_edge,
            "base_color_max_edge": mesh.base_color_max_edge,
            "base_color_min_edge": mesh.base_color_min_edge,
            "texture_resolution_score": mesh.texture_resolution_score,
            "target_texture_size": target_texture_size,
            "rebake_ready": material_rebake_ready,
            "rebaked_channels": material_rebaked_channels,
            "rebake_pending_channels": material_rebake_pending_channels,
            "unresolved_rebakes": unresolved_rebakes,
        },
        "rig": asdict(rig),
        "part_map": asdict(part_map_result) if part_map_result is not None else None,
        "judge": {
            "score": champion_data.get("score"),
            "visual_score": champion_data.get("visual_score"),
            "visual_views": judged_views,
            "appearance_score": champion_data.get("appearance_score"),
            "appearance_detail_score": champion_data.get("appearance_detail_score"),
            "appearance_face_detail_score": champion_data.get("appearance_face_detail_score"),
            "appearance_details": champion_data.get("appearance_details"),
            "normal_support_score": champion_data.get("normal_support_score"),
        },
        "gameprep": gameprep_data,
        "source_coverage": {
            "expected": expected_sources,
            "judged": source_coverage,
        },
        "face_evidence": {
            "required": face_evidence_required,
            "references": [str(p) for p in face_detail_refs],
            "score": face_evidence_score,
            "ready": face_evidence_ready,
        },
        "turntable_qa": asdict(turntable_qa) if turntable_qa is not None else None,
        "production_ready": production_ready,
        "warnings": warnings,
    }
    report_path = out_dir / "qa_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    return QAPackageResult(
        report=str(report_path),
        contact_sheet=str(contact_path) if contact_path else None,
        turntable_report=str(turntable_report_path) if turntable_report_path else None,
        turntable_contact_sheet=str(turntable_contact_path) if turntable_contact_path else None,
        part_map=str(part_map_path) if part_map_path else None,
        geometry_ready=geometry_ready,
        material_ready=material_ready,
        material_rebake_ready=material_rebake_ready,
        material_rebaked_channels=material_rebaked_channels,
        material_rebake_pending_channels=material_rebake_pending_channels,
        rig_ready=rig_ready,
        animation_ready=animation_ready,
        turntable_ready=turntable_ready,
        turntable_score=turntable_score,
        face_evidence_ready=face_evidence_ready,
        face_evidence_score=(
            float(face_evidence_score)
            if face_evidence_score is not None else None
        ),
        head_density_score=(
            float(mesh.head_density_score)
            if mesh.head_density_score is not None else None
        ),
        head_texel_density_score=(
            float(mesh.head_texel_density_score)
            if mesh.head_texel_density_score is not None else None
        ),
        production_ready=production_ready,
        warnings=warnings,
    )
