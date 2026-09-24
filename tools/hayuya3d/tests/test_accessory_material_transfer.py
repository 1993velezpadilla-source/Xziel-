from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image

from tools.hayuya3d.accessory_material_transfer import (
    accessory_material_transfer_supported,
    transfer_accessory_material,
)
from tools.hayuya3d.glb_images import write_glb
from tools.hayuya3d.rigged_accessory_insert import insert_rigged_accessory
from tools.hayuya3d.shading_basis_qa import audit_shading_basis
from tools.hayuya3d.uv_tangent_qa import audit_uv_tangents


def _align(blob: bytearray) -> int:
    while len(blob) % 4:
        blob.append(0)
    return len(blob)


def _append(blob: bytearray, payload: bytes) -> tuple[int, int]:
    offset = _align(blob)
    blob.extend(payload)
    return offset, len(payload)


def write_skinned_base_with_normals(path: Path) -> None:
    source = trimesh.creation.icosphere(subdivisions=2, radius=1.0)
    vertices = np.asarray(source.vertices, dtype=np.float32)
    normals = np.asarray(source.vertex_normals, dtype=np.float32)
    faces = np.asarray(source.faces, dtype=np.uint16)
    count = len(vertices)
    joints = np.zeros((count, 4), dtype=np.uint8)
    weights = np.zeros((count, 4), dtype=np.float32)
    upper = vertices[:, 1] >= 0.0
    joints[upper, 0] = 1
    weights[:, 0] = 1.0
    delta = np.zeros((count, 3), dtype=np.float32)
    delta[upper, 2] = 0.01

    blob = bytearray()
    payloads = [
        vertices.astype("<f4").tobytes(),
        normals.astype("<f4").tobytes(),
        joints.tobytes(),
        weights.astype("<f4").tobytes(),
        faces.astype("<u2").reshape(-1).tobytes(),
        delta.astype("<f4").tobytes(),
    ]
    chunks = [_append(blob, payload) for payload in payloads]
    views = [
        {"buffer": 0, "byteOffset": off, "byteLength": size}
        for off, size in chunks
    ]
    accessors = [
        {
            "bufferView": 0, "componentType": 5126,
            "count": count, "type": "VEC3",
            "min": vertices.min(axis=0).astype(float).tolist(),
            "max": vertices.max(axis=0).astype(float).tolist(),
        },
        {
            "bufferView": 1, "componentType": 5126,
            "count": count, "type": "VEC3",
            "min": normals.min(axis=0).astype(float).tolist(),
            "max": normals.max(axis=0).astype(float).tolist(),
        },
        {
            "bufferView": 2, "componentType": 5121,
            "count": count, "type": "VEC4",
        },
        {
            "bufferView": 3, "componentType": 5126,
            "count": count, "type": "VEC4",
        },
        {
            "bufferView": 4, "componentType": 5123,
            "count": int(faces.size), "type": "SCALAR",
        },
        {
            "bufferView": 5, "componentType": 5126,
            "count": count, "type": "VEC3",
            "min": delta.min(axis=0).astype(float).tolist(),
            "max": delta.max(axis=0).astype(float).tolist(),
        },
    ]
    doc = {
        "asset": {"version": "2.0"},
        "buffers": [{"byteLength": len(blob)}],
        "bufferViews": views,
        "accessors": accessors,
        "meshes": [{
            "primitives": [{
                "attributes": {
                    "POSITION": 0,
                    "NORMAL": 1,
                    "JOINTS_0": 2,
                    "WEIGHTS_0": 3,
                },
                "indices": 4,
                "targets": [{"POSITION": 5}],
            }],
            "weights": [0.0],
        }],
        "nodes": [{"mesh": 0, "skin": 0}, {}, {}],
        "skins": [{"joints": [1, 2]}],
        "scenes": [{"nodes": [0, 1, 2]}],
        "scene": 0,
    }
    write_glb(path, doc, bytes(blob))


def write_textured_donor(path: Path) -> None:
    body = trimesh.creation.icosphere(subdivisions=2, radius=1.0)
    body_v = np.asarray(body.vertices, dtype=np.float32)
    body_n = np.asarray(body.vertex_normals, dtype=np.float32)
    body_f = np.asarray(body.faces, dtype=np.uint16)

    center = np.asarray([0.0, 1.08, 0.0], dtype=np.float32)
    accessory_v = np.asarray([
        [-0.08, -0.07, -0.05],
        [ 0.08, -0.07, -0.05],
        [ 0.00,  0.09, -0.03],
        [ 0.00, -0.01,  0.08],
    ], dtype=np.float32) + center
    accessory_f = np.asarray([
        [0, 2, 1],
        [0, 1, 3],
        [1, 2, 3],
        [2, 0, 3],
    ], dtype=np.uint16)
    accessory_mesh = trimesh.Trimesh(
        vertices=accessory_v,
        faces=accessory_f,
        process=False,
    )
    accessory_n = np.asarray(
        accessory_mesh.vertex_normals,
        dtype=np.float32,
    )
    accessory_uv = np.asarray([
        [0.05, 0.05],
        [0.95, 0.05],
        [0.20, 0.95],
        [0.80, 0.85],
    ], dtype=np.float32)

    image = Image.new("RGBA", (16, 16), (190, 130, 40, 255))
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    png = stream.getvalue()

    blob = bytearray()
    payloads = [
        body_v.astype("<f4").tobytes(),
        body_n.astype("<f4").tobytes(),
        body_f.astype("<u2").reshape(-1).tobytes(),
        accessory_v.astype("<f4").tobytes(),
        accessory_n.astype("<f4").tobytes(),
        accessory_uv.astype("<f4").tobytes(),
        accessory_f.astype("<u2").reshape(-1).tobytes(),
        png,
    ]
    chunks = [_append(blob, payload) for payload in payloads]
    views = [
        {"buffer": 0, "byteOffset": off, "byteLength": size}
        for off, size in chunks
    ]
    accessors = [
        {
            "bufferView": 0, "componentType": 5126,
            "count": len(body_v), "type": "VEC3",
            "min": body_v.min(axis=0).astype(float).tolist(),
            "max": body_v.max(axis=0).astype(float).tolist(),
        },
        {
            "bufferView": 1, "componentType": 5126,
            "count": len(body_n), "type": "VEC3",
        },
        {
            "bufferView": 2, "componentType": 5123,
            "count": int(body_f.size), "type": "SCALAR",
        },
        {
            "bufferView": 3, "componentType": 5126,
            "count": len(accessory_v), "type": "VEC3",
            "min": accessory_v.min(axis=0).astype(float).tolist(),
            "max": accessory_v.max(axis=0).astype(float).tolist(),
        },
        {
            "bufferView": 4, "componentType": 5126,
            "count": len(accessory_n), "type": "VEC3",
        },
        {
            "bufferView": 5, "componentType": 5126,
            "count": len(accessory_uv), "type": "VEC2",
        },
        {
            "bufferView": 6, "componentType": 5123,
            "count": int(accessory_f.size), "type": "SCALAR",
        },
    ]
    doc = {
        "asset": {"version": "2.0"},
        "buffers": [{"byteLength": len(blob)}],
        "bufferViews": views,
        "accessors": accessors,
        "images": [{
            "bufferView": 7,
            "mimeType": "image/png",
        }],
        "textures": [{"source": 0}],
        "materials": [{
            "pbrMetallicRoughness": {
                "baseColorTexture": {"index": 0},
                "metallicFactor": 0.0,
                "roughnessFactor": 0.55,
            }
        }],
        "meshes": [{
            "primitives": [
                {
                    "attributes": {
                        "POSITION": 0,
                        "NORMAL": 1,
                    },
                    "indices": 2,
                },
                {
                    "attributes": {
                        "POSITION": 3,
                        "NORMAL": 4,
                        "TEXCOORD_0": 5,
                    },
                    "indices": 6,
                    "material": 0,
                },
            ]
        }],
        "nodes": [{"mesh": 0}],
        "scenes": [{"nodes": [0]}],
        "scene": 0,
    }
    write_glb(path, doc, bytes(blob))


def write_shared_atlas_cluster_donor(path: Path) -> None:
    body = trimesh.creation.icosphere(subdivisions=2, radius=1.0)
    body_v = np.asarray(body.vertices, dtype=np.float32)
    body_f = np.asarray(body.faces, dtype=np.int64)

    pieces = []
    for center in (
        (0.0, 1.06, 0.0),
        (0.0, 1.17, 0.0),
        (0.0, 1.28, 0.0),
    ):
        local = np.asarray([
            [-0.045, -0.040, -0.035],
            [ 0.045, -0.040, -0.035],
            [ 0.000,  0.050, -0.025],
            [ 0.000,  0.000,  0.050],
        ], dtype=np.float32)
        local += np.asarray(center, dtype=np.float32)
        faces = np.asarray([
            [0, 2, 1],
            [0, 1, 3],
            [1, 2, 3],
            [2, 0, 3],
        ], dtype=np.int64)
        pieces.append((local, faces))

    vertices = [body_v]
    faces = [body_f]
    cursor = len(body_v)
    for vv, ff in pieces:
        vertices.append(vv)
        faces.append(ff + cursor)
        cursor += len(vv)
    vertices = np.concatenate(vertices, axis=0).astype(np.float32)
    faces = np.concatenate(faces, axis=0).astype(np.uint16)

    combined = trimesh.Trimesh(
        vertices=vertices,
        faces=np.asarray(faces, dtype=np.int64),
        process=False,
    )
    normals = np.asarray(combined.vertex_normals, dtype=np.float32)

    uvs = np.zeros((len(vertices), 2), dtype=np.float32)
    cursor = len(body_v)
    piece_uv = np.asarray([
        [0.05, 0.05],
        [0.35, 0.08],
        [0.14, 0.38],
        [0.38, 0.34],
    ], dtype=np.float32)
    offsets = (
        (0.00, 0.00),
        (0.48, 0.00),
        (0.22, 0.52),
    )
    for offset in offsets:
        uv = piece_uv + np.asarray(offset, dtype=np.float32)
        uvs[cursor:cursor + 4] = uv
        cursor += 4

    image = Image.new("RGBA", (32, 32), (176, 120, 42, 255))
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    png = stream.getvalue()

    blob = bytearray()
    payloads = [
        vertices.astype("<f4").tobytes(),
        normals.astype("<f4").tobytes(),
        uvs.astype("<f4").tobytes(),
        faces.astype("<u2").reshape(-1).tobytes(),
        png,
    ]
    chunks = [_append(blob, payload) for payload in payloads]
    views = [
        {"buffer": 0, "byteOffset": off, "byteLength": size}
        for off, size in chunks
    ]
    accessors = [
        {
            "bufferView": 0, "componentType": 5126,
            "count": len(vertices), "type": "VEC3",
            "min": vertices.min(axis=0).astype(float).tolist(),
            "max": vertices.max(axis=0).astype(float).tolist(),
        },
        {
            "bufferView": 1, "componentType": 5126,
            "count": len(normals), "type": "VEC3",
        },
        {
            "bufferView": 2, "componentType": 5126,
            "count": len(uvs), "type": "VEC2",
        },
        {
            "bufferView": 3, "componentType": 5123,
            "count": int(faces.size), "type": "SCALAR",
        },
    ]
    doc = {
        "asset": {"version": "2.0"},
        "buffers": [{"byteLength": len(blob)}],
        "bufferViews": views,
        "accessors": accessors,
        "images": [{"bufferView": 4, "mimeType": "image/png"}],
        "textures": [{"source": 0}],
        "materials": [{
            "pbrMetallicRoughness": {
                "baseColorTexture": {"index": 0},
                "metallicFactor": 0.1,
                "roughnessFactor": 0.48,
            }
        }],
        "meshes": [{
            "primitives": [{
                "attributes": {
                    "POSITION": 0,
                    "NORMAL": 1,
                    "TEXCOORD_0": 2,
                },
                "indices": 3,
                "material": 0,
            }]
        }],
        "nodes": [{"mesh": 0}],
        "scenes": [{"nodes": [0]}],
        "scene": 0,
    }
    write_glb(path, doc, bytes(blob))


class AccessoryMaterialTransferTests(unittest.TestCase):
    def test_textured_donor_material_becomes_valid_inserted_primitive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / "base.glb"
            donor = root / "donor.glb"
            raw = root / "raw-insert.glb"
            final = root / "material-insert.glb"
            write_skinned_base_with_normals(base)
            write_textured_donor(donor)

            supported, blocker = accessory_material_transfer_supported(
                donor,
                up_axis="y",
            )
            self.assertTrue(supported, blocker)

            inserted = insert_rigged_accessory(
                base,
                donor,
                raw,
            )
            self.assertTrue(inserted.geometry_ready, inserted.errors)
            self.assertFalse(inserted.production_ready)

            transfer = transfer_accessory_material(
                donor,
                raw,
                final,
                donor_up_axis="y",
            )
            self.assertTrue(transfer.ready, transfer.errors)
            self.assertEqual(transfer.uv_vertices, inserted.inserted_vertices)
            self.assertEqual(transfer.copied_images, 1)
            self.assertEqual(transfer.copied_textures, 1)
            self.assertIn("baseColor", transfer.copied_channels)
            self.assertTrue(transfer.uv_tangent_ready)
            self.assertTrue(transfer.shading_basis_ready)
            self.assertFalse(transfer.tangent_generated)
            self.assertTrue(audit_uv_tangents(final).ready)
            self.assertTrue(audit_shading_basis(final).ready)

    def test_shared_atlas_multi_piece_cluster_transfers_as_one_material(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / "base.glb"
            donor = root / "cluster.glb"
            raw = root / "cluster-raw.glb"
            final = root / "cluster-final.glb"
            write_skinned_base_with_normals(base)
            write_shared_atlas_cluster_donor(donor)

            supported, blocker = accessory_material_transfer_supported(
                donor,
                up_axis="y",
            )
            self.assertTrue(supported, blocker)

            inserted = insert_rigged_accessory(
                base,
                donor,
                raw,
            )
            self.assertTrue(inserted.geometry_ready, inserted.errors)
            self.assertEqual(inserted.spatial_label, "cluster")
            self.assertFalse(inserted.production_ready)

            transfer = transfer_accessory_material(
                donor,
                raw,
                final,
                donor_up_axis="y",
            )
            self.assertTrue(transfer.ready, transfer.errors)
            self.assertEqual(len(transfer.donor_component_ids), 3)
            self.assertEqual(
                transfer.uv_vertices,
                inserted.inserted_vertices,
            )
            self.assertEqual(transfer.copied_images, 1)
            self.assertEqual(transfer.copied_textures, 1)
            self.assertIn("baseColor", transfer.copied_channels)
            self.assertTrue(transfer.uv_tangent_ready)
            self.assertTrue(transfer.shading_basis_ready)
            self.assertTrue(audit_uv_tangents(final).ready)
            self.assertTrue(audit_shading_basis(final).ready)

    def test_untextured_donor_material_support_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            donor = Path(tmp) / "donor.glb"
            body = trimesh.creation.icosphere(subdivisions=2, radius=1.0)
            charm = trimesh.creation.box(
                extents=[0.12, 0.12, 0.10]
            )
            charm.apply_translation([0.0, 1.08, 0.0])
            scene = trimesh.Scene()
            scene.add_geometry(body)
            scene.add_geometry(charm)
            donor.write_bytes(trimesh.exchange.gltf.export_glb(scene))

            supported, blocker = accessory_material_transfer_supported(donor)
            self.assertFalse(supported)
            self.assertIsNotNone(blocker)


if __name__ == "__main__":
    unittest.main()
