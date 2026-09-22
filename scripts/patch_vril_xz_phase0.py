#!/usr/bin/env python3
"""Inject Xziel Phase-0 runtime telemetry into the freshly cloned Vril tree.

The Android build intentionally clones upstream Vril on every run. Xziel-owned
modules live in engine/xz/ and are copied into Vril's source root here so the
existing Android.mk wildcard compiles them without vendoring/forking Vril.

Phase 0 established telemetry and recommendations. By Phase 15 the modern
shadow renderer actively applies those recommendations to render scale,
quality budgets and asset residency while legacy GL4ES remains visible.
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
    "xz_device_caps.h",
    "xz_device_caps.c",
    "xz_scene_budget.h",
    "xz_scene_budget.c",
    "xz_render_plan.h",
    "xz_render_plan.c",
    "xz_rhi.h",
    "xz_rhi.c",
    "xz_gles3_probe.h",
    "xz_gles3_probe.c",
    "xz_render_graph.h",
    "xz_render_graph.c",
    "xz_gles3_shadow.h",
    "xz_gles3_shadow.c",
    "xz_gpu_resources.h",
    "xz_gpu_resources.c",
    "xz_command_stream.h",
    "xz_command_stream.c",
    "xz_gles3_resource_plan.h",
    "xz_gles3_resource_plan.c",
    "xz_pass_targets.h",
    "xz_pass_targets.c",
    "xz_pass_inputs.h",
    "xz_pass_inputs.c",
    "xz_visibility.h",
    "xz_visibility.c",
    "xz_material_lighting.h",
    "xz_material_lighting.c",
    "xz_active_quality.h",
    "xz_active_quality.c",
    "xz_stream_residency.h",
    "xz_stream_residency.c",
    "xz_cutover.h",
    "xz_cutover.c",
    "xz_geometry_tap.h",
    "xz_geometry_tap.c",
    "xz_texture_tap.h",
    "xz_texture_tap.c",
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
    '#include "xz_texture_tap.h"\n'
    '#endif\n'
)
if '#include "xz_android_runtime.h"' not in text:
    if include_anchor not in text:
        raise SystemExit("Missing sys_sdl include anchor")
    text = text.replace(include_anchor, include_block, 1)

if '#include "xz_geometry_tap.h"' not in text:
    anchor = '#include "xz_vril_bridge.h"\n'
    if anchor not in text:
        raise SystemExit("Missing geometry-tap include anchor")
    text = text.replace(
        anchor,
        anchor + '#include "xz_geometry_tap.h"\n',
        1,
    )

init_anchor = '\tHost_Init(&parms);\n'
init_block = (
    '#ifdef __ANDROID__\n'
    '\t/* Capture renderer uploads performed during Host_Init. */\n'
    '\tXzTextureTap_Init();\n'
    '#endif\n'
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

if "XzGeometryTap_Init();" not in text:
    anchor = "\tXzVrilBridge_Init();\n"
    if anchor not in text:
        raise SystemExit("Missing geometry-tap init anchor")
    text = text.replace(
        anchor,
        anchor + "\tXzGeometryTap_Init();\n",
        1,
    )

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

if "XzGeometryTap_BeginFrame" not in text:
    begin_anchor = "\t\tXzAndroidRuntime_BeginFrame(now);\n"
    if begin_anchor not in text:
        raise SystemExit("Missing geometry-tap begin anchor")
    text = text.replace(
        begin_anchor,
        begin_anchor +
        "\t\tXzGeometryTap_BeginFrame((uint64_t)(xz_frame_before + 1));\n",
        1,
    )

if "XzGeometryTap_CommitFrame();" not in text:
    commit_anchor = "\t\t\tXzVrilBridge_CapturePresentation(host_framecount);\n"
    if commit_anchor not in text:
        raise SystemExit("Missing geometry-tap commit anchor")
    text = text.replace(
        commit_anchor,
        "\t\t\tXzGeometryTap_CommitFrame();\n" + commit_anchor,
        1,
    )

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


# Capture the actual SDL/GL geometry batches that legacy Vril submits. Xz uses
# these only for parity validation; the legacy GL4ES draw calls remain intact.
gl_hyena = source / "platform" / "sdl" / "gl" / "gl_hyena.c"
hyena = gl_hyena.read_text(encoding="utf-8")

if '#include "xz_geometry_tap.h"' not in hyena:
    anchor = '#include "../../../nzportable_def.h"\n'
    if anchor not in hyena:
        raise SystemExit("Missing gl_hyena include anchor")
    hyena = hyena.replace(
        anchor,
        anchor +
        '#ifdef __ANDROID__\n'
        '#include "xz_geometry_tap.h"\n'
        '#include <stddef.h>\n'
        '#endif\n',
        1,
    )

alias_anchor = (
    "void Hyena_DrawAliasBatch(const alias_batch_t *batch)\n"
    "{\n"
    "    if (!batch->num_indices) return;\n"
)
if "XzGeometryTap_CaptureAlias(" not in hyena:
    if alias_anchor not in hyena:
        raise SystemExit("Missing alias geometry capture anchor")
    alias_capture = alias_anchor + (
        "#ifdef __ANDROID__\n"
        "    {\n"
        "        float xz_mv[16], xz_pr[16];\n"
        "        GLint xz_tex = 0;\n"
        "        glGetFloatv(GL_MODELVIEW_MATRIX, xz_mv);\n"
        "        glGetFloatv(GL_PROJECTION_MATRIX, xz_pr);\n"
        "        glGetIntegerv(GL_TEXTURE_BINDING_2D, &xz_tex);\n"
        "        XzGeometryTap_CaptureAlias(\n"
        "            batch->vertices,\n"
        "            (unsigned int)batch->num_vertices,\n"
        "            (unsigned int)sizeof(alias_vertex_t),\n"
        "            (unsigned int)offsetof(alias_vertex_t, xyz),\n"
        "            (unsigned int)offsetof(alias_vertex_t, uv),\n"
        "            batch->indices,\n"
        "            (unsigned int)batch->num_indices,\n"
        "            (int)xz_tex,\n"
        "            xz_mv,\n"
        "            xz_pr);\n"
        "    }\n"
        "#endif\n"
    )
    hyena = hyena.replace(alias_anchor, alias_capture, 1)

warp_anchor = (
    "        for (i = 0; i < count; ++i) {\n"
    "            const float *in = source + i * stride;\n"
    "            Hyena_2DTextureCoord(&vertices[i], in[texture_offset], in[texture_offset + 1]);\n"
    "            Hyena_VertexXYZ(&vertices[i], in[0] + 8*sinf(in[1]*0.05f+(float)time)*sinf(in[2]*0.05f+(float)time), in[1] + 8*sinf(in[0]*0.05f+(float)time)*sinf(in[2]*0.05f+(float)time), in[2]);\n"
    "        }\n"
)
if "XZ_GEOMETRY_WARP_CAPTURE" not in hyena:
    if warp_anchor not in hyena:
        raise SystemExit("Missing warped surface capture anchor")
    warp_capture = warp_anchor + (
        "#ifdef __ANDROID__\n"
        "        /* XZ_GEOMETRY_WARP_CAPTURE */\n"
        "        {\n"
        "            float xz_mv[16], xz_pr[16];\n"
        "            GLint xz_tex = 0;\n"
        "            glGetFloatv(GL_MODELVIEW_MATRIX, xz_mv);\n"
        "            glGetFloatv(GL_PROJECTION_MATRIX, xz_pr);\n"
        "            glGetIntegerv(GL_TEXTURE_BINDING_2D, &xz_tex);\n"
        "            XzGeometryTap_CaptureSurfaceFan(\n"
        "                (const float *)vertices,\n"
        "                (unsigned int)count,\n"
        "                (unsigned int)(sizeof(vertex_t) / sizeof(float)),\n"
        "                (unsigned int)(offsetof(vertex_t, xyz) / sizeof(float)),\n"
        "                (unsigned int)(offsetof(vertex_t, uv) / sizeof(float)),\n"
        "                (int)xz_tex,\n"
        "                xz_mv,\n"
        "                xz_pr);\n"
        "        }\n"
        "#endif\n"
    )
    hyena = hyena.replace(warp_anchor, warp_capture, 1)

surface_anchor = (
    "    glEnableClientState(GL_VERTEX_ARRAY); glEnableClientState(GL_TEXTURE_COORD_ARRAY);\n"
    "    glVertexPointer(3, GL_FLOAT, stride * sizeof(float), source);\n"
)
if "XZ_GEOMETRY_SURFACE_CAPTURE" not in hyena:
    if surface_anchor not in hyena:
        raise SystemExit("Missing surface geometry capture anchor")
    surface_capture = (
        "#ifdef __ANDROID__\n"
        "    /* XZ_GEOMETRY_SURFACE_CAPTURE */\n"
        "    {\n"
        "        float xz_mv[16], xz_pr[16];\n"
        "        GLint xz_tex = 0;\n"
        "        glGetFloatv(GL_MODELVIEW_MATRIX, xz_mv);\n"
        "        glGetFloatv(GL_PROJECTION_MATRIX, xz_pr);\n"
        "        glGetIntegerv(GL_TEXTURE_BINDING_2D, &xz_tex);\n"
        "        XzGeometryTap_CaptureSurfaceFan(\n"
        "            source,\n"
        "            (unsigned int)count,\n"
        "            (unsigned int)stride,\n"
        "            0u,\n"
        "            (unsigned int)texture_offset,\n"
        "            (int)xz_tex,\n"
        "            xz_mv,\n"
        "            xz_pr);\n"
        "    }\n"
        "#endif\n"
    ) + surface_anchor
    hyena = hyena.replace(surface_anchor, surface_capture, 1)

gl_hyena.write_text(hyena, encoding="utf-8")


# Capture the exact level-0 RGBA texels that Vril uploads to legacy GL4ES.
# GL_Upload32 mutates its scratch buffer while generating mip levels, so the
# tap must run immediately after the level-0 upload and before that loop.
gl_draw = source / "platform" / "sdl" / "gl" / "gl_draw.c"
draw = gl_draw.read_text(encoding="utf-8")

if '#include "xz_texture_tap.h"' not in draw:
    anchor = '#include "../../../nzportable_def.h"\n'
    if anchor not in draw:
        raise SystemExit("Missing gl_draw texture-tap include anchor")
    draw = draw.replace(
        anchor,
        anchor +
        '#ifdef __ANDROID__\n'
        '#include "xz_texture_tap.h"\n'
        '#endif\n',
        1,
    )

texture_upload_anchor = (
    "    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, scaled_width, "
    "scaled_height, 0, GL_RGBA, GL_UNSIGNED_BYTE, scaled);\n"
)
if "XZ_TEXTURE_RGBA_CAPTURE" not in draw:
    if texture_upload_anchor not in draw:
        raise SystemExit("Missing GL_Upload32 level-0 texture anchor")
    texture_capture = texture_upload_anchor + (
        "#ifdef __ANDROID__\n"
        "    /* XZ_TEXTURE_RGBA_CAPTURE: before scaled is mip-mutated. */\n"
        "    XzTextureTap_CaptureRgba(\n"
        "        (unsigned int)gl_id,\n"
        "        scaled,\n"
        "        (unsigned int)scaled_width,\n"
        "        (unsigned int)scaled_height);\n"
        "#endif\n"
    )
    draw = draw.replace(
        texture_upload_anchor,
        texture_capture,
        1,
    )

gl_draw.write_text(draw, encoding="utf-8")

if draw.count('#include "xz_texture_tap.h"') != 1:
    raise SystemExit("Texture tap header injection count mismatch")
if draw.count("XZ_TEXTURE_RGBA_CAPTURE") != 1:
    raise SystemExit("Texture RGBA capture injection count mismatch")


gl_rmain = source / "platform" / "sdl" / "gl" / "gl_rmain.c"
rmain = gl_rmain.read_text(encoding="utf-8")

if '#include "xz_geometry_tap.h"' not in rmain:
    anchor = '#include "../../../nzportable_def.h"\n'
    if anchor not in rmain:
        raise SystemExit("Missing gl_rmain include anchor")
    rmain = rmain.replace(
        anchor,
        anchor +
        '#ifdef __ANDROID__\n'
        '#include "xz_geometry_tap.h"\n'
        '#endif\n',
        1,
    )

sprite_anchor = "GL_Bind(frame->gl_texturenum);"
if "XZ_GEOMETRY_SPRITE_CAPTURE" not in rmain:
    if sprite_anchor not in rmain:
        raise SystemExit("Missing sprite geometry capture anchor")
    sprite_capture = sprite_anchor + (
        "\n#ifdef __ANDROID__\n"
        "\t/* XZ_GEOMETRY_SPRITE_CAPTURE */\n"
        "\t{\n"
        "\t\tfloat xz_positions[12];\n"
        "\t\tconst float xz_uvs[8] = {0,1, 0,0, 1,0, 1,1};\n"
        "\t\tfloat xz_mv[16], xz_pr[16];\n"
        "\t\tGLint xz_tex = 0;\n"
        "\t\tvec3_t xz_point;\n"
        "\t\tVectorMA (e->origin, frame->down * scale, up, xz_point);\n"
        "\t\tVectorMA (xz_point, frame->left * scale, right, xz_point);\n"
        "\t\tmemcpy(&xz_positions[0], xz_point, sizeof(vec3_t));\n"
        "\t\tVectorMA (e->origin, frame->up * scale, up, xz_point);\n"
        "\t\tVectorMA (xz_point, frame->left * scale, right, xz_point);\n"
        "\t\tmemcpy(&xz_positions[3], xz_point, sizeof(vec3_t));\n"
        "\t\tVectorMA (e->origin, frame->up * scale, up, xz_point);\n"
        "\t\tVectorMA (xz_point, frame->right * scale, right, xz_point);\n"
        "\t\tmemcpy(&xz_positions[6], xz_point, sizeof(vec3_t));\n"
        "\t\tVectorMA (e->origin, frame->down * scale, up, xz_point);\n"
        "\t\tVectorMA (xz_point, frame->right * scale, right, xz_point);\n"
        "\t\tmemcpy(&xz_positions[9], xz_point, sizeof(vec3_t));\n"
        "\t\tglGetFloatv(GL_MODELVIEW_MATRIX, xz_mv);\n"
        "\t\tglGetFloatv(GL_PROJECTION_MATRIX, xz_pr);\n"
        "\t\tglGetIntegerv(GL_TEXTURE_BINDING_2D, &xz_tex);\n"
        "\t\tXzGeometryTap_CaptureSpriteQuad(\n"
        "\t\t\txz_positions,\n"
        "\t\t\txz_uvs,\n"
        "\t\t\t(int)xz_tex,\n"
        "\t\t\txz_mv,\n"
        "\t\t\txz_pr);\n"
        "\t}\n"
        "#endif"
    )
    rmain = rmain.replace(sprite_anchor, sprite_capture, 1)

gl_rmain.write_text(rmain, encoding="utf-8")


# Validate the expected integration exactly once. Failing here is preferable to
# silently building an APK that is not actually collecting Phase-0 telemetry.
checks = {
    "runtime header": '#include "xz_android_runtime.h"',
    "bridge header": '#include "xz_vril_bridge.h"',
    "init": "XzAndroidRuntime_Init(heap_size);",
    "texture init": "XzTextureTap_Init();",
    "bridge init": "XzVrilBridge_Init();",
    "begin": "XzAndroidRuntime_BeginFrame(now);",
    "frame-counter snapshot": "int xz_frame_before = host_framecount;",
    "real first-frame gate": "xziel_first_frame && host_framecount != xz_frame_before",
    "capture": "XzVrilBridge_CapturePresentation(host_framecount);",
    "end": "XzAndroidRuntime_EndFrame(Sys_FloatTime());",
    "geometry begin": "XzGeometryTap_BeginFrame",
    "geometry commit": "XzGeometryTap_CommitFrame();",
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

print("Injected Xziel Xz runtime through Phase 16 + real geometry + texture parity taps.")
