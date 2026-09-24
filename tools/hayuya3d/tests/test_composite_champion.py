from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import trimesh
from PIL import Image

from tools.hayuya3d.composite_champion import (
    build_composite_plan,
    execute_safe_head_wrap_challenger,
    execute_safe_material_challenger,
)


def candidate(
    backend: str,
    score: float,
    *,
    face_min=None,
    face_mesh=None,
    face_tex=None,
    face_detail=None,
    visual=None,
    appearance=None,
    material=None,
    texture=None,
):
    return SimpleNamespace(
        backend=backend,
        path=f"/tmp/{backend}.glb",
        score=score,
        valid=True,
        production_score=score,
        visual_score=visual,
        appearance_score=appearance,
        appearance_face_detail_score=face_min,
        appearance_face_detail_min_score=face_min,
        head_density_score=face_mesh,
        head_texel_density_score=face_tex,
        head_texture_detail_score=face_detail,
        material_score=material,
        texture_resolution_score=texture,
    )


class CompositeChampionPlannerTests(unittest.TestCase):
    def test_high_global_base_can_borrow_better_face(self):
        base=candidate(
            "global99",99.0,
            face_min=70.0,
            face_mesh=97.0,
            face_tex=96.0,
            face_detail=82.0,
            visual=99.0,
            appearance=98.0,
            material=98.0,
            texture=100.0,
        )
        face=candidate(
            "face80",80.0,
            face_min=98.0,
            face_mesh=100.0,
            face_tex=100.0,
            face_detail=99.0,
            visual=80.0,
            appearance=90.0,
            material=85.0,
            texture=100.0,
        )
        plan=build_composite_plan(
            [base,face],
            mode="character",
            inspect_parts=False,
        )
        self.assertEqual(plan.base_backend,"global99")
        identity=next(x for x in plan.donors if x.region=="face_identity")
        self.assertEqual(identity.donor_backend,"face80")
        self.assertEqual(identity.base_score,70.0)
        self.assertEqual(identity.donor_score,98.0)
        self.assertTrue(plan.composite_required)
        self.assertIn("face_identity",plan.executable_now)
        self.assertNotIn("face_identity",plan.deferred_transfers)

    def test_material_and_face_can_come_from_different_finalists(self):
        base=candidate(
            "base",95.0,
            face_min=85.0,face_mesh=95.0,face_tex=90.0,face_detail=88.0,
            visual=96.0,appearance=93.0,material=80.0,texture=90.0,
        )
        face=candidate(
            "face",84.0,
            face_min=99.0,face_mesh=100.0,face_tex=100.0,face_detail=100.0,
            visual=82.0,appearance=90.0,material=75.0,texture=90.0,
        )
        material=candidate(
            "material",83.0,
            face_min=80.0,face_mesh=92.0,face_tex=95.0,face_detail=94.0,
            visual=81.0,appearance=91.0,material=100.0,texture=100.0,
        )
        plan=build_composite_plan(
            [base,face,material],
            mode="character",
            inspect_parts=False,
        )
        donors={x.region:x.donor_backend for x in plan.donors}
        self.assertEqual(donors["face_identity"],"face")
        self.assertEqual(donors["face_geometry"],"face")
        self.assertEqual(donors["material_response"],"material")
        self.assertEqual(donors["texture_resolution"],"material")

    def test_single_finalist_stays_non_composite(self):
        only=candidate(
            "only",91.0,
            face_min=90.0,face_mesh=100.0,face_tex=100.0,face_detail=90.0,
            visual=91.0,appearance=91.0,material=91.0,texture=100.0,
        )
        plan=build_composite_plan(
            [only],
            mode="character",
            inspect_parts=False,
        )
        self.assertFalse(plan.composite_required)
        self.assertEqual(plan.deferred_transfers,[])
        self.assertEqual(plan.executable_now,[])

    def test_small_metric_noise_does_not_request_composite(self):
        base=candidate(
            "base",95.0,
            face_min=90.0,face_mesh=99.0,face_tex=99.0,face_detail=90.0,
            visual=95.0,appearance=95.0,material=95.0,texture=100.0,
        )
        tiny=candidate(
            "tiny",90.0,
            face_min=90.2,face_mesh=99.2,face_tex=99.2,face_detail=90.2,
            visual=94.0,appearance=94.0,material=95.2,texture=100.0,
        )
        plan=build_composite_plan(
            [base,tiny],
            mode="character",
            minimum_regional_gain=0.5,
            inspect_parts=False,
        )
        self.assertFalse(plan.composite_required)

    def test_face_donor_executes_as_head_wrap_challenger_when_unskinned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            base_path=root/"base_face.glb"
            donor_path=root/"donor_face.glb"

            sphere=trimesh.creation.icosphere(subdivisions=3,radius=1.0)
            base_vertices=np.asarray(sphere.vertices,dtype=np.float64).copy()
            base_vertices[:,1]*=2.0
            lo=float(base_vertices[:,1].min())
            hi=float(base_vertices[:,1].max())
            normalized=(base_vertices[:,1]-lo)/max(hi-lo,1e-9)
            donor_vertices=base_vertices.copy()
            head=normalized>=0.78
            donor_vertices[head,0]*=1.12
            donor_vertices[head,2]*=1.12

            base_mesh=trimesh.Trimesh(
                vertices=base_vertices,
                faces=np.asarray(sphere.faces).copy(),
                process=False,
            )
            donor_mesh=trimesh.Trimesh(
                vertices=donor_vertices,
                faces=np.asarray(sphere.faces).copy(),
                process=False,
            )
            base_path.write_bytes(
                trimesh.exchange.gltf.export_glb(trimesh.Scene(base_mesh))
            )
            donor_path.write_bytes(
                trimesh.exchange.gltf.export_glb(trimesh.Scene(donor_mesh))
            )

            base=candidate(
                "base",99.0,
                face_min=70.0,face_mesh=98.0,face_tex=98.0,face_detail=90.0,
                visual=99.0,appearance=96.0,material=90.0,texture=100.0,
            )
            donor=candidate(
                "face",80.0,
                face_min=98.0,face_mesh=100.0,face_tex=98.0,face_detail=96.0,
                visual=80.0,appearance=92.0,material=85.0,texture=100.0,
            )
            base.path=str(base_path)
            donor.path=str(donor_path)
            plan=build_composite_plan(
                [base,donor],
                mode="character",
                inspect_parts=False,
            )
            self.assertIn("face_identity",plan.executable_now)

            result=execute_safe_head_wrap_challenger(
                plan,
                root/"head-composite",
                texture_size=256,
            )
            self.assertTrue(result.attempted)
            self.assertTrue(result.ready,result.error)
            self.assertEqual(result.donor_backend,"face")
            self.assertTrue(Path(result.candidate_path or "").is_file())
            self.assertTrue(result.fusion and result.fusion["geometry_ready"])

    def test_material_donor_executes_as_geometry_preserving_challenger(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            base_path=root/"base.glb"
            donor_path=root/"donor.glb"

            vertices=np.array([
                [-0.5,-0.5,0.0],
                [ 0.5,-0.5,0.0],
                [ 0.5, 0.5,0.0],
                [-0.5, 0.5,0.0],
            ],dtype=np.float64)
            faces=np.array([[0,1,2],[0,2,3]],dtype=np.int64)
            uv=np.array([
                [0.0,0.0],
                [1.0,0.0],
                [1.0,1.0],
                [0.0,1.0],
            ],dtype=np.float64)

            base_material=trimesh.visual.material.PBRMaterial(
                baseColorTexture=Image.fromarray(
                    np.full((8,8,4),[90,90,90,255],dtype=np.uint8),
                    mode="RGBA",
                ),
                roughnessFactor=0.9,
                metallicFactor=0.0,
            )
            donor_material=trimesh.visual.material.PBRMaterial(
                baseColorTexture=Image.fromarray(
                    np.full((8,8,4),[190,60,45,255],dtype=np.uint8),
                    mode="RGBA",
                ),
                metallicRoughnessTexture=Image.fromarray(
                    np.full((8,8,3),[0,80,180],dtype=np.uint8),
                    mode="RGB",
                ),
                roughnessFactor=0.55,
                metallicFactor=0.25,
            )
            base_mesh=trimesh.Trimesh(
                vertices=vertices,
                faces=faces,
                process=False,
                visual=trimesh.visual.TextureVisuals(
                    uv=uv,
                    material=base_material,
                ),
            )
            donor_mesh=trimesh.Trimesh(
                vertices=vertices,
                faces=faces,
                process=False,
                visual=trimesh.visual.TextureVisuals(
                    uv=uv,
                    material=donor_material,
                ),
            )
            base_path.write_bytes(
                trimesh.exchange.gltf.export_glb(trimesh.Scene(base_mesh))
            )
            donor_path.write_bytes(
                trimesh.exchange.gltf.export_glb(trimesh.Scene(donor_mesh))
            )

            base=candidate(
                "base",95.0,
                face_min=90.0,face_mesh=100.0,face_tex=100.0,face_detail=90.0,
                visual=95.0,appearance=95.0,material=60.0,texture=100.0,
            )
            donor=candidate(
                "material",80.0,
                face_min=80.0,face_mesh=95.0,face_tex=95.0,face_detail=85.0,
                visual=80.0,appearance=88.0,material=95.0,texture=100.0,
            )
            base.path=str(base_path)
            donor.path=str(donor_path)
            plan=build_composite_plan(
                [base,donor],
                mode="character",
                inspect_parts=False,
            )
            self.assertIn("material_response",plan.executable_now)

            result=execute_safe_material_challenger(
                plan,
                root/"composite",
                texture_size=64,
                total_samples=4000,
            )
            self.assertTrue(result.attempted)
            self.assertTrue(result.ready,result.error)
            self.assertTrue(result.geometry_preserved)
            self.assertEqual(result.donor_backend,"material")
            self.assertTrue(Path(result.candidate_path or "").is_file())
            self.assertEqual(
                Path(result.candidate_path or "").read_bytes()[:4],
                b"glTF",
            )

    def test_promotion_contract_requires_rejudge_and_atomic_fallback(self):
        base=candidate(
            "base",95.0,
            face_min=80.0,face_mesh=90.0,face_tex=90.0,face_detail=80.0,
            visual=95.0,appearance=95.0,material=95.0,texture=100.0,
        )
        donor=candidate(
            "donor",85.0,
            face_min=98.0,face_mesh=100.0,face_tex=100.0,face_detail=98.0,
            visual=85.0,appearance=90.0,material=90.0,texture=100.0,
        )
        plan=build_composite_plan(
            [base,donor],
            mode="character",
            inspect_parts=False,
        )
        text=" ".join(plan.promotion_contract+plan.notes).lower()
        self.assertIn("re-enter",text)
        self.assertIn("weakest face",text)
        self.assertIn("atomic",text)
        self.assertIn("rig",text)


if __name__=="__main__":
    unittest.main()
