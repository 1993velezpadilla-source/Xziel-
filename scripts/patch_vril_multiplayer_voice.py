#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_vril_multiplayer_voice.py <vril-root>")

root = Path(sys.argv[1])
source = root / "source"

# ---------------------------------------------------------------------------
# Main menu: enable the formerly-grey cooperative slot as MULTIPLAYER.
# Android UI owns create/join room so the game menu stays touch-safe.
# ---------------------------------------------------------------------------
main = source / "menu" / "menu_main.c"
text = main.read_text(encoding="utf-8")

resume_anchor = """#ifdef __ANDROID__
static qboolean Menu_XzielResumeExists(void)
"""
if "Menu_XzielMultiplayer" not in text:
    if resume_anchor not in text:
        raise SystemExit("Could not find Android main-menu block")
    bridge = """#ifdef __ANDROID__
extern void Xziel_Android_OpenMultiplayer(void);

static void Menu_XzielMultiplayer(void)
{
    Xziel_Android_OpenMultiplayer();
}
#endif

"""
    text = text.replace(resume_anchor, bridge + resume_anchor, 1)

old = """		Menu_DrawButton(1 + xziel_offset, xziel_offset, "SOLO", "Play Solo.", Menu_Solo);
		Menu_DrawGreyButton(2 + xziel_offset, "COOPERATIVE");

		Menu_DrawDivider(3 + xziel_offset);

		Menu_DrawButton(3 + xziel_offset, 1 + xziel_offset, "CONFIGURATION", "Tweak Game Related Options", Menu_Configuration_Set);
		Menu_DrawButton(4 + xziel_offset, 2 + xziel_offset, "CHARACTER BIOS", "View Character Bios", Menu_Bios_Set);

		Menu_DrawDivider(5 + xziel_offset);

		Menu_DrawButton(5 + xziel_offset, 3 + xziel_offset, "CREDITS", "NZ:P Team + Special Thanks", Menu_Credits_Set);

		Menu_DrawDivider(6 + xziel_offset);

		Menu_DrawButton(6 + xziel_offset, 4 + xziel_offset, "QUIT GAME", "Return to Home Screen", Menu_EnterSubMenu);
"""
new = """		Menu_DrawButton(1 + xziel_offset, xziel_offset, "SOLO", "Play Solo.", Menu_Solo);
		Menu_DrawButton(2 + xziel_offset, 1 + xziel_offset, "MULTIPLAYER", "Create or join a private online Zombies room.", Menu_XzielMultiplayer);

		Menu_DrawDivider(3 + xziel_offset);

		Menu_DrawButton(3 + xziel_offset, 2 + xziel_offset, "CONFIGURATION", "Tweak Game Related Options", Menu_Configuration_Set);
		Menu_DrawButton(4 + xziel_offset, 3 + xziel_offset, "CHARACTER BIOS", "View Character Bios", Menu_Bios_Set);

		Menu_DrawDivider(5 + xziel_offset);

		Menu_DrawButton(5 + xziel_offset, 4 + xziel_offset, "CREDITS", "NZ:P Team + Special Thanks", Menu_Credits_Set);

		Menu_DrawDivider(6 + xziel_offset);

		Menu_DrawButton(6 + xziel_offset, 5 + xziel_offset, "QUIT GAME", "Return to Home Screen", Menu_EnterSubMenu);
"""
if old not in text:
    raise SystemExit("Could not find final Android main-menu buttons")
text = text.replace(old, new, 1)
main.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# Proximity voice listener position.
# Push the real rendered player entity origin to Android after each relink.
# Java only stores three floats here, so this does not block the game thread.
# ---------------------------------------------------------------------------
cl_main = source / "cl_main.c"
text = cl_main.read_text(encoding="utf-8")

include_anchor = '#include "quakedef.h"\n'
extern_block = """#ifdef __ANDROID__
extern void Xziel_Android_VoiceUpdatePosition(float x, float y, float z);
#endif
"""
if "Xziel_Android_VoiceUpdatePosition" not in text:
    if include_anchor not in text:
        raise SystemExit("Could not find cl_main include anchor")
    text = text.replace(include_anchor, include_anchor + extern_block, 1)

update_anchor = """	CL_RelinkEntities ();
	CL_UpdateTEnts ();

//
// bring the links up to date
//
"""
update_repl = """	CL_RelinkEntities ();
	CL_UpdateTEnts ();

#ifdef __ANDROID__
	if (cl.viewentity > 0 && cl.viewentity < cl.num_entities) {
		entity_t *voice_listener = &cl_entities[cl.viewentity];
		Xziel_Android_VoiceUpdatePosition(
			voice_listener->origin[0],
			voice_listener->origin[1],
			voice_listener->origin[2]);
	}
#endif

//
// bring the links up to date
//
"""
if "entity_t *voice_listener" not in text:
    if update_anchor not in text:
        raise SystemExit("Could not find CL_ReadFromServer update anchor")
    text = text.replace(update_anchor, update_repl, 1)

cl_main.write_text(text, encoding="utf-8")
print("multiplayer/voice Vril patch applied")
