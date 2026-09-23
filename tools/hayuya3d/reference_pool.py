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
\nVIEW_RULES = [\n    (("front_45_right", "front45right", "front_right_45"), 45.0),\n    (("back_45_right", "back45right", "back_right_45"), 135.0),\n    (("back_45_left", "back45left", "back_left_45"), 225.0),\n    (("front_45_left", "front45left", "front_left_45"), 315.0),\n    (("right_side", "_right", "right_"), 90.0),\n    (("left_side", "_left", "left_"), 270.0),\n    (("back", "rear"), 180.0),\n    (("front",), 0.0),\n]\n\nCOVERAGE_PRIORITY = [90.0, 180.0, 270.0, 45.0, 135.0, 225.0, 315.0, 0.0]\n\n\ndef infer_view_hint(path: Path) -> float | None:\n    name = path.stem.lower().replace("-", "_").replace(" ", "_")\n    for needles, angle in VIEW_RULES:\n        if any(n in name for n in needles):\n            return angle\n    return None\n\n\ndef order_for_multiview_coverage(paths: list[Path]) -> list[Path]:\n    """Prefer broad canonical-angle coverage before redundant same-angle references."""\n    indexed = list(enumerate(paths))\n    priority = {angle: i for i, angle in enumerate(COVERAGE_PRIORITY)}\n\n    def key(item):\n        original_index, path = item\n        hint = infer_view_hint(path)\n        if hint is None:\n            return (1, original_index, original_index)\n        return (0, priority.get(hint, len(priority)), original_index)\n\n    return [path for _, path in sorted(indexed, key=key)]\n

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
