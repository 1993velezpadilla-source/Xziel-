#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
HAYUYA3D = HERE.parent
sys.path.insert(0, str(HAYUYA3D))

from hayuya_lighting import compile_lighting_intelligence
from hayuya_map import make_plan, parse_bounds
from map_design_brain import compile_design_intelligence
from map_source_registry import default_providers, readiness_report
from world_semantics import Evidence, SourceRecord, WorldEntity, WorldGraph, WorldRelation


class WorldSemanticsTests(unittest.TestCase):
    def test_unseen_labels_and_predicates_need_no_schema_change(self):
        graph = WorldGraph("everything-test")
        graph.add_source(
            SourceRecord(
                source_id="photo-1",
                uri="user://reference.jpg",
                provider="user_capture",
                kind="image",
                usage="user_owned",
            )
        )
        unknown = WorldEntity(
            entity_id="thing-47",
            labels=[
                "unidentified_ritual_mechanical_structure",
                "label_that_never_existed_when_hayuya_was_written",
            ],
            properties={
                "whatever_future_model_discovers": {
                    "nested": ["freeform", 1993, {"works": True}]
                }
            },
        )
        unknown.add_capability("casts_dynamic_shadow")
        unknown.add_capability("future_capability_not_in_any_enum")
        unknown.add_evidence(Evidence("photo-1", 0.71, "observed"))
        room = WorldEntity(entity_id="room-x", labels=["impossible_future_room_type"])
        graph.add_entity(unknown)
        graph.add_entity(room)
        graph.add_relation(
            WorldRelation(
                relation_id="relation-x",
                subject_id="thing-47",
                predicate="mysteriously_resonates_with",
                object_id="room-x",
                confidence=0.55,
                evidence=[Evidence("photo-1", 0.6, "inferred")],
            )
        )

        encoded = graph.to_dict()
        self.assertIn(
            "label_that_never_existed_when_hayuya_was_written",
            encoded["entities"]["thing-47"]["labels"],
        )
        self.assertIn(
            "future_capability_not_in_any_enum",
            encoded["entities"]["thing-47"]["capabilities"],
        )
        self.assertEqual(
            encoded["relations"]["relation-x"]["predicate"],
            "mysteriously_resonates_with",
        )

    def test_missing_evidence_source_is_rejected(self):
        graph = WorldGraph("bad-evidence")
        entity = WorldEntity(entity_id="x")
        entity.add_evidence(Evidence("missing-source", 0.9))
        graph.add_entity(entity)
        with self.assertRaises(ValueError):
            graph.to_dict()

    def test_provider_registry_exposes_google_without_requiring_secret_in_git(self):
        providers = default_providers()
        google = providers["google_maps_platform"]
        self.assertIn("photorealistic_3d_tiles", google.capabilities)
        report = readiness_report(
            ["google_maps_platform"],
            env={"GOOGLE_MAPS_API_KEY": ""},
        )
        self.assertFalse(report["providers"]["google_maps_platform"]["ready"])
        self.assertEqual(
            report["providers"]["google_maps_platform"]["missing_credentials"],
            ["GOOGLE_MAPS_API_KEY"],
        )

    def test_google_images_is_legacy_optional_not_scrape_fallback(self):
        provider = default_providers()["google_custom_search_legacy"]
        self.assertIn("closed to new customers", provider.notes)
        self.assertIn("Never scrape Google Images HTML", provider.notes)

    def test_plan_is_open_world_and_keeps_truth_layers_separate(self):
        plan = make_plan(
            job_id="sanctum-world",
            sources=["church-front.jpg", "https://example.com/context.webp"],
            goal="build the complete playable location",
            provider_ids=["user_capture", "overture_maps", "openstreetmap_overpass"],
            bounds=[-66.8, 18.1, -66.7, 18.2],
            env={},
        )
        self.assertTrue(plan["perception_policy"]["freeform_labels"])
        self.assertTrue(plan["perception_policy"]["unknown_is_valid"])
        self.assertFalse(plan["perception_policy"]["closed_class_detector_is_authoritative"])
        self.assertEqual(
            set(plan["truth_layers"]),
            {"observed", "inferred", "generated", "policy"},
        )
        self.assertIn("xziel_compile", plan["stages"])
        self.assertEqual(len(plan["world_graph"]["sources"]), 2)

    def test_bounds_validation(self):
        self.assertEqual(
            parse_bounds("-66.8,18.1,-66.7,18.2"),
            [-66.8, 18.1, -66.7, 18.2],
        )
        with self.assertRaises(ValueError):
            parse_bounds("-66.7,18.2,-66.8,18.1")

    def test_zombies_design_brain_loads_complete_clean_room_profile(self):
        intelligence = compile_design_intelligence("sanctum_classic")
        self.assertEqual(intelligence["engine"], "HAYUYA Map Structure Brain")
        self.assertGreaterEqual(intelligence["knowledge"]["atlas_map_count"], 60)
        self.assertEqual(len(intelligence["source_maps"]), 8)
        self.assertTrue(intelligence["targets"]["requiredEarlyFork"])
        self.assertTrue(intelligence["targets"]["requiredCompletedCombatLoop"])
        self.assertTrue(intelligence["generation_contract"]["author_original_geometry"])
        self.assertFalse(intelligence["generation_contract"]["copy_reference_layout"])
        self.assertIn("no_exact_layout_reconstruction", intelligence["guardrails"])
        self.assertGreaterEqual(len(intelligence["cross_map_patterns"]["archetypes"]), 6)
        self.assertTrue(intelligence["cross_map_patterns"]["global_rules"])

    def test_hayuya_lighting_profile_preserves_horror_and_readability(self):
        lighting = compile_lighting_intelligence("zombies_horror")
        self.assertEqual(lighting["engine"], "HAYUYA Lighting")
        self.assertIn("power_off", lighting["states"])
        self.assertIn("power_on", lighting["states"])
        self.assertIn("storm_flash", lighting["states"])
        self.assertTrue(lighting["beauty_contract"]["depth_layers_required"])
        self.assertFalse(
            lighting["beauty_contract"]["black_crush_on_critical_path_allowed"]
        )
        self.assertFalse(
            lighting["beauty_contract"]["constant_random_flicker_allowed"]
        )
        self.assertIn("power_off", lighting["cross_map_state_composition"])

    def test_zombie_goal_auto_attaches_map_and_lighting_intelligence(self):
        plan = make_plan(
            job_id="zombies-intelligence",
            sources=["church-reference.jpg"],
            goal="author an original round-based zombie horror map for Xziel",
            provider_ids=["user_capture"],
            env={},
        )
        self.assertEqual(
            plan["map_design_intelligence"]["profile_id"],
            "sanctum_classic",
        )
        self.assertEqual(
            plan["lighting_intelligence"]["profile_id"],
            "zombies_horror",
        )
        self.assertIn("zombies_map_dna_atlas", plan["knowledge_library"])
        self.assertIn("lighting_standard", plan["knowledge_library"])
        self.assertIn(
            "zombies_design_pattern_library",
            plan["knowledge_library"],
        )
        self.assertIn(
            "zombies_lighting_pattern_library",
            plan["knowledge_library"],
        )
        self.assertTrue(
            plan["lighting_intelligence"]["selected_horror_identities"]
        )

    def test_generic_world_does_not_force_zombies_profile(self):
        plan = make_plan(
            job_id="generic-world",
            sources=[],
            goal="reconstruct a neutral city block from survey evidence",
            provider_ids=["user_capture"],
            env={},
        )
        self.assertIsNone(plan["map_design_intelligence"])
        self.assertIsNone(plan["lighting_intelligence"])


if __name__ == "__main__":
    unittest.main()
