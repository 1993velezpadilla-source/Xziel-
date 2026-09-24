from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.hayuya3d import hayuya


class HighEndTextureContractTests(unittest.TestCase):
    def test_monster_and_ultra_require_native_4k_visible_textures(self):
        self.assertEqual(hayuya.PROFILES["monster"].texture_size, 4096)
        self.assertEqual(hayuya.PROFILES["ultra"].texture_size, 4096)

    def test_texture_superres_only_targets_high_end_under_resolved_visible_color(self):
        self.assertTrue(hayuya.needs_texture_superres("monster", 2048, 4096))
        self.assertTrue(hayuya.needs_texture_superres("ultra", 1024, 4096))
        self.assertFalse(hayuya.needs_texture_superres("game", 1024, 2048))
        self.assertFalse(hayuya.needs_texture_superres("monster", 4096, 4096))
        self.assertFalse(hayuya.needs_texture_superres("monster", 0, 4096))
        self.assertFalse(hayuya.needs_texture_superres("monster", None, 4096))

    def test_build_plan_documents_texture_superres_as_challenger(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            image=root/"front.png"
            from PIL import Image
            Image.new("RGB",(32,32),(120,80,60)).save(image)
            plan=hayuya.make_job_plan(
                [image],
                profile_name="monster",
                mode="character",
                seed=1993,
                selected_backends=["trellis2"],
                model_root=root/"models",
                texture_superres_mode="auto",
            )
        self.assertEqual(plan["texture_superres"]["mode"],"auto")
        self.assertIn("challenger",plan["texture_superres"]["policy"])
        self.assertEqual(plan["texture_superres"]["model"],"realesrgan-x4plus")

    def test_trellis2_receives_profile_texture_target_without_downshift(self):
        calls = {}

        def fake_generator(image, out_dir, **kwargs):
            calls.update(kwargs)
            return object()

        original = hayuya.GENERATORS["trellis2"]
        hayuya.GENERATORS["trellis2"] = fake_generator
        try:
            with tempfile.TemporaryDirectory() as tmp:
                hayuya.run_single_backend(
                    "trellis2",
                    Path(tmp) / "face.png",
                    Path(tmp) / "out",
                    profile=hayuya.PROFILES["monster"],
                    seed=1993,
                    model_root=Path(tmp) / "models",
                )
            self.assertEqual(calls["texture_size"], 4096)
            self.assertEqual(calls["resolution"], 1024)
            self.assertEqual(calls["faces"], 250000)
        finally:
            hayuya.GENERATORS["trellis2"] = original


if __name__ == "__main__":
    unittest.main()
