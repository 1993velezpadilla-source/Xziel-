#!/usr/bin/env python3
"""Prepare Penitent prayer voice assets for runtime spatialization.

The game should spatialize the resulting mono voice in-engine. This tool only
normalizes/filters the source and creates a subtle horror-texture stem.
"""

import argparse
import shutil
import subprocess
from pathlib import Path


def run(cmd):
    print(" ".join(str(x) for x in cmd))
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path, help="Source WAV/FLAC/MP3/OGG")
    ap.add_argument("--out-dir", type=Path, default=Path("church/audio"))
    ap.add_argument("--ffmpeg", default="ffmpeg")
    args = ap.parse_args()

    if not args.input.is_file():
        raise SystemExit(f"Input not found: {args.input}")
    if shutil.which(args.ffmpeg) is None:
        raise SystemExit("ffmpeg is required")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    dry = args.out_dir / "penitent_prayer_mono_48k.wav"
    texture = args.out_dir / "penitent_prayer_texture_48k.wav"

    # Preserve intelligibility. 3D distance/occlusion belongs to the engine.
    dry_filter = (
        "highpass=f=105,"
        "lowpass=f=11500,"
        "equalizer=f=3000:t=q:w=1.3:g=-1.8,"
        "acompressor=threshold=-24dB:ratio=2:attack=18:release=180:makeup=1.5dB,"
        "alimiter=limit=0.88"
    )
    run([
        args.ffmpeg, "-y", "-i", str(args.input),
        "-ac", "1", "-ar", "48000",
        "-af", dry_filter,
        "-c:a", "pcm_s16le", str(dry),
    ])

    # Quiet parallel texture. Do not use this as the positional source by itself.
    texture_filter = (
        "highpass=f=150,"
        "lowpass=f=7200,"
        "aecho=0.72:0.38:43|89:0.16|0.09,"
        "volume=0.42,"
        "alimiter=limit=0.75"
    )
    run([
        args.ffmpeg, "-y", "-i", str(dry),
        "-af", texture_filter,
        "-c:a", "pcm_s16le", str(texture),
    ])

    print("PENITENT_AUDIO_OK")
    print("DRY", dry)
    print("TEXTURE", texture)
    print("Runtime: use DRY as 3D emitter; TEXTURE as low-level local room/terror send.")


if __name__ == "__main__":
    main()
