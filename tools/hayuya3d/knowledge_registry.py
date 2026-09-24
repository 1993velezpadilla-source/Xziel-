#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DEFAULT_KNOWLEDGE_DIRS = (
    ROOT / "hayuya" / "knowledge",
    ROOT / "hayuya" / "standards",
)


@dataclass(frozen=True)
class KnowledgePack:
    pack_id: str
    path: str
    schema: Any
    top_level_keys: tuple[str, ...]
    kind: str


def _classify(path: Path) -> str:
    if "standards" in path.parts:
        return "standard"
    if "knowledge" in path.parts:
        return "knowledge"
    return "external"


def discover_knowledge_packs(
    extra_dirs: Iterable[Path] = (),
    *,
    strict: bool = True,
) -> dict[str, Any]:
    roots = [*DEFAULT_KNOWLEDGE_DIRS, *(Path(p) for p in extra_dirs)]
    packs: dict[str, KnowledgePack] = {}
    errors: list[dict[str, str]] = []

    for root in roots:
        if not root.exists():
            if strict:
                raise FileNotFoundError(root)
            errors.append({"path": str(root), "error": "directory_missing"})
            continue

        for path in sorted(root.rglob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("knowledge pack root must be a JSON object")
                pack_id = str(
                    data.get("id")
                    or data.get("profile")
                    or path.stem
                ).strip()
                if not pack_id:
                    raise ValueError("knowledge pack id is empty")
                if pack_id in packs:
                    raise ValueError(
                        f"duplicate knowledge pack id {pack_id!r}: "
                        f"{packs[pack_id].path} vs {path}"
                    )
                try:
                    relative = str(path.resolve().relative_to(ROOT.resolve()))
                except ValueError:
                    relative = str(path.resolve())

                packs[pack_id] = KnowledgePack(
                    pack_id=pack_id,
                    path=relative,
                    schema=data.get("schema", data.get("schemaVersion")),
                    top_level_keys=tuple(sorted(str(k) for k in data)),
                    kind=_classify(path),
                )
            except Exception as exc:
                if strict:
                    raise
                errors.append(
                    {
                        "path": str(path),
                        "error": f"{type(exc).__name__}:{exc}",
                    }
                )

    return {
        "schema": 1,
        "pack_count": len(packs),
        "packs": {
            pack_id: {
                "id": pack.pack_id,
                "path": pack.path,
                "schema": pack.schema,
                "top_level_keys": list(pack.top_level_keys),
                "kind": pack.kind,
            }
            for pack_id, pack in sorted(packs.items())
        },
        "errors": errors,
        "contract": {
            "new_pack_requires_core_code_change": False,
            "arbitrary_json_schema_allowed": True,
            "stable_pack_id_required": True,
            "duplicate_pack_ids_rejected": True,
            "external_directories_supported": True,
        },
    }
