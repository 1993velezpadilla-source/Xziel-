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


# Android/Bionic does not expose gethostid(). Keep UDP multiplayer enabled by
# resolving the local hostname to an IPv4 address instead of disabling UDP.
udp = source / "platform" / "sdl" / "net_udp_sdl.c"
text = udp.read_text(encoding="utf-8")
old_udp = """	#if defined(_WIN32)
		{
			char hostname[256];
			struct hostent *hostentry;

			gethostname(hostname, sizeof(hostname));

			hostentry = gethostbyname(hostname);
			if (hostentry && hostentry->h_addr_list[0])
				myAddr = *(unsigned long *)hostentry->h_addr_list[0];
			else
				myAddr = inet_addr("127.0.0.1");
		}
	#else
		myAddr = gethostid();
	#endif
"""
new_udp = """	#if defined(_WIN32)
		{
			char hostname[256];
			struct hostent *hostentry;

			gethostname(hostname, sizeof(hostname));

			hostentry = gethostbyname(hostname);
			if (hostentry && hostentry->h_addr_list[0])
				myAddr = *(unsigned long *)hostentry->h_addr_list[0];
			else
				myAddr = inet_addr("127.0.0.1");
		}
	#elif defined(__ANDROID__)
		{
			char local_hostname[256] = "localhost";
			struct hostent *hostentry;
			struct in_addr resolved;

			if (gethostname(local_hostname, sizeof(local_hostname)) != 0)
				strcpy(local_hostname, "localhost");
			local_hostname[sizeof(local_hostname) - 1] = 0;

			hostentry = gethostbyname(local_hostname);
			if (hostentry && hostentry->h_addr_list[0]) {
				memcpy(&resolved.s_addr, hostentry->h_addr_list[0], sizeof(resolved.s_addr));
				myAddr = resolved.s_addr;
			} else {
				myAddr = inet_addr("127.0.0.1");
			}
		}
	#else
		myAddr = gethostid();
	#endif
"""
if old_udp not in text:
    raise SystemExit("Could not find UDP gethostid block")
text = text.replace(old_udp, new_udp, 1)
udp.write_text(text, encoding="utf-8")


# Persist coarse Android startup stages so a device-side crash can be
# diagnosed on the next launch even without adb/logcat.
sys_sdl = source / "platform" / "sdl" / "sys_sdl.c"
text = sys_sdl.read_text(encoding="utf-8")

android_diag = r'''
#ifdef __ANDROID__
#include <android/log.h>
static const char *xziel_diag_basedir = NULL;

static void Xziel_WriteStage(const char *stage)
{
    char path[1024];
    FILE *f;
    if (!xziel_diag_basedir || !stage)
        return;
    snprintf(path, sizeof(path), "%s/.xziel-stage", xziel_diag_basedir);
    f = fopen(path, "wb");
    if (f) {
        fwrite(stage, 1, strlen(stage), f);
        fwrite("\n", 1, 1, f);
        fclose(f);
    }
    __android_log_print(ANDROID_LOG_INFO, "Xziel", "stage=%s", stage);
}

static void Xziel_WriteError(const char *error)
{
    char path[1024];
    FILE *f;
    if (!xziel_diag_basedir || !error)
        return;
    snprintf(path, sizeof(path), "%s/.xziel-last-error", xziel_diag_basedir);
    f = fopen(path, "wb");
    if (f) {
        fwrite(error, 1, strlen(error), f);
        fwrite("\n", 1, 1, f);
        fclose(f);
    }
    __android_log_print(ANDROID_LOG_ERROR, "Xziel", "%s", error);
}
#endif
'''

needle = "#define DEFAULT_MEMORY_MB 128\n"
if android_diag not in text:
    text = text.replace(needle, needle + android_diag, 1)

old_system_error = 'void Sys_SystemError(char *error) { fprintf(stderr, "Vril Engine: %s\\n", error); if (SDL_WasInit(SDL_INIT_VIDEO)) SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_ERROR, "Vril Engine", error, sdl_window); SDL_Quit(); exit(1); }'
new_system_error = '''void Sys_SystemError(char *error) {
#ifdef __ANDROID__
    Xziel_WriteError(error);
    Xziel_WriteStage("SYS_ERROR");
#endif
    fprintf(stderr, "Vril Engine: %s\\n", error);
    if (SDL_WasInit(SDL_INIT_VIDEO))
        SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_ERROR, "Vril Engine", error, sdl_window);
    SDL_Quit();
    exit(1);
}'''
if old_system_error in text:
    text = text.replace(old_system_error, new_system_error, 1)

old_base = '''	if (!Startup_GetBaseDirectory(&startup, ".", &base_directory,
		startup_error, sizeof(startup_error))) {
		fprintf(stderr, "Startup: %s\\n", startup_error);
		Startup_FreeArguments(&startup);
		return 1;
	}
'''
new_base = old_base + '''#ifdef __ANDROID__
	xziel_diag_basedir = base_directory;
	Xziel_WriteStage("ARGS_READY");
#endif
'''
if old_base not in text:
    raise SystemExit("Could not find base-directory startup block")
text = text.replace(old_base, new_base, 1)

old_sdl = '''	if (SDL_Init(headless_test ? SDL_INIT_TIMER :
		(SDL_INIT_VIDEO | SDL_INIT_AUDIO | SDL_INIT_EVENTS | SDL_INIT_GAMECONTROLLER)) != 0) {
		fprintf(stderr, "SDL_Init: %s\\n", SDL_GetError());
		Startup_FreeArguments(&startup);
		return 1;
	}
'''
new_sdl = old_sdl + '''#ifdef __ANDROID__
	Xziel_WriteStage("SDL_INIT_OK");
#endif
'''
if old_sdl not in text:
    raise SystemExit("Could not find SDL_Init block")
text = text.replace(old_sdl, new_sdl, 1)

old_host = '''	Host_Init(&parms);
	oldtime = Sys_FloatTime();
	while (sdl_running) {
'''
new_host = '''#ifdef __ANDROID__
	Xziel_WriteStage("HOST_INIT_BEGIN");
#endif
	Host_Init(&parms);
#ifdef __ANDROID__
	Xziel_WriteStage("HOST_INIT_OK");
#endif
	oldtime = Sys_FloatTime();
	{
		int xziel_first_frame = 1;
	while (sdl_running) {
'''
if old_host not in text:
    raise SystemExit("Could not find Host_Init block")
text = text.replace(old_host, new_host, 1)

old_loop_tail = '''		music_update();
		oldtime = now;
	}
	if (host_initialized)
'''
new_loop_tail = '''		music_update();
		oldtime = now;
#ifdef __ANDROID__
		if (xziel_first_frame) {
			Xziel_WriteStage("FIRST_FRAME_OK");
			xziel_first_frame = 0;
		}
#endif
	}
	}
#ifdef __ANDROID__
	Xziel_WriteStage("CLEAN_EXIT");
#endif
	if (host_initialized)
'''
if old_loop_tail not in text:
    raise SystemExit("Could not find main loop tail")
text = text.replace(old_loop_tail, new_loop_tail, 1)

sys_sdl.write_text(text, encoding="utf-8")
