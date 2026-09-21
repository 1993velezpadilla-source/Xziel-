#!/usr/bin/env python3
"""Keep stock Nacht and the Xziel Enchanted Lab as two separate maps.

There is intentionally no Classic/Enchanted toggle. The stock `ndu` entry
stays stock. The separate `ndu_enchanted` user-map entry always opts into the
Xziel laboratory presentation/runtime layer.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_quakec_nacht_activation.py <quakec-root>")

root = Path(sys.argv[1])
maps = root / "source" / "menu" / "menu_maps.qc"


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
                if end < len(src) and src[end] == ";":
                    end += 1
                break
    if end < 0:
        raise SystemExit("Could not find function end: " + signature)
    return src[:start] + replacement + src[end:]


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

    // Two-map architecture:
    // - ndu            = untouched stock comparison map
    // - ndu_enchanted  = Xziel development laboratory
    if (bsp_name == "ndu") {
        cvar_set("xziel_nacht_enhanced", "0");
    }

    if (bsp_name == "ndu_enchanted") {
        cvar_set("xziel_nacht_enhanced", "1");
        cvar_set("xziel_modern_zombies", "1");
    }

    current_menu = MENU_LOBBY;
};'''

s = replace_function(s, "void(string bsp_name) Menu_Maps_LoadMap =", load_map)
maps.write_text(s, encoding="utf-8")
print("Separated stock ndu and ndu_enchanted; no lobby/version toggle.")
