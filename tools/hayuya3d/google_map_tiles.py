#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Iterable


GOOGLE_TILE_BASE = "https://tile.googleapis.com/v1"


@dataclass(frozen=True)
class MapTilesSession:
    session: str
    expiry: str
    tile_width: int
    tile_height: int
    image_format: str

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "MapTilesSession":
        return cls(
            session=str(payload["session"]),
            expiry=str(payload["expiry"]),
            tile_width=int(payload["tileWidth"]),
            tile_height=int(payload["tileHeight"]),
            image_format=str(payload["imageFormat"]),
        )


class GoogleMapTilesClient:
    """
    Minimal official Google Map Tiles API client.

    The caller owns credential storage, billing/quota decisions, attribution UI,
    caching policy, and current Google Maps Platform terms compliance.
    """

    def __init__(self, api_key: str, *, timeout_seconds: float = 20.0):
        api_key = api_key.strip()
        if not api_key:
            raise ValueError("Google Maps API key is required")
        self._api_key = api_key
        self.timeout_seconds = float(timeout_seconds)

    def _url(self, path: str, **query: Any) -> str:
        params = {key: value for key, value in query.items() if value is not None}
        params["key"] = self._api_key
        return f"{GOOGLE_TILE_BASE}/{path.lstrip('/')}?{urllib.parse.urlencode(params)}"

    def _json_request(
        self,
        path: str,
        *,
        method: str = "GET",
        body: dict[str, Any] | None = None,
        **query: Any,
    ) -> dict[str, Any]:
        data = None
        headers = {}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self._url(path, **query),
            data=data,
            headers=headers,
            method=method,
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def create_session(
        self,
        *,
        map_type: str,
        language: str,
        region: str,
        image_format: str | None = None,
        scale: str | None = None,
        high_dpi: bool | None = None,
        layer_types: Iterable[str] | None = None,
        overlay: bool | None = None,
    ) -> MapTilesSession:
        allowed = {"roadmap", "satellite", "terrain", "streetview"}
        if map_type not in allowed:
            raise ValueError(f"unsupported Google Map Tiles mapType: {map_type}")
        if not language.strip() or not region.strip():
            raise ValueError("language and region are required by createSession")

        layers = list(layer_types or ())
        if map_type == "terrain" and "layerRoadmap" not in layers:
            layers.append("layerRoadmap")

        body: dict[str, Any] = {
            "mapType": map_type,
            "language": language,
            "region": region.upper(),
        }
        if image_format is not None:
            body["imageFormat"] = image_format
        if scale is not None:
            body["scale"] = scale
        if high_dpi is not None:
            body["highDpi"] = bool(high_dpi)
        if layers:
            body["layerTypes"] = layers
        if overlay is not None:
            body["overlay"] = bool(overlay)

        payload = self._json_request("createSession", method="POST", body=body)
        return MapTilesSession.from_payload(payload)

    def tile_2d_url(
        self,
        *,
        session: str,
        zoom: int,
        x: int,
        y: int,
        orientation: int | None = None,
    ) -> str:
        if not 0 <= zoom <= 22:
            raise ValueError("2D tile zoom must be within [0, 22]")
        if orientation not in {None, 0, 90, 180, 270}:
            raise ValueError("orientation must be one of 0, 90, 180, 270")
        return self._url(
            f"2dtiles/{zoom}/{x}/{y}",
            session=session,
            orientation=orientation,
        )

    def streetview_pano_ids(
        self,
        *,
        session: str,
        locations: Iterable[tuple[float, float]],
        radius_m: float = 50.0,
    ) -> list[str]:
        rows = [{"lat": float(lat), "lng": float(lng)} for lat, lng in locations]
        if not 1 <= len(rows) <= 100:
            raise ValueError("Street View panoId request needs 1..100 locations")
        if radius_m <= 0:
            raise ValueError("Street View radius must be > 0")
        payload = self._json_request(
            "streetview/panoIds",
            method="POST",
            body={"locations": rows, "radius": float(radius_m)},
            session=session,
        )
        return [str(item) for item in payload.get("panoIds", [])]

    def streetview_metadata(self, *, session: str, pano_id: str) -> dict[str, Any]:
        return self._json_request(
            "streetview/metadata",
            session=session,
            panoId=pano_id,
        )

    def streetview_tile_url(
        self,
        *,
        session: str,
        pano_id: str,
        zoom: int,
        x: int,
        y: int,
    ) -> str:
        if not 0 <= zoom <= 5:
            raise ValueError("Street View tile zoom must be within [0, 5]")
        return self._url(
            f"streetview/tiles/{zoom}/{x}/{y}",
            session=session,
            panoId=pano_id,
        )

    def photorealistic_3d_root_url(self) -> str:
        # 3D Tiles do not use createSession. Child URIs returned by Google contain
        # their generated session parameter; the renderer/client must preserve it
        # and append the API credential while displaying all required attribution.
        return self._url("3dtiles/root.json")

    @staticmethod
    def attribution_from_streetview_metadata(metadata: dict[str, Any]) -> dict[str, str]:
        return {
            "copyright": str(metadata.get("copyright") or ""),
            "report_problem_link": str(metadata.get("reportProblemLink") or ""),
        }
