#!/usr/bin/env python3
"""Fail CI when deterministic Sanctum tour screenshots are visually degraded.

This gate intentionally judges pixels, not engine telemetry. The tour camera is
fixed, so normalized world-region metrics are stable enough to reject the
mushy/low-detail captures that runtime-only checks cannot see.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

CANONICAL_WIDTH = 1280
WORLD_ROI = (0.10, 0.08, 0.76, 0.64)

MIN_WIDTH = 1920
MIN_HEIGHT = 864

# User-visible quality floor. #554 (the rejected blurry capture) is below these
# detail floors even though runtime/PBR/ASTC telemetry is healthy.
MAX_MEDIAN_BLUR_INDEX = 0.300
MIN_MEDIAN_HIGH_FREQ_RMS = 0.034
MIN_MEDIAN_EDGE_DENSITY = 0.140
MIN_MEDIAN_CONTRAST = 0.100
MIN_MEDIAN_LUMA = 0.200
MAX_MEDIAN_LUMA = 0.720

# A median can hide a catastrophically soft primary camera if other views have
# more edges. These deterministic gameplay views are mandatory individually.
CRITICAL_FRAME_MARKERS = (
    "tour-01-entry",
    "tour-03-forward",
)
MAX_CRITICAL_BLUR_INDEX = 0.305
MIN_CRITICAL_HIGH_FREQ_RMS = 0.032
MIN_CRITICAL_EDGE_DENSITY = 0.135


def _axis_box_blur(values: np.ndarray, axis: int, size: int = 9) -> np.ndarray:
    pad = size // 2
    pads = [(0, 0)] * values.ndim
    pads[axis] = (pad, pad)
    padded = np.pad(values, pads, mode="edge")
    cumulative = np.cumsum(padded, axis=axis, dtype=np.float64)

    zero_shape = list(cumulative.shape)
    zero_shape[axis] = 1
    cumulative = np.concatenate(
        [np.zeros(zero_shape, dtype=np.float64), cumulative],
        axis=axis,
    )

    end = [slice(None)] * values.ndim
    begin = [slice(None)] * values.ndim
    end[axis] = slice(size, None)
    begin[axis] = slice(None, -size)

    return (
        (cumulative[tuple(end)] - cumulative[tuple(begin)]) / float(size)
    ).astype(np.float32)


def _blur_index(luma: np.ndarray) -> float:
    directional = []
    for axis in (0, 1):
        blurred = _axis_box_blur(luma, axis=axis, size=9)
        original_edges = np.abs(np.diff(luma, axis=axis))
        blurred_edges = np.abs(np.diff(blurred, axis=axis))

        edge_sum = float(original_edges.sum())
        if edge_sum <= 1.0e-9:
            directional.append(1.0)
            continue

        removed = np.maximum(
            original_edges - blurred_edges,
            0.0,
        )
        directional.append(
            float((edge_sum - removed.sum()) / edge_sum)
        )

    return max(directional)


def _frame_metrics(path: Path) -> dict[str, float | int | str]:
    with Image.open(path) as image:
        image = image.convert("RGB")
        source_width, source_height = image.size

        canonical_height = max(
            1,
            round(source_height * CANONICAL_WIDTH / source_width),
        )
        canonical = image.resize(
            (CANONICAL_WIDTH, canonical_height),
            Image.Resampling.LANCZOS,
        )

    rgb = np.asarray(canonical, dtype=np.float32) / 255.0
    height, width = rgb.shape[:2]

    x0 = int(WORLD_ROI[0] * width)
    y0 = int(WORLD_ROI[1] * height)
    x1 = int(WORLD_ROI[2] * width)
    y1 = int(WORLD_ROI[3] * height)

    roi = rgb[y0:y1, x0:x1]
    luma = (
        roi[..., 0] * 0.2126
        + roi[..., 1] * 0.7152
        + roi[..., 2] * 0.0722
    ).astype(np.float32)

    dx = np.diff(luma, axis=1)
    dy = np.diff(luma, axis=0)
    gradient = np.sqrt(
        dx[:-1, :] * dx[:-1, :]
        + dy[:, :-1] * dy[:, :-1]
    )

    gray = Image.fromarray(
        np.clip(luma * 255.0, 0.0, 255.0).astype(np.uint8),
        mode="L",
    )
    low_pass = (
        np.asarray(
            gray.filter(ImageFilter.BoxBlur(2)),
            dtype=np.float32,
        )
        / 255.0
    )
    high_frequency = luma - low_pass

    return {
        "path": str(path),
        "width": source_width,
        "height": source_height,
        "mean_luma": float(luma.mean()),
        "contrast_std": float(luma.std()),
        "blur_index": _blur_index(luma),
        "high_freq_rms": float(
            np.sqrt(np.mean(high_frequency * high_frequency))
        ),
        "edge_density": float((gradient > 0.06).mean()),
        "gradient_p90": float(np.quantile(gradient, 0.90)),
    }


def _median(frames: list[dict[str, float | int | str]], key: str) -> float:
    return float(np.median([float(frame[key]) for frame in frames]))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("images", nargs="+", type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()

    frames = []
    failures = []

    for image_path in args.images:
        if not image_path.is_file():
            failures.append(f"missing screenshot: {image_path}")
            continue

        frame = _frame_metrics(image_path)
        frames.append(frame)

        if int(frame["width"]) < MIN_WIDTH or int(frame["height"]) < MIN_HEIGHT:
            failures.append(
                f"{image_path.name}: capture is only "
                f"{frame['width']}x{frame['height']}"
            )

    critical_frames = [
        frame
        for frame in frames
        if any(
            marker in Path(str(frame["path"])).name
            for marker in CRITICAL_FRAME_MARKERS
        )
    ]

    for marker in CRITICAL_FRAME_MARKERS:
        matched = [
            frame for frame in critical_frames
            if marker in Path(str(frame["path"])).name
        ]
        if len(matched) != 1:
            failures.append(
                f"critical frame {marker!r} missing or duplicated"
            )
            continue

        frame = matched[0]
        frame_name = Path(str(frame["path"])).name

        if float(frame["blur_index"]) > MAX_CRITICAL_BLUR_INDEX:
            failures.append(
                f"{frame_name}: critical view too blurry: blur_index="
                f"{float(frame['blur_index']):.4f} > "
                f"{MAX_CRITICAL_BLUR_INDEX:.4f}"
            )

        if float(frame["high_freq_rms"]) < MIN_CRITICAL_HIGH_FREQ_RMS:
            failures.append(
                f"{frame_name}: critical micro-detail too weak: "
                f"high_freq_rms={float(frame['high_freq_rms']):.4f} < "
                f"{MIN_CRITICAL_HIGH_FREQ_RMS:.4f}"
            )

        if float(frame["edge_density"]) < MIN_CRITICAL_EDGE_DENSITY:
            failures.append(
                f"{frame_name}: critical edge/detail density too low: "
                f"edge_density={float(frame['edge_density']):.4f} < "
                f"{MIN_CRITICAL_EDGE_DENSITY:.4f}"
            )

    aggregate = {}
    if frames:
        aggregate = {
            "median_luma": _median(frames, "mean_luma"),
            "median_contrast": _median(frames, "contrast_std"),
            "median_blur_index": _median(frames, "blur_index"),
            "median_high_freq_rms": _median(frames, "high_freq_rms"),
            "median_edge_density": _median(frames, "edge_density"),
            "median_gradient_p90": _median(frames, "gradient_p90"),
        }

        if aggregate["median_luma"] < MIN_MEDIAN_LUMA:
            failures.append(
                f"scene too dark: median_luma={aggregate['median_luma']:.4f} "
                f"< {MIN_MEDIAN_LUMA:.4f}"
            )
        if aggregate["median_luma"] > MAX_MEDIAN_LUMA:
            failures.append(
                f"scene too washed out: median_luma={aggregate['median_luma']:.4f} "
                f"> {MAX_MEDIAN_LUMA:.4f}"
            )
        if aggregate["median_contrast"] < MIN_MEDIAN_CONTRAST:
            failures.append(
                f"scene contrast collapsed: median_contrast="
                f"{aggregate['median_contrast']:.4f} "
                f"< {MIN_MEDIAN_CONTRAST:.4f}"
            )
        if aggregate["median_blur_index"] > MAX_MEDIAN_BLUR_INDEX:
            failures.append(
                f"world image is too blurry: median_blur_index="
                f"{aggregate['median_blur_index']:.4f} "
                f"> {MAX_MEDIAN_BLUR_INDEX:.4f}"
            )
        if aggregate["median_high_freq_rms"] < MIN_MEDIAN_HIGH_FREQ_RMS:
            failures.append(
                f"world micro-detail is too weak: median_high_freq_rms="
                f"{aggregate['median_high_freq_rms']:.4f} "
                f"< {MIN_MEDIAN_HIGH_FREQ_RMS:.4f}"
            )
        if aggregate["median_edge_density"] < MIN_MEDIAN_EDGE_DENSITY:
            failures.append(
                f"world edge/detail density is too low: median_edge_density="
                f"{aggregate['median_edge_density']:.4f} "
                f"< {MIN_MEDIAN_EDGE_DENSITY:.4f}"
            )

    report = {
        "schemaVersion": 1,
        "verdict": "fail" if failures else "pass",
        "thresholds": {
            "minWidth": MIN_WIDTH,
            "minHeight": MIN_HEIGHT,
            "maxMedianBlurIndex": MAX_MEDIAN_BLUR_INDEX,
            "minMedianHighFreqRms": MIN_MEDIAN_HIGH_FREQ_RMS,
            "minMedianEdgeDensity": MIN_MEDIAN_EDGE_DENSITY,
            "minMedianContrast": MIN_MEDIAN_CONTRAST,
            "minMedianLuma": MIN_MEDIAN_LUMA,
            "maxMedianLuma": MAX_MEDIAN_LUMA,
            "criticalFrameMarkers": list(CRITICAL_FRAME_MARKERS),
            "maxCriticalBlurIndex": MAX_CRITICAL_BLUR_INDEX,
            "minCriticalHighFreqRms": MIN_CRITICAL_HIGH_FREQ_RMS,
            "minCriticalEdgeDensity": MIN_CRITICAL_EDGE_DENSITY,
        },
        "aggregate": aggregate,
        "frames": frames,
        "failures": failures,
    }

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(report, indent=2))

    if failures:
        for failure in failures:
            print(f"XZIEL_VISUAL_QA_FAIL {failure}", file=sys.stderr)
        return 1

    print(
        "XZIEL_VISUAL_QA_PASS "
        f"blur={aggregate['median_blur_index']:.4f} "
        f"hf={aggregate['median_high_freq_rms']:.4f} "
        f"edges={aggregate['median_edge_density']:.4f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
