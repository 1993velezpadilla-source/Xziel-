#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
HAYUYA3D = HERE.parent
sys.path.insert(0, str(HAYUYA3D))

from knowledge_registry import discover_knowledge_packs


class KnowledgeRegistryTests(unittest.TestCase):
    def test_builtin_registry_discovers_expanding_knowledge_without_code_enum(self):
        registry = discover_knowledge_packs(strict=False)
        self.assertGreater(registry["pack_count"], 5)
        self.assertTrue(registry["contract"]["new_pack_requires_core_code_change"] is False)
        self.assertTrue(registry["contract"]["arbitrary_json_schema_allowed"])
        paths = [x["path"] for x in registry["packs"].values()]
        self.assertTrue(any("world_generation_ai_atlas_v1.json" in p for p in paths))
        self.assertTrue(any("hayuya_monetization_brain_v1.json" in p for p in paths))
        self.assertTrue(any("hayuya_encounter_director_v1.json" in p for p in paths))
        self.assertTrue(any("church_giant_encounters_v1.json" in p for p in paths))

    def test_external_pack_is_discovered_without_core_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "totally-new-domain.json").write_text(
                json.dumps(
                    {
                        "id": "totally_new_domain_2099",
                        "schema": 77,
                        "whateverFutureKnowledge": {
                            "unknownConcept": ["a", "b", "c"]
                        },
                    }
                ),
                encoding="utf-8",
            )
            registry = discover_knowledge_packs([root], strict=False)
            self.assertIn("totally_new_domain_2099", registry["packs"])
            pack = registry["packs"]["totally_new_domain_2099"]
            self.assertEqual(pack["schema"], 77)
            self.assertIn("whateverFutureKnowledge", pack["top_level_keys"])


if __name__ == "__main__":
    unittest.main()
