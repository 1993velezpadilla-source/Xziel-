from __future__ import annotations

import unittest

from tools.hayuya3d.qa import head_density_score_from_ratio


class HeadDensityScoreTests(unittest.TestCase):
    def test_missing_density_is_neutral_telemetry(self):
        self.assertIsNone(head_density_score_from_ratio(None))

    def test_coarse_head_loses_score_proportionally(self):
        self.assertEqual(head_density_score_from_ratio(0.50), 50.0)
        self.assertEqual(head_density_score_from_ratio(0.875), 87.5)

    def test_equal_or_denser_head_caps_at_full_credit(self):
        self.assertEqual(head_density_score_from_ratio(1.0), 100.0)
        self.assertEqual(head_density_score_from_ratio(1.8), 100.0)


if __name__ == "__main__":
    unittest.main()
