from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import trimesh

from tools.hayuya3d.lod_parity import (
    audit_lod_chain,
    compare_lod,
)


def write_sphere(
    path:Path,
    subdivisions:int,
    *,
    scale:float=1.0,
    pbr:bool=False,
)->None:
    mesh=trimesh.creation.icosphere(
        subdivisions=subdivisions,
        radius=0.5*scale,
    )
    if pbr:
        mesh.visual=trimesh.visual.TextureVisuals(
            uv=np.zeros((len(mesh.vertices),2),dtype=np.float64),
            material=trimesh.visual.material.PBRMaterial(
                baseColorFactor=[160,110,80,255],
                metallicFactor=0.0,
                roughnessFactor=0.7,
            ),
        )
    else:
        rgba=np.tile(
            np.array([[160,110,80,255]],dtype=np.uint8),
            (len(mesh.vertices),1),
        )
        mesh.visual=trimesh.visual.ColorVisuals(
            mesh,vertex_colors=rgba
        )
    path.write_bytes(
        trimesh.exchange.gltf.export_glb(
            trimesh.Scene(mesh)
        )
    )


class LODParityTests(unittest.TestCase):
    def test_lower_density_sphere_preserves_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            master=root/"master.glb"
            lod=root/"lod1.glb"
            write_sphere(master,3)
            write_sphere(lod,2)

            item=compare_lod(
                master,lod,
                name="LOD1",
                mode="prop",
                samples=4000,
            )
            self.assertTrue(item.ready,item.errors)
            self.assertLess(item.shape_p95_distance_ratio,0.075)
            self.assertGreater(item.bbox_extent_ratio_min,0.9)
            self.assertLess(item.bbox_extent_ratio_max,1.1)

    def test_collapsed_lod_fails_shape_and_bounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            master=root/"master.glb"
            bad=root/"lod1.glb"
            write_sphere(master,3)
            write_sphere(bad,2,scale=0.2)

            item=compare_lod(
                master,bad,
                name="LOD1",
                mode="prop",
                samples=3000,
            )
            self.assertFalse(item.ready)
            self.assertLess(item.bbox_extent_ratio_min,0.70)
            self.assertTrue(
                any("bbox extent collapse" in x for x in item.errors),
                item.errors,
            )

    def test_chain_requires_monotonic_face_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            master=root/"master.glb"
            lod0=root/"lod0.glb"
            lod1=root/"lod1.glb"
            write_sphere(master,3)
            write_sphere(lod0,1)
            write_sphere(lod1,2)

            report=audit_lod_chain(
                master,
                [("LOD0",lod0),("LOD1",lod1)],
                mode="prop",
                samples=2500,
            )
            self.assertFalse(report.ready)
            self.assertFalse(report.face_chain_monotonic)
            self.assertTrue(
                any("monotonically" in x for x in report.errors),
                report.errors,
            )

    def test_material_channel_loss_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            master=root/"master.glb"
            lod=root/"lod.glb"
            write_sphere(master,2,pbr=True)
            write_sphere(lod,2,pbr=False)

            item=compare_lod(
                master,lod,
                name="LOD1",
                mode="prop",
                samples=2000,
            )
            self.assertFalse(item.ready)
            self.assertTrue(item.missing_material_channels)
            self.assertTrue(
                any("material channels lost" in x for x in item.errors),
                item.errors,
            )


if __name__=="__main__":
    unittest.main()
