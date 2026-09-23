from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HAYUYA_DIR = ROOT / "tools" / "hayuya3d"
sys.path.insert(0, str(HAYUYA_DIR))

import numpy as np
import trimesh

from material_bridge import transfer_base_color


class MaterialBridgeTests(unittest.TestCase):
    def test_uniform_source_color_transfers_to_refined_mesh(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_path = root / "source.glb"
            refined_path = root / "refined.glb"
            output_path = root / "bridged.glb"

            source = trimesh.creation.box(extents=[1.0, 1.0, 1.0])
            rgba = np.tile(
                np.array([[20, 210, 60, 255]], dtype=np.uint8),
                (len(source.vertices), 1),
            )
            source.visual = trimesh.visual.ColorVisuals(
                source,
                vertex_colors=rgba,
            )
            source_path.write_bytes(
                trimesh.exchange.gltf.export_glb(trimesh.Scene(source))
            )

            refined = trimesh.creation.icosphere(subdivisions=2, radius=0.48)
            refined_path.write_bytes(
                trimesh.exchange.gltf.export_glb(trimesh.Scene(refined))
            )

            result = transfer_base_color(
                source_path,
                refined_path,
                output_path,
                total_samples=5000,
            )
            self.assertTrue(output_path.is_file())
            self.assertEqual(output_path.read_bytes()[:4], b"glTF")
            self.assertGreater(result.sample_count, 1000)

            loaded = trimesh.load(output_path, force="scene", process=False)
            mesh = trimesh.util.concatenate(list(loaded.geometry.values()))
            colors = np.asarray(mesh.visual.vertex_colors[:, :3])
            mean = colors.mean(axis=0)
            self.assertLess(float(mean[0]), 50.0)
            self.assertGreater(float(mean[1]), 170.0)
            self.assertLess(float(mean[2]), 90.0)


if __name__ == "__main__":
    unittest.main()
