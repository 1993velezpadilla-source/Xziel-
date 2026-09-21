#!/usr/bin/env python3
"""Validate redistributable asset metadata for Nacht Enhanced."""
import json, sys
from pathlib import Path

if len(sys.argv) != 2:
    raise SystemExit("usage: validate_nacht_assets.py <manifest.json>")
p=Path(sys.argv[1])
data=json.loads(p.read_text())
required={"id","source","author","license","redistributable","commercial_use","role"}
seen=set()
for i,a in enumerate(data.get("assets",[])):
    missing=required-set(a)
    if missing: raise SystemExit(f"asset {i}: missing {sorted(missing)}")
    if a["id"] in seen: raise SystemExit(f"duplicate asset id: {a['id']}")
    seen.add(a["id"])
    if not a["redistributable"]:
        raise SystemExit(f"{a['id']}: cannot enter distributable APK")
    if not a["commercial_use"]:
        raise SystemExit(f"{a['id']}: keep out of commercial-safe Enhanced bundle")
print(f"Nacht asset manifest OK: {len(seen)} distributable assets")
