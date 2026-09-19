#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_vril_android.py <vril-engine-dir>")

root = Path(sys.argv[1]).resolve()
source = root / "source"

if not source.is_dir():
    raise SystemExit(f"Vril source directory not found: {source}")

try:
    git_hash = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
        text=True,
    ).strip()
except Exception:
    git_hash = "unknown"

(source / "_build_info.h").write_text(
    '#define GIT_HASH "{}"\n'
    '#define GIT_BRANCH "xziel-android"\n'
    '#define BUILD_DATE "{}"\n'.format(
        git_hash,
        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    ),
    encoding="utf-8",
)

gl_main = source / "platform" / "sdl" / "gl" / "gl_main.h"
text = gl_main.read_text(encoding="utf-8")
text = text.replace(
    "#else\n#include <GL/gl.h>\n#include <GL/glu.h>\n#endif",
    "#else\n#include <GL/gl.h>\n#ifndef __ANDROID__\n#include <GL/glu.h>\n#endif\n#endif",
)
gl_main.write_text(text, encoding="utf-8")

rmain = source / "platform" / "sdl" / "gl" / "gl_rmain.c"
text = rmain.read_text(encoding="utf-8")
text = text.replace(
    "gluPerspective (r_refdef.fov_y,  screenaspect,  4,  4096);",
    "MYgluPerspective (r_refdef.fov_y,  screenaspect,  4,  4096);",
)
rmain.write_text(text, encoding="utf-8")

vid = source / "platform" / "sdl" / "gl" / "gl_vidsdl.c"
text = vid.read_text(encoding="utf-8")

needle = '#include "../../../nzportable_def.h"\n#include "../sdl_local.h"\n'
replacement = (
    '#include "../../../nzportable_def.h"\n'
    '#include "../sdl_local.h"\n\n'
    '#ifdef __ANDROID__\n'
    'extern void initialize_gl4es(void);\n'
    '#endif\n'
)
if needle not in text:
    raise SystemExit("Could not find gl_vidsdl include block")
text = text.replace(needle, replacement, 1)

old_context = """\tSDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 2);
\tSDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 1);
\tSDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK, SDL_GL_CONTEXT_PROFILE_COMPATIBILITY);
"""
new_context = """#ifdef __ANDROID__
\tSDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 2);
\tSDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 0);
\tSDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK, SDL_GL_CONTEXT_PROFILE_ES);
#else
\tSDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 2);
\tSDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 1);
\tSDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK, SDL_GL_CONTEXT_PROFILE_COMPATIBILITY);
#endif
"""
if old_context not in text:
    raise SystemExit("Could not find desktop GL context setup")
text = text.replace(old_context, new_context, 1)

old_create = """\tsdl_gl_context = SDL_GL_CreateContext(sdl_window);
\tif (!sdl_gl_context) Sys_Error("SDL_GL_CreateContext: %s", SDL_GetError());
"""
new_create = """\tsdl_gl_context = SDL_GL_CreateContext(sdl_window);
\tif (!sdl_gl_context) Sys_Error("SDL_GL_CreateContext: %s", SDL_GetError());
#ifdef __ANDROID__
\tinitialize_gl4es();
#endif
"""
if old_create not in text:
    raise SystemExit("Could not find SDL_GL_CreateContext block")
text = text.replace(old_create, new_create, 1)

vid.write_text(text, encoding="utf-8")

print(f"Patched Vril {git_hash} for Android/GL4ES")
