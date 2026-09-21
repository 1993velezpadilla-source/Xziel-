#!/usr/bin/env python3
"""Instrument Vril's accepted Host_Frame stages for Xziel Phase 2.

This patch is intentionally timing-only. It does not change simulation,
rendering decisions, audio behavior, frame pacing, or cvars.
"""

from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_vril_xz_stage_metrics.py <vril-root>")

vril = Path(sys.argv[1]).resolve()
host = vril / "source" / "host.c"

if not host.is_file():
    raise SystemExit(f"Vril host.c not found: {host}")

text = host.read_text(encoding="utf-8")

include_anchor = '#include "nzportable_def.h"\n'
include_block = (
    '#include "nzportable_def.h"\n'
    '#ifdef __ANDROID__\n'
    '#include "xz_android_runtime.h"\n'
    '#endif\n'
)
if '#include "xz_android_runtime.h"' not in text:
    if include_anchor not in text:
        raise SystemExit("Missing host.c include anchor")
    text = text.replace(include_anchor, include_block, 1)

filter_anchor = '''\tif (!Host_FilterTime (time))
\t{
\t\treturn;\t\t\t// don't run too fast, or packets will flood out
\t}
'''
filter_block = filter_anchor + '''#ifdef __ANDROID__
\tXzAndroidRuntime_BeginStage(XZ_CPU_STAGE_UPDATE, Sys_FloatTime());
#endif
'''
if 'XZ_CPU_STAGE_UPDATE' not in text:
    if filter_anchor not in text:
        raise SystemExit("Missing Host_FilterTime stage anchor")
    text = text.replace(filter_anchor, filter_block, 1)

video_anchor = '''// update video
\tif (host_speeds.value)
\t\ttime1 = Sys_FloatTime ();
\tSCR_UpdateScreen ();
\tif (host_speeds.value)
\t\ttime2 = Sys_FloatTime ();
// update audio
'''
video_block = '''// update video
#ifdef __ANDROID__
\tXzAndroidRuntime_EndStage(XZ_CPU_STAGE_UPDATE, Sys_FloatTime());
\tXzAndroidRuntime_BeginStage(XZ_CPU_STAGE_RENDER, Sys_FloatTime());
#endif
\tif (host_speeds.value)
\t\ttime1 = Sys_FloatTime ();
\tSCR_UpdateScreen ();
\tif (host_speeds.value)
\t\ttime2 = Sys_FloatTime ();
#ifdef __ANDROID__
\tXzAndroidRuntime_EndStage(XZ_CPU_STAGE_RENDER, Sys_FloatTime());
\tXzAndroidRuntime_BeginStage(XZ_CPU_STAGE_AUDIO, Sys_FloatTime());
#endif
// update audio
'''
if 'XZ_CPU_STAGE_RENDER' not in text:
    if video_anchor not in text:
        raise SystemExit("Missing SCR_UpdateScreen timing anchor")
    text = text.replace(video_anchor, video_block, 1)

audio_anchor = '''\tMusic_Update();
\tLoadingScreen_Update();

\tif (host_speeds.value)
'''
audio_block = '''\tMusic_Update();
\tLoadingScreen_Update();
#ifdef __ANDROID__
\tXzAndroidRuntime_EndStage(XZ_CPU_STAGE_AUDIO, Sys_FloatTime());
#endif

\tif (host_speeds.value)
'''
if 'XzAndroidRuntime_EndStage(XZ_CPU_STAGE_AUDIO' not in text:
    if audio_anchor not in text:
        raise SystemExit("Missing audio-stage timing anchor")
    text = text.replace(audio_anchor, audio_block, 1)

checks = {
    "runtime include": '#include "xz_android_runtime.h"',
    "update begin": "XzAndroidRuntime_BeginStage(XZ_CPU_STAGE_UPDATE",
    "update end": "XzAndroidRuntime_EndStage(XZ_CPU_STAGE_UPDATE",
    "render begin": "XzAndroidRuntime_BeginStage(XZ_CPU_STAGE_RENDER",
    "render end": "XzAndroidRuntime_EndStage(XZ_CPU_STAGE_RENDER",
    "audio begin": "XzAndroidRuntime_BeginStage(XZ_CPU_STAGE_AUDIO",
    "audio end": "XzAndroidRuntime_EndStage(XZ_CPU_STAGE_AUDIO",
}
for label, needle in checks.items():
    count = text.count(needle)
    if count != 1:
        raise SystemExit(
            f"Phase-2 stage integration check failed for {label}: {count} occurrences"
        )

host.write_text(text, encoding="utf-8")
print("Injected Xziel Xz Phase 2 CPU stage metrics.")
