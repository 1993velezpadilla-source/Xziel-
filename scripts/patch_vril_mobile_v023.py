#!/usr/bin/env python3
"""Xziel v0.23 HUD visual pass.

Final authority after v0.22:
- mobile-FPS/CODM-inspired icon hierarchy using Xziel-original vector art;
- ADS+FIRE uses the bullet-over-reticle icon requested by the project;
- quieter, thinner touch surfaces without the old compass-like rings;
- compact weapon cards with a large weapon silhouette and minimal chrome.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_vril_mobile_v023.py <vril-root>")

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

action_icon = r'''static image_t Xziel_ActionIcon(const char *label1, const char *label2)
{
	/* ADS+FIRE deliberately uses the bullet-over-reticle art. Test this
	   before the generic ADS branch or it would resolve to plain reticle. */
	if (!strcmp(label1, "ADS") && label2 && !strcmp(label2, "FIRE"))
		return xziel_icon_fire;
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
text = replace_function(text, "static image_t Xziel_ActionIcon(", action_icon)

action_glyph = r'''static qboolean Xziel_DrawActionGlyph(int cx, int cy, int radius,
	const char *label1, const char *label2, qboolean pressed)
{
	image_t icon = Xziel_ActionIcon(label1, label2);
	float factor = 0.96f;
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
		factor = 1.03f;

	size = (int)(radius * factor);
	if (size < 14)
		size = 14;

	alpha = pressed ? 255 : 246;
	Draw_ColoredStretchPic(cx - size/2, cy - size/2, icon,
		size, size, 255,255,255,alpha);
	return true;
}'''
action_sig = "static qboolean Xziel_DrawActionGlyph("
action_pos = text.rfind(action_sig)
if action_pos < 0:
    raise SystemExit("Could not find final Xziel_DrawActionGlyph implementation")
text = text[:action_pos] + replace_function(
    text[action_pos:], action_sig, action_glyph
)

touch_button = r'''static void Xziel_DrawTouchButton(float nx, float ny, float radius_h,
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

	/* Primary fire stays easy to acquire by thumb, but the visible ring is
	   intentionally thinner and less busy than the v0.22 surface. */
	size = (int)(radius * 2.04f);
	if (!strcmp(label1, "FIRE"))
		size = (int)(radius * 2.10f);

	surface = editor ? xziel_touch_editor :
		(pressed ? xziel_touch_pressed : xziel_touch_idle);
	alpha = (int)(238 * xziel_mobile_hud_opacity.value * local_opacity);

	if (surface)
		Draw_ColoredStretchPic(cx - size/2, cy - size/2, surface,
			size,size,255,255,255,alpha);

	Xziel_DrawActionGlyph(cx,cy,radius,label1,label2,pressed);
}'''
text = replace_function(text, "static void Xziel_DrawTouchButton(", touch_button)

weapon_card = r'''static void Xziel_DrawWeaponCard(int cx, int cy, int w, int h,
	int weapon, int mag, int reserve, qboolean active, qboolean editor,
	float opacity, const char *slot_name)
{
	int x = cx - w/2;
	int y = cy - h/2;
	int line = (int)fmaxf(1.0f, 1.35f * vid.scale);
	int panel_alpha;
	int accent_alpha;
	int icon_alpha;
	int chip;
	int ammo_w;
	char ammo[32];
	const char *active_name = NULL;
	qboolean protected_pistol =
		xziel_mobile_unlimited_pistol.value >= 0.5f &&
		Xziel_HUDIsPistol(weapon);

	if (opacity < 0.15f) opacity = 0.15f;
	if (opacity > 1.0f) opacity = 1.0f;

	panel_alpha = (int)((active ? 118 : 70) *
		xziel_mobile_hud_opacity.value * opacity);
	accent_alpha = (int)((active ? 238 : 105) *
		xziel_mobile_hud_opacity.value * opacity);
	icon_alpha = (int)((active ? 255 : 205) *
		xziel_mobile_hud_opacity.value * opacity);

	/* Compact smoked-glass card. No class label and no heavy rectangular
	   border: the weapon silhouette is the visual focus. */
	Draw_FillByColor(x, y, w, h, 5,7,9,panel_alpha);
	Draw_FillByColor(x + line, y + line, w - line*2, h - line*2,
		15,18,21,(int)(panel_alpha * 0.38f));

	if (active)
		Draw_FillByColor(x, y + h - line, w, line,
			246,199,43,accent_alpha);

	chip = (int)((active ? 12 : 10) * vid.scale);
	if (chip < 10) chip = 10;
	Draw_FillByColor(x + line, y + line, chip, chip,
		active ? 244 : 45,
		active ? 198 : 49,
		active ? 42 : 54,
		(int)((active ? 220 : 145) * opacity));
	Xziel_DrawFitString(x + line + (int)(3*vid.scale),
		y + line + (int)(2*vid.scale), chip - (int)(4*vid.scale),
		slot_name,
		active ? 15 : 225, active ? 15 : 225, active ? 15 : 225,
		238, vid.scale * (active ? 0.56f : 0.50f));

	if (weapon != 0) {
		float icon_scale = h / (active ? 39.0f : 37.0f);
		int icon_y = cy - (int)((active ? 4 : 1) * vid.scale);
		Xziel_DrawWeaponGlyph(cx, icon_y, weapon, icon_scale, icon_alpha);

		if (protected_pistol)
			snprintf(ammo, sizeof(ammo), "%d / INF", mag);
		else
			snprintf(ammo, sizeof(ammo), "%d / %d", mag, reserve);

		ammo_w = getTextWidth(ammo, vid.scale * (active ? 0.61f : 0.50f));
		Draw_ColoredString(x + w - ammo_w - (int)(4*vid.scale),
			y + h - (int)(9*vid.scale), ammo,
			mag <= 0 ? 236 : 238,
			mag <= 0 ? 66 : 240,
			mag <= 0 ? 58 : 242,
			(int)(232*opacity),
			vid.scale * (active ? 0.61f : 0.50f));

		/* Only the active slot gets a name, and it is kept small so the
		   bottom-center HUD reads as a weapon selector rather than a panel. */
		if (active && sv_player) {
			active_name = PR_GetString(sv_player->v.Weapon_Name);
			if (active_name && active_name[0])
				Xziel_DrawFitString(x + (int)(4*vid.scale),
					y + h - (int)(9*vid.scale),
					w - ammo_w - (int)(13*vid.scale),
					active_name, 202,206,210,(int)(195*opacity),
					vid.scale*0.47f);
		}
	} else if (editor) {
		const char *empty = "EMPTY";
		int tw = getTextWidth((char *)empty, vid.scale * 0.50f);
		Draw_ColoredString(cx - tw/2, cy - (int)(2*vid.scale),
			(char *)empty, 150,155,160,(int)(180*opacity),vid.scale*0.50f);
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
		switch_anim_until = now + 0.14;
	}
	if (switch_anim_until > now) {
		float t = (float)((switch_anim_until - now) / 0.14);
		pulse = 1.0f + 0.045f * t;
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
		int w = (int)((i==0 ? 92 : 68) * vid.scale * c[i].s);
		int h = (int)((i==0 ? 46 : 38) * vid.scale * c[i].s);
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
print("Applied Xziel v0.23 mobile-FPS HUD and compact weapon cards.")
