#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import struct
from dataclasses import asdict, dataclass
from pathlib import Path

JSON_CHUNK = 0x4E4F534A

def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())

def _load_glb_json(path: Path) -> dict:
    blob = path.read_bytes()
    if len(blob) < 20 or blob[:4] != b"glTF":
        raise ValueError("not a GLB")
    version, total = struct.unpack_from("<II", blob, 4)
    if version != 2 or total > len(blob):
        raise ValueError("invalid GLB header")
    offset = 12
    while offset + 8 <= total:
        length, chunk_type = struct.unpack_from("<II", blob, offset)
        offset += 8
        end = offset + length
        if end > total:
            raise ValueError("chunk exceeds GLB length")
        data = blob[offset:end]
        offset = end
        if chunk_type == JSON_CHUNK:
            return json.loads(data.rstrip(b"\x00 \t\r\n").decode("utf-8"))
    raise ValueError("GLB missing JSON chunk")

def _load_spec(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def _target_names(doc: dict) -> list[str]:
    names: list[str] = []
    for mesh in doc.get("meshes", []):
        extras = mesh.get("extras") or {}
        for name in extras.get("targetNames", []) or []:
            if isinstance(name, str):
                names.append(name)
    return names

def _matches(names: list[str], aliases: list[str]) -> bool:
    normalized = {_norm(n) for n in names}
    return any(_norm(a) in normalized for a in aliases)

def _pattern_hits(names: list[str], patterns: list[str]) -> list[str]:
    pats = [_norm(p) for p in patterns]
    hits = []
    for name in names:
        n = _norm(name)
        if any(p and p in n for p in pats):
            hits.append(name)
    return sorted(set(hits))

@dataclass
class RigReport:
    schema: int
    skeleton_type: str
    valid_glb: bool
    skins: int
    joints: int
    required_groups_found: int
    required_groups_total: int
    required_group_fraction: float
    missing_required_groups: list[str]
    animation_clips: list[str]
    rig_ready: bool
    animation_ready: bool
    preview_animation_ready: bool
    facial: dict
    secondary_motion: dict
    warnings: list[str]

def inspect(glb: Path, spec_path: Path) -> RigReport:
    spec = _load_spec(spec_path)
    doc = _load_glb_json(glb)
    nodes = doc.get("nodes", [])
    node_names = [str(n.get("name", "")) for n in nodes]
    skins = doc.get("skins", [])
    joint_indices = set()
    for skin in skins:
        for idx in skin.get("joints", []) or []:
            if isinstance(idx, int):
                joint_indices.add(idx)
    joint_names = [
        node_names[i] for i in sorted(joint_indices)
        if 0 <= i < len(node_names)
    ]

    required = spec.get("required_bones", {})
    missing = []
    found = 0
    for group, aliases in required.items():
        if _matches(joint_names, aliases):
            found += 1
        else:
            missing.append(group)
    total = max(1, len(required))
    fraction = found / total

    animations = []
    for i, anim in enumerate(doc.get("animations", []) or []):
        name = str(anim.get("name") or f"clip_{i}")
        animations.append(name)

    targets = _target_names(doc)
    facial_optional = spec.get("facial_optional", {})
    jaw = _matches(joint_names, facial_optional.get("jaw", [])) or bool(
        _pattern_hits(targets, ["jaw", "mouthopen", "viseme"])
    )
    eye_l = _matches(joint_names, facial_optional.get("eye_l", []))
    eye_r = _matches(joint_names, facial_optional.get("eye_r", []))
    blink_l = _matches(joint_names, facial_optional.get("eyelid_l", [])) or bool(
        _pattern_hits(targets, ["blink_l", "blinkleft", "eyeblinkleft"])
    )
    blink_r = _matches(joint_names, facial_optional.get("eyelid_r", [])) or bool(
        _pattern_hits(targets, ["blink_r", "blinkright", "eyeblinkright"])
    )

    secondary = spec.get("secondary_motion_patterns", {})
    hair_hits = _pattern_hits(node_names, secondary.get("hair", []))
    cloth_hits = _pattern_hits(node_names, secondary.get("cloth", []))

    rules = spec.get("rules", {})
    min_joints = int(rules.get("min_joint_count", 15))
    min_fraction = float(rules.get("ready_required_group_fraction", 0.8))
    require_skin = bool(rules.get("require_skin", True))
    rig_ready = (
        (not require_skin or len(skins) > 0)
        and len(joint_indices) >= min_joints
        and fraction >= min_fraction
    )

    warnings = []
    if not skins:
        warnings.append("no_skin")
    if len(joint_indices) < min_joints:
        warnings.append(f"too_few_joints:{len(joint_indices)}<{min_joints}")
    if fraction < min_fraction:
        warnings.append(f"missing_core_bones:{found}/{len(required)}")
    if not animations:
        warnings.append("no_embedded_animation_clips")
    if not jaw:
        warnings.append("no_jaw_control")
    if not (blink_l and blink_r):
        warnings.append("no_blink_controls")

    return RigReport(
        schema=1,
        skeleton_type=str(spec.get("id", "hayuya_humanoid_v1")),
        valid_glb=True,
        skins=len(skins),
        joints=len(joint_indices),
        required_groups_found=found,
        required_groups_total=len(required),
        required_group_fraction=round(fraction, 6),
        missing_required_groups=missing,
        animation_clips=animations,
        rig_ready=rig_ready,
        animation_ready=rig_ready,
        preview_animation_ready=rig_ready and bool(animations),
        facial={
            "jaw": jaw,
            "eye_l": eye_l,
            "eye_r": eye_r,
            "blink_l": blink_l,
            "blink_r": blink_r,
            "morph_targets": targets,
        },
        secondary_motion={
            "hair_nodes": hair_hits,
            "cloth_nodes": cloth_hits,
            "hair_ready": bool(hair_hits),
            "cloth_ready": bool(cloth_hits),
        },
        warnings=warnings,
    )

def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect a GLB for HAYUYA humanoid rig/animation readiness.")
    parser.add_argument("glb", type=Path)
    parser.add_argument(
        "--spec",
        type=Path,
        default=Path("hayuya/standards/hayuya_humanoid_v1.json"),
    )
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    try:
        report = inspect(args.glb, args.spec)
        payload = json.dumps(asdict(report), indent=2)
        print(payload)
        if args.json:
            args.json.parent.mkdir(parents=True, exist_ok=True)
            args.json.write_text(payload + "\n", encoding="utf-8")
        return 0
    except Exception as exc:
        payload = {
            "schema": 1,
            "skeleton_type": "hayuya_humanoid_v1",
            "valid_glb": False,
            "rig_ready": False,
            "animation_ready": False,
            "preview_animation_ready": False,
            "warnings": [f"{type(exc).__name__}:{exc}"],
        }
        print(json.dumps(payload, indent=2))
        if args.json:
            args.json.parent.mkdir(parents=True, exist_ok=True)
            args.json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
