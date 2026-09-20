#!/usr/bin/env python3
import json
import sys
from pathlib import Path

ALLOWED_LICENSES = {
    "CC0-1.0",
    "CC-BY-4.0",
    "CC-BY-SA-4.0",
    "OWNED",
}

BLOCKED_STATUS_WORDS = {
    "ripped",
    "extracted",
    "editorial",
    "non-commercial",
    "personal-use",
    "unknown",
}

def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)

def main() -> None:
    manifest_path = Path(sys.argv[1] if len(sys.argv) > 1 else "content/enhanced/asset_manifest.json")
    if not manifest_path.is_file():
        fail(f"manifest not found: {manifest_path}")

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assets = data.get("assets")
    if not isinstance(assets, list) or not assets:
        fail("manifest must contain a non-empty assets list")

    seen = set()
    for index, asset in enumerate(assets):
        asset_id = asset.get("id")
        if not asset_id:
            fail(f"asset #{index} has no id")
        if asset_id in seen:
            fail(f"duplicate asset id: {asset_id}")
        seen.add(asset_id)

        license_id = asset.get("license")
        if license_id not in ALLOWED_LICENSES:
            fail(f"{asset_id}: license '{license_id}' is not approved for the enhanced pipeline")

        source_url = asset.get("source_url")
        if not isinstance(source_url, str) or not source_url.startswith(("https://", "http://")):
            fail(f"{asset_id}: source_url must be an http(s) URL")

        status = str(asset.get("status", "")).lower()
        notes = str(asset.get("notes", "")).lower()
        combined = f"{status} {notes}"
        for word in BLOCKED_STATUS_WORDS:
            if word in combined:
                fail(f"{asset_id}: blocked provenance marker found: {word}")

        if asset.get("requires_attribution") and not asset.get("author"):
            fail(f"{asset_id}: attribution is required but author is missing")

    print(f"OK: {len(assets)} enhanced asset records validated")

if __name__ == "__main__":
    main()
