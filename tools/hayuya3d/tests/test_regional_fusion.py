from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import trimesh

from tools.hayuya3d.regional_fusion import (
    build_head_wrap_geometry,
    prepare_head_wrap_challenger,
)


def make_character(path:Path, *, head_scale:float=1.0):
    mesh=trimesh.creation.icosphere(subdivisions=3,radius=1.0)
    vertices=np.asarray(mesh.vertices,dtype=np.float64).copy()
    # Make Y the character height axis.
    vertices[:,1]*=2.0
    low=float(vertices[:,1].min())
    high=float(vertices[:,1].max())
    norm=(vertices[:,1]-low)/max(high-low,1e-9)
    head=norm>=0.78
    vertices[head,0]*=head_scale
    vertices[head,2]*=head_scale
    out=trimesh.Trimesh(
        vertices=vertices,
        faces=np.asarray(mesh.faces).copy(),
        process=False,
    )
    path.write_bytes(trimesh.exchange.gltf.export_glb(trimesh.Scene(out)))


class RegionalFusionTests(unittest.TestCase):
    def test_head_wrap_changes_head_with_soft_neck_and_bounded_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            base=root/"base.glb"
            donor=root/"donor.glb"
            output=root/"wrapped.glb"
            make_character(base,head_scale=1.0)
            make_character(donor,head_scale=1.18)

            result=build_head_wrap_geometry(
                base,
                donor,
                output,
            )
            self.assertTrue(result.attempted)
            self.assertTrue(result.geometry_ready,result.error)
            self.assertGreater(result.head_vertices,16)
            self.assertGreater(result.changed_vertices,0)
            self.assertTrue(output.is_file())
            self.assertEqual(output.read_bytes()[:4],b"glTF")
            self.assertIsNotNone(result.seam_max_displacement_normalized)
            self.assertLessEqual(
                result.seam_max_displacement_normalized or 1.0,
                0.012,
            )
            self.assertLessEqual(
                result.max_displacement_normalized or 1.0,
                0.055001,
            )
            self.assertLessEqual(
                result.bbox_drift_fraction or 1.0,
                0.08,
            )

    def test_untextured_fixture_needs_no_material_rebake(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            base=root/"base.glb"
            donor=root/"donor.glb"
            make_character(base,head_scale=1.0)
            make_character(donor,head_scale=1.10)

            result=prepare_head_wrap_challenger(
                base,
                donor,
                root/"fusion",
                texture_size=256,
            )
            self.assertTrue(result.geometry_ready,result.error)
            self.assertTrue(result.rebake_ready,result.error)
            self.assertTrue(result.ready_for_judge,result.error)
            self.assertEqual(result.rebake_required,[])
            self.assertTrue(Path(result.output_glb or "").is_file())

    def test_skin_guard_fails_closed_before_geometry_transfer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            base=root/"base.glb"
            donor=root/"donor.glb"
            make_character(base)
            make_character(donor,head_scale=1.1)

            with mock.patch(
                "tools.hayuya3d.regional_fusion._rig_blocked",
                side_effect=[
                    (True,"skinned_geometry_transfer_requires_weight_transfer"),
                ],
            ):
                result=build_head_wrap_geometry(
                    base,
                    donor,
                    root/"blocked.glb",
                )
            self.assertFalse(result.attempted)
            self.assertFalse(result.geometry_ready)
            self.assertFalse(result.ready_for_judge)
            self.assertIn("weight_transfer",result.error or "")
            self.assertFalse((root/"blocked.glb").exists())

    def test_extreme_donor_is_clamped_not_allowed_to_explode_head(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            base=root/"base.glb"
            donor=root/"donor.glb"
            make_character(base,head_scale=1.0)
            make_character(donor,head_scale=3.0)

            result=build_head_wrap_geometry(
                base,
                donor,
                root/"wrapped.glb",
            )
            self.assertTrue(result.attempted)
            self.assertGreater(result.clamped_vertices,0)
            self.assertLessEqual(
                result.max_displacement_normalized or 1.0,
                0.055001,
            )


if __name__=="__main__":
    unittest.main()
