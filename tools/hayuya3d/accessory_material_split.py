#!/usr/bin/env python3
from __future__ import annotations

import copy
import math
from pathlib import Path


def _deps():
    import numpy as np
    from scipy.spatial import cKDTree
    return np, cKDTree


def _mapped_cluster_components(path: Path, *, up_axis: str):
    np, _ = _deps()
    from accessory_match import inspect_accessories
    from accessory_cluster import inspect_accessory_clusters
    from accessory_material_transfer import _bbox, _world_components

    candidates = inspect_accessories(
        path,
        mode="character",
        up_axis=up_axis,
    )
    if len(candidates) < 2:
        raise RuntimeError(
            "split material transfer requires a multi-piece donor cluster"
        )
    cluster = inspect_accessory_clusters(
        path,
        mode="character",
        up_axis=up_axis,
    )
    if not cluster.ready or not cluster.selected_component_ids:
        detail = ";".join(cluster.errors or [])
        raise RuntimeError(
            "split material transfer requires one proven anchored logical "
            "accessory cluster"
            + (f": {detail}" if detail else "")
        )
    by_id = {int(item.component_id): item for item in candidates}
    selected_ids = [int(x) for x in cluster.selected_component_ids]
    if set(selected_ids) != set(by_id):
        raise RuntimeError(
            "cluster proof did not account for every donor accessory candidate"
        )
    selected = [by_id[x] for x in selected_ids]

    doc, binary, components = _world_components(path)
    all_points = np.concatenate([
        item["positions_world"][item["used_vertex_ids"]]
        for item in components
    ], axis=0)
    lo, _, _, extent = _bbox(all_points)
    diagonal = max(float(np.linalg.norm(extent)), 1e-9)
    safe_extent = np.maximum(extent, diagonal * 1e-6)

    mapped = []
    used_rows = set()
    for wanted in selected:
        wanted_centroid = np.asarray(
            wanted.normalized_centroid, dtype=np.float64
        )
        wanted_extent = np.asarray(
            wanted.normalized_extent, dtype=np.float64
        )
        scored = []
        for item in components:
            if int(item["face_count"]) != int(wanted.face_count):
                continue
            key = (
                int(item["node_index"]),
                int(item["mesh_index"]),
                int(item["primitive_index"]),
                int(item["component_id"]),
            )
            if key in used_rows:
                continue
            centroid = (
                np.asarray(item["centroid"], dtype=np.float64) - lo
            ) / safe_extent
            comp_extent = (
                np.asarray(item["extent"], dtype=np.float64)
                / safe_extent
            )
            score = float(
                np.linalg.norm(centroid - wanted_centroid)
                + np.linalg.norm(comp_extent - wanted_extent)
            )
            scored.append((score, key, item))
        if not scored:
            raise RuntimeError(
                f"could not map donor component {wanted.component_id} "
                "back to its source primitive"
            )
        scored.sort(key=lambda row: row[0])
        best_score, best_key, best = scored[0]
        second = scored[1][0] if len(scored) > 1 else None
        if best_score > 0.02:
            raise RuntimeError(
                "donor component mapping drift too large: "
                f"{best_score:.6f}>0.020000"
            )
        if second is not None and second - best_score < 0.01:
            raise RuntimeError(
                "donor component to primitive mapping is ambiguous"
            )
        used_rows.add(best_key)
        row = dict(best)
        row["candidate"] = wanted
        mapped.append(row)

    locations = {
        (
            int(item["node_index"]),
            int(item["mesh_index"]),
            int(item["primitive_index"]),
        )
        for item in mapped
    }
    if len(locations) < 2:
        raise RuntimeError(
            "cluster already fits the shared-primitive/atlas material path"
        )
    return doc, binary, mapped


def _validate_material_component(doc, binary, item):
    from accessory_material_transfer import (
        _copy_material_bundle,
        _material_basecolor_texture,
    )

    primitive = item["primitive"]
    attrs = primitive.get("attributes") or {}
    uv_index = attrs.get("TEXCOORD_0")
    material_index = primitive.get("material")
    if not isinstance(uv_index, int):
        raise RuntimeError(
            "cluster piece source primitive has no TEXCOORD_0"
        )
    if not isinstance(material_index, int):
        raise RuntimeError(
            "cluster piece source primitive has no explicit material"
        )
    materials = doc.get("materials") or []
    if not (0 <= material_index < len(materials)):
        raise RuntimeError("cluster piece material index is invalid")
    material = materials[material_index]
    if not _material_basecolor_texture(material):
        raise RuntimeError(
            "cluster piece material has no baseColor texture"
        )
    scratch_doc = {"bufferViews": []}
    scratch_blob = bytearray()
    _copy_material_bundle(
        doc,
        binary,
        scratch_doc,
        scratch_blob,
        material_index,
    )
    return uv_index, material_index


def split_accessory_material_supported(
    donor_mesh: Path,
    *,
    up_axis: str = "y",
) -> tuple[bool, str | None]:
    try:
        doc, binary, mapped = _mapped_cluster_components(
            donor_mesh,
            up_axis=up_axis,
        )
        for item in mapped:
            _validate_material_component(doc, binary, item)
        return True, None
    except Exception as exc:
        return False, f"{type(exc).__name__}:{exc}"


def _component_rows(positions, faces):
    np, _ = _deps()
    from part_map import _component_ids

    component_ids = _component_ids(faces)
    rows = []
    for component_id in np.unique(component_ids):
        comp_faces = faces[component_ids == int(component_id)]
        used = np.unique(comp_faces.reshape(-1))
        vv = positions[used]
        rows.append({
            "component_id": int(component_id),
            "faces": comp_faces,
            "used": used,
            "centroid": np.mean(vv, axis=0),
            "extent": np.max(vv, axis=0) - np.min(vv, axis=0),
            "face_count": int(len(comp_faces)),
        })
    return rows


def _map_inserted_to_donor(mapped, inserted_rows, inserted_positions):
    np, _ = _deps()

    donor_points = np.concatenate([
        item["positions_world"][item["used_vertex_ids"]]
        for item in mapped
    ], axis=0)
    inserted_points = np.concatenate([
        inserted_positions[item["used"]]
        for item in inserted_rows
    ], axis=0)
    donor_center = np.mean(donor_points, axis=0)
    inserted_center = np.mean(inserted_points, axis=0)
    donor_diag = max(float(np.linalg.norm(
        np.max(donor_points, axis=0) - np.min(donor_points, axis=0)
    )), 1e-9)
    inserted_diag = max(float(np.linalg.norm(
        np.max(inserted_points, axis=0) - np.min(inserted_points, axis=0)
    )), 1e-9)

    scored = []
    for donor_index, donor in enumerate(mapped):
        d_centroid = (
            np.asarray(donor["centroid"], dtype=np.float64) - donor_center
        ) / donor_diag
        d_extent = np.asarray(donor["extent"], dtype=np.float64) / donor_diag
        for inserted_index, inserted in enumerate(inserted_rows):
            if int(donor["face_count"]) != int(inserted["face_count"]):
                continue
            i_centroid = (
                np.asarray(inserted["centroid"], dtype=np.float64)
                - inserted_center
            ) / inserted_diag
            i_extent = (
                np.asarray(inserted["extent"], dtype=np.float64)
                / inserted_diag
            )
            score = float(
                np.linalg.norm(d_centroid - i_centroid)
                + np.linalg.norm(d_extent - i_extent)
            )
            scored.append((score, donor_index, inserted_index))

    matches = {}
    used_inserted = set()
    for donor_index in range(len(mapped)):
        options = sorted(
            row for row in scored
            if row[1] == donor_index and row[2] not in used_inserted
        )
        if not options:
            raise RuntimeError(
                f"no inserted component matches donor material piece {donor_index}"
            )
        best = options[0]
        second = options[1] if len(options) > 1 else None
        if best[0] > 0.03:
            raise RuntimeError(
                "inserted/donor component mapping drift too large: "
                f"{best[0]:.6f}>0.030000"
            )
        if second is not None and second[0] - best[0] < 0.01:
            raise RuntimeError(
                "inserted component material mapping is ambiguous"
            )
        matches[donor_index] = best[2]
        used_inserted.add(best[2])

    if len(matches) != len(mapped) or len(used_inserted) != len(inserted_rows):
        raise RuntimeError(
            "material split did not map every inserted/donor component exactly once"
        )
    return matches


def _vertex_correspondence(donor_points, inserted_points):
    np, cKDTree = _deps()
    donor_points = np.asarray(donor_points, dtype=np.float64)
    inserted_points = np.asarray(inserted_points, dtype=np.float64)
    if len(donor_points) != len(inserted_points):
        raise RuntimeError(
            "donor/inserted piece vertex counts differ"
        )
    d_center = np.mean(donor_points, axis=0)
    i_center = np.mean(inserted_points, axis=0)
    d_diag = max(float(np.linalg.norm(
        np.max(donor_points, axis=0) - np.min(donor_points, axis=0)
    )), 1e-9)
    i_diag = max(float(np.linalg.norm(
        np.max(inserted_points, axis=0) - np.min(inserted_points, axis=0)
    )), 1e-9)
    d_norm = (donor_points - d_center) / d_diag
    i_norm = (inserted_points - i_center) / i_diag
    tree = cKDTree(d_norm)
    distances, nearest = tree.query(i_norm, k=1, workers=1)
    distances = np.asarray(distances, dtype=np.float64)
    nearest = np.asarray(nearest, dtype=np.int64)
    if len(set(int(x) for x in nearest.tolist())) != len(nearest):
        raise RuntimeError(
            "donor UV vertex mapping is not one-to-one"
        )
    max_distance = float(np.max(distances)) if len(distances) else 0.0
    if max_distance > 1e-4:
        raise RuntimeError(
            "donor UV vertex correspondence drift too large: "
            f"{max_distance:.8f}>0.00010000"
        )
    return nearest


def _append_piece_primitive(
    doc,
    blob,
    *,
    source_primitive,
    source_doc,
    source_binary,
    donor_item,
    inserted_item,
    positions,
    normals,
    joints,
    weights,
    target_arrays,
    joint_component,
):
    np, _ = _deps()
    from accessory_material_transfer import (
        _copy_material_bundle,
        _generate_tangents,
    )
    from rigged_accessory_insert import (
        _append_accessor,
        _pack_joints,
    )
    from skin_weight_qa import _read_accessor

    used = np.asarray(inserted_item["used"], dtype=np.int64)
    source_used = np.asarray(donor_item["used_vertex_ids"], dtype=np.int64)
    donor_points = donor_item["positions_world"][source_used]
    inserted_points = positions[used]
    nearest = _vertex_correspondence(
        donor_points,
        inserted_points,
    )

    source_attrs = source_primitive.get("attributes") or {}
    uv_index = source_attrs.get("TEXCOORD_0")
    material_index = source_primitive.get("material")
    if not isinstance(uv_index, int) or not isinstance(material_index, int):
        raise RuntimeError(
            "split material source is missing UV or material binding"
        )
    donor_uv_all = np.asarray(
        _read_accessor(source_doc, source_binary, uv_index),
        dtype=np.float64,
    )
    donor_uv = donor_uv_all[source_used][nearest]
    if donor_uv.shape != (len(used), 2) or not np.isfinite(donor_uv).all():
        raise RuntimeError("split donor UV payload is invalid")

    remap = {int(old): new for new, old in enumerate(used.tolist())}
    local_faces = np.asarray([
        [remap[int(x)] for x in tri]
        for tri in inserted_item["faces"]
    ], dtype=np.int64)

    pos = positions[used]
    nrm = normals[used]
    jnt = joints[used]
    wgt = weights[used]

    position_accessor = _append_accessor(
        doc, blob, np.asarray(pos, dtype="<f4").tobytes(),
        component_type=5126, count=len(pos), accessor_type="VEC3",
        minimum=np.min(pos, axis=0), maximum=np.max(pos, axis=0),
        target=34962,
    )
    normal_accessor = _append_accessor(
        doc, blob, np.asarray(nrm, dtype="<f4").tobytes(),
        component_type=5126, count=len(nrm), accessor_type="VEC3",
        minimum=np.min(nrm, axis=0), maximum=np.max(nrm, axis=0),
        target=34962,
    )
    joint_accessor = _append_accessor(
        doc, blob, _pack_joints(jnt, int(joint_component)),
        component_type=int(joint_component), count=len(jnt), accessor_type="VEC4",
    )
    weight_accessor = _append_accessor(
        doc, blob, np.asarray(wgt, dtype="<f4").tobytes(),
        component_type=5126, count=len(wgt), accessor_type="VEC4",
    )
    uv_accessor = _append_accessor(
        doc, blob, np.asarray(donor_uv, dtype="<f4").tobytes(),
        component_type=5126, count=len(donor_uv), accessor_type="VEC2",
    )

    max_index = int(np.max(local_faces))
    if max_index <= 65535:
        index_component = 5123
        index_payload = np.asarray(local_faces, dtype="<u2").reshape(-1).tobytes()
    else:
        index_component = 5125
        index_payload = np.asarray(local_faces, dtype="<u4").reshape(-1).tobytes()
    index_accessor = _append_accessor(
        doc, blob, index_payload,
        component_type=index_component,
        count=int(local_faces.size),
        accessor_type="SCALAR",
        minimum=[0], maximum=[max_index], target=34963,
    )

    bundle = _copy_material_bundle(
        source_doc,
        source_binary,
        doc,
        blob,
        int(material_index),
    )

    attributes = {
        "POSITION": position_accessor,
        "NORMAL": normal_accessor,
        "JOINTS_0": joint_accessor,
        "WEIGHTS_0": weight_accessor,
        "TEXCOORD_0": uv_accessor,
    }
    tangent_generated = False
    if bundle["has_normal_map"]:
        tangents = _generate_tangents(
            pos, nrm, donor_uv, local_faces
        )
        tangent_accessor = _append_accessor(
            doc, blob, np.asarray(tangents, dtype="<f4").tobytes(),
            component_type=5126, count=len(tangents), accessor_type="VEC4",
        )
        attributes["TANGENT"] = tangent_accessor
        tangent_generated = True

    targets = []
    for target in target_arrays:
        target_out = {}
        for semantic, array in target.items():
            values = np.asarray(array, dtype=np.float64)[used]
            accessor = _append_accessor(
                doc, blob, np.asarray(values, dtype="<f4").tobytes(),
                component_type=5126, count=len(values), accessor_type="VEC3",
                minimum=np.min(values, axis=0),
                maximum=np.max(values, axis=0),
            )
            target_out[semantic] = accessor
        targets.append(target_out)

    primitive = {
        "attributes": attributes,
        "indices": index_accessor,
        "mode": 4,
        "material": int(bundle["material_index"]),
    }
    if targets:
        primitive["targets"] = targets

    return primitive, bundle, tangent_generated


def transfer_split_accessory_material(
    donor_mesh: Path,
    inserted_mesh: Path,
    output_glb: Path,
    *,
    donor_up_axis: str = "y",
):
    np, _ = _deps()
    from accessory_material_transfer import AccessoryMaterialTransferResult
    warnings = []
    errors = []
    try:
        donor_doc, donor_binary, mapped = _mapped_cluster_components(
            donor_mesh,
            up_axis=donor_up_axis,
        )
        for item in mapped:
            _validate_material_component(
                donor_doc, donor_binary, item
            )

        from glb_images import read_glb, write_glb
        from skin_weight_qa import _read_accessor

        doc, binary = read_glb(inserted_mesh)
        doc = copy.deepcopy(doc)
        blob = bytearray(binary)
        skinned_nodes = [
            node for node in doc.get("nodes") or []
            if isinstance(node.get("mesh"), int)
            and isinstance(node.get("skin"), int)
        ]
        if len(skinned_nodes) != 1:
            raise RuntimeError(
                "split material transfer requires exactly one skinned mesh node"
            )
        mesh_index = int(skinned_nodes[0]["mesh"])
        mesh = (doc.get("meshes") or [])[mesh_index]
        primitives = mesh.get("primitives") or []
        if len(primitives) < 2:
            raise RuntimeError(
                "inserted GLB has no combined accessory primitive to split"
            )
        inserted_primitive_index = len(primitives) - 1
        combined = primitives[inserted_primitive_index]
        attrs = combined.get("attributes") or {}
        required = ("POSITION", "NORMAL", "JOINTS_0", "WEIGHTS_0")
        if not all(isinstance(attrs.get(key), int) for key in required):
            raise RuntimeError(
                "combined accessory primitive lacks runtime attributes"
            )
        if not isinstance(combined.get("indices"), int):
            raise RuntimeError(
                "combined accessory primitive has no indices"
            )

        positions = np.asarray(
            _read_accessor(doc, binary, int(attrs["POSITION"])),
            dtype=np.float64,
        )
        normals = np.asarray(
            _read_accessor(doc, binary, int(attrs["NORMAL"])),
            dtype=np.float64,
        )
        joints = np.asarray(
            _read_accessor(doc, binary, int(attrs["JOINTS_0"])),
            dtype=np.int64,
        )
        weights = np.asarray(
            _read_accessor(doc, binary, int(attrs["WEIGHTS_0"])),
            dtype=np.float64,
        )
        raw_indices = np.asarray(
            _read_accessor(doc, binary, int(combined["indices"])),
            dtype=np.int64,
        ).reshape(-1)
        if len(raw_indices) % 3:
            raise RuntimeError(
                "combined accessory indices are not triangle-aligned"
            )
        faces = raw_indices.reshape((-1, 3))
        inserted_rows = _component_rows(
            positions, faces
        )
        if len(inserted_rows) != len(mapped):
            raise RuntimeError(
                "combined inserted component count does not match donor cluster: "
                f"{len(inserted_rows)}!={len(mapped)}"
            )
        matches = _map_inserted_to_donor(
            mapped,
            inserted_rows,
            positions,
        )

        target_arrays = []
        for target in combined.get("targets") or []:
            row = {}
            for semantic, accessor_index in (target or {}).items():
                if semantic not in {"POSITION", "NORMAL", "TANGENT"}:
                    continue
                row[semantic] = np.asarray(
                    _read_accessor(doc, binary, int(accessor_index)),
                    dtype=np.float64,
                )
            target_arrays.append(row)

        accessors = doc.get("accessors") or []
        joint_meta = accessors[int(attrs["JOINTS_0"])]
        joint_component = int(joint_meta.get("componentType") or 0)
        if joint_component not in {5121, 5123}:
            raise RuntimeError(
                "split material transfer supports UBYTE/USHORT JOINTS_0 only"
            )

        new_primitives = []
        copied_images = 0
        copied_textures = 0
        copied_samplers = 0
        channels = set()
        tangent_generated = False
        material_indices = []

        for donor_index, donor_item in enumerate(mapped):
            inserted_item = inserted_rows[matches[donor_index]]
            primitive, bundle, generated = _append_piece_primitive(
                doc,
                blob,
                source_primitive=donor_item["primitive"],
                source_doc=donor_doc,
                source_binary=donor_binary,
                donor_item=donor_item,
                inserted_item=inserted_item,
                positions=positions,
                normals=normals,
                joints=joints,
                weights=weights,
                target_arrays=target_arrays,
                joint_component=joint_component,
            )
            new_primitives.append(primitive)
            copied_images += int(bundle["images"])
            copied_textures += int(bundle["textures"])
            copied_samplers += int(bundle["samplers"])
            channels.update(bundle["channels"])
            tangent_generated = tangent_generated or generated
            material_indices.append(int(bundle["material_index"]))

        mesh["primitives"] = (
            primitives[:inserted_primitive_index]
            + new_primitives
        )
        write_glb(output_glb, doc, bytes(blob))

        from uv_tangent_qa import audit_uv_tangents
        from shading_basis_qa import audit_shading_basis
        uv = audit_uv_tangents(output_glb)
        shading = audit_shading_basis(output_glb)
        uv_ready = bool(uv.applicable and uv.ready)
        shading_ready = bool(shading.applicable and shading.ready)
        warnings.extend(uv.warnings or [])
        warnings.extend(shading.warnings or [])
        if not uv_ready:
            errors.append(
                "UV/tangent QA failed after split accessory material transfer"
            )
            errors.extend(uv.errors or [])
        if not shading_ready:
            errors.append(
                "shading-basis QA failed after split accessory material transfer"
            )
            errors.extend(shading.errors or [])

        from texture_gate import embedded_images
        if not embedded_images(output_glb):
            errors.append(
                "split material transfer produced no embedded image evidence"
            )

        component_ids = [
            int(item["candidate"].component_id)
            for item in mapped
        ]
        return AccessoryMaterialTransferResult(
            donor_mesh=str(donor_mesh),
            inserted_mesh=str(inserted_mesh),
            output_glb=str(output_glb),
            attempted=True,
            ready=not errors,
            donor_component_id=component_ids[0],
            donor_component_ids=component_ids,
            donor_mesh_index=int(mapped[0]["mesh_index"]),
            donor_primitive_index=int(mapped[0]["primitive_index"]),
            material_index=material_indices[0],
            inserted_primitive_index=int(inserted_primitive_index),
            uv_vertices=int(len(positions)),
            copied_images=int(copied_images),
            copied_textures=int(copied_textures),
            copied_samplers=int(copied_samplers),
            copied_channels=sorted(channels),
            tangent_generated=bool(tangent_generated),
            uv_tangent_ready=uv_ready,
            shading_basis_ready=shading_ready,
            warnings=warnings,
            errors=errors,
        )
    except Exception as exc:
        from accessory_material_transfer import AccessoryMaterialTransferResult
        return AccessoryMaterialTransferResult(
            donor_mesh=str(donor_mesh),
            inserted_mesh=str(inserted_mesh),
            output_glb=str(output_glb),
            attempted=True,
            ready=False,
            donor_component_id=None,
            donor_component_ids=[],
            donor_mesh_index=None,
            donor_primitive_index=None,
            material_index=None,
            inserted_primitive_index=None,
            uv_vertices=0,
            copied_images=0,
            copied_textures=0,
            copied_samplers=0,
            copied_channels=[],
            tangent_generated=False,
            uv_tangent_ready=False,
            shading_basis_ready=False,
            warnings=warnings,
            errors=[f"{type(exc).__name__}:{exc}"],
        )
