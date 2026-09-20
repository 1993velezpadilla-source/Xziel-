#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_vril_weaponhud.py <vril-root>")

root = Path(sys.argv[1])
source = root / "source"

def replace_c_function(text, signature, replacement):
    start = text.find(signature)
    if start < 0:
        raise SystemExit(f"Could not find C function: {signature}")
    brace = text.find("{", start)
    if brace < 0:
        raise SystemExit(f"Could not find body: {signature}")
    depth = 0
    end = -1
    for i in range(brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end < 0:
        raise SystemExit(f"Unterminated C function: {signature}")
    return text[:start] + replacement + text[end:]

# ---------------------------------------------------------------------------
# Persistent Android settings / HUD placement
# ---------------------------------------------------------------------------
inp = source / "input.c"
text = inp.read_text(encoding="utf-8")

cvar_anchor = 'cvar_t xziel_mobile_hud_opacity = {"xziel_mobile_hud_opacity", "0.72", true};\n'
cvars = '''cvar_t xziel_mobile_unlimited_pistol = {"xziel_mobile_unlimited_pistol", "0", true};
cvar_t xziel_hud_weapons_x = {"xziel_hud_weapons_x", "0.50", true};
cvar_t xziel_hud_weapons_y = {"xziel_hud_weapons_y", "0.885", true};
cvar_t xziel_hud_weapons_scale = {"xziel_hud_weapons_scale", "1.0", true};
'''
if "xziel_mobile_unlimited_pistol" not in text:
    if cvar_anchor not in text:
        raise SystemExit("Could not find mobile HUD opacity cvar")
    text = text.replace(cvar_anchor, cvar_anchor + cvars, 1)

reg_anchor = "\tCvar_RegisterVariable(&xziel_mobile_hud_opacity);\n"
regs = """\tCvar_RegisterVariable(&xziel_mobile_unlimited_pistol);
\tCvar_RegisterVariable(&xziel_hud_weapons_x);
\tCvar_RegisterVariable(&xziel_hud_weapons_y);
\tCvar_RegisterVariable(&xziel_hud_weapons_scale);
"""
if "Cvar_RegisterVariable(&xziel_mobile_unlimited_pistol);" not in text:
    if reg_anchor not in text:
        raise SystemExit("Could not find mobile HUD opacity registration")
    text = text.replace(reg_anchor, reg_anchor + regs, 1)

inp.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# Reuse the standard stat-update service so the base clientdata packet remains
# protocol-compatible. Stats 25..30 were unused in current Vril.
# ---------------------------------------------------------------------------
defs = source / "nzportable_def.h"
text = defs.read_text(encoding="utf-8")
stat_anchor = "#define STAT_GUNGAME_SCOREGOAL\t24\n"
stat_defs = """#define STAT_XZIEL_W2            25
#define STAT_XZIEL_W2MAG         26
#define STAT_XZIEL_W2RES         27
#define STAT_XZIEL_W3            28
#define STAT_XZIEL_W3MAG         29
#define STAT_XZIEL_W3RES         30
"""
if "STAT_XZIEL_W2" not in text:
    if stat_anchor not in text:
        raise SystemExit("Could not find stat extension anchor")
    text = text.replace(stat_anchor, stat_anchor + stat_defs, 1)
defs.write_text(text, encoding="utf-8")

sv = source / "sv_main.c"
text = sv.read_text(encoding="utf-8")
write_anchor = """\tMSG_WriteByte (msg, ent->v.gungame_weapon_idx);
\tMSG_WriteShort (msg, ent->v.gungame_score_threshold);
"""
extra_stats = """\tMSG_WriteByte (msg, ent->v.gungame_weapon_idx);
\tMSG_WriteShort (msg, ent->v.gungame_score_threshold);

#ifdef __ANDROID__
\t/* Optional Xziel weapon-HUD stats. svc_updatestat keeps the legacy
\t   svc_clientdata payload unchanged for protocol compatibility. */
\tMSG_WriteByte(msg, svc_updatestat);
\tMSG_WriteByte(msg, STAT_XZIEL_W2);
\tMSG_WriteLong(msg, (int)PR_GetEdictFloat(ent, "xziel_weapon2_id"));
\tMSG_WriteByte(msg, svc_updatestat);
\tMSG_WriteByte(msg, STAT_XZIEL_W2MAG);
\tMSG_WriteLong(msg, (int)PR_GetEdictFloat(ent, "xziel_weapon2_mag"));
\tMSG_WriteByte(msg, svc_updatestat);
\tMSG_WriteByte(msg, STAT_XZIEL_W2RES);
\tMSG_WriteLong(msg, (int)PR_GetEdictFloat(ent, "xziel_weapon2_reserve"));
\tMSG_WriteByte(msg, svc_updatestat);
\tMSG_WriteByte(msg, STAT_XZIEL_W3);
\tMSG_WriteLong(msg, (int)PR_GetEdictFloat(ent, "xziel_weapon3_id"));
\tMSG_WriteByte(msg, svc_updatestat);
\tMSG_WriteByte(msg, STAT_XZIEL_W3MAG);
\tMSG_WriteLong(msg, (int)PR_GetEdictFloat(ent, "xziel_weapon3_mag"));
\tMSG_WriteByte(msg, svc_updatestat);
\tMSG_WriteByte(msg, STAT_XZIEL_W3RES);
\tMSG_WriteLong(msg, (int)PR_GetEdictFloat(ent, "xziel_weapon3_reserve"));
#endif
"""
if "STAT_XZIEL_W2MAG" not in text:
    if write_anchor not in text:
        raise SystemExit("Could not find SV clientdata tail")
    text = text.replace(write_anchor, extra_stats, 1)
sv.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# Touch selection + Custom HUD dragging
# ---------------------------------------------------------------------------
sdl = source / "platform" / "sdl" / "sys_sdl.c"
text = sdl.read_text(encoding="utf-8")

extern_anchor = "extern cvar_t xziel_hud_grenade_y;\n"
externs = """extern cvar_t xziel_mobile_unlimited_pistol;
extern cvar_t xziel_hud_weapons_x;
extern cvar_t xziel_hud_weapons_y;
extern cvar_t xziel_hud_weapons_scale;
"""
if "extern cvar_t xziel_hud_weapons_x;" not in text:
    if extern_anchor not in text:
        raise SystemExit("Could not find Android HUD extern anchor")
    text = text.replace(extern_anchor, extern_anchor + externs, 1)

enum_start = text.find("typedef enum {", text.find("#ifdef __ANDROID__"))
enum_end = text.find("} xziel_touch_role_t;", enum_start)
if enum_start < 0 or enum_end < 0:
    raise SystemExit("Could not find Android touch enum")
enum_text = text[enum_start:enum_end]
if "XZ_TOUCH_WEAPON2" not in enum_text:
    insertion = "\tXZ_TOUCH_WEAPON2,\n\tXZ_TOUCH_WEAPON3,\n\tXZ_TOUCH_WEAPONSTRIP,\n"
    # Insert before enum close; ensure the previous enumerator has a comma.
    prefix = text[:enum_end]
    stripped = prefix.rstrip()
    if not stripped.endswith(","):
        stripped += ","
    text = stripped + "\n" + insertion + text[enum_end:]

weapon_hit_helpers = r'''
static qboolean Xziel_PointInRect(float x, float y, float cx, float cy, float w, float h)
{
    return x >= cx - w * 0.5f && x <= cx + w * 0.5f &&
        y >= cy - h * 0.5f && y <= cy + h * 0.5f;
}

static qboolean Xziel_WeaponStripHit(float x, float y, int slot)
{
    float s = xziel_hud_weapons_scale.value;
    float bx = xziel_hud_weapons_x.value;
    float by = xziel_hud_weapons_y.value;

    if (s < 0.65f) s = 0.65f;
    if (s > 1.45f) s = 1.45f;

    if (slot == 0)
        return Xziel_PointInRect(x, y, bx - 0.115f * s, by,
            0.150f * s, 0.100f * s);
    if (slot == 1)
        return Xziel_PointInRect(x, y, bx + 0.025f * s, by,
            0.110f * s, 0.080f * s);
    return Xziel_PointInRect(x, y, bx + 0.145f * s, by,
        0.110f * s, 0.080f * s);
}

static qboolean Xziel_WeaponStripGroupHit(float x, float y)
{
    float s = xziel_hud_weapons_scale.value;
    float bx = xziel_hud_weapons_x.value;
    float by = xziel_hud_weapons_y.value;
    if (s < 0.65f) s = 0.65f;
    if (s > 1.45f) s = 1.45f;
    return Xziel_PointInRect(x, y, bx + 0.015f * s, by,
        0.390f * s, 0.120f * s);
}
'''
if "static qboolean Xziel_WeaponStripHit" not in text:
    anchor = "static xziel_touch_role_t Xziel_RoleForPoint(float x, float y)\n"
    idx = text.find(anchor)
    if idx < 0:
        raise SystemExit("Could not find touch role function for weapon helpers")
    text = text[:idx] + weapon_hit_helpers + "\n" + text[idx:]

role_func = r'''static xziel_touch_role_t Xziel_RoleForPoint(float x, float y)
{
    float hs = xziel_mobile_hud_scale.value;

    /* The weapon cards replace the old SWAP button. Slot 0 is already active;
       tapping the other cards selects them directly. */
    if (cl.stats[STAT_XZIEL_W2] != 0 && Xziel_WeaponStripHit(x, y, 1))
        return XZ_TOUCH_WEAPON2;
    if (cl.stats[STAT_XZIEL_W3] != 0 && Xziel_WeaponStripHit(x, y, 2))
        return XZ_TOUCH_WEAPON3;

    if (Xziel_IsInside(x, y, xziel_hud_fire_x.value, xziel_hud_fire_y.value, 0.073f * hs)) return XZ_TOUCH_FIRE;
    if (Xziel_IsInside(x, y, xziel_hud_adsfire_x.value, xziel_hud_adsfire_y.value, 0.056f * hs)) return XZ_TOUCH_ADSFIRE;
    if (Xziel_IsInside(x, y, xziel_hud_ads_x.value, xziel_hud_ads_y.value, 0.047f * hs)) return XZ_TOUCH_ADS;
    if (Xziel_IsInside(x, y, xziel_hud_reload_x.value, xziel_hud_reload_y.value, 0.044f * hs)) return XZ_TOUCH_RELOAD;
    if (xziel_mobile_use_available && Xziel_IsInside(x, y, xziel_hud_use_x.value, xziel_hud_use_y.value, 0.050f * hs)) return XZ_TOUCH_USE;
    if (Xziel_IsInside(x, y, xziel_hud_pause_x.value, xziel_hud_pause_y.value, 0.036f * hs)) return XZ_TOUCH_PAUSE;
    if (Xziel_IsInside(x, y, xziel_hud_grenade_x.value, xziel_hud_grenade_y.value, 0.041f * hs)) return XZ_TOUCH_GRENADE;
    if (Xziel_IsInside(x, y, xziel_hud_jump_x.value, xziel_hud_jump_y.value, 0.044f * hs)) return XZ_TOUCH_JUMP;
    if ((!xziel_mobile_knife_range_only.value || xziel_mobile_knife_target_near) &&
        Xziel_IsInside(x, y, xziel_hud_knife_x.value, xziel_hud_knife_y.value, 0.044f * hs))
        return XZ_TOUCH_KNIFE;
    if (x < 0.45f && y > 0.30f) return XZ_TOUCH_MOVE;
    return XZ_TOUCH_LOOK;
}'''
text = replace_c_function(
    text,
    "static xziel_touch_role_t Xziel_RoleForPoint(float x, float y)",
    role_func
)

editor_role = r'''static xziel_touch_role_t Xziel_HudEditorRole(float x, float y)
{
    float hs = xziel_mobile_hud_scale.value;
    if (Xziel_WeaponStripGroupHit(x, y)) return XZ_TOUCH_WEAPONSTRIP;
    if (Xziel_IsInside(x, y, xziel_hud_fire_x.value, xziel_hud_fire_y.value, 0.090f * hs)) return XZ_TOUCH_FIRE;
    if (Xziel_IsInside(x, y, xziel_hud_adsfire_x.value, xziel_hud_adsfire_y.value, 0.075f * hs)) return XZ_TOUCH_ADSFIRE;
    if (Xziel_IsInside(x, y, xziel_hud_ads_x.value, xziel_hud_ads_y.value, 0.065f * hs)) return XZ_TOUCH_ADS;
    if (Xziel_IsInside(x, y, xziel_hud_reload_x.value, xziel_hud_reload_y.value, 0.060f * hs)) return XZ_TOUCH_RELOAD;
    if (Xziel_IsInside(x, y, xziel_hud_use_x.value, xziel_hud_use_y.value, 0.065f * hs)) return XZ_TOUCH_USE;
    if (Xziel_IsInside(x, y, xziel_hud_pause_x.value, xziel_hud_pause_y.value, 0.055f * hs)) return XZ_TOUCH_PAUSE;
    if (Xziel_IsInside(x, y, xziel_hud_grenade_x.value, xziel_hud_grenade_y.value, 0.057f * hs)) return XZ_TOUCH_GRENADE;
    if (Xziel_IsInside(x, y, xziel_hud_jump_x.value, xziel_hud_jump_y.value, 0.060f * hs)) return XZ_TOUCH_JUMP;
    if (Xziel_IsInside(x, y, xziel_hud_knife_x.value, xziel_hud_knife_y.value, 0.060f * hs)) return XZ_TOUCH_KNIFE;
    if (Xziel_IsInside(x, y, xziel_hud_joy_x.value, xziel_hud_joy_y.value, 0.120f * hs)) return XZ_TOUCH_MOVE;
    return XZ_TOUCH_NONE;
}'''
text = replace_c_function(
    text,
    "static xziel_touch_role_t Xziel_HudEditorRole(float x, float y)",
    editor_role
)

editor_set = r'''static void Xziel_HudEditorSetPosition(xziel_touch_role_t role, float x, float y)
{
    if (x < 0.035f) x = 0.035f;
    if (x > 0.965f) x = 0.965f;
    if (y < 0.055f) y = 0.055f;
    if (y > 0.945f) y = 0.945f;

    switch (role) {
    case XZ_TOUCH_MOVE:
        Cvar_SetValue("xziel_hud_joy_x", x); Cvar_SetValue("xziel_hud_joy_y", y); break;
    case XZ_TOUCH_FIRE:
        Cvar_SetValue("xziel_hud_fire_x", x); Cvar_SetValue("xziel_hud_fire_y", y); break;
    case XZ_TOUCH_ADSFIRE:
        Cvar_SetValue("xziel_hud_adsfire_x", x); Cvar_SetValue("xziel_hud_adsfire_y", y); break;
    case XZ_TOUCH_ADS:
        Cvar_SetValue("xziel_hud_ads_x", x); Cvar_SetValue("xziel_hud_ads_y", y); break;
    case XZ_TOUCH_RELOAD:
        Cvar_SetValue("xziel_hud_reload_x", x); Cvar_SetValue("xziel_hud_reload_y", y); break;
    case XZ_TOUCH_USE:
        Cvar_SetValue("xziel_hud_use_x", x); Cvar_SetValue("xziel_hud_use_y", y); break;
    case XZ_TOUCH_JUMP:
        Cvar_SetValue("xziel_hud_jump_x", x); Cvar_SetValue("xziel_hud_jump_y", y); break;
    case XZ_TOUCH_KNIFE:
        Cvar_SetValue("xziel_hud_knife_x", x); Cvar_SetValue("xziel_hud_knife_y", y); break;
    case XZ_TOUCH_GRENADE:
        Cvar_SetValue("xziel_hud_grenade_x", x); Cvar_SetValue("xziel_hud_grenade_y", y); break;
    case XZ_TOUCH_PAUSE:
        Cvar_SetValue("xziel_hud_pause_x", x); Cvar_SetValue("xziel_hud_pause_y", y); break;
    case XZ_TOUCH_WEAPONSTRIP:
        Cvar_SetValue("xziel_hud_weapons_x", x);
        Cvar_SetValue("xziel_hud_weapons_y", y);
        break;
    default:
        break;
    }
}'''
text = replace_c_function(
    text,
    "static void Xziel_HudEditorSetPosition(xziel_touch_role_t role, float x, float y)",
    editor_set
)

# Direct weapon card actions: clear ADS cleanly, then ask authoritative QC to
# rotate the requested native inventory slot into slot zero.
needle = "\tcase XZ_TOUCH_SWITCH:\n"
weapon_cases = """\tcase XZ_TOUCH_WEAPON2:
\t\tXziel_ForceExitAdsForSprint();
\t\tCbuf_AddText("impulse 60\\n");
\t\tCbuf_Execute();
\t\tbreak;

\tcase XZ_TOUCH_WEAPON3:
\t\tXziel_ForceExitAdsForSprint();
\t\tCbuf_AddText("impulse 61\\n");
\t\tCbuf_Execute();
\t\tbreak;

\tcase XZ_TOUCH_WEAPONSTRIP:
\t\tbreak;

"""
action_start = text.find("static void Xziel_ActionDown(xziel_touch_role_t role)")
action_end = text.find("static void Xziel_ActionUp(xziel_touch_role_t role)", action_start)
if action_start < 0 or action_end < 0:
    raise SystemExit("Could not locate mobile action functions")
action_chunk = text[action_start:action_end]
if "case XZ_TOUCH_WEAPON2:" not in action_chunk:
    if needle not in action_chunk:
        raise SystemExit("Could not find switch case in ActionDown")
    action_chunk = action_chunk.replace(needle, weapon_cases + needle, 1)
    text = text[:action_start] + action_chunk + text[action_end:]

action_start = text.find("static void Xziel_ActionUp(xziel_touch_role_t role)")
action_end = text.find("static xziel_touch_slot_t *Xziel_FindTouch", action_start)
if action_start < 0 or action_end < 0:
    raise SystemExit("Could not locate ActionUp tail")
action_chunk = text[action_start:action_end]
if "case XZ_TOUCH_WEAPON2:" not in action_chunk:
    if needle not in action_chunk:
        raise SystemExit("Could not find switch case in ActionUp")
    up_cases = """\tcase XZ_TOUCH_WEAPON2:
\tcase XZ_TOUCH_WEAPON3:
\tcase XZ_TOUCH_WEAPONSTRIP:
\t\tbreak;

"""
    action_chunk = action_chunk.replace(needle, up_cases + needle, 1)
    text = text[:action_start] + action_chunk + text[action_end:]

sdl.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# HUD: weapon strip + original icon-first controls
# ---------------------------------------------------------------------------
hud = source / "render" / "r_hud.c"
text = hud.read_text(encoding="utf-8")

hud_anchor = "extern cvar_t xziel_hud_grenade_y;\n"
hud_externs = """extern cvar_t xziel_mobile_unlimited_pistol;
extern cvar_t xziel_hud_weapons_x;
extern cvar_t xziel_hud_weapons_y;
extern cvar_t xziel_hud_weapons_scale;
"""
if "extern cvar_t xziel_hud_weapons_x;" not in text:
    if hud_anchor not in text:
        raise SystemExit("Could not find HUD weapon extern anchor")
    text = text.replace(hud_anchor, hud_anchor + hud_externs, 1)

glyph_code = r'''
static qboolean Xziel_HUDIsPistol(int id)
{
    return id == W_COLT || id == W_357 || id == W_BIATCH || id == W_KILLU;
}

static qboolean Xziel_HUDIsShotgun(int id)
{
    return id == W_DB || id == W_SAWNOFF || id == W_TRENCH ||
        id == W_SNUFF || id == W_BORE || id == W_GUT;
}

static qboolean Xziel_HUDIsSniper(int id)
{
    return id == W_KAR_SCOPE || id == W_PTRS ||
        id == W_HEADCRACKER || id == W_PENETRATOR;
}

static void Xziel_DrawWeaponGlyph(int cx, int cy, int id, float scale, int alpha)
{
    int body_w, body_h, grip_w, grip_h;

    if (Xziel_HUDIsPistol(id)) {
        body_w = (int)(24 * scale); body_h = (int)(5 * scale);
        grip_w = (int)(5 * scale); grip_h = (int)(12 * scale);
        Draw_FillByColor(cx - body_w/2, cy - body_h/2, body_w, body_h, 245,245,245,alpha);
        Draw_FillByColor(cx + body_w/5, cy + body_h/2 - 1, grip_w, grip_h, 245,245,245,alpha);
        Draw_FillByColor(cx - body_w/2 - (int)(4*scale), cy - 1, (int)(5*scale), (int)(2*scale), 245,245,245,alpha);
        return;
    }

    body_w = (int)((Xziel_HUDIsSniper(id) ? 42 : 35) * scale);
    body_h = (int)((Xziel_HUDIsShotgun(id) ? 5 : 7) * scale);
    Draw_FillByColor(cx - body_w/2, cy - body_h/2, body_w, body_h, 245,245,245,alpha);
    Draw_FillByColor(cx + body_w/2 - 1, cy - (int)(2*scale), (int)(10*scale), (int)(4*scale), 245,245,245,alpha);
    Draw_FillByColor(cx - body_w/6, cy + body_h/2 - 1, (int)(5*scale), (int)(11*scale), 245,245,245,alpha);
    if (Xziel_HUDIsSniper(id)) {
        Draw_FillByColor(cx - (int)(7*scale), cy - (int)(7*scale), (int)(15*scale), (int)(3*scale), 245,245,245,alpha);
        Xziel_DrawDisc(cx, cy - (int)(6*scale), (int)(3*scale), 245,245,245,alpha);
    }
}

static qboolean Xziel_DrawActionGlyph(int cx, int cy, int radius,
    const char *label1, const char *label2, qboolean pressed)
{
    int a = pressed ? 255 : 225;
    int t = (int)fmaxf(2.0f, 2.0f * vid.scale);

    if (!strcmp(label1, "II")) {
        Draw_FillByColor(cx - radius/4, cy - radius/3, t, radius*2/3, 255,255,255,a);
        Draw_FillByColor(cx + radius/4 - t, cy - radius/3, t, radius*2/3, 255,255,255,a);
        return true;
    }

    if (!strcmp(label1, "FIRE")) {
        Xziel_DrawDisc(cx, cy, (int)(3*vid.scale), 255,255,255,a);
        Draw_FillByColor(cx - radius/2, cy - t/2, radius/3, t, 255,255,255,a);
        Draw_FillByColor(cx + radius/6, cy - t/2, radius/3, t, 255,255,255,a);
        Draw_FillByColor(cx - t/2, cy - radius/2, t, radius/3, 255,255,255,a);
        Draw_FillByColor(cx - t/2, cy + radius/6, t, radius/3, 255,255,255,a);
        return true;
    }

    if (!strcmp(label1, "ADS")) {
        int rr = (int)(radius * 0.42f);
        Xziel_DrawDisc(cx, cy, rr, 255,255,255,a);
        Xziel_DrawDisc(cx, cy, rr - t, 8,8,8,180);
        Draw_FillByColor(cx - rr - t, cy - t/2, rr/2, t, 255,255,255,a);
        Draw_FillByColor(cx + rr/2 + t, cy - t/2, rr/2, t, 255,255,255,a);
        Draw_FillByColor(cx - t/2, cy - rr - t, t, rr/2, 255,255,255,a);
        Draw_FillByColor(cx - t/2, cy + rr/2 + t, t, rr/2, 255,255,255,a);
        if (label2 && !strcmp(label2, "FIRE"))
            Draw_FillByColor(cx + rr/2, cy + rr/3, (int)(9*vid.scale), (int)(3*vid.scale), 255,255,255,a);
        return true;
    }

    if (!strcmp(label1, "RLD")) {
        int w = radius;
        Draw_FillByColor(cx - w/2, cy - w/4, w*2/3, t, 255,255,255,a);
        Draw_FillByColor(cx + w/6, cy - w/4, t, w/3, 255,255,255,a);
        Draw_FillByColor(cx - w/6, cy + w/4, w*2/3, t, 255,255,255,a);
        Draw_FillByColor(cx - w/2, cy, t, w/3, 255,255,255,a);
        return true;
    }

    if (!strcmp(label1, "USE")) {
        Draw_FillByColor(cx - radius/4, cy - radius/8, radius/2, radius/2, 255,255,255,a);
        Draw_FillByColor(cx - radius/3, cy - radius/3, t, radius/3, 255,255,255,a);
        Draw_FillByColor(cx - radius/10, cy - radius/3, t, radius/3, 255,255,255,a);
        Draw_FillByColor(cx + radius/7, cy - radius/3, t, radius/3, 255,255,255,a);
        return true;
    }

    if (!strcmp(label1, "JUMP")) {
        Draw_FillByColor(cx - t/2, cy - radius/3, t, radius*2/3, 255,255,255,a);
        Draw_FillByColor(cx - radius/4, cy - radius/3, radius/2, t, 255,255,255,a);
        Draw_FillByColor(cx - radius/3, cy - radius/5, t, t*2, 255,255,255,a);
        Draw_FillByColor(cx + radius/3 - t, cy - radius/5, t, t*2, 255,255,255,a);
        return true;
    }

    if (!strcmp(label1, "KNIFE")) {
        Draw_FillByColor(cx - radius/2, cy - t/2, radius, t*2, 255,255,255,a);
        Draw_FillByColor(cx + radius/4, cy - t*2, t*2, t*4, 255,255,255,a);
        return true;
    }

    if (!strcmp(label1, "NADE")) {
        int rr = (int)(radius * 0.38f);
        Xziel_DrawDisc(cx, cy + radius/10, rr, 255,255,255,a);
        Draw_FillByColor(cx - t/2, cy - rr, t*2, rr/2, 255,255,255,a);
        Draw_FillByColor(cx + t, cy - rr - t, rr/2, t, 255,255,255,a);
        return true;
    }

    return false;
}

static void Xziel_DrawWeaponCard(float nx, float ny, float nw, float nh,
    int weapon, int mag, int reserve, qboolean active, qboolean editor)
{
    int x = (int)((nx - nw*0.5f) * vid.width);
    int y = (int)((ny - nh*0.5f) * vid.height);
    int w = (int)(nw * vid.width);
    int h = (int)(nh * vid.height);
    int border = (int)fmaxf(1.0f, 2.0f * vid.scale);
    int alpha = (int)(xziel_mobile_hud_opacity.value * (active ? 185 : 135));
    char ammo[32];
    float gs;

    if (weapon == 0 && !editor)
        return;

    Draw_FillByColor(x, y, w, h, 4, 4, 4, alpha);
    Draw_FillByColor(x, y, w, border, active ? 255 : 190, active ? 205 : 190, active ? 40 : 190, 220);
    Draw_FillByColor(x, y + h - border, w, border, active ? 255 : 190, active ? 205 : 190, active ? 40 : 190, 220);

    if (weapon != 0) {
        gs = (active ? 0.95f : 0.78f) * vid.scale * xziel_hud_weapons_scale.value;
        Xziel_DrawWeaponGlyph(x + w/2, y + h/2 - (int)(5*vid.scale), weapon, gs, 235);

        if (xziel_mobile_unlimited_pistol.value >= 0.5f && Xziel_HUDIsPistol(weapon))
            snprintf(ammo, sizeof(ammo), "%d / INF", mag);
        else
            snprintf(ammo, sizeof(ammo), "%d / %d", mag, reserve);

        Draw_ColoredString(x + (int)(5*vid.scale), y + h - (int)(11*vid.scale),
            ammo, 255,255,255,230, vid.scale * (active ? 0.68f : 0.56f));
    } else {
        const char *empty = "EMPTY";
        Draw_ColoredString(x + (w - getTextWidth((char *)empty, vid.scale*0.55f))/2,
            y + h/2, (char *)empty, 170,170,170,180, vid.scale*0.55f);
    }
}

static void Xziel_DrawWeaponStrip(qboolean editor)
{
    float s = xziel_hud_weapons_scale.value;
    float bx = xziel_hud_weapons_x.value;
    float by = xziel_hud_weapons_y.value;

    if (s < 0.65f) s = 0.65f;
    if (s > 1.45f) s = 1.45f;

    Xziel_DrawWeaponCard(bx - 0.115f*s, by, 0.150f*s, 0.100f*s,
        cl.stats[STAT_ACTIVEWEAPON], cl.stats[STAT_CURRENTMAG], cl.stats[STAT_AMMO],
        true, editor);

    Xziel_DrawWeaponCard(bx + 0.025f*s, by, 0.110f*s, 0.080f*s,
        cl.stats[STAT_XZIEL_W2], cl.stats[STAT_XZIEL_W2MAG], cl.stats[STAT_XZIEL_W2RES],
        false, editor);

    if (editor || cl.stats[STAT_XZIEL_W3] != 0)
        Xziel_DrawWeaponCard(bx + 0.145f*s, by, 0.110f*s, 0.080f*s,
            cl.stats[STAT_XZIEL_W3], cl.stats[STAT_XZIEL_W3MAG], cl.stats[STAT_XZIEL_W3RES],
            false, editor);
}
'''
if "static void Xziel_DrawWeaponStrip(qboolean editor)" not in text:
    anchor = "static void Xziel_MobileHUD_DrawInternal(qboolean editor)\n"
    idx = text.find(anchor)
    if idx < 0:
        raise SystemExit("Could not find mobile HUD renderer for weapon strip")
    text = text[:idx] + glyph_code + "\n" + text[idx:]

touch_button = r'''static void Xziel_DrawTouchButton(float nx, float ny, float radius_h,
    const char *label1, const char *label2, qboolean pressed)
{
    int cx = (int)(nx * vid.width);
    int cy = (int)(ny * vid.height);
    int radius = (int)(radius_h * vid.height);
    int inner = radius - (int)(2.0f * vid.scale);
    float text_scale = vid.scale * 0.58f;
    int tw;

    if (inner < 2) inner = 2;
    Xziel_DrawDisc(cx, cy, radius, 235, 235, 235,
        (int)((pressed ? 155 : 95) * xziel_mobile_hud_opacity.value));
    Xziel_DrawDisc(cx, cy, inner,
        pressed ? 110 : 8, pressed ? 18 : 8, pressed ? 18 : 8,
        (int)((pressed ? 175 : 115) * xziel_mobile_hud_opacity.value));

    /* Icon-first mobile controls. Labels remain a fallback for any future
       action that does not yet have an original glyph. */
    if (Xziel_DrawActionGlyph(cx, cy, radius, label1, label2, pressed))
        return;

    if (label1 && label1[0]) {
        tw = getTextWidth((char *)label1, text_scale);
        Draw_ColoredString(cx - tw / 2, cy - (int)(3 * vid.scale),
            (char *)label1, 255,255,255,235, text_scale);
    }
}'''
text = replace_c_function(
    text,
    "static void Xziel_DrawTouchButton(float nx, float ny, float radius_h,",
    touch_button
)

old_swap = '\tXziel_DrawTouchButton(xziel_hud_switch_x.value, xziel_hud_switch_y.value, 0.041f, "SWAP", "", xziel_mobile_switch_pressed);\n'
if old_swap in text:
    text = text.replace(old_swap, "\tXziel_DrawWeaponStrip(editor);\n", 1)
elif "Xziel_DrawWeaponStrip(editor);" not in text:
    raise SystemExit("Could not replace old SWAP HUD control")

hud.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# Mobile settings
# ---------------------------------------------------------------------------
controls = source / "menu" / "menu_controls.c"
text = controls.read_text(encoding="utf-8")

extern_anchor = "extern cvar_t xziel_mobile_sprint_zone;\n"
menu_externs = """extern cvar_t xziel_mobile_unlimited_pistol;
extern cvar_t xziel_hud_weapons_x;
extern cvar_t xziel_hud_weapons_y;
extern cvar_t xziel_hud_weapons_scale;
"""
if "extern cvar_t xziel_mobile_unlimited_pistol;" not in text:
    if extern_anchor not in text:
        raise SystemExit("Could not find mobile menu extern anchor")
    text = text.replace(extern_anchor, extern_anchor + menu_externs, 1)

string_anchor = "static char *xziel_mobile_knife_visibility_string;\n"
if "xziel_mobile_unlimited_pistol_string" not in text:
    if string_anchor not in text:
        raise SystemExit("Could not find mobile gameplay string anchor")
    text = text.replace(
        string_anchor,
        string_anchor + "static char *xziel_mobile_unlimited_pistol_string;\n",
        1
    )

toggle_anchor = "static void Menu_Mobile_ToggleKnifeVisibility(void)\n"
if "Menu_Mobile_ToggleUnlimitedPistol" not in text:
    idx = text.find(toggle_anchor)
    if idx < 0:
        raise SystemExit("Could not find mobile toggle insertion point")
    # Insert before existing toggle so no function parsing is needed.
    toggle = r'''static void Menu_Mobile_ToggleUnlimitedPistol(void)
{
    Cvar_SetValue("xziel_mobile_unlimited_pistol",
        xziel_mobile_unlimited_pistol.value >= 0.5f ? 0.0f : 1.0f);
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

    Menu_DrawButton(row++, idx++, "SPRINT ACTIVATION HEIGHT",
        "Higher means drag farther above the joystick before native sprint starts.", NULL);
    Menu_DrawOptionSlider(row-1, idx-1, 1.10f, 1.85f,
        xziel_mobile_sprint_zone, "xziel_mobile_sprint_zone", false, true, 0.05f);

    Menu_DrawButton(row++, idx++, "UNLIMITED PISTOL RESERVE",
        "Pistol magazines stay finite and still reload. Reserve refills and a third weapon slot becomes available.",
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

    Menu_DrawButton(row++, idx++, "KNIFE RANGE",
        "Uses native weapon melee range; not an artificial mobile distance.", NULL);
    Menu_DrawOptionButton(row-1, "NATIVE 88 / 96");

    Menu_DrawButton(-1, idx, "BACK", "Return to Mobile Settings.", Menu_Mobile_Set);
}'''
text = replace_c_function(text, "void Menu_MobileGameplay_Draw(void)", gameplay)

hud_page = r'''void Menu_MobileHud_Draw(void)
{
    int idx = 0, row = 1;

    Menu_DrawCustomBackground(true);
    Menu_DrawTitle("MOBILE - HUD & LAYOUT", MENU_COLOR_WHITE);
    Menu_DrawMapPanel();

    Menu_DrawButton(row++, idx++, "HUD SCALE", "Scale mobile action controls.", NULL);
    Menu_DrawOptionSlider(row-1, idx-1, 0.70f, 1.35f,
        xziel_mobile_hud_scale, "xziel_mobile_hud_scale", false, true, 0.05f);

    Menu_DrawButton(row++, idx++, "HUD OPACITY", "Opacity of mobile controls.", NULL);
    Menu_DrawOptionSlider(row-1, idx-1, 0.25f, 1.0f,
        xziel_mobile_hud_opacity, "xziel_mobile_hud_opacity", false, true, 0.05f);

    Menu_DrawButton(row++, idx++, "WEAPON STRIP SCALE", "Scale the weapon cards independently.", NULL);
    Menu_DrawOptionSlider(row-1, idx-1, 0.65f, 1.45f,
        xziel_hud_weapons_scale, "xziel_hud_weapons_scale", false, true, 0.05f);

    Menu_DrawButton(row++, idx++, "CUSTOM HUD",
        "Drag controls and the whole weapon strip to your preferred positions.", Menu_HudEdit_Set);

    Menu_DrawButton(-1, idx, "BACK", "Return to Mobile Settings.", Menu_Mobile_Set);
}'''
text = replace_c_function(text, "void Menu_MobileHud_Draw(void)", hud_page)

# Reset location/scale together with the rest of the HUD.
reset_anchor = 'Cvar_SetValue("xziel_hud_grenade_x", 0.835f); Cvar_SetValue("xziel_hud_grenade_y", 0.300f);\n'
reset_more = '''\tCvar_SetValue("xziel_hud_weapons_x", 0.50f); Cvar_SetValue("xziel_hud_weapons_y", 0.885f);
\tCvar_SetValue("xziel_hud_weapons_scale", 1.0f);
'''
if 'Cvar_SetValue("xziel_hud_weapons_x"' not in text:
    if reset_anchor not in text:
        raise SystemExit("Could not find HUD reset grenade anchor")
    text = text.replace(reset_anchor, reset_anchor + reset_more, 1)

controls.write_text(text, encoding="utf-8")

print("Patched Vril weapon HUD / mobile inventory UI.")
