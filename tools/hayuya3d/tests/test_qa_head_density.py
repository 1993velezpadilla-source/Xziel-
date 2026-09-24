from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
HAYUYA_DIR = ROOT / "tools" / "hayuya3d"
sys.path.insert(0, str(HAYUYA_DIR))

from qa import head_density_score_from_ratio, inspect_mesh


class HeadDensityScoreTests(unittest.TestCase):
    def test_missing_density_is_neutral_telemetry(self):
        self.assertIsNone(head_density_score_from_ratio(None))

    def test_coarse_head_loses_score_proportionally(self):
        self.assertEqual(head_density_score_from_ratio(0.50), 50.0)
        self.assertEqual(head_density_score_from_ratio(0.875), 87.5)

    def test_equal_or_denser_head_caps_at_full_credit(self):
        self.assertEqual(head_density_score_from_ratio(1.0), 100.0)
        self.assertEqual(head_density_score_from_ratio(1.8), 100.0)

    def test_head_texel_density_detects_tiny_face_uv_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "face-uv-budget.glb"

            vertices = np.array([
                [-0.5, -0.5, 0.0],
                [ 0.5, -0.5, 0.0],
                [ 0.5,  0.5, 0.0],
                [-0.5,  0.5, 0.0],
                [-0.5, -0.5, 2.0],
                [ 0.5, -0.5, 2.0],
                [ 0.5,  0.5, 2.0],
                [-0.5,  0.5, 2.0],
            ], dtype=np.float64)
            faces = np.array([
                [0, 1, 2], [0, 2, 3],
                [4, 5, 6], [4, 6, 7],
            ], dtype=np.int64)
            # Lower/body plane owns ~81% of UV area. The upper/head plane gets
            # only ~1%, despite equal world-space surface area.
            uvs = np.array([
                [0.00, 0.00], [0.90, 0.00], [0.90, 0.90], [0.00, 0.90],
                [0.90, 0.90], [1.00, 0.90], [1.00, 1.00], [0.90, 1.00],
            ], dtype=np.float64)
            base = Image.fromarray(
                np.full((256, 256, 4), [160, 100, 80, 255], dtype=np.uint8),
                mode="RGBA",
            )
            material = trimesh.visual.material.PBRMaterial(
                baseColorTexture=base,
                roughnessFactor=0.7,
                metallicFactor=0.0,
            )
            mesh = trimesh.Trimesh(
                vertices=vertices,
                faces=faces,
                process=False,
                visual=trimesh.visual.TextureVisuals(uv=uvs, material=material),
            )
            path.write_bytes(trimesh.exchange.gltf.export_glb(trimesh.Scene(mesh)))

            score = inspect_mesh(
                path,
                backend="face_uv_test",
                mode="character",
                target_faces=4,
                target_texture_size=256,
            )
            self.assertTrue(score.valid, score.notes)
            self.assertIsNotNone(score.head_texel_density_ratio)
            self.assertLess(score.head_texel_density_ratio, 0.10)
            self.assertIsNotNone(score.head_texel_density_score)
            self.assertLess(score.head_texel_density_score, 10.0)
            self.assertTrue(
                any("texel density" in note for note in score.notes or []),
                score.notes,
            )


if __name__ == "__main__":
    unittest.main()
