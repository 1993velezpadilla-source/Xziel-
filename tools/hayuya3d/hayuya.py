#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
import traceback
from dataclasses import asdict, dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

from adapters import DEFAULT_MODEL_ROOT, GENERATORS
from qa import export_glb, rank_candidates


@dataclass(frozen=True)
class Profile:
    faces: int
    texture_size: int
    trellis2_resolution: int
    backends: tuple[str, ...]
    dual_anchor: bool


PROFILES = {
    "preview": Profile(
        faces=30_000,
        texture_size=1024,
        trellis2_resolution=512,
        backends=("triposr", "triposg"),
        dual_anchor=False,
    ),
    "mobile": Profile(
        faces=35_000,
        texture_size=2048,
        trellis2_resolution=512,
        backends=("trellis", "triposg", "triposr"),
        dual_anchor=False,
    ),
    "game": Profile(
        faces=80_000,
        texture_size=2048,
        trellis2_resolution=1024,
        backends=("triposg", "trellis", "instantmesh", "triposr"),
        dual_anchor=True,
    ),
    "monster": Profile(
        faces=250_000,
        texture_size=4096,
        trellis2_resolution=1024,
        backends=("trellis2", "triposg", "trellis", "instantmesh", "triposr"),
        dual_anchor=True,
    ),
    "ultra": Profile(
        faces=500_000,
        texture_size=4096,
        trellis2_resolution=1536,
        backends=("trellis2", "triposg", "trellis", "instantmesh", "triposr"),
        dual_anchor=True,
    ),
}


def load_lock() -> dict:
    return json.loads((HERE / "backends.lock.json").read_text(encoding="utf-8"))


def backend_meta(lock: dict) -> dict[str, dict]:
    return {x["id"]: x for x in lock["backends"]}


def validate_inputs(inputs: list[Path]) -> list[Path]:
    if not 1 <= len(inputs) <= 2:
        raise ValueError("Hayuya Monster accepts exactly 1 or 2 source photos")
    out: list[Path] = []
    for p in inputs:
        p = p.resolve()
        if not p.is_file():
            raise FileNotFoundError(p)
        if p.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            raise ValueError(f"unsupported image format: {p}")
        if p.stat().st_size < 512:
            raise ValueError(f"image is unexpectedly small: {p}")
        out.append(p)
    return out


def make_job_plan(
    inputs: list[Path],
    *,
    profile_name: str,
    mode: str,
    seed: int,
    selected_backends: list[str],
    model_root: Path,
) -> dict:
    profile = PROFILES[profile_name]
    return {
        "engine": "HAYUYA MONSTER",
        "schema": 1,
        "inputs": [str(p) for p in inputs],
        "input_count": len(inputs),
        "mode": mode,
        "profile": profile_name,
        "seed": seed,
        "targets": {
            "faces": profile.faces,
            "texture_size": profile.texture_size,
            "trellis2_resolution": profile.trellis2_resolution,
        },
        "viewforge": {
            "strategy": (
                "single-photo: synthesize canonical sparse views with open-source multiview priors"
                if len(inputs) == 1
                else "two-photo anchor fusion: preserve both views and synthesize only missing coverage"
            ),
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
        },
        "candidate_backends": selected_backends,
        "dual_anchor": bool(profile.dual_anchor and len(inputs) == 2),
        "judge": {
            "version": "v2",
            "production_subscore": {
                "geometry_capacity_weight": 0.42,
                "topology_health_weight": 0.33,
                "material_readiness_weight": 0.18,
                "bbox_health_weight": 0.07
            },
            "final_mix": {
                "source_visual_weight": 0.55,
                "production_weight": 0.45
            },
            "source_visual": {
                "method": "software silhouette camera search",
                "azimuth_step_degrees": 30,
                "elevations_degrees": [-15, 0, 15],
                "up_axis_hypotheses": ["y", "z"],
                "per_source_metric": "0.72 silhouette IoU + 0.28 boundary F1",
                "multi_source_aggregation": "0.70 mean + 0.30 minimum"
            },
            "future_extension": "DINO/MEt3R feature consistency + RGB/normal/depth rerender scoring"
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


def run_backend(
    backend: str,
    inputs: list[Path],
    out_dir: Path,
    *,
    profile: Profile,
    seed: int,
    model_root: Path,
):
    if backend == "trellis":
        return GENERATORS[backend](
            inputs,
            out_dir,
            seed=seed,
            texture_size=profile.texture_size,
            model_root=model_root,
        )
    if backend == "trellis2":
        return GENERATORS[backend](
            inputs[0],
            out_dir,
            seed=seed,
            resolution=profile.trellis2_resolution,
            faces=profile.faces,
            texture_size=profile.texture_size,
            model_root=model_root,
        )
    if backend == "triposg":
        return GENERATORS[backend](
            inputs[0],
            out_dir,
            faces=profile.faces,
            seed=seed,
            model_root=model_root,
        )
    if backend == "triposr":
        return GENERATORS[backend](
            inputs[0],
            out_dir,
            texture_size=profile.texture_size,
            model_root=model_root,
        )
    if backend == "instantmesh":
        return GENERATORS[backend](
            inputs[0],
            out_dir,
            seed=seed,
            model_root=model_root,
        )
    if backend == "spar3d":
        return GENERATORS[backend](
            inputs[0],
            out_dir,
            texture_size=profile.texture_size,
            faces=profile.faces,
            model_root=model_root,
        )
    raise ValueError(f"unsupported executable backend: {backend}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HAYUYA MONSTER: open ensemble image-to-3D orchestrator for 1-2 photos."
    )
    parser.add_argument("--input", type=Path, action="append", required=True, help="1 or 2 source images")
    parser.add_argument("--profile", choices=sorted(PROFILES), default="monster")
    parser.add_argument("--mode", choices=["auto", "prop", "character", "architecture"], default="auto")
    parser.add_argument("--seed", type=int, default=1993)
    parser.add_argument("--backends", help="comma-separated override")
    parser.add_argument("--gpu-vram", type=int, help="VRAM budget in GB; skips larger backends")
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODEL_ROOT)
    parser.add_argument("--output-root", type=Path, default=ROOT / "out" / "hayuya3d")
    parser.add_argument("--execute", action="store_true", help="actually run installed backends")
    parser.add_argument("--require-all", action="store_true", help="fail if any selected backend fails")
    parser.add_argument("--allow-restricted", action="store_true", help="allow explicitly opt-in non-permissive backends")
    args = parser.parse_args()

    inputs = validate_inputs(args.input)
    profile = PROFILES[args.profile]
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
        mode = "character" if "character" in inputs[0].stem.lower() else "prop"

    job_name = f"{inputs[0].stem}-{args.profile}-{args.seed}"
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
    )
    (job_dir / "plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(plan, indent=2))

    if not args.execute:
        print(f"HAYUYA_PLAN_READY {job_dir / 'plan.json'}")
        return 0

    candidates: list[tuple[str, Path]] = []
    failures: dict[str, str] = {}

    for backend in selected:
        out_dir = candidates_dir / backend
        try:
            candidate = run_backend(
                backend,
                inputs,
                out_dir,
                profile=profile,
                seed=args.seed,
                model_root=args.model_root,
            )
            candidates.append((candidate.backend, candidate.model_path))
            print(f"HAYUYA_CANDIDATE_READY {candidate.backend} {candidate.model_path}")
        except Exception as exc:
            failures[backend] = f"{type(exc).__name__}: {exc}"
            print(f"HAYUYA_CANDIDATE_FAILED {backend}: {failures[backend]}", file=sys.stderr)
            traceback.print_exc()
            if args.require_all:
                raise

    # With two anchors, generate a second independent TripoSG geometry hypothesis.
    if profile.dual_anchor and len(inputs) == 2 and "triposg" in selected:
        label = "triposg_anchor2"
        try:
            candidate = GENERATORS["triposg"](
                inputs[1],
                candidates_dir / label,
                faces=profile.faces,
                seed=args.seed + 1,
                model_root=args.model_root,
            )
            candidates.append((label, candidate.model_path))
            print(f"HAYUYA_CANDIDATE_READY {label} {candidate.model_path}")
        except Exception as exc:
            failures[label] = f"{type(exc).__name__}: {exc}"
            print(f"HAYUYA_CANDIDATE_FAILED {label}: {failures[label]}", file=sys.stderr)
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
        source_images=inputs,
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
            "Judge v2 combines production mesh health with source-image silhouette agreement.",
            "Every real source photo contributes to the visual score; the weakest anchor explicitly drags the final score down.",
            "Next judge stage adds DINO/MEt3R RGB feature consistency plus normal/depth agreement.",
            "Two-photo jobs already use both anchors natively through TRELLIS multi-image and an independent secondary TripoSG hypothesis.",
        ],
    }
    (job_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"HAYUYA_MONSTER_READY {final_glb}")
    print(f"HAYUYA_CHAMPION backend={champion.backend} score={champion.score}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
