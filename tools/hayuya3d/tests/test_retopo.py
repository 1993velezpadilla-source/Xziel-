from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
HAYUYA_DIR = ROOT / "tools" / "hayuya3d"
sys.path.insert(0, str(HAYUYA_DIR))

from retopo import (
    build_instant_meshes_command,
    instant_meshes_binary,
    parse_obj_topology,
    retopo_target_native_faces,
)


class RetopoTests(unittest.TestCase):
    def test_quad_target_maps_runtime_triangles_to_native_quads(self):
        self.assertEqual(retopo_target_native_faces(20000, "pure_quad"), 10000)
        self.assertEqual(retopo_target_native_faces(20000, "quad_dominant"), 10000)

    def test_command_uses_deterministic_pure_quad_by_default(self):
        cmd = build_instant_meshes_command(
            Path("/tmp/Instant Meshes"),
            Path("/tmp/in.obj"),
            Path("/tmp/out.obj"),
            target_triangle_faces=20000,
            style="pure_quad",
            crease_angle=55.0,
        )
        self.assertIn("--deterministic", cmd)
        self.assertIn("--boundaries", cmd)
        self.assertIn("--faces", cmd)
        self.assertEqual(cmd[cmd.index("--faces") + 1], "10000")
        self.assertNotIn("--dominant", cmd)
        self.assertEqual(cmd[-1], "/tmp/in.obj")

    def test_quad_dominant_flag_is_explicit(self):
        cmd = build_instant_meshes_command(
            Path("/tmp/Instant Meshes"),
            Path("/tmp/in.obj"),
            Path("/tmp/out.obj"),
            target_triangle_faces=8000,
            style="quad_dominant",
            crease_angle=70.0,
        )
        self.assertIn("--dominant", cmd)

    def test_obj_topology_counts_quads_triangles_and_ngons(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mesh.obj"
            path.write_text(
                "\n".join([
                    "v 0 0 0",
                    "v 1 0 0",
                    "v 1 1 0",
                    "v 0 1 0",
                    "v 0 0 1",
                    "f 1 2 3 4",
                    "f 1 2 5",
                    "f 1 2 3 4 5",
                ]) + "\n",
                encoding="utf-8",
            )
            stats = parse_obj_topology(path)
            self.assertEqual(stats["polygon_count"], 3)
            self.assertEqual(stats["quad_count"], 1)
            self.assertEqual(stats["triangle_count"], 1)
            self.assertEqual(stats["ngon_count"], 1)
            self.assertAlmostEqual(stats["quad_fraction"], 1 / 3)

    def test_binary_environment_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "instant-meshes"
            binary.write_bytes(b"binary")
            with mock.patch.dict(
                os.environ,
                {"HAYUYA_INSTANT_MESHES_BIN": str(binary)},
            ):
                self.assertEqual(instant_meshes_binary(Path(tmp)), binary.resolve())


if __name__ == "__main__":
    unittest.main()
