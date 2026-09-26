#!/usr/bin/env python3
"""Verify XZIEL .xzp package structure, hashes, and runtime-promotion proof."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import zipfile

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_VALIDATOR = ROOT / "tools/maps/xziel_runtime_manifest.py"

spec = importlib.util.spec_from_file_location(
    "xziel_runtime_manifest",
    RUNTIME_VALIDATOR,
)
if spec is None or spec.loader is None:
    raise SystemExit("unable to load XZIEL runtime manifest validator")
runtime_validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime_validator)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fail(msg: str) -> None:
    raise SystemExit(f"XZIEL_XZP_VERIFY_FAIL: {msg}")


def verify(path) -> dict:
    with zipfile.ZipFile(path, "r") as zf:
        names = zf.namelist()
        if names.count("xziel.package.json") != 1:
            fail("package must contain exactly one xziel.package.json")

        try:
            manifest = json.loads(zf.read("xziel.package.json"))
        except Exception as exc:
            fail(f"invalid xziel.package.json: {exc}")

        package = manifest.get("package", {})
        if package.get("format") != "xziel_xzp_v1":
            fail("package format drift")
        if package.get("payloadRoot") != "payload/":
            fail("payload root drift")
        if package.get("sourceBytesPreserved") is not True:
            fail("sourceBytesPreserved must remain true")
        if package.get("runtimePromotionRequired") is not True:
            fail("runtimePromotionRequired must remain true")
        if manifest.get("summary", {}).get("strictReady") is not True:
            fail("embedded inventory is not strictReady")

        map_meta = manifest.get("map", {})
        map_id = map_meta.get("mapId")
        entry_world = map_meta.get("entryWorld")
        if not isinstance(map_id, str) or not map_id:
            fail("mapId missing")
        if map_meta.get("contentContract") != "xziel_map_content_contract_v1":
            fail("map content contract drift")
        if map_meta.get("gameMode") != "round_based_zombies":
            fail("unsupported map gameMode")
        if map_meta.get("serverAuthoritative") is not True:
            fail("map must remain server authoritative")
        if (
            not isinstance(map_meta.get("maxPlayers"), int)
            or isinstance(map_meta.get("maxPlayers"), bool)
            or not (1 <= map_meta["maxPlayers"] <= 4)
        ):
            fail("map maxPlayers out of range")
        if (
            not isinstance(entry_world, str)
            or not entry_world.startswith("maps/")
            or not entry_world.endswith(".bsp")
        ):
            fail("entryWorld invalid")
        if entry_world != f"maps/{map_id}.bsp":
            fail("entryWorld must equal maps/<mapId>.bsp")

        expected = {}
        for row in manifest.get("files", []):
            rel = row.get("path")
            if not isinstance(rel, str) or not rel:
                fail("manifest file path invalid")
            pp = PurePosixPath(rel)
            if pp.is_absolute() or ".." in pp.parts:
                fail(f"unsafe manifest path: {rel}")
            arc = "payload/" + rel
            if arc in expected:
                fail(f"duplicate payload path in manifest: {rel}")
            expected[arc] = row

        if "payload/" + entry_world not in expected:
            fail("entryWorld missing from embedded inventory")
        runtime_arc = "payload/" + runtime_validator.RUNTIME_FILE
        if runtime_arc not in expected:
            fail("runtime manifest missing from embedded inventory")

        actual = [
            n for n in names
            if n.startswith("payload/") and not n.endswith("/")
        ]
        if sorted(actual) != sorted(expected):
            missing = sorted(set(expected) - set(actual))
            extra = sorted(set(actual) - set(expected))
            fail(f"payload membership mismatch missing={missing} extra={extra}")

        total = 0
        payload_bytes = {}
        for arc, row in expected.items():
            data = zf.read(arc)
            payload_bytes[arc] = data
            total += len(data)
            if len(data) != row.get("bytes"):
                fail(f"size mismatch: {arc}")
            if digest(data) != row.get("sha256"):
                fail(f"sha256 mismatch: {arc}")

        if total != manifest["summary"]["totalBytes"]:
            fail("total payload byte count mismatch")

        try:
            runtime = json.loads(payload_bytes[runtime_arc])
        except Exception as exc:
            fail(f"invalid payload/{runtime_validator.RUNTIME_FILE}: {exc}")

        runtime_row = expected[runtime_arc]
        try:
            runtime_summary = runtime_validator.validate_runtime_manifest(
                runtime,
                map_meta,
                {row["path"] for row in manifest.get("files", [])},
                inventory_strict_ready=True,
                manifest_sha256=runtime_row.get("sha256", ""),
            )
        except SystemExit as exc:
            fail(str(exc))

        if manifest.get("runtime") != runtime_summary:
            fail("embedded runtime promotion summary drift")

        return manifest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("package")
    args = ap.parse_args()
    manifest = verify(args.package)
    print(
        "XZIEL_XZP_VERIFY_OK",
        {
            "files": manifest["summary"]["fileCount"],
            "bytes": manifest["summary"]["totalBytes"],
            "runtimeReady": manifest["runtime"]["runtimeReady"],
            "readyFamilies": manifest["runtime"]["readyFamilyCount"],
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
