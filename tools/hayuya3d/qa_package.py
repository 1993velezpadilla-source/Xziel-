#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from gltf_audit import audit_glb
from mesh_doctor import audit_mesh as audit_mesh_structure
from qa import inspect_mesh


@dataclass
class QAPackageResult:
    report: str
    contact_sheet: str | None
    turntable_report: str | None
    turntable_contact_sheet: str | None
    part_map: str | None
    geometry_ready: bool
    material_ready: bool
    rig_ready: bool
    animation_ready: bool
    turntable_ready: bool
    turntable_score: float | None
    production_ready: bool
    warnings: list[str]


def _champion_dict(champion: Any) -> dict:
    if isinstance(champion, dict):
        return dict(champion)
    try:
        return asdict(champion)
    except Exception:
        return {}


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
) -> QAPackageResult:
    out_dir.mkdir(parents=True, exist_ok=True)
    champion_data = _champion_dict(champion)
    mesh = inspect_mesh(
        final_glb,
        backend=str(champion_data.get("backend", "final")),
        mode=mode,
        target_faces=target_faces,
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
    except Exception as exc:
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

    material_ready = bool(
        mesh.material_score >= 55.0
        or ("baseColor" in set(mesh.pbr_channels or []) and mesh.has_uv)
    )

    rig_required = mode == "character"
    rig_ready = bool(rig.rig_ready)
    animation_ready = bool(rig.animation_ready)

    if rig_required and not rig_ready:
        warnings.append(
            "character asset is geometrically usable but unrigged; animation/gameplay-ready status is false"
        )
    if rig_ready and not animation_ready:
        warnings.append("rig is valid but no glTF animation clips are embedded")
    if mode != "character" and not rig_ready:
        # Unrigged props/architecture are normal; do not treat this as a readiness failure.
        pass

    expected_sources = len(source_images)
    judged_views = champion_data.get("visual_views") or []
    source_coverage = len(judged_views)

    if expected_sources and source_coverage < expected_sources:
        warnings.append(
            f"Judge source coverage {source_coverage}/{expected_sources}; not every geometry reference has a recorded visual view"
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

    production_ready = bool(
        geometry_ready
        and material_ready
        and source_coverage >= expected_sources
        and gameprep_ready
        and turntable_ready
        and (rig_ready if rig_required else True)
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
            "mesh_doctor": asdict(structure),
            "unresolved_structural_defects": unresolved_structural_defects,
        },
        "materials": {
            "ready": material_ready,
            "has_uv": mesh.has_uv,
            "textured": mesh.textured,
            "pbr_channels": mesh.pbr_channels or [],
            "material_score": mesh.material_score,
        },
        "references": {
            "geometry_source_count": expected_sources,
            "detail_source_count": len(detail_images),
            "judge_visual_view_count": source_coverage,
            "all_geometry_sources_judged": source_coverage >= expected_sources,
        },
        "source_vs_turntable": (
            asdict(turntable_qa)
            if turntable_qa is not None
            else {
                "ready": turntable_ready,
                "score": turntable_score,
                "report": str(turntable_report_path) if turntable_report_path else None,
                "contact_sheet": str(turntable_contact_path) if turntable_contact_path else None,
            }
        ),
        "part_map": (
            {
                **asdict(part_map_result),
                "report": str(part_map_path) if part_map_path else None,
            }
            if part_map_result is not None
            else None
        ),
        "rig": asdict(rig),
        "gameprep": gameprep_data,
        "readiness": {
            "geometry_ready": geometry_ready,
            "material_ready": material_ready,
            "rig_required": rig_required,
            "rig_ready": rig_ready,
            "animation_ready": animation_ready,
            "gameprep_ready": gameprep_ready,
            "turntable_ready": turntable_ready,
            "turntable_score": turntable_score,
            "production_ready": production_ready,
        },
        "warnings": list(dict.fromkeys(warnings)),
        "contact_sheet": str(contact_path) if contact_path else None,
        "source_vs_turntable_sheet": str(turntable_contact_path) if turntable_contact_path else None,
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
        rig_ready=rig_ready,
        animation_ready=animation_ready,
        turntable_ready=turntable_ready,
        turntable_score=turntable_score,
        production_ready=production_ready,
        warnings=report["warnings"],
    )


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Build a HAYUYA final asset QA package.")
    parser.add_argument("glb", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=["prop", "character", "architecture"], default="prop")
    parser.add_argument("--profile", default="game")
    parser.add_argument("--target-faces", type=int, default=100000)
    parser.add_argument("--source", type=Path, action="append", default=[])
    args = parser.parse_args()

    result = build_qa_package(
        args.glb,
        args.output,
        champion={},
        mode=args.mode,
        profile=args.profile,
        source_images=args.source,
        detail_images=[],
        target_faces=args.target_faces,
    )
    print(json.dumps(asdict(result), indent=2))
    return 0 if result.geometry_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
