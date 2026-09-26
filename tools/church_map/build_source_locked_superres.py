#!/usr/bin/env python3
"""
Build a *derivative* high-resolution St Giles albedo while keeping the
photogrammetry source as the low-frequency authority.

This is deliberately NOT called an original texture.  Real-ESRGAN may infer
high-frequency content.  We therefore keep only a bounded high-pass residual
from the SR result, add it to a deterministic Lanczos upscale of the exact
source, then verify that downsampling back to source resolution remains close
to the original pixels.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


def sha_rgba(image: Image.Image) -> str:
    return hashlib.sha256(image.convert("RGBA").tobytes()).hexdigest()


def psnr(a: np.ndarray, b: np.ndarray) -> float:
    mse = float(np.mean((a.astype(np.float32) - b.astype(np.float32)) ** 2))
    if mse <= 1.0e-12:
        return float("inf")
    return 20.0 * math.log10(255.0 / math.sqrt(mse))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--sr", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--alpha", type=float, default=0.35)
    parser.add_argument("--max-mae", type=float, default=2.0)
    parser.add_argument("--min-psnr", type=float, default=38.0)
    args = parser.parse_args()

    source_path = Path(args.source)
    sr_path = Path(args.sr)
    output_path = Path(args.output)
    report_path = Path(args.report)

    source = Image.open(source_path).convert("RGB")
    sr = Image.open(sr_path).convert("RGB")

    expected = (source.width * 4, source.height * 4)
    if sr.size != expected:
        raise RuntimeError(
            f"unexpected SR dimensions {sr.size}, expected {expected}"
        )

    source_up = source.resize(expected, Image.Resampling.LANCZOS)
    source_up_np = np.asarray(source_up, dtype=np.float32)
    sr_np = np.asarray(sr, dtype=np.float32)

    # SOURCE_LOCKED_SR_HIGH_PASS_V1
    # Real-ESRGAN is allowed to contribute only high-frequency residual. The
    # original scan owns color, broad stone variation, shadows, moss and every
    # architectural macro pattern.
    sr_low = np.asarray(
        sr.filter(ImageFilter.GaussianBlur(radius=4.0)),
        dtype=np.float32,
    )
    residual = sr_np - sr_low

    requested_alpha = max(0.0, min(1.0, float(args.alpha)))
    candidate_alpha = requested_alpha
    accepted = None
    metrics = None

    source_np = np.asarray(source, dtype=np.float32)

    # Back off automatically until the 4K derivative round-trips closely to
    # the exact 1K source. This prevents an AI restoration pass from silently
    # becoming the visual authority.
    for _ in range(12):
        candidate_np = np.clip(
            source_up_np + residual * candidate_alpha,
            0.0,
            255.0,
        ).astype(np.uint8)
        candidate = Image.fromarray(candidate_np, "RGB")
        down = candidate.resize(source.size, Image.Resampling.LANCZOS)
        down_np = np.asarray(down, dtype=np.float32)

        mae = float(np.mean(np.abs(down_np - source_np)))
        peak_error = int(
            np.max(np.abs(down_np - source_np))
        )
        current_psnr = psnr(down_np, source_np)

        if mae <= args.max_mae and current_psnr >= args.min_psnr:
            accepted = candidate
            metrics = {
                "roundTripMae": mae,
                "roundTripPeakError": peak_error,
                "roundTripPsnrDb": current_psnr,
            }
            break

        candidate_alpha *= 0.78

    if accepted is None or metrics is None:
        raise RuntimeError(
            "unable to produce a source-locked SR derivative within fidelity "
            f"limits mae<={args.max_mae} psnr>={args.min_psnr}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    accepted.save(output_path, format="PNG", compress_level=3)

    source_sha = sha_rgba(source)
    report = {
        "schemaVersion": 1,
        "method": "SOURCE_LOCKED_REALESRGAN_HIGH_PASS_V1",
        "classification": "DERIVATIVE_NOT_ORIGINAL",
        "sourcePath": str(source_path),
        "sourceDimensions": [source.width, source.height],
        "sourceDecodedRgbaSha256": source_sha,
        "srInputDimensions": [sr.width, sr.height],
        "outputDimensions": [accepted.width, accepted.height],
        "requestedHighPassAlpha": requested_alpha,
        "acceptedHighPassAlpha": candidate_alpha,
        "gaussianHighPassRadius": 4.0,
        "maxRoundTripMae": args.max_mae,
        "minRoundTripPsnrDb": args.min_psnr,
        **metrics,
        "outputDecodedRgbaSha256": sha_rgba(accepted),
        "sourceAuthority": True,
        "runtimeApproved": False,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(
        "XZIEL_SOURCE_LOCKED_SR_READY",
        json.dumps(
            {
                "source": report["sourceDimensions"],
                "output": report["outputDimensions"],
                "alpha": round(candidate_alpha, 5),
                "mae": round(metrics["roundTripMae"], 4),
                "psnrDb": round(metrics["roundTripPsnrDb"], 3),
                "classification": report["classification"],
            },
            separators=(",", ":"),
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
