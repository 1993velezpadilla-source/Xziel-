#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from judge_v4_face_worker import _crop_top_subject, _ensure_model


@dataclass
class SourceAutofixItem:
    source: str
    face_detail: str | None
    method: str
    direct_face_detected: bool
    used_zoom_probe: bool
    face_box_fraction: float | None
    source_size: list[int]
    output_size: list[int] | None
    warning: str | None = None


@dataclass
class SourceAutofixReport:
    schema: int
    ready: bool
    sources: list[SourceAutofixItem]
    derived_detail_sources: list[str]
    real_sources_preserved: bool
    derived_sources_are_not_independent_references: bool
    policy: str
    manifest: str


def _face_crop_from_landmarks(image: Image.Image, landmarks, output_edge: int = 1024):
    w, h = image.size
    xs = [float(p.x) for p in landmarks]
    ys = [float(p.y) for p in landmarks]
    x0 = max(0.0, min(xs))
    x1 = min(1.0, max(xs))
    y0 = max(0.0, min(ys))
    y1 = min(1.0, max(ys))
    bw = max(1.0, (x1 - x0) * w)
    bh = max(1.0, (y1 - y0) * h)
    cx = ((x0 + x1) * 0.5) * w
    cy = ((y0 + y1) * 0.5) * h

    # Include cranium, chin, and a little context. This is a crop/zoom only:
    # no generative face restoration that could invent identity.
    side = max(bw * 1.85, bh * 1.65, 48.0)
    left = max(0, int(round(cx - side * 0.5)))
    top = max(0, int(round(cy - side * 0.52)))
    right = min(w, int(round(cx + side * 0.5)))
    bottom = min(h, int(round(cy + side * 0.48)))
    crop = image.crop((left, top, right, bottom)).convert("RGB")
    crop = ImageOps.pad(
        crop,
        (output_edge, output_edge),
        method=Image.Resampling.LANCZOS,
        color=(0, 0, 0),
        centering=(0.5, 0.5),
    )
    frac = ((x1 - x0) * (y1 - y0))
    return crop, float(frac)


def _mediapipe_face(source: Path, out_path: Path, cache_path: Path):
    import mediapipe as mp

    model_path = _ensure_model(cache_path)
    options = mp.tasks.vision.FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
        running_mode=mp.tasks.vision.RunningMode.IMAGE,
        num_faces=1,
        min_face_detection_confidence=0.30,
        min_face_presence_confidence=0.30,
        output_face_blendshapes=False,
    )

    original = Image.open(source).convert("RGB")
    attempts = [
        ("direct", original),
        ("zoom_probe", _crop_top_subject(original)),
    ]
    with mp.tasks.vision.FaceLandmarker.create_from_options(options) as detector:
        for label, pil in attempts:
            arr = np.asarray(pil, dtype=np.uint8)
            result = detector.detect(
                mp.Image(image_format=mp.ImageFormat.SRGB, data=arr)
            )
            if not result.face_landmarks:
                continue
            crop, frac = _face_crop_from_landmarks(pil, result.face_landmarks[0])
            out_path.parent.mkdir(parents=True, exist_ok=True)
            crop.save(out_path, optimize=True)
            return {
                "face_detail": str(out_path),
                "method": "mediapipe_face_landmarker_direct" if label == "direct" else "mediapipe_face_landmarker_zoom_probe",
                "direct_face_detected": label == "direct",
                "used_zoom_probe": label != "direct",
                "face_box_fraction": round(frac, 8),
                "output_size": [crop.width, crop.height],
            }
    return None


def _grounded_head_fallback(source: Path, out_path: Path, work_dir: Path):
    # Reuse HAYUYA's existing GroundingDINO + SAM2 detector. This only runs
    # when MediaPipe could not recover a face from the original or zoom probe.
    if any(importlib.util.find_spec(name) is None for name in ("torch", "transformers")):
        return None

    work_dir.mkdir(parents=True, exist_ok=True)
    plan_path = work_dir / "head_plan.json"
    detect_dir = work_dir / "grounded"
    plan = {
        "schema": 1,
        "asset_profile": "character.humanoid",
        "weapon_family": "auto",
        "required": ["head"],
        "optional": ["body"],
        "prompts": {
            "head": ["human head", "face"],
            "body": ["human body", "person"],
        },
    }
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    script = Path(__file__).resolve().parent / "semantic_part_detector.py"
    cmd = [
        sys.executable,
        str(script),
        "--image", str(source),
        "--plan", str(plan_path),
        "--out", str(detect_dir),
        "--box-threshold", "0.20",
        "--text-threshold", "0.16",
    ]
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    report_path = detect_dir / "semantic_parts.json"
    if proc.returncode != 0 or not report_path.is_file():
        return None
    report = json.loads(report_path.read_text(encoding="utf-8"))
    head = next(
        (x for x in report.get("detections", []) if x.get("part") == "head"),
        None,
    )
    if not head:
        return None

    image = Image.open(source).convert("RGB")
    w, h = image.size
    x0, y0, x1, y1 = [float(x) for x in head["box_xyxy"]]
    bw = max(1.0, x1 - x0)
    bh = max(1.0, y1 - y0)
    cx = (x0 + x1) * 0.5
    cy = (y0 + y1) * 0.5
    side = max(bw * 1.35, bh * 1.25, 48.0)
    left = max(0, int(round(cx - side * 0.5)))
    top = max(0, int(round(cy - side * 0.52)))
    right = min(w, int(round(cx + side * 0.5)))
    bottom = min(h, int(round(cy + side * 0.48)))
    crop = image.crop((left, top, right, bottom))
    crop = ImageOps.pad(
        crop,
        (1024, 1024),
        method=Image.Resampling.LANCZOS,
        color=(0, 0, 0),
        centering=(0.5, 0.5),
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    crop.save(out_path, optimize=True)
    frac = (bw * bh) / float(max(1, w * h))
    return {
        "face_detail": str(out_path),
        "method": "groundingdino_sam2_head_fallback",
        "direct_face_detected": False,
        "used_zoom_probe": True,
        "face_box_fraction": round(frac, 8),
        "output_size": [crop.width, crop.height],
    }


def build_source_autofix(
    sources: list[Path],
    out_dir: Path,
    *,
    policy: str = "auto",
    cache_path: Path | None = None,
) -> SourceAutofixReport:
    policy = str(policy).lower()
    if policy not in {"off", "auto", "required"}:
        raise ValueError("source autofix policy must be off, auto, or required")

    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "source_autofix.json"
    if policy == "off":
        report = SourceAutofixReport(
            schema=1,
            ready=True,
            sources=[],
            derived_detail_sources=[],
            real_sources_preserved=True,
            derived_sources_are_not_independent_references=True,
            policy=policy,
            manifest=str(manifest_path),
        )
        manifest_path.write_text(json.dumps(asdict(report), indent=2) + "\n", encoding="utf-8")
        return report

    cache_path = cache_path or (Path.home() / ".cache" / "hayuya" / "face_landmarker.task")
    items: list[SourceAutofixItem] = []
    details: list[str] = []

    for index, source in enumerate(sources):
        image = Image.open(source)
        target = out_dir / "details" / f"{index:03d}-face_detail-auto.png"
        result = None
        warning = None
        try:
            result = _mediapipe_face(source, target, cache_path)
        except Exception as exc:
            warning = f"mediapipe:{type(exc).__name__}:{exc}"

        if result is None:
            try:
                result = _grounded_head_fallback(
                    source,
                    target,
                    out_dir / "fallback" / f"{index:03d}",
                )
            except Exception as exc:
                extra = f"grounded:{type(exc).__name__}:{exc}"
                warning = f"{warning};{extra}" if warning else extra

        if result is not None:
            details.append(str(target))
            item = SourceAutofixItem(
                source=str(source),
                face_detail=result["face_detail"],
                method=result["method"],
                direct_face_detected=bool(result["direct_face_detected"]),
                used_zoom_probe=bool(result["used_zoom_probe"]),
                face_box_fraction=result["face_box_fraction"],
                source_size=[image.width, image.height],
                output_size=result["output_size"],
                warning=warning,
            )
        else:
            item = SourceAutofixItem(
                source=str(source),
                face_detail=None,
                method="no_face_evidence_recovered",
                direct_face_detected=False,
                used_zoom_probe=True,
                face_box_fraction=None,
                source_size=[image.width, image.height],
                output_size=None,
                warning=warning or "no_face_or_head_detected",
            )
        items.append(item)

    ready = bool(sources)
    if policy == "required" and not details:
        raise RuntimeError("source autofix required but no face/head evidence could be recovered")

    report = SourceAutofixReport(
        schema=1,
        ready=ready,
        sources=items,
        derived_detail_sources=details,
        real_sources_preserved=True,
        derived_sources_are_not_independent_references=True,
        policy=policy,
        manifest=str(manifest_path),
    )
    manifest_path.write_text(json.dumps(asdict(report), indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    p = argparse.ArgumentParser(description="HAYUYA single-photo source autofix and automatic face zoom.")
    p.add_argument("--input", type=Path, action="append", required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--policy", choices=["off", "auto", "required"], default="auto")
    a = p.parse_args()
    report = build_source_autofix(a.input, a.out, policy=a.policy)
    print("HAYUYA_SOURCE_AUTOFIX " + json.dumps(asdict(report), separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
