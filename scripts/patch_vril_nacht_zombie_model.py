#!/usr/bin/env python3
"""Render a real alternate zombie model in Nacht Enhanced.

Presentation-only: server AI, health, damage, hitboxes, navigation, limb
state, scoring and round logic remain NZ:P authoritative.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_vril_nacht_zombie_model.py <vril-root>")

p = Path(sys.argv[1]) / "source" / "platform" / "sdl" / "gl" / "gl_rmain.c"
s = p.read_text(encoding="utf-8")

def function_bounds(src: str, signature: str):
    start = src.find(signature)
    if start < 0:
        raise SystemExit("Could not find function: " + signature)
    brace = src.find("{", start)
    if brace < 0:
        raise SystemExit("Could not find function body: " + signature)
    depth = 0
    for i in range(brace, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return start, i + 1
    raise SystemExit("Could not find function end: " + signature)

extern_anchor = "extern\tcvar_t\tgl_ztrick;\n"
extern_line = "extern cvar_t xziel_nacht_enhanced;\n"
if extern_line not in s:
    if extern_anchor not in s:
        raise SystemExit("Nacht zombie cvar extern anchor missing")
    s = s.replace(extern_anchor, extern_anchor + extern_line, 1)

helper_anchor = "int doZHack;\n"
helper = r'''static int Xziel_NachtEnhanced_ScaleFrame(int frame, int src_first, int src_last, int dst_first, int dst_last)
{
    if (src_last <= src_first)
        return dst_first;
    return dst_first + ((frame - src_first) * (dst_last - dst_first)) / (src_last - src_first);
}

static int Xziel_NachtEnhanced_MapZombieFrame(int frame)
{
    // NZ:P source body (zb%.mdl) uses 211 frames. Map each *actual runtime
    // sequence* independently so loops do not jump into the middle of the
    // LibreQuake animation. Target ranges come from LibreQuake zombie.qc:
    // stand 0-14, walk 15-33, run 34-51, attack A/B/C 52-90,
    // pain A 91-102, pain E knock-down 162-191.
    //
    // Idle: NZ:P 0-12 -> complete 15-frame LibreQuake stand cycle.
    if (frame >= 0 && frame <= 12)
        return Xziel_NachtEnhanced_ScaleFrame(frame, 0, 12, 0, 14);

    // Three independent NZ:P walk styles. Scale each one separately to the
    // same complete target walk cycle; never modulo across style boundaries.
    if (frame >= 37 && frame <= 52)
        return Xziel_NachtEnhanced_ScaleFrame(frame, 37, 52, 15, 33);
    if (frame >= 53 && frame <= 66)
        return Xziel_NachtEnhanced_ScaleFrame(frame, 53, 66, 15, 33);
    if (frame >= 67 && frame <= 82)
        return Xziel_NachtEnhanced_ScaleFrame(frame, 67, 82, 15, 33);

    // Jog and sprint are separate NZ:P loops. Both get the full run cycle so
    // each loop closes cleanly instead of wrapping halfway through a stride.
    if (frame >= 83 && frame <= 90)
        return Xziel_NachtEnhanced_ScaleFrame(frame, 83, 90, 34, 51);
    if (frame >= 92 && frame <= 101)
        return Xziel_NachtEnhanced_ScaleFrame(frame, 92, 101, 34, 51);

    // Zombie swipes. Use one complete melee sequence.
    if (frame >= 102 && frame <= 112)
        return Xziel_NachtEnhanced_ScaleFrame(frame, 102, 112, 65, 78);

    // Window hop has no exact LibreQuake equivalent. Pain-A is a bounded
    // forward body motion and is visually safer than an unrelated attack.
    if (frame >= 113 && frame <= 122)
        return Xziel_NachtEnhanced_ScaleFrame(frame, 113, 122, 91, 102);

    // NZ:P death A/B/C. LibreQuake's pain-E is a knock-down + resurrection;
    // use ONLY its falling/ground portion (162-172), never frames 173-191
    // which stand the monster back up.
    if (frame >= 123 && frame <= 133)
        return Xziel_NachtEnhanced_ScaleFrame(frame, 123, 133, 162, 172);
    if (frame >= 134 && frame <= 138)
        return Xziel_NachtEnhanced_ScaleFrame(frame, 134, 138, 162, 172);
    if (frame >= 139 && frame <= 148)
        return Xziel_NachtEnhanced_ScaleFrame(frame, 139, 148, 162, 172);

    // Falling/Wunder sequence: fall through the down section, then remain
    // prone for landing frames instead of visually resurrecting.
    if (frame >= 149 && frame <= 152)
        return Xziel_NachtEnhanced_ScaleFrame(frame, 149, 152, 162, 171);
    if (frame >= 153 && frame <= 159)
        return 172;

    // Barricade ripping and through-window attacks: map the three distinct
    // source ranges to the three complete target attack sequences.
    if (frame >= 181 && frame <= 191)
        return Xziel_NachtEnhanced_ScaleFrame(frame, 181, 191, 52, 64);
    if (frame >= 192 && frame <= 201)
        return Xziel_NachtEnhanced_ScaleFrame(frame, 192, 201, 65, 78);
    if (frame >= 202 && frame <= 210)
        return Xziel_NachtEnhanced_ScaleFrame(frame, 202, 210, 79, 90);

    // 13-36, 91 and 160-180 are not live body sequences in the current NZ:P
    // zombie logic. Fail neutral instead of frame%250, which could expose a
    // random pain/crucified pose if an unknown state ever reaches the renderer.
    return 0;
}

static const char *Xziel_NachtEnhanced_ZombieVariant(model_t *source)
{
    if (xziel_nacht_enhanced.value < 0.5f || !source || !cl.worldmodel)
        return NULL;
    if (strcmp(cl.worldmodel->name, "maps/ndu.bsp"))
        return NULL;

    // Normal standing/running zombie body only. Crawlers use zbc%.mdl and
    // deliberately stay on the stock segmented path until a purpose-built
    // crawl replacement ships.
    if (strcmp(source->name, "models/ai/zb%.mdl"))
        return NULL;

    // z_head/z_larm/z_rarm are NZ:P's authoritative attached-limb entity
    // indices. Pick a body variant that visually matches that state instead
    // of snapping back to the Classic zombie after dismemberment.
    if (currententity->z_head && currententity->z_larm && currententity->z_rarm)
        return "models/xziel/nacht/zombie_lq.mdl";
    if (!currententity->z_head && currententity->z_larm && currententity->z_rarm)
        return "models/xziel/nacht/zombie_lq_h0.mdl";
    if (currententity->z_head && !currententity->z_larm && currententity->z_rarm)
        return "models/xziel/nacht/zombie_lq_l0.mdl";
    if (currententity->z_head && currententity->z_larm && !currententity->z_rarm)
        return "models/xziel/nacht/zombie_lq_r0.mdl";
    if (!currententity->z_head && !currententity->z_larm && currententity->z_rarm)
        return "models/xziel/nacht/zombie_lq_h0_l0.mdl";
    if (!currententity->z_head && currententity->z_larm && !currententity->z_rarm)
        return "models/xziel/nacht/zombie_lq_h0_r0.mdl";
    if (currententity->z_head && !currententity->z_larm && !currententity->z_rarm)
        return "models/xziel/nacht/zombie_lq_l0_r0.mdl";
    return "models/xziel/nacht/zombie_lq_h0_l0_r0.mdl";
}
'''
if "Xziel_NachtEnhanced_MapZombieFrame" not in s:
    if helper_anchor not in s:
        raise SystemExit("Nacht zombie renderer helper anchor missing")
    s = s.replace(helper_anchor, helper + helper_anchor, 1)

start, end = function_bounds(s, "void R_DrawAliasModel (entity_t *e)")
chunk = s[start:end]

decl_anchor = '''	int			anim;

	clmodel = currententity->model;
'''
decl_repl = '''	int			anim;
	model_t     *xziel_source_model = NULL;
	int          xziel_source_frame = e->frame;
	int          xziel_source_skin = e->skinnum;
	qboolean     xziel_nacht_zombie_replaced = false;

	clmodel = currententity->model;
'''
if "xziel_nacht_zombie_replaced" not in chunk:
    if decl_anchor not in chunk:
        raise SystemExit("Nacht zombie local declaration anchor missing")
    chunk = chunk.replace(decl_anchor, decl_repl, 1)

cull_anchor = '''	if (R_CullBox (mins, maxs))
		return;

	specChar = clmodel->name[strlen(clmodel->name) - 5];
'''
cull_repl = '''	if (R_CullBox (mins, maxs))
		return;

	// Swap only the render model. Network/server state never changes.
	{
		const char *xziel_variant = Xziel_NachtEnhanced_ZombieVariant(clmodel);
		if (xziel_variant)
		{
			model_t *replacement = Mod_ForName((char *)xziel_variant, false);
			if (replacement && replacement->type == mod_alias)
			{
				xziel_source_model = e->model;
				xziel_source_frame = e->frame;
				xziel_source_skin = e->skinnum;
				e->model = replacement;
				e->frame = Xziel_NachtEnhanced_MapZombieFrame(xziel_source_frame);
				e->skinnum = 0;
				clmodel = replacement;
				xziel_nacht_zombie_replaced = true;
			}
		}
	}

	specChar = clmodel->name[strlen(clmodel->name) - 5];
'''
if "Xziel_NachtEnhanced_ZombieVariant(clmodel)" not in chunk:
    if cull_anchor not in chunk:
        raise SystemExit("Nacht zombie cull anchor missing")
    chunk = chunk.replace(cull_anchor, cull_repl, 1)

# Restore the real network entity after every draw; shadows intentionally use
# the replacement geometry first.
final_brace = chunk.rfind("}")
restore = r'''
	if (xziel_nacht_zombie_replaced)
	{
		e->model = xziel_source_model;
		e->frame = xziel_source_frame;
		e->skinnum = xziel_source_skin;
	}

'''
if "e->model = xziel_source_model;" not in chunk:
    chunk = chunk[:final_brace] + restore + chunk[final_brace:]

s = s[:start] + chunk + s[end:]
p.write_text(s, encoding="utf-8")
print("Enabled real Nacht Enhanced alternate zombie render model.")
