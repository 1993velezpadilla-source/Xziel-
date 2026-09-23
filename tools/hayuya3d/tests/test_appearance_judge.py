from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HAYUYA_DIR = ROOT / "tools" / "hayuya3d"
sys.path.insert(0, str(HAYUYA_DIR))

import numpy as np
from appearance_judge import aggregate_appearance_scores, cosine_similarity, rasterize_rgb


class AppearanceJudgeTests(unittest.TestCase):
    def test_cosine_identity(self):
        a = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        self.assertAlmostEqual(cosine_similarity(a, a), 1.0, places=6)

    def test_cosine_orthogonal(self):
        a = np.array([1.0, 0.0], dtype=np.float32)
        b = np.array([0.0, 1.0], dtype=np.float32)
        self.assertAlmostEqual(cosine_similarity(a, b), 0.0, places=6)

    def test_many_view_appearance_penalizes_weak_tail(self):
        good = aggregate_appearance_scores([91, 90, 92, 89, 90])
        mixed = aggregate_appearance_scores([95, 94, 93, 92, 30])
        self.assertGreater(good, mixed)

    def test_cpu_rasterizer_draws_triangle(self):
        xy = np.array([[8, 8], [56, 8], [32, 56]], dtype=np.float32)
        z = np.array([1, 1, 1], dtype=np.float32)
        faces = np.array([[0, 1, 2]], dtype=np.int64)
        colors = np.array([[255, 0, 0], [255, 0, 0], [255, 0, 0]], dtype=np.float32)
        image = np.asarray(rasterize_rgb(xy, z, faces, colors, size=64))
        self.assertGreater(int(image[:, :, 0].max()), 200)
        self.assertTrue(np.any(np.all(image != np.array([127, 127, 127]), axis=2)))

    def test_zbuffer_prefers_larger_depth(self):
        xy = np.array([
            [8, 8], [56, 8], [32, 56],
            [8, 8], [56, 8], [32, 56],
        ], dtype=np.float32)
        z = np.array([0, 0, 0, 1, 1, 1], dtype=np.float32)
        faces = np.array([[0, 1, 2], [3, 4, 5]], dtype=np.int64)
        colors = np.array([
            [255, 0, 0], [255, 0, 0], [255, 0, 0],
            [0, 255, 0], [0, 255, 0], [0, 255, 0],
        ], dtype=np.float32)
        image = np.asarray(rasterize_rgb(xy, z, faces, colors, size=64))
        center = image[32, 32]
        self.assertGreater(int(center[1]), int(center[0]))


if __name__ == "__main__":
    unittest.main()
