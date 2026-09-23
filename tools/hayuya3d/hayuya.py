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

from adapters import DEFAULT_MODEL_ROOT, GENERATORS
from qa import export_glb, rank_candidates
from reference_pool import order_for_multiview_coverage, split_reference_roles


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
) -> dict:
    profile = PROFILES[profile_name]
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
        "seed": seed,
        "targets": {
            "faces": profile.faces,
            "texture_size": profile.texture_size,
            "trellis2_resolution": profile.trellis2_resolution,
        },
        "viewforge": {
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
        },
        "candidate_backends": selected_backends,
        "judge": {
            "version": "v2",
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
                "method": "software silhouette camera search",
                "azimuth_step_degrees": 30,
                "elevations_degrees": [-15, 0, 15],
                "up_axis_hypotheses": ["y", "z"],
                "per_source_metric": "0.72 silhouette IoU + 0.28 boundary F1",
                "multi_source_aggregation": "<=2: 0.70 mean + 0.30 min; >=3: 0.65 mean + 0.25 lower-quartile mean + 0.10 min",
                "evaluate_every_geometry_source": True,
            },
            "future_extension": "DINO/MEt3R feature consistency + RGB/normal/depth rerender scoring",
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
    parser.add_argument("--mode", choices=["auto", "prop", "character", "architecture"], default="auto")
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
        mode = "character" if "character" in geometry_inputs[0].stem.lower() else "prop"

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
    )
    (job_dir / "plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(plan, indent=2))

    if not args.execute:
        print(f"HAYUYA_PLAN_READY {job_dir / 'plan.json'}")
        return 0

    candidates: list[tuple[str, Path]] = []
    failures: dict[str, str] = {}

    for backend in selected:
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
            continue

        # Expensive single-image backends run once from the primary source.
        # TripoSG is special in multi-anchor profiles: by default every real source
        # can produce an independent geometry hypothesis, with an explicit CLI budget
        # available when compute needs to be bounded.
        run_refs = anchor_refs if backend == "triposg" and profile.multi_anchor else [geometry_inputs[0]]
        for anchor_index, image in enumerate(run_refs, start=1):
            label = backend if len(run_refs) == 1 else f"{backend}_anchor{anchor_index:03d}"
            try:
                candidate = run_single_backend(
                    backend,
                    image,
                    candidates_dir / label,
                    profile=profile,
                    seed=args.seed + anchor_index - 1,
                    model_root=args.model_root,
                )
                candidates.append((label, candidate.model_path))
                print(
                    f"HAYUYA_CANDIDATE_READY {label} {candidate.model_path} "
                    f"source={image}"
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

    ranked = rank_candidates(
        candidates,
        mode=mode,
        target_faces=profile.faces,
        source_images=geometry_inputs,
        visual_weight=0.55,
    )
    ranking_data = [asdict(x) for x in ranked]
    (job_dir / "ranking.json").write_text(json.dumps(ranking_data, indent=2) + "\n", encoding="utf-8")

    valid = [x for x in ranked if x.valid]
    if not valid:
        raise SystemExit("Candidates were produced but none passed Hayuya Judge")

    champion = valid[0]
    source = Path(champion.path)
    final_glb = export_glb(source, job_dir / "hayuya_final.glb")

    manifest = {
        **plan,
        "status": "success",
        "failures": failures,
        "ranking": ranking_data,
        "champion": asdict(champion),
        "final_glb": str(final_glb),
        "notes": [
            "The reference pool has no Hayuya-level photo-count cap.",
            "All unique full-object/geometry source photos participate in Judge v2.",
            "Detail/close-up sources remain in the reference pool for material and local-detail stages instead of being misused as whole-object silhouettes.",
            "Multi-image backends receive grouped real geometry references when one call should be bounded for VRAM/practicality.",
            "Monster/Ultra multi-anchor mode can generate TripoSG hypotheses from every source unless the user explicitly sets a budget.",
            "Judge v2 combines production mesh health with source-image silhouette agreement.",
            "Next judge stage adds DINO/MEt3R RGB feature consistency plus normal/depth agreement.",
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
