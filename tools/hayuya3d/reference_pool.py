#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DETAIL_DIR_TOKENS = {
    "detail",
    "details",
    "closeup",
    "closeups",
    "macro",
    "texture",
    "textures",
    "material",
    "materials",
    "surface",
    "surfaces",
}

DETAIL_TOKENS = (
    "detail",
    "closeup",
    "close_up",
    "macro",
    "face_close",
    "face_detail",
    "hand_detail",
    "hair_detail",
    "dress_detail",
    "cloth_detail",
    "fabric",
    "texture",
    "material",
    "surface",
    "torso_detail",
    "hem_detail",
    "accessory_detail",
    "logo_detail",
    "inscription_detail",
    "tattoo_detail",
    "wound_detail",
)


@dataclass(frozen=True)
class ReferenceRoles:
    geometry: list[Path]
    detail: list[Path]


def classify_reference(path: Path) -> str:
    """
    Conservative filename-based role inference.

    Unknown references default to geometry because dropping a useful full-object view
    would be worse than keeping it. Explicit Hayuya detail naming is recognized.
    """
    name = path.stem.lower().replace("-", "_").replace(" ", "_")
    parent_parts = {
        part.lower().replace("-", "_").replace(" ", "_")
        for part in path.parts[:-1]
    }
    if parent_parts & DETAIL_DIR_TOKENS:
        return "detail"
    if any(token in name for token in DETAIL_TOKENS):
        return "detail"
    return "geometry"


def split_reference_roles(paths: list[Path]) -> ReferenceRoles:
    geometry: list[Path] = []
    detail: list[Path] = []

    for path in paths:
        if classify_reference(path) == "detail":
            detail.append(path)
        else:
            geometry.append(path)

    # Safety fallback: if every file was named as a detail, do not make the job
    # impossible. Treat the complete pool as geometry and preserve the warning in plan.
    if not geometry and paths:
        geometry = list(paths)
        detail = []

    return ReferenceRoles(geometry=geometry, detail=detail)
