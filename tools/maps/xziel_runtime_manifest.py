#!/usr/bin/env python3
"""Validate promotion from strict source inventory to runtime-ready XZIEL map.

A source folder/ZIP being internally consistent is necessary but not sufficient
for runtime installation. This module validates xziel.runtime.json against the
universal map-content contract and returns the compact promotion summary that is
embedded into xziel.package.json.

The validator intentionally fails closed:
- every universally required family must be declared exactly once;
- every required family must be in the ready state;
- runtime artifacts must be explicit package-relative files;
- validation evidence must be explicit and non-empty;
- every global runtime gate must be true;
- world_geometry must explicitly bind the descriptor entryWorld.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
CONTENT_CONTRACT_PATH = (
    ROOT / "assets/map_package/xziel_map_content_contract_v1.json"
)
RUNTIME_CONTRACT_PATH = (
    ROOT / "assets/map_package/xziel_runtime_manifest_contract_v1.json"
)

RUNTIME_FILE = "xziel.runtime.json"
RUNTIME_FORMAT = "xziel_runtime_manifest_v1"
CONTENT_CONTRACT_ID = "xziel_map_content_contract_v1"


def fail(message: str) -> None:
    raise SystemExit(f"XZIEL_RUNTIME_MANIFEST_FAIL: {message}")


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"invalid JSON {path}: {exc}")
    if not isinstance(value, dict):
        fail(f"JSON root must be an object: {path}")
    return value


def _normalize_rel(value: str) -> str:
    value = value.replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    while "//" in value:
        value = value.replace("//", "/")
    return str(PurePosixPath(value))


def _safe_rel(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        fail(f"{label} must be a non-empty relative path")
    normalized = _normalize_rel(value)
    pp = PurePosixPath(normalized)
    if (
        pp.is_absolute()
        or ".." in pp.parts
        or normalized.startswith("/")
        or normalized == "."
    ):
        fail(f"{label} is unsafe: {value}")
    return normalized


def contract_definition() -> tuple[list[str], list[str]]:
    content = _read_json(CONTENT_CONTRACT_PATH)
    runtime = _read_json(RUNTIME_CONTRACT_PATH)

    required = [
        row["id"]
        for row in content.get("requiredFamilies", [])
        if row.get("required") is True
    ]
    if len(required) != runtime.get("requiredFamilyCount"):
        fail(
            "contract drift: content required family count does not match "
            "runtime requiredFamilyCount"
        )
    if len(required) != len(set(required)):
        fail("contract drift: duplicate required family IDs")

    global_requirements = runtime.get("globalRequirements")
    if not isinstance(global_requirements, dict) or not global_requirements:
        fail("contract drift: globalRequirements missing")

    global_keys = []
    for key, expected in global_requirements.items():
        if expected is not True:
            fail(f"contract drift: global requirement {key} must be true")
        global_keys.append(key)

    return required, global_keys


def runtime_manifest_digest(runtime_bytes: bytes) -> str:
    return hashlib.sha256(runtime_bytes).hexdigest()


def validate_runtime_manifest(
    runtime: dict,
    map_meta: dict,
    inventory_paths: set[str],
    *,
    inventory_strict_ready: bool,
    manifest_sha256: str,
) -> dict:
    if not isinstance(runtime, dict):
        fail("xziel.runtime.json root must be an object")

    if runtime.get("schemaVersion") != 1:
        fail("schemaVersion must be 1")
    if runtime.get("format") != RUNTIME_FORMAT:
        fail(f"format must be {RUNTIME_FORMAT}")

    map_id = map_meta.get("mapId")
    if runtime.get("mapId") != map_id:
        fail("runtime mapId must match xziel.map.json")
    if runtime.get("contentContract") != CONTENT_CONTRACT_ID:
        fail("runtime contentContract mismatch")

    if inventory_strict_ready is not True:
        fail("source inventory is not strictReady")
    if runtime.get("sourceInventoryStrictReady") is not True:
        fail("runtime manifest does not attest strict source inventory")

    required, global_keys = contract_definition()

    globals_value = runtime.get("globalRequirements")
    if not isinstance(globals_value, dict):
        fail("globalRequirements must be an object")
    for key in global_keys:
        if globals_value.get(key) is not True:
            fail(f"global requirement not ready: {key}")

    families = runtime.get("families")
    if not isinstance(families, list):
        fail("families must be an array")
    if len(families) != len(required):
        fail(
            f"families must contain exactly {len(required)} required entries; "
            f"got {len(families)}"
        )

    seen: set[str] = set()
    world_artifacts: list[str] = []

    for row in families:
        if not isinstance(row, dict):
            fail("each family entry must be an object")

        family_id = row.get("id")
        if not isinstance(family_id, str) or family_id not in required:
            fail(f"unknown required family id: {family_id!r}")
        if family_id in seen:
            fail(f"duplicate required family id: {family_id}")
        seen.add(family_id)

        if row.get("state") != "ready":
            fail(f"required family is not ready: {family_id}")

        artifacts = row.get("runtimeArtifacts")
        if not isinstance(artifacts, list) or not artifacts:
            fail(f"runtimeArtifacts must be non-empty for {family_id}")

        normalized_artifacts: list[str] = []
        artifact_seen: set[str] = set()
        for artifact in artifacts:
            rel = _safe_rel(
                artifact,
                f"runtimeArtifacts[{family_id}]",
            )
            if rel == RUNTIME_FILE:
                fail(
                    f"{family_id} may not use {RUNTIME_FILE} as its own "
                    "runtime artifact"
                )
            if rel not in inventory_paths:
                fail(f"runtime artifact missing from package: {family_id}: {rel}")
            if rel in artifact_seen:
                fail(f"duplicate runtime artifact for {family_id}: {rel}")
            artifact_seen.add(rel)
            normalized_artifacts.append(rel)

        evidence = row.get("validationEvidence")
        if not isinstance(evidence, list) or not evidence:
            fail(f"validationEvidence must be non-empty for {family_id}")
        for item in evidence:
            if not isinstance(item, str) or not item.strip():
                fail(f"invalid validationEvidence for {family_id}")

        if family_id == "world_geometry":
            world_artifacts = normalized_artifacts

    missing = sorted(set(required) - seen)
    extra = sorted(seen - set(required))
    if missing or extra:
        fail(f"family coverage mismatch missing={missing} extra={extra}")

    entry_world = map_meta.get("entryWorld")
    if entry_world not in world_artifacts:
        fail(
            "world_geometry runtimeArtifacts must explicitly include "
            "descriptor entryWorld"
        )

    if not isinstance(manifest_sha256, str) or len(manifest_sha256) != 64:
        fail("runtime manifest SHA-256 metadata missing")

    summary_globals = {key: True for key in global_keys}
    return {
        "format": RUNTIME_FORMAT,
        "manifestPath": RUNTIME_FILE,
        "manifestSha256": manifest_sha256,
        "requiredFamilyCount": len(required),
        "readyFamilyCount": len(required),
        "runtimeReady": True,
        "sourceInventoryStrictReady": True,
        "globalRequirements": summary_globals,
    }


def load_runtime_manifest(root: Path, map_meta: dict, source_manifest: dict) -> dict:
    path = root / RUNTIME_FILE
    if not path.is_file():
        fail(f"missing root {RUNTIME_FILE}")

    inventory = source_manifest.get("files", [])
    file_by_path = {
        row.get("path"): row
        for row in inventory
        if isinstance(row, dict) and isinstance(row.get("path"), str)
    }
    row = file_by_path.get(RUNTIME_FILE)
    if row is None:
        fail(f"{RUNTIME_FILE} is missing from source inventory")

    runtime = _read_json(path)
    return validate_runtime_manifest(
        runtime,
        map_meta,
        set(file_by_path),
        inventory_strict_ready=(
            source_manifest.get("summary", {}).get("strictReady") is True
        ),
        manifest_sha256=row.get("sha256", ""),
    )
