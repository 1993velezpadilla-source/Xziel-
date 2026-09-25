#!/usr/bin/env python3
"""
Audit the migrated Fab source for St Giles Cripplegate without logging in,
purchasing, acquiring, or downloading the asset.

The current Objaverse/Sketchfab-converted GLB carries only a 1024x1024
exterior atlas. Fab exposes the same artfletch model and an original OBJ
format publicly. This probe determines whether the free source listing
contains a higher-fidelity file worth importing before we touch the runtime
texture again.

Fails closed on licensing or upstream contract ambiguity.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import os
import subprocess
import tempfile
import time


LISTING_ID = "36c06a81-a1b8-4ebd-a734-9e2da2d2814e"
ORIGIN = "https://www.fab.com"
OUT = Path("build/st-giles-fab-source-audit.json")
UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.I,
)


def get_json(url: str):
    command = os.environ.get("FAB_CURL_IMPERSONATE", "").strip()
    if not command:
        raise RuntimeError("FAB_CURL_IMPERSONATE is not configured")

    waits = (0, 5, 15)
    with tempfile.TemporaryDirectory(prefix="xziel-fab-") as tmp:
        cookie_jar = Path(tmp) / "cookies.txt"

        for attempt, wait_seconds in enumerate(waits):
            if wait_seconds:
                time.sleep(wait_seconds)

            headers_path = Path(tmp) / f"headers-{attempt}.txt"
            body_path = Path(tmp) / f"body-{attempt}.bin"

            completed = subprocess.run(
                [
                    command,
                    "-sS",
                    "-b", str(cookie_jar),
                    "-c", str(cookie_jar),
                    "-D", str(headers_path),
                    "-o", str(body_path),
                    "--max-time", "30",
                    url,
                ],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            if completed.returncode != 0:
                raise RuntimeError(
                    "curl-impersonate transport failed: "
                    f"exit={completed.returncode}"
                )

            raw_headers = headers_path.read_text(
                encoding="utf-8",
                errors="replace",
            )
            blocks = [
                block.strip()
                for block in raw_headers.replace("\r\n", "\n").split("\n\n")
                if block.strip()
            ]
            final = blocks[-1] if blocks else ""
            header_lines = final.splitlines()
            status = 0
            if header_lines:
                match = re.search(r"\b(\d{3})\b", header_lines[0])
                if match:
                    status = int(match.group(1))

            parsed_headers = {}
            for line in header_lines[1:]:
                if ":" not in line:
                    continue
                name, value = line.split(":", 1)
                parsed_headers[name.strip().lower()] = value.strip()

            content_type = parsed_headers.get("content-type", "")
            challenged = (
                status == 403
                and (
                    parsed_headers.get("cf-mitigated", "").lower()
                    == "challenge"
                    or "text/html" in content_type.lower()
                )
            )
            if challenged and attempt + 1 < len(waits):
                continue

            if status < 200 or status >= 300:
                raise RuntimeError(
                    f"Fab anonymous API returned HTTP {status}"
                )

            if "json" not in content_type.lower():
                raise RuntimeError(
                    f"Fab returned non-JSON content type {content_type!r}"
                )

            return json.loads(
                body_path.read_text(
                    encoding="utf-8",
                    errors="strict",
                )
            )

    raise RuntimeError("Fab anonymous API remained challenged")


def record_license(detail: dict) -> dict:
    licenses = detail.get("licenses") or []
    compact = []
    free_by_tier = False

    for value in licenses:
        if not isinstance(value, dict):
            continue
        tier = value.get("priceTier")
        if not isinstance(tier, dict):
            tier = {}
        price = tier.get("price")
        amount = tier.get("amount")
        if price == 0 or amount == 0:
            free_by_tier = True

        compact.append(
            {
                "slug": value.get("slug")
                or value.get("code")
                or value.get("name"),
                "name": value.get("name")
                or value.get("displayName"),
                "price": price,
                "amount": amount,
            }
        )

    is_free = bool(detail.get("isFree")) or free_by_tier
    return {
        "isFree": is_free,
        "licenses": compact,
    }


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)

    detail = get_json(
        f"{ORIGIN}/i/listings/{LISTING_ID}?currency=USD"
    )

    title = detail.get("title") or detail.get("name")
    if not isinstance(title, str) or "St Giles Cripplegate" not in title:
        raise RuntimeError(
            f"unexpected Fab listing identity: {title!r}"
        )

    license_info = record_license(detail)
    if not license_info["isFree"]:
        raise RuntimeError(
            "Fab St Giles listing is not provably free; refusing source probe"
        )

    formats = []
    for entry in detail.get("assetFormats") or []:
        if not isinstance(entry, dict):
            continue
        kind = entry.get("assetFormatType")
        code = kind.get("code") if isinstance(kind, dict) else None
        if isinstance(code, str):
            formats.append(code.lower())

    if "obj" not in formats:
        raise RuntimeError(
            f"Fab source listing exposes no OBJ format: {formats}"
        )

    format_payload = get_json(
        f"{ORIGIN}/i/listings/{LISTING_ID}/asset-formats/obj"
    )

    files = []
    for value in format_payload.get("files") or []:
        if not isinstance(value, dict):
            continue
        uid = value.get("uid")
        name = value.get("name")
        size = value.get("size")
        status = value.get("status")
        file_type = value.get("fileType")
        if (
            isinstance(uid, str)
            and UUID.match(uid)
            and isinstance(name, str)
            and isinstance(size, (int, float))
        ):
            files.append(
                {
                    "uid": uid,
                    "name": name,
                    "sizeBytes": int(size),
                    "status": status,
                    "fileType": file_type,
                }
            )

    ready = [
        item
        for item in files
        if item["status"] == "ready"
    ]
    if not ready:
        raise RuntimeError(
            "Fab OBJ source format contains no ready files"
        )

    report = {
        "schemaVersion": 1,
        "listingId": LISTING_ID,
        "title": title,
        "seller": (
            detail.get("seller", {}).get("name")
            if isinstance(detail.get("seller"), dict)
            else None
        ),
        **license_info,
        "formats": sorted(set(formats)),
        "objFiles": ready,
        "largestObjFileBytes": max(
            item["sizeBytes"]
            for item in ready
        ),
        "decision": "SOURCE_DOWNLOAD_CANDIDATE",
        "note": (
            "Metadata-only audit. No login, acquisition, purchase, "
            "download-info request, or asset download was performed."
        ),
    }

    OUT.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print(
        "XZIEL_FAB_ST_GILES_SOURCE_CANDIDATE",
        json.dumps(
            {
                "title": title,
                "formats": report["formats"],
                "objFiles": len(ready),
                "largestObjMB": round(
                    report["largestObjFileBytes"] /
                    (1024 * 1024),
                    2,
                ),
                "licenses": report["licenses"],
            },
            separators=(",", ":"),
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
