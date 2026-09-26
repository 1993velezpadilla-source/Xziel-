#!/usr/bin/env python3
"""Self-test the XZIEL folder/ZIP zero-omission inventory builder."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools/maps/build_xziel_map_package.py"

spec = importlib.util.spec_from_file_location("xziel_map_builder", MODULE)
if spec is None or spec.loader is None:
    raise SystemExit("unable to load map package builder")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

with tempfile.TemporaryDirectory(prefix="xziel-package-test-") as td:
    root = Path(td) / "fixture"
    root.mkdir()
    (root / "models").mkdir()
    (root / "textures").mkdir()
    (root / "sound").mkdir()

    (root / "models/test.mdl").write_bytes(b"model")
    (root / "textures/test.png").write_bytes(b"texture")
    (root / "sound/test.wav").write_bytes(b"audio")
    (root / "map.gsc").write_text(
        'model "models/test.mdl"\n'
        'texture "textures/test.png"\n'
        'sound "sound/test.wav"\n',
        encoding="utf-8",
    )

    good = mod.build_manifest(root, "folder", "fixture")
    assert good["summary"]["fileCount"] == 4
    assert good["summary"]["referenceCount"] == 3
    assert good["summary"]["blockerCount"] == 0
    assert good["summary"]["strictReady"] is True

    # Same basename in separate directories is diagnostic-only when references
    # are explicit and therefore deterministic.
    (root / "textures2").mkdir()
    (root / "textures2/test.png").write_bytes(b"other")
    duplicate = mod.build_manifest(root, "folder", "fixture")
    assert duplicate["summary"]["strictReady"] is True
    assert duplicate["diagnostics"]["duplicateBasenames"]

    # Wrong-case reference must fail on Android-style case-sensitive mounts.
    (root / "map.gsc").write_text(
        'model "Models/test.mdl"\n'
        'texture "textures/test.png"\n'
        'sound "sound/test.wav"\n',
        encoding="utf-8",
    )
    wrong_case = mod.build_manifest(root, "folder", "fixture")
    assert wrong_case["summary"]["strictReady"] is False
    assert len(wrong_case["blockers"]["unresolvedAssetReferences"]) == 1

    # Missing dependency must block strict readiness.
    (root / "map.gsc").write_text(
        'model "models/missing.mdl"\n',
        encoding="utf-8",
    )
    missing = mod.build_manifest(root, "folder", "fixture")
    assert missing["summary"]["strictReady"] is False
    assert len(missing["blockers"]["unresolvedAssetReferences"]) == 1

    # ZIP and folder inventory must agree on the same payload.
    (root / "map.gsc").write_text(
        'model "models/test.mdl"\n'
        'texture "textures/test.png"\n'
        'sound "sound/test.wav"\n',
        encoding="utf-8",
    )
    zpath = Path(td) / "fixture.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        for p in sorted(root.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(root).as_posix())

    extract = Path(td) / "unzipped"
    extract.mkdir()
    mod.safe_extract_zip(zpath, extract)
    zipped = mod.build_manifest(extract, "zip", "fixture.zip")

    folder_paths = {r["path"]: r["sha256"] for r in mod.build_manifest(root, "folder", "fixture")["files"]}
    zip_paths = {r["path"]: r["sha256"] for r in zipped["files"]}
    assert folder_paths == zip_paths

print("XZIEL_MAP_PACKAGE_BUILDER_OK")
