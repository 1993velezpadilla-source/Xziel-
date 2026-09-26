#!/usr/bin/env python3
"""Test strict deterministic XZIEL .xzp compilation and runtime promotion."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"unable to load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


compiler = load(
    "xziel_xzp_compiler",
    ROOT / "tools/maps/compile_xziel_map_package.py",
)
verifier = load(
    "xziel_xzp_verifier",
    ROOT / "tools/maps/verify_xziel_map_package.py",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_runtime_manifest(map_id: str) -> dict:
    content_contract = json.loads(
        (
            ROOT
            / "assets/map_package/xziel_map_content_contract_v1.json"
        ).read_text(encoding="utf-8")
    )
    runtime_contract = json.loads(
        (
            ROOT
            / "assets/map_package/xziel_runtime_manifest_contract_v1.json"
        ).read_text(encoding="utf-8")
    )

    families = []
    for family in content_contract["requiredFamilies"]:
        if family.get("required") is not True:
            continue
        family_id = family["id"]
        artifact = (
            f"maps/{map_id}.bsp"
            if family_id == "world_geometry"
            else "runtime/proof.txt"
        )
        families.append(
            {
                "id": family_id,
                "state": "ready",
                "runtimeArtifacts": [artifact],
                "validationEvidence": [f"fixture:{family_id}:pass"],
            }
        )

    return {
        "schemaVersion": 1,
        "format": "xziel_runtime_manifest_v1",
        "mapId": map_id,
        "contentContract": "xziel_map_content_contract_v1",
        "sourceInventoryStrictReady": True,
        "globalRequirements": {
            key: True
            for key in runtime_contract["globalRequirements"]
        },
        "families": families,
    }


with tempfile.TemporaryDirectory(prefix="xziel-xzp-test-") as td:
    td = Path(td)
    src = td / "map"
    (src / "models").mkdir(parents=True)
    (src / "textures").mkdir()
    (src / "sound").mkdir()
    (src / "maps").mkdir()
    (src / "runtime").mkdir()

    (src / "maps/test_map.bsp").write_bytes(b"BSP-V1")
    (src / "models/weapon.mdl").write_bytes(b"MODEL-V1")
    (src / "textures/weapon.png").write_bytes(b"TEXTURE-V1")
    (src / "sound/fire.wav").write_bytes(b"AUDIO-V1")
    (src / "runtime/proof.txt").write_text(
        "XZIEL runtime validation fixture\n",
        encoding="utf-8",
    )
    (src / "logic.gsc").write_text(
        'model "models/weapon.mdl"\n'
        'texture "textures/weapon.png"\n'
        'sound "sound/fire.wav"\n',
        encoding="utf-8",
    )
    (src / "xziel.map.json").write_text(
        """{
  "schemaVersion": 1,
  "format": "xziel_map_descriptor_v1",
  "mapId": "test_map",
  "displayName": "Test Map",
  "entryWorld": "maps/test_map.bsp",
  "gameMode": "round_based_zombies",
  "maxPlayers": 4,
  "contentContract": "xziel_map_content_contract_v1",
  "serverAuthoritative": true
}
""",
        encoding="utf-8",
    )
    (src / "xziel.runtime.json").write_text(
        json.dumps(make_runtime_manifest("test_map"), indent=2) + "\n",
        encoding="utf-8",
    )

    a = td / "a.xzp"
    b = td / "b.xzp"
    ma = compiler.compile_package(src, a)
    mb = compiler.compile_package(src, b)
    assert ma["summary"]["strictReady"] is True
    assert ma["runtime"]["runtimeReady"] is True
    assert ma["runtime"]["requiredFamilyCount"] == 24
    assert ma["runtime"]["readyFamilyCount"] == 24
    assert mb["runtime"] == ma["runtime"]
    assert sha(a) == sha(b), "deterministic package bytes drift"

    va = verifier.verify(a)
    assert va["summary"]["fileCount"] == 8
    assert va["map"]["mapId"] == "test_map"
    assert va["map"]["entryWorld"] == "maps/test_map.bsp"
    assert va["runtime"]["runtimeReady"] is True
    assert va["runtime"]["readyFamilyCount"] == 24
    assert va["summary"]["totalBytes"] == sum(
        p.stat().st_size for p in src.rglob("*") if p.is_file()
    )

    source_zip = td / "source.zip"
    with zipfile.ZipFile(source_zip, "w") as zf:
        for p in sorted(src.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(src).as_posix())
    zpack = td / "source.xzp"
    mz = compiler.compile_package(source_zip, zpack)
    assert {
        row["path"]: row["sha256"] for row in ma["files"]
    } == {
        row["path"]: row["sha256"] for row in mz["files"]
    }

    # A source inventory without runtime promotion proof must not become .xzp.
    no_runtime = td / "no_runtime"
    shutil.copytree(src, no_runtime)
    (no_runtime / "xziel.runtime.json").unlink()
    no_runtime_failed = False
    no_runtime_package = td / "no-runtime.xzp"
    try:
        compiler.compile_package(no_runtime, no_runtime_package)
    except SystemExit as exc:
        no_runtime_failed = "xziel.runtime.json" in str(exc)
    assert no_runtime_failed, "missing runtime manifest unexpectedly promoted"
    assert not no_runtime_package.exists()

    # A single partial universal family must close the promotion gate.
    partial = td / "partial"
    shutil.copytree(src, partial)
    partial_runtime = json.loads(
        (partial / "xziel.runtime.json").read_text(encoding="utf-8")
    )
    partial_runtime["families"][0]["state"] = "partial"
    (partial / "xziel.runtime.json").write_text(
        json.dumps(partial_runtime, indent=2) + "\n",
        encoding="utf-8",
    )
    partial_failed = False
    partial_package = td / "partial.xzp"
    try:
        compiler.compile_package(partial, partial_package)
    except SystemExit as exc:
        partial_failed = "not ready" in str(exc)
    assert partial_failed, "partial runtime family unexpectedly promoted"
    assert not partial_package.exists()

    # Descriptor must not be allowed to point at a missing world.
    bad_descriptor = td / "bad_descriptor"
    shutil.copytree(src, bad_descriptor)
    (bad_descriptor / "xziel.map.json").write_text(
        """{
  "schemaVersion": 1,
  "format": "xziel_map_descriptor_v1",
  "mapId": "broken_map",
  "displayName": "Broken Map",
  "entryWorld": "maps/not_here.bsp",
  "gameMode": "round_based_zombies",
  "maxPlayers": 4,
  "contentContract": "xziel_map_content_contract_v1",
  "serverAuthoritative": true
}
""",
        encoding="utf-8",
    )
    descriptor_failed = False
    bad_package = td / "bad.xzp"
    try:
        compiler.compile_package(bad_descriptor, bad_package)
    except SystemExit:
        descriptor_failed = True
    assert descriptor_failed, "missing entryWorld unexpectedly packaged"
    assert not bad_package.exists(), "rejected descriptor left a package behind"

    # Rebuild a maliciously modified package with the original manifest but one
    # changed payload. Verification must fail on SHA-256 mismatch.
    corrupt = td / "corrupt.xzp"
    with zipfile.ZipFile(a, "r") as srczip, zipfile.ZipFile(corrupt, "w") as dstzip:
        for info in srczip.infolist():
            data = srczip.read(info.filename)
            if info.filename == "payload/models/weapon.mdl":
                data = b"TAMPERED"
            dstzip.writestr(info, data)

    failed = False
    try:
        verifier.verify(corrupt)
    except SystemExit as exc:
        failed = "sha256 mismatch" in str(exc) or "size mismatch" in str(exc)
    assert failed, "tampered payload unexpectedly verified"

    # A forged runtime summary inside xziel.package.json must also fail even if
    # payload bytes themselves are unchanged.
    forged = td / "forged-runtime-summary.xzp"
    with zipfile.ZipFile(a, "r") as srczip, zipfile.ZipFile(forged, "w") as dstzip:
        for info in srczip.infolist():
            data = srczip.read(info.filename)
            if info.filename == "xziel.package.json":
                package = json.loads(data)
                package["runtime"]["readyFamilyCount"] = 23
                data = (json.dumps(package, indent=2) + "\n").encode("utf-8")
            dstzip.writestr(info, data)

    forged_failed = False
    try:
        verifier.verify(forged)
    except SystemExit as exc:
        forged_failed = "runtime promotion summary drift" in str(exc)
    assert forged_failed, "forged runtime summary unexpectedly verified"

print("XZIEL_XZP_PACKAGE_TEST_OK")
