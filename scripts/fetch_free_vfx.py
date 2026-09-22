#!/usr/bin/env python3
"""Fetch candidate Xziel VFX assets with provenance and hash locking.

This tool is intentionally NOT run by release builds when a source has no
locked SHA-256. A developer may fetch an unlocked CC0 candidate, inspect it,
then copy the printed SHA-256 into assets/vfx/sources.json. Release automation
can then use --require-locked to reject source drift.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "assets" / "vfx" / "sources.json"
DEFAULT_CACHE = ROOT / "build" / "free-vfx-cache"


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_id")
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--require-locked", action="store_true")
    args = parser.parse_args()

    manifest = load_manifest()
    source = next(
        (item for item in manifest["sources"] if item["id"] == args.source_id),
        None,
    )
    if source is None:
        raise SystemExit(f"Unknown source id: {args.source_id}")

    if source.get("license") != "CC0-1.0":
        raise SystemExit(
            f"Refusing unreviewed license for {args.source_id}: "
            f"{source.get('license')}"
        )

    url = source.get("download_url")
    if not url:
        raise SystemExit(
            f"{args.source_id} is a catalog/API source, not a direct download"
        )

    locked = source.get("locked_sha256")
    if args.require_locked and not locked:
        raise SystemExit(
            f"{args.source_id} is not hash-locked; review and lock it first"
        )

    args.cache.mkdir(parents=True, exist_ok=True)
    suffix = Path(url.split("?", 1)[0]).suffix or ".bin"
    destination = args.cache / f"{args.source_id}{suffix}"

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "XzielEngineAssetAudit/1.0"},
    )
    print(f"Fetching {source['name']} from {source['source_page']}")
    with urllib.request.urlopen(request, timeout=60) as response:
        with destination.open("wb") as output:
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                output.write(block)

    actual = sha256(destination)
    print(f"saved={destination}")
    print(f"sha256={actual}")

    if locked and actual.lower() != locked.lower():
        destination.unlink(missing_ok=True)
        raise SystemExit(
            f"SHA-256 mismatch for {args.source_id}: "
            f"expected {locked}, got {actual}"
        )

    if not locked:
        print(
            "UNLOCKED CANDIDATE: inspect the asset and its license/source page, "
            "then pin this SHA-256 before any release build."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
