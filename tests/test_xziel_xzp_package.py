#!/usr/bin/env python3
"""Test strict deterministic XZIEL .xzp compilation and verification."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
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

compiler = load("xziel_xzp_compiler", ROOT / "tools/maps/compile_xziel_map_package.py")
verifier = load("xziel_xzp_verifier", ROOT / "tools/maps/verify_xziel_map_package.py")

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

with tempfile.TemporaryDirectory(prefix="xziel-xzp-test-") as td:
    td = Path(td)
    src = td / "map"
    (src / "models").mkdir(parents=True)
    (src / "textures").mkdir()
    (src / "sound").mkdir()

    (src / "models/weapon.mdl").write_bytes(b"MODEL-V1")
    (src / "textures/weapon.png").write_bytes(b"TEXTURE-V1")
    (src / "sound/fire.wav").write_bytes(b"AUDIO-V1")
    (src / "logic.gsc").write_text(
        'model "models/weapon.mdl"\n'
        'texture "textures/weapon.png"\n'
        'sound "sound/fire.wav"\n',
        encoding="utf-8",
    )

    a = td / "a.xzp"
    b = td / "b.xzp"
    ma = compiler.compile_package(src, a)
    mb = compiler.compile_package(src, b)
    assert ma["summary"]["strictReady"] is True
    assert mb["summary"]["strictReady"] is True
    assert sha(a) == sha(b), "deterministic package bytes drift"

    va = verifier.verify(a)
    assert va["summary"]["fileCount"] == 4
    assert va["summary"]["totalBytes"] == sum(p.stat().st_size for p in src.rglob("*") if p.is_file())

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

print("XZIEL_XZP_PACKAGE_TEST_OK")
