#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
HAYUYA3D = HERE.parent
sys.path.insert(0, str(HAYUYA3D))

from hayuya_ads import compile_monetization_intelligence, discover_diegetic_candidates
from universal_game_design import compile_universal_design_intelligence, infer_domains
from world_reasoning import compile_world_reasoning_intelligence
from world_model_broker import compile_world_model_broker


class UniversalDesignBrainTests(unittest.TestCase):
    def test_horror_coop_mobile_goal_loads_cross_genre_domains(self):
        domains = infer_domains(
            "four player co-op zombie survival horror FPS on Android mobile"
        )
        self.assertIn("survival_horror", domains)
        self.assertIn("combat", domains)
        self.assertIn("coop", domains)
        self.assertIn("navigation", domains)
        self.assertIn("technical", domains)

    def test_universal_design_is_not_a_closed_world_ontology(self):
        plan = compile_universal_design_intelligence(
            "open world stealth survival map",
            custom_constraints=[
                "invent a traversal mechanic that is not in the standard library"
            ],
        )
        self.assertTrue(plan["generation_contract"]["domain_library_is_not_ontology"])
        self.assertTrue(plan["generation_contract"]["freeform_gameplay_constraints_allowed"])
        self.assertIn(
            "invent a traversal mechanic that is not in the standard library",
            plan["custom_constraints"],
        )
        self.assertGreaterEqual(plan["ai_world_research"]["system_count"], 10)

    def test_solver_agents_are_part_of_generation_contract(self):
        plan = compile_universal_design_intelligence("tactical puzzle campaign")
        self.assertIn("critical_path_solver", plan["solver_agents"])
        self.assertIn("lost_player_agent", plan["solver_agents"])
        self.assertIn("solve_before_expensive_art", plan["generation_contract"])
        self.assertTrue(plan["generation_contract"]["solve_before_expensive_art"])


class WorldReasoningBrainTests(unittest.TestCase):
    def test_all_world_domains_remain_available_even_when_not_prioritized(self):
        plan = compile_world_reasoning_intelligence("small interior horror map on Android")
        self.assertEqual(plan["knowledge_scope"], "all_domains_available")
        self.assertIn("architecture", plan["domains"])
        self.assertIn("terrain_and_hydrology", plan["domains"])
        self.assertIn("multiplayer_networking", plan["domains"])
        self.assertIn("monetization_and_policy", plan["domains"])
        self.assertTrue(plan["reasoning_contract"]["priority_is_not_exclusion"])

    def test_goal_prioritizes_but_does_not_remove_domains(self):
        plan = compile_world_reasoning_intelligence(
            "online four player city map with ads and Google Play mobile target"
        )
        self.assertIn("urbanism", plan["priority_domains"])
        self.assertIn("multiplayer_networking", plan["priority_domains"])
        self.assertIn("mobile_rendering", plan["priority_domains"])
        self.assertIn("monetization_and_policy", plan["priority_domains"])


class WorldModelBrokerTests(unittest.TestCase):
    def test_geometry_arena_has_independent_candidates(self):
        broker = compile_world_model_broker()
        ids = [x["id"] for x in broker["stages"]["metric_geometry_arena"]]
        self.assertIn("meta_mapanything", ids)
        self.assertIn("meta_vggt", ids)
        self.assertTrue(broker["policies"]["independent_challengers_for_uncertain_geometry"])

    def test_product_benchmarks_do_not_claim_execution(self):
        broker = compile_world_model_broker()
        genie = broker["stages"]["interactive_world_simulation"][1]
        self.assertEqual(genie["id"], "google_genie_3")
        self.assertEqual(genie["mode"], "product_benchmark")
        self.assertFalse(genie["execution"]["wired_in_hayuya_map"])
        self.assertTrue(broker["policies"]["research_is_not_execution"])


class MonetizationBrainTests(unittest.TestCase):
    def test_brandable_world_entity_becomes_direct_diegetic_candidate(self):
        graph = {
            "entities": {
                "radio-1": {
                    "labels": ["old radio"],
                    "aliases": [],
                    "capabilities": ["radio_or_speaker"],
                    "properties": {},
                }
            }
        }
        candidates = discover_diegetic_candidates(graph)
        self.assertEqual(len(candidates), 1)
        slot = candidates[0]
        self.assertEqual(slot["delivery_path"], "DIRECT_DIEGETIC_SPONSOR")
        self.assertIn("SPATIAL_AUDIO", slot["accepted_formats"])
        self.assertFalse(slot["network_required"])
        self.assertTrue(slot["fallback_required"])

    def test_gameplay_critical_surface_is_never_auto_sold(self):
        graph = {
            "entities": {
                "door-sign": {
                    "labels": ["navigation_critical_sign"],
                    "aliases": [],
                    "capabilities": ["flat_noninteractive_surface"],
                    "properties": {"navigation_critical": True},
                }
            }
        }
        self.assertEqual(discover_diegetic_candidates(graph), [])

    def test_google_programmatic_is_ui_not_world_texture(self):
        plan = compile_monetization_intelligence({"entities": {}})
        self.assertFalse(plan["policy"]["programmatic_world_space_texture_baking"])
        self.assertTrue(
            plan["policy"]["direct_diegetic_and_google_programmatic_are_separate"]
        )
        google = plan["delivery_paths"]["GOOGLE_ADMOB_UI"]
        self.assertFalse(google["worldSpace"])
        self.assertIn("INTERSTITIAL", google["formats"])
        self.assertIn("REWARDED", google["formats"])
        self.assertGreater(plan["shared_xziel_ad_contract"]["inventory_pattern_count"], 30)
        self.assertTrue(plan["shared_xziel_ad_contract"]["google_play_principles"]["gameplayFirst"])

    def test_active_gameplay_rejects_programmatic_overlay(self):
        plan = compile_monetization_intelligence({"entities": {}})
        rules = plan["runtime_hooks"]["active_gameplay"]["rules"]
        self.assertIn("no_programmatic_fullscreen", rules)
        self.assertIn("no_programmatic_banner_overlay", rules)


if __name__ == "__main__":
    unittest.main()
