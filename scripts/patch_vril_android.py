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
\t/* GL4ES performs its own temporary EGL hardware probe and finishes by
\t * unbinding/terminating that EGL display. Run it before SDL creates the
\t * real game context so its cleanup cannot invalidate SDL's context. */
\tinitialize_gl4es();
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
\tif (SDL_GL_MakeCurrent(sdl_window, sdl_gl_context) != 0)
\t\tSys_Error("SDL_GL_MakeCurrent: %s", SDL_GetError());
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

# Keep Android in landscape before SDL creates the video window. SDL2 otherwise
# maps a resizable window with no orientation hint to FULL_USER, which can
# rotate/recreate the Surface and invalidate the just-created EGL context.
android_orientation_needle = """	if (SDL_Init(headless_test ? SDL_INIT_TIMER :
"""
android_orientation_replacement = """#ifdef __ANDROID__
	SDL_SetHintWithPriority(SDL_HINT_ORIENTATIONS,
		"LandscapeLeft LandscapeRight", SDL_HINT_OVERRIDE);
#endif
	if (SDL_Init(headless_test ? SDL_INIT_TIMER :
"""
if android_orientation_needle not in text:
    raise SystemExit("Could not find SDL_Init orientation insertion point")
text = text.replace(android_orientation_needle, android_orientation_replacement, 1)

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


# Android music fallback: Vril's SFX backend already owns an SDL audio device.
# SDL_mixer currently attempts to open a second device for MP3 music and can
# fail on Android/OpenSL ES. Do not abort the whole engine: keep SFX active and
# leave background music disabled until both paths are mixed through one device.
snd_music = source / "snd_music.c"
text = snd_music.read_text(encoding="utf-8")

old_music_init = """	if (music_init() == 0) {
		Sys_Error("Could not Initialize Music Subsystem.");
	}
"""
new_music_init = """	if (music_init() == 0) {
#ifdef __ANDROID__
		Con_Printf("Android music backend unavailable; continuing with SFX audio only.\\n");
		enabled = false;
		return;
#else
		Sys_Error("Could not Initialize Music Subsystem.");
#endif
	}
"""
if old_music_init not in text:
    raise SystemExit("Could not find Music_Init failure block")
text = text.replace(old_music_init, new_music_init, 1)

old_music_play = """void Music_PlayFromString(char* track_name, qboolean looping)
{
	Music_Stop();
"""
new_music_play = """void Music_PlayFromString(char* track_name, qboolean looping)
{
#ifdef __ANDROID__
	if (!enabled) return;
#endif
	Music_Stop();
"""
if old_music_play not in text:
    raise SystemExit("Could not find Music_PlayFromString block")
text = text.replace(old_music_play, new_music_play, 1)

old_music_shutdown = """void Music_Shutdown(void)
{
	Music_Stop();
	music_deinit();
}
"""
new_music_shutdown = """void Music_Shutdown(void)
{
#ifdef __ANDROID__
	if (!enabled) return;
#endif
	Music_Stop();
	music_deinit();
	enabled = false;
}
"""
if old_music_shutdown not in text:
    raise SystemExit("Could not find Music_Shutdown block")
text = text.replace(old_music_shutdown, new_music_shutdown, 1)

snd_music.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Xziel Android native mobile controls v1
# ---------------------------------------------------------------------------
# Goals:
# - real SDL finger events, no touch->mouse synthesis
# - dynamic left movement stick
# - free-look on the right side
# - dedicated FIRE, ADS, ADS+FIRE, RELOAD, USE, JUMP, KNIFE, SWITCH buttons
# - semi-auto pistol auto-tap while FIRE is held
# - direct menu touch coordinates
# - tap/back to leave Game Over
#
# This intentionally uses Vril's existing input commands instead of inventing
# a parallel movement/weapon system.

in_sdl = source / "platform" / "sdl" / "in_sdl.c"
text = in_sdl.read_text(encoding="utf-8")

touch_externs = r'''
#ifdef __ANDROID__
extern qboolean xziel_mobile_move_active;
extern float xziel_mobile_move_x;
extern float xziel_mobile_move_y;
#endif
'''
inc = '#include "sdl_local.h"\n'
if touch_externs not in text:
    if inc not in text:
        raise SystemExit("Could not find in_sdl include anchor")
    text = text.replace(inc, inc + touch_externs, 1)

old_stick = r'''void IN_GetAnalogStick(in_analog_stick_id_t stick, in_analog_stick_t *value)
{
	SDL_GameControllerAxis xaxis = stick == IN_STICK_LEFT ? SDL_CONTROLLER_AXIS_LEFTX : SDL_CONTROLLER_AXIS_RIGHTX;
	SDL_GameControllerAxis yaxis = stick == IN_STICK_LEFT ? SDL_CONTROLLER_AXIS_LEFTY : SDL_CONTROLLER_AXIS_RIGHTY;
	value->x = value->y = 0.0f;
	if (!sdl_controller) return;
	value->x = SDL_GameControllerGetAxis(sdl_controller, xaxis) / 32767.0f;
	value->y = -SDL_GameControllerGetAxis(sdl_controller, yaxis) / 32767.0f;
}
'''
new_stick = r'''void IN_GetAnalogStick(in_analog_stick_id_t stick, in_analog_stick_t *value)
{
	SDL_GameControllerAxis xaxis = stick == IN_STICK_LEFT ? SDL_CONTROLLER_AXIS_LEFTX : SDL_CONTROLLER_AXIS_RIGHTX;
	SDL_GameControllerAxis yaxis = stick == IN_STICK_LEFT ? SDL_CONTROLLER_AXIS_LEFTY : SDL_CONTROLLER_AXIS_RIGHTY;
	value->x = value->y = 0.0f;
#ifdef __ANDROID__
	if (stick == IN_STICK_LEFT && xziel_mobile_move_active) {
		value->x = xziel_mobile_move_x;
		value->y = xziel_mobile_move_y;
		return;
	}
#endif
	if (!sdl_controller) return;
	value->x = SDL_GameControllerGetAxis(sdl_controller, xaxis) / 32767.0f;
	value->y = -SDL_GameControllerGetAxis(sdl_controller, yaxis) / 32767.0f;
}
'''
if old_stick not in text:
    raise SystemExit("Could not find IN_GetAnalogStick block")
text = text.replace(old_stick, new_stick, 1)
in_sdl.write_text(text, encoding="utf-8")

sys_sdl = source / "platform" / "sdl" / "sys_sdl.c"
text = sys_sdl.read_text(encoding="utf-8")

touch_core = r'''
#ifdef __ANDROID__
#define XZIEL_MAX_TOUCHES 12

typedef enum {
	XZ_TOUCH_NONE = 0,
	XZ_TOUCH_MOVE,
	XZ_TOUCH_LOOK,
	XZ_TOUCH_FIRE,
	XZ_TOUCH_ADSFIRE,
	XZ_TOUCH_ADS,
	XZ_TOUCH_RELOAD,
	XZ_TOUCH_USE,
	XZ_TOUCH_JUMP,
	XZ_TOUCH_KNIFE,
	XZ_TOUCH_SWITCH
} xziel_touch_role_t;

typedef struct {
	qboolean active;
	SDL_FingerID finger;
	xziel_touch_role_t role;
	float last_x;
	float last_y;
} xziel_touch_slot_t;

static xziel_touch_slot_t xziel_touches[XZIEL_MAX_TOUCHES];

qboolean xziel_mobile_move_active = false;
float xziel_mobile_move_x = 0.0f;
float xziel_mobile_move_y = 0.0f;
float xziel_mobile_move_anchor_x = 0.17f;
float xziel_mobile_move_anchor_y = 0.74f;

qboolean xziel_mobile_fire_pressed = false;
qboolean xziel_mobile_adsfire_pressed = false;
qboolean xziel_mobile_ads_pressed = false;
qboolean xziel_mobile_reload_pressed = false;
qboolean xziel_mobile_use_pressed = false;
qboolean xziel_mobile_jump_pressed = false;
qboolean xziel_mobile_knife_pressed = false;
qboolean xziel_mobile_switch_pressed = false;

static int xziel_attack_refs = 0;
static int xziel_aim_refs = 0;
static qboolean xziel_attack_command_down = false;
static Uint32 xziel_attack_release_ms = 0;
static Uint32 xziel_attack_next_ms = 0;

static qboolean Xziel_IsInside(float nx, float ny, float cx, float cy, float radius_h)
{
	float px = nx * (float)vid.width;
	float py = ny * (float)vid.height;
	float bx = cx * (float)vid.width;
	float by = cy * (float)vid.height;
	float r = radius_h * (float)vid.height;
	float dx = px - bx;
	float dy = py - by;
	return dx * dx + dy * dy <= r * r;
}

static qboolean Xziel_IsAutoTapPistol(void)
{
	switch (cl.stats[STAT_ACTIVEWEAPON]) {
	case W_COLT:
	case W_357:
	case W_KILLU:
	case W_BIATCH:
		return true;
	default:
		return false;
	}
}

static void Xziel_QueueHold(const char *down, const char *up, int *refs, qboolean pressed)
{
	if (pressed) {
		(*refs)++;
		if (*refs == 1)
			Cbuf_AddText((char *)down);
	} else {
		if (*refs > 0)
			(*refs)--;
		if (*refs == 0)
			Cbuf_AddText((char *)up);
	}
}

static void Xziel_SetAttackRef(qboolean pressed)
{
	if (pressed) {
		xziel_attack_refs++;
		if (xziel_attack_refs == 1) {
			xziel_attack_next_ms = SDL_GetTicks();
			xziel_attack_release_ms = 0;
		}
	} else {
		if (xziel_attack_refs > 0)
			xziel_attack_refs--;
		if (xziel_attack_refs == 0 && xziel_attack_command_down) {
			Cbuf_AddText("-attack\n");
			xziel_attack_command_down = false;
		}
	}
}

static void Xziel_UpdateMobileFire(void)
{
	Uint32 now = SDL_GetTicks();

	if (xziel_attack_refs <= 0) {
		if (xziel_attack_command_down) {
			Cbuf_AddText("-attack\n");
			xziel_attack_command_down = false;
		}
		return;
	}

	if (!Xziel_IsAutoTapPistol()) {
		if (!xziel_attack_command_down) {
			Cbuf_AddText("+attack\n");
			xziel_attack_command_down = true;
		}
		return;
	}

	/* Semi-auto pistols require a release between shots. Generate short,
	   bounded pulses while the mobile fire control is held. Weapon fire_delay
	   remains authoritative, so this cannot exceed the weapon's real ROF. */
	if (xziel_attack_command_down && now >= xziel_attack_release_ms) {
		Cbuf_AddText("-attack\n");
		xziel_attack_command_down = false;
	}
	if (!xziel_attack_command_down && now >= xziel_attack_next_ms) {
		Cbuf_AddText("+attack\n");
		xziel_attack_command_down = true;
		xziel_attack_release_ms = now + 42;
		xziel_attack_next_ms = now + 92;
	}
}

static void Xziel_ActionDown(xziel_touch_role_t role)
{
	switch (role) {
	case XZ_TOUCH_FIRE:
		xziel_mobile_fire_pressed = true;
		Xziel_SetAttackRef(true);
		break;
	case XZ_TOUCH_ADSFIRE:
		xziel_mobile_adsfire_pressed = true;
		Xziel_SetAttackRef(true);
		Xziel_QueueHold("+aim\n", "-aim\n", &xziel_aim_refs, true);
		break;
	case XZ_TOUCH_ADS:
		xziel_mobile_ads_pressed = true;
		Xziel_QueueHold("+aim\n", "-aim\n", &xziel_aim_refs, true);
		break;
	case XZ_TOUCH_RELOAD:
		xziel_mobile_reload_pressed = true;
		Cbuf_AddText("+reload\n");
		break;
	case XZ_TOUCH_USE:
		xziel_mobile_use_pressed = true;
		Cbuf_AddText("+use\n");
		break;
	case XZ_TOUCH_JUMP:
		xziel_mobile_jump_pressed = true;
		Cbuf_AddText("+jump\n");
		break;
	case XZ_TOUCH_KNIFE:
		xziel_mobile_knife_pressed = true;
		Cbuf_AddText("+knife\n");
		break;
	case XZ_TOUCH_SWITCH:
		xziel_mobile_switch_pressed = true;
		Cbuf_AddText("+switch\n");
		break;
	default:
		break;
	}
}

static void Xziel_ActionUp(xziel_touch_role_t role)
{
	switch (role) {
	case XZ_TOUCH_FIRE:
		xziel_mobile_fire_pressed = false;
		Xziel_SetAttackRef(false);
		break;
	case XZ_TOUCH_ADSFIRE:
		xziel_mobile_adsfire_pressed = false;
		Xziel_SetAttackRef(false);
		Xziel_QueueHold("+aim\n", "-aim\n", &xziel_aim_refs, false);
		break;
	case XZ_TOUCH_ADS:
		xziel_mobile_ads_pressed = false;
		Xziel_QueueHold("+aim\n", "-aim\n", &xziel_aim_refs, false);
		break;
	case XZ_TOUCH_RELOAD:
		xziel_mobile_reload_pressed = false;
		Cbuf_AddText("-reload\n");
		break;
	case XZ_TOUCH_USE:
		xziel_mobile_use_pressed = false;
		Cbuf_AddText("-use\n");
		break;
	case XZ_TOUCH_JUMP:
		xziel_mobile_jump_pressed = false;
		Cbuf_AddText("-jump\n");
		break;
	case XZ_TOUCH_KNIFE:
		xziel_mobile_knife_pressed = false;
		Cbuf_AddText("-knife\n");
		break;
	case XZ_TOUCH_SWITCH:
		xziel_mobile_switch_pressed = false;
		Cbuf_AddText("-switch\n");
		break;
	default:
		break;
	}
}

static xziel_touch_slot_t *Xziel_FindTouch(SDL_FingerID finger)
{
	int i;
	for (i = 0; i < XZIEL_MAX_TOUCHES; ++i)
		if (xziel_touches[i].active && xziel_touches[i].finger == finger)
			return &xziel_touches[i];
	return NULL;
}

static xziel_touch_slot_t *Xziel_AllocTouch(SDL_FingerID finger)
{
	int i;
	for (i = 0; i < XZIEL_MAX_TOUCHES; ++i) {
		if (!xziel_touches[i].active) {
			memset(&xziel_touches[i], 0, sizeof(xziel_touches[i]));
			xziel_touches[i].active = true;
			xziel_touches[i].finger = finger;
			return &xziel_touches[i];
		}
	}
	return NULL;
}

static xziel_touch_role_t Xziel_RoleForPoint(float x, float y)
{
	/* Button cluster: COD-style separation leaves the middle-right area open
	   for free-look while keeping fire controls reachable by the thumb. */
	if (Xziel_IsInside(x, y, 0.885f, 0.585f, 0.073f)) return XZ_TOUCH_FIRE;
	if (Xziel_IsInside(x, y, 0.795f, 0.435f, 0.056f)) return XZ_TOUCH_ADSFIRE;
	if (Xziel_IsInside(x, y, 0.695f, 0.575f, 0.047f)) return XZ_TOUCH_ADS;
	if (Xziel_IsInside(x, y, 0.805f, 0.785f, 0.044f)) return XZ_TOUCH_RELOAD;
	if (Xziel_IsInside(x, y, 0.605f, 0.675f, 0.044f)) return XZ_TOUCH_USE;
	if (Xziel_IsInside(x, y, 0.695f, 0.790f, 0.044f)) return XZ_TOUCH_JUMP;
	if (Xziel_IsInside(x, y, 0.915f, 0.800f, 0.044f)) return XZ_TOUCH_KNIFE;
	if (Xziel_IsInside(x, y, 0.905f, 0.300f, 0.041f)) return XZ_TOUCH_SWITCH;
	if (x < 0.45f && y > 0.30f) return XZ_TOUCH_MOVE;
	return XZ_TOUCH_LOOK;
}

static void Xziel_UpdateMove(float x, float y)
{
	float dx, dy, len, radius_x, radius_y;
	radius_x = 0.16f * ((float)vid.height / (float)vid.width);
	radius_y = 0.16f;
	dx = (x - xziel_mobile_move_anchor_x) / radius_x;
	dy = (xziel_mobile_move_anchor_y - y) / radius_y;
	len = sqrtf(dx * dx + dy * dy);
	if (len < 0.10f) {
		xziel_mobile_move_x = 0.0f;
		xziel_mobile_move_y = 0.0f;
		return;
	}
	if (len > 1.0f) {
		dx /= len;
		dy /= len;
	}
	xziel_mobile_move_x = dx;
	xziel_mobile_move_y = dy;
}

static void Xziel_ReleaseAllTouches(void)
{
	int i;
	for (i = 0; i < XZIEL_MAX_TOUCHES; ++i) {
		if (!xziel_touches[i].active)
			continue;
		Xziel_ActionUp(xziel_touches[i].role);
		xziel_touches[i].active = false;
	}
	xziel_mobile_move_active = false;
	xziel_mobile_move_x = 0.0f;
	xziel_mobile_move_y = 0.0f;
	if (xziel_attack_command_down) {
		Cbuf_AddText("-attack\n");
		xziel_attack_command_down = false;
	}
	xziel_attack_refs = 0;
	if (xziel_aim_refs > 0)
		Cbuf_AddText("-aim\n");
	xziel_aim_refs = 0;
}

static void Xziel_MenuFinger(float x, float y, qboolean down, qboolean motion)
{
	int mx = (int)(x * (float)vid.width);
	int my = (int)(y * (float)vid.height);
	qboolean slider_handled = false;

	Menu_MouseMove(mx, my);
	if (motion)
		return;

	if (down) {
		slider_handled = Menu_MouseButton(mx, my, true);
		if (!slider_handled)
			Menu_ButtonPress();
	} else {
		Menu_MouseButton(mx, my, false);
	}
}

static void Xziel_FingerDown(const SDL_TouchFingerEvent *finger)
{
	xziel_touch_slot_t *slot;
	xziel_touch_role_t role;

	IN_SetActiveDevice(IN_DEVICE_KEYBOARD_MOUSE);
	Menu_SetInputDevice(IN_DEVICE_KEYBOARD_MOUSE);

	if (cl.stats[STAT_HEALTH] <= 0 && key_dest == key_game) {
		Xziel_ReleaseAllTouches();
		Menu_ExitMap();
		return;
	}

	if (key_dest == key_menu || key_dest == key_menu_pause) {
		Xziel_MenuFinger(finger->x, finger->y, true, false);
		return;
	}

	if (key_dest != key_game)
		return;

	slot = Xziel_AllocTouch(finger->fingerId);
	if (!slot)
		return;

	role = Xziel_RoleForPoint(finger->x, finger->y);
	slot->role = role;
	slot->last_x = finger->x;
	slot->last_y = finger->y;

	if (role == XZ_TOUCH_MOVE) {
		xziel_mobile_move_active = true;
		xziel_mobile_move_anchor_x = finger->x;
		xziel_mobile_move_anchor_y = finger->y;
		Xziel_UpdateMove(finger->x, finger->y);
	} else if (role != XZ_TOUCH_LOOK) {
		Xziel_ActionDown(role);
	}
}

static void Xziel_FingerMotion(const SDL_TouchFingerEvent *finger)
{
	xziel_touch_slot_t *slot;

	if (key_dest == key_menu || key_dest == key_menu_pause) {
		Xziel_MenuFinger(finger->x, finger->y, false, true);
		return;
	}

	slot = Xziel_FindTouch(finger->fingerId);
	if (!slot)
		return;

	if (slot->role == XZ_TOUCH_MOVE) {
		Xziel_UpdateMove(finger->x, finger->y);
	} else if (slot->role == XZ_TOUCH_LOOK ||
		slot->role == XZ_TOUCH_FIRE ||
		slot->role == XZ_TOUCH_ADSFIRE ||
		slot->role == XZ_TOUCH_ADS) {
		/* Free-look remains active while dragging FIRE/ADS controls, matching
		   modern mobile FPS behavior. */
		mouse_dx += (int)((finger->x - slot->last_x) * (float)vid.width);
		mouse_dy += (int)((finger->y - slot->last_y) * (float)vid.height);
	}
	slot->last_x = finger->x;
	slot->last_y = finger->y;
}

static void Xziel_FingerUp(const SDL_TouchFingerEvent *finger)
{
	xziel_touch_slot_t *slot;

	if (key_dest == key_menu || key_dest == key_menu_pause) {
		Xziel_MenuFinger(finger->x, finger->y, false, false);
		return;
	}

	slot = Xziel_FindTouch(finger->fingerId);
	if (!slot)
		return;

	if (slot->role == XZ_TOUCH_MOVE) {
		xziel_mobile_move_active = false;
		xziel_mobile_move_x = 0.0f;
		xziel_mobile_move_y = 0.0f;
	} else if (slot->role != XZ_TOUCH_LOOK) {
		Xziel_ActionUp(slot->role);
	}
	slot->active = false;
}
#endif
'''

mouse_anchor = "int mouse_dx;\nint mouse_dy;\n"
if touch_core not in text:
    if mouse_anchor not in text:
        raise SystemExit("Could not find SDL mouse globals anchor")
    text = text.replace(mouse_anchor, mouse_anchor + touch_core, 1)

# Android system Back behaves like Escape; on Game Over it exits the map.
key_anchor = "case SDLK_ESCAPE: return K_ESCAPE; case SDLK_RETURN: case SDLK_KP_ENTER: return K_ENTER;"
key_repl = """case SDLK_ESCAPE: return K_ESCAPE;
#ifdef __ANDROID__
\tcase SDLK_AC_BACK: return K_ESCAPE;
#endif
\tcase SDLK_RETURN: case SDLK_KP_ENTER: return K_ENTER;"""
if key_anchor not in text:
    raise SystemExit("Could not find SDL key mapping anchor")
text = text.replace(key_anchor, key_repl, 1)

# Handle direct finger events before synthetic mouse events.
event_anchor = "\t\tcase SDL_MOUSEBUTTONDOWN: case SDL_MOUSEBUTTONUP:\n"
event_repl = r'''#ifdef __ANDROID__
		case SDL_FINGERDOWN:
			Xziel_FingerDown(&event.tfinger);
			break;
		case SDL_FINGERMOTION:
			Xziel_FingerMotion(&event.tfinger);
			break;
		case SDL_FINGERUP:
			Xziel_FingerUp(&event.tfinger);
			break;
#endif
		case SDL_MOUSEBUTTONDOWN: case SDL_MOUSEBUTTONUP:
'''
if event_anchor not in text:
    raise SystemExit("Could not find SDL event insertion anchor")
text = text.replace(event_anchor, event_repl, 1)

# Back key shortcut for the end screen.
keydown_anchor = """\t\tcase SDL_KEYDOWN: case SDL_KEYUP:
\t\t\tif (event.type == SDL_KEYDOWN) { IN_SetActiveDevice(IN_DEVICE_KEYBOARD_MOUSE); Menu_SetInputDevice(IN_DEVICE_KEYBOARD_MOUSE); }
"""
keydown_repl = """\t\tcase SDL_KEYDOWN: case SDL_KEYUP:
\t\t\tif (event.type == SDL_KEYDOWN) { IN_SetActiveDevice(IN_DEVICE_KEYBOARD_MOUSE); Menu_SetInputDevice(IN_DEVICE_KEYBOARD_MOUSE); }
#ifdef __ANDROID__
\t\t\tif (event.type == SDL_KEYDOWN && event.key.keysym.sym == SDLK_AC_BACK &&
\t\t\t\tcl.stats[STAT_HEALTH] <= 0 && key_dest == key_game) {
\t\t\t\tXziel_ReleaseAllTouches();
\t\t\t\tMenu_ExitMap();
\t\t\t\tbreak;
\t\t\t}
#endif
"""
if keydown_anchor not in text:
    raise SystemExit("Could not find SDL keydown block")
text = text.replace(keydown_anchor, keydown_repl, 1)

# Release held virtual buttons if Android loses focus, and advance auto-fire
# once per input pump.
window_anchor = """\t\tcase SDL_WINDOWEVENT:
\t\t\tif (event.window.event == SDL_WINDOWEVENT_SIZE_CHANGED || event.window.event == SDL_WINDOWEVENT_RESIZED)
\t\t\t\tVID_SDLResize();
\t\t\tbreak;
"""
window_repl = """\t\tcase SDL_WINDOWEVENT:
\t\t\tif (event.window.event == SDL_WINDOWEVENT_SIZE_CHANGED || event.window.event == SDL_WINDOWEVENT_RESIZED)
\t\t\t\tVID_SDLResize();
#ifdef __ANDROID__
\t\t\tif (event.window.event == SDL_WINDOWEVENT_FOCUS_LOST ||
\t\t\t\tevent.window.event == SDL_WINDOWEVENT_MINIMIZED)
\t\t\t\tXziel_ReleaseAllTouches();
#endif
\t\t\tbreak;
"""
if window_anchor not in text:
    raise SystemExit("Could not find SDL window-event block")
text = text.replace(window_anchor, window_repl, 1)

pump_anchor = """\t}
\tSDL_SetRelativeMouseMode((key_dest == key_game && SDL_GetKeyboardFocus() == sdl_window) ? SDL_TRUE : SDL_FALSE);
}
"""
pump_repl = """\t}
#ifdef __ANDROID__
\tXziel_UpdateMobileFire();
\t/* Touch is handled directly above. Avoid Android relative-mouse capture and
\t   SDL's touch-mouse path fighting the mobile camera. */
\tSDL_SetRelativeMouseMode(SDL_FALSE);
#else
\tSDL_SetRelativeMouseMode((key_dest == key_game && SDL_GetKeyboardFocus() == sdl_window) ? SDL_TRUE : SDL_FALSE);
#endif
}
"""
if pump_anchor not in text:
    raise SystemExit("Could not find SDL event-pump tail")
text = text.replace(pump_anchor, pump_repl, 1)

# Stop SDL from synthesizing mouse button/motion events for finger input.
hint_anchor = """#ifdef __ANDROID__
\tSDL_SetHintWithPriority(SDL_HINT_ORIENTATIONS,
\t\t"LandscapeLeft LandscapeRight", SDL_HINT_OVERRIDE);
#endif
"""
hint_repl = """#ifdef __ANDROID__
\tSDL_SetHintWithPriority(SDL_HINT_ORIENTATIONS,
\t\t"LandscapeLeft LandscapeRight", SDL_HINT_OVERRIDE);
\tSDL_SetHintWithPriority(SDL_HINT_TOUCH_MOUSE_EVENTS, "0", SDL_HINT_OVERRIDE);
#endif
"""
if hint_anchor not in text:
    raise SystemExit("Could not find Android SDL hint block")
text = text.replace(hint_anchor, hint_repl, 1)

sys_sdl.write_text(text, encoding="utf-8")

# Draw a native mobile HUD over the existing game HUD. No external artwork is
# used; controls are translucent geometry/text so they can be restyled later.
hud = source / "render" / "r_hud.c"
text = hud.read_text(encoding="utf-8")

mobile_hud = r'''
#ifdef __ANDROID__
extern qboolean xziel_mobile_move_active;
extern float xziel_mobile_move_x;
extern float xziel_mobile_move_y;
extern float xziel_mobile_move_anchor_x;
extern float xziel_mobile_move_anchor_y;
extern qboolean xziel_mobile_fire_pressed;
extern qboolean xziel_mobile_adsfire_pressed;
extern qboolean xziel_mobile_ads_pressed;
extern qboolean xziel_mobile_reload_pressed;
extern qboolean xziel_mobile_use_pressed;
extern qboolean xziel_mobile_jump_pressed;
extern qboolean xziel_mobile_knife_pressed;
extern qboolean xziel_mobile_switch_pressed;

static void Xziel_DrawDisc(int cx, int cy, int radius, int r, int g, int b, int a)
{
	int y;
	int step = radius / 10;
	if (step < 2) step = 2;
	for (y = -radius; y <= radius; y += step) {
		float fy = (float)y;
		int half = (int)sqrtf((float)(radius * radius) - fy * fy);
		Draw_FillByColor(cx - half, cy + y, half * 2, step + 1, r, g, b, a);
	}
}

static void Xziel_DrawTouchButton(float nx, float ny, float radius_h,
	const char *label1, const char *label2, qboolean pressed)
{
	int cx = (int)(nx * vid.width);
	int cy = (int)(ny * vid.height);
	int radius = (int)(radius_h * vid.height);
	int inner = radius - (int)(2.0f * vid.scale);
	float text_scale = vid.scale * 0.70f;
	int tw;

	if (inner < 2) inner = 2;
	Xziel_DrawDisc(cx, cy, radius, 235, 235, 235, pressed ? 150 : 95);
	Xziel_DrawDisc(cx, cy, inner, pressed ? 110 : 8, pressed ? 18 : 8,
		pressed ? 18 : 8, pressed ? 155 : 105);

	if (label1 && label1[0]) {
		tw = getTextWidth((char *)label1, text_scale);
		Draw_ColoredString(cx - tw / 2,
			cy - (label2 && label2[0] ? (int)(7 * vid.scale) : (int)(3 * vid.scale)),
			(char *)label1, 255, 255, 255, 235, text_scale);
	}
	if (label2 && label2[0]) {
		tw = getTextWidth((char *)label2, text_scale);
		Draw_ColoredString(cx - tw / 2, cy + (int)(3 * vid.scale),
			(char *)label2, 255, 255, 255, 235, text_scale);
	}
}

static void Xziel_MobileHUD_Draw(void)
{
	int base_x, base_y, knob_x, knob_y, radius, knob_r;

	if (key_dest != key_game || cl.stats[STAT_HEALTH] <= 0)
		return;

	/* Dynamic joystick, with a faint home position before first touch. */
	base_x = (int)((xziel_mobile_move_active ? xziel_mobile_move_anchor_x : 0.17f) * vid.width);
	base_y = (int)((xziel_mobile_move_active ? xziel_mobile_move_anchor_y : 0.74f) * vid.height);
	radius = (int)(0.095f * vid.height);
	knob_r = (int)(0.042f * vid.height);
	Xziel_DrawDisc(base_x, base_y, radius, 240, 240, 240, 55);
	Xziel_DrawDisc(base_x, base_y, radius - (int)(2 * vid.scale), 0, 0, 0, 45);
	knob_x = base_x + (int)(xziel_mobile_move_x * radius * 0.72f);
	knob_y = base_y - (int)(xziel_mobile_move_y * radius * 0.72f);
	Xziel_DrawDisc(knob_x, knob_y, knob_r, 245, 245, 245,
		xziel_mobile_move_active ? 125 : 70);

	Xziel_DrawTouchButton(0.885f, 0.585f, 0.073f, "FIRE", "", xziel_mobile_fire_pressed);
	Xziel_DrawTouchButton(0.795f, 0.435f, 0.056f, "ADS", "FIRE", xziel_mobile_adsfire_pressed);
	Xziel_DrawTouchButton(0.695f, 0.575f, 0.047f, "ADS", "", xziel_mobile_ads_pressed);
	Xziel_DrawTouchButton(0.805f, 0.785f, 0.044f, "RLD", "", xziel_mobile_reload_pressed);
	Xziel_DrawTouchButton(0.605f, 0.675f, 0.044f, "USE", "", xziel_mobile_use_pressed);
	Xziel_DrawTouchButton(0.695f, 0.790f, 0.044f, "JUMP", "", xziel_mobile_jump_pressed);
	Xziel_DrawTouchButton(0.915f, 0.800f, 0.044f, "KNIFE", "", xziel_mobile_knife_pressed);
	Xziel_DrawTouchButton(0.905f, 0.300f, 0.041f, "SWAP", "", xziel_mobile_switch_pressed);
}

static void Xziel_MobileGameOverPrompt(void)
{
	const char *msg = "TAP TO RETURN TO MENU";
	float s = vid.scale;
	int w = getTextWidth((char *)msg, s);
	Draw_ColoredString((vid.width - w) / 2, vid.height - (int)(28 * vid.scale),
		(char *)msg, 255, 255, 255, 235, s);
}
#endif
'''

hud_anchor = "void\nHUD_Draw(void)\n{"
if mobile_hud not in text:
    if hud_anchor not in text:
        raise SystemExit("Could not find HUD_Draw anchor")
    text = text.replace(hud_anchor, mobile_hud + "\n" + hud_anchor, 1)

gameover_anchor = """    if (cl.stats[STAT_HEALTH] <= 0 || showscoreboard == true) {
        HUD_EndScreen();

        // Make sure we still draw the screen flash.
"""
gameover_repl = """    if (cl.stats[STAT_HEALTH] <= 0 || showscoreboard == true) {
        HUD_EndScreen();
#ifdef __ANDROID__
        if (cl.stats[STAT_HEALTH] <= 0)
            Xziel_MobileGameOverPrompt();
#endif

        // Make sure we still draw the screen flash.
"""
if gameover_anchor not in text:
    raise SystemExit("Could not find HUD game-over block")
text = text.replace(gameover_anchor, gameover_repl, 1)

zoom_anchor = """    if (cl.stats[STAT_ZOOM] == 2) {
        if (screenflash_duration > sv.time)
            HUD_Screenflash();
        return;
    }
"""
zoom_repl = """    if (cl.stats[STAT_ZOOM] == 2) {
        if (screenflash_duration > sv.time)
            HUD_Screenflash();
#ifdef __ANDROID__
        Xziel_MobileHUD_Draw();
#endif
        return;
    }
"""
if zoom_anchor not in text:
    raise SystemExit("Could not find scoped HUD block")
text = text.replace(zoom_anchor, zoom_repl, 1)

gamemode_anchor = """        if (screenflash_duration > sv.time)
            HUD_Screenflash();

        return;
    }

    if (bettyprompt_time > sv.time)
"""
gamemode_repl = """        if (screenflash_duration > sv.time)
            HUD_Screenflash();
#ifdef __ANDROID__
        Xziel_MobileHUD_Draw();
#endif

        return;
    }

    if (bettyprompt_time > sv.time)
"""
if gamemode_anchor not in text:
    raise SystemExit("Could not find special gamemode HUD block")
text = text.replace(gamemode_anchor, gamemode_repl, 1)

hud_tail = """    // This should always come last!
    if (screenflash_duration > sv.time)
        HUD_Screenflash();
} /* HUD_Draw */
"""
hud_tail_repl = """    // This should always come last!
    if (screenflash_duration > sv.time)
        HUD_Screenflash();
#ifdef __ANDROID__
    Xziel_MobileHUD_Draw();
#endif
} /* HUD_Draw */
"""
if hud_tail not in text:
    raise SystemExit("Could not find HUD tail")
text = text.replace(hud_tail, hud_tail_repl, 1)

hud.write_text(text, encoding="utf-8")
