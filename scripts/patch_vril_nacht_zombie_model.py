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
helper = r'''static int Xziel_NachtEnhanced_MapZombieFrame(int frame)
{
    // LibreQuake zombie layout: stand 0-14, walk 15-33, run 34-51,
    // attacks 52-90 and pain/down sequences 91-191.
    if (frame >= 0 && frame <= 13)
        return (frame * 14) / 13;
    if (frame >= 37 && frame <= 82)
        return 15 + ((frame - 37) % 19);
    if (frame >= 83 && frame <= 101)
        return 34 + ((frame - 83) % 18);
    if (frame >= 102 && frame <= 112)
        return 65 + ((frame - 102) % 14);
    if (frame >= 113 && frame <= 122)
        return 91 + ((frame - 113) % 12);
    if (frame >= 123 && frame <= 148)
        return 162 + (((frame - 123) * 29) / 25);
    if (frame >= 149 && frame <= 159)
        return 162 + (((frame - 149) * 29) / 10);
    if (frame >= 181 && frame <= 210)
        return 52 + ((frame - 181) % 39);
    if (frame < 0)
        return 0;
    return frame % 250;
}

static qboolean Xziel_NachtEnhanced_ShouldReplaceZombie(model_t *source)
{
    if (xziel_nacht_enhanced.value < 0.5f || !source || !cl.worldmodel)
        return false;
    if (strcmp(cl.worldmodel->name, "maps/ndu.bsp"))
        return false;

    // Crawlers retain stock segmented geometry until a purpose-built
    // crawl/death replacement is ready.
    return !strcmp(source->name, "models/ai/zb%.mdl");
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
	if (Xziel_NachtEnhanced_ShouldReplaceZombie(clmodel))
	{
		model_t *replacement = Mod_ForName("models/xziel/nacht/zombie_lq.mdl", false);
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

	specChar = clmodel->name[strlen(clmodel->name) - 5];
'''
if "Xziel_NachtEnhanced_ShouldReplaceZombie(clmodel)" not in chunk:
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
