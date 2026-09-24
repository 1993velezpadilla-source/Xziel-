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
