#!/usr/bin/env python3
"""Xziel v0.22 Vril mobile polish.

Final authority after v0.21:
- server-authoritative ADS walk slider (client no longer double-damps movement);
- reliable crouch/slide input arbitration;
- 20%-400% Custom HUD scaling;
- completely new antialiased touch-control surfaces (no scanline discs);
- weapon-specific NZ:P silhouettes rather than generic category cards;
- live-server filtering for zombie threat indicators;
- Modern Zombie Motion toggle.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_vril_mobile_v022.py <vril-root>")

root = Path(sys.argv[1])
source = root / "source"

def replace_function(src: str, signature: str, replacement: str) -> str:
    start = src.find(signature)
    if start < 0:
        raise SystemExit("Could not find function: " + signature)
    brace = src.find("{", start)
    if brace < 0:
        raise SystemExit("Could not find body: " + signature)
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

def add_after(src: str, anchor: str, payload: str, label: str) -> str:
    if payload.strip() in src:
        return src
    if anchor not in src:
        raise SystemExit("Missing anchor: " + label)
    return src.replace(anchor, anchor + payload, 1)

# ---------------------------------------------------------------------------
# Cvars
# ---------------------------------------------------------------------------
inp = source / "input.c"
text = inp.read_text(encoding="utf-8")
cvar_anchor = 'cvar_t xziel_mobile_ads_move_sensitivity = {"xziel_mobile_ads_move_sensitivity", "0.90", true};\n'
if "xziel_modern_zombies" not in text:
    text = add_after(
        text, cvar_anchor,
        'cvar_t xziel_modern_zombies = {"xziel_modern_zombies", "1", true};\n',
        "modern zombie cvar"
    )
reg_anchor = "\tCvar_RegisterVariable(&xziel_mobile_ads_move_sensitivity);\n"
if "Cvar_RegisterVariable(&xziel_modern_zombies);" not in text:
    text = add_after(
        text, reg_anchor,
        "\tCvar_RegisterVariable(&xziel_modern_zombies);\n",
        "modern zombie registration"
    )
inp.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# SDL input: no second ADS walking slowdown; server QuakeC owns actual speed.
# ---------------------------------------------------------------------------
sdl = source / "platform" / "sdl" / "sys_sdl.c"
text = sdl.read_text(encoding="utf-8")

move = r'''static void Xziel_UpdateMove(float x, float y)
{
	float raw_dx, raw_dy, dx, dy, len, radius_x, radius_y;
	float sprint_zone;
	float response;
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

	xziel_mobile_sprint_zone_hot =
		raw_dy >= sprint_zone &&
		fabsf(raw_dx) <= raw_dy * 0.70f;

	/* A slide temporarily owns the sprint lane. Once its short suppression
	   window ends, holding the stick forward can naturally return to sprint. */
	if (xziel_mobile_sprint_suppressed &&
		xziel_mobile_sprint_retry_ms &&
		now >= xziel_mobile_sprint_retry_ms) {
		xziel_mobile_sprint_suppressed = false;
		xziel_mobile_sprint_retry_ms = 0;
	}

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
text = replace_function(text, "static void Xziel_UpdateMove(float x, float y)", move)

# Crouch/slide wins over the sprint retry impulse for this touch.
down_start = text.find("static void Xziel_ActionDown(xziel_touch_role_t role)")
down_end = text.find("static void Xziel_ActionUp(xziel_touch_role_t role)", down_start)
if down_start < 0 or down_end < 0:
    raise SystemExit("Could not find ActionDown")
chunk = text[down_start:down_end]
old_case = """\tcase XZ_TOUCH_SLIDE:
\t\txziel_mobile_slide_pressed = true;
\t\tCbuf_AddText("impulse 34\\n");
\t\tCbuf_Execute();
\t\tbreak;
"""
new_case = """\tcase XZ_TOUCH_SLIDE:
\t\txziel_mobile_slide_pressed = true;
\t\txziel_mobile_sprint_suppressed = true;
\t\txziel_mobile_sprint_active = false;
\t\txziel_mobile_sprint_retry_ms = SDL_GetTicks() + 650;
\t\tCbuf_AddText("impulse 34\\n");
\t\tCbuf_Execute();
\t\tbreak;
"""
if old_case not in chunk:
    raise SystemExit("Could not find v0.21 slide ActionDown case")
chunk = chunk.replace(old_case, new_case, 1)
text = text[:down_start] + chunk + text[down_end:]
sdl.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# HUD surfaces, weapon silhouettes and threat filtering
# ---------------------------------------------------------------------------
hud = source / "render" / "r_hud.c"
text = hud.read_text(encoding="utf-8")

# Modern touch surface handles.
handle_anchor = "static image_t xziel_icon_slide;\n"
surface_handles = r'''static image_t xziel_touch_idle;
static image_t xziel_touch_pressed;
static image_t xziel_touch_editor;
static image_t xziel_joystick_ring;
static image_t xziel_joystick_knob;
static image_t xziel_joystick_knob_active;

static image_t xziel_weapon_colt;
static image_t xziel_weapon_revolver;
static image_t xziel_weapon_kar;
static image_t xziel_weapon_kar_scope;
static image_t xziel_weapon_thompson;
static image_t xziel_weapon_bar;
static image_t xziel_weapon_ballistic;
static image_t xziel_weapon_browning;
static image_t xziel_weapon_doublebarrel;
static image_t xziel_weapon_sawnoff;
static image_t xziel_weapon_fg42;
static image_t xziel_weapon_gewehr;
static image_t xziel_weapon_m1;
static image_t xziel_weapon_m1a1;
static image_t xziel_weapon_flamer;
static image_t xziel_weapon_mp40;
static image_t xziel_weapon_mg42;
static image_t xziel_weapon_panzer;
static image_t xziel_weapon_ppsh;
static image_t xziel_weapon_ptrs;
static image_t xziel_weapon_ray;
static image_t xziel_weapon_raymk2;
static image_t xziel_weapon_stg;
static image_t xziel_weapon_trench;
static image_t xziel_weapon_type100;
static image_t xziel_weapon_mp5;
static image_t xziel_weapon_tesla;
static image_t xziel_weapon_springfield;
'''
if "static image_t xziel_touch_idle;" not in text:
    text = add_after(text, handle_anchor, surface_handles, "HUD modern handles")

load_anchor = '    xziel_icon_slide   = Image_LoadImage("gfx/xziel/slide", IMAGE_PNG, 0, true, false);\n'
loads = r'''    xziel_touch_idle = Image_LoadImage("gfx/xziel/touch_idle", IMAGE_PNG, 0, true, false);
    xziel_touch_pressed = Image_LoadImage("gfx/xziel/touch_pressed", IMAGE_PNG, 0, true, false);
    xziel_touch_editor = Image_LoadImage("gfx/xziel/touch_editor", IMAGE_PNG, 0, true, false);
    xziel_joystick_ring = Image_LoadImage("gfx/xziel/joystick_ring", IMAGE_PNG, 0, true, false);
    xziel_joystick_knob = Image_LoadImage("gfx/xziel/joystick_knob", IMAGE_PNG, 0, true, false);
    xziel_joystick_knob_active = Image_LoadImage("gfx/xziel/joystick_knob_active", IMAGE_PNG, 0, true, false);

    xziel_weapon_colt = Image_LoadImage("gfx/xziel/weapon_colt", IMAGE_PNG, 0, true, false);
    xziel_weapon_revolver = Image_LoadImage("gfx/xziel/weapon_revolver", IMAGE_PNG, 0, true, false);
    xziel_weapon_kar = Image_LoadImage("gfx/xziel/weapon_kar", IMAGE_PNG, 0, true, false);
    xziel_weapon_kar_scope = Image_LoadImage("gfx/xziel/weapon_kar_scope", IMAGE_PNG, 0, true, false);
    xziel_weapon_thompson = Image_LoadImage("gfx/xziel/weapon_thompson", IMAGE_PNG, 0, true, false);
    xziel_weapon_bar = Image_LoadImage("gfx/xziel/weapon_bar", IMAGE_PNG, 0, true, false);
    xziel_weapon_ballistic = Image_LoadImage("gfx/xziel/weapon_ballistic", IMAGE_PNG, 0, true, false);
    xziel_weapon_browning = Image_LoadImage("gfx/xziel/weapon_browning", IMAGE_PNG, 0, true, false);
    xziel_weapon_doublebarrel = Image_LoadImage("gfx/xziel/weapon_doublebarrel", IMAGE_PNG, 0, true, false);
    xziel_weapon_sawnoff = Image_LoadImage("gfx/xziel/weapon_sawnoff", IMAGE_PNG, 0, true, false);
    xziel_weapon_fg42 = Image_LoadImage("gfx/xziel/weapon_fg42", IMAGE_PNG, 0, true, false);
    xziel_weapon_gewehr = Image_LoadImage("gfx/xziel/weapon_gewehr", IMAGE_PNG, 0, true, false);
    xziel_weapon_m1 = Image_LoadImage("gfx/xziel/weapon_m1", IMAGE_PNG, 0, true, false);
    xziel_weapon_m1a1 = Image_LoadImage("gfx/xziel/weapon_m1a1", IMAGE_PNG, 0, true, false);
    xziel_weapon_flamer = Image_LoadImage("gfx/xziel/weapon_flamer", IMAGE_PNG, 0, true, false);
    xziel_weapon_mp40 = Image_LoadImage("gfx/xziel/weapon_mp40", IMAGE_PNG, 0, true, false);
    xziel_weapon_mg42 = Image_LoadImage("gfx/xziel/weapon_mg42", IMAGE_PNG, 0, true, false);
    xziel_weapon_panzer = Image_LoadImage("gfx/xziel/weapon_panzer", IMAGE_PNG, 0, true, false);
    xziel_weapon_ppsh = Image_LoadImage("gfx/xziel/weapon_ppsh", IMAGE_PNG, 0, true, false);
    xziel_weapon_ptrs = Image_LoadImage("gfx/xziel/weapon_ptrs", IMAGE_PNG, 0, true, false);
    xziel_weapon_ray = Image_LoadImage("gfx/xziel/weapon_ray", IMAGE_PNG, 0, true, false);
    xziel_weapon_raymk2 = Image_LoadImage("gfx/xziel/weapon_raymk2", IMAGE_PNG, 0, true, false);
    xziel_weapon_stg = Image_LoadImage("gfx/xziel/weapon_stg", IMAGE_PNG, 0, true, false);
    xziel_weapon_trench = Image_LoadImage("gfx/xziel/weapon_trench", IMAGE_PNG, 0, true, false);
    xziel_weapon_type100 = Image_LoadImage("gfx/xziel/weapon_type100", IMAGE_PNG, 0, true, false);
    xziel_weapon_mp5 = Image_LoadImage("gfx/xziel/weapon_mp5", IMAGE_PNG, 0, true, false);
    xziel_weapon_tesla = Image_LoadImage("gfx/xziel/weapon_tesla", IMAGE_PNG, 0, true, false);
    xziel_weapon_springfield = Image_LoadImage("gfx/xziel/weapon_springfield", IMAGE_PNG, 0, true, false);
'''
if 'gfx/xziel/touch_idle' not in text:
    text = add_after(text, load_anchor, loads, "HUD modern image loads")

# Remove the coarse stepped-disc look from touch controls entirely.
action_glyph = r'''static qboolean Xziel_DrawActionGlyph(int cx, int cy, int radius,
	const char *label1, const char *label2, qboolean pressed)
{
	image_t icon = Xziel_ActionIcon(label1, label2);
	int size;
	int alpha;

	if (!icon)
		return false;

	size = (int)(radius * 0.96f);
	if (size < 14) size = 14;
	alpha = pressed ? 255 : 238;
	Draw_ColoredStretchPic(cx - size/2, cy - size/2, icon,
		size, size, 255,255,255,alpha);

	if (!strcmp(label1, "ADS") && label2 && !strcmp(label2, "FIRE")) {
		int dot = (int)fmaxf(3.0f, 3.0f * vid.scale);
		Draw_FillByColor(cx + size/4, cy + size/4,
			dot, dot, 244,200,61,255);
	}
	return true;
}'''
action_pos = text.rfind("static qboolean Xziel_DrawActionGlyph(")
if action_pos < 0:
    raise SystemExit("Could not find final Xziel_DrawActionGlyph implementation")
text = text[:action_pos] + replace_function(
    text[action_pos:], "static qboolean Xziel_DrawActionGlyph(", action_glyph
)

touch = r'''static void Xziel_DrawTouchButton(float nx, float ny, float radius_h,
	const char *label1, const char *label2, qboolean pressed, qboolean editor)
{
	float local_scale, local_opacity;
	int cx = (int)(nx * vid.width);
	int cy = (int)(ny * vid.height);
	int radius;
	int size;
	int alpha;
	image_t surface;

	Xziel_ControlStyle(label1, label2, &local_scale, &local_opacity);
	if (local_scale < 0.20f) local_scale = 0.20f;
	if (local_scale > 4.00f) local_scale = 4.00f;
	if (local_opacity < 0.15f) local_opacity = 0.15f;
	if (local_opacity > 1.00f) local_opacity = 1.00f;

	radius = (int)(radius_h * vid.height *
		xziel_mobile_hud_scale.value * local_scale);
	if (radius < 9) radius = 9;
	size = (int)(radius * 2.16f);

	surface = editor ? xziel_touch_editor :
		(pressed ? xziel_touch_pressed : xziel_touch_idle);
	alpha = (int)(255 * xziel_mobile_hud_opacity.value * local_opacity);

	if (surface)
		Draw_ColoredStretchPic(cx - size/2, cy - size/2, surface,
			size,size,255,255,255,alpha);

	Xziel_DrawActionGlyph(cx,cy,radius,label1,label2,pressed);
}'''
text = replace_function(
    text,
    "static void Xziel_DrawTouchButton(",
    touch
)

# Exact physical silhouettes instead of one icon per broad category.
weapon_image = r'''static image_t Xziel_HUDWeaponImage(int id)
{
	switch (id) {
	case W_COLT: case W_BIATCH: return xziel_weapon_colt;
	case W_357: case W_KILLU: return xziel_weapon_revolver;
	case W_KAR: case W_ARMAGEDDON: return xziel_weapon_kar;
	case W_KAR_SCOPE: case W_HEADCRACKER: return xziel_weapon_kar_scope;
	case W_SPRING: case W_PULVERIZER: return xziel_weapon_springfield;
	case W_THOMPSON: case W_GIBS: return xziel_weapon_thompson;
	case W_BAR: case W_WIDOW: return xziel_weapon_bar;
	case W_BK: return xziel_weapon_ballistic;
	case W_BROWNING: case W_ACCELERATOR: return xziel_weapon_browning;
	case W_DB: case W_BORE: return xziel_weapon_doublebarrel;
	case W_SAWNOFF: case W_SNUFF: return xziel_weapon_sawnoff;
	case W_FG: case W_IMPELLER: return xziel_weapon_fg42;
	case W_GEWEHR: case W_COMPRESSOR: return xziel_weapon_gewehr;
	case W_M1: case W_M1000: case W_M14: return xziel_weapon_m1;
	case W_M1A1: case W_WIDDER: return xziel_weapon_m1a1;
	case W_M2: case W_FIW: return xziel_weapon_flamer;
	case W_MP40: case W_AFTERBURNER: return xziel_weapon_mp40;
	case W_MG: case W_BARRACUDA: return xziel_weapon_mg42;
	case W_PANZER: case W_LONGINUS: return xziel_weapon_panzer;
	case W_PPSH: case W_REAPER: return xziel_weapon_ppsh;
	case W_PTRS: case W_PENETRATOR: return xziel_weapon_ptrs;
	case W_RAY: case W_PORTER: return xziel_weapon_ray;
	case W_RAYMK2: case W_PORTERMK2: return xziel_weapon_raymk2;
	case W_STG: case W_SPATZ: return xziel_weapon_stg;
	case W_TRENCH: case W_GUT: return xziel_weapon_trench;
	case W_TYPE: case W_SAMURAI: return xziel_weapon_type100;
	case W_MP5: case W_KOLLIDER: return xziel_weapon_mp5;
	case W_TESLA: case W_DG3: return xziel_weapon_tesla;
	default:
		return xziel_icon_weapon_assault ?
			xziel_icon_weapon_assault : xziel_icon_weapon;
	}
}'''
text = replace_function(text, "static image_t Xziel_HUDWeaponImage(int id)", weapon_image)

weapon_glyph = r'''static void Xziel_DrawWeaponGlyph(int cx, int cy, int id, float scale, int alpha)
{
	image_t icon = Xziel_HUDWeaponImage(id);
	int h = (int)(21.0f * scale);
	int w;

	if (!icon)
		icon = xziel_icon_weapon;
	if (h < 14) h = 14;

	if (Xziel_HUDIsPistol(id) || Xziel_HUDIsRevolver(id) || id == W_BK)
		w = (int)(h * 1.72f);
	else if (id == W_RAY || id == W_PORTER ||
		id == W_RAYMK2 || id == W_PORTERMK2 ||
		id == W_TESLA || id == W_DG3)
		w = (int)(h * 1.82f);
	else
		w = (int)(h * 2.28f);

	Draw_ColoredStretchPic(cx - w/2, cy - h/2, icon,
		w,h,255,255,255,alpha);
}'''
text = replace_function(text, "static void Xziel_DrawWeaponGlyph(", weapon_glyph)

# Modern joystick renderer: a single antialiased texture per layer, no stepped
# horizontal rectangles. The rest of the HUD keeps the exact saved positions.
mobile_hud = r'''static void Xziel_MobileHUD_DrawInternal(qboolean editor)
{
	int base_x, base_y, knob_x, knob_y, radius, knob_r, size, knob_size;
	float joy_scale = xziel_hud_joy_scale.value;
	float joy_alpha = xziel_hud_joy_opacity.value;
	image_t knob;

	if (!editor && (key_dest != key_game || cl.stats[STAT_HEALTH] <= 0))
		return;

	if (joy_scale < 0.20f) joy_scale = 0.20f;
	if (joy_scale > 4.00f) joy_scale = 4.00f;
	if (joy_alpha < 0.15f) joy_alpha = 0.15f;
	if (joy_alpha > 1.00f) joy_alpha = 1.00f;

	base_x = (int)((xziel_mobile_move_active && !editor ?
		xziel_mobile_move_anchor_x : xziel_hud_joy_x.value) * vid.width);
	base_y = (int)((xziel_mobile_move_active && !editor ?
		xziel_mobile_move_anchor_y : xziel_hud_joy_y.value) * vid.height);
	radius = (int)(0.095f * vid.height *
		xziel_mobile_hud_scale.value * joy_scale);
	knob_r = (int)(0.042f * vid.height *
		xziel_mobile_hud_scale.value * joy_scale);
	if (radius < 18) radius = 18;
	if (knob_r < 9) knob_r = 9;
	size = (int)(radius * 2.12f);

	if (xziel_joystick_ring)
		Draw_ColoredStretchPic(base_x-size/2,base_y-size/2,
			xziel_joystick_ring,size,size,255,255,255,
			(int)(255*xziel_mobile_hud_opacity.value*joy_alpha));

	knob_x = base_x + (int)(xziel_mobile_move_x * radius * 0.72f);
	knob_y = base_y - (int)(xziel_mobile_move_y * radius * 0.72f);
	knob_size = (int)(knob_r * 2.18f);
	knob = xziel_mobile_move_active ?
		xziel_joystick_knob_active : xziel_joystick_knob;
	if (knob)
		Draw_ColoredStretchPic(knob_x-knob_size/2,knob_y-knob_size/2,
			knob,knob_size,knob_size,255,255,255,
			(int)(255*xziel_mobile_hud_opacity.value*joy_alpha));

	Xziel_DrawTouchButton(xziel_hud_fire_x.value, xziel_hud_fire_y.value,
		0.073f, "FIRE", "", xziel_mobile_fire_pressed, editor);
	Xziel_DrawTouchButton(xziel_hud_adsfire_x.value, xziel_hud_adsfire_y.value,
		0.056f, "ADS", "FIRE", xziel_mobile_adsfire_pressed, editor);
	Xziel_DrawTouchButton(xziel_hud_ads_x.value, xziel_hud_ads_y.value,
		0.047f, "ADS", "", xziel_mobile_ads_pressed, editor);
	Xziel_DrawTouchButton(xziel_hud_reload_x.value, xziel_hud_reload_y.value,
		0.044f, "RLD", "", xziel_mobile_reload_pressed, editor);
	if (editor || xziel_mobile_use_available)
		Xziel_DrawTouchButton(xziel_hud_use_x.value, xziel_hud_use_y.value,
			0.050f, "USE", "", xziel_mobile_use_pressed, editor);
	Xziel_DrawTouchButton(xziel_hud_pause_x.value, xziel_hud_pause_y.value,
		0.036f, "II", "", false, editor);
	Xziel_DrawTouchButton(xziel_hud_grenade_x.value, xziel_hud_grenade_y.value,
		0.041f, "NADE", "", xziel_mobile_grenade_pressed, editor);
	Xziel_DrawTouchButton(xziel_hud_jump_x.value, xziel_hud_jump_y.value,
		0.044f, "JUMP", "", xziel_mobile_jump_pressed, editor);
	Xziel_DrawTouchButton(xziel_hud_slide_x.value, xziel_hud_slide_y.value,
		0.044f, "SLIDE", "", xziel_mobile_slide_pressed, editor);
	if (editor || !xziel_mobile_knife_range_only.value ||
		xziel_mobile_knife_target_near)
		Xziel_DrawTouchButton(xziel_hud_knife_x.value, xziel_hud_knife_y.value,
			0.044f, "KNIFE", "", xziel_mobile_knife_pressed, editor);

	Xziel_DrawWeaponStrip(editor);
}'''
text = replace_function(
    text,
    "static void Xziel_MobileHUD_DrawInternal(qboolean editor)",
    mobile_hud
)

# Live threat filter. In Solo/local host client entity numbers map to server
# edicts; use that authoritative health/class state to reject corpses and stale
# render entities. Remote clients still fall back to the model whitelist.
live_helper = r'''
static qboolean Xziel_ServerThreatAlive(int entnum)
{
	edict_t *ed;
	const char *classname;

	if (!sv.active)
		return true;
	if (entnum <= 0 || entnum >= sv.num_edicts)
		return false;

	ed = EDICT_NUM(entnum);
	if (!ed || ed->free || ed->v.health <= 0)
		return false;
	if (!((int)ed->v.flags & FL_MONSTER))
		return false;

	classname = PR_GetString(ed->v.classname);
	if (!classname)
		return false;
	return !strcmp(classname, "ai_zombie") ||
		!strcmp(classname, "ai_dog");
}
'''
if "static qboolean Xziel_ServerThreatAlive" not in text:
    idx = text.find("static void Xziel_DrawThreatIndicators(void)")
    if idx < 0:
        raise SystemExit("Could not find threat renderer")
    text = text[:idx] + live_helper + "\n" + text[idx:]

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
		if (!Xziel_ServerThreatAlive(i))
			continue;

		dx = ent->origin[0] - cl_entities[cl.viewentity].origin[0];
		dy = ent->origin[1] - cl_entities[cl.viewentity].origin[1];
		dz = ent->origin[2] - cl_entities[cl.viewentity].origin[2];
		dist = sqrtf(dx*dx + dy*dy + dz*dz);
		if (dist < 24.0f || dist > 760.0f)
			continue;

		world_yaw = atan2f(dy,dx) * 57.295779513f;
		delta = Xziel_AngleDelta(world_yaw - cl.viewangles[YAW]);
		threshold = dist < 190.0f ? 30.0f : 55.0f;
		if (fabsf(delta) < threshold)
			continue;

		if (fabsf(delta) >= 165.0f) sector = 2;
		else if (delta < -120.0f) sector = 1;
		else if (delta < 0) sector = 0;
		else if (delta > 120.0f) sector = 3;
		else sector = 4;

		if (dist < best_dist[sector])
			best_dist[sector] = dist;
	}

	for (sector = 0; sector < 5; ++sector) {
		float proximity;
		int size,x,y,alpha;

		if (best_dist[sector] >= 999998.0f)
			continue;

		proximity = 1.0f - (best_dist[sector] / 760.0f);
		if (proximity < 0.12f) proximity = 0.12f;
		if (proximity > 1.0f) proximity = 1.0f;
		size = (int)((14.0f + 11.0f*proximity) * vid.scale);
		alpha = (int)(105 + 145*proximity);

		switch (sector) {
		case 0:
			x=(int)(24*vid.scale); y=(int)(vid.height*.48f)-size/2; break;
		case 1:
			x=vid.width/2-(int)(72*vid.scale)-size/2;
			y=vid.height-(int)(76*vid.scale)-size; break;
		case 2:
			x=vid.width/2-size/2;
			y=vid.height-(int)(54*vid.scale)-size; break;
		case 3:
			x=vid.width/2+(int)(72*vid.scale)-size/2;
			y=vid.height-(int)(76*vid.scale)-size; break;
		default:
			x=vid.width-(int)(24*vid.scale)-size;
			y=(int)(vid.height*.48f)-size/2; break;
		}

		Draw_ColoredStretchPic(x,y,xziel_icon_threat,size,size,
			255,255,255,alpha);
	}
}'''
text = replace_function(text, "static void Xziel_DrawThreatIndicators(void)", threat)

# Wider editor scale limits everywhere final HUD code clamps them.
text = text.replace("if (*scale < 0.30f) *scale = 0.30f;",
                    "if (*scale < 0.20f) *scale = 0.20f;")
text = text.replace("if (*scale > 2.50f) *scale = 2.50f;",
                    "if (*scale > 4.00f) *scale = 4.00f;")
text = text.replace("if (s < 0.30f) s = 0.30f;",
                    "if (s < 0.20f) s = 0.20f;")
text = text.replace("if (s > 2.50f) s = 2.50f;",
                    "if (s > 4.00f) s = 4.00f;")

hud.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# Menus
# ---------------------------------------------------------------------------
controls = source / "menu" / "menu_controls.c"
text = controls.read_text(encoding="utf-8")

extern_anchor = "extern cvar_t xziel_mobile_ads_move_sensitivity;\n"
if "extern cvar_t xziel_modern_zombies;" not in text:
    text = add_after(text, extern_anchor,
                     "extern cvar_t xziel_modern_zombies;\n",
                     "modern zombie menu extern")

str_anchor = "static char *xziel_mobile_movement_string;\n"
if "xziel_modern_zombies_string" not in text:
    text = add_after(text, str_anchor,
                     "static char *xziel_modern_zombies_string;\n",
                     "modern zombie menu string")

toggle_anchor = "static void Menu_Mobile_ToggleModernMovement(void)"
if "Menu_Mobile_ToggleModernZombiesV22" not in text:
    idx = text.find(toggle_anchor)
    if idx < 0:
        raise SystemExit("Could not find movement toggle")
    toggle = r'''static void Menu_Mobile_ToggleModernZombiesV22(void)
{
	Cvar_SetValue("xziel_modern_zombies",
		xziel_modern_zombies.value >= 0.5f ? 0.0f : 1.0f);
}

'''
    text = text[:idx] + toggle + text[idx:]

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
	xziel_modern_zombies_string =
		xziel_modern_zombies.value >= 0.5f ? "MODERN" : "CLASSIC";

	Menu_DrawButton(row++, idx++, "MOVEMENT MODEL",
		"Modern: grounded FPS acceleration, braking, air steering and weighted jump. Classic restores legacy Quake movement.",
		Menu_Mobile_ToggleModernMovement);
	Menu_DrawOptionButton(row-1, xziel_mobile_movement_string);

	Menu_DrawButton(row++, idx++, "ZOMBIE MOTION",
		"Modern smooths zombie velocity/turn transitions while preserving NZ:P attack, crawl, barrier and death animation states.",
		Menu_Mobile_ToggleModernZombiesV22);
	Menu_DrawOptionButton(row-1, xziel_modern_zombies_string);

	Menu_DrawButton(row++, idx++, "JOYSTICK RESPONSE",
		"How quickly movement reaches full analog input. Sprint trigger still uses physical stick travel.",
		NULL);
	Menu_DrawOptionSlider(row-1, idx-1, 0.50f, 2.00f,
		xziel_mobile_joystick_sensitivity, "xziel_mobile_joystick_sensitivity",
		false, true, 0.05f);

	Menu_DrawButton(row++, idx++, "ADS WALK SPEED",
		"Actual server ADS movement multiplier. NZ:P weapon weight still applies after this; 1.00 removes the old universal 50% ADS cap.",
		NULL);
	Menu_DrawOptionSlider(row-1, idx-1, 0.35f, 1.75f,
		xziel_mobile_ads_move_sensitivity, "xziel_mobile_ads_move_sensitivity",
		false, true, 0.05f);

	Menu_DrawButton(row++, idx++, "SPRINT ACTIVATION HEIGHT",
		"Higher means drag farther above the joystick before native sprint starts.", NULL);
	Menu_DrawOptionSlider(row-1, idx-1, 1.10f, 1.85f,
		xziel_mobile_sprint_zone, "xziel_mobile_sprint_zone", false, true, 0.05f);

	Menu_DrawButton(row++, idx++, "UNLIMITED PISTOL RESERVE",
		"Pistol magazines stay finite and still reload. Enables two ordinary weapons plus a protected pistol.",
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

# 20%..400% per-control range in the editor.
text = text.replace(
    "Menu_DrawOptionSlider(1, 0, 0.30f, 2.50f, CVAR_SCALE, #CVAR_SCALE, false, true, 0.05f);",
    "Menu_DrawOptionSlider(1, 0, 0.20f, 4.00f, CVAR_SCALE, #CVAR_SCALE, false, true, 0.05f);"
)
controls.write_text(text, encoding="utf-8")

print("Applied Xziel v0.22 Vril mobile polish.")


# ===========================================================================
# v0.23 final pass: COD-style Track Fire + live minimap foundation
# ===========================================================================
# Persistent settings.
inp = source / "input.c"
text = inp.read_text(encoding="utf-8")
cvar_anchor = 'cvar_t xziel_modern_zombies = {"xziel_modern_zombies", "1", true};\n'
v23_cvars = r'''cvar_t xziel_mobile_track_fire = {"xziel_mobile_track_fire", "1", true};
cvar_t xziel_mobile_fire_camera_rotation = {"xziel_mobile_fire_camera_rotation", "1", true};
cvar_t xziel_mobile_minimap = {"xziel_mobile_minimap", "1", true};
cvar_t xziel_mobile_minimap_range = {"xziel_mobile_minimap_range", "950", true};
cvar_t xziel_hud_minimap_x = {"xziel_hud_minimap_x", "0.915", true};
cvar_t xziel_hud_minimap_y = {"xziel_hud_minimap_y", "0.155", true};
cvar_t xziel_hud_minimap_scale = {"xziel_hud_minimap_scale", "1.00", true};
cvar_t xziel_hud_minimap_opacity = {"xziel_hud_minimap_opacity", "0.88", true};
'''
if "xziel_mobile_track_fire" not in text:
    text = add_after(text, cvar_anchor, v23_cvars, "v0.23 cvars")

reg_anchor = "\tCvar_RegisterVariable(&xziel_modern_zombies);\n"
v23_regs = '''\tCvar_RegisterVariable(&xziel_mobile_track_fire);
\tCvar_RegisterVariable(&xziel_mobile_fire_camera_rotation);
\tCvar_RegisterVariable(&xziel_mobile_minimap);
\tCvar_RegisterVariable(&xziel_mobile_minimap_range);
\tCvar_RegisterVariable(&xziel_hud_minimap_x);
\tCvar_RegisterVariable(&xziel_hud_minimap_y);
\tCvar_RegisterVariable(&xziel_hud_minimap_scale);
\tCvar_RegisterVariable(&xziel_hud_minimap_opacity);
'''
if "Cvar_RegisterVariable(&xziel_mobile_track_fire);" not in text:
    text = add_after(text, reg_anchor, v23_regs, "v0.23 cvar registration")
inp.write_text(text, encoding="utf-8")

# Touch runtime. Keep the existing relative-delta aiming model, but expose the
# two COD-style concepts separately: Track/Fixed visual behavior and whether
# R-Fire is allowed to rotate the camera.
sdl = source / "platform" / "sdl" / "sys_sdl.c"
text = sdl.read_text(encoding="utf-8")

ext_anchor = "extern cvar_t xziel_mobile_ads_move_sensitivity;\n"
v23_exts = r'''extern cvar_t xziel_mobile_track_fire;
extern cvar_t xziel_mobile_fire_camera_rotation;
extern cvar_t xziel_mobile_minimap;
extern cvar_t xziel_mobile_minimap_range;
extern cvar_t xziel_hud_minimap_x;
extern cvar_t xziel_hud_minimap_y;
extern cvar_t xziel_hud_minimap_scale;
extern cvar_t xziel_hud_minimap_opacity;
'''
if "extern cvar_t xziel_mobile_track_fire;" not in text:
    text = add_after(text, ext_anchor, v23_exts, "v0.23 SDL externs")

# Append one editor-only role after SLIDE, preserving all established role IDs.
if "XZ_TOUCH_MINIMAP" not in text:
    enum_end = text.find("} xziel_touch_role_t;")
    if enum_end < 0:
        raise SystemExit("Could not find touch role enum for minimap")
    prefix = text[:enum_end].rstrip()
    if not prefix.endswith(","):
        prefix += ","
    text = prefix + "\n\tXZ_TOUCH_MINIMAP\n" + text[enum_end:]

state_anchor = "qboolean xziel_mobile_slide_pressed = false;\n"
v23_state = r'''float xziel_mobile_track_fire_dx = 0.0f;
float xziel_mobile_track_fire_dy = 0.0f;
float xziel_mobile_track_adsfire_dx = 0.0f;
float xziel_mobile_track_adsfire_dy = 0.0f;
'''
if "xziel_mobile_track_fire_dx" not in text:
    text = add_after(text, state_anchor, v23_state, "Track Fire state")

editor_role_v23 = r'''static xziel_touch_role_t Xziel_HudEditorRole(float x, float y)
{
	float hs = xziel_mobile_hud_scale.value;
	if (Xziel_IsInside(x, y, xziel_hud_minimap_x.value, xziel_hud_minimap_y.value,
		0.082f * hs * xziel_hud_minimap_scale.value)) return XZ_TOUCH_MINIMAP;
	if (Xziel_WeaponStripHit(x, y, 0)) return XZ_TOUCH_WEAPONSTRIP;
	if (Xziel_WeaponStripHit(x, y, 1)) return XZ_TOUCH_WEAPON2;
	if (Xziel_WeaponStripHit(x, y, 2)) return XZ_TOUCH_WEAPON3;
	if (Xziel_IsInside(x, y, xziel_hud_fire_x.value, xziel_hud_fire_y.value, 0.090f * hs * xziel_hud_fire_scale.value)) return XZ_TOUCH_FIRE;
	if (Xziel_IsInside(x, y, xziel_hud_adsfire_x.value, xziel_hud_adsfire_y.value, 0.075f * hs * xziel_hud_adsfire_scale.value)) return XZ_TOUCH_ADSFIRE;
	if (Xziel_IsInside(x, y, xziel_hud_ads_x.value, xziel_hud_ads_y.value, 0.065f * hs * xziel_hud_ads_scale.value)) return XZ_TOUCH_ADS;
	if (Xziel_IsInside(x, y, xziel_hud_reload_x.value, xziel_hud_reload_y.value, 0.060f * hs * xziel_hud_reload_scale.value)) return XZ_TOUCH_RELOAD;
	if (Xziel_IsInside(x, y, xziel_hud_use_x.value, xziel_hud_use_y.value, 0.065f * hs * xziel_hud_use_scale.value)) return XZ_TOUCH_USE;
	if (Xziel_IsInside(x, y, xziel_hud_pause_x.value, xziel_hud_pause_y.value, 0.055f * hs * xziel_hud_pause_scale.value)) return XZ_TOUCH_PAUSE;
	if (Xziel_IsInside(x, y, xziel_hud_grenade_x.value, xziel_hud_grenade_y.value, 0.057f * hs * xziel_hud_grenade_scale.value)) return XZ_TOUCH_GRENADE;
	if (Xziel_IsInside(x, y, xziel_hud_slide_x.value, xziel_hud_slide_y.value, 0.060f * hs * xziel_hud_slide_scale.value)) return XZ_TOUCH_SLIDE;
	if (Xziel_IsInside(x, y, xziel_hud_jump_x.value, xziel_hud_jump_y.value, 0.060f * hs * xziel_hud_jump_scale.value)) return XZ_TOUCH_JUMP;
	if (Xziel_IsInside(x, y, xziel_hud_knife_x.value, xziel_hud_knife_y.value, 0.060f * hs * xziel_hud_knife_scale.value)) return XZ_TOUCH_KNIFE;
	if (Xziel_IsInside(x, y, xziel_hud_joy_x.value, xziel_hud_joy_y.value, 0.120f * hs * xziel_hud_joy_scale.value)) return XZ_TOUCH_MOVE;
	return XZ_TOUCH_NONE;
}'''
text = replace_function(text, "static xziel_touch_role_t Xziel_HudEditorRole", editor_role_v23)

editor_set_v23 = r'''static void Xziel_HudEditorSetPosition(xziel_touch_role_t role, float x, float y)
{
	if (x < 0.035f) x = 0.035f;
	if (x > 0.965f) x = 0.965f;
	if (y < 0.055f) y = 0.055f;
	if (y > 0.945f) y = 0.945f;
	xziel_hud_editor_selected = role;
	switch (role) {
	case XZ_TOUCH_MOVE: Cvar_SetValue("xziel_hud_joy_x", x); Cvar_SetValue("xziel_hud_joy_y", y); break;
	case XZ_TOUCH_FIRE: Cvar_SetValue("xziel_hud_fire_x", x); Cvar_SetValue("xziel_hud_fire_y", y); break;
	case XZ_TOUCH_ADSFIRE: Cvar_SetValue("xziel_hud_adsfire_x", x); Cvar_SetValue("xziel_hud_adsfire_y", y); break;
	case XZ_TOUCH_ADS: Cvar_SetValue("xziel_hud_ads_x", x); Cvar_SetValue("xziel_hud_ads_y", y); break;
	case XZ_TOUCH_RELOAD: Cvar_SetValue("xziel_hud_reload_x", x); Cvar_SetValue("xziel_hud_reload_y", y); break;
	case XZ_TOUCH_USE: Cvar_SetValue("xziel_hud_use_x", x); Cvar_SetValue("xziel_hud_use_y", y); break;
	case XZ_TOUCH_JUMP: Cvar_SetValue("xziel_hud_jump_x", x); Cvar_SetValue("xziel_hud_jump_y", y); break;
	case XZ_TOUCH_SLIDE: Cvar_SetValue("xziel_hud_slide_x", x); Cvar_SetValue("xziel_hud_slide_y", y); break;
	case XZ_TOUCH_KNIFE: Cvar_SetValue("xziel_hud_knife_x", x); Cvar_SetValue("xziel_hud_knife_y", y); break;
	case XZ_TOUCH_GRENADE: Cvar_SetValue("xziel_hud_grenade_x", x); Cvar_SetValue("xziel_hud_grenade_y", y); break;
	case XZ_TOUCH_PAUSE: Cvar_SetValue("xziel_hud_pause_x", x); Cvar_SetValue("xziel_hud_pause_y", y); break;
	case XZ_TOUCH_WEAPONSTRIP: Cvar_SetValue("xziel_hud_weapon1_x", x); Cvar_SetValue("xziel_hud_weapon1_y", y); break;
	case XZ_TOUCH_WEAPON2: Cvar_SetValue("xziel_hud_weapon2_x", x); Cvar_SetValue("xziel_hud_weapon2_y", y); break;
	case XZ_TOUCH_WEAPON3: Cvar_SetValue("xziel_hud_pistol_x", x); Cvar_SetValue("xziel_hud_pistol_y", y); break;
	case XZ_TOUCH_MINIMAP: Cvar_SetValue("xziel_hud_minimap_x", x); Cvar_SetValue("xziel_hud_minimap_y", y); break;
	default: break;
	}
}'''
text = replace_function(text, "static void Xziel_HudEditorSetPosition", editor_set_v23)

# Reset the tracked knob to center on each new FIRE / ADS+FIRE press.
down_block = '''\tslot->role = Xziel_RoleForPoint(finger->x, finger->y);
\tslot->last_x = finger->x;
\tslot->last_y = finger->y;
\tif (slot->role == XZ_TOUCH_MOVE) {
'''
down_repl = '''\tslot->role = Xziel_RoleForPoint(finger->x, finger->y);
\tslot->last_x = finger->x;
\tslot->last_y = finger->y;
\tif (slot->role == XZ_TOUCH_FIRE) {
\t\txziel_mobile_track_fire_dx = 0.0f;
\t\txziel_mobile_track_fire_dy = 0.0f;
\t} else if (slot->role == XZ_TOUCH_ADSFIRE) {
\t\txziel_mobile_track_adsfire_dx = 0.0f;
\t\txziel_mobile_track_adsfire_dy = 0.0f;
\t}
\tif (slot->role == XZ_TOUCH_MOVE) {
'''
fd0 = text.find("static void Xziel_FingerDown")
fd1 = text.find("static void Xziel_FingerMotion", fd0)
if fd0 < 0 or fd1 < 0:
    raise SystemExit("Could not find FingerDown for Track Fire")
fd = text[fd0:fd1]
if "xziel_mobile_track_fire_dx = 0.0f;" not in fd:
    if down_block not in fd:
        raise SystemExit("Could not find FingerDown gameplay block")
    fd = fd.replace(down_block, down_repl, 1)
    text = text[:fd0] + fd + text[fd1:]

# Existing mobile controls already aim by relative drag while FIRE/ADS+FIRE is
# held. Preserve that feel, add the explicit camera-rotation switch, and track
# the visual knob inside the circular button.
fm0 = text.find("static void Xziel_FingerMotion")
fm1 = text.find("static void Xziel_Finger", fm0 + 10)
if fm0 < 0:
    raise SystemExit("Could not find FingerMotion")
if fm1 < 0:
    fm1 = text.find("#endif", fm0)
fm = text[fm0:fm1]
motion_old = '''\t\tmouse_dx += (int)((finger->x - slot->last_x) * (float)vid.width * look_scale);
\t\tmouse_dy += (int)((finger->y - slot->last_y) * (float)vid.height * look_scale);
'''
motion_new = '''\t\tif (!((slot->role == XZ_TOUCH_FIRE || slot->role == XZ_TOUCH_ADSFIRE) &&
\t\t\txziel_mobile_fire_camera_rotation.value < 0.5f)) {
\t\t\tmouse_dx += (int)((finger->x - slot->last_x) * (float)vid.width * look_scale);
\t\t\tmouse_dy += (int)((finger->y - slot->last_y) * (float)vid.height * look_scale);
\t\t}

\t\tif (xziel_mobile_track_fire.value >= 0.5f &&
\t\t\t(slot->role == XZ_TOUCH_FIRE || slot->role == XZ_TOUCH_ADSFIRE)) {
\t\t\tfloat cx = slot->role == XZ_TOUCH_FIRE ? xziel_hud_fire_x.value : xziel_hud_adsfire_x.value;
\t\t\tfloat cy = slot->role == XZ_TOUCH_FIRE ? xziel_hud_fire_y.value : xziel_hud_adsfire_y.value;
\t\t\tfloat rs = slot->role == XZ_TOUCH_FIRE ?
\t\t\t\t(0.073f * xziel_mobile_hud_scale.value * xziel_hud_fire_scale.value) :
\t\t\t\t(0.056f * xziel_mobile_hud_scale.value * xziel_hud_adsfire_scale.value);
\t\t\tfloat dx = (finger->x - cx) * ((float)vid.width / (float)vid.height) / rs;
\t\t\tfloat dy = (finger->y - cy) / rs;
\t\t\tfloat len = sqrtf(dx*dx + dy*dy);
\t\t\tif (len > 0.78f) { dx *= 0.78f/len; dy *= 0.78f/len; }
\t\t\tif (slot->role == XZ_TOUCH_FIRE) {
\t\t\t\txziel_mobile_track_fire_dx = dx;
\t\t\t\txziel_mobile_track_fire_dy = dy;
\t\t\t} else {
\t\t\t\txziel_mobile_track_adsfire_dx = dx;
\t\t\t\txziel_mobile_track_adsfire_dy = dy;
\t\t\t}
\t\t}
'''
if "xziel_mobile_fire_camera_rotation.value" not in fm:
    if motion_old not in fm:
        raise SystemExit("Could not find relative-look lines in FingerMotion")
    fm = fm.replace(motion_old, motion_new, 1)
    text = text[:fm0] + fm + text[fm1:]

sdl.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# v0.23 HUD presentation: distinct controls, compact weapon cards and minimap
# ---------------------------------------------------------------------------
hud = source / "render" / "r_hud.c"
text = hud.read_text(encoding="utf-8")

hud_ext_anchor = "extern cvar_t xziel_hud_slide_opacity;\n"
hud_exts = r'''extern cvar_t xziel_mobile_track_fire;
extern cvar_t xziel_mobile_fire_camera_rotation;
extern cvar_t xziel_mobile_minimap;
extern cvar_t xziel_mobile_minimap_range;
extern cvar_t xziel_hud_minimap_x;
extern cvar_t xziel_hud_minimap_y;
extern cvar_t xziel_hud_minimap_scale;
extern cvar_t xziel_hud_minimap_opacity;
extern float xziel_mobile_track_fire_dx;
extern float xziel_mobile_track_fire_dy;
extern float xziel_mobile_track_adsfire_dx;
extern float xziel_mobile_track_adsfire_dy;
'''
if "extern cvar_t xziel_mobile_track_fire;" not in text:
    text = add_after(text, hud_ext_anchor, hud_exts, "v0.23 HUD externs")

handle_anchor = "static image_t xziel_joystick_knob_active;\n"
v23_handles = r'''static image_t xziel_icon_adsfire;
static image_t xziel_touch_small_idle;
static image_t xziel_touch_small_pressed;
static image_t xziel_touch_fire_idle;
static image_t xziel_touch_fire_pressed;
static image_t xziel_touch_ads_idle;
static image_t xziel_touch_ads_pressed;
static image_t xziel_touch_adsfire_idle;
static image_t xziel_touch_adsfire_pressed;
static image_t xziel_minimap_ring;
static image_t xziel_minimap_player;
'''
if "static image_t xziel_icon_adsfire;" not in text:
    text = add_after(text, handle_anchor, v23_handles, "v0.23 image handles")

load_anchor = '    xziel_joystick_knob_active = Image_LoadImage("gfx/xziel/joystick_knob_active", IMAGE_PNG, 0, true, false);\n'
v23_loads = r'''    xziel_icon_adsfire = Image_LoadImage("gfx/xziel/adsfire", IMAGE_PNG, 0, true, false);
    xziel_touch_small_idle = Image_LoadImage("gfx/xziel/touch_small_idle", IMAGE_PNG, 0, true, false);
    xziel_touch_small_pressed = Image_LoadImage("gfx/xziel/touch_small_pressed", IMAGE_PNG, 0, true, false);
    xziel_touch_fire_idle = Image_LoadImage("gfx/xziel/touch_fire_idle", IMAGE_PNG, 0, true, false);
    xziel_touch_fire_pressed = Image_LoadImage("gfx/xziel/touch_fire_pressed", IMAGE_PNG, 0, true, false);
    xziel_touch_ads_idle = Image_LoadImage("gfx/xziel/touch_ads_idle", IMAGE_PNG, 0, true, false);
    xziel_touch_ads_pressed = Image_LoadImage("gfx/xziel/touch_ads_pressed", IMAGE_PNG, 0, true, false);
    xziel_touch_adsfire_idle = Image_LoadImage("gfx/xziel/touch_adsfire_idle", IMAGE_PNG, 0, true, false);
    xziel_touch_adsfire_pressed = Image_LoadImage("gfx/xziel/touch_adsfire_pressed", IMAGE_PNG, 0, true, false);
    xziel_minimap_ring = Image_LoadImage("gfx/xziel/minimap_ring", IMAGE_PNG, 0, true, false);
    xziel_minimap_player = Image_LoadImage("gfx/xziel/minimap_player", IMAGE_PNG, 0, true, false);
'''
if 'gfx/xziel/adsfire' not in text:
    text = add_after(text, load_anchor, v23_loads, "v0.23 image loads")

action_icon_v23 = r'''static image_t Xziel_ActionIcon(const char *label1, const char *label2)
{
	if (!strcmp(label1, "ADS") && label2 && !strcmp(label2, "FIRE")) return xziel_icon_adsfire;
	if (!strcmp(label1, "FIRE")) return xziel_icon_fire;
	if (!strcmp(label1, "ADS")) return xziel_icon_ads;
	if (!strcmp(label1, "RLD")) return xziel_icon_reload;
	if (!strcmp(label1, "USE")) return xziel_icon_use;
	if (!strcmp(label1, "JUMP")) return xziel_icon_jump;
	if (!strcmp(label1, "KNIFE")) return xziel_icon_knife;
	if (!strcmp(label1, "NADE")) return xziel_icon_grenade;
	if (!strcmp(label1, "SLIDE")) return xziel_icon_slide;
	if (!strcmp(label1, "II")) return xziel_icon_pause;
	return 0;
}'''
text = replace_function(text, "static image_t Xziel_ActionIcon", action_icon_v23)

action_glyph_v23 = r'''static qboolean Xziel_DrawActionGlyph(int cx, int cy, int radius,
	const char *label1, const char *label2, qboolean pressed)
{
	image_t icon = Xziel_ActionIcon(label1, label2);
	int size;
	int alpha;
	int gx = cx, gy = cy;

	if (!icon)
		return false;

	if (!strcmp(label1, "FIRE")) {
		size = (int)(radius * 1.08f);
		if (pressed && xziel_mobile_track_fire.value >= 0.5f) {
			gx += (int)(xziel_mobile_track_fire_dx * radius * 0.58f);
			gy += (int)(xziel_mobile_track_fire_dy * radius * 0.58f);
		}
	} else if (!strcmp(label1, "ADS") && label2 && !strcmp(label2, "FIRE")) {
		size = (int)(radius * 1.18f);
		if (pressed && xziel_mobile_track_fire.value >= 0.5f) {
			gx += (int)(xziel_mobile_track_adsfire_dx * radius * 0.58f);
			gy += (int)(xziel_mobile_track_adsfire_dy * radius * 0.58f);
		}
	} else if (!strcmp(label1, "ADS")) {
		size = (int)(radius * 1.08f);
	} else {
		size = (int)(radius * 0.90f);
	}

	if (size < 14) size = 14;
	alpha = pressed ? 255 : 238;
	Draw_ColoredStretchPic(gx - size/2, gy - size/2, icon,
		size, size, 255,255,255,alpha);
	return true;
}'''
action_pos = text.rfind("static qboolean Xziel_DrawActionGlyph(")
if action_pos < 0:
    raise SystemExit("Could not find final action glyph for v0.23")
text = text[:action_pos] + replace_function(
    text[action_pos:], "static qboolean Xziel_DrawActionGlyph(", action_glyph_v23
)

touch_v23 = r'''static void Xziel_DrawTouchButton(float nx, float ny, float radius_h,
	const char *label1, const char *label2, qboolean pressed, qboolean editor)
{
	float local_scale, local_opacity;
	int cx = (int)(nx * vid.width);
	int cy = (int)(ny * vid.height);
	int radius;
	int size;
	int alpha;
	image_t surface = 0;

	Xziel_ControlStyle(label1, label2, &local_scale, &local_opacity);
	if (local_scale < 0.20f) local_scale = 0.20f;
	if (local_scale > 4.00f) local_scale = 4.00f;
	if (local_opacity < 0.15f) local_opacity = 0.15f;
	if (local_opacity > 1.00f) local_opacity = 1.00f;

	radius = (int)(radius_h * vid.height *
		xziel_mobile_hud_scale.value * local_scale);
	if (radius < 9) radius = 9;
	size = (int)(radius * 2.14f);
	alpha = (int)(255 * xziel_mobile_hud_opacity.value * local_opacity);

	if (editor) {
		surface = xziel_touch_editor;
	} else if (!strcmp(label1, "FIRE")) {
		surface = pressed ? xziel_touch_fire_pressed : xziel_touch_fire_idle;
	} else if (!strcmp(label1, "ADS") && label2 && !strcmp(label2, "FIRE")) {
		surface = pressed ? xziel_touch_adsfire_pressed : xziel_touch_adsfire_idle;
	} else if (!strcmp(label1, "ADS")) {
		surface = pressed ? xziel_touch_ads_pressed : xziel_touch_ads_idle;
	} else {
		surface = pressed ? xziel_touch_small_pressed : xziel_touch_small_idle;
	}

	if (surface)
		Draw_ColoredStretchPic(cx - size/2, cy - size/2, surface,
			size,size,255,255,255,alpha);

	Xziel_DrawActionGlyph(cx,cy,radius,label1,label2,pressed);
}'''
text = replace_function(text, "static void Xziel_DrawTouchButton(", touch_v23)

weapon_card_v23 = r'''static void Xziel_DrawWeaponCard(int cx, int cy, int w, int h,
	int weapon, int mag, int reserve, qboolean active, qboolean editor,
	float opacity, const char *slot_name)
{
	int x = cx - w/2;
	int y = cy - h/2;
	int border = (int)fmaxf(1.0f, 1.5f * vid.scale);
	int panel_alpha;
	int edge_alpha;
	int chip;
	char ammo[32];
	qboolean protected_pistol =
		xziel_mobile_unlimited_pistol.value >= 0.5f &&
		Xziel_HUDIsPistol(weapon);

	if (opacity < 0.15f) opacity = 0.15f;
	if (opacity > 1.0f) opacity = 1.0f;
	panel_alpha = (int)((active ? 204 : 164) *
		xziel_mobile_hud_opacity.value * opacity);
	edge_alpha = (int)((active ? 250 : 152) *
		xziel_mobile_hud_opacity.value * opacity);

	/* Dark graphite card with a thin warm outline. Do not tint the whole
	   active panel yellow: that was the main visual mismatch in v0.23 RC1. */
	Draw_FillByColor(x, y, w, h, 5,8,11,panel_alpha);
	Draw_FillByColor(x + border, y + border, w - border*2, h - border*2,
		10,13,16,(int)((active ? 222 : 188) *
		xziel_mobile_hud_opacity.value * opacity));
	Draw_FillByColor(x + border*2, y + border*2, w - border*4,
		(int)fmaxf(1.0f, 5.0f*vid.scale), 24,28,32,(int)(88*opacity));

	/* Four explicit border strips create the selected yellow outline without
	   bleeding yellow through the translucent card body. */
	Draw_FillByColor(x, y, w, border,
		active ? 244 : 92, active ? 198 : 100, active ? 42 : 108, edge_alpha);
	Draw_FillByColor(x, y + h - border, w, border,
		active ? 244 : 92, active ? 198 : 100, active ? 42 : 108, edge_alpha);
	Draw_FillByColor(x, y, border, h,
		active ? 244 : 92, active ? 198 : 100, active ? 42 : 108, edge_alpha);
	Draw_FillByColor(x + w - border, y, border, h,
		active ? 244 : 92, active ? 198 : 100, active ? 42 : 108, edge_alpha);

	chip = (int)(14.0f * vid.scale);
	if (chip < 11) chip = 11;
	Draw_FillByColor(x + border, y + border, chip, chip,
		active ? 244 : 62, active ? 198 : 67, active ? 42 : 72,
		(int)(232*opacity));
	{
		int tw = getTextWidth((char *)slot_name, vid.scale*0.56f);
		Draw_ColoredString(x + border + (chip-tw)/2,
			y + border + (int)(2*vid.scale), (char *)slot_name,
			active ? 12 : 235, active ? 12 : 235, active ? 12 : 235,
			245,vid.scale*0.56f);
	}

	if (weapon != 0) {
		float icon_scale = h / (active ? 48.0f : 52.0f);
		Xziel_DrawWeaponGlyph(cx, cy - (int)(5*vid.scale), weapon,
			icon_scale, (int)((active ? 255 : 224)*opacity));

		if (protected_pistol)
			snprintf(ammo, sizeof(ammo), "%d / INF", mag);
		else
			snprintf(ammo, sizeof(ammo), "%d / %d", mag, reserve);

		Draw_ColoredString(x + (int)(7*vid.scale),
			y + h - (int)(12*vid.scale), ammo,
			244,246,248,(int)(242*opacity),
			vid.scale*(active ? 0.72f : 0.64f));
	} else if (editor) {
		const char *empty = "EMPTY";
		int tw = getTextWidth((char *)empty, vid.scale*0.55f);
		Draw_ColoredString(cx-tw/2,cy-(int)(3*vid.scale),(char *)empty,
			145,151,158,(int)(185*opacity),vid.scale*0.55f);
	}
}'''
text = replace_function(text, "static void Xziel_DrawWeaponCard(", weapon_card_v23)

# Slightly widen the v0.20 rail without changing the user's saved positions.
text = text.replace(
    "int w = (int)((i==0 ? 108 : 84) * vid.scale * c[i].s);",
    "int w = (int)((i==0 ? 118 : 96) * vid.scale * c[i].s);"
)
text = text.replace(
    "int h = (int)((i==0 ? 60 : 50) * vid.scale * c[i].s);",
    "int h = (int)((i==0 ? 59 : 52) * vid.scale * c[i].s);"
)

# Live rotating player-up minimap. It reuses the strict zombie whitelist and
# server-authoritative alive filter, so dead/stale render entities never become
# phantom red dots.
mobile_pos = text.find("static void Xziel_MobileHUD_DrawInternal")
if mobile_pos < 0:
    raise SystemExit("Could not find mobile HUD renderer for minimap")
if "static void Xziel_DrawMiniMapV23" not in text:
    minimap_v23 = r'''
static qboolean Xziel_IsZombieThreatEntity(entity_t *ent);
static qboolean Xziel_ServerThreatAlive(int entnum);

static void Xziel_DrawMiniMapV23(qboolean editor)
{
	float s = xziel_hud_minimap_scale.value;
	float o = xziel_hud_minimap_opacity.value;
	float range = xziel_mobile_minimap_range.value;
	int cx,cy,radius,size,inner,alpha;
	int i;
	float yaw,cs,sn;

	if (!editor && xziel_mobile_minimap.value < 0.5f)
		return;
	if (!editor && (key_dest != key_game || cl.stats[STAT_HEALTH] <= 0))
		return;

	if (s < 0.20f) s = 0.20f;
	if (s > 4.00f) s = 4.00f;
	if (o < 0.15f) o = 0.15f;
	if (o > 1.00f) o = 1.00f;
	if (range < 300.0f) range = 300.0f;
	if (range > 2400.0f) range = 2400.0f;

	cx = (int)(xziel_hud_minimap_x.value * vid.width);
	cy = (int)(xziel_hud_minimap_y.value * vid.height);
	radius = (int)(0.090f * vid.height * xziel_mobile_hud_scale.value * s);
	if (radius < 28) radius = 28;
	size = radius*2;
	inner = (int)(radius*0.76f);
	alpha = (int)(255*xziel_mobile_hud_opacity.value*o);

	if (xziel_minimap_ring)
		Draw_ColoredStretchPic(cx-radius,cy-radius,xziel_minimap_ring,
			size,size,255,255,255,alpha);

	if (editor || cl.viewentity <= 0 || cl.viewentity >= cl.num_entities) {
		if (xziel_minimap_player) {
			int p=(int)(radius*0.30f);
			Draw_ColoredStretchPic(cx-p/2,cy-p/2,xziel_minimap_player,
				p,p,255,226,92,245);
		}
		return;
	}

	yaw = cl.viewangles[YAW] * 0.017453292519943295f;
	cs = cosf(yaw);
	sn = sinf(yaw);

	for (i=1; i<cl.num_entities; ++i) {
		entity_t *ent;
		float dx,dy,dz,dist,fwd,right,nx,ny;
		int px,py,dot;
		if (i == cl.viewentity) continue;
		ent = &cl_entities[i];
		if (!Xziel_IsZombieThreatEntity(ent)) continue;
		if (!Xziel_ServerThreatAlive(i)) continue;

		dx = ent->origin[0] - cl_entities[cl.viewentity].origin[0];
		dy = ent->origin[1] - cl_entities[cl.viewentity].origin[1];
		dz = ent->origin[2] - cl_entities[cl.viewentity].origin[2];
		dist = sqrtf(dx*dx + dy*dy + dz*dz);
		if (dist > range || dist < 12.0f) continue;

		fwd = dx*cs + dy*sn;
		right = -dx*sn + dy*cs;
		nx = right/range;
		ny = -fwd/range;
		if (nx*nx + ny*ny > 0.96f) continue;
		px = cx + (int)(nx*inner);
		py = cy + (int)(ny*inner);
		dot = (int)fmaxf(3.0f, 4.0f*vid.scale*s);
		Draw_FillByColor(px-dot/2,py-dot/2,dot,dot,
			229,38,44,(int)(242*o));
	}

	if (xziel_minimap_player) {
		int p=(int)(radius*0.30f);
		Draw_ColoredStretchPic(cx-p/2,cy-p/2,xziel_minimap_player,
			p,p,255,226,92,245);
	}

	/* Cardinal markers rotate around a fixed player-up arrow. */
	{
		const char *labels[4]={"N","E","S","W"};
		float wx[4]={0,1,0,-1};
		float wy[4]={1,0,-1,0};
		int k;
		for (k=0;k<4;++k) {
			float f=wx[k]*cs+wy[k]*sn;
			float r=-wx[k]*sn+wy[k]*cs;
			int tx=cx+(int)(r*radius*0.83f);
			int ty=cy-(int)(f*radius*0.83f);
			int tw=getTextWidth((char*)labels[k],vid.scale*0.48f*s);
			Draw_ColoredString(tx-tw/2,ty-(int)(3*vid.scale*s),
				(char*)labels[k],215,220,225,(int)(205*o),
				vid.scale*0.48f*s);
		}
	}
}

'''
    text = text[:mobile_pos] + minimap_v23 + text[mobile_pos:]

# Draw minimap before controls so controls remain on top if the user overlaps
# them in Custom HUD.
mh0 = text.find("static void Xziel_MobileHUD_DrawInternal")
mh1 = text.find("static void Xziel_MobileHUD_Draw(", mh0)
if mh0 < 0:
    raise SystemExit("Could not find final mobile HUD for minimap call")
mh = text[mh0:mh1 if mh1 > 0 else len(text)]
health_block = '''\tif (!editor && (key_dest != key_game || cl.stats[STAT_HEALTH] <= 0))
\t\treturn;
'''
if "Xziel_DrawMiniMapV23(editor);" not in mh:
    if health_block not in mh:
        raise SystemExit("Could not find HUD early-return block")
    mh = mh.replace(health_block, health_block + "\n\tXziel_DrawMiniMapV23(editor);\n", 1)
    text = text[:mh0] + mh + text[mh1 if mh1 > 0 else len(text):]

hud.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# v0.23 menus: Track/Fixed fire and Custom HUD minimap
# ---------------------------------------------------------------------------
controls = source / "menu" / "menu_controls.c"
text = controls.read_text(encoding="utf-8")

menu_ext_anchor = "extern cvar_t xziel_modern_zombies;\n"
menu_exts = r'''extern cvar_t xziel_mobile_track_fire;
extern cvar_t xziel_mobile_fire_camera_rotation;
extern cvar_t xziel_mobile_minimap;
extern cvar_t xziel_mobile_minimap_range;
extern cvar_t xziel_hud_minimap_x;
extern cvar_t xziel_hud_minimap_y;
extern cvar_t xziel_hud_minimap_scale;
extern cvar_t xziel_hud_minimap_opacity;
'''
if "extern cvar_t xziel_mobile_track_fire;" not in text:
    text = add_after(text, menu_ext_anchor, menu_exts, "v0.23 menu externs")

helper_anchor = "static void Menu_Mobile_ToggleModernZombiesV22(void)"
if "Menu_Mobile_ToggleTrackFireV23" not in text:
    idx = text.find(helper_anchor)
    if idx < 0:
        raise SystemExit("Could not find v0.22 menu helper anchor")
    helpers = r'''static char *xziel_mobile_track_fire_string;
static char *xziel_mobile_fire_rotation_string;

static void Menu_Mobile_ToggleTrackFireV23(void)
{
	Cvar_SetValue("xziel_mobile_track_fire",
		xziel_mobile_track_fire.value >= 0.5f ? 0.0f : 1.0f);
}

static void Menu_Mobile_ToggleFireRotationV23(void)
{
	Cvar_SetValue("xziel_mobile_fire_camera_rotation",
		xziel_mobile_fire_camera_rotation.value >= 0.5f ? 0.0f : 1.0f);
}

'''
    text = text[:idx] + helpers + text[idx:]

# Add COD-style fire behavior controls without removing the existing ADS
# Hold/Toggle or sensitivity families.
aim0 = text.find("void Menu_MobileAim_Draw(void)")
if aim0 < 0:
    raise SystemExit("Could not find Mobile Aim menu for v0.23")
aim1 = text.find("}", text.find("{", aim0))
depth=0
for j in range(text.find("{", aim0), len(text)):
    if text[j] == "{": depth += 1
    elif text[j] == "}":
        depth -= 1
        if depth == 0:
            aim1 = j+1
            break
aim = text[aim0:aim1]

if "xziel_mobile_track_fire_string =" not in aim:
    assign = '''\txziel_mobile_ads_button_string =
\t\txziel_mobile_ads_toggle.value >= 0.5f ? "TOGGLE" : "HOLD";
'''
    extra_assign = assign + '''\txziel_mobile_track_fire_string =
\t\txziel_mobile_track_fire.value >= 0.5f ? "TRACK" : "FIXED";
\txziel_mobile_fire_rotation_string =
\t\txziel_mobile_fire_camera_rotation.value >= 0.5f ? "ON" : "OFF";
'''
    if assign not in aim:
        raise SystemExit("Could not find ADS button string in Mobile Aim")
    aim = aim.replace(assign, extra_assign, 1)

ads_option = '''\tMenu_DrawOptionButton(b-1, xziel_mobile_ads_button_string);
'''
if '"FIRE BUTTON BEHAVIOR"' not in aim:
    fire_rows = r'''
	Menu_DrawButton(b++, i++, "FIRE BUTTON BEHAVIOR",
		"Track lets the FIRE / ADS+FIRE control follow your thumb inside the button while you aim and shoot. Fixed keeps the icon centered.",
		Menu_Mobile_ToggleTrackFireV23);
	Menu_DrawOptionButton(b-1, xziel_mobile_track_fire_string);

	Menu_DrawButton(b++, i++, "FIRE CAMERA ROTATION",
		"ON lets dragging FIRE / ADS+FIRE rotate the camera while the shot remains held, matching modern mobile FPS controls.",
		Menu_Mobile_ToggleFireRotationV23);
	Menu_DrawOptionButton(b-1, xziel_mobile_fire_rotation_string);
'''
    if ads_option not in aim:
        raise SystemExit("Could not find ADS option row in Mobile Aim")
    aim = aim.replace(ads_option, ads_option + fire_rows, 1)
text = text[:aim0] + aim + text[aim1:]

# Custom HUD role 17 is the v0.23 minimap. It can be dragged and independently
# resized/faded exactly like the rest of the touch layout.
ed0 = text.find("void Menu_HudEdit_Draw(void)")
if ed0 < 0:
    raise SystemExit("Could not find Custom HUD menu for minimap")
brace = text.find("{", ed0); depth=0; ed1=-1
for j in range(brace, len(text)):
    if text[j] == "{": depth += 1
    elif text[j] == "}":
        depth -= 1
        if depth == 0:
            ed1=j+1
            break
ed = text[ed0:ed1]

if 'case 17: name="MINIMAP";' not in ed:
    label_anchor = '\tcase 16: name="CROUCH / SLIDE"; break;\n'
    if label_anchor not in ed:
        raise SystemExit("Could not find slide label in Custom HUD")
    ed = ed.replace(label_anchor,
        label_anchor + '\tcase 17: name="MINIMAP"; break;\n', 1)

if "case 17: DRAW_STYLE(xziel_hud_minimap_scale" not in ed:
    style_anchor = "\tcase 16: DRAW_STYLE(xziel_hud_slide_scale, xziel_hud_slide_opacity); break;\n"
    if style_anchor not in ed:
        raise SystemExit("Could not find slide style in Custom HUD")
    ed = ed.replace(style_anchor, style_anchor +
        "\tcase 17: DRAW_STYLE(xziel_hud_minimap_scale, xziel_hud_minimap_opacity); break;\n", 1)

text = text[:ed0] + ed + text[ed1:]

# Restore minimap defaults together with the rest of the Custom HUD.
reset0 = text.find("static void Menu_HudEdit_Reset(void)")
if reset0 < 0:
    raise SystemExit("Could not find Custom HUD reset")
brace = text.find("{", reset0); depth=0; reset1=-1
for j in range(brace, len(text)):
    if text[j] == "{": depth += 1
    elif text[j] == "}":
        depth -= 1
        if depth == 0:
            reset1=j+1
            break
reset = text[reset0:reset1]
if '"xziel_hud_minimap_x"' not in reset:
    reset_anchor = '\tCvar_SetValue("xziel_hud_slide_scale", 1.0f); Cvar_SetValue("xziel_hud_slide_opacity", 0.82f);\n'
    payload = reset_anchor + \
        '\tCvar_SetValue("xziel_hud_minimap_x", 0.915f); Cvar_SetValue("xziel_hud_minimap_y", 0.155f);\n' + \
        '\tCvar_SetValue("xziel_hud_minimap_scale", 1.0f); Cvar_SetValue("xziel_hud_minimap_opacity", 0.88f);\n'
    if reset_anchor not in reset:
        raise SystemExit("Could not find slide reset anchor")
    reset = reset.replace(reset_anchor, payload, 1)
    text = text[:reset0] + reset + text[reset1:]

controls.write_text(text, encoding="utf-8")
print("Applied Xziel v0.23 COD-style HUD, Track Fire and live minimap.")
