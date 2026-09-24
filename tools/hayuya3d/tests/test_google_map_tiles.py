#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
HAYUYA3D = HERE.parent
sys.path.insert(0, str(HAYUYA3D))

from google_map_tiles import GoogleMapTilesClient


class GoogleMapTilesClientTests(unittest.TestCase):
    def setUp(self):
        self.client = GoogleMapTilesClient("TEST_KEY")

    def test_2d_tile_url_uses_official_endpoint_shape(self):
        url = self.client.tile_2d_url(
            session="SESSION",
            zoom=10,
            x=192,
            y=401,
        )
        self.assertIn("/v1/2dtiles/10/192/401?", url)
        self.assertIn("session=SESSION", url)
        self.assertIn("key=TEST_KEY", url)

    def test_streetview_tile_zoom_is_bounded_by_google_contract(self):
        url = self.client.streetview_tile_url(
            session="SESSION",
            pano_id="PANO",
            zoom=5,
            x=1,
            y=2,
        )
        self.assertIn("/v1/streetview/tiles/5/1/2?", url)
        with self.assertRaises(ValueError):
            self.client.streetview_tile_url(
                session="SESSION",
                pano_id="PANO",
                zoom=6,
                x=1,
                y=2,
            )

    def test_photorealistic_root_is_official_3d_tiles_endpoint(self):
        url = self.client.photorealistic_3d_root_url()
        self.assertIn("/v1/3dtiles/root.json?", url)
        self.assertIn("key=TEST_KEY", url)

    def test_terrain_session_auto_requires_roadmap_layer(self):
        captured = {}

        def fake_request(path, *, method="GET", body=None, **query):
            captured["path"] = path
            captured["method"] = method
            captured["body"] = body
            return {
                "session": "SESSION",
                "expiry": "123",
                "tileWidth": 256,
                "tileHeight": 256,
                "imageFormat": "png",
            }

        self.client._json_request = fake_request
        session = self.client.create_session(
            map_type="terrain",
            language="en-US",
            region="US",
        )
        self.assertEqual(session.session, "SESSION")
        self.assertIn("layerRoadmap", captured["body"]["layerTypes"])

    def test_streetview_pano_ids_caps_locations_at_100(self):
        with self.assertRaises(ValueError):
            self.client.streetview_pano_ids(
                session="SESSION",
                locations=[(0.0, 0.0)] * 101,
            )

    def test_attribution_is_preserved_from_metadata(self):
        out = self.client.attribution_from_streetview_metadata(
            {
                "copyright": "Example copyright",
                "reportProblemLink": "https://example.invalid/report",
            }
        )
        self.assertEqual(out["copyright"], "Example copyright")
        self.assertIn("report", out["report_problem_link"])


if __name__ == "__main__":
    unittest.main()
