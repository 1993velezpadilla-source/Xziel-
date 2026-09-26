#!/usr/bin/env python3
"""Enable Xziel's Nacht golden-reference stress controls in NZ:P QuakeC.

This patch is intentionally benchmark-only. Normal Android builds do not call
it, so release gameplay remains unchanged.

Benchmark controls:
- START ROUND slider: 1..100 (underlying server supports up to 1000).
- HORDE SIZE slider: 2..96 (native engine cap must be compiled high enough).
- BENCHMARK GOD toggle: player damage is ignored for soak/stress runs.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_quakec_nacht_benchmark.py <quakec-root>")

root = Path(sys.argv[1]).resolve()
menu_gset = root / "source" / "menu" / "menu_gset.qc"
menu_main = root / "source" / "menu" / "main.qc"
server_main = root / "source" / "server" / "main.qc"
damage = root / "source" / "server" / "damage.qc"

for path in (menu_gset, menu_main, server_main, damage):
    if not path.is_file():
        raise SystemExit(f"missing QuakeC source: {path}")

# ---------------------------------------------------------------------------
# Expose round 100, horde 96, and a benchmark-only invulnerability toggle.
# ---------------------------------------------------------------------------
text = menu_gset.read_text(encoding="utf-8")

old_buttons = 'string menu_gset_buttons[8] = {"ge_mode", "ge_diff", "ge_rond", "ge_magc", "ge_head", "ge_hord", "ge_frnd", "ge_back"};'
new_buttons = 'string menu_gset_buttons[9] = {"ge_mode", "ge_diff", "ge_rond", "ge_magc", "ge_head", "ge_hord", "ge_frnd", "ge_god", "ge_back"};'
if old_buttons not in text and new_buttons not in text:
    raise SystemExit("Could not find game-settings button table")
text = text.replace(old_buttons, new_buttons, 1)

text = text.replace(
    'Menu_CvarSlider(3, "ge_rond", [0, 50, 10], "sv_startround", true, false, true);',
    'Menu_CvarSlider(3, "ge_rond", [0, 100, 20], "sv_startround", true, false, true);',
    1,
)
text = text.replace(
    'Menu_CvarSlider(6, "ge_hord", [2, 64, 31], "sv_maxai", true, false, false);',
    'Menu_CvarSlider(6, "ge_hord", [2, 96, 47], "sv_maxai", true, false, false);',
    1,
)

god_fn = r'''
void() Menu_GameSettings_ApplyBenchmarkGod =
{
    Menu_PlaySound(MENU_SND_ENTER);

    float enabled = cvar("xziel_benchmark_god");
    enabled = !enabled;
    cvar_set("xziel_benchmark_god", ftos(enabled));
};
'''
fast_fn_end = '''void() Menu_GameSettings_ApplyFastRounds =
{
    Menu_PlaySound(MENU_SND_ENTER);

    float current_fastrounds = cvar("sv_fastrounds");
    current_fastrounds = !current_fastrounds;

    cvar_set("sv_fastrounds", ftos(current_fastrounds));
};
'''
if god_fn.strip() not in text:
    if fast_fn_end not in text:
        raise SystemExit("Could not find FAST ROUNDS toggle function")
    text = text.replace(fast_fn_end, fast_fn_end + god_fn, 1)

god_ui = r'''
    // Benchmark God Mode
    string benchmark_god_string = "";
    Menu_Button(8, "ge_god", "BENCHMARK GOD", "Invulnerability for high-round engine stress testing.") ? Menu_GameSettings_ApplyBenchmarkGod() : 0;
    if (cvar("xziel_benchmark_god")) {
        benchmark_god_string = "ENABLED";
    } else {
        benchmark_god_string = "DISABLED";
    }
    Menu_DrawOptionValue(8, benchmark_god_string);

'''
back_anchor = '    Menu_Button(-1, "ge_back", "BACK", "Return to Pre-Game Menu.") ? current_menu = MENU_LOBBY : 0;'
if god_ui.strip() not in text:
    if back_anchor not in text:
        raise SystemExit("Could not find Game Settings BACK button")
    text = text.replace(back_anchor, god_ui + back_anchor, 1)

menu_gset.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# Register the benchmark cvar on both menu and server VMs.
# ---------------------------------------------------------------------------
for path in (menu_main, server_main):
    text = path.read_text(encoding="utf-8")
    anchor = '\tautocvar(sv_fastrounds, 0);'
    addition = anchor + '\n\tautocvar(xziel_benchmark_god, 0);'
    if "autocvar(xziel_benchmark_god, 0);" not in text:
        if anchor not in text:
            raise SystemExit(f"Could not find sv_fastrounds autocvar in {path}")
        text = text.replace(anchor, addition, 1)
    path.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# God mode is deliberately implemented in gameplay code rather than relying on
# a console being reachable on a phone. It is benchmark-only because this
# patch itself is benchmark-only.
# ---------------------------------------------------------------------------
text = damage.read_text(encoding="utf-8")
anchor = '''void(entity victim, entity attacker, float damage, float d_style) DamageHandler = {
'''
addition = anchor + '''\tif (victim.classname == "player" && cvar("xziel_benchmark_god") >= 0.5)
\t\treturn;

'''
if 'cvar("xziel_benchmark_god") >= 0.5' not in text:
    if anchor not in text:
        raise SystemExit("Could not find DamageHandler")
    text = text.replace(anchor, addition, 1)
damage.write_text(text, encoding="utf-8")

print("Enabled Xziel Nacht benchmark controls: round<=100, horde<=96, benchmark god mode.")
