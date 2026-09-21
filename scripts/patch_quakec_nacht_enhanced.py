#!/usr/bin/env python3
"""Add a Nacht-only Classic/Enhanced presentation toggle to NZ:P game settings."""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_quakec_nacht_enhanced.py <quakec-root>")
root=Path(sys.argv[1])
g=root/"source/menu/menu_gset.qc"
l=root/"source/menu/menu_loby.qc"
s=g.read_text()

s=s.replace('string menu_gset_buttons[8] = {"ge_mode", "ge_diff", "ge_rond", "ge_magc", "ge_head", "ge_hord", "ge_frnd", "ge_back"};',
'''string menu_gset_buttons[9] = {"ge_mode", "ge_diff", "ge_rond", "ge_magc", "ge_head", "ge_hord", "ge_frnd", "ge_enhc", "ge_back"};''')

# Skip the Nacht-only row when navigating settings for every other map.
s=s.replace("""    return ret;
};

string(string next_id) Menu_GameSettings_GetPreviousButton =""","""    if (ret == "ge_enhc" && current_selected_bsp != "ndu")
        return "ge_back";

    return ret;
};

string(string next_id) Menu_GameSettings_GetPreviousButton =""",1)
s=s.replace("""    return ret;
};

void() Menu_GameSettings_ApplyGameMode =""","""    if (ret == "ge_enhc" && current_selected_bsp != "ndu")
        return "ge_frnd";

    return ret;
};

void() Menu_GameSettings_ApplyGameMode =""",1)

anchor='void() Menu_GameSettings = \n{'
helper='''void() Menu_GameSettings_ApplyNachtEnhanced =
{
    Menu_PlaySound(MENU_SND_ENTER);
    float enabled = cvar("xziel_nacht_enhanced");
    cvar_set("xziel_nacht_enhanced", enabled ? "0" : "1");
};

'''
if helper not in s:
    s=s.replace(anchor,helper+anchor)

needle='''    Menu_DrawOptionValue(7, fast_string);

    Menu_Button(-1, "ge_back", "BACK", "Return to Pre-Game Menu.") ? current_menu = MENU_LOBBY : 0;'''
repl='''    Menu_DrawOptionValue(7, fast_string);

    // Nacht der Untoten presentation mode. Classic remains byte-for-byte
    // gameplay-compatible; Enhanced is opt-in and is consumed by the Android
    // asset/runtime overlay without changing the BSP layout or zombie rules.
    if (current_selected_bsp == "ndu") {
        string enhanced_string = cvar("xziel_nacht_enhanced") ? "ENHANCED" : "CLASSIC";
        Menu_Button(8, "ge_enhc", "NACHT VISUALS", "Classic layout with optional enhanced models, materials, lighting and effects.") ? Menu_GameSettings_ApplyNachtEnhanced() : 0;
        Menu_DrawOptionValue(8, enhanced_string);
    }

    Menu_Button(-1, "ge_back", "BACK", "Return to Pre-Game Menu.") ? current_menu = MENU_LOBBY : 0;'''
if needle not in s: raise SystemExit("game settings anchor not found")
s=s.replace(needle,repl,1)
g.write_text(s)

s=l.read_text()
needle='''    string fast_rounds = "";'''
s=s.replace(needle,needle+'\n    string nacht_visuals = "";',1)
needle='''    if (cvar("sv_fastrounds") == 1) fast_rounds = "ENABLED";
    else fast_rounds = "DISABLED";'''
s=s.replace(needle,needle+'''\n\n    if (current_selected_bsp == "ndu") {
        if (cvar("xziel_nacht_enhanced")) nacht_visuals = "ENHANCED";
        else nacht_visuals = "CLASSIC";
    }''',1)
needle='''    sui_fill([80, -15], [90, 2], [0.2, 0.2, 0.2], 1, 0);'''
s=s.replace(needle,needle+'''\n\n    if (current_selected_bsp == "ndu") {
        sui_text([220, -40], MENU_TEXT_MEDIUM, "Nacht Visuals", [1, 1, 1], 1, 0);
        sui_text([220, -25], MENU_TEXT_SMALL, nacht_visuals, [1, 1, 0], 1, 0);
        sui_fill([220, -15], [90, 2], [0.2, 0.2, 0.2], 1, 0);
    }''',1)
l.write_text(s)
print("Added Nacht Classic/Enhanced setting.")
