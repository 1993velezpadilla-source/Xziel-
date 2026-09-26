#!/usr/bin/env python3
"""Build a deterministic XZIEL map-package inventory from a folder or ZIP.

This is the first layer of the drag/drop map ingestion path. It never guesses
missing content and it never rewrites source assets. It inventories everything,
hashes payloads, classifies common game-asset types, extracts conservative text
references, and records blockers that must be zero before a package can be
promoted to strict/runtime-ready.

Designed for user-owned/licensed source payloads. The manifest contains metadata
and hashes; it does not embed third-party asset bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
import zipfile

TEXT_EXTS = {
    ".cfg", ".csv", ".ent", ".gsc", ".h", ".ini", ".json", ".map", ".material",
    ".qc", ".qcc", ".shader", ".txt", ".xml", ".yaml", ".yml",
}
TYPE_BY_EXT = {
    ".bsp": "world_geometry",
    ".map": "world_source",
    ".obj": "mesh",
    ".fbx": "mesh",
    ".gltf": "mesh",
    ".glb": "mesh",
    ".mdl": "model",
    ".md3": "model",
    ".iqm": "model",
    ".xmodel_bin": "model",
    ".png": "texture",
    ".jpg": "texture",
    ".jpeg": "texture",
    ".tga": "texture",
    ".dds": "texture",
    ".ktx": "texture",
    ".ktx2": "texture",
    ".wav": "audio",
    ".ogg": "audio",
    ".mp3": "audio",
    ".flac": "audio",
    ".xanim_bin": "animation",
    ".anim": "animation",
    ".nav": "navigation",
    ".aas": "navigation",
    ".lit": "lighting",
    ".lux": "lighting",
    ".shader": "material_script",
    ".material": "material_script",
    ".gsc": "gameplay_script",
    ".qc": "gameplay_script",
    ".cfg": "config",
    ".json": "metadata",
    ".csv": "metadata",
}

# Conservative path-like references only. Bare identifiers are intentionally not
# treated as assets because that creates false missing dependencies.
REF_RE = re.compile(
    r"""(?ix)
    (?:
        ["'(=:\s]
    )
    (
        (?:[a-z0-9_.-]+/)*
        [a-z0-9_.@+-]+
        \.
        (?:bsp|map|obj|fbx|gltf|glb|mdl|md3|iqm|xmodel_bin|
           png|jpe?g|tga|dds|ktx2?|wav|ogg|mp3|flac|
           xanim_bin|anim|nav|aas|lit|lux|shader|material|
           gsc|qc|cfg|json|csv)
    )
    """,
)

IGNORE_NAMES = {".ds_store", "thumbs.db"}
IGNORE_DIRS = {".git", "__macosx"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_rel(path: str) -> str:
    s = path.replace("\\", "/").lstrip("./")
    while "//" in s:
        s = s.replace("//", "/")
    return str(PurePosixPath(s))


def classify(rel: str) -> str:
    p = PurePosixPath(rel)
    ext = p.suffix.lower()
    if rel.lower().endswith(".xmodel_bin"):
        ext = ".xmodel_bin"
    elif rel.lower().endswith(".xanim_bin"):
        ext = ".xanim_bin"
    return TYPE_BY_EXT.get(ext, "other")


def collect_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel_parts = p.relative_to(root).parts
        if any(part.lower() in IGNORE_DIRS for part in rel_parts):
            continue
        if p.name.lower() in IGNORE_NAMES:
            continue
        out.append(p)
    return sorted(out, key=lambda p: normalize_rel(str(p.relative_to(root))).lower())


def safe_extract_zip(src: Path, dst: Path) -> None:
    with zipfile.ZipFile(src, "r") as zf:
        for member in zf.infolist():
            name = normalize_rel(member.filename)
            if not name or member.is_dir():
                continue
            if name.startswith("../") or "/../" in f"/{name}" or PurePosixPath(name).is_absolute():
                raise SystemExit(f"unsafe ZIP member path: {member.filename}")
            target = dst / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member, "r") as rf, target.open("wb") as wf:
                shutil.copyfileobj(rf, wf)


def maybe_text(path: Path) -> str | None:
    ext = path.suffix.lower()
    if path.name.lower().endswith((".xmodel_bin", ".xanim_bin")):
        return None
    if ext not in TEXT_EXTS:
        return None
    try:
        raw = path.read_bytes()
        if b"\x00" in raw[:4096]:
            return None
        return raw.decode("utf-8", errors="strict")
    except (UnicodeDecodeError, OSError):
        return None


def resolve_reference(source_rel: str, ref: str, all_paths: set[str]) -> tuple[str | None, list[str]]:
    ref = normalize_rel(ref)
    source_dir = str(PurePosixPath(source_rel).parent)
    candidates: list[str] = []

    direct = normalize_rel(ref)
    relative = normalize_rel(str(PurePosixPath(source_dir) / ref)) if source_dir != "." else direct
    for candidate in (direct, relative):
        if candidate in all_paths and candidate not in candidates:
            candidates.append(candidate)

    if not candidates:
        # Last-resort suffix lookup supports scripts that omit a package root
        # such as "sound/foo.wav" while the extracted package has "raw/sound/foo.wav".
        suffix = "/" + direct
        suffix_matches = sorted(
            p for p in all_paths
            if p == direct or p.endswith(suffix)
        )
        candidates.extend(suffix_matches)

    if len(candidates) == 1:
        return candidates[0], candidates
    return None, candidates


def build_manifest(root: Path, source_kind: str, source_name: str) -> dict:
    files = collect_files(root)
    rels = [normalize_rel(str(p.relative_to(root))) for p in files]
    path_set = set(rels)

    case_groups: dict[str, list[str]] = {}
    base_groups: dict[str, list[str]] = {}
    for rel in rels:
        case_groups.setdefault(rel.lower(), []).append(rel)
        base_groups.setdefault(PurePosixPath(rel).name.lower(), []).append(rel)

    case_collisions = [
        sorted(v) for v in case_groups.values() if len(v) > 1
    ]
    duplicate_basenames = [
        sorted(v) for v in base_groups.values() if len(v) > 1
    ]

    records = []
    zero_byte = []
    refs = []
    unresolved = []
    ambiguous = []
    category_counts: dict[str, int] = {}

    for p, rel in zip(files, rels):
        size = p.stat().st_size
        kind = classify(rel)
        category_counts[kind] = category_counts.get(kind, 0) + 1
        if size == 0:
            zero_byte.append(rel)

        record = {
            "path": rel,
            "bytes": size,
            "sha256": sha256(p),
            "kind": kind,
        }
        records.append(record)

        text = maybe_text(p)
        if text is None:
            continue

        seen = set()
        for m in REF_RE.finditer(text):
            requested = normalize_rel(m.group(1))
            key = requested.lower()
            if key in seen:
                continue
            seen.add(key)
            resolved, candidates = resolve_reference(rel, requested, path_set)
            edge = {
                "from": rel,
                "requested": requested,
                "resolved": resolved,
            }
            if resolved is None and len(candidates) > 1:
                edge["candidates"] = candidates
                ambiguous.append(edge)
            elif resolved is None:
                unresolved.append(edge)
            refs.append(edge)

    blockers = {
        "zeroByteFiles": zero_byte,
        "casePathCollisions": case_collisions,
        "unresolvedAssetReferences": unresolved,
        "ambiguousAssetReferences": ambiguous,
    }
    blocker_count = sum(len(v) for v in blockers.values())

    return {
        "schemaVersion": 1,
        "format": "xziel_map_package_inventory_v1",
        "source": {
            "kind": source_kind,
            "name": source_name,
        },
        "policy": {
            "zeroOmission": True,
            "strictReadyRequiresZeroBlockers": True,
            "hashAlgorithm": "sha256",
            "caseSensitiveCanonicalPaths": True,
        },
        "summary": {
            "fileCount": len(records),
            "totalBytes": sum(r["bytes"] for r in records),
            "categoryCounts": dict(sorted(category_counts.items())),
            "referenceCount": len(refs),
            "blockerCount": blocker_count,
            "strictReady": blocker_count == 0 and len(records) > 0,
        },
        "files": records,
        "references": refs,
        "blockers": blockers,
        "diagnostics": {
            "duplicateBasenames": duplicate_basenames,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path, help="map folder or .zip")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--strict", action="store_true", help="exit nonzero on any blocker")
    args = ap.parse_args()

    src = args.input.resolve()
    if not src.exists():
        raise SystemExit(f"input does not exist: {src}")

    temp: tempfile.TemporaryDirectory[str] | None = None
    if src.is_dir():
        root = src
        source_kind = "folder"
    elif src.is_file() and src.suffix.lower() == ".zip":
        temp = tempfile.TemporaryDirectory(prefix="xziel-map-")
        root = Path(temp.name)
        safe_extract_zip(src, root)
        source_kind = "zip"
    else:
        raise SystemExit("input must be a directory or ZIP")

    try:
        manifest = build_manifest(root, source_kind, src.name)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(manifest["summary"], sort_keys=True))
        if args.strict and not manifest["summary"]["strictReady"]:
            return 2
        return 0
    finally:
        if temp is not None:
            temp.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
