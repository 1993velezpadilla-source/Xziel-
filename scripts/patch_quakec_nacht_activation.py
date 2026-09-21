#!/usr/bin/env python3
"""Make Nacht Enhanced impossible to miss on mobile.

The old implementation only exposed the toggle inside GAME SETTINGS. This
adds a dedicated PRE-GAME button for Nacht and defaults stock Nacht selection
to Enhanced. Classic remains one tap away and gameplay rules are unchanged.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_quakec_nacht_activation.py <quakec-root>")

root = Path(sys.argv[1])
maps = root / "source" / "menu" / "menu_maps.qc"
lobby = root / "source" / "menu" / "menu_loby.qc"


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
                # QC functions conventionally terminate with ';'
                if end < len(src) and src[end] == ";":
                    end += 1
                break
    if end < 0:
        raise SystemExit("Could not find function end: " + signature)
    return src[:start] + replacement + src[end:]


# Stock Nacht enters the lobby in Enhanced mode by default. This also fixes
# devices that have an archived xziel_nacht_enhanced=0 from an older APK.
s = maps.read_text(encoding="utf-8")
load_map = r'''void(string bsp_name) Menu_Maps_LoadMap =
{
    current_selected_bsp = bsp_name;
    last_map_menu = current_menu;
    cvar_set("sv_gamemode", "0");
	cvar_set("sv_difficulty", "0");
	cvar_set("sv_startround", "0");
	cvar_set("sv_magic", "1");
	cvar_set("sv_headshotonly", "0");
	cvar_set("sv_maxai", "24");
	cvar_set("sv_fastrounds", "0");

    // Xziel's stock Nacht entry is the Enhanced presentation by default.
    // The PRE-GAME screen exposes a one-tap Classic/Enhanced switch.
    if (bsp_name == "ndu") {
        cvar_set("xziel_nacht_enhanced", "1");
        cvar_set("xziel_modern_zombies", "1");
    }

    current_menu = MENU_LOBBY;
};'''
s = replace_function(s, "void(string bsp_name) Menu_Maps_LoadMap =", load_map)
maps.write_text(s, encoding="utf-8")


s = lobby.read_text(encoding="utf-8")
s = s.replace(
    'string menu_loby_buttons[3] = {"lo_start", "lo_games", "lo_back"};',
    'string menu_loby_buttons[4] = {"lo_start", "lo_enh", "lo_games", "lo_back"};',
    1,
)

next_fn = r'''string(string prev_id) Menu_Lobby_GetNextButton =
{
    if (menu_loby_countdown != 0)
        return "lo_cancl";

    if (prev_id == "")
        return menu_loby_buttons[0];

    string ret = menu_loby_buttons[0];

    for(float i = 0; i < menu_loby_buttons.length; i++) {
        if (menu_loby_buttons[i] == prev_id) {
            if (i + 1 >= menu_loby_buttons.length)
                break;

            ret = menu_loby_buttons[i + 1];
            break;
        }
    }

    if (ret == "lo_enh" && current_selected_bsp != "ndu")
        ret = "lo_games";

    if (ret == "lo_games" && !UserMapSupportsCustomGameLookup(current_selected_bsp))
        ret = "lo_back";

    return ret;
};'''
s = replace_function(s, "string(string prev_id) Menu_Lobby_GetNextButton =", next_fn)

prev_fn = r'''string(string next_id) Menu_Lobby_GetPreviousButton =
{
    if (menu_loby_countdown != 0)
        return "lo_cancl";

    if (next_id == "")
        return menu_loby_buttons[menu_loby_buttons.length - 1];

    string ret = menu_loby_buttons[menu_loby_buttons.length - 1];

    for(float i = menu_loby_buttons.length - 1; i > 0; i--) {
        if (menu_loby_buttons[i] == next_id) {
            if (i - 1 < 0)
                break;

            ret = menu_loby_buttons[i - 1];
            break;
        }
    }

    if (ret == "lo_games" && !UserMapSupportsCustomGameLookup(current_selected_bsp)) {
        if (current_selected_bsp == "ndu")
            ret = "lo_enh";
        else
            ret = "lo_start";
    }

    if (ret == "lo_enh" && current_selected_bsp != "ndu")
        ret = "lo_start";

    return ret;
};'''
s = replace_function(s, "string(string next_id) Menu_Lobby_GetPreviousButton =", prev_fn)

toggle = r'''
void() Menu_Lobby_ToggleNachtEnhanced =
{
    Menu_PlaySound(MENU_SND_ENTER);

    if (cvar("xziel_nacht_enhanced") >= 0.5)
        cvar_set("xziel_nacht_enhanced", "0");
    else {
        cvar_set("xziel_nacht_enhanced", "1");
        // Enhanced mode always opts into the smoother zombie motion layer.
        cvar_set("xziel_modern_zombies", "1");
    }
};

'''
if "Menu_Lobby_ToggleNachtEnhanced" not in s:
    anchor = "void() Menu_Lobby ="
    idx = s.find(anchor)
    if idx < 0:
        raise SystemExit("Lobby draw anchor missing")
    s = s[:idx] + toggle + s[idx:]

lobby_fn = r'''void() Menu_Lobby =
{
    Menu_DrawBackground();
    Menu_DrawTitle("PRE-GAME");

    float support_gamesettings = UserMapSupportsCustomGameLookup(current_selected_bsp);
    string nacht_button = "NACHT: CLASSIC";
    if (cvar("xziel_nacht_enhanced") >= 0.5)
        nacht_button = "NACHT: ENHANCED";

    if (menu_loby_countdown == 0) {
        Menu_Button(1, "lo_start", "START GAME", "Face the Horde!") ? Menu_Lobby_StartCountdown() : 0;

        if (current_selected_bsp == "ndu") {
            Menu_Button(2, "lo_enh", nacht_button,
                "Toggle the Enhanced materials, lighting, atmosphere and effects layer. Classic preserves stock presentation.")
                ? Menu_Lobby_ToggleNachtEnhanced() : 0;

            if (support_gamesettings)
                Menu_Button(3, "lo_games", "GAME SETTINGS", "Adjust Gameplay Options.") ? current_menu = MENU_GAMESETTINGS : 0;
            else
                Menu_GreyButton(3, "NOT SUPPORTED BY MAP");
        } else {
            if (support_gamesettings)
                Menu_Button(2, "lo_games", "GAME SETTINGS", "Adjust Gameplay Options.") ? current_menu = MENU_GAMESETTINGS : 0;
            else
                Menu_GreyButton(2, "NOT SUPPORTED BY MAP");
        }

        Menu_Button(-1, "lo_back", "BACK", "Return to Map Selection.") ? current_menu = last_map_menu : 0;
    } else {
        Menu_Button(1, "lo_cancl", "CANCEL", "..Take it back!") ? Menu_Lobby_StopCountdown() : 0;

        if (current_selected_bsp == "ndu") {
            Menu_GreyButton(2, nacht_button);
            if (support_gamesettings)
                Menu_GreyButton(3, "GAME SETTINGS");
            else
                Menu_GreyButton(3, "NOT SUPPORTED BY MAP");
        } else {
            if (support_gamesettings)
                Menu_GreyButton(2, "GAME SETTINGS");
            else
                Menu_GreyButton(2, "NOT SUPPORTED BY MAP");
        }

        Menu_GreyButton(-1, "BACK");
    }

    Menu_DrawMapPanel();
    Menu_DrawMapPreview();

    sui_set_align([SUI_ALIGN_CENTER, SUI_ALIGN_CENTER]);

    string gamemode = "";
    string difficulty = "";
    string start_round = "";
    string magic = "";
    string headshots = "";
    string fast_rounds = "";
    string nacht_visuals = "";

    switch(cvar("sv_gamemode")) {
        case 0: gamemode = "CLASSIC"; break;
        case 1: gamemode = "GRIEF"; break;
        case 2: gamemode = "GUN GAME"; break;
        case 3: gamemode = "HARDCORE"; break;
        case 4: gamemode = "WILD WEST"; break;
        case 5: gamemode = "STICKS & STONES"; break;
        case 6: gamemode = "FEVER"; break;
        default: gamemode = "???"; break;
    }

    switch(cvar("sv_difficulty")) {
        case 0: difficulty = "NORMAL"; break;
        case 1: difficulty = "EASY"; break;
        case 2: difficulty = "HARD"; break;
        case 3: difficulty = "NIGHTMARE"; break;
        default: difficulty = "???"; break;
    }

    start_round = ftos(cvar("sv_startround"));
    if (start_round == "0") start_round = "1";

    if (cvar("sv_magic") == 1) magic = "ENABLED";
    else magic = "DISABLED";

    if (cvar("sv_headshotonly") == 1) headshots = "ENABLED";
    else headshots = "DISABLED";

    if (cvar("sv_fastrounds") == 1) fast_rounds = "ENABLED";
    else fast_rounds = "DISABLED";

    if (current_selected_bsp == "ndu") {
        if (cvar("xziel_nacht_enhanced")) nacht_visuals = "ENHANCED";
        else nacht_visuals = "CLASSIC";
    }

    sui_text([80, -160], MENU_TEXT_MEDIUM, "Game Mode", [1, 1, 1], 1, 0);
    sui_text([80, -145], MENU_TEXT_SMALL, gamemode, [1, 1, 0], 1, 0);
    sui_fill([80, -135], [90, 2], [0.2, 0.2, 0.2], 1, 0);

    sui_text([220, -160], MENU_TEXT_MEDIUM, "Difficulty", [1, 1, 1], 1, 0);
    sui_text([220, -145], MENU_TEXT_SMALL, difficulty, [1, 1, 0], 1, 0);
    sui_fill([220, -135], [90, 2], [0.2, 0.2, 0.2], 1, 0);

    sui_text([80, -120], MENU_TEXT_MEDIUM, "Start Round", [1, 1, 1], 1, 0);
    sui_text([80, -105], MENU_TEXT_SMALL, start_round, [1, 1, 0], 1, 0);
    sui_fill([80, -95], [90, 2], [0.2, 0.2, 0.2], 1, 0);

    sui_text([220, -120], MENU_TEXT_MEDIUM, "Magic", [1, 1, 1], 1, 0);
    sui_text([220, -105], MENU_TEXT_SMALL, magic, [1, 1, 0], 1, 0);
    sui_fill([220, -95], [90, 2], [0.2, 0.2, 0.2], 1, 0);

    sui_text([80, -80], MENU_TEXT_MEDIUM, "Headshots Only", [1, 1, 1], 1, 0);
    sui_text([80, -65], MENU_TEXT_SMALL, headshots, [1, 1, 0], 1, 0);
    sui_fill([80, -55], [90, 2], [0.2, 0.2, 0.2], 1, 0);

    sui_text([220, -80], MENU_TEXT_MEDIUM, "Horde Size", [1, 1, 1], 1, 0);
    sui_text([220, -65], MENU_TEXT_SMALL, sprintf("%d", cvar("sv_maxai")), [1, 1, 0], 1, 0);
    sui_fill([220, -55], [90, 2], [0.2, 0.2, 0.2], 1, 0);

    sui_text([80, -40], MENU_TEXT_MEDIUM, "Fast Rounds", [1, 1, 1], 1, 0);
    sui_text([80, -25], MENU_TEXT_SMALL, fast_rounds, [1, 1, 0], 1, 0);
    sui_fill([80, -15], [90, 2], [0.2, 0.2, 0.2], 1, 0);

    if (current_selected_bsp == "ndu") {
        sui_text([220, -40], MENU_TEXT_MEDIUM, "Nacht Visuals", [1, 1, 1], 1, 0);
        sui_text([220, -25], MENU_TEXT_SMALL, nacht_visuals, [1, 1, 0], 1, 0);
        sui_fill([220, -15], [90, 2], [0.2, 0.2, 0.2], 1, 0);
    }

    float lobby_delta = menu_loby_countdown - time;
    if (lobby_delta > 0) {
        sui_text([150, 5], MENU_TEXT_SMALL, sprintf("Game Starting In.. %d", lobby_delta), [1, 1, 1], 1, 0);
	    sui_fill([150, 20], [75 * (lobby_delta/6), 6], [0.2, 0.2 * (lobby_delta/6), 0.2 * (lobby_delta/6)], 1, 0);

        if (menu_loby_last != floor(lobby_delta)) {
            Menu_PlaySound(MENU_SND_BEEP);
            menu_loby_last = floor(lobby_delta);
        }
    } else if (lobby_delta < 0 && menu_loby_countdown != 0) {
        localcmd(sprintf("map %s\n", current_selected_bsp));
        Menu_Lobby_StopCountdown();
        current_menu = MENU_MAIN;
    }

	sui_pop_frame();
};'''
s = replace_function(s, "void() Menu_Lobby =", lobby_fn)
lobby.write_text(s, encoding="utf-8")

print("Added first-class Nacht Enhanced activation in map/lobby flow.")
