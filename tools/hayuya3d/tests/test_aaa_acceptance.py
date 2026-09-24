from __future__ import annotations

import unittest

from tools.hayuya3d.aaa_acceptance import evaluate_aaa_acceptance


def base_manifest():
    return {
        "status":"success",
        "mode":"character",
        "profile":"monster",
        "champion":{"backend":"composite_material_b"},
        "gameprep":{"lods":[{"name":"LOD0"},{"name":"LOD1"},{"name":"LOD2"},{"name":"LOD3"}]},
        "portable_pack":{
            "complete_lod_chain":True,
            "tiers":[{"name":"flagship"},{"name":"high"},{"name":"balanced"},{"name":"compatibility"}],
        },
        "composite_champion":{
            "composite_required":True,
            "deferred_transfers":[],
        },
        "composite_execution":{"ready":True},
    }


def base_qa():
    return {
        "mode":"character",
        "profile":"monster",
        "production_ready":True,
        "geometry":{
            "ready":True,
            "head_density_score":99.0,
            "head_texel_density_score":98.0,
            "head_texture_detail_score":90.0,
        },
        "structure":{
            "valid":True,
            "finite_vertices":True,
            "duplicate_faces":0,
            "degenerate_faces":0,
            "nonmanifold_edges":0,
            "winding_consistent":True,
        },
        "source_coverage":{"expected":2,"judged":2},
        "turntable_qa":{"ready":True},
        "material":{
            "ready":True,
            "texture_resolution_ready":True,
            "rebake_ready":True,
            "channels":["baseColor","roughness","normal","occlusion"],
            "base_color_min_edge":4096,
            "target_texture_size":4096,
        },
        "face_evidence":{
            "required":True,
            "ready":True,
            "quality_evidence_ready":True,
            "evaluated":2,
            "expected":2,
            "min_score":90.0,
        },
        "rig":{
            "rig_ready":True,
            "animation_ready":True,
            "skins":1,
            "joint_count":65,
            "animations":3,
        },
        "warnings":[],
    }


class AAAAcceptanceTests(unittest.TestCase):
    def test_complete_high_end_character_passes_internal_contract(self):
        report=evaluate_aaa_acceptance(base_manifest(),base_qa())
        self.assertTrue(report.ready,report.blockers)
        self.assertEqual(report.passed_required,report.total_required)

    def test_missing_face_texel_evidence_fails_closed(self):
        qa=base_qa()
        qa["geometry"]["head_texel_density_score"]=None
        qa["face_evidence"]["quality_evidence_ready"]=False
        report=evaluate_aaa_acceptance(base_manifest(),qa)
        self.assertFalse(report.ready)
        self.assertTrue(
            any("face-quality evidence" in x for x in report.blockers),
            report.blockers,
        )
        self.assertTrue(
            any("head_texel_density_score" in x for x in report.blockers),
            report.blockers,
        )

    def test_unresolved_better_regional_donor_blocks_aaa_claim(self):
        manifest=base_manifest()
        manifest["composite_champion"]["deferred_transfers"]=["face_identity"]
        report=evaluate_aaa_acceptance(manifest,base_qa())
        self.assertFalse(report.ready)
        self.assertTrue(
            any("Composite Champion" in x for x in report.blockers),
            report.blockers,
        )

    def test_non_composite_base_can_pass_when_no_region_is_better(self):
        manifest=base_manifest()
        manifest["champion"]={"backend":"trellis2"}
        manifest["composite_champion"]={
            "composite_required":False,
            "deferred_transfers":[],
        }
        manifest["composite_execution"]=None
        report=evaluate_aaa_acceptance(manifest,base_qa())
        self.assertTrue(report.ready,report.blockers)

    def test_high_end_missing_normal_map_fails(self):
        qa=base_qa()
        qa["material"]["channels"]=["baseColor","roughness"]
        report=evaluate_aaa_acceptance(base_manifest(),qa)
        self.assertFalse(report.ready)
        self.assertTrue(
            any("PBR" in x for x in report.blockers),
            report.blockers,
        )

    def test_character_without_animation_fails(self):
        qa=base_qa()
        qa["rig"]["animation_ready"]=False
        report=evaluate_aaa_acceptance(base_manifest(),qa)
        self.assertFalse(report.ready)
        self.assertTrue(
            any("animation" in x.lower() for x in report.blockers),
            report.blockers,
        )


if __name__=="__main__":
    unittest.main()
