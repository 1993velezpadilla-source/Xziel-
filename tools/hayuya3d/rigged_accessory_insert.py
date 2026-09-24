#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import struct
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class RiggedAccessoryInsertResult:
    base_mesh: str
    donor_mesh: str
    output_glb: str
    attempted: bool
    ready: bool
    donor_component_id: int | None
    spatial_label: str | None
    inserted_vertices: int
    inserted_faces: int
    transferred_weight_vertices: int
    weight_source_max_distance_ratio: float | None
    weight_source_mean_distance_ratio: float | None
    morph_targets_transferred: int
    morph_semantics_transferred: list[str]
    rig_ready: bool
    skin_weights_ready: bool
    morph_ready: bool
    morph_deformation_ready: bool | None
    animation_ready: bool | None
    deformation_ready: bool | None
    attachment_ready: bool
    component_crossing_ready: bool
    self_intersection_ready: bool
    bbox_drift_fraction: float | None
    warnings: list[str]
    errors: list[str]
    method: str = "hayuya-rigged-accessory-insert-v1"


def _deps():
    import numpy as np
    from scipy.spatial import cKDTree
    return np, cKDTree


def _fail(
    base_mesh: Path,
    donor_mesh: Path,
    output_glb: Path,
    message: str,
    *,
    warnings: list[str] | None = None,
) -> RiggedAccessoryInsertResult:
    return RiggedAccessoryInsertResult(
        base_mesh=str(base_mesh),
        donor_mesh=str(donor_mesh),
        output_glb=str(output_glb),
        attempted=True,
        ready=False,
        donor_component_id=None,
        spatial_label=None,
        inserted_vertices=0,
        inserted_faces=0,
        transferred_weight_vertices=0,
        weight_source_max_distance_ratio=None,
        weight_source_mean_distance_ratio=None,
        morph_targets_transferred=0,
        morph_semantics_transferred=[],
        rig_ready=False,
        skin_weights_ready=False,
        morph_ready=False,
        morph_deformation_ready=None,
        animation_ready=None,
        deformation_ready=None,
        attachment_ready=False,
        component_crossing_ready=False,
        self_intersection_ready=False,
        bbox_drift_fraction=None,
        warnings=list(warnings or []),
        errors=[message],
    )


def _bbox(vertices):
    np, _ = _deps()
    vv = np.asarray(vertices, dtype=np.float64)
    lo = np.min(vv, axis=0)
    hi = np.max(vv, axis=0)
    return lo, hi, (lo + hi) * 0.5, hi - lo


def _base_primitive(path: Path):
    np, _ = _deps()
    from gltf_position_patch import (
        _doc_and_bin,
        mesh_nodes_identity_for_accessors,
    )
    from skin_weight_qa import _read_accessor

    doc, binary, _ = _doc_and_bin(path)
    meshes = doc.get("meshes") or []
    nodes = doc.get("nodes") or []

    rows = []
    for node_index, node in enumerate(nodes):
        mesh_index = node.get("mesh")
        skin_index = node.get("skin")
        if not isinstance(mesh_index, int) or not isinstance(skin_index, int):
            continue
        if not (0 <= mesh_index < len(meshes)):
            continue
        for primitive_index, primitive in enumerate(
            meshes[mesh_index].get("primitives") or []
        ):
            attrs = primitive.get("attributes") or {}
            if (
                isinstance(attrs.get("POSITION"), int)
                and isinstance(attrs.get("JOINTS_0"), int)
                and isinstance(attrs.get("WEIGHTS_0"), int)
                and isinstance(primitive.get("indices"), int)
            ):
                rows.append((
                    node_index,
                    mesh_index,
                    primitive_index,
                    skin_index,
                    primitive,
                ))

    if len(rows) != 1:
        raise RuntimeError(
            "new-vertex accessory insertion currently requires exactly one "
            f"indexed skinned primitive; found {len(rows)}"
        )

    node_index, mesh_index, primitive_index, skin_index, primitive = rows[0]
    attrs = primitive.get("attributes") or {}
    if any(
        key.startswith("JOINTS_") and key != "JOINTS_0"
        for key in attrs
    ) or any(
        key.startswith("WEIGHTS_") and key != "WEIGHTS_0"
        for key in attrs
    ):
        raise RuntimeError(
            "new-vertex insertion v1 supports one JOINTS_0/WEIGHTS_0 set only"
        )

    position_accessor = int(attrs["POSITION"])
    if not mesh_nodes_identity_for_accessors(doc, [position_accessor]):
        raise RuntimeError(
            "skinned mesh node transform is not identity; object-space "
            "new-vertex insertion is unsafe"
        )

    positions = np.asarray(
        _read_accessor(doc, binary, position_accessor),
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
    if positions.ndim != 2 or positions.shape[1] != 3:
        raise RuntimeError("base POSITION accessor is not VEC3")
    if joints.shape != (len(positions), 4):
        raise RuntimeError("base JOINTS_0 accessor is not VEC4")
    if weights.shape != (len(positions), 4):
        raise RuntimeError("base WEIGHTS_0 accessor is not VEC4")

    accessors = doc.get("accessors") or []
    joint_meta = accessors[int(attrs["JOINTS_0"])]
    weight_meta = accessors[int(attrs["WEIGHTS_0"])]
    joint_component = int(joint_meta.get("componentType") or 0)
    weight_component = int(weight_meta.get("componentType") or 0)
    if joint_component not in {5121, 5123}:
        raise RuntimeError(
            "new-vertex insertion v1 requires unsigned byte/short JOINTS_0"
        )
    if weight_component != 5126 or bool(weight_meta.get("normalized")):
        raise RuntimeError(
            "new-vertex insertion v1 requires FLOAT WEIGHTS_0"
        )

    return {
        "doc": doc,
        "binary": binary,
        "node_index": node_index,
        "mesh_index": mesh_index,
        "primitive_index": primitive_index,
        "skin_index": skin_index,
        "primitive": primitive,
        "positions": positions,
        "joints": joints,
        "weights": weights,
        "joint_component": joint_component,
    }


def _donor_accessory(path: Path, *, mode: str, up_axis: str):
    np, _ = _deps()
    from accessory_match import inspect_accessories
    from part_map import _component_ids, _load_mesh

    candidates = inspect_accessories(
        path,
        mode=mode,
        up_axis=up_axis,
    )
    if len(candidates) != 1:
        raise RuntimeError(
            "new-vertex insertion requires exactly one unambiguous donor "
            f"accessory candidate; found {len(candidates)}"
        )
    selected = candidates[0]
    if float(selected.attachment_distance_ratio) > 0.18:
        raise RuntimeError(
            "donor accessory is too detached from its source body for "
            "automatic insertion"
        )

    mesh = _load_mesh(path)
    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    faces = np.asarray(mesh.faces, dtype=np.int64)
    component_ids = _component_ids(faces)
    chosen_faces = faces[
        component_ids == int(selected.component_id)
    ]
    if not len(chosen_faces):
        raise RuntimeError("donor accessory component has no faces")
    used = np.unique(chosen_faces.reshape(-1))
    remap = {int(old): new for new, old in enumerate(used.tolist())}
    local_faces = np.asarray([
        [remap[int(x)] for x in tri]
        for tri in chosen_faces
    ], dtype=np.int64)
    local_vertices = vertices[used]
    if len(local_vertices) < 3 or len(local_faces) < 1:
        raise RuntimeError("donor accessory component is too sparse")

    return selected, mesh, local_vertices, local_faces


def _append_bytes(blob: bytearray, payload: bytes) -> tuple[int, int]:
    while len(blob) % 4:
        blob.append(0)
    offset = len(blob)
    blob.extend(payload)
    return offset, len(payload)


def _append_accessor(
    doc: dict,
    blob: bytearray,
    payload: bytes,
    *,
    component_type: int,
    count: int,
    accessor_type: str,
    minimum=None,
    maximum=None,
    normalized: bool = False,
    target: int | None = None,
) -> int:
    offset, length = _append_bytes(blob, payload)
    view = {
        "buffer": 0,
        "byteOffset": offset,
        "byteLength": length,
    }
    if target is not None:
        view["target"] = int(target)
    views = doc.setdefault("bufferViews", [])
    view_index = len(views)
    views.append(view)

    accessor = {
        "bufferView": view_index,
        "componentType": int(component_type),
        "count": int(count),
        "type": str(accessor_type),
    }
    if normalized:
        accessor["normalized"] = True
    if minimum is not None:
        accessor["min"] = [float(x) for x in minimum]
    if maximum is not None:
        accessor["max"] = [float(x) for x in maximum]
    accessors = doc.setdefault("accessors", [])
    accessor_index = len(accessors)
    accessors.append(accessor)
    return accessor_index


def _pack_joints(values, component_type: int) -> bytes:
    np, _ = _deps()
    arr = np.asarray(values)
    if component_type == 5121:
        if np.any(arr < 0) or np.any(arr > 255):
            raise ValueError("JOINTS_0 exceeds UNSIGNED_BYTE range")
        return arr.astype(np.uint8).tobytes()
    if component_type == 5123:
        if np.any(arr < 0) or np.any(arr > 65535):
            raise ValueError("JOINTS_0 exceeds UNSIGNED_SHORT range")
        return arr.astype("<u2").tobytes()
    raise ValueError(f"unsupported JOINTS_0 component type {component_type}")


def _read_target_deltas(base, semantic: str):
    np, _ = _deps()
    from skin_weight_qa import _read_accessor

    doc = base["doc"]
    binary = base["binary"]
    primitive = base["primitive"]
    count = len(base["positions"])
    output = []
    for target in primitive.get("targets") or []:
        accessor = (target or {}).get(semantic)
        if accessor is None:
            output.append(np.zeros((count, 3), dtype=np.float64))
            continue
        rows = np.asarray(
            _read_accessor(doc, binary, int(accessor)),
            dtype=np.float64,
        )
        if rows.shape != (count, 3):
            raise RuntimeError(
                f"base morph {semantic} accessor shape {rows.shape} "
                f"!= {(count, 3)}"
            )
        if not np.isfinite(rows).all():
            raise RuntimeError(f"base morph {semantic} contains non-finite values")
        output.append(rows)
    return output


def rigged_accessory_insert_supported(
    base_mesh: Path,
    donor_mesh: Path,
    *,
    base_up_axis: str = "y",
    donor_up_axis: str | None = None,
) -> tuple[bool, str | None]:
    try:
        from gltf_audit import audit_glb
        from skin_weight_qa import audit_skin_weights

        rig = audit_glb(base_mesh)
        skin = audit_skin_weights(base_mesh)
        if not rig.rig_ready:
            return False, "base rig is not valid"
        if not skin.applicable or not skin.ready:
            return False, "base skin weights are not valid"
        _base_primitive(base_mesh)
        _donor_accessory(
            donor_mesh,
            mode="character",
            up_axis=donor_up_axis or base_up_axis,
        )
        return True, None
    except Exception as exc:
        return False, f"{type(exc).__name__}:{exc}"


def insert_rigged_accessory(
    base_mesh: Path,
    donor_mesh: Path,
    output_glb: Path,
    *,
    base_up_axis: str = "y",
    donor_up_axis: str | None = None,
    max_weight_source_distance_ratio: float = 0.12,
    max_bbox_drift_fraction: float = 0.18,
) -> RiggedAccessoryInsertResult:
    np, cKDTree = _deps()
    warnings: list[str] = []
    errors: list[str] = []
    donor_up_axis = donor_up_axis or base_up_axis

    try:
        from gltf_audit import audit_glb
        from skin_weight_qa import audit_skin_weights

        before_rig = audit_glb(base_mesh)
        before_skin = audit_skin_weights(base_mesh)
        if not before_rig.rig_ready:
            raise RuntimeError("base rig is not valid")
        if not before_skin.applicable or not before_skin.ready:
            raise RuntimeError("base skin weights are not valid")

        base = _base_primitive(base_mesh)
        selected, donor_mesh_flat, donor_vertices, donor_faces = _donor_accessory(
            donor_mesh,
            mode="character",
            up_axis=donor_up_axis,
        )

        base_vertices = base["positions"]
        _, _, base_center, base_extent = _bbox(base_vertices)
        donor_all = np.asarray(donor_mesh_flat.vertices, dtype=np.float64)
        _, _, donor_center, donor_extent = _bbox(donor_all)
        base_diag = max(float(np.linalg.norm(base_extent)), 1e-9)
        donor_diag = max(float(np.linalg.norm(donor_extent)), 1e-9)
        aligned = (
            (donor_vertices - donor_center)
            * (base_diag / donor_diag)
            + base_center
        )

        body_tree = cKDTree(base_vertices)
        source_distance, nearest = body_tree.query(
            aligned,
            k=1,
            workers=-1,
        )
        source_distance = np.asarray(source_distance, dtype=np.float64)
        nearest = np.asarray(nearest, dtype=np.int64)
        source_ratio = source_distance / base_diag
        max_source_ratio = (
            float(np.max(source_ratio)) if len(source_ratio) else 0.0
        )
        mean_source_ratio = (
            float(np.mean(source_ratio)) if len(source_ratio) else 0.0
        )
        if max_source_ratio > max_weight_source_distance_ratio:
            raise RuntimeError(
                "new accessory is too far from canonical body for safe "
                "nearest-surface weight transfer: "
                f"{max_source_ratio:.6f}>{max_weight_source_distance_ratio:.6f}"
            )

        transferred_joints = base["joints"][nearest]
        transferred_weights = base["weights"][nearest].copy()
        sums = np.sum(transferred_weights, axis=1)
        if np.any(~np.isfinite(transferred_weights)) or np.any(sums <= 1e-8):
            raise RuntimeError("nearest canonical skin weights are invalid")
        transferred_weights /= sums[:, None]

        doc = json.loads(json.dumps(base["doc"]))
        blob = bytearray(base["binary"])

        position_accessor = _append_accessor(
            doc,
            blob,
            np.asarray(aligned, dtype="<f4").tobytes(),
            component_type=5126,
            count=len(aligned),
            accessor_type="VEC3",
            minimum=np.min(aligned, axis=0),
            maximum=np.max(aligned, axis=0),
            target=34962,
        )
        joint_accessor = _append_accessor(
            doc,
            blob,
            _pack_joints(
                transferred_joints,
                int(base["joint_component"]),
            ),
            component_type=int(base["joint_component"]),
            count=len(aligned),
            accessor_type="VEC4",
        )
        weight_accessor = _append_accessor(
            doc,
            blob,
            np.asarray(transferred_weights, dtype="<f4").tobytes(),
            component_type=5126,
            count=len(aligned),
            accessor_type="VEC4",
        )

        max_index = int(np.max(donor_faces))
        if max_index <= 65535:
            index_component = 5123
            index_bytes = np.asarray(donor_faces, dtype="<u2").reshape(-1).tobytes()
        else:
            index_component = 5125
            index_bytes = np.asarray(donor_faces, dtype="<u4").reshape(-1).tobytes()
        index_accessor = _append_accessor(
            doc,
            blob,
            index_bytes,
            component_type=index_component,
            count=int(donor_faces.size),
            accessor_type="SCALAR",
            minimum=[0],
            maximum=[max_index],
            target=34963,
        )

        # Add computed normals. Keeping the new primitive independent from the
        # base UV/material topology prevents stale tangent-space evidence.
        import trimesh
        temp = trimesh.Trimesh(
            vertices=np.asarray(aligned, dtype=np.float64),
            faces=np.asarray(donor_faces, dtype=np.int64),
            process=False,
        )
        normals = np.asarray(temp.vertex_normals, dtype=np.float64)
        normal_accessor = _append_accessor(
            doc,
            blob,
            np.asarray(normals, dtype="<f4").tobytes(),
            component_type=5126,
            count=len(normals),
            accessor_type="VEC3",
            minimum=np.min(normals, axis=0),
            maximum=np.max(normals, axis=0),
            target=34962,
        )

        base_targets = base["primitive"].get("targets") or []
        new_targets = []
        semantics = sorted({
            semantic
            for target in base_targets
            for semantic in (target or {}).keys()
            if semantic in {"POSITION", "NORMAL", "TANGENT"}
        })
        transferred_semantics = set()
        for target_index in range(len(base_targets)):
            target_out = {}
            for semantic in semantics:
                deltas = _read_target_deltas(base, semantic)
                source = deltas[target_index][nearest]
                accessor = _append_accessor(
                    doc,
                    blob,
                    np.asarray(source, dtype="<f4").tobytes(),
                    component_type=5126,
                    count=len(source),
                    accessor_type="VEC3",
                    minimum=np.min(source, axis=0),
                    maximum=np.max(source, axis=0),
                )
                target_out[semantic] = accessor
                transferred_semantics.add(semantic)
            new_targets.append(target_out)

        new_primitive = {
            "attributes": {
                "POSITION": position_accessor,
                "NORMAL": normal_accessor,
                "JOINTS_0": joint_accessor,
                "WEIGHTS_0": weight_accessor,
            },
            "indices": index_accessor,
            "mode": 4,
        }
        if new_targets:
            new_primitive["targets"] = new_targets

        meshes = doc.get("meshes") or []
        mesh = meshes[int(base["mesh_index"])]
        mesh.setdefault("primitives", []).append(new_primitive)

        from glb_images import write_glb
        write_glb(output_glb, doc, bytes(blob))

        after_rig = audit_glb(output_glb)
        after_skin = audit_skin_weights(output_glb)
        rig_ready = bool(after_rig.rig_ready)
        skin_ready = bool(after_skin.applicable and after_skin.ready)
        morph_ready = bool(
            after_rig.morph_ready
            and after_rig.morph_target_count == before_rig.morph_target_count
        )
        if not rig_ready:
            errors.append("rig audit failed after new accessory insertion")
            errors.extend(after_rig.errors or [])
        if not skin_ready:
            errors.append("skin-weight QA failed after new accessory insertion")
            errors.extend(after_skin.errors or [])
        if not morph_ready:
            errors.append(
                "morph structure changed or became invalid after new accessory insertion"
            )

        morph_deformation_ready = None
        if before_rig.morph_target_count > 0:
            from morph_deformation_qa import audit_morph_deformation
            morph = audit_morph_deformation(output_glb)
            morph_deformation_ready = bool(morph.applicable and morph.ready)
            warnings.extend(morph.warnings or [])
            if not morph_deformation_ready:
                errors.append(
                    "morph deformation QA failed after new accessory insertion"
                )
                errors.extend(morph.errors or [])

        animation_ready = None
        deformation_ready = None
        if before_rig.animation_count > 0:
            from animation_qa import audit_animation
            from deformation_qa import audit_deformation

            animation = audit_animation(output_glb)
            deformation = audit_deformation(
                output_glb,
                max_frames_per_animation=6,
            )
            animation_ready = bool(animation.applicable and animation.ready)
            deformation_ready = bool(deformation.applicable and deformation.ready)
            warnings.extend(animation.warnings or [])
            warnings.extend(deformation.warnings or [])
            if not animation_ready:
                errors.append("animation QA failed after new accessory insertion")
                errors.extend(animation.errors or [])
            if not deformation_ready:
                errors.append("deformation QA failed after new accessory insertion")
                errors.extend(deformation.errors or [])

        from composite_attachment_qa import audit_composite_attachments
        attachment = audit_composite_attachments(
            output_glb,
            mode="character",
        )
        warnings.extend(attachment.warnings or [])
        attachment_ready = bool(attachment.applicable and attachment.ready)
        if not attachment_ready:
            errors.append(
                "new accessory does not remain coherently attached to canonical body"
            )
            errors.extend(attachment.errors or [])

        from component_crossing_qa import audit_component_crossings
        crossing = audit_component_crossings(output_glb)
        if not crossing.ready:
            errors.append(
                "new accessory insertion introduced major component crossings"
            )

        from self_intersection_qa import audit_self_intersections
        self_cross = audit_self_intersections(output_glb)
        if not self_cross.ready:
            errors.append(
                "new accessory insertion introduced self intersections"
            )

        from part_map import _load_mesh
        output_mesh = _load_mesh(output_glb)
        _, _, _, output_extent = _bbox(output_mesh.vertices)
        bbox_drift = float(np.max(
            np.abs(output_extent - base_extent)
            / np.maximum(base_extent, base_diag * 1e-6)
        ))
        if bbox_drift > max_bbox_drift_fraction:
            errors.append(
                "new accessory bbox drift "
                f"{bbox_drift:.6f}>{max_bbox_drift_fraction:.6f}"
            )

        return RiggedAccessoryInsertResult(
            base_mesh=str(base_mesh),
            donor_mesh=str(donor_mesh),
            output_glb=str(output_glb),
            attempted=True,
            ready=not errors,
            donor_component_id=int(selected.component_id),
            spatial_label=str(selected.spatial_label),
            inserted_vertices=int(len(aligned)),
            inserted_faces=int(len(donor_faces)),
            transferred_weight_vertices=int(len(aligned)),
            weight_source_max_distance_ratio=round(max_source_ratio, 8),
            weight_source_mean_distance_ratio=round(mean_source_ratio, 8),
            morph_targets_transferred=int(len(new_targets)),
            morph_semantics_transferred=sorted(transferred_semantics),
            rig_ready=rig_ready,
            skin_weights_ready=skin_ready,
            morph_ready=morph_ready,
            morph_deformation_ready=morph_deformation_ready,
            animation_ready=animation_ready,
            deformation_ready=deformation_ready,
            attachment_ready=attachment_ready,
            component_crossing_ready=bool(crossing.ready),
            self_intersection_ready=bool(self_cross.ready),
            bbox_drift_fraction=round(bbox_drift, 8),
            warnings=warnings,
            errors=errors,
        )
    except Exception as exc:
        return _fail(
            base_mesh,
            donor_mesh,
            output_glb,
            f"{type(exc).__name__}:{exc}",
            warnings=warnings,
        )


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description=(
            "Insert one new detached accessory primitive into a validated "
            "skinned HAYUYA character with nearest-surface skin-weight and "
            "morph-delta transfer."
        )
    )
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--donor", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-up-axis", choices=["x", "y", "z"], default="y")
    parser.add_argument("--donor-up-axis", choices=["x", "y", "z"])
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()

    result = insert_rigged_accessory(
        args.base,
        args.donor,
        args.output,
        base_up_axis=args.base_up_axis,
        donor_up_axis=args.donor_up_axis,
    )
    payload = json.dumps(asdict(result), indent=2)
    print(payload)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(payload + "\n", encoding="utf-8")
    return 0 if result.ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
