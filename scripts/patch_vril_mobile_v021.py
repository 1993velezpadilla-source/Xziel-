#!/usr/bin/env python3
"""Xziel v0.21 mobile controls/handling/threat polish.

Applied after v0.20 HUD and combat feedback so this script owns final mobile
input/UI behavior for the release candidate.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_vril_mobile_v021.py <vril-root>")

root = Path(sys.argv[1])
source = root / "source"

def replace_function(src: str, signature: str, replacement: str) -> str:
    start = src.find(signature)
    if start < 0:
        raise SystemExit("Could not find function: " + signature)
    brace = src.find("{", start)
    if brace < 0:
        raise SystemExit("Could not find function body: " + signature)
    depth = 0
    end = -1
    for i in range(brace, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end < 0:
        raise SystemExit("Could not find function end: " + signature)
    return src[:start] + replacement + src[end:]

def insert_after(src: str, anchor: str, payload: str, label: str) -> str:
    if payload.strip() in src:
        return src
    if anchor not in src:
        raise SystemExit("Missing anchor: " + label)
    return src.replace(anchor, anchor + payload, 1)

# ---------------------------------------------------------------------------
# Persistent mobile movement + new crouch/slide HUD cvars
# ---------------------------------------------------------------------------
inp = source / "input.c"
text = inp.read_text(encoding="utf-8")

cvar_anchor = 'cvar_t xziel_mobile_ads_sensitivity = {"xziel_mobile_ads_sensitivity", "0.62", true};\n'
cvars = r'''cvar_t xziel_mobile_joystick_sensitivity = {"xziel_mobile_joystick_sensitivity", "1.00", true};
cvar_t xziel_mobile_ads_move_sensitivity = {"xziel_mobile_ads_move_sensitivity", "0.90", true};
'''
if "xziel_mobile_joystick_sensitivity" not in text:
    text = insert_after(text, cvar_anchor, cvars, "movement cvars")

style_anchor = 'cvar_t xziel_hud_grenade_opacity = {"xziel_hud_grenade_opacity", "0.82", true};\n'
slide_cvars = r'''cvar_t xziel_hud_slide_x = {"xziel_hud_slide_x", "0.745", true};
cvar_t xziel_hud_slide_y = {"xziel_hud_slide_y", "0.825", true};
cvar_t xziel_hud_slide_scale = {"xziel_hud_slide_scale", "1.00", true};
cvar_t xziel_hud_slide_opacity = {"xziel_hud_slide_opacity", "0.82", true};
'''
if "xziel_hud_slide_x" not in text:
    text = insert_after(text, style_anchor, slide_cvars, "slide cvars")

reg_anchor = "\tCvar_RegisterVariable(&xziel_mobile_ads_sensitivity);\n"
regs = """\tCvar_RegisterVariable(&xziel_mobile_joystick_sensitivity);
\tCvar_RegisterVariable(&xziel_mobile_ads_move_sensitivity);
"""
if "Cvar_RegisterVariable(&xziel_mobile_joystick_sensitivity);" not in text:
    text = insert_after(text, reg_anchor, regs, "movement cvar registrations")

style_reg_anchor = "\tCvar_RegisterVariable(&xziel_hud_grenade_opacity);\n"
style_regs = """\tCvar_RegisterVariable(&xziel_hud_slide_x);
\tCvar_RegisterVariable(&xziel_hud_slide_y);
\tCvar_RegisterVariable(&xziel_hud_slide_scale);
\tCvar_RegisterVariable(&xziel_hud_slide_opacity);
"""
if "Cvar_RegisterVariable(&xziel_hud_slide_x);" not in text:
    text = insert_after(text, style_reg_anchor, style_regs, "slide cvar registrations")

inp.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# Touch runtime
# ---------------------------------------------------------------------------
sdl = source / "platform" / "sdl" / "sys_sdl.c"
text = sdl.read_text(encoding="utf-8")

extern_anchor = "extern cvar_t xziel_mobile_ads_sensitivity;\n"
externs = """extern cvar_t xziel_mobile_joystick_sensitivity;
extern cvar_t xziel_mobile_ads_move_sensitivity;
extern cvar_t xziel_hud_slide_x;
extern cvar_t xziel_hud_slide_y;
extern cvar_t xziel_hud_slide_scale;
extern cvar_t xziel_hud_slide_opacity;
"""
if "extern cvar_t xziel_mobile_joystick_sensitivity;" not in text:
    text = insert_after(text, extern_anchor, externs, "SDL movement externs")

# Append a new role so every existing editor role number remains stable.
enum_end = "} xziel_touch_role_t;"
if "XZ_TOUCH_SLIDE" not in text:
    enum_pos = text.find(enum_end)
    if enum_pos < 0:
        raise SystemExit("Could not find touch-role enum end")
    before = text[:enum_pos].rstrip()
    if not before.endswith(","):
        before += ","
    text = before + "\n\tXZ_TOUCH_SLIDE\n" + text[enum_pos:]

state_anchor = "static int xziel_menu_confirm_state = -1;\n"
if "xziel_mobile_slide_pressed" not in text:
    text = insert_after(
        text, state_anchor,
        "static qboolean xziel_mobile_slide_pressed = false;\n",
        "slide pressed state"
    )

# Weapon-class ADS movement is intentionally relative. COD-style modern
# handling gives light weapons more ADS mobility and heavy/precision weapons
# less, while the user-facing slider remains the master preference.
move_func = r'''static void Xziel_UpdateMove(float x, float y)
{
	float raw_dx, raw_dy, dx, dy, len, radius_x, radius_y;
	float sprint_zone;
	float response;
	float ads_walk = 1.0f;
	float class_walk = 1.0f;
	Uint32 now = SDL_GetTicks();

	radius_x = 0.16f * ((float)vid.height / (float)vid.width);
	radius_y = 0.16f;
	raw_dx = (x - xziel_mobile_move_anchor_x) / radius_x;
	raw_dy = (xziel_mobile_move_anchor_y - y) / radius_y;

	dx = raw_dx;
	dy = raw_dy;
	len = sqrtf(dx * dx + dy * dy);

	if (len < 0.10f) {
		xziel_mobile_move_x = 0.0f;
		xziel_mobile_move_y = 0.0f;
		xziel_mobile_sprint_zone_hot = false;
		if (xziel_mobile_sprint_active || cl.stats[STAT_ZOOM] == 3) {
			Cbuf_AddText("impulse 24\n");
			Cbuf_Execute();
		}
		xziel_mobile_sprint_active = false;
		xziel_mobile_sprint_suppressed = false;
		xziel_mobile_sprint_retry_ms = 0;
		return;
	}

	if (len > 1.0f) {
		dx /= len;
		dy /= len;
	}

	response = xziel_mobile_joystick_sensitivity.value;
	if (response < 0.50f) response = 0.50f;
	if (response > 2.00f) response = 2.00f;
	dx *= response;
	dy *= response;

	if (cl.stats[STAT_ZOOM] == 1 || cl.stats[STAT_ZOOM] == 2) {
		ads_walk = xziel_mobile_ads_move_sensitivity.value;
		if (ads_walk < 0.35f) ads_walk = 0.35f;
		if (ads_walk > 1.25f) ads_walk = 1.25f;

		switch (cl.stats[STAT_ACTIVEWEAPON]) {
		case W_COLT:
		case W_357:
		case W_KILLU:
			class_walk = 1.00f; break;

		case W_THOMPSON:
		case W_GIBS:
		case W_MP40:
		case W_AFTERBURNER:
		case W_PPSH:
		case W_REAPER:
		case W_MP5:
		case W_KOLLIDER:
			class_walk = 0.94f; break;

		case W_DB:
		case W_BORE:
		case W_SAWNOFF:
		case W_TRENCH:
		case W_GUT:
			class_walk = 0.88f; break;

		case W_BROWNING:
		case W_ACCELERATOR:
		case W_MG:
		case W_BARRACUDA:
			class_walk = 0.72f; break;

		case W_KAR_SCOPE:
		case W_HEADCRACKER:
		case W_PTRS:
		case W_PENETRATOR:
		case W_KAR:
		case W_ARMAGEDDON:
		case W_SPRING:
		case W_PULVERIZER:
			class_walk = 0.68f; break;

		case W_PANZER:
		case W_LONGINUS:
			class_walk = 0.66f; break;

		case W_RAY:
		case W_PORTER:
		case W_RAYMK2:
		case W_PORTERMK2:
		case W_TESLA:
		case W_DG3:
			class_walk = 0.82f; break;

		default:
			class_walk = 0.83f; break;
		}

		dx *= ads_walk * class_walk;
		dy *= ads_walk * class_walk;
	}

	len = sqrtf(dx * dx + dy * dy);
	if (len > 1.0f) {
		dx /= len;
		dy /= len;
	}

	xziel_mobile_move_x = dx;
	xziel_mobile_move_y = dy;

	sprint_zone = xziel_mobile_sprint_zone.value;
	if (sprint_zone < 1.10f) sprint_zone = 1.10f;
	if (sprint_zone > 1.85f) sprint_zone = 1.85f;

	/* Sprint target uses the raw physical stick travel, not response/ADS
	   scaling, so changing sensitivity never makes sprint harder to trigger. */
	xziel_mobile_sprint_zone_hot =
		raw_dy >= sprint_zone &&
		fabsf(raw_dx) <= raw_dy * 0.70f;

	if (xziel_mobile_sprint_zone_hot) {
		if (!xziel_mobile_sprint_suppressed) {
			if (cl.stats[STAT_ZOOM] == 1 ||
				cl.stats[STAT_ZOOM] == 2 ||
				xziel_aim_refs > 0 ||
				xziel_adsfire_release_pending ||
				xziel_adsfire_release_requested ||
				xziel_adsfire_attack_engaged ||
				xziel_adsfire_temp_aim ||
				xziel_release_shot_active ||
				xziel_marksman_sticky_ads ||
				xziel_mobile_ads_latched) {
				Xziel_ForceExitAdsForSprint();
			}

			if (cl.stats[STAT_ZOOM] != 3 && now >= xziel_mobile_sprint_retry_ms) {
				Cbuf_AddText("impulse 23\n");
				Cbuf_Execute();
				xziel_mobile_sprint_retry_ms = now + 120;
			}
			xziel_mobile_sprint_active = true;
		}
	} else {
		if (xziel_mobile_sprint_active || cl.stats[STAT_ZOOM] == 3) {
			Cbuf_AddText("impulse 24\n");
			Cbuf_Execute();
		}
		xziel_mobile_sprint_active = false;
		xziel_mobile_sprint_suppressed = false;
		xziel_mobile_sprint_retry_ms = 0;
	}
}'''
text = replace_function(text, "static void Xziel_UpdateMove(float x, float y)", move_func)

# Critical regression fix: v0.18 rebuilt FingerDown but omitted this flag.
needle = """\tif (slot->role == XZ_TOUCH_MOVE) {
\t\txziel_mobile_move_anchor_x = xziel_hud_joy_x.value;
"""
replacement = """\tif (slot->role == XZ_TOUCH_MOVE) {
\t\txziel_mobile_move_active = true;
\t\txziel_mobile_move_anchor_x = xziel_hud_joy_x.value;
"""
if "xziel_mobile_move_active = true;" not in text[text.find("static void Xziel_FingerDown"):text.find("static void Xziel_FingerMotion")]:
    if needle not in text:
        raise SystemExit("Could not find final FingerDown movement block")
    text = text.replace(needle, replacement, 1)

# Hit-test / editor support for the new Crouch/Slide control.
role_old = "\tif (Xziel_IsInside(x, y, xziel_hud_jump_x.value, xziel_hud_jump_y.value, 0.044f * hs * xziel_hud_jump_scale.value)) return XZ_TOUCH_JUMP;\n"
role_new = """\tif (Xziel_IsInside(x, y, xziel_hud_slide_x.value, xziel_hud_slide_y.value, 0.044f * hs * xziel_hud_slide_scale.value)) return XZ_TOUCH_SLIDE;
""" + role_old
role_start = text.find("static xziel_touch_role_t Xziel_RoleForPoint")
role_end = text.find("static xziel_touch_role_t Xziel_HudEditorRole", role_start)
role_chunk = text[role_start:role_end]
if "XZ_TOUCH_SLIDE" not in role_chunk:
    if role_old not in role_chunk:
        raise SystemExit("Could not find gameplay jump hitbox")
    role_chunk = role_chunk.replace(role_old, role_new, 1)
    text = text[:role_start] + role_chunk + text[role_end:]

editor_old = "\tif (Xziel_IsInside(x, y, xziel_hud_jump_x.value, xziel_hud_jump_y.value, 0.060f * hs * xziel_hud_jump_scale.value)) return XZ_TOUCH_JUMP;\n"
editor_new = """\tif (Xziel_IsInside(x, y, xziel_hud_slide_x.value, xziel_hud_slide_y.value, 0.060f * hs * xziel_hud_slide_scale.value)) return XZ_TOUCH_SLIDE;
""" + editor_old
editor_start = text.find("static xziel_touch_role_t Xziel_HudEditorRole")
editor_end = text.find("static void Xziel_HudEditorSetPosition", editor_start)
editor_chunk = text[editor_start:editor_end]
if "XZ_TOUCH_SLIDE" not in editor_chunk:
    if editor_old not in editor_chunk:
        raise SystemExit("Could not find editor jump hitbox")
    editor_chunk = editor_chunk.replace(editor_old, editor_new, 1)
    text = text[:editor_start] + editor_chunk + text[editor_end:]

set_start = text.find("static void Xziel_HudEditorSetPosition")
set_end = text.find("static void Xziel_FingerDown", set_start)
set_chunk = text[set_start:set_end]
set_anchor = '\tcase XZ_TOUCH_JUMP: Cvar_SetValue("xziel_hud_jump_x", x); Cvar_SetValue("xziel_hud_jump_y", y); break;\n'
set_insert = '\tcase XZ_TOUCH_SLIDE: Cvar_SetValue("xziel_hud_slide_x", x); Cvar_SetValue("xziel_hud_slide_y", y); break;\n'
if "case XZ_TOUCH_SLIDE:" not in set_chunk:
    if set_anchor not in set_chunk:
        raise SystemExit("Could not find editor jump position case")
    set_chunk = set_chunk.replace(set_anchor, set_insert + set_anchor, 1)
    text = text[:set_start] + set_chunk + text[set_end:]

# One-shot mobile crouch/slide action. Server QC decides crouch vs slide.
down_start = text.find("static void Xziel_ActionDown(xziel_touch_role_t role)")
down_end = text.find("static void Xziel_ActionUp(xziel_touch_role_t role)", down_start)
down_chunk = text[down_start:down_end]
down_anchor = "\tcase XZ_TOUCH_JUMP:\n"
slide_down = """\tcase XZ_TOUCH_SLIDE:
\t\txziel_mobile_slide_pressed = true;
\t\tCbuf_AddText("impulse 34\\n");
\t\tCbuf_Execute();
\t\tbreak;

"""
if "case XZ_TOUCH_SLIDE:" not in down_chunk:
    if down_anchor not in down_chunk:
        raise SystemExit("Could not find ActionDown jump case")
    down_chunk = down_chunk.replace(down_anchor, slide_down + down_anchor, 1)
    text = text[:down_start] + down_chunk + text[down_end:]

up_start = text.find("static void Xziel_ActionUp(xziel_touch_role_t role)")
up_end = text.find("static xziel_touch_slot_t *Xziel_FindTouch", up_start)
up_chunk = text[up_start:up_end]
up_anchor = "\tcase XZ_TOUCH_JUMP:\n"
slide_up = """\tcase XZ_TOUCH_SLIDE:
\t\txziel_mobile_slide_pressed = false;
\t\tbreak;

"""
if "case XZ_TOUCH_SLIDE:" not in up_chunk:
    if up_anchor not in up_chunk:
        raise SystemExit("Could not find ActionUp jump case")
    up_chunk = up_chunk.replace(up_anchor, slide_up + up_anchor, 1)
    text = text[:up_start] + up_chunk + text[up_end:]

# Class-aware visual ADS timing. This is presentation/input gating only;
# native weapon fire delay remains authoritative.
ads_delay = r'''static Uint32 Xziel_AdsVisualDelayMs(void)
{
	switch (cl.stats[STAT_ACTIVEWEAPON]) {
	case W_COLT:
	case W_357:
	case W_KILLU:
		return 115;

	case W_THOMPSON:
	case W_GIBS:
	case W_MP40:
	case W_AFTERBURNER:
	case W_PPSH:
	case W_REAPER:
	case W_MP5:
	case W_KOLLIDER:
		return 130;

	case W_DB:
	case W_BORE:
	case W_SAWNOFF:
	case W_TRENCH:
	case W_GUT:
		return 150;

	case W_BROWNING:
	case W_ACCELERATOR:
	case W_MG:
	case W_BARRACUDA:
		return 195;

	case W_KAR:
	case W_ARMAGEDDON:
	case W_SPRING:
	case W_PULVERIZER:
	case W_GEWEHR:
	case W_COMPRESSOR:
	case W_M1:
	case W_M1000:
	case W_M1A1:
	case W_WIDDER:
		return 190;

	case W_KAR_SCOPE:
	case W_HEADCRACKER:
	case W_PTRS:
	case W_PENETRATOR:
		return 220;

	default:
		return 165;
	}
}'''
text = replace_function(text, "static Uint32 Xziel_AdsVisualDelayMs(void)", ads_delay)

sdl.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# HUD: slide icon/button + broader resize range
# ---------------------------------------------------------------------------
hud = source / "render" / "r_hud.c"
text = hud.read_text(encoding="utf-8")

hud_ext_anchor = "extern cvar_t xziel_hud_grenade_opacity;\n"
hud_ext = """extern cvar_t xziel_hud_slide_x;
extern cvar_t xziel_hud_slide_y;
extern cvar_t xziel_hud_slide_scale;
extern cvar_t xziel_hud_slide_opacity;
extern qboolean xziel_mobile_slide_pressed;
"""
# slide pressed is static in sys_sdl and cannot be extern; make it global there.
# Remove static qualifier in state declaration before writing sys_sdl.
sdl = source / "platform" / "sdl" / "sys_sdl.c"
stext = sdl.read_text(encoding="utf-8")
stext = stext.replace("static qboolean xziel_mobile_slide_pressed = false;",
                      "qboolean xziel_mobile_slide_pressed = false;", 1)
sdl.write_text(stext, encoding="utf-8")

if "extern cvar_t xziel_hud_slide_x;" not in text:
    if hud_ext_anchor not in text:
        raise SystemExit("Could not find HUD grenade-opacity extern")
    text = text.replace(hud_ext_anchor, hud_ext_anchor + hud_ext, 1)

image_anchor = "static image_t xziel_icon_sprint;\n"
if "static image_t xziel_icon_slide;" not in text:
    if image_anchor not in text:
        raise SystemExit("Could not find sprint icon handle")
    text = text.replace(image_anchor, image_anchor + "static image_t xziel_icon_slide;\n", 1)

load_anchor = '    xziel_icon_sprint  = Image_LoadImage("gfx/xziel/sprint", IMAGE_PNG, 0, true, false);\n'
if 'gfx/xziel/slide' not in text:
    if load_anchor not in text:
        raise SystemExit("Could not find sprint icon loader")
    text = text.replace(
        load_anchor,
        load_anchor + '    xziel_icon_slide   = Image_LoadImage("gfx/xziel/slide", IMAGE_PNG, 0, true, false);\n',
        1
    )

style_start = text.find("static void Xziel_ControlStyle")
style_end = text.find("static image_t Xziel_ActionIcon", style_start)
style_chunk = text[style_start:style_end]
style_anchor = '\telse if (!strcmp(label1, "NADE")) { *scale = xziel_hud_grenade_scale.value; *opacity = xziel_hud_grenade_opacity.value; }\n'
if '"SLIDE"' not in style_chunk:
    if style_anchor not in style_chunk:
        raise SystemExit("Could not find ControlStyle grenade case")
    style_chunk = style_chunk.replace(
        style_anchor,
        style_anchor + '\telse if (!strcmp(label1, "SLIDE")) { *scale = xziel_hud_slide_scale.value; *opacity = xziel_hud_slide_opacity.value; }\n',
        1
    )
    style_chunk = style_chunk.replace("if (*scale < 0.50f) *scale = 0.50f;",
                                      "if (*scale < 0.30f) *scale = 0.30f;")
    style_chunk = style_chunk.replace("if (*scale > 1.80f) *scale = 1.80f;",
                                      "if (*scale > 2.50f) *scale = 2.50f;")
    text = text[:style_start] + style_chunk + text[style_end:]

icon_start = text.find("static image_t Xziel_ActionIcon")
icon_end = text.find("static qboolean Xziel_DrawActionGlyph", icon_start)
icon_chunk = text[icon_start:icon_end]
icon_anchor = '\tif (!strcmp(label1, "NADE")) return xziel_icon_grenade;\n'
if '"SLIDE"' not in icon_chunk:
    if icon_anchor not in icon_chunk:
        raise SystemExit("Could not find action icon grenade case")
    icon_chunk = icon_chunk.replace(
        icon_anchor,
        icon_anchor + '\tif (!strcmp(label1, "SLIDE")) return xziel_icon_slide;\n',
        1
    )
    text = text[:icon_start] + icon_chunk + text[icon_end:]

draw_start = text.find("static void Xziel_MobileHUD_DrawInternal(qboolean editor)")
draw_end = text.find("static void Xziel_MobileHUD_Draw(void)", draw_start)
draw_chunk = text[draw_start:draw_end]
jump_anchor = "\tXziel_DrawTouchButton(xziel_hud_jump_x.value"
if "xziel_hud_slide_x.value" not in draw_chunk:
    j = draw_chunk.find(jump_anchor)
    if j < 0:
        raise SystemExit("Could not find final HUD jump draw")
    line_end = draw_chunk.find("\n", j)
    slide_line = '\tXziel_DrawTouchButton(xziel_hud_slide_x.value, xziel_hud_slide_y.value, 0.044f, "SLIDE", "", xziel_mobile_slide_pressed, editor);\n'
    draw_chunk = draw_chunk[:j] + slide_line + draw_chunk[j:]
    text = text[:draw_start] + draw_chunk + text[draw_end:]

# Weapon-card editor hit testing also gets the wider scale envelope.
text = text.replace("if (s < 0.55f) s = 0.55f;", "if (s < 0.30f) s = 0.30f;")
text = text.replace("if (s > 1.80f) s = 1.80f;", "if (s > 2.50f) s = 2.50f;")

# ---------------------------------------------------------------------------
# Threat indicator correctness: use NZ:P's own body-model whitelist and
# directional sectors so rear threats do not all collapse to left/right.
# ---------------------------------------------------------------------------
zombie_entity = r'''static qboolean Xziel_IsZombieThreatEntity(entity_t *ent)
{
	const char *name;
	if (!ent || !ent->model)
		return false;
	name = ent->model->name;
	if (!name || !name[0])
		return false;

	/* Exact body models from NZ:P client/zombie.qc zombie_snap_struct.
	   Do not include detachable head/arm meshes or each zombie duplicates. */
	return !strcmp(name, "models/ai/zfull.mdl") ||
		!strcmp(name, "models/ai/zb%.mdl") ||
		!strcmp(name, "models/ai/zcfull.mdl") ||
		!strcmp(name, "models/ai/zbc%.mdl") ||
		!strcmp(name, "models/ai/dog.mdl");
}'''
text = replace_function(text, "static qboolean Xziel_IsZombieThreatEntity(entity_t *ent)", zombie_entity)

threat = r'''static void Xziel_DrawThreatIndicators(void)
{
	float best_dist[5] = {999999,999999,999999,999999,999999};
	int i, sector;

	if (key_dest != key_game || cl.stats[STAT_HEALTH] <= 0)
		return;
	if (cl.viewentity <= 0 || cl.viewentity >= cl.num_entities)
		return;

	for (i = 1; i < cl.num_entities; ++i) {
		entity_t *ent;
		float dx,dy,dz,dist,world_yaw,delta,threshold;

		if (i == cl.viewentity)
			continue;
		ent = &cl_entities[i];
		if (!Xziel_IsZombieThreatEntity(ent))
			continue;

		dx = ent->origin[0] - cl_entities[cl.viewentity].origin[0];
		dy = ent->origin[1] - cl_entities[cl.viewentity].origin[1];
		dz = ent->origin[2] - cl_entities[cl.viewentity].origin[2];
		dist = sqrtf(dx*dx + dy*dy + dz*dz);
		if (dist < 24.0f || dist > 850.0f)
			continue;

		world_yaw = atan2f(dy,dx) * 57.295779513f;
		delta = Xziel_AngleDelta(world_yaw - cl.viewangles[YAW]);

		/* Very close zombies deserve a warning even near the edge of the
		   visible FOV; farther ones only warn once clearly off-screen. */
		threshold = dist < 190.0f ? 30.0f : 52.0f;
		if (fabsf(delta) < threshold)
			continue;

		if (fabsf(delta) >= 165.0f)
			sector = 2;              /* directly behind */
		else if (delta < -120.0f)
			sector = 1;              /* rear-left */
		else if (delta < 0)
			sector = 0;              /* left */
		else if (delta > 120.0f)
			sector = 3;              /* rear-right */
		else
			sector = 4;              /* right */

		if (dist < best_dist[sector])
			best_dist[sector] = dist;
	}

	for (sector = 0; sector < 5; ++sector) {
		float proximity;
		int size,x,y,alpha;

		if (best_dist[sector] >= 999998.0f)
			continue;

		proximity = 1.0f - (best_dist[sector] / 850.0f);
		if (proximity < 0.12f) proximity = 0.12f;
		if (proximity > 1.0f) proximity = 1.0f;
		size = (int)((14.0f + 11.0f*proximity) * vid.scale);
		alpha = (int)(105 + 145*proximity);

		switch (sector) {
		case 0: /* left */
			x = (int)(24*vid.scale);
			y = (int)(vid.height*0.48f) - size/2;
			break;
		case 1: /* rear-left */
			x = vid.width/2 - (int)(72*vid.scale) - size/2;
			y = vid.height - (int)(76*vid.scale) - size;
			break;
		case 2: /* directly behind */
			x = vid.width/2 - size/2;
			y = vid.height - (int)(54*vid.scale) - size;
			break;
		case 3: /* rear-right */
			x = vid.width/2 + (int)(72*vid.scale) - size/2;
			y = vid.height - (int)(76*vid.scale) - size;
			break;
		default: /* right */
			x = vid.width - (int)(24*vid.scale) - size;
			y = (int)(vid.height*0.48f) - size/2;
			break;
		}

		Draw_ColoredStretchPic(x,y,xziel_icon_threat,size,size,
			255,255,255,alpha);
	}
}'''
text = replace_function(text, "static void Xziel_DrawThreatIndicators(void)", threat)

hud.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# Mobile settings + Custom HUD editor
# ---------------------------------------------------------------------------
controls = source / "menu" / "menu_controls.c"
text = controls.read_text(encoding="utf-8")

menu_ext_anchor = "extern cvar_t xziel_mobile_ads_sensitivity;\n"
menu_ext = """extern cvar_t xziel_mobile_ads_toggle;
extern cvar_t xziel_mobile_joystick_sensitivity;
extern cvar_t xziel_mobile_ads_move_sensitivity;
extern cvar_t xziel_hud_slide_scale;
extern cvar_t xziel_hud_slide_opacity;
"""
if "extern cvar_t xziel_mobile_joystick_sensitivity;" not in text:
    text = insert_after(text, menu_ext_anchor, menu_ext, "menu movement externs")

# ADS hold/toggle was already implemented in runtime but had disappeared from
# the settings UI.
aim_sig = "void Menu_MobileAim_Draw(void)"
aim_idx = text.find(aim_sig)
if aim_idx < 0:
    raise SystemExit("Could not find Mobile Aim menu")

ads_helpers = r'''
static char *xziel_mobile_ads_button_string;

static void Menu_Mobile_ToggleAdsButtonV21(void)
{
	Cvar_SetValue("xziel_mobile_ads_toggle",
		xziel_mobile_ads_toggle.value >= 0.5f ? 0.0f : 1.0f);
}

'''
if "Menu_Mobile_ToggleAdsButtonV21" not in text:
    text = text[:aim_idx] + ads_helpers + text[aim_idx:]

aim = r'''void Menu_MobileAim_Draw(void)
{
	int b=1, i=0;
	Menu_DrawCustomBackground(true);
	Menu_DrawMapPanel();
	Menu_DrawTitle("MOBILE AIM", MENU_COLOR_WHITE);

	xziel_mobile_ads_button_string =
		xziel_mobile_ads_toggle.value >= 0.5f ? "TOGGLE" : "HOLD";

	Menu_DrawButton(b++, i++, "ADS BUTTON", "Hold releases ADS with your finger. Toggle stays aimed until tapped again.", Menu_Mobile_ToggleAdsButtonV21);
	Menu_DrawOptionButton(b-1, xziel_mobile_ads_button_string);

	Menu_DrawButton(b++, i++, "CAMERA - STANDARD", "Look sensitivity while not aiming.", NULL);
	Menu_DrawOptionSlider(b-1, i-1, 0.25f, 4.0f, xziel_mobile_touch_sensitivity, "xziel_mobile_touch_sensitivity", false, true, 0.05f);

	Menu_DrawButton(b++, i++, "CAMERA - ADS", "Look multiplier while aiming down sights.", NULL);
	Menu_DrawOptionSlider(b-1, i-1, 0.15f, 1.5f, xziel_mobile_ads_sensitivity, "xziel_mobile_ads_sensitivity", false, true, 0.05f);

	Menu_DrawButton(b++, i++, "CAMERA - SNIPER", "Look multiplier for scoped sniper ADS.", NULL);
	Menu_DrawOptionSlider(b-1, i-1, 0.10f, 1.5f, xziel_mobile_sniper_sensitivity, "xziel_mobile_sniper_sensitivity", false, true, 0.05f);

	Menu_DrawButton(b++, i++, "FIRING - STANDARD", "Look multiplier while dragging a fire control.", NULL);
	Menu_DrawOptionSlider(b-1, i-1, 0.25f, 2.0f, xziel_mobile_fire_sensitivity, "xziel_mobile_fire_sensitivity", false, true, 0.05f);

	Menu_DrawButton(b++, i++, "FIRING - ADS", "Look multiplier while firing in ADS.", NULL);
	Menu_DrawOptionSlider(b-1, i-1, 0.15f, 1.5f, xziel_mobile_ads_fire_sensitivity, "xziel_mobile_ads_fire_sensitivity", false, true, 0.05f);

	Menu_DrawButton(b++, i++, "FIRING - SNIPER", "Look multiplier while firing a scoped sniper.", NULL);
	Menu_DrawOptionSlider(b-1, i-1, 0.10f, 1.5f, xziel_mobile_sniper_fire_sensitivity, "xziel_mobile_sniper_fire_sensitivity", false, true, 0.05f);

	Menu_DrawButton(-1, i, "BACK", "Return to Mobile Controls.", Menu_Mobile_Set);
}'''
text = replace_function(text, aim_sig, aim)

gameplay = r'''void Menu_MobileGameplay_Draw(void)
{
	int idx = 0, row = 1;

	Menu_DrawCustomBackground(true);
	Menu_DrawTitle("MOBILE - GAMEPLAY", MENU_COLOR_WHITE);
	Menu_DrawMapPanel();

	xziel_mobile_auto_rebuild_string =
		xziel_mobile_auto_rebuild.value >= 0.5f ? "ENABLED" : "DISABLED";
	xziel_mobile_auto_knife_string =
		xziel_mobile_auto_knife.value >= 0.5f ? "ENABLED" : "DISABLED";
	xziel_mobile_knife_visibility_string =
		xziel_mobile_knife_range_only.value >= 0.5f ? "IN RANGE" : "ALWAYS";
	xziel_mobile_unlimited_pistol_string =
		xziel_mobile_unlimited_pistol.value >= 0.5f ? "ENABLED" : "DISABLED";
	xziel_mobile_movement_string =
		Cvar_VariableValue("xziel_modern_movement") >= 0.5f ? "MODERN" : "CLASSIC";

	Menu_DrawButton(row++, idx++, "MOVEMENT MODEL",
		"Modern: grounded FPS acceleration, braking, air steering and weighted jump. Classic restores legacy Quake movement.",
		Menu_Mobile_ToggleModernMovement);
	Menu_DrawOptionButton(row-1, xziel_mobile_movement_string);

	Menu_DrawButton(row++, idx++, "JOYSTICK RESPONSE",
		"How quickly movement reaches full analog input. Sprint trigger uses physical stick travel, so this will not break sprint.",
		NULL);
	Menu_DrawOptionSlider(row-1, idx-1, 0.50f, 2.00f,
		xziel_mobile_joystick_sensitivity, "xziel_mobile_joystick_sensitivity",
		false, true, 0.05f);

	Menu_DrawButton(row++, idx++, "ADS WALK SENSITIVITY",
		"Master ADS movement multiplier. Weapon classes automatically keep lighter guns more mobile and heavy/precision guns slower.",
		NULL);
	Menu_DrawOptionSlider(row-1, idx-1, 0.35f, 1.25f,
		xziel_mobile_ads_move_sensitivity, "xziel_mobile_ads_move_sensitivity",
		false, true, 0.05f);

	Menu_DrawButton(row++, idx++, "SPRINT ACTIVATION HEIGHT",
		"Higher means drag farther above the joystick before native sprint starts.", NULL);
	Menu_DrawOptionSlider(row-1, idx-1, 1.10f, 1.85f,
		xziel_mobile_sprint_zone, "xziel_mobile_sprint_zone", false, true, 0.05f);

	Menu_DrawButton(row++, idx++, "UNLIMITED PISTOL RESERVE",
		"Pistol magazines stay finite and still reload. Enables three total guns: two ordinary weapons plus a protected pistol.",
		Menu_Mobile_ToggleUnlimitedPistol);
	Menu_DrawOptionButton(row-1, xziel_mobile_unlimited_pistol_string);

	Menu_DrawButton(row++, idx++, "AUTO REBUILD BARRIERS",
		"Automatically repair barricades while you remain in range.", Menu_Mobile_ToggleAutoRebuild);
	Menu_DrawOptionButton(row-1, xziel_mobile_auto_rebuild_string);

	Menu_DrawButton(row++, idx++, "AUTO KNIFE",
		"Automatically melee only when native NZ:P melee distance can reach the target.", Menu_Mobile_ToggleAutoKnife);
	Menu_DrawOptionButton(row-1, xziel_mobile_auto_knife_string);

	Menu_DrawButton(row++, idx++, "KNIFE BUTTON",
		"Show the manual knife button always or only at native melee distance.", Menu_Mobile_ToggleKnifeVisibility);
	Menu_DrawOptionButton(row-1, xziel_mobile_knife_visibility_string);

	Menu_DrawButton(-1, idx, "BACK", "Return to Mobile Settings.", Menu_Mobile_Set);
}'''
text = replace_function(text, "void Menu_MobileGameplay_Draw(void)", gameplay)

# Custom HUD: 30%..250% range and independent Crouch/Slide styling.
text = text.replace(
    'Menu_DrawOptionSlider(1, 0, 0.50f, 1.80f, CVAR_SCALE, #CVAR_SCALE, false, true, 0.05f);',
    'Menu_DrawOptionSlider(1, 0, 0.30f, 2.50f, CVAR_SCALE, #CVAR_SCALE, false, true, 0.05f);'
)

editor_sig = "void Menu_HudEdit_Draw(void)"
ed_start = text.find(editor_sig)
if ed_start < 0:
    raise SystemExit("Could not find Custom HUD menu")
ed_end = text.find("void Menu_MobileAim_Draw(void)", ed_start)
ed_chunk = text[ed_start:ed_end]

if 'case 16: name="CROUCH / SLIDE";' not in ed_chunk:
    label_anchor = 'case 15: name="WEAPON 1"; break;\n'
    if label_anchor not in ed_chunk:
        raise SystemExit("Could not find Custom HUD weapon1 label")
    ed_chunk = ed_chunk.replace(
        label_anchor,
        label_anchor + '\tcase 16: name="CROUCH / SLIDE"; break;\n',
        1
    )

if "DRAW_STYLE(xziel_hud_slide_scale" not in ed_chunk:
    style_case_anchor = "case 15: DRAW_STYLE(xziel_hud_weapon1_scale, xziel_hud_weapon1_opacity); break;\n"
    if style_case_anchor not in ed_chunk:
        raise SystemExit("Could not find Custom HUD weapon1 style case")
    ed_chunk = ed_chunk.replace(
        style_case_anchor,
        style_case_anchor + "\tcase 16: DRAW_STYLE(xziel_hud_slide_scale, xziel_hud_slide_opacity); break;\n",
        1
    )
text = text[:ed_start] + ed_chunk + text[ed_end:]

reset_start = text.find("static void Menu_HudEdit_Reset(void)")
reset_end = text.find("void Menu_HudEdit_Draw(void)", reset_start)
reset_chunk = text[reset_start:reset_end]
if 'xziel_hud_slide_x' not in reset_chunk:
    reset_anchor = '\tCvar_SetValue("xziel_hud_grenade_scale", 1.0f); Cvar_SetValue("xziel_hud_grenade_opacity", 0.82f);\n'
    if reset_anchor not in reset_chunk:
        raise SystemExit("Could not find Custom HUD reset style anchor")
    reset_chunk = reset_chunk.replace(
        reset_anchor,
        reset_anchor +
        '\tCvar_SetValue("xziel_hud_slide_x", 0.745f); Cvar_SetValue("xziel_hud_slide_y", 0.825f);\n'
        '\tCvar_SetValue("xziel_hud_slide_scale", 1.0f); Cvar_SetValue("xziel_hud_slide_opacity", 0.82f);\n',
        1
    )
    text = text[:reset_start] + reset_chunk + text[reset_end:]

controls.write_text(text, encoding="utf-8")

print("Applied Xziel v0.21 mobile input, ADS, slide and threat-indicator polish.")
