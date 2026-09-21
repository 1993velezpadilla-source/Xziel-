#!/usr/bin/env python3
"""Inject Xziel Phase-0 runtime telemetry into the freshly cloned Vril tree.

The Android build intentionally clones upstream Vril on every run. Xziel-owned
modules live in engine/xz/ and are copied into Vril's source root here so the
existing Android.mk wildcard compiles them without vendoring/forking Vril.

Phase 0 is passive: it measures frame/memory/device state and computes quality
recommendations, but it does not mutate gameplay or renderer state.
"""

from pathlib import Path
import shutil
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_vril_xz_phase0.py <vril-root>")

vril = Path(sys.argv[1]).resolve()
source = vril / "source"
repo = Path(__file__).resolve().parents[1]
modules = repo / "engine" / "xz"

if not source.is_dir():
    raise SystemExit(f"Vril source directory not found: {source}")
if not modules.is_dir():
    raise SystemExit(f"Xz module directory not found: {modules}")

for name in (
    "xz_phase0.h",
    "xz_phase0.c",
    "xz_android_runtime.h",
    "xz_android_runtime.c",
    "xz_present_world.h",
    "xz_present_world.c",
    "xz_vril_bridge.h",
    "xz_vril_bridge.c",
):
    src = modules / name
    if not src.is_file():
        raise SystemExit(f"Missing Xz source: {src}")
    shutil.copy2(src, source / name)

sys_sdl = source / "platform" / "sdl" / "sys_sdl.c"
text = sys_sdl.read_text(encoding="utf-8")

include_anchor = '#include "sdl_local.h"\n'
include_block = (
    '#include "sdl_local.h"\n'
    '#ifdef __ANDROID__\n'
    '#include "xz_android_runtime.h"\n'
    '#include "xz_vril_bridge.h"\n'
    '#endif\n'
)
if '#include "xz_android_runtime.h"' not in text:
    if include_anchor not in text:
        raise SystemExit("Missing sys_sdl include anchor")
    text = text.replace(include_anchor, include_block, 1)

init_anchor = '\tHost_Init(&parms);\n'
init_block = (
    '\tHost_Init(&parms);\n'
    '#ifdef __ANDROID__\n'
    '\tXzAndroidRuntime_Init(heap_size);\n'
    '\tXzVrilBridge_Init();\n'
    '#endif\n'
)
if 'XzAndroidRuntime_Init(heap_size);' not in text:
    if init_anchor not in text:
        raise SystemExit("Missing Host_Init Phase-0 anchor")
    text = text.replace(init_anchor, init_block, 1)

loop_anchor = (
    '\t\tdouble now = Sys_FloatTime();\n'
    '\t\tHost_Frame(now - oldtime);\n'
    '\t\tmusic_update();\n'
    '\t\toldtime = now;\n'
)
loop_block = (
    '\t\tdouble now = Sys_FloatTime();\n'
    '#ifdef __ANDROID__\n'
    '\t\tint xz_frame_before = host_framecount;\n'
    '\t\tXzAndroidRuntime_BeginFrame(now);\n'
    '#endif\n'
    '\t\tHost_Frame(now - oldtime);\n'
    '\t\tmusic_update();\n'
    '#ifdef __ANDROID__\n'
    '\t\t/* Host_FilterTime can reject a loop iteration. Only publish a\n'
    '\t\t * metric when Vril actually processed a frame. */\n'
    '\t\tif (host_framecount != xz_frame_before) {\n'
    '\t\t\tXzVrilBridge_CapturePresentation(host_framecount);\n'
    '\t\t\tXzAndroidRuntime_EndFrame(Sys_FloatTime());\n'
    '\t\t}\n'
    '#endif\n'
    '\t\toldtime = now;\n'
)
if 'XzAndroidRuntime_BeginFrame(now);' not in text:
    if loop_anchor not in text:
        raise SystemExit("Missing SDL frame-loop Phase-0 anchor")
    text = text.replace(loop_anchor, loop_block, 1)

first_frame_old = (
    '#ifdef __ANDROID__\n'
    '\t\tif (xziel_first_frame) {\n'
    '\t\t\tXziel_WriteStage("FIRST_FRAME_OK");\n'
    '\t\t\txziel_first_frame = 0;\n'
    '\t\t}\n'
    '#endif\n'
)
first_frame_new = (
    '#ifdef __ANDROID__\n'
    '\t\tif (xziel_first_frame && host_framecount != xz_frame_before) {\n'
    '\t\t\tXziel_WriteStage("FIRST_FRAME_OK");\n'
    '\t\t\txziel_first_frame = 0;\n'
    '\t\t}\n'
    '#endif\n'
)
if 'xziel_first_frame && host_framecount != xz_frame_before' not in text:
    if first_frame_old not in text:
        raise SystemExit("Missing FIRST_FRAME_OK hardening anchor")
    text = text.replace(first_frame_old, first_frame_new, 1)

shutdown_anchor = '\tif (host_initialized)\n\t\tHost_Shutdown();\n'
shutdown_block = (
    '#ifdef __ANDROID__\n'
    '\tXzVrilBridge_Shutdown();\n'
    '\tXzAndroidRuntime_Shutdown();\n'
    '#endif\n'
    '\tif (host_initialized)\n'
    '\t\tHost_Shutdown();\n'
)
if 'XzAndroidRuntime_Shutdown();' not in text:
    if shutdown_anchor not in text:
        raise SystemExit("Missing shutdown Phase-0 anchor")
    text = text.replace(shutdown_anchor, shutdown_block, 1)

sys_sdl.write_text(text, encoding="utf-8")

# Validate the expected integration exactly once. Failing here is preferable to
# silently building an APK that is not actually collecting Phase-0 telemetry.
checks = {
    "runtime header": '#include "xz_android_runtime.h"',
    "bridge header": '#include "xz_vril_bridge.h"',
    "init": "XzAndroidRuntime_Init(heap_size);",
    "bridge init": "XzVrilBridge_Init();",
    "begin": "XzAndroidRuntime_BeginFrame(now);",
    "frame-counter snapshot": "int xz_frame_before = host_framecount;",
    "real first-frame gate": "xziel_first_frame && host_framecount != xz_frame_before",
    "capture": "XzVrilBridge_CapturePresentation(host_framecount);",
    "end": "XzAndroidRuntime_EndFrame(Sys_FloatTime());",
    "bridge shutdown": "XzVrilBridge_Shutdown();",
    "shutdown": "XzAndroidRuntime_Shutdown();",
}
final = sys_sdl.read_text(encoding="utf-8")
for label, needle in checks.items():
    count = final.count(needle)
    if count != 1:
        raise SystemExit(
            f"Phase-0 integration check failed for {label}: {count} occurrences"
        )

print("Injected Xziel Xz runtime Phase 0 + PresentWorld Phase 1 bridge.")
