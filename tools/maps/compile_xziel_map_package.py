#!/usr/bin/env python3
"""Compile a folder or ZIP into a deterministic strict XZIEL .xzp package."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "tools/maps/build_xziel_map_package.py"

spec = importlib.util.spec_from_file_location("xziel_map_builder", BUILDER)
if spec is None or spec.loader is None:
    raise SystemExit("unable to load XZIEL map package builder")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

FIXED_ZIP_DT = (2000, 1, 1, 0, 0, 0)

MAP_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_]{0,62}$")


def load_map_descriptor(root: Path, manifest: dict) -> dict:
    descriptor_path = root / "xziel.map.json"
    if not descriptor_path.is_file():
        raise SystemExit("XZIEL package rejected: missing root xziel.map.json")

    try:
        descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"XZIEL package rejected: invalid xziel.map.json: {exc}")

    if descriptor.get("schemaVersion") != 1:
        raise SystemExit("XZIEL package rejected: descriptor schemaVersion must be 1")
    if descriptor.get("format") != "xziel_map_descriptor_v1":
        raise SystemExit("XZIEL package rejected: descriptor format drift")

    map_id = descriptor.get("mapId")
    if not isinstance(map_id, str) or not MAP_ID_RE.fullmatch(map_id):
        raise SystemExit("XZIEL package rejected: invalid mapId")

    display_name = descriptor.get("displayName")
    if not isinstance(display_name, str) or not (1 <= len(display_name) <= 128):
        raise SystemExit("XZIEL package rejected: invalid displayName")

    entry_world = descriptor.get("entryWorld")
    if not isinstance(entry_world, str):
        raise SystemExit("XZIEL package rejected: entryWorld missing")
    entry_world = builder.normalize_rel(entry_world)
    pp = PurePosixPath(entry_world)
    if (
        pp.is_absolute()
        or ".." in pp.parts
        or not entry_world.startswith("maps/")
        or not entry_world.endswith(".bsp")
    ):
        raise SystemExit("XZIEL package rejected: entryWorld must be maps/*.bsp")

    game_mode = descriptor.get("gameMode")
    if game_mode != "round_based_zombies":
        raise SystemExit("XZIEL package rejected: unsupported gameMode")

    max_players = descriptor.get("maxPlayers")
    if not isinstance(max_players, int) or isinstance(max_players, bool) or not (1 <= max_players <= 4):
        raise SystemExit("XZIEL package rejected: maxPlayers must be integer 1..4")

    if descriptor.get("contentContract") != "xziel_map_content_contract_v1":
        raise SystemExit("XZIEL package rejected: contentContract mismatch")
    if descriptor.get("serverAuthoritative") is not True:
        raise SystemExit("XZIEL package rejected: serverAuthoritative must be true")

    file_by_path = {row["path"]: row for row in manifest["files"]}
    if entry_world not in file_by_path:
        raise SystemExit(
            f"XZIEL package rejected: entryWorld not found with exact case: {entry_world}"
        )
    if file_by_path[entry_world].get("kind") != "world_geometry":
        raise SystemExit("XZIEL package rejected: entryWorld is not world_geometry")

    return {
        "mapId": map_id,
        "displayName": display_name,
        "entryWorld": entry_world,
        "gameMode": game_mode,
        "maxPlayers": max_players,
        "contentContract": descriptor["contentContract"],
        "serverAuthoritative": True,
    }



def add_bytes(zf: zipfile.ZipFile, arcname: str, payload: bytes) -> None:
    info = zipfile.ZipInfo(arcname, FIXED_ZIP_DT)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    zf.writestr(info, payload)


def compile_package(src: Path, out: Path) -> dict:
    src = src.resolve()
    if not src.exists():
        raise SystemExit(f"input does not exist: {src}")

    temp = None
    if src.is_dir():
        root = src
        source_kind = "folder"
    elif src.is_file() and src.suffix.lower() == ".zip":
        temp = tempfile.TemporaryDirectory(prefix="xziel-pack-")
        root = Path(temp.name)
        builder.safe_extract_zip(src, root)
        source_kind = "zip"
    else:
        raise SystemExit("input must be a directory or ZIP")

    try:
        manifest = builder.build_manifest(root, source_kind, src.name)
        if not manifest["summary"]["strictReady"]:
            raise SystemExit(
                "XZIEL package rejected: zero-omission inventory has blockers: "
                + json.dumps(manifest["blockers"], sort_keys=True)
            )

        manifest["map"] = load_map_descriptor(root, manifest)
        manifest["package"] = {
            "format": "xziel_xzp_v1",
            "payloadRoot": "payload/",
            "deterministic": True,
            "sourceBytesPreserved": True,
        }
        manifest_bytes = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")

        out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out, "w") as zf:
            add_bytes(zf, "xziel.package.json", manifest_bytes)
            for row in sorted(manifest["files"], key=lambda r: r["path"]):
                payload = (root / row["path"]).read_bytes()
                add_bytes(zf, "payload/" + row["path"], payload)

        return manifest
    finally:
        if temp is not None:
            temp.cleanup()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    manifest = compile_package(args.input, args.output)
    print(
        "XZIEL_XZP_BUILD_OK",
        json.dumps(
            {
                "output": str(args.output),
                "files": manifest["summary"]["fileCount"],
                "bytes": manifest["summary"]["totalBytes"],
                "mapId": manifest["map"]["mapId"],
                "entryWorld": manifest["map"]["entryWorld"],
            },
            sort_keys=True,
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
