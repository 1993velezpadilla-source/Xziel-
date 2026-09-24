#!/usr/bin/env python3
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
HAYUYA3D = HERE.parent
sys.path.insert(0, str(HAYUYA3D))

from geo_coordinates import (
    WGS84_A,
    ENU,
    Geodetic,
    enu_to_xziel,
    geodetic_to_ecef,
    geodetic_to_enu,
)


class GeoCoordinateTests(unittest.TestCase):
    def test_wgs84_equator_prime_meridian(self):
        p = geodetic_to_ecef(Geodetic(0.0, 0.0, 0.0))
        self.assertAlmostEqual(p.x, WGS84_A, places=5)
        self.assertAlmostEqual(p.y, 0.0, places=5)
        self.assertAlmostEqual(p.z, 0.0, places=5)

    def test_origin_maps_to_zero_enu(self):
        origin = Geodetic(18.25, -66.50, 123.0)
        enu = geodetic_to_enu(origin, origin)
        self.assertAlmostEqual(enu.east, 0.0, places=6)
        self.assertAlmostEqual(enu.north, 0.0, places=6)
        self.assertAlmostEqual(enu.up, 0.0, places=6)

    def test_small_latitude_step_moves_north_in_meters(self):
        origin = Geodetic(18.25, -66.50, 0.0)
        p = Geodetic(18.25001, -66.50, 0.0)
        enu = geodetic_to_enu(p, origin)
        self.assertGreater(enu.north, 1.0)
        self.assertLess(enu.north, 1.2)
        self.assertLess(abs(enu.east), 0.01)

    def test_small_longitude_step_moves_east_in_meters(self):
        origin = Geodetic(18.25, -66.50, 0.0)
        p = Geodetic(18.25, -66.49999, 0.0)
        enu = geodetic_to_enu(p, origin)
        self.assertGreater(enu.east, 1.0)
        self.assertLess(enu.east, 1.2)
        self.assertLess(abs(enu.north), 0.01)

    def test_xziel_default_is_y_up_meter_space(self):
        xz = enu_to_xziel(ENU(east=3.0, north=7.0, up=2.0))
        self.assertEqual((xz.x, xz.y, xz.z), (3.0, 2.0, 7.0))

    def test_invalid_coordinate_rejected(self):
        with self.assertRaises(ValueError):
            geodetic_to_ecef(Geodetic(91.0, 0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
