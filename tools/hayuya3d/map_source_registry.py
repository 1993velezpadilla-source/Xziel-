#!/usr/bin/env python3
from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Iterable


@dataclass(frozen=True)
class MapSourceProvider:
    provider_id: str
    label: str
    capabilities: tuple[str, ...]
    credential_env: tuple[str, ...] = ()
    official_api: bool = True
    persistent_derivatives: str = "review_provider_terms"
    notes: str = ""

    def readiness(self, env: dict[str, str] | None = None) -> dict:
        current = os.environ if env is None else env
        missing = [name for name in self.credential_env if not current.get(name)]
        return {
            **asdict(self),
            "ready": not missing,
            "missing_credentials": missing,
        }


def default_providers() -> dict[str, MapSourceProvider]:
    providers = [
        MapSourceProvider(
            provider_id="google_maps_platform",
            label="Google Maps Platform",
            capabilities=(
                "roadmap_tiles",
                "satellite_tiles",
                "terrain_tiles",
                "street_view_tiles",
                "photorealistic_3d_tiles",
                "places_context",
            ),
            credential_env=("GOOGLE_MAPS_API_KEY",),
            persistent_derivatives="restricted_by_google_maps_platform_terms",
            notes=(
                "Official API only. Preserve required attribution and respect current "
                "display, caching, storage, mixing, and derivative-use terms."
            ),
        ),
        MapSourceProvider(
            provider_id="google_custom_search_legacy",
            label="Google Custom Search JSON API (legacy optional)",
            capabilities=("web_image_search",),
            credential_env=("GOOGLE_CUSTOM_SEARCH_API_KEY", "GOOGLE_CUSTOM_SEARCH_CX"),
            persistent_derivatives="source_rights_must_be_resolved_per_result",
            notes=(
                "Optional compatibility adapter only. Google documents the Custom Search "
                "JSON API as closed to new customers and existing customers must transition "
                "by 2027-01-01. Never scrape Google Images HTML as a replacement."
            ),
        ),
        MapSourceProvider(
            provider_id="overture_maps",
            label="Overture Maps",
            capabilities=(
                "buildings",
                "places",
                "transportation",
                "addresses",
                "base",
                "divisions",
                "infrastructure",
            ),
            official_api=False,
            persistent_derivatives="follow_overture_dataset_and_source_attribution_terms",
            notes="Open geospatial dataset family; use release/version provenance.",
        ),
        MapSourceProvider(
            provider_id="openstreetmap_overpass",
            label="OpenStreetMap / Overpass",
            capabilities=("vector_features", "roads", "buildings", "poi", "relations"),
            official_api=True,
            persistent_derivatives="follow_odbl_and_attribution_requirements",
            notes="Queryable OSM data; cache responsibly and retain attribution/provenance.",
        ),
        MapSourceProvider(
            provider_id="mapbox",
            label="Mapbox",
            capabilities=(
                "map_tiles",
                "satellite",
                "terrain",
                "3d_buildings",
                "model_layers",
            ),
            credential_env=("MAPBOX_ACCESS_TOKEN",),
            persistent_derivatives="review_mapbox_terms",
        ),
        MapSourceProvider(
            provider_id="cesium_ion",
            label="Cesium ion",
            capabilities=("3d_tiles", "terrain", "imagery", "geospatial_streaming"),
            credential_env=("CESIUM_ION_TOKEN",),
            persistent_derivatives="review_content_provider_and_cesium_terms",
        ),
        MapSourceProvider(
            provider_id="esri_arcgis",
            label="Esri ArcGIS / Reality",
            capabilities=(
                "imagery",
                "terrain",
                "reality_mesh",
                "point_cloud",
                "gaussian_splats",
                "photogrammetry",
            ),
            credential_env=("ARCGIS_TOKEN",),
            persistent_derivatives="review_esri_and_source_dataset_terms",
        ),
        MapSourceProvider(
            provider_id="user_capture",
            label="User-owned capture/reference",
            capabilities=(
                "photos",
                "video",
                "depth",
                "lidar",
                "point_cloud",
                "mesh",
                "annotations",
            ),
            official_api=False,
            persistent_derivatives="depends_on_user_rights",
            notes="Highest-value editable source when the user has rights to transform it.",
        ),
        MapSourceProvider(
            provider_id="openverse",
            label="Openverse",
            capabilities=("open_licensed_image_search", "open_licensed_audio_search", "reference_discovery"),
            official_api=True,
            persistent_derivatives="verify_each_work_license_and_attribution_before_use",
            notes=(
                "Search engine for openly licensed/public-domain media. License metadata is evidence, "
                "not a guarantee; verify the selected work before redistribution or derivation."
            ),
        ),
        MapSourceProvider(
            provider_id="wikimedia",
            label="Wikimedia / Commons APIs",
            capabilities=("reference_discovery", "encyclopedic_context", "commons_media_search"),
            official_api=True,
            persistent_derivatives="follow_each_file_license_and_required_attribution",
            notes="Public MediaWiki/Wikimedia APIs; retain source page/file metadata and attribution.",
        ),
        MapSourceProvider(
            provider_id="pexels",
            label="Pexels API",
            capabilities=("photo_search", "video_search", "reference_discovery"),
            credential_env=("PEXELS_API_KEY",),
            official_api=True,
            persistent_derivatives="follow_pexels_api_and_content_license_terms",
            notes="Official REST API. Preserve required Pexels/photographer credit and current API terms.",
        ),
        MapSourceProvider(
            provider_id="unsplash",
            label="Unsplash API",
            capabilities=("photo_search", "reference_discovery"),
            credential_env=("UNSPLASH_ACCESS_KEY",),
            official_api=True,
            persistent_derivatives="reference_or_authorized_use_under_unsplash_api_terms",
            notes=(
                "Official API only. Hotlink returned image URLs, trigger the required download endpoint "
                "for download-like actions, provide attribution, and do not use as an AI training/data-mining source."
            ),
        ),
        MapSourceProvider(
            provider_id="generic_web_images",
            label="Provider-pluggable web image research",
            capabilities=("web_image_search", "reference_discovery"),
            official_api=True,
            persistent_derivatives="source_rights_must_be_resolved_per_result",
            notes=(
                "Research layer, not a scraping loophole. Adapters must retain result URL, "
                "provider, attribution/license evidence, and allowed-use classification."
            ),
        ),
    ]
    return {provider.provider_id: provider for provider in providers}


def providers_for(capability: str) -> list[MapSourceProvider]:
    return [
        provider
        for provider in default_providers().values()
        if capability in provider.capabilities
    ]


def readiness_report(
    provider_ids: Iterable[str] | None = None,
    *,
    env: dict[str, str] | None = None,
) -> dict:
    registry = default_providers()
    ids = list(provider_ids) if provider_ids is not None else list(registry)
    unknown = [provider_id for provider_id in ids if provider_id not in registry]
    if unknown:
        raise ValueError(f"unknown map source providers: {', '.join(unknown)}")
    return {
        "schema": 1,
        "providers": {
            provider_id: registry[provider_id].readiness(env)
            for provider_id in ids
        },
    }
