from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HAYUYA_DIR = ROOT / "tools" / "hayuya3d"
sys.path.insert(0, str(HAYUYA_DIR))

from studio_server import JobState, hydrate_candidate_ranking, parse_multipart, parse_pipeline_line


class StudioServerTests(unittest.TestCase):
    def make_job(self, root: Path) -> JobState:
        return JobState(id="test-job", root=str(root))

    def test_parse_candidate_and_final_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate = root / "output" / "candidate.glb"
            candidate.parent.mkdir(parents=True)
            candidate.write_bytes(b"glTF" + b"x" * 32)
            final = root / "output" / "hayuya_final.glb"
            final.write_bytes(b"glTF" + b"y" * 32)

            job = self.make_job(root)
            parse_pipeline_line(
                job,
                f"HAYUYA_CANDIDATE_READY trellis2 {candidate} source=front.png",
            )
            self.assertIn("trellis2", job.candidates)
            self.assertEqual(job.stage, "generating")
            self.assertTrue(job.candidates["trellis2"].url.endswith("output/candidate.glb"))

            parse_pipeline_line(
                job,
                "HAYUYA_JUDGE_SCORE backend=trellis2 score=88.75 valid=true rank=1 pass=1",
            )
            self.assertEqual(job.stage, "judge")
            self.assertEqual(job.candidates["trellis2"].score, 88.75)
            self.assertEqual(job.events[-1]["kind"], "judge_score")

            parse_pipeline_line(
                job,
                "HAYUYA_CHAMPION backend=trellis2 score=91.25 references=4",
            )
            self.assertEqual(job.champion, "trellis2")
            self.assertTrue(job.candidates["trellis2"].is_champion)
            self.assertEqual(job.candidates["trellis2"].score, 91.25)

            parse_pipeline_line(job, f"HAYUYA_MONSTER_READY {final}")
            self.assertTrue(job.final_model_url.endswith("output/hayuya_final.glb"))

    def test_live_judge_metrics_hydrate_candidate_and_emit_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate = root / "candidate.glb"
            candidate.write_bytes(b"glTF" + b"x" * 32)
            job = self.make_job(root)
            parse_pipeline_line(
                job,
                f"HAYUYA_CANDIDATE_READY trellis2 {candidate} source=front.png",
            )
            metrics = {
                "backend": "trellis2",
                "production_score": 89.0,
                "visual_score": 95.0,
                "appearance_score": 94.0,
                "appearance_detail_score": 92.0,
                "appearance_face_detail_score": 97.0,
                "material_score": 90.0,
                "texture_resolution_score": 100.0,
                "base_color_max_edge": 4096,
                "head_region_faces": 20000,
                "head_region_vertices": 11000,
                "head_region_face_fraction": 0.09,
                "global_median_edge_normalized": 0.0013,
                "head_region_median_edge_normalized": 0.0011,
                "head_region_density_ratio": 1.1818,
                "pbr_channels": ["baseColor", "normal", "roughness"],
            }
            parse_pipeline_line(
                job,
                "HAYUYA_JUDGE_METRICS " + json.dumps(metrics,separators=(",",":")),
            )
            item = job.candidates["trellis2"]
            self.assertEqual(item.face_detail_score, 97.0)
            self.assertEqual(item.base_color_max_edge, 4096)
            self.assertEqual(item.head_region_faces, 20000)
            self.assertAlmostEqual(item.head_region_density_ratio, 1.1818)
            self.assertEqual(job.events[-1]["kind"], "judge_metrics")
            self.assertEqual(job.events[-1]["candidate"]["face_detail_score"], 97.0)

    def test_ranking_hydration_keeps_face_texture_and_head_geometry_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate = root / "candidate.glb"
            candidate.write_bytes(b"glTF" + b"x" * 32)
            job = self.make_job(root)
            parse_pipeline_line(
                job,
                f"HAYUYA_CANDIDATE_READY trellis2 {candidate} source=front.png",
            )

            hydrate_candidate_ranking(job, [{
                "backend": "trellis2",
                "score": 93.5,
                "production_score": 88.0,
                "visual_score": 94.0,
                "appearance_score": 91.0,
                "appearance_detail_score": 90.0,
                "appearance_face_detail_score": 96.0,
                "material_score": 87.0,
                "texture_resolution_score": 100.0,
                "base_color_max_edge": 4096,
                "head_region_faces": 18240,
                "head_region_vertices": 10420,
                "head_region_face_fraction": 0.082,
                "global_median_edge_normalized": 0.00140,
                "head_region_median_edge_normalized": 0.00123,
                "head_region_density_ratio": 1.1382,
                "pbr_channels": ["baseColor", "normal", "roughness"],
            }])

            item = job.candidates["trellis2"]
            self.assertEqual(item.face_detail_score, 96.0)
            self.assertEqual(item.texture_resolution_score, 100.0)
            self.assertEqual(item.base_color_max_edge, 4096)
            self.assertEqual(item.head_region_faces, 18240)
            self.assertAlmostEqual(item.head_region_median_edge_normalized, 0.00123)
            self.assertAlmostEqual(item.head_region_density_ratio, 1.1382)
            self.assertIn("normal", item.pbr_channels or [])

    def test_pipeline_stage_events_are_real_stage_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            job = self.make_job(Path(tmp))
            lines = [
                ("HAYUYA_VIEWFORGE_READY backend=wonder3d synthetic_views=5", "viewforge"),
                ("HAYUYA_REFINEMENT_READY source=x preferred=y improvement=2", "refinement"),
                ("HAYUYA_MESH_DOCTOR_CLEAN defect_score=0", "mesh_doctor"),
                ("HAYUYA_RETOPO_READY style=pure_quad quad_fraction=1 obj=x", "retopo"),
                ("HAYUYA_GAMEPREP_READY lods=4 collision=True turntable=8", "gameprep"),
                ("HAYUYA_PORTABLE_PACK_READY tiers=4 complete_lods=True manifest=x", "portable"),
                ("HAYUYA_QA_READY production_ready=True rig_ready=False report=x", "qa"),
            ]
            last_progress = -1
            for line, expected in lines:
                parse_pipeline_line(job, line)
                self.assertEqual(job.stage, expected)
                self.assertGreater(job.progress, last_progress)
                last_progress = job.progress

    def test_multipart_accepts_many_images_and_fields(self):
        boundary = "----hayuya-test"
        parts = []
        def field(name: str, value: str):
            return (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                f"{value}\r\n"
            ).encode()
        def file(name: str, filename: str, payload: bytes):
            return (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
                f"Content-Type: image/png\r\n\r\n"
            ).encode() + payload + b"\r\n"

        parts.append(field("profile", "ultra"))
        parts.append(field("mode", "character"))
        parts.append(file("images", "front.png", b"PNG-A"))
        parts.append(file("images", "back.png", b"PNG-B"))
        parts.append(file("face_images", "IMG_1234.jpg", b"FACE-C"))
        body = b"".join(parts) + f"--{boundary}--\r\n".encode()

        fields, files = parse_multipart(
            body,
            f"multipart/form-data; boundary={boundary}",
        )
        self.assertEqual(fields["profile"], "ultra")
        self.assertEqual(fields["mode"], "character")
        self.assertEqual(len(files), 3)
        self.assertEqual(files[0][1], "front.png")
        self.assertEqual(files[1][2], b"PNG-B")
        self.assertEqual(files[2][0], "face_images")
        self.assertEqual(files[2][1], "IMG_1234.jpg")
        self.assertEqual(files[2][2], b"FACE-C")


if __name__ == "__main__":
    unittest.main()
