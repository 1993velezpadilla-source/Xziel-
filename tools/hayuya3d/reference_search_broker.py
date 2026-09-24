#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import os
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any, Callable

UA = "HAYUYA-MAP/1.0 public-reference-research"


@dataclass(frozen=True)
class ReferenceResult:
    provider: str
    result_id: str
    title: str
    media_url: str
    source_page_url: str
    author: str = ""
    license: str = ""
    license_url: str = ""
    attribution: str = ""
    usage_policy: str = "verify_before_use"
    extra: dict[str, Any] | None = None


def _json_get(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 20.0,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": UA, **(headers or {})},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _clean_html(value: str) -> str:
    import re
    value = re.sub(r"<[^>]+>", " ", value or "")
    return " ".join(html.unescape(value).split())


def search_google_custom_legacy(
    query: str,
    *,
    limit: int,
    env: dict[str, str],
) -> list[ReferenceResult]:
    key = env.get("GOOGLE_CUSTOM_SEARCH_API_KEY", "").strip()
    cx = env.get("GOOGLE_CUSTOM_SEARCH_CX", "").strip()
    if not key or not cx:
        raise RuntimeError(
            "Google Custom Search legacy adapter requires "
            "GOOGLE_CUSTOM_SEARCH_API_KEY and GOOGLE_CUSTOM_SEARCH_CX"
        )
    params = urllib.parse.urlencode(
        {
            "key": key,
            "cx": cx,
            "q": query,
            "searchType": "image",
            "num": max(1, min(10, int(limit))),
            "safe": "active",
        }
    )
    data = _json_get("https://www.googleapis.com/customsearch/v1?" + params)
    out: list[ReferenceResult] = []
    for item in data.get("items", []) or []:
        image = item.get("image", {}) or {}
        out.append(
            ReferenceResult(
                provider="google_custom_search_legacy",
                result_id=str(item.get("cacheId") or item.get("link") or ""),
                title=str(item.get("title") or ""),
                media_url=str(item.get("link") or ""),
                source_page_url=str(image.get("contextLink") or ""),
                author=str(item.get("displayLink") or ""),
                license="unknown",
                usage_policy="research_reference_only_until_rights_resolved",
                extra={"mime": item.get("mime"), "fileFormat": item.get("fileFormat")},
            )
        )
    return out


def search_wikimedia(
    query: str,
    *,
    limit: int,
    env: dict[str, str],
) -> list[ReferenceResult]:
    params = urllib.parse.urlencode(
        {
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": "6",
            "gsrlimit": max(1, min(50, int(limit))),
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "format": "json",
            "formatversion": "2",
            "origin": "*",
        }
    )
    data = _json_get("https://commons.wikimedia.org/w/api.php?" + params)
    out: list[ReferenceResult] = []
    for page in (data.get("query", {}) or {}).get("pages", []) or []:
        imageinfo = (page.get("imageinfo") or [{}])[0]
        meta = imageinfo.get("extmetadata", {}) or {}

        def meta_value(key: str) -> str:
            return _clean_html(str((meta.get(key) or {}).get("value") or ""))

        page_title = str(page.get("title") or "")
        source_page = "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(
            page_title.replace(" ", "_")
        )
        out.append(
            ReferenceResult(
                provider="wikimedia",
                result_id=str(page.get("pageid") or page_title),
                title=page_title,
                media_url=str(imageinfo.get("url") or ""),
                source_page_url=source_page,
                author=meta_value("Artist"),
                license=meta_value("LicenseShortName"),
                license_url=str((meta.get("LicenseUrl") or {}).get("value") or ""),
                attribution=meta_value("Credit"),
                usage_policy="follow_file_license_and_attribution",
                extra={"description": meta_value("ImageDescription")},
            )
        )
    return out


def search_pexels(
    query: str,
    *,
    limit: int,
    env: dict[str, str],
) -> list[ReferenceResult]:
    key = env.get("PEXELS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Pexels adapter requires PEXELS_API_KEY")
    params = urllib.parse.urlencode(
        {"query": query, "per_page": max(1, min(80, int(limit)))}
    )
    data = _json_get(
        "https://api.pexels.com/v1/search?" + params,
        headers={"Authorization": key},
    )
    out: list[ReferenceResult] = []
    for photo in data.get("photos", []) or []:
        src = photo.get("src", {}) or {}
        out.append(
            ReferenceResult(
                provider="pexels",
                result_id=str(photo.get("id") or ""),
                title=str(photo.get("alt") or query),
                media_url=str(src.get("large2x") or src.get("large") or src.get("original") or ""),
                source_page_url=str(photo.get("url") or ""),
                author=str(photo.get("photographer") or ""),
                license="Pexels content license",
                attribution=(
                    f"Photo by {photo.get('photographer')} on Pexels"
                    if photo.get("photographer")
                    else "Photos provided by Pexels"
                ),
                usage_policy="follow_current_pexels_api_and_content_license_terms",
            )
        )
    return out


def search_unsplash(
    query: str,
    *,
    limit: int,
    env: dict[str, str],
) -> list[ReferenceResult]:
    key = env.get("UNSPLASH_ACCESS_KEY", "").strip()
    if not key:
        raise RuntimeError("Unsplash adapter requires UNSPLASH_ACCESS_KEY")
    params = urllib.parse.urlencode(
        {
            "query": query,
            "per_page": max(1, min(30, int(limit))),
            "content_filter": "high",
        }
    )
    data = _json_get(
        "https://api.unsplash.com/search/photos?" + params,
        headers={"Authorization": f"Client-ID {key}"},
    )
    out: list[ReferenceResult] = []
    for photo in data.get("results", []) or []:
        urls = photo.get("urls", {}) or {}
        user = photo.get("user", {}) or {}
        links = photo.get("links", {}) or {}
        out.append(
            ReferenceResult(
                provider="unsplash",
                result_id=str(photo.get("id") or ""),
                title=str(photo.get("alt_description") or photo.get("description") or query),
                media_url=str(urls.get("regular") or urls.get("full") or ""),
                source_page_url=str(links.get("html") or ""),
                author=str(user.get("name") or user.get("username") or ""),
                license="Unsplash license/API terms",
                attribution=(
                    f"Photo by {user.get('name')} on Unsplash"
                    if user.get("name")
                    else "Photo via Unsplash"
                ),
                usage_policy=(
                    "hotlink_api_urls_preserve_attribution_trigger_download_endpoint_when_required_"
                    "no_data_mining_or_ai_training"
                ),
                extra={"download_location": links.get("download_location")},
            )
        )
    return out


SEARCHERS: dict[str, Callable[..., list[ReferenceResult]]] = {
    "google_custom_search_legacy": search_google_custom_legacy,
    "wikimedia": search_wikimedia,
    "pexels": search_pexels,
    "unsplash": search_unsplash,
}


def search_references(
    query: str,
    *,
    providers: list[str],
    per_provider: int = 8,
    env: dict[str, str] | None = None,
    tolerate_unready: bool = True,
) -> dict[str, Any]:
    current = dict(os.environ if env is None else env)
    results: list[ReferenceResult] = []
    failures: dict[str, str] = {}
    for provider in providers:
        searcher = SEARCHERS.get(provider)
        if searcher is None:
            failures[provider] = "no_executable_adapter"
            continue
        try:
            results.extend(
                searcher(
                    query,
                    limit=per_provider,
                    env=current,
                )
            )
        except Exception as exc:
            if not tolerate_unready:
                raise
            failures[provider] = f"{type(exc).__name__}:{exc}"

    return {
        "schema": 1,
        "query": query,
        "providers": providers,
        "result_count": len(results),
        "results": [asdict(result) for result in results],
        "failures": failures,
        "policy": {
            "search_result_is_evidence_not_asset_permission": True,
            "license_must_be_verified_before_derivative_or_redistribution": True,
            "preserve_source_page": True,
            "preserve_attribution": True,
            "no_search_provider_used_as_training_dataset_without_explicit_permission": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HAYUYA public-reference search broker using official provider APIs."
    )
    parser.add_argument("--query", required=True)
    parser.add_argument(
        "--provider",
        action="append",
        default=[],
        choices=sorted(SEARCHERS),
    )
    parser.add_argument("--per-provider", type=int, default=8)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    providers = args.provider or ["wikimedia"]
    report = search_references(
        args.query,
        providers=providers,
        per_provider=args.per_provider,
        tolerate_unready=not args.strict,
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
