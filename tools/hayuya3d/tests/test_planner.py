from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HAYUYA_DIR = ROOT / "tools" / "hayuya3d"
sys.path.insert(0, str(HAYUYA_DIR))

from reference_pool import classify_reference, split_reference_roles

spec = importlib.util.spec_from_file_location("hayuya_main", HAYUYA_DIR / "hayuya.py")
hayuya = importlib.util.module_from_spec(spec)
assert spec.loader
sys.modules[spec.name] = hayuya
spec.loader.exec_module(hayuya)


class HayuyaPlannerTests(unittest.TestCase):
    def test_profiles_have_monster_path(self):
        p = hayuya.PROFILES["monster"]
        self.assertGreaterEqual(p.faces, 200_000)
        self.assertGreaterEqual(p.texture_size, 4096)
        self.assertIn("trellis2", p.backends)
        self.assertIn("triposg", p.backends)
        self.assertIn("trellis", p.backends)

    def test_multi_photo_plan_has_no_logical_limit(self):
        refs = [Path(f"/tmp/view-{i}.png") for i in range(9)]
        plan = hayuya.make_job_plan(
            refs,
            profile_name="monster",
            mode="character",
            seed=1993,
            selected_backends=["trellis2", "triposg", "trellis"],
            model_root=Path("/tmp/models"),
        )
        self.assertEqual(plan["input_count"], 9)
        self.assertIsNone(plan["reference_pool"]["logical_limit"])
        self.assertTrue(plan["multi_reference"]["enabled"])
        self.assertTrue(plan["multi_reference"]["all_geometry_sources_always_used_by_judge"])
        self.assertIn("reference-pool fusion", plan["viewforge"]["strategy"])

    def test_reference_groups_cover_every_source(self):
        refs = [Path(f"/tmp/view-{i}.png") for i in range(14)]
        groups = hayuya.make_reference_groups(refs, 6)
        self.assertGreater(len(groups), 1)
        self.assertTrue(all(group[0] == refs[0] for group in groups))
        covered = {p for group in groups for p in group}
        self.assertEqual(covered, set(refs))
        self.assertTrue(all(len(group) <= 6 for group in groups))

    def test_anchor_budget_zero_means_all_sources(self):
        refs = [Path(f"/tmp/view-{i}.png") for i in range(11)]
        self.assertEqual(hayuya.limit_anchor_refs(refs, 0), refs)
        limited = hayuya.limit_anchor_refs(refs, 4)
        self.assertEqual(len(limited), 4)
        self.assertEqual(limited[0], refs[0])
        self.assertEqual(limited[-1], refs[-1])

    def test_detail_references_are_preserved_but_not_geometry_judged(self):
        refs = [
            Path("/tmp/zombie_front.png"),
            Path("/tmp/zombie_back.png"),
            Path("/tmp/zombie_face_closeup.png"),
            Path("/tmp/zombie_hand_detail.png"),
        ]
        roles = split_reference_roles(refs)
        self.assertEqual(roles.geometry, refs[:2])
        self.assertEqual(roles.detail, refs[2:])

        plan = hayuya.make_job_plan(
            refs,
            profile_name="monster",
            mode="character",
            seed=1993,
            selected_backends=["trellis", "triposg"],
            model_root=Path("/tmp/models"),
        )
        self.assertEqual(plan["reference_pool"]["geometry_source_count"], 2)
        self.assertEqual(plan["reference_pool"]["detail_source_count"], 2)
        self.assertEqual(plan["multi_reference"]["group_count"], 1)

    def test_reference_role_inference_is_conservative(self):
        self.assertEqual(classify_reference(Path("zombie_front.png")), "geometry")
        self.assertEqual(classify_reference(Path("zombie_face_closeup.png")), "detail")
        self.assertEqual(classify_reference(Path("zombie_texture_detail.png")), "detail")
        self.assertEqual(classify_reference(Path("refs/details/01.png")), "detail")
        self.assertEqual(classify_reference(Path("refs/textures/albedo.png")), "detail")
        self.assertEqual(classify_reference(Path("refs/individual/zombie_back.png")), "geometry")
        self.assertEqual(classify_reference(Path("unknown_phone_photo.png")), "geometry")

    def test_default_stack_is_permissive(self):
        lock = hayuya.load_lock()
        for item in lock["backends"]:
            if item["enabled_by_default"]:
                self.assertIn(item["license"], {"MIT", "Apache-2.0"})

    def test_vram_budget_filters_expensive_models(self):
        lock = hayuya.load_lock()
        selected = hayuya.choose_backends(
            lock,
            hayuya.PROFILES["monster"],
            None,
            gpu_vram=8,
            allow_restricted=False,
        )
        self.assertIn("triposg", selected)
        self.assertIn("triposr", selected)
        self.assertNotIn("trellis2", selected)
        self.assertNotIn("trellis", selected)
        self.assertNotIn("instantmesh", selected)

    def test_hunyuan_is_not_default(self):
        lock = hayuya.load_lock()
        meta = hayuya.backend_meta(lock)
        self.assertFalse(meta["hunyuan3d_2_1"]["enabled_by_default"])


if __name__ == "__main__":
    unittest.main()
