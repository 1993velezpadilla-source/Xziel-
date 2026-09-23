from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HAYUYA_DIR = ROOT / "tools" / "hayuya3d"
sys.path.insert(0, str(HAYUYA_DIR))

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

    def test_two_photo_plan_enables_dual_anchor(self):
        plan = hayuya.make_job_plan(
            [Path("/tmp/front.png"), Path("/tmp/back.png")],
            profile_name="monster",
            mode="character",
            seed=1993,
            selected_backends=["trellis2", "triposg", "trellis"],
            model_root=Path("/tmp/models"),
        )
        self.assertEqual(plan["input_count"], 2)
        self.assertTrue(plan["dual_anchor"])
        self.assertIn("two-photo anchor fusion", plan["viewforge"]["strategy"])

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
