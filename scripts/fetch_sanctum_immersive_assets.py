#!/usr/bin/env python3
"""Fetch redistributable CC0 Sanctum immersion assets.

Only manifest entries explicitly marked CC0-1.0 are mirrored. Libraries that
are free to use in a game but prohibit raw redistribution stay outside this
pipeline.
"""

from __future__ import annotations

import argparse
import hashlib
import html.parser
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
AUDIO_MANIFEST = ROOT / "assets/audio/sanctum/sources.json"
MODEL_MANIFEST = ROOT / "assets/models/sanctum_atmosphere/sources.json"
USER_AGENT = (
    "Xziel-Sanctum-Asset-Pipeline/1.0 "
    "(+https://github.com/1993velezpadilla-source/config-old-3)"
)
ALLOWED_DOWNLOAD_HOSTS = {
    "opengameart.org",
    "www.opengameart.org",
    "api.polyhaven.com",
    "dl.polyhaven.org",
    "cdn.polyhaven.com",
}


class LinkCollector(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag.lower() != "a":
            return
        values = dict(attrs)
        self._href = values.get("href")
        self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            self.links.append(
                (self._href, "".join(self._text).strip())
            )
            self._href = None
            self._text = []


def request(url: str) -> bytes:
    parsed = urllib.parse.urlparse(url)
    if parsed.hostname not in ALLOWED_DOWNLOAD_HOSTS:
        raise RuntimeError(
            f"Blocked download host: {parsed.hostname}"
        )

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        return response.read()


def request_text(url: str) -> str:
    return request(url).decode("utf-8", errors="replace")


def safe_name(value: str) -> str:
    value = urllib.parse.unquote(value)
    value = value.replace("\\", "_").replace("/", "_")
    return (
        re.sub(
            r"[^A-Za-z0-9._() \-\[\]]+",
            "_",
            value,
        ).strip()
        or "asset.bin"
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    destination.write_bytes(request(url))


def verify_cc0_page(page: str, source_page: str) -> None:
    normalized = re.sub(r"\s+", " ", page).lower()
    if "cc0" not in normalized:
        raise RuntimeError(
            "License verification failed: "
            f"CC0 marker not found on {source_page}"
        )


def find_oga_file(
    source_page: str,
    file_contains: str,
) -> str:
    page = request_text(source_page)
    verify_cc0_page(page, source_page)

    parser = LinkCollector()
    parser.feed(page)
    needle = file_contains.lower()

    candidates: list[str] = []
    for href, label in parser.links:
        absolute = urllib.parse.urljoin(
            source_page,
            href,
        )
        haystack = (
            label + " " + urllib.parse.unquote(absolute)
        ).lower()
        if needle in haystack:
            candidates.append(absolute)

    if not candidates:
        token = re.sub(r"[^a-z0-9]+", "", needle)
        for href, label in parser.links:
            absolute = urllib.parse.urljoin(
                source_page,
                href,
            )
            haystack = re.sub(
                r"[^a-z0-9]+",
                "",
                (
                    label
                    + urllib.parse.unquote(absolute)
                ).lower(),
            )
            if token and token in haystack:
                candidates.append(absolute)

    if not candidates:
        raise RuntimeError(
            "Could not resolve requested OGA file "
            f"{file_contains!r} from {source_page}"
        )

    return candidates[0]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def tier_allowed(
    entry_tier: str,
    requested: str,
) -> bool:
    if requested == "all":
        return True
    if requested == "extended":
        return entry_tier in {"core", "extended"}
    return entry_tier == "core"


def collect_url_records(node, path=()):
    if isinstance(node, dict):
        if isinstance(node.get("url"), str):
            yield path, node

        for key, value in node.items():
            if key in {"url", "md5", "size"}:
                continue
            yield from collect_url_records(
                value,
                path + (str(key),),
            )
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from collect_url_records(
                value,
                path + (str(index),),
            )


def score_polyhaven_record(
    path_parts: tuple[str, ...],
    record: dict,
) -> tuple:
    path = "/".join(path_parts).lower()
    url = str(record.get("url", "")).lower()

    resolution_score = (
        0
        if "1k" in path or "_1k" in url
        else 1
    )

    format_order = {
        ".gltf": 0,
        ".glb": 1,
        ".zip": 2,
        ".blend": 3,
        ".fbx": 4,
        ".usd": 5,
    }
    format_score = 9

    for suffix, score in format_order.items():
        if (
            urllib.parse.urlparse(url)
            .path.lower()
            .endswith(suffix)
        ):
            format_score = score
            break

    size = int(record.get("size") or (1 << 60))
    return resolution_score, format_score, size


def download_polyhaven_model(
    asset_id: str,
    destination: Path,
) -> list[Path]:
    files_url = (
        "https://api.polyhaven.com/files/"
        + urllib.parse.quote(asset_id)
    )
    tree = json.loads(request_text(files_url))

    records = list(collect_url_records(tree))
    model_records = [
        item
        for item in records
        if any(
            urllib.parse.urlparse(
                str(item[1].get("url", ""))
            ).path.lower().endswith(ext)
            for ext in (
                ".gltf",
                ".glb",
                ".zip",
                ".blend",
                ".fbx",
                ".usd",
            )
        )
    ]

    if not model_records:
        raise RuntimeError(
            "No downloadable model file found "
            f"for Poly Haven {asset_id}"
        )

    path_parts, record = min(
        model_records,
        key=lambda item: score_polyhaven_record(
            item[0],
            item[1],
        ),
    )

    downloaded: list[Path] = []
    primary_url = record["url"]
    primary_name = safe_name(
        Path(
            urllib.parse.urlparse(primary_url).path
        ).name
    )
    primary = destination / primary_name
    download(primary_url, primary)
    downloaded.append(primary)

    include = record.get("include")
    if include:
        for _, dep_record in collect_url_records(include):
            dep_url = dep_record.get("url")
            if not dep_url:
                continue
            dep_name = safe_name(
                Path(
                    urllib.parse.urlparse(dep_url).path
                ).name
            )
            dep_dest = (
                destination
                / "dependencies"
                / dep_name
            )
            download(dep_url, dep_dest)
            downloaded.append(dep_dest)

    metadata = {
        "assetId": asset_id,
        "apiEndpoint": files_url,
        "selectedPath": list(path_parts),
        "selectedUrl": primary_url,
        "downloadedFiles": [
            str(path.relative_to(destination))
            for path in downloaded
        ],
    }
    (
        destination / "polyhaven_selection.json"
    ).write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )

    return downloaded


def extract_zip(
    path: Path,
    destination: Path,
) -> None:
    if path.suffix.lower() != ".zip":
        return

    destination.mkdir(
        parents=True,
        exist_ok=True,
    )
    with zipfile.ZipFile(path) as archive:
        for member in archive.infolist():
            member_path = Path(member.filename)
            if (
                member_path.is_absolute()
                or ".." in member_path.parts
            ):
                raise RuntimeError(
                    "Unsafe ZIP member: "
                    f"{member.filename}"
                )
        archive.extractall(destination)


def fetch_oga_entry(
    entry: dict,
    out_root: Path,
) -> list[Path]:
    source_page = entry["sourcePage"]
    file_contains = entry["fileContains"]
    url = find_oga_file(
        source_page,
        file_contains,
    )

    basename = safe_name(
        Path(
            urllib.parse.urlparse(url).path
        ).name
    )
    destination = (
        out_root / entry["id"] / basename
    )
    download(url, destination)
    extract_zip(
        destination,
        destination.parent / "extracted",
    )
    return [destination]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tier",
        choices=("core", "extended", "all"),
        default="core",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            ROOT
            / "dist"
            / "sanctum-immersive-assets"
        ),
    )
    parser.add_argument(
        "--include-models",
        action="store_true",
    )
    args = parser.parse_args()

    audio = load_json(AUDIO_MANIFEST)
    models = load_json(MODEL_MANIFEST)

    args.output.mkdir(
        parents=True,
        exist_ok=True,
    )

    lock: dict = {
        "schemaVersion": 1,
        "tier": args.tier,
        "files": [],
    }

    for entry in audio["entries"]:
        if not tier_allowed(
            entry.get("tier", "core"),
            args.tier,
        ):
            continue

        if entry.get("license") != "CC0-1.0":
            raise RuntimeError(
                "Auto-fetch refused non-CC0 audio "
                f"entry: {entry['id']}"
            )

        for path in fetch_oga_entry(
            entry,
            args.output / "audio",
        ):
            lock["files"].append(
                {
                    "id": entry["id"],
                    "path": str(
                        path.relative_to(args.output)
                    ),
                    "sha256": sha256_file(path),
                    "license": entry["license"],
                    "sourcePage": entry[
                        "sourcePage"
                    ],
                }
            )

    if args.include_models:
        for entry in models["entries"]:
            if not tier_allowed(
                entry.get("tier", "core"),
                args.tier,
            ):
                continue

            if entry.get("license") != "CC0-1.0":
                raise RuntimeError(
                    "Auto-fetch refused non-CC0 model "
                    f"entry: {entry['id']}"
                )

            provider = entry.get("provider")
            if provider == "OpenGameArt":
                paths = fetch_oga_entry(
                    entry,
                    args.output / "models",
                )
            elif provider == "Poly Haven":
                destination = (
                    args.output
                    / "models"
                    / entry["id"]
                )
                destination.mkdir(
                    parents=True,
                    exist_ok=True,
                )
                paths = download_polyhaven_model(
                    entry["apiAssetId"],
                    destination,
                )
            else:
                raise RuntimeError(
                    "Unsupported model provider: "
                    f"{provider}"
                )

            for path in paths:
                lock["files"].append(
                    {
                        "id": entry["id"],
                        "path": str(
                            path.relative_to(
                                args.output
                            )
                        ),
                        "sha256": sha256_file(
                            path
                        ),
                        "license": entry[
                            "license"
                        ],
                        "sourcePage": entry[
                            "sourcePage"
                        ],
                    }
                )

    lock_path = (
        args.output / "ASSET_LOCK.json"
    )
    lock_path.write_text(
        json.dumps(lock, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        "Fetched "
        f"{len(lock['files'])} "
        "primary CC0 files"
    )
    print(f"Lockfile: {lock_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
