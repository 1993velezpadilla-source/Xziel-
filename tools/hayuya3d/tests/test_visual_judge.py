from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HAYUYA_DIR = ROOT / "tools" / "hayuya3d"
sys.path.insert(0, str(HAYUYA_DIR))

import numpy as np
from visual_judge import score_masks


class VisualJudgeTests(unittest.TestCase):
    def test_identical_silhouette_scores_perfect(self):
        a = np.zeros((64, 64), dtype=bool)
        a[12:52, 18:46] = True
        score, iou, edge = score_masks(a, a.copy())
        self.assertAlmostEqual(iou, 1.0, places=6)
        self.assertAlmostEqual(edge, 1.0, places=6)
        self.assertAlmostEqual(score, 100.0, places=6)

    def test_wrong_shape_scores_lower(self):
        a = np.zeros((64, 64), dtype=bool)
        a[10:54, 20:44] = True

        b = np.zeros((64, 64), dtype=bool)
        yy, xx = np.ogrid[:64, :64]
        b[(xx - 32) ** 2 + (yy - 32) ** 2 <= 17 ** 2] = True

        same, _, _ = score_masks(a, a)
        wrong, _, _ = score_masks(a, b)
        self.assertGreater(same, wrong)
        self.assertLess(wrong, 95.0)

    def test_partial_overlap_is_not_rewarded_as_identity(self):
        a = np.zeros((64, 64), dtype=bool)
        a[12:52, 12:36] = True
        b = np.zeros((64, 64), dtype=bool)
        b[12:52, 28:52] = True
        score, iou, edge = score_masks(a, b)
        self.assertLess(iou, 0.25)
        self.assertLess(score, 40.0)


if __name__ == "__main__":
    unittest.main()
