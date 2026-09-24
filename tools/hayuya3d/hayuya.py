#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import traceback
from dataclasses import asdict, dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

from adapters import DEFAULT_MODEL_ROOT, GENERATORS, REFINERS, pshuman_readiness
from qa import export_glb, rank_candidates
from reference_pool import infer_detail_region_hint, order_for_multiview_coverage, split_reference_roles
from mobile_portability import build_portability_plan


@dataclass(frozen=True)
class Profile:
    faces: int
    texture_size: int
    trellis2_resolution: int
    backends: tuple[str, ...]
    multi_anchor: bool
    multiview_group_size: int


PROFILES = {
    "preview": Profile(
        faces=30_000,
        texture_size=1024,
        trellis2_resolution=512,
        backends=("triposr", "triposg"),
        multi_anchor=False,
        multiview_group_size=4,
    ),
    "mobile": Profile(
        faces=35_000,
        texture_size=2048,
        trellis2_resolution=512,
        backends=("trellis", "triposg", "triposr"),
        multi_anchor=False,
        multiview_group_size=5,
    ),
    "game": Profile(
        faces=80_000,
        texture_size=2048,
        trellis2_resolution=1024,
        backends=("triposg", "trellis", "instantmesh", "triposr"),
        multi_anchor=True,
        multiview_group_size=6,
    ),
    "monster": Profile(
        faces=250_000,
        texture_size=4096,
        trellis2_resolution=1024,
        backends=("trellis2", "triposg", "trellis", "instantmesh", "triposr"),
        multi_anchor=True,
        multiview_group_size=6,
    ),
    "ultra": Profile(
        faces=500_000,
        texture_size=4096,
        trellis2_resolution=1536,
        backends=("trellis2", "triposg", "trellis", "instantmesh", "triposr"),
        multi_anchor=True,
        multiview_group_size=8,
    ),
}


def load_lock() -> dict:
    return json.loads((HERE / "backends.lock.json").read_text(encoding="utf-8"))


def backend_meta(lock: dict) -> dict[str, dict]:
    return {x["id"]: x for x in lock["backends"]}


def validate_inputs(inputs: list[Path]) -> list[Path]:
    if not inputs:
        raise ValueError("Hayuya Monster requires at least one source photo")

    out: list[Path] = []
    seen_paths: set[Path] = set()
    seen_content: set[str] = set()
    for p in inputs:
        p = p.resolve()
        if p in seen_paths:
            # Do not let accidental duplicate CLI args overweight one image in the Judge.
            continue
        seen_paths.add(p)

        if not p.is_file():
            raise FileNotFoundError(p)
        if p.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            raise ValueError(f"unsupported image format: {p}")
        if p.stat().st_size < 512:
            raise ValueError(f"image is unexpectedly small: {p}")

        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        if digest in seen_content:
            # Copied/renamed duplicate files should not count as extra evidence.
            continue
        seen_content.add(digest)
        out.append(p)

    if not out:
        raise ValueError("no unique valid source photos remain")
    return out


def infer_asset_mode(primary: Path) -> str:
    parts = {part.lower() for part in primary.parts}
    stem_tokens = set(primary.stem.lower().replace("-", "_").split("_"))
    tokens = parts | stem_tokens

    character_tokens = {
        "character", "characters", "zombie", "zombies", "human", "humans",
        "humanoid", "humanoids", "npc", "npcs", "llorona",
    }
    architecture_tokens = {
        "architecture", "building", "buildings", "church", "churches", "iglesia",
    }
    if tokens & character_tokens:
        return "character"
    if tokens & architecture_tokens:
        return "architecture"
    return "prop"


ASSET_PROFILE_IDS = {
    "auto", "character.humanoid", "character.creature", "weapon.firearm",
    "weapon.melee", "prop.mechanical", "vehicle", "foliage.grass",
    "foliage.tree", "prop.static", "environment.modular",
}


def infer_asset_profile(primary: Path, mode: str = "auto") -> str:
    raw_parts = [part.lower() for part in primary.parts]
    tokens = set(raw_parts)
    for part in [*raw_parts, primary.stem.lower()]:
        tokens.update(part.replace("-", "_").replace(".", "_").split("_"))

    if tokens & {"pistol","handgun","revolver","shotgun","rifle","smg","lmg","gun","firearm","sniper","launcher","p90"}:
        return "weapon.firearm"
    if tokens & {"sword","knife","machete","axe","bat","club","melee"}:
        return "weapon.melee"
    if tokens & {"grass","turf"}:
        return "foliage.grass"
    if tokens & {"tree","trees","bush","bushes","plant","plants","foliage"}:
        return "foliage.tree"
    if tokens & {"car","cars","truck","vehicle","vehicles","van","bike","motorcycle"}:
        return "vehicle"
    if tokens & {"door","fan","gear","machine","mechanical","hinge","elevator"}:
        return "prop.mechanical"
    if tokens & {"monster","creature","animal","quadruped"}:
        return "character.creature"
    if tokens & {"character","characters","zombie","zombies","human","humans","humanoid","humanoids","npc","npcs","llorona"}:
        return "character.humanoid"
    if mode == "character":
        return "character.humanoid"
    if mode == "architecture":
        return "environment.modular"
    return "prop.static"


def load_asset_profile_spec(asset_profile: str) -> dict:
    path = ROOT / "hayuya" / "standards" / "hayuya_asset_profiles_v1.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for profile in data.get("profiles", []):
        if profile.get("id") == asset_profile:
            return profile
    if asset_profile == "auto":
        return {
            "id": "auto",
            "label": "Auto",
            "animation_systems": [],
            "preferred_pipeline": [],
            "required_qa": ["mesh_gate", "texture_clarity"],
        }
    raise ValueError(f"unknown asset profile: {asset_profile}")


def face_seed_hypothesis_count(profile_name: str, detail_inputs: list[Path]) -> int:
    has_face_reference=any(
        infer_detail_region_hint(path)=="head"
        for path in detail_inputs
    )
    if not has_face_reference:
        return 1
    if profile_name=="ultra":
        return 3
    if profile_name=="monster":
        return 2
    return 1


def needs_texture_superres(
    profile_name: str,
    base_color_min_edge: int | None,
    target_edge: int,
) -> bool:
    if profile_name not in {"monster", "ultra"}:
        return False
    edge=int(base_color_min_edge or 0)
    return edge>0 and edge<int(target_edge)


def make_reference_groups(inputs: list[Path], group_size: int) -> list[list[Path]]:
    """
    Split an arbitrary reference pool into backend-sized groups without dropping evidence.

    The first source is the continuity anchor and appears in every group. Every other
    source appears in exactly one group. The global Judge still evaluates every
    candidate against the complete reference pool.
    """
    if group_size < 2:
        raise ValueError("multiview group size must be >= 2")
    if len(inputs) <= group_size:
        return [list(inputs)]

    primary = inputs[0]
    payload = group_size - 1
    groups: list[list[Path]] = []
    others = order_for_multiview_coverage(inputs[1:])
    for i in range(0, len(others), payload):
        groups.append([primary, *others[i:i + payload]])
    return groups


def limit_anchor_refs(inputs: list[Path], budget: int | None) -> list[Path]:
    """
    budget=None or <=0 means every real source can spawn a single-image hypothesis.
    A positive budget is an explicit user/CI cost control, never a hidden fidelity cap.
    """
    if budget is None or budget <= 0 or budget >= len(inputs):
        return list(inputs)
    if budget == 1:
        return [inputs[0]]

    # Deterministically sample across the entire ordered reference pool.
    picks = [0]
    remaining = budget - 1
    span = len(inputs) - 1
    for i in range(1, remaining + 1):
        idx = round(i * span / remaining)
        picks.append(min(len(inputs) - 1, idx))
    deduped: list[Path] = []
    seen: set[int] = set()
    for idx in picks:
        if idx not in seen:
            seen.add(idx)
            deduped.append(inputs[idx])
    return deduped


def _viewforge_strategy(count: int) -> str:
    if count == 1:
        return "single-source expansion: synthesize only missing coverage"
    if count == 2:
        return "multi-source fusion: preserve both real anchors and synthesize only missing coverage"
    return (
        f"reference-pool fusion: preserve all {count} real sources, group only where a backend "
        "needs bounded batches, and synthesize only uncovered viewpoints"
    )


def make_job_plan(
    inputs: list[Path],
    *,
    profile_name: str,
    mode: str,
    seed: int,
    selected_backends: list[str],
    model_root: Path,
    multiview_group_size: int | None = None,
    anchor_hypothesis_budget: int | None = None,
    appearance_mode: str = "auto",
    viewforge_mode: str = "auto",
    geometry_refine_mode: str = "auto",
    gameprep_mode: str = "auto",
    character_specialist_mode: str = "off",
    mesh_doctor_mode: str = "auto",
    retopo_mode: str = "auto",
    texture_superres_mode: str = "auto",
    portable_target: str = "auto",
    portable_pack_mode: str = "auto",
    texture_delivery_mode: str = "auto",
    asset_profile: str | None = None,
    animation_requested: bool = False,
) -> dict:
    profile = PROFILES[profile_name]
    resolved_asset_profile = asset_profile or infer_asset_profile(inputs[0], mode)
    if resolved_asset_profile == "auto":
        resolved_asset_profile = infer_asset_profile(inputs[0], mode)
    asset_spec = load_asset_profile_spec(resolved_asset_profile)
    portability_plan = build_portability_plan(
        mode=mode,
        tier=portable_target,
        profile_name=profile_name,
    )
    roles = split_reference_roles(inputs)
    geometry_inputs = roles.geometry
    detail_inputs = roles.detail
    group_size = multiview_group_size or profile.multiview_group_size
    groups = make_reference_groups(geometry_inputs, group_size) if len(geometry_inputs) > 1 else [list(geometry_inputs)]
    anchor_refs = (
        limit_anchor_refs(geometry_inputs, anchor_hypothesis_budget)
        if profile.multi_anchor
        else [geometry_inputs[0]]
    )
    face_seed_count=face_seed_hypothesis_count(profile_name,detail_inputs)

    return {
        "engine": "HAYUYA MONSTER",
        "schema": 2,
        "inputs": [str(p) for p in inputs],
        "input_count": len(inputs),
        "reference_pool": {
            "logical_limit": None,
            "all_real_sources_are_authoritative": True,
            "duplicate_paths_are_deduplicated": True,
            "duplicate_file_content_is_deduplicated": True,
            "ordered_primary_source": str(geometry_inputs[0]),
            "geometry_sources": [str(p) for p in geometry_inputs],
            "geometry_source_count": len(geometry_inputs),
            "detail_sources": [str(p) for p in detail_inputs],
            "detail_source_count": len(detail_inputs),
            "detail_policy": "detail/close-up references are preserved for material/local-detail stages and do not distort whole-object silhouette scoring",
        },
        "mode": mode,
        "profile": profile_name,
        "asset_profile": resolved_asset_profile,
        "asset_pipeline": {
            "label": asset_spec.get("label", resolved_asset_profile),
            "animation_requested": bool(animation_requested),
            "animation_systems": asset_spec.get("animation_systems", []),
            "preferred_pipeline": asset_spec.get("preferred_pipeline", []),
            "required_qa": asset_spec.get("required_qa", []),
            "policy": "asset-type-specific postprocess; never force humanoid rigging or incompatible mechanical animation onto unrelated geometry",
        },
        "mobile_portability": portability_plan,
        "portable_pack": {
            "mode": portable_pack_mode,
            "texture_delivery_mode": texture_delivery_mode,
            "tiers": ["flagship", "high", "balanced", "compatibility"],
            "policy": "derive every runtime tier independently from the preserved Hero Master; never cascade quality loss from one tier into the next",
        },
        "seed": seed,
        "targets": {
            "faces": profile.faces,
            "texture_size": profile.texture_size,
            "trellis2_resolution": profile.trellis2_resolution,
        },
        "viewforge": {
            "mode": viewforge_mode,
            "auto_activation": "one real geometry source + bootstrapped Wonder3D",
            "strategy": _viewforge_strategy(len(geometry_inputs)),
            "canonical_views": [
                "front",
                "front_45_right",
                "right",
                "back_45_right",
                "back",
                "back_45_left",
                "left",
                "front_45_left",
            ],
            "normal_support": ["wonder3d"],
            "sparse_view_support": ["instantmesh/zero123++"],
            "real_sources_override_synthetic_views": True,
            "wonder3d_rgb_normal_stage": True,
            "single_source_trellis_fusion": "real primary anchor + up to five non-front synthetic Wonder3D RGB views",
            "synthetic_views_never_enter_real_source_judge": True,
        },
        "multi_reference": {
            "enabled": len(geometry_inputs) > 1,
            "backend_group_size": group_size,
            "group_count": len(groups),
            "groups": [[str(p) for p in group] for group in groups],
            "single_image_anchor_hypotheses": [str(p) for p in anchor_refs],
            "anchor_hypothesis_budget": anchor_hypothesis_budget,
            "all_geometry_sources_always_used_by_judge": True,
            "detail_sources_reserved_for_material_and_local_detail_validation": True,
            "detail_sources_enter_judge_v3_when_appearance_is_active": True,
        },
        "candidate_backends": selected_backends,
        "face_seed_tournament": {
            "enabled": face_seed_count>1,
            "trellis2_seed_count": face_seed_count,
            "activation": "Monster/Ultra + explicit head/face detail evidence",
            "policy": "extra high-end stochastic hypotheses are judged against the same geometry and face evidence; no seed is auto-promoted",
        },
        "character_specialist": {
            "mode": character_specialist_mode,
            "backend": "PSHuman 768 6-view",
            "activation": "explicit non-off opt-in + --allow-restricted + character mode + complete PSHuman auxiliary assets + >=40GB VRAM",
            "policy": "specialist is one additional candidate and must win the same real-source Judge; never auto-promoted",
            "auxiliary_asset_gate": "smpl_related + PIXIE/SMPLX assets must exist; Hayuya does not auto-download separately licensed body-model data"
        },
        "mesh_doctor": {
            "mode": mesh_doctor_mode,
            "activation": "audit provisional champion before retopology; safe repair challenger only when structural defects are detected",
            "safe_repairs": ["duplicate faces", "degenerate faces", "unreferenced vertices", "winding/normals", "small simple holes for props/architecture"],
            "audit_only": ["tiny disconnected components"],
            "policy": "never delete tiny accessories automatically; repaired/material-restored GLB must re-enter the complete real-source Judge",
            "rig_policy": "audit rigged glTF but skip topology-changing repair until JOINTS/WEIGHTS transfer exists"
        },
        "retopology": {
            "mode": retopo_mode,
            "backend": "Instant Meshes field-aligned retopology",
            "activation": "unrigged provisional champion + bootstrapped/built Instant Meshes binary",
            "style": "pure_quad for prop/architecture; quad_dominant for unrigged character",
            "policy": "preserve retopo_master.obj as editable topology, restore PBR through Material Bridge v2, then re-enter the complete real-source Judge; never overwrite the source candidate blindly",
            "rig_policy": "skip any glTF with skins until skin-weight-preserving retopology transfer exists"
        },
        "texture_superres": {
            "mode": texture_superres_mode,
            "backend": "Real-ESRGAN NCNN Vulkan",
            "activation": "Monster/Ultra provisional champion only when weakest embedded baseColor is below the profile target and the optional executable is available",
            "policy": "rewrite only embedded baseColor image payloads, preserve geometry/skin/animation buffers byte-for-byte, add as a separate challenger, and require the complete Judge to choose it",
            "model": "realesrgan-x4plus"
        },
        "geometry_refinement": {
            "mode": geometry_refine_mode,
            "backend": "TripoSF SparseFlex 1024^3",
            "activation": "monster/ultra execution when bootstrapped and VRAM budget >=12GB",
            "policy": "refined topology is a challenger; real-source geometry evidence must improve before it is marked preferred",
            "asset_promotion": "when refined geometry wins, Material Bridge v2 transfers/reprojects the strongest available material evidence and the bridged GLB must win the full final Judge",
            "material_bridge_v2": "packed PBR atlas + nearest-surface UV projection preserves baseColor/metallic/roughness/normal/AO/emissive when source UV/PBR exists; automatic v1 base-color fallback otherwise"
        },
        "gameprep": {
            "mode": gameprep_mode,
            "activation": "auto for mobile/game/monster/ultra after final champion",
            "outputs": ["master.glb", "LOD0.glb", "LOD1.glb", "LOD2.glb", "LOD3.glb", "collision_convex.glb", "8-frame turntable", "gameprep_manifest.json"],
            "lod_material_policy": "master keeps original materials; simplified LODs reuse one Material Bridge v2 transfer context so PBR/UV survives when source material supports it, with v1 base-color fallback"
        },
        "judge": {
            "version": "v3-auto" if appearance_mode != "off" else "v2",
            "production_subscore": {
                "geometry_capacity_weight": 0.42,
                "topology_health_weight": 0.33,
                "material_readiness_weight": 0.18,
                "bbox_health_weight": 0.07,
            },
            "final_mix": {
                "source_visual_weight": 0.55,
                "production_weight": 0.45,
            },
            "source_visual": {
                "method": "two-stage software silhouette camera search",
                "azimuth_step_degrees": 30,
                "elevations_degrees": [-15, 0, 15],
                "up_axis_hypotheses": ["y", "z"],
                "projection_stage_1": "global orthographic bank",
                "projection_stage_2": "local +/-15 degree refinement across orthographic and perspective camera distances [1.4, 2.4, 4.0]",
                "per_source_metric": "0.72 silhouette IoU + 0.28 boundary F1",
                "multi_source_aggregation": "<=2: 0.70 mean + 0.30 min; >=3: 0.65 mean + 0.25 lower-quartile mean + 0.10 min",
                "evaluate_every_geometry_source": True,
            },
            "appearance": {
                "mode": appearance_mode,
                "backend": "DINOv2 ViT-S/14 LVD-142M",
                "license": "Apache-2.0",
                "candidate_render": "Hayuya deterministic CPU RGB z-buffer from matched v2 camera, including recovered perspective",
                "texture_rendering": "per-pixel UV/base-color texture sampling with vertex-color fallback",
                "weight_when_active": 0.25,
                "whole_object_vs_detail_mix": "0.72 geometry appearance + 0.28 local-detail retrieval when detail refs exist",
                "detail_search": "8 canonical candidate views x whole-frame + 3x3 local patches",
                "fallback": "Judge v2 when DINOv2 is unavailable in auto mode"
            },
            "synthetic_normal_support": {
                "source": "Wonder3D ViewForge normals when available",
                "coordinate_system": "front-view OpenGL normal system from pinned Wonder3D",
                "weight": 0.06,
                "evidence_class": "synthetic support only; never equivalent to a real reference"
            },
            "future_extension": "normal/depth agreement + calibrated camera estimation + local-detail appearance Judge",
        },
        "model_root": str(model_root.resolve()),
        "output": "hayuya_final.glb",
    }


def choose_backends(
    lock: dict,
    profile: Profile,
    override: str | None,
    *,
    gpu_vram: int | None,
    allow_restricted: bool,
) -> list[str]:
    meta = backend_meta(lock)
    requested = list(profile.backends if not override else [x.strip() for x in override.split(",") if x.strip()])
    selected: list[str] = []
    for backend in requested:
        if backend not in meta:
            raise ValueError(f"unknown backend: {backend}")
        if backend == "pshuman":
            raise ValueError(
                "PSHuman is a gated character specialist; use "
                "--character-specialist auto|required with --allow-restricted"
            )
        entry = meta[backend]
        permissive = entry["license"] in {"MIT", "Apache-2.0"}
        if not permissive and not allow_restricted:
            print(f"SKIP {backend}: opt-in/restricted license", file=sys.stderr)
            continue
        if gpu_vram is not None and int(entry["min_vram_gb"]) > gpu_vram:
            print(
                f"SKIP {backend}: requires >= {entry['min_vram_gb']}GB VRAM, budget={gpu_vram}GB",
                file=sys.stderr,
            )
            continue
        if backend not in GENERATORS:
            print(f"SKIP {backend}: planner knows it but no executable adapter exists yet", file=sys.stderr)
            continue
        selected.append(backend)
    return selected


def run_single_backend(
    backend: str,
    image: Path,
    out_dir: Path,
    *,
    profile: Profile,
    seed: int,
    model_root: Path,
):
    if backend == "trellis2":
        return GENERATORS[backend](
            image,
            out_dir,
            seed=seed,
            resolution=profile.trellis2_resolution,
            faces=profile.faces,
            texture_size=profile.texture_size,
            model_root=model_root,
        )
    if backend == "triposg":
        return GENERATORS[backend](
            image,
            out_dir,
            faces=profile.faces,
            seed=seed,
            model_root=model_root,
        )
    if backend == "triposr":
        return GENERATORS[backend](
            image,
            out_dir,
            texture_size=profile.texture_size,
            model_root=model_root,
        )
    if backend == "instantmesh":
        return GENERATORS[backend](
            image,
            out_dir,
            seed=seed,
            model_root=model_root,
        )
    if backend == "pshuman":
        return GENERATORS[backend](
            image,
            out_dir,
            seed=seed,
            model_root=model_root,
        )
    if backend == "spar3d":
        return GENERATORS[backend](
            image,
            out_dir,
            texture_size=profile.texture_size,
            faces=profile.faces,
            model_root=model_root,
        )
    raise ValueError(f"unsupported single-image backend: {backend}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HAYUYA MONSTER: open ensemble image-to-3D orchestrator for an arbitrary reference pool."
    )
    parser.add_argument(
        "--input",
        type=Path,
        action="append",
        default=[],
        help="source image; repeat as many times as useful",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        action="append",
        default=[],
        help="directory containing reference images; repeatable and recursively scanned",
    )
    parser.add_argument("--profile", choices=sorted(PROFILES), default="monster")
    parser.add_argument(
        "--portable-target",
        choices=["auto", "compatibility", "balanced", "high", "flagship"],
        default="auto",
        help="runtime mobile portability tier; auto maps preview/mobile/game/monster/ultra to compatibility/compatibility/balanced/high/flagship",
    )
    parser.add_argument("--mode", choices=["auto", "prop", "character", "architecture"], default="auto")
    parser.add_argument("--asset-profile", choices=sorted(ASSET_PROFILE_IDS), default="auto")
    parser.add_argument("--animation", action="store_true", help="request the profile-compatible animation/postprocess path")
    parser.add_argument("--seed", type=int, default=1993)
    parser.add_argument("--backends", help="comma-separated override")
    parser.add_argument("--gpu-vram", type=int, help="VRAM budget in GB; skips larger backends")
    parser.add_argument(
        "--multiview-group-size",
        type=int,
        help="practical per-call multiview batch size; does not limit the total reference pool",
    )
    parser.add_argument(
        "--anchor-hypothesis-budget",
        type=int,
        default=0,
        help="single-image hypothesis budget; 0 means use every real source in multi-anchor profiles",
    )
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODEL_ROOT)
    parser.add_argument("--output-root", type=Path, default=ROOT / "out" / "hayuya3d")
    parser.add_argument("--execute", action="store_true", help="actually run installed backends")
    parser.add_argument("--require-all", action="store_true", help="fail if any selected backend candidate fails")
    parser.add_argument("--allow-restricted", action="store_true", help="allow explicitly opt-in non-permissive backends")
    parser.add_argument(
        "--viewforge",
        choices=["off", "auto", "required"],
        default="auto",
        help="Wonder3D RGB+normal expansion policy; auto activates for one-source jobs when bootstrapped",
    )
    parser.add_argument(
        "--geometry-refine",
        choices=["off", "auto", "required"],
        default="auto",
        help="TripoSF SparseFlex geometry challenger policy for monster/ultra execution",
    )
    parser.add_argument(
        "--mesh-doctor",
        choices=["off", "auto", "required"],
        default="auto",
        help="audit provisional champion and add a conservative structural-repair challenger when safe",
    )
    parser.add_argument(
        "--retopo",
        choices=["off", "auto", "required"],
        default="auto",
        help="Instant Meshes deterministic quad retopology challenger; auto runs only when the optional native binary is ready and the provisional champion is unrigged",
    )
    parser.add_argument(
        "--texture-superres",
        choices=["off", "auto", "required"],
        default="auto",
        help="Real-ESRGAN visible baseColor challenger; auto runs for Monster/Ultra only when the provisional champion is below the profile texture target",
    )
    parser.add_argument(
        "--character-specialist",
        choices=["off", "auto", "required"],
        default="off",
        help="PSHuman 40GB+ humanoid challenger. Mixed third-party licensing: requires explicit non-off selection plus --allow-restricted.",
    )
    parser.add_argument(
        "--gameprep",
        choices=["off", "auto", "required"],
        default="auto",
        help="build selected-tier master/LOD/collision/turntable pack after the final champion",
    )
    parser.add_argument(
        "--portable-pack",
        choices=["off", "auto", "required"],
        default="auto",
        help="derive Flagship/High/Balanced/Compatibility runtime packs independently from the preserved Hero Master",
    )
    parser.add_argument(
        "--texture-delivery",
        choices=["off", "auto", "required"],
        default="auto",
        help="physical KTX2/BasisU delivery policy for portable runtime LOD GLBs",
    )
    parser.add_argument(
        "--appearance-judge",
        choices=["off", "auto", "required"],
        default="auto",
        help="Judge v3 DINOv2 appearance scoring policy; auto falls back to v2 if evaluator is not bootstrapped",
    )
    args = parser.parse_args()

    raw_inputs = list(args.input)
    for root in args.input_dir:
        root = root.resolve()
        if not root.is_dir():
            parser.error(f"--input-dir is not a directory: {root}")
        raw_inputs.extend(
            p for p in sorted(root.rglob("*"))
            if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
        )
    if not raw_inputs:
        parser.error("provide at least one --input or --input-dir")

    inputs = validate_inputs(raw_inputs)
    roles = split_reference_roles(inputs)
    geometry_inputs = roles.geometry
    detail_inputs = roles.detail
    profile = PROFILES[args.profile]
    group_size = args.multiview_group_size or profile.multiview_group_size
    if group_size < 2:
        parser.error("--multiview-group-size must be >= 2")

    lock = load_lock()
    selected = choose_backends(
        lock,
        profile,
        args.backends,
        gpu_vram=args.gpu_vram,
        allow_restricted=args.allow_restricted,
    )
    if not selected:
        raise SystemExit("No executable backends selected")

    mode = args.mode
    if mode == "auto":
        mode = infer_asset_mode(geometry_inputs[0])
    if args.character_specialist != "off" and not args.allow_restricted:
        parser.error("--character-specialist requires --allow-restricted because PSHuman includes separately licensed third-party human-model components")
    if args.character_specialist == "required" and mode != "character":
        parser.error("--character-specialist required needs --mode character or a character-path input")

    reference_groups = (
        make_reference_groups(geometry_inputs, group_size)
        if len(geometry_inputs) > 1
        else [list(geometry_inputs)]
    )
    anchor_refs = (
        limit_anchor_refs(geometry_inputs, args.anchor_hypothesis_budget)
        if profile.multi_anchor
        else [geometry_inputs[0]]
    )
    face_seed_count=face_seed_hypothesis_count(args.profile,detail_inputs)

    job_name = f"{geometry_inputs[0].stem}-{args.profile}-{args.seed}"
    job_dir = args.output_root / job_name
    candidates_dir = job_dir / "candidates"
    job_dir.mkdir(parents=True, exist_ok=True)

    plan = make_job_plan(
        inputs,
        profile_name=args.profile,
        mode=mode,
        seed=args.seed,
        selected_backends=selected,
        model_root=args.model_root,
        multiview_group_size=group_size,
        anchor_hypothesis_budget=args.anchor_hypothesis_budget,
        appearance_mode=args.appearance_judge,
        viewforge_mode=args.viewforge,
        geometry_refine_mode=args.geometry_refine,
        gameprep_mode=args.gameprep,
        character_specialist_mode=args.character_specialist,
        mesh_doctor_mode=args.mesh_doctor,
        retopo_mode=args.retopo,
        texture_superres_mode=args.texture_superres,
        portable_target=args.portable_target,
        portable_pack_mode=args.portable_pack,
        texture_delivery_mode=args.texture_delivery,
        asset_profile=(None if args.asset_profile == "auto" else args.asset_profile),
        animation_requested=args.animation,
    )
    portable_runtime = plan["mobile_portability"]["runtime_target"]
    portable_lod0_ceiling = int(portable_runtime["lod0_triangles"][1])
    portable_texture_ceiling = int(portable_runtime["exceptional_texture_edge_px"])
    (job_dir / "plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(plan, indent=2))

    if not args.execute:
        print(f"HAYUYA_PLAN_READY {job_dir / 'plan.json'}")
        return 0

    candidates: list[tuple[str, Path]] = []
    failures: dict[str, str] = {}

    viewforge_result = None
    viewforge_failure = None
    should_try_viewforge = args.viewforge in {"auto", "required"} and len(geometry_inputs) == 1
    if should_try_viewforge:
        wonder_ready = (args.model_root / "wonder3d").is_dir()
        if not wonder_ready and args.viewforge == "required":
            raise RuntimeError(
                "ViewForge required but Wonder3D is not bootstrapped. "
                "Run: python tools/hayuya3d/bootstrap.py --backend wonder3d"
            )
        if wonder_ready:
            try:
                from viewforge import generate_wonder3d_views
                viewforge_result = generate_wonder3d_views(
                    geometry_inputs[0],
                    job_dir / "viewforge",
                    seed=args.seed,
                    model_root=args.model_root,
                )
                print(
                    f"HAYUYA_VIEWFORGE_READY backend={viewforge_result.backend} "
                    f"synthetic_views={len(viewforge_result.synthetic_reconstruction_views)}"
                )
            except Exception as exc:
                viewforge_failure = f"{type(exc).__name__}: {exc}"
                print(f"HAYUYA_VIEWFORGE_FAILED {viewforge_failure}", file=sys.stderr)
                traceback.print_exc()
                if args.viewforge == "required":
                    raise

    character_specialist_failure = None
    character_specialist_status = "not_applicable"
    if mode == "character" and args.character_specialist in {"auto", "required"}:
        character_specialist_status = "checking"
        repo_ready = (args.model_root / "pshuman").is_dir()
        vram_ready = args.gpu_vram is None or args.gpu_vram >= 40
        assets_ready, missing_assets = pshuman_readiness(args.model_root) if repo_ready else (False, ["backend repo missing"])

        if not repo_ready or not vram_ready or not assets_ready:
            reasons = []
            if not repo_ready:
                reasons.append("PSHuman backend not bootstrapped")
            if not vram_ready:
                reasons.append(f"PSHuman requires >40GB VRAM; budget={args.gpu_vram}GB")
            if repo_ready and not assets_ready:
                reasons.append("missing auxiliary assets: " + ", ".join(missing_assets))
            character_specialist_failure = "; ".join(reasons)
            character_specialist_status = "skipped"
            print(
                f"HAYUYA_CHARACTER_SPECIALIST_SKIPPED {character_specialist_failure}",
                file=sys.stderr,
            )
            if args.character_specialist == "required":
                raise RuntimeError(character_specialist_failure)
        else:
            try:
                specialist = run_single_backend(
                    "pshuman",
                    geometry_inputs[0],
                    candidates_dir / "pshuman",
                    profile=profile,
                    seed=args.seed,
                    model_root=args.model_root,
                )
                candidates.append(("pshuman", specialist.model_path))
                character_specialist_status = "candidate_ready"
                print(
                    f"HAYUYA_CANDIDATE_READY pshuman {specialist.model_path} "
                    "specialist=humanoid"
                )
            except Exception as exc:
                character_specialist_failure = f"{type(exc).__name__}: {exc}"
                character_specialist_status = "failed"
                print(
                    f"HAYUYA_CHARACTER_SPECIALIST_FAILED {character_specialist_failure}",
                    file=sys.stderr,
                )
                traceback.print_exc()
                if args.character_specialist == "required":
                    raise

    for backend in selected:
        if backend == "pshuman":
            # Specialist is managed above so it cannot accidentally run twice.
            continue
        if backend == "trellis":
            # Native multi-image backend: every source participates in at least one group.
            for group_index, group in enumerate(reference_groups, start=1):
                label = f"trellis_group{group_index:02d}"
                try:
                    candidate = GENERATORS["trellis"](
                        group,
                        candidates_dir / label,
                        seed=args.seed + group_index - 1,
                        texture_size=profile.texture_size,
                        model_root=args.model_root,
                    )
                    candidates.append((label, candidate.model_path))
                    print(
                        f"HAYUYA_CANDIDATE_READY {label} {candidate.model_path} "
                        f"sources={len(group)}"
                    )
                except Exception as exc:
                    failures[label] = f"{type(exc).__name__}: {exc}"
                    print(f"HAYUYA_CANDIDATE_FAILED {label}: {failures[label]}", file=sys.stderr)
                    traceback.print_exc()
                    if args.require_all:
                        raise
            # One-photo jobs gain an additional native multi-image TRELLIS hypothesis
            # from the real anchor plus ViewForge's synthetic missing coverage.
            if viewforge_result is not None and len(geometry_inputs) == 1:
                synthetic = [
                    Path(p)
                    for p in viewforge_result.synthetic_reconstruction_views
                ][: max(0, group_size - 1)]
                vf_inputs = [geometry_inputs[0], *synthetic]
                if len(vf_inputs) > 1:
                    label = "trellis_viewforge"
                    try:
                        candidate = GENERATORS["trellis"](
                            vf_inputs,
                            candidates_dir / label,
                            seed=args.seed + 777,
                            texture_size=profile.texture_size,
                            model_root=args.model_root,
                        )
                        candidates.append((label, candidate.model_path))
                        print(
                            f"HAYUYA_CANDIDATE_READY {label} {candidate.model_path} "
                            f"real_sources=1 synthetic_sources={len(synthetic)}"
                        )
                    except Exception as exc:
                        failures[label] = f"{type(exc).__name__}: {exc}"
                        print(
                            f"HAYUYA_CANDIDATE_FAILED {label}: {failures[label]}",
                            file=sys.stderr,
                        )
                        traceback.print_exc()
                        if args.require_all:
                            raise
            continue

        # Expensive single-image backends normally run once from the primary
        # source. When explicit face evidence exists, Monster/Ultra allow a
        # bounded TRELLIS.2 seed tournament so the appearance Judge can choose
        # among genuinely different high-end face hypotheses instead of grading
        # one stochastic draw. No extra seeds run without face evidence.
        run_refs = anchor_refs if backend == "triposg" and profile.multi_anchor else [geometry_inputs[0]]
        seed_count = face_seed_count if backend == "trellis2" else 1
        for anchor_index, image in enumerate(run_refs, start=1):
            for seed_index in range(seed_count):
                seed_value=args.seed + anchor_index - 1 + seed_index*1009
                if len(run_refs)==1 and seed_count==1:
                    label=backend
                elif seed_count>1:
                    label=f"{backend}_seed{seed_index+1:02d}"
                else:
                    label=f"{backend}_anchor{anchor_index:03d}"
                try:
                    candidate = run_single_backend(
                        backend,
                        image,
                        candidates_dir / label,
                        profile=profile,
                        seed=seed_value,
                        model_root=args.model_root,
                    )
                    candidates.append((label, candidate.model_path))
                    print(
                        f"HAYUYA_CANDIDATE_READY {label} {candidate.model_path} "
                        f"source={image} seed={seed_value}"
                    )
                except Exception as exc:
                    failures[label] = f"{type(exc).__name__}: {exc}"
                    print(f"HAYUYA_CANDIDATE_FAILED {label}: {failures[label]}", file=sys.stderr)
                    traceback.print_exc()
                    if args.require_all:
                        raise

    if not candidates:
        manifest = {**plan, "status": "failed", "failures": failures}
        (job_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        raise SystemExit("All Hayuya candidates failed")

    normal_support_images = (
        {name: Path(path) for name, path in viewforge_result.normal_views.items()}
        if viewforge_result is not None
        else None
    )

    refinement_decision = None
    refinement_failure = None
    material_bridge_result = None
    material_bridge_failure = None
    should_try_refinement = (
        args.geometry_refine in {"auto", "required"}
        and args.profile in {"monster", "ultra"}
    )
    if should_try_refinement:
        triposf_ready = (args.model_root / "triposf").is_dir()
        enough_vram = args.gpu_vram is None or args.gpu_vram >= 12
        if args.geometry_refine == "required" and not triposf_ready:
            raise RuntimeError(
                "TripoSF refinement required but backend is not bootstrapped"
            )
        if args.geometry_refine == "required" and not enough_vram:
            raise RuntimeError(
                "TripoSF refinement required but VRAM budget is below 12GB"
            )

        if triposf_ready and enough_vram:
            try:
                preliminary = rank_candidates(
                    candidates,
                    mode=mode,
                    target_faces=profile.faces,
                    target_texture_size=profile.texture_size,
                    source_images=geometry_inputs,
                    visual_weight=0.55,
                    appearance_mode="off",
                    normal_support_images=normal_support_images,
                    normal_support_weight=0.06,
                )
                eligible = [
                    item for item in preliminary
                    if item.valid and item.visual_score is not None
                ]
                if not eligible:
                    raise RuntimeError("no valid geometry seed candidate for TripoSF")
                seed_candidate = max(
                    eligible,
                    key=lambda item: (
                        item.visual_score or 0.0,
                        item.production_score or 0.0,
                    ),
                )

                refine_root = job_dir / "refinement" / "triposf"
                refined_raw = REFINERS["triposf"](
                    Path(seed_candidate.path),
                    refine_root / "raw",
                    model_root=args.model_root,
                )

                from geometry_refinement import (
                    compare_refinement,
                    restore_refined_bounds,
                    write_decision,
                )

                restored = restore_refined_bounds(
                    Path(seed_candidate.path),
                    refined_raw.model_path,
                    refine_root / "triposf_refined_bounds_restored.glb",
                )
                refinement_decision = compare_refinement(
                    seed_candidate.backend,
                    Path(seed_candidate.path),
                    restored,
                    sources=geometry_inputs,
                    mode=mode,
                    target_faces=profile.faces,
                    normal_support_images=normal_support_images,
                )
                write_decision(
                    refine_root / "refinement_decision.json",
                    refinement_decision,
                )
                print(
                    "HAYUYA_REFINEMENT_READY "
                    f"source={seed_candidate.backend} "
                    f"preferred={refinement_decision.preferred} "
                    f"improvement={refinement_decision.improvement}"
                )

                if refinement_decision.promote_to_final_geometry:
                    try:
                        from material_bridge import transfer_best_material
                        bridged_path = (
                            refine_root / "triposf_material_bridge.glb"
                        )
                        material_bridge_result = transfer_best_material(
                            Path(seed_candidate.path),
                            restored,
                            bridged_path,
                            max_texture_size=profile.texture_size,
                        )
                        candidates.append(
                            ("triposf_material_bridge", bridged_path)
                        )
                        print(
                            "HAYUYA_MATERIAL_BRIDGE_READY "
                            f"{bridged_path}"
                        )
                    except Exception as bridge_exc:
                        material_bridge_failure = (
                            f"{type(bridge_exc).__name__}: {bridge_exc}"
                        )
                        print(
                            "HAYUYA_MATERIAL_BRIDGE_FAILED "
                            f"{material_bridge_failure}",
                            file=sys.stderr,
                        )
                        traceback.print_exc()
            except Exception as exc:
                refinement_failure = f"{type(exc).__name__}: {exc}"
                print(
                    f"HAYUYA_REFINEMENT_FAILED {refinement_failure}",
                    file=sys.stderr,
                )
                traceback.print_exc()
                if args.geometry_refine == "required":
                    raise

    ranking_pass = 0

    def run_full_ranking():
        nonlocal ranking_pass
        ranking_pass += 1
        result = rank_candidates(
            candidates,
            mode=mode,
            target_faces=profile.faces,
            target_texture_size=profile.texture_size,
            source_images=geometry_inputs,
            detail_images=detail_inputs,
            visual_weight=0.55,
            appearance_mode=args.appearance_judge,
            appearance_model_root=args.model_root,
            appearance_render_root=job_dir / "judge_v3_renders",
            appearance_weight=0.25,
            normal_support_images=normal_support_images,
            normal_support_weight=0.06,
        )
        for position, item in enumerate(result, start=1):
            print(
                "HAYUYA_JUDGE_SCORE "
                f"backend={item.backend} score={item.score:.3f} "
                f"valid={str(bool(item.valid)).lower()} rank={position} pass={ranking_pass}"
            )
            live_metrics = {
                "backend": item.backend,
                "production_score": item.production_score,
                "visual_score": item.visual_score,
                "appearance_score": item.appearance_score,
                "appearance_detail_score": item.appearance_detail_score,
                "appearance_face_detail_score": item.appearance_face_detail_score,
                "material_score": item.material_score,
                "texture_resolution_score": item.texture_resolution_score,
                "base_color_max_edge": item.base_color_max_edge,
                "base_color_min_edge": item.base_color_min_edge,
                "head_region_faces": item.head_region_faces,
                "head_region_vertices": item.head_region_vertices,
                "head_region_face_fraction": item.head_region_face_fraction,
                "global_median_edge_normalized": item.global_median_edge_normalized,
                "head_region_median_edge_normalized": item.head_region_median_edge_normalized,
                "head_region_density_ratio": item.head_region_density_ratio,
                "head_density_score": item.head_density_score,
                "head_texel_density_ratio": item.head_texel_density_ratio,
                "head_texel_density_score": item.head_texel_density_score,
                "pbr_channels": item.pbr_channels,
            }
            print(
                "HAYUYA_JUDGE_METRICS "
                + json.dumps(live_metrics,separators=(",",":"))
            )
        return result

    ranked = run_full_ranking()
    valid = [x for x in ranked if x.valid]
    if not valid:
        raise SystemExit("Candidates were produced but none passed Hayuya Judge")

    mesh_doctor_audit = None
    mesh_doctor_result = None
    mesh_doctor_failure = None
    mesh_doctor_status = "off" if args.mesh_doctor == "off" else "checking"

    if args.mesh_doctor in {"auto", "required"}:
        provisional = valid[0]
        provisional_path = Path(provisional.path)
        try:
            from mesh_doctor import audit_mesh, repair_candidate

            mesh_doctor_audit = audit_mesh(provisional_path)
            if not mesh_doctor_audit.valid:
                mesh_doctor_status = "audit_invalid"
                mesh_doctor_failure = "provisional champion failed Mesh Doctor audit"
                if args.mesh_doctor == "required":
                    raise RuntimeError(mesh_doctor_failure)
            else:
                boundary_repair_needed = bool(
                    mode in {"prop", "architecture"}
                    and mesh_doctor_audit.boundary_edges > 0
                    and not mesh_doctor_audit.watertight
                )
                repair_needed = bool(
                    mesh_doctor_audit.repair_recommended
                    or boundary_repair_needed
                )

                if not repair_needed:
                    mesh_doctor_status = "clean"
                    print(
                        "HAYUYA_MESH_DOCTOR_CLEAN "
                        f"defect_score={mesh_doctor_audit.defect_score:.3f}"
                    )
                    rigged = None
                else:
                    rigged = False

                if rigged is None:
                    pass
                else:
                    if provisional_path.suffix.lower() == ".glb":
                        try:
                            from gltf_audit import audit_glb
                            provisional_rig = audit_glb(provisional_path)
                            rigged = provisional_rig.skin_count > 0
                        except Exception:
                            rigged = False

                    if rigged:
                        mesh_doctor_status = "skipped_rigged"
                        mesh_doctor_failure = (
                            "structural repair needed but provisional champion is skinned; "
                            "topology-changing repair would invalidate JOINTS/WEIGHTS"
                        )
                        print(
                            f"HAYUYA_MESH_DOCTOR_SKIPPED {mesh_doctor_failure}",
                            file=sys.stderr,
                        )
                        if args.mesh_doctor == "required":
                            raise RuntimeError(mesh_doctor_failure)
                    else:
                        mesh_doctor_result = repair_candidate(
                            provisional_path,
                            job_dir / "mesh_doctor",
                            mode=mode,
                            texture_size=profile.texture_size,
                        )
                        if mesh_doctor_result.safe_for_arena:
                            candidates.append(
                                ("mesh_doctor_repair", Path(mesh_doctor_result.bridged_glb))
                            )
                            mesh_doctor_status = "candidate_ready"
                            print(
                                "HAYUYA_MESH_DOCTOR_READY "
                                f"defects={mesh_doctor_result.before.defect_score:.3f}->"
                                f"{mesh_doctor_result.after.defect_score:.3f} "
                                f"drift={mesh_doctor_result.vertex_surface_drift_normalized:.6f}"
                            )
                            ranked = run_full_ranking()
                            valid = [x for x in ranked if x.valid]
                            if not valid:
                                raise RuntimeError(
                                    "Mesh Doctor re-ranking produced no valid candidates"
                                )
                        else:
                            mesh_doctor_status = "rejected_unsafe"
                            mesh_doctor_failure = "; ".join(mesh_doctor_result.reasons)
                            print(
                                f"HAYUYA_MESH_DOCTOR_REJECTED {mesh_doctor_failure}",
                                file=sys.stderr,
                            )
                            if args.mesh_doctor == "required":
                                raise RuntimeError(mesh_doctor_failure)
        except Exception as exc:
            if mesh_doctor_status not in {"skipped_rigged", "rejected_unsafe", "audit_invalid"}:
                mesh_doctor_status = "failed"
                mesh_doctor_failure = f"{type(exc).__name__}: {exc}"
                print(
                    f"HAYUYA_MESH_DOCTOR_FAILED {mesh_doctor_failure}",
                    file=sys.stderr,
                )
                traceback.print_exc()
            if args.mesh_doctor == "required":
                raise

    retopo_result = None
    retopo_failure = None
    retopo_status = "off" if args.retopo == "off" else "checking"

    if args.retopo in {"auto", "required"}:
        provisional = valid[0]
        provisional_path = Path(provisional.path)
        rigged = False
        rig_reason = None

        if provisional_path.suffix.lower() == ".glb":
            try:
                from gltf_audit import audit_glb
                provisional_rig = audit_glb(provisional_path)
                rigged = provisional_rig.skin_count > 0
                if rigged:
                    rig_reason = (
                        f"provisional champion has {provisional_rig.skin_count} glTF skin(s); "
                        "retopology would destroy JOINTS/WEIGHTS"
                    )
            except Exception as exc:
                rig_reason = f"rig audit unavailable: {type(exc).__name__}: {exc}"

        if rigged:
            retopo_status = "skipped_rigged"
            retopo_failure = rig_reason
            print(f"HAYUYA_RETOPO_SKIPPED {rig_reason}", file=sys.stderr)
            if args.retopo == "required":
                raise RuntimeError(rig_reason)
        else:
            try:
                from retopo import retopo_readiness, run_retopology

                ready, missing = retopo_readiness(args.model_root)
                if not ready:
                    retopo_status = "skipped_unavailable"
                    retopo_failure = "; ".join(missing)
                    print(
                        f"HAYUYA_RETOPO_SKIPPED {retopo_failure}",
                        file=sys.stderr,
                    )
                    if args.retopo == "required":
                        raise RuntimeError(retopo_failure)
                else:
                    source_faces = int(provisional.faces or profile.faces)
                    target_runtime_faces = max(
                        200,
                        min(profile.faces, source_faces),
                    )
                    style = (
                        "quad_dominant"
                        if mode == "character"
                        else "pure_quad"
                    )
                    retopo_result = run_retopology(
                        provisional_path,
                        job_dir / "retopo",
                        target_triangle_faces=target_runtime_faces,
                        style=style,
                        texture_size=profile.texture_size,
                        model_root=args.model_root,
                    )
                    candidates.append(
                        ("instant_meshes_retopo", Path(retopo_result.bridged_glb))
                    )
                    retopo_status = "candidate_ready"
                    print(
                        "HAYUYA_RETOPO_READY "
                        f"style={retopo_result.style} "
                        f"quad_fraction={retopo_result.quad_fraction:.4f} "
                        f"obj={retopo_result.retopo_obj}"
                    )

                    # The retopologized/PBR-restored asset earns nothing for merely
                    # existing. Re-run exactly the same real-source Judge arena.
                    ranked = run_full_ranking()
                    valid = [x for x in ranked if x.valid]
                    if not valid:
                        raise RuntimeError("retopo re-ranking produced no valid candidates")
            except Exception as exc:
                if retopo_status != "skipped_unavailable":
                    retopo_status = "failed"
                    retopo_failure = f"{type(exc).__name__}: {exc}"
                    print(
                        f"HAYUYA_RETOPO_FAILED {retopo_failure}",
                        file=sys.stderr,
                    )
                    traceback.print_exc()
                if args.retopo == "required":
                    raise

    texture_superres_result = None
    texture_superres_failure = None
    texture_superres_status = (
        "off" if args.texture_superres == "off" else "checking"
    )

    if args.texture_superres in {"auto", "required"}:
        provisional = valid[0]
        provisional_edge = int(provisional.base_color_min_edge or 0)
        if args.profile not in {"monster", "ultra"}:
            texture_superres_status = "skipped_profile"
        elif provisional_edge <= 0:
            texture_superres_status = "skipped_no_basecolor"
            texture_superres_failure = (
                "provisional champion has no embedded visible baseColor texture"
            )
            print(
                f"HAYUYA_TEXTURE_SUPERRES_SKIPPED {texture_superres_failure}",
                file=sys.stderr,
            )
            if args.texture_superres == "required":
                raise RuntimeError(texture_superres_failure)
        elif not needs_texture_superres(
            args.profile,
            provisional_edge,
            profile.texture_size,
        ):
            texture_superres_status = "already_at_target"
            print(
                "HAYUYA_TEXTURE_SUPERRES_CLEAN "
                f"basecolor={provisional_edge} target={profile.texture_size}"
            )
        else:
            try:
                from texture_superres import superresolve_basecolor_glb

                sr_dir = job_dir / "texture_superres"
                sr_output = sr_dir / (
                    f"{provisional.backend}_basecolor_{profile.texture_size}.glb"
                )
                texture_superres_result = superresolve_basecolor_glb(
                    Path(provisional.path),
                    sr_output,
                    target_edge=profile.texture_size,
                    auto_install=True,
                )
                if texture_superres_result.ready:
                    sr_label = f"{provisional.backend}_texture_sr"
                    candidates.append(
                        (sr_label, Path(texture_superres_result.output_glb))
                    )
                    texture_superres_status = "candidate_ready"
                    print(
                        "HAYUYA_TEXTURE_SUPERRES_READY "
                        f"source={provisional.backend} candidate={sr_label} "
                        f"basecolor={provisional_edge}->{profile.texture_size} "
                        f"items={len(texture_superres_result.items)}"
                    )
                    print(
                        "HAYUYA_CANDIDATE_READY "
                        f"{sr_label} {texture_superres_result.output_glb} "
                        "source=texture_superres"
                    )
                    # Super-resolution earns nothing merely for reaching 4K.
                    # It must survive the same full real-source Judge arena.
                    ranked = run_full_ranking()
                    valid = [x for x in ranked if x.valid]
                    if not valid:
                        raise RuntimeError(
                            "texture super-resolution re-ranking produced no valid candidates"
                        )
                else:
                    texture_superres_failure = (
                        texture_superres_result.error
                        or texture_superres_result.method
                    )
                    texture_superres_status = (
                        "skipped_unavailable"
                        if texture_superres_result.method == "realesrgan_unavailable"
                        else "rejected"
                    )
                    print(
                        "HAYUYA_TEXTURE_SUPERRES_SKIPPED "
                        f"{texture_superres_failure}",
                        file=sys.stderr,
                    )
                    if args.texture_superres == "required":
                        raise RuntimeError(texture_superres_failure)
            except Exception as exc:
                if texture_superres_status != "skipped_unavailable":
                    texture_superres_status = "failed"
                    texture_superres_failure = f"{type(exc).__name__}: {exc}"
                    print(
                        f"HAYUYA_TEXTURE_SUPERRES_FAILED {texture_superres_failure}",
                        file=sys.stderr,
                    )
                    traceback.print_exc()
                if args.texture_superres == "required":
                    raise

    ranking_data = [asdict(x) for x in ranked]
    (job_dir / "ranking.json").write_text(
        json.dumps(ranking_data, indent=2) + "\n",
        encoding="utf-8",
    )

    champion = valid[0]
    source = Path(champion.path)
    final_glb = export_glb(source, job_dir / "hayuya_final.glb")

    gameprep_result = None
    gameprep_failure = None
    should_try_gameprep = (
        args.gameprep in {"auto", "required"}
        and args.profile in {"mobile", "game", "monster", "ultra"}
    )
    if should_try_gameprep:
        try:
            from gameprep import build_gameprep
            from visual_judge import SourceViewScore

            anchor_view = None
            if champion.visual_views:
                anchor_view = SourceViewScore(**champion.visual_views[0])

            gameprep_result = build_gameprep(
                final_glb,
                job_dir / "gameprep",
                target_faces=min(profile.faces, portable_lod0_ceiling),
                anchor_view=anchor_view,
                material_samples=(
                    80000 if args.profile == "mobile"
                    else 120000 if args.profile == "game"
                    else 180000
                ),
                max_texture_size=portable_texture_ceiling,
            )
            print(
                "HAYUYA_GAMEPREP_READY "
                f"lods={len(gameprep_result.lods)} "
                f"collision={bool(gameprep_result.collision)} "
                f"turntable={len(gameprep_result.turntable_frames)}"
            )
        except Exception as exc:
            gameprep_failure = f"{type(exc).__name__}: {exc}"
            print(
                f"HAYUYA_GAMEPREP_FAILED {gameprep_failure}",
                file=sys.stderr,
            )
            traceback.print_exc()
            if args.gameprep == "required":
                raise

    portable_pack_result = None
    portable_pack_failure = None
    should_try_portable_pack = (
        args.portable_pack in {"auto", "required"}
        and args.profile in {"mobile", "game", "monster", "ultra"}
    )
    if should_try_portable_pack:
        try:
            from portable_pack import build_portable_pack
            from visual_judge import SourceViewScore

            portable_anchor = None
            if champion.visual_views:
                portable_anchor = SourceViewScore(**champion.visual_views[0])

            portable_pack_result = build_portable_pack(
                final_glb,
                job_dir / "portable",
                mode=mode,
                profile_name=args.profile,
                anchor_view=portable_anchor,
                material_samples=(
                    80000 if args.profile == "mobile"
                    else 120000 if args.profile == "game"
                    else 180000
                ),
                texture_delivery_mode=args.texture_delivery,
            )
            print(
                "HAYUYA_PORTABLE_PACK_READY "
                f"tiers={len(portable_pack_result.tiers)} "
                f"complete_lods={portable_pack_result.complete_lod_chain} "
                f"manifest={portable_pack_result.manifest}"
            )
        except Exception as exc:
            portable_pack_failure = f"{type(exc).__name__}: {exc}"
            print(
                f"HAYUYA_PORTABLE_PACK_FAILED {portable_pack_failure}",
                file=sys.stderr,
            )
            traceback.print_exc()
            if args.portable_pack == "required":
                raise

    qa_package_result = None
    qa_package_failure = None
    try:
        from qa_package import build_qa_package

        qa_package_result = build_qa_package(
            final_glb,
            job_dir / "qa",
            champion=champion,
            mode=mode,
            profile=args.profile,
            source_images=geometry_inputs,
            detail_images=detail_inputs,
            gameprep=gameprep_result,
            target_faces=profile.faces,
            target_texture_size=profile.texture_size,
        )
        print(
            "HAYUYA_QA_READY "
            f"production_ready={qa_package_result.production_ready} "
            f"material_ready={qa_package_result.material_ready} "
            f"texture_ready={qa_package_result.texture_resolution_ready} "
            f"texture_score={qa_package_result.texture_resolution_score if qa_package_result.texture_resolution_score is not None else 'none'} "
            f"basecolor_min={qa_package_result.base_color_min_edge} "
            f"basecolor_max={qa_package_result.base_color_max_edge} "
            f"texture_target={qa_package_result.target_texture_size if qa_package_result.target_texture_size is not None else 'none'} "
            f"rebake_ready={qa_package_result.material_rebake_ready} "
            f"rebaked={','.join(qa_package_result.material_rebaked_channels) if qa_package_result.material_rebaked_channels else 'none'} "
            f"rebake_pending={','.join(qa_package_result.material_rebake_pending_channels) if qa_package_result.material_rebake_pending_channels else 'none'} "
            f"rig_ready={qa_package_result.rig_ready} "
            f"animation_ready={qa_package_result.animation_ready} "
            f"face_ready={qa_package_result.face_evidence_ready} "
            f"face_score={qa_package_result.face_evidence_score if qa_package_result.face_evidence_score is not None else 'none'} "
            f"facemesh_score={qa_package_result.head_density_score if qa_package_result.head_density_score is not None else 'none'} "
            f"facetex_score={qa_package_result.head_texel_density_score if qa_package_result.head_texel_density_score is not None else 'none'} "
            f"report={qa_package_result.report}"
        )
    except Exception as exc:
        qa_package_failure = f"{type(exc).__name__}: {exc}"
        print(f"HAYUYA_QA_FAILED {qa_package_failure}", file=sys.stderr)
        traceback.print_exc()

    manifest = {
        **plan,
        "status": "success",
        "failures": failures,
        "viewforge": asdict(viewforge_result) if viewforge_result is not None else None,
        "viewforge_failure": viewforge_failure,
        "character_specialist": {
            "status": character_specialist_status,
            "failure": character_specialist_failure,
        },
        "mesh_doctor": {
            "status": mesh_doctor_status,
            "audit": asdict(mesh_doctor_audit) if mesh_doctor_audit is not None else None,
            "result": asdict(mesh_doctor_result) if mesh_doctor_result is not None else None,
            "failure": mesh_doctor_failure,
            "won_final_arena": champion.backend == "mesh_doctor_repair",
        },
        "retopology": {
            "status": retopo_status,
            "result": asdict(retopo_result) if retopo_result is not None else None,
            "failure": retopo_failure,
            "won_final_arena": champion.backend == "instant_meshes_retopo",
        },
        "texture_superres": {
            "mode": args.texture_superres,
            "status": texture_superres_status,
            "result": (
                asdict(texture_superres_result)
                if texture_superres_result is not None else None
            ),
            "failure": texture_superres_failure,
            "won_final_arena": champion.backend.endswith("_texture_sr"),
            "policy": "baseColor-only GLB payload rewrite; original candidate preserved; challenger must win complete Judge",
        },
        "geometry_refinement": asdict(refinement_decision) if refinement_decision is not None else None,
        "geometry_refinement_failure": refinement_failure,
        "material_bridge": asdict(material_bridge_result) if material_bridge_result is not None else None,
        "material_bridge_failure": material_bridge_failure,
        "ranking": ranking_data,
        "champion": asdict(champion),
        "final_glb": str(final_glb),
        "gameprep": asdict(gameprep_result) if gameprep_result is not None else None,
        "gameprep_failure": gameprep_failure,
        "portable_pack": asdict(portable_pack_result) if portable_pack_result is not None else None,
        "portable_pack_failure": portable_pack_failure,
        "qa_package": asdict(qa_package_result) if qa_package_result is not None else None,
        "qa_package_failure": qa_package_failure,
        "notes": [
            "The reference pool has no Hayuya-level photo-count cap.",
            "All unique full-object/geometry source photos participate in Judge v2.",
            "Detail/close-up sources stay out of whole-object silhouette scoring but enter Judge v3 through multi-view local patch retrieval when DINOv2 is active.",
            "Multi-image backends receive grouped real geometry references when one call should be bounded for VRAM/practicality.",
            "Monster/Ultra multi-anchor mode can generate TripoSG hypotheses from every source unless the user explicitly sets a budget.",
            "A one-photo job can add a TRELLIS fusion candidate from the real anchor plus Wonder3D RGB/normal ViewForge coverage; synthetic RGB views never enter the real-source Judge.",
            "Wonder3D normal maps may contribute a deliberately small 6% synthetic-support score using the pinned front-view normal coordinate convention.",
            "TripoSF can challenge the best geometry seed at 1024^3 in Monster/Ultra; it must pass real-source geometry evidence.",
            "If TripoSF wins geometry, Material Bridge v2 reprojects packed PBR UV/material evidence when available (base-color fallback otherwise) and the bridged GLB re-enters the final Judge rather than being auto-promoted.",
            "Mesh Doctor audits the provisional champion before retopology; conservative structural repairs are material-restored and must win the same Judge, while tiny disconnected components are audit-only to protect intentional accessories.",
            "Instant Meshes retopology is an optional deterministic challenger: editable quad/quad-dominant OBJ is preserved, Material Bridge v2 restores runtime material evidence, and the bridged GLB must win the same Judge.",
            "Monster/Ultra may add one Real-ESRGAN baseColor-only super-resolution challenger when the provisional champion is below the native texture target; geometry/skin/animation buffers are preserved and the refined GLB must win the complete Judge.",
            "GamePrep audits glTF rig/skin state first; skinned assets skip destructive retopology/LOD simplification and preserve exact master/LOD0 until skin-weight transfer exists.",
            "QA Package v1 records geometry/material/reference/rig/GamePrep readiness and creates a source-vs-turntable contact sheet.",
            "Mobile portability is resolved from the versioned HAYUYA knowledge base; the source-faithful Hero Master is preserved while GamePrep derives tier-budget LODs and texture ceilings.",
            "Portable Pack derives Flagship, High, Balanced and Compatibility independently from the same Hero Master; lower tiers never become the source for higher tiers.",
            "Judge v2 combines production mesh health with source-image silhouette agreement.",
            "Judge v3 auto adds DINOv2 appearance similarity when the pinned evaluator is bootstrapped; otherwise it falls back to v2.",
            "Next judge stage adds normal/depth agreement, calibrated camera estimation and local-detail matching.",
        ],
    }
    (job_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"HAYUYA_MONSTER_READY {final_glb}")
    print(
        f"HAYUYA_CHAMPION backend={champion.backend} score={champion.score} "
        f"references={len(inputs)} geometry_refs={len(geometry_inputs)} "
        f"detail_refs={len(detail_inputs)} candidates={len(candidates)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
