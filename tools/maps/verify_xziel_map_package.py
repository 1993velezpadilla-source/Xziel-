#!/usr/bin/env python3
"""Verify XZIEL .xzp package structure and payload hashes before runtime mount."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import PurePosixPath
import zipfile


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
        if manifest.get("summary", {}).get("strictReady") is not True:
            fail("embedded inventory is not strictReady")

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

        actual = [n for n in names if n.startswith("payload/") and not n.endswith("/")]
        if sorted(actual) != sorted(expected):
            missing = sorted(set(expected) - set(actual))
            extra = sorted(set(actual) - set(expected))
            fail(f"payload membership mismatch missing={missing} extra={extra}")

        total = 0
        for arc, row in expected.items():
            data = zf.read(arc)
            total += len(data)
            if len(data) != row.get("bytes"):
                fail(f"size mismatch: {arc}")
            if digest(data) != row.get("sha256"):
                fail(f"sha256 mismatch: {arc}")

        if total != manifest["summary"]["totalBytes"]:
            fail("total payload byte count mismatch")

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
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
