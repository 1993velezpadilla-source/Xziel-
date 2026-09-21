#!/usr/bin/env python3
"""Xziel v0.24 approved HUD pass.

Applies the approved mockup to the real Vril HUD:
- clearer jump/slide/action pictograms from v0.24 generated assets;
- premium smoked-glass weapon cards with yellow active accent;
- larger dedicated per-weapon silhouettes;
- no generic weapon-category art when a physical weapon is known.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_vril_mobile_v024.py <vril-root>")

root = Path(sys.argv[1])
hud = root / "source" / "render" / "r_hud.c"


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


text = hud.read_text(encoding="utf-8")

handle_anchor = "static image_t xziel_touch_editor;\n"
if "static image_t xziel_weapon_card_active;" not in text:
    if handle_anchor not in text:
        raise SystemExit("v0.24 card handle anchor missing")
    text = text.replace(
        handle_anchor,
        handle_anchor +
        "static image_t xziel_weapon_card_active;\n"
        "static image_t xziel_weapon_card_inactive;\n",
        1,
    )

load_anchor = '    xziel_touch_editor = Image_LoadImage("gfx/xziel/touch_editor", IMAGE_PNG, 0, true, false);\n'
if 'gfx/xziel/weapon_card_active' not in text:
    if load_anchor not in text:
        raise SystemExit("v0.24 card load anchor missing")
    text = text.replace(
        load_anchor,
        load_anchor +
        '    xziel_weapon_card_active = Image_LoadImage("gfx/xziel/weapon_card_active", IMAGE_PNG, 0, true, false);\n'
        '    xziel_weapon_card_inactive = Image_LoadImage("gfx/xziel/weapon_card_inactive", IMAGE_PNG, 0, true, false);\n',
        1,
    )

action_glyph = r'''static qboolean Xziel_DrawActionGlyph(int cx, int cy, int radius,
	const char *label1, const char *label2, qboolean pressed)
{
	image_t icon = Xziel_ActionIcon(label1, label2);
	float factor = 1.00f;
	int size;
	int alpha;

	if (!icon)
		return false;

	if (!strcmp(label1, "FIRE"))
		factor = 1.23f;
	else if (!strcmp(label1, "ADS") && label2 && !strcmp(label2, "FIRE"))
		factor = 1.23f;
	else if (!strcmp(label1, "ADS"))
		factor = 1.08f;
	else if (!strcmp(label1, "RLD"))
		factor = 1.06f;
	else if (!strcmp(label1, "JUMP"))
		factor = 1.13f;
	else if (!strcmp(label1, "SLIDE"))
		factor = 1.15f;
	else if (!strcmp(label1, "USE"))
		factor = 1.08f;
	else if (!strcmp(label1, "KNIFE"))
		factor = 1.08f;
	else if (!strcmp(label1, "NADE"))
		factor = 1.07f;

	size = (int)(radius * factor);
	if (size < 15)
		size = 15;

	alpha = pressed ? 255 : 248;
	Draw_ColoredStretchPic(cx - size/2, cy - size/2, icon,
		size, size, 255,255,255,alpha);
	return true;
}'''
sig = "static qboolean Xziel_DrawActionGlyph("
pos = text.rfind(sig)
if pos < 0:
    raise SystemExit("v0.24 final action glyph missing")
text = text[:pos] + replace_function(text[pos:], sig, action_glyph)

weapon_card = r'''static void Xziel_DrawWeaponCard(int cx, int cy, int w, int h,
	int weapon, int mag, int reserve, qboolean active, qboolean editor,
	float opacity, const char *slot_name)
{
	int x = cx - w/2;
	int y = cy - h/2;
	int chip;
	int chip_pad;
	int ammo_w;
	float ammo_scale;
	float name_scale;
	char ammo[32];
	const char *active_name = NULL;
	image_t frame = active ? xziel_weapon_card_active : xziel_weapon_card_inactive;
	qboolean protected_pistol =
		xziel_mobile_unlimited_pistol.value >= 0.5f &&
		Xziel_HUDIsPistol(weapon);

	if (opacity < 0.15f) opacity = 0.15f;
	if (opacity > 1.0f) opacity = 1.0f;

	if (frame) {
		Draw_ColoredStretchPic(x, y, frame, w, h,
			255,255,255,(int)(255 * xziel_mobile_hud_opacity.value * opacity));
	} else {
		Draw_FillByColor(x, y, w, h, 5,7,9,
			(int)((active ? 175 : 105) * xziel_mobile_hud_opacity.value * opacity));
		if (active)
			Draw_FillByColor(x, y+h-(int)fmaxf(1.0f,2.0f*vid.scale), w,
				(int)fmaxf(1.0f,2.0f*vid.scale), 244,199,43,(int)(235*opacity));
	}

	chip = (int)((active ? 15 : 12) * vid.scale);
	if (chip < 12) chip = 12;
	chip_pad = (int)(3 * vid.scale);
	Draw_FillByColor(x + chip_pad, y + chip_pad, chip, chip,
		active ? 244 : 55,
		active ? 199 : 59,
		active ? 43 : 64,
		(int)((active ? 245 : 175) * opacity));
	Xziel_DrawFitString(x + chip_pad + (int)(4*vid.scale),
		y + chip_pad + (int)(3*vid.scale),
		chip - (int)(6*vid.scale),
		slot_name,
		active ? 12 : 235, active ? 12 : 235, active ? 12 : 235,
		245, vid.scale * (active ? 0.62f : 0.53f));

	if (weapon != 0) {
		float icon_scale = h / (active ? 32.5f : 31.0f);
		int icon_y = cy - (int)((active ? 4 : 2) * vid.scale);

		/* The runtime selector resolves a physical weapon to its dedicated
		   silhouette image. PaP variants intentionally share only with their
		   own base gun because the physical gun body is the same. */
		Xziel_DrawWeaponGlyph(cx, icon_y, weapon, icon_scale,
			(int)((active ? 255 : 225) * opacity));

		if (protected_pistol)
			snprintf(ammo, sizeof(ammo), "%d / INF", mag);
		else
			snprintf(ammo, sizeof(ammo), "%d / %d", mag, reserve);

		ammo_scale = vid.scale * (active ? 0.70f : 0.55f);
		name_scale = vid.scale * (active ? 0.55f : 0.47f);
		ammo_w = getTextWidth(ammo, ammo_scale);

		Draw_ColoredString(x + w - ammo_w - (int)(5*vid.scale),
			y + h - (int)(12*vid.scale), ammo,
			mag <= 0 ? 238 : 246,
			mag <= 0 ? 69 : 246,
			mag <= 0 ? 58 : 246,
			(int)(245*opacity), ammo_scale);

		if (active && sv_player) {
			active_name = PR_GetString(sv_player->v.Weapon_Name);
			if (active_name && active_name[0])
				Xziel_DrawFitString(
					x + (int)(5*vid.scale),
					y + h - (int)(12*vid.scale),
					w - ammo_w - (int)(18*vid.scale),
					active_name,
					220,224,228,(int)(226*opacity),name_scale);
		}
	} else if (editor) {
		const char *empty = "EMPTY";
		int tw = getTextWidth((char *)empty, vid.scale * 0.53f);
		Draw_ColoredString(cx - tw/2, cy - (int)(2*vid.scale),
			(char *)empty, 155,160,166,(int)(185*opacity),vid.scale*0.53f);
	}
}'''
text = replace_function(text, "static void Xziel_DrawWeaponCard(", weapon_card)

weapon_strip = r'''static void Xziel_DrawWeaponStrip(qboolean editor)
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
		switch_anim_until = now + 0.16;
	}
	if (switch_anim_until > now) {
		float t = (float)((switch_anim_until - now) / 0.16);
		pulse = 1.0f + 0.05f * t;
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
		int w = (int)((i==0 ? 112 : 76) * vid.scale * c[i].s);
		int h = (int)((i==0 ? 58 : 42) * vid.scale * c[i].s);
		if (!editor && c[i].weapon == 0)
			continue;
		Xziel_DrawWeaponCard((int)(c[i].x*vid.width),
			(int)(c[i].y*vid.height), w,h,
			c[i].weapon,c[i].mag,c[i].reserve,
			c[i].active,editor,c[i].o,c[i].badge);
	}
}'''
text = replace_function(text, "static void Xziel_DrawWeaponStrip(qboolean editor)", weapon_strip)

hud.write_text(text, encoding="utf-8")
print("Applied Xziel v0.24 approved HUD layout and dedicated-weapon card styling.")
