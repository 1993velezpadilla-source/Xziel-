from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import trimesh

from tools.hayuya3d.glb_images import write_glb
from tools.hayuya3d.gltf_audit import audit_glb
from tools.hayuya3d.morph_deformation_qa import audit_morph_deformation
from tools.hayuya3d.rigged_accessory_insert import insert_rigged_accessory
from tools.hayuya3d.skin_weight_qa import audit_skin_weights


def _align(blob: bytearray) -> int:
    while len(blob) % 4:
        blob.append(0)
    return len(blob)


def write_skinned_base(path: Path, *, morph: bool = True) -> None:
    source = trimesh.creation.icosphere(subdivisions=2, radius=1.0)
    vertices = np.asarray(source.vertices, dtype=np.float32)
    faces = np.asarray(source.faces, dtype=np.uint16)
    count = len(vertices)

    # Two-bone field: upper half follows joint 1, lower half joint 0.
    joints = np.zeros((count, 4), dtype=np.uint8)
    weights = np.zeros((count, 4), dtype=np.float32)
    upper = vertices[:, 1] >= 0.0
    joints[upper, 0] = 1
    weights[:, 0] = 1.0

    blob = bytearray()
    pos_offset = _align(blob)
    pos_bytes = vertices.astype("<f4").tobytes()
    blob.extend(pos_bytes)
    joint_offset = _align(blob)
    joint_bytes = joints.tobytes()
    blob.extend(joint_bytes)
    weight_offset = _align(blob)
    weight_bytes = weights.astype("<f4").tobytes()
    blob.extend(weight_bytes)
    index_offset = _align(blob)
    index_bytes = faces.astype("<u2").reshape(-1).tobytes()
    blob.extend(index_bytes)

    views = [
        {"buffer": 0, "byteOffset": pos_offset, "byteLength": len(pos_bytes)},
        {"buffer": 0, "byteOffset": joint_offset, "byteLength": len(joint_bytes)},
        {"buffer": 0, "byteOffset": weight_offset, "byteLength": len(weight_bytes)},
        {"buffer": 0, "byteOffset": index_offset, "byteLength": len(index_bytes)},
    ]
    accessors = [
        {
            "bufferView": 0,
            "componentType": 5126,
            "count": count,
            "type": "VEC3",
            "min": vertices.min(axis=0).astype(float).tolist(),
            "max": vertices.max(axis=0).astype(float).tolist(),
        },
        {
            "bufferView": 1,
            "componentType": 5121,
            "count": count,
            "type": "VEC4",
        },
        {
            "bufferView": 2,
            "componentType": 5126,
            "count": count,
            "type": "VEC4",
        },
        {
            "bufferView": 3,
            "componentType": 5123,
            "count": int(faces.size),
            "type": "SCALAR",
        },
    ]
    primitive = {
        "attributes": {
            "POSITION": 0,
            "JOINTS_0": 1,
            "WEIGHTS_0": 2,
        },
        "indices": 3,
    }
    mesh = {"primitives": [primitive]}

    if morph:
        delta = np.zeros((count, 3), dtype=np.float32)
        # Upper-body breathing/shape target. New accessory vertices should
        # inherit nearby canonical deltas instead of receiving invented zeros.
        delta[upper, 2] = 0.015
        morph_offset = _align(blob)
        morph_bytes = delta.astype("<f4").tobytes()
        blob.extend(morph_bytes)
        views.append({
            "buffer": 0,
            "byteOffset": morph_offset,
            "byteLength": len(morph_bytes),
        })
        accessors.append({
            "bufferView": len(views) - 1,
            "componentType": 5126,
            "count": count,
            "type": "VEC3",
            "min": delta.min(axis=0).astype(float).tolist(),
            "max": delta.max(axis=0).astype(float).tolist(),
        })
        primitive["targets"] = [{"POSITION": len(accessors) - 1}]
        mesh["weights"] = [0.0]

    doc = {
        "asset": {"version": "2.0"},
        "buffers": [{"byteLength": len(blob)}],
        "bufferViews": views,
        "accessors": accessors,
        "meshes": [mesh],
        "nodes": [
            {"mesh": 0, "skin": 0},
            {},
            {},
        ],
        "skins": [{"joints": [1, 2]}],
        "scenes": [{"nodes": [0, 1, 2]}],
        "scene": 0,
    }
    write_glb(path, doc, bytes(blob))


def write_donor(path: Path, *, ambiguous: bool = False) -> None:
    body = trimesh.creation.icosphere(subdivisions=2, radius=1.0)
    charm = trimesh.creation.box(extents=[0.16, 0.18, 0.10])
    charm.apply_translation([0.0, 1.10, 0.0])
    scene = trimesh.Scene()
    scene.add_geometry(body, node_name="body")
    scene.add_geometry(charm, node_name="charm")
    if ambiguous:
        second = trimesh.creation.box(extents=[0.14, 0.16, 0.10])
        second.apply_translation([0.25, 1.08, 0.0])
        scene.add_geometry(second, node_name="second_charm")
    path.write_bytes(trimesh.exchange.gltf.export_glb(scene))


class RiggedAccessoryInsertTests(unittest.TestCase):
    def test_new_accessory_gets_skin_weights_and_morph_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / "base.glb"
            donor = root / "donor.glb"
            output = root / "inserted.glb"
            write_skinned_base(base, morph=True)
            write_donor(donor)

            before = audit_glb(base)
            self.assertTrue(before.rig_ready)
            self.assertEqual(before.morph_target_count, 1)

            result = insert_rigged_accessory(
                base,
                donor,
                output,
            )

            self.assertTrue(result.ready, result.errors)
            self.assertTrue(output.is_file())
            self.assertGreater(result.inserted_vertices, 0)
            self.assertGreater(result.inserted_faces, 0)
            self.assertEqual(
                result.transferred_weight_vertices,
                result.inserted_vertices,
            )
            self.assertTrue(result.rig_ready)
            self.assertTrue(result.skin_weights_ready)
            self.assertTrue(result.morph_ready)
            self.assertTrue(result.morph_deformation_ready)
            self.assertEqual(result.morph_targets_transferred, 1)
            self.assertIn("POSITION", result.morph_semantics_transferred)
            self.assertTrue(result.attachment_ready)
            self.assertTrue(result.component_crossing_ready)
            self.assertTrue(result.self_intersection_ready)

            after = audit_glb(output)
            self.assertTrue(after.rig_ready, after.errors)
            self.assertTrue(after.morph_ready, after.errors)
            self.assertEqual(after.morph_target_count, 1)
            self.assertEqual(after.morph_primitive_count, 2)
            self.assertTrue(audit_skin_weights(output).ready)
            self.assertTrue(audit_morph_deformation(output).ready)

    def test_ambiguous_multiple_donor_accessories_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / "base.glb"
            donor = root / "ambiguous.glb"
            output = root / "blocked.glb"
            write_skinned_base(base, morph=True)
            write_donor(donor, ambiguous=True)

            result = insert_rigged_accessory(
                base,
                donor,
                output,
            )
            self.assertFalse(result.ready)
            self.assertFalse(output.exists())
            self.assertTrue(
                any(
                    "exactly one unambiguous donor accessory" in error
                    for error in result.errors
                ),
                result.errors,
            )


if __name__ == "__main__":
    unittest.main()
