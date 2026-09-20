#!/usr/bin/env python3
"""Xziel v0.20 professional mobile weapon HUD.

Presentation-only:
- category-correct CC0 weapon silhouettes;
- compact active/inactive hierarchy;
- ammo readability and protected-pistol treatment;
- switch pulse when the active weapon changes;
- active weapon name without re-networking weapon state;
- dynamic custom-HUD label for the protected pistol slot.

Applied after patch_vril_mobile_v018.py.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_vril_weaponhud_v020.py <vril-root>")

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

hud = source / "render" / "r_hud.c"
text = hud.read_text(encoding="utf-8")

# Category-specific CC0 image handles.
handle_anchor = "static image_t xziel_icon_weapon;\n"
handles = r'''static image_t xziel_icon_weapon_pistol;
static image_t xziel_icon_weapon_revolver;
static image_t xziel_icon_weapon_shotgun;
static image_t xziel_icon_weapon_sniper;
static image_t xziel_icon_weapon_smg;
static image_t xziel_icon_weapon_assault;
static image_t xziel_icon_weapon_wonder;
static image_t xziel_icon_weapon_launcher;
'''
if "xziel_icon_weapon_revolver" not in text:
    if handle_anchor not in text:
        raise SystemExit("Could not find weapon icon handle anchor")
    text = text.replace(handle_anchor, handle_anchor + handles, 1)

load_anchor = '    xziel_icon_weapon  = Image_LoadImage("gfx/xziel/weapon", IMAGE_PNG, 0, true, false);\n'
loads = r'''    xziel_icon_weapon_pistol   = Image_LoadImage("gfx/xziel/weapon_pistol", IMAGE_PNG, 0, true, false);
    xziel_icon_weapon_revolver = Image_LoadImage("gfx/xziel/weapon_revolver", IMAGE_PNG, 0, true, false);
    xziel_icon_weapon_shotgun  = Image_LoadImage("gfx/xziel/weapon_shotgun", IMAGE_PNG, 0, true, false);
    xziel_icon_weapon_sniper   = Image_LoadImage("gfx/xziel/weapon_sniper", IMAGE_PNG, 0, true, false);
    xziel_icon_weapon_smg      = Image_LoadImage("gfx/xziel/weapon_smg", IMAGE_PNG, 0, true, false);
    xziel_icon_weapon_assault  = Image_LoadImage("gfx/xziel/weapon_assault", IMAGE_PNG, 0, true, false);
    xziel_icon_weapon_wonder   = Image_LoadImage("gfx/xziel/weapon_wonder", IMAGE_PNG, 0, true, false);
    xziel_icon_weapon_launcher = Image_LoadImage("gfx/xziel/weapon_launcher", IMAGE_PNG, 0, true, false);
'''
if 'gfx/xziel/weapon_revolver' not in text:
    if load_anchor not in text:
        raise SystemExit("Could not find weapon icon load anchor")
    text = text.replace(load_anchor, load_anchor + loads, 1)

# Insert classification helpers immediately before the final glyph renderer.
glyph_sig = "static void Xziel_DrawWeaponGlyph(int cx, int cy, int id, float scale, int alpha)"
helper = r'''
static qboolean Xziel_HUDIsRevolver(int id)
{
	return id == W_357 || id == W_KILLU;
}

static qboolean Xziel_HUDIsWonder(int id)
{
	switch (id) {
	case W_RAY:
	case W_PORTER:
	case W_RAYMK2:
	case W_PORTERMK2:
	case W_TESLA:
	case W_DG3:
		return true;
	default:
		return false;
	}
}

static qboolean Xziel_HUDIsLauncher(int id)
{
	return id == W_PANZER || id == W_LONGINUS;
}

static qboolean Xziel_HUDIsSMG(int id)
{
	switch (id) {
	case W_THOMPSON:
	case W_GIBS:
	case W_MP40:
	case W_AFTERBURNER:
	case W_PPSH:
	case W_REAPER:
	case W_MP5:
	case W_KOLLIDER:
		return true;
	default:
		return false;
	}
}

static qboolean Xziel_HUDIsLMG(int id)
{
	return id == W_BROWNING || id == W_ACCELERATOR ||
		id == W_MG || id == W_BARRACUDA;
}

static const char *Xziel_HUDWeaponClass(int id)
{
	if (id == 0) return "EMPTY";
	if (Xziel_HUDIsWonder(id)) return "WONDER";
	if (Xziel_HUDIsLauncher(id)) return "LAUNCHER";
	if (Xziel_HUDIsRevolver(id)) return "REVOLVER";
	if (Xziel_HUDIsPistol(id)) return "HANDGUN";
	if (Xziel_HUDIsShotgun(id)) return "SHOTGUN";
	if (Xziel_HUDIsSniper(id)) return "SNIPER";
	if (Xziel_HUDIsSMG(id)) return "SMG";
	if (Xziel_HUDIsLMG(id)) return "LMG";
	return "RIFLE";
}

static image_t Xziel_HUDWeaponImage(int id)
{
	if (Xziel_HUDIsWonder(id)) return xziel_icon_weapon_wonder;
	if (Xziel_HUDIsLauncher(id)) return xziel_icon_weapon_launcher;
	if (Xziel_HUDIsRevolver(id)) return xziel_icon_weapon_revolver;
	if (Xziel_HUDIsPistol(id)) return xziel_icon_weapon_pistol;
	if (Xziel_HUDIsShotgun(id)) return xziel_icon_weapon_shotgun;
	if (Xziel_HUDIsSniper(id)) return xziel_icon_weapon_sniper;
	if (Xziel_HUDIsSMG(id)) return xziel_icon_weapon_smg;
	/* LMGs deliberately use the long assault silhouette instead of falling
	   back to the old bullet glyph. */
	return xziel_icon_weapon_assault ? xziel_icon_weapon_assault : xziel_icon_weapon;
}

static void Xziel_DrawFitString(int x, int y, int max_width, const char *value,
	int r, int g, int b, int a, float base_scale)
{
	float scale = base_scale;
	int width;
	if (!value || !value[0] || max_width <= 0)
		return;
	width = getTextWidth((char *)value, scale);
	if (width > max_width && width > 0) {
		scale *= (float)max_width / (float)width;
		if (scale < vid.scale * 0.43f)
			scale = vid.scale * 0.43f;
	}
	Draw_ColoredString(x, y, (char *)value, r,g,b,a,scale);
}
'''
if "Xziel_HUDWeaponImage" not in text:
    idx = text.find(glyph_sig)
    if idx < 0:
        raise SystemExit("Could not find final weapon glyph renderer")
    text = text[:idx] + helper + "\n" + text[idx:]

glyph = r'''static void Xziel_DrawWeaponGlyph(int cx, int cy, int id, float scale, int alpha)
{
	image_t icon = Xziel_HUDWeaponImage(id);
	int h = (int)(20.0f * scale);
	int w;

	if (!icon)
		icon = xziel_icon_weapon;
	if (h < 14) h = 14;

	/* Gun art is intentionally rendered wide rather than stretched into the
	   square icon box that made v0.18 look toy-like. */
	if (Xziel_HUDIsPistol(id) || Xziel_HUDIsRevolver(id))
		w = (int)(h * 1.65f);
	else if (Xziel_HUDIsWonder(id) || Xziel_HUDIsLauncher(id))
		w = (int)(h * 1.35f);
	else
		w = (int)(h * 2.10f);

	Draw_ColoredStretchPic(cx - w/2, cy - h/2, icon, w, h,
		255,255,255,alpha);
}'''
text = replace_function(text, glyph_sig, glyph)

card = r'''static void Xziel_DrawWeaponCard(int cx, int cy, int w, int h,
	int weapon, int mag, int reserve, qboolean active, qboolean editor,
	float opacity, const char *slot_name)
{
	int x = cx - w/2;
	int y = cy - h/2;
	int line = (int)fmaxf(1.0f, 2.0f * vid.scale);
	int alpha;
	int accent_alpha;
	int text_alpha;
	int ammo_r = 244, ammo_g = 244, ammo_b = 244;
	int mag_w;
	float mag_scale;
	float reserve_scale;
	char mag_text[16];
	char reserve_text[24];
	const char *category = Xziel_HUDWeaponClass(weapon);
	const char *active_name = NULL;
	qboolean protected_pistol =
		xziel_mobile_unlimited_pistol.value >= 0.5f &&
		Xziel_HUDIsPistol(weapon);

	if (opacity < 0.15f) opacity = 0.15f;
	if (opacity > 1.0f) opacity = 1.0f;
	alpha = (int)((active ? 174 : 105) * xziel_mobile_hud_opacity.value * opacity);
	accent_alpha = (int)((active ? 245 : 145) * xziel_mobile_hud_opacity.value * opacity);
	text_alpha = (int)(235 * xziel_mobile_hud_opacity.value * opacity);

	/* Soft two-layer panel; no giant outline around every slot. */
	Draw_FillByColor(x, y, w, h, 4,6,8,alpha);
	Draw_FillByColor(x + line, y + line, w - line*2, h - line*2,
		14,17,20,(int)(alpha * 0.62f));

	/* Active uses the warm Zombies accent. Inactive is intentionally quiet. */
	Draw_FillByColor(x, y + h - line, w, line,
		active ? 248 : 142,
		active ? 197 : 148,
		active ? 45 : 154,
		accent_alpha);

	/* Slot chip. P is explicit only when the protected-pistol mode is active. */
	{
		const char *badge = slot_name;
		int chip = (int)(13 * vid.scale);
		if (chip < 11) chip = 11;
		Draw_FillByColor(x + line, y + line, chip, chip,
			active ? 245 : 45, active ? 196 : 48, active ? 36 : 52,
			(int)(200 * opacity));
		Xziel_DrawFitString(x + line + (int)(3*vid.scale),
			y + line + (int)(2*vid.scale), chip - (int)(4*vid.scale),
			badge, active ? 15 : 230, active ? 15 : 230, active ? 15 : 230,
			235, vid.scale * 0.56f);
	}

	/* Class label keeps the cards readable even if an asset is unfamiliar. */
	{
		int tw = getTextWidth((char *)category, vid.scale * 0.48f);
		Draw_ColoredString(x + w - tw - (int)(4*vid.scale),
			y + (int)(4*vid.scale), (char *)category,
			185,190,196,(int)(205*opacity),vid.scale*0.48f);
	}

	if (weapon != 0) {
		float icon_scale = h / (active ? 48.0f : 50.0f);
		Xziel_DrawWeaponGlyph(cx, cy - (int)(4*vid.scale), weapon,
			icon_scale, (int)((active ? 255 : 215) * opacity));

		if (active && sv_player) {
			active_name = PR_GetString(sv_player->v.Weapon_Name);
			if (active_name && active_name[0])
				Xziel_DrawFitString(x + (int)(4*vid.scale),
					y + h - (int)(19*vid.scale),
					w - (int)(8*vid.scale),
					active_name, 218,220,222,(int)(205*opacity),
					vid.scale*0.52f);
		}

		snprintf(mag_text, sizeof(mag_text), "%d", mag);
		if (protected_pistol)
			Q_strncpyz(reserve_text, "INF", sizeof(reserve_text));
		else
			snprintf(reserve_text, sizeof(reserve_text), "%d", reserve);

		if (mag <= 0) {
			ammo_r = 230; ammo_g = 60; ammo_b = 55;
		} else if (reserve <= 0 && !protected_pistol) {
			ammo_r = 244; ammo_g = 197; ammo_b = 45;
		}

		mag_scale = vid.scale * (active ? 0.76f : 0.66f);
		reserve_scale = vid.scale * (active ? 0.52f : 0.47f);
		mag_w = getTextWidth(mag_text, mag_scale);
		Draw_ColoredString(x + w - mag_w - (int)(21*vid.scale),
			y + h - (int)(10*vid.scale), mag_text,
			ammo_r,ammo_g,ammo_b,text_alpha,mag_scale);
		Draw_ColoredString(x + w - (int)(18*vid.scale),
			y + h - (int)(9*vid.scale), "/", 150,155,160,
			(int)(190*opacity),reserve_scale);
		Draw_ColoredString(x + w - (int)(12*vid.scale),
			y + h - (int)(9*vid.scale), reserve_text,
			210,214,218,text_alpha,reserve_scale);
	} else if (editor) {
		const char *empty = "EMPTY";
		int tw = getTextWidth((char *)empty, vid.scale * 0.58f);
		Draw_ColoredString(cx - tw/2, cy - (int)(3*vid.scale),
			(char *)empty, 150,155,160,(int)(190*opacity),vid.scale*0.58f);
	}
}'''
text = replace_function(text, "static void Xziel_DrawWeaponCard(", card)

strip = r'''static void Xziel_DrawWeaponStrip(qboolean editor)
{
	static int last_active_weapon = -1;
	static double switch_anim_until;
	double now = Sys_FloatTime();
	float pulse = 1.0f;
	struct carddef {
		float x,y,s,o;
		int weapon,mag,reserve;
		const char *badge;
		qboolean active;
	} c[3];

	if (cl.stats[STAT_ACTIVEWEAPON] != last_active_weapon) {
		last_active_weapon = cl.stats[STAT_ACTIVEWEAPON];
		switch_anim_until = now + 0.18;
	}
	if (switch_anim_until > now) {
		float t = (float)((switch_anim_until - now) / 0.18);
		pulse = 1.0f + 0.075f * t;
	}

	c[0].x=xziel_hud_weapon1_x.value; c[0].y=xziel_hud_weapon1_y.value;
	c[0].s=xziel_hud_weapon1_scale.value * pulse; c[0].o=xziel_hud_weapon1_opacity.value;
	c[0].weapon=cl.stats[STAT_ACTIVEWEAPON]; c[0].mag=cl.stats[STAT_CURRENTMAG];
	c[0].reserve=cl.stats[STAT_AMMO]; c[0].badge="1"; c[0].active=true;

	c[1].x=xziel_hud_weapon2_x.value; c[1].y=xziel_hud_weapon2_y.value;
	c[1].s=xziel_hud_weapon2_scale.value; c[1].o=xziel_hud_weapon2_opacity.value;
	c[1].weapon=cl.stats[STAT_XZIEL_W2]; c[1].mag=cl.stats[STAT_XZIEL_W2MAG];
	c[1].reserve=cl.stats[STAT_XZIEL_W2RES]; c[1].badge="2"; c[1].active=false;

	c[2].x=xziel_hud_pistol_x.value; c[2].y=xziel_hud_pistol_y.value;
	c[2].s=xziel_hud_pistol_scale.value; c[2].o=xziel_hud_pistol_opacity.value;
	c[2].weapon=cl.stats[STAT_XZIEL_W3]; c[2].mag=cl.stats[STAT_XZIEL_W3MAG];
	c[2].reserve=cl.stats[STAT_XZIEL_W3RES];
	c[2].badge=xziel_mobile_unlimited_pistol.value >= 0.5f ? "P" : "3";
	c[2].active=false;

	for (int i=0; i<3; ++i) {
		int w = (int)((i==0 ? 108 : 84) * vid.scale * c[i].s);
		int h = (int)((i==0 ? 60 : 50) * vid.scale * c[i].s);
		if (!editor && c[i].weapon == 0)
			continue;
		Xziel_DrawWeaponCard((int)(c[i].x*vid.width),
			(int)(c[i].y*vid.height), w,h,
			c[i].weapon,c[i].mag,c[i].reserve,
			c[i].active,editor,c[i].o,c[i].badge);
	}
}'''
text = replace_function(text, "static void Xziel_DrawWeaponStrip(qboolean editor)", strip)

hud.write_text(text, encoding="utf-8")

# Custom HUD makes the special third-slot rule explicit when enabled.
controls = source / "menu" / "menu_controls.c"
ctext = controls.read_text(encoding="utf-8")
ctext = ctext.replace(
	'case 14: name="WEAPON 3"; break;',
	'case 14: name=xziel_mobile_unlimited_pistol.value >= 0.5f ? "PISTOL SLOT" : "WEAPON 3"; break;',
	1
)
controls.write_text(ctext, encoding="utf-8")

print("Xziel v0.20 professional weapon HUD applied.")
