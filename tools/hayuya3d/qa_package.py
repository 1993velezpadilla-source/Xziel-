#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from gltf_audit import audit_glb
from qa import inspect_mesh


@dataclass
class QAPackageResult:
    report: str
    contact_sheet: str | None
    geometry_ready: bool
    material_ready: bool
    rig_ready: bool
    animation_ready: bool
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

    gameprep_data = asdict(gameprep) if gameprep is not None else None
    lods = (gameprep_data or {}).get("lods", [])
    turntable = [Path(p) for p in (gameprep_data or {}).get("turntable_frames", [])]
    collision = (gameprep_data or {}).get("collision")

    warnings: list[str] = []
    warnings.extend(mesh.notes or [])
    warnings.extend(rig.warnings)
    warnings.extend(rig.errors)

    geometry_ready = bool(
        mesh.valid
        and mesh.faces >= 50
        and mesh.degenerate_ratio <= 0.02
        and mesh.bbox
        and all(x > 1e-9 for x in mesh.bbox)
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
        "rig": asdict(rig),
        "gameprep": gameprep_data,
        "readiness": {
            "geometry_ready": geometry_ready,
            "material_ready": material_ready,
            "rig_required": rig_required,
            "rig_ready": rig_ready,
            "animation_ready": animation_ready,
            "gameprep_ready": gameprep_ready,
            "production_ready": production_ready,
        },
        "warnings": list(dict.fromkeys(warnings)),
        "contact_sheet": str(contact_path) if contact_path else None,
    }
    report_path = out_dir / "qa_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    return QAPackageResult(
        report=str(report_path),
        contact_sheet=str(contact_path) if contact_path else None,
        geometry_ready=geometry_ready,
        material_ready=material_ready,
        rig_ready=rig_ready,
        animation_ready=animation_ready,
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
