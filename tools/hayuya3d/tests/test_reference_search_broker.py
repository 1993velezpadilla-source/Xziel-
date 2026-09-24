#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
HAYUYA3D = HERE.parent
sys.path.insert(0, str(HAYUYA3D))

import reference_search_broker as broker


class ReferenceSearchBrokerTests(unittest.TestCase):
    def test_wikimedia_normalizes_license_and_attribution(self):
        payload = {
            "query": {
                "pages": [
                    {
                        "pageid": 42,
                        "title": "File:Old church.jpg",
                        "imageinfo": [
                            {
                                "url": "https://upload.wikimedia.org/example.jpg",
                                "extmetadata": {
                                    "Artist": {"value": "<b>Example Author</b>"},
                                    "LicenseShortName": {"value": "CC BY-SA 4.0"},
                                    "LicenseUrl": {"value": "https://creativecommons.org/licenses/by-sa/4.0/"},
                                    "Credit": {"value": "Example credit"},
                                },
                            }
                        ],
                    }
                ]
            }
        }
        with patch.object(broker, "_json_get", return_value=payload):
            rows = broker.search_wikimedia("old church", limit=5, env={})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].license, "CC BY-SA 4.0")
        self.assertEqual(rows[0].author, "Example Author")
        self.assertIn("commons.wikimedia.org/wiki/", rows[0].source_page_url)

    def test_google_legacy_adapter_is_explicitly_credential_gated(self):
        with self.assertRaises(RuntimeError):
            broker.search_google_custom_legacy("church", limit=3, env={})

    def test_google_legacy_uses_image_search_contract(self):
        captured = {}

        def fake(url, **kwargs):
            captured["url"] = url
            return {"items": []}

        with patch.object(broker, "_json_get", side_effect=fake):
            broker.search_google_custom_legacy(
                "church",
                limit=3,
                env={
                    "GOOGLE_CUSTOM_SEARCH_API_KEY": "KEY",
                    "GOOGLE_CUSTOM_SEARCH_CX": "CX",
                },
            )
        self.assertIn("searchType=image", captured["url"])
        self.assertIn("safe=active", captured["url"])

    def test_unready_paid_provider_does_not_break_broker_in_tolerant_mode(self):
        report = broker.search_references(
            "cathedral",
            providers=["pexels"],
            per_provider=2,
            env={},
            tolerate_unready=True,
        )
        self.assertEqual(report["result_count"], 0)
        self.assertIn("pexels", report["failures"])

    def test_result_policy_never_treats_search_as_asset_permission(self):
        report = broker.search_references(
            "anything",
            providers=[],
            env={},
        )
        self.assertTrue(
            report["policy"]["search_result_is_evidence_not_asset_permission"]
        )
        self.assertTrue(
            report["policy"]["license_must_be_verified_before_derivative_or_redistribution"]
        )


if __name__ == "__main__":
    unittest.main()
