#!/usr/bin/env python3
"""Wire original generated Enchanted cues as the safe default audio lane."""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_quakec_nacht_original_audio.py <quakec-root>")

root = Path(sys.argv[1])
main = root / "source/server/main.qc"
s = main.read_text(encoding="utf-8")

anchor = '''    xziel_waw_round1_ready = false;
    xziel_waw_gameover_ready = false;
    xziel_waw_chalk_ready = false;
    xziel_waw_roundover_ready = false;
'''
insert = anchor + '''
    // Original Xziel cues are always available in the Enchanted practice
    // package. Optional local WaW files may override them for private A/B
    // reference, but the public-safe path never depends on ripped audio.
    precache_sound("sounds/xziel/enchant/round_omen.wav");
    precache_sound("sounds/xziel/enchant/mystery_hum.wav");
    precache_sound("sounds/xziel/enchant/gameover_guitar.wav");
'''
if 'precache_sound("sounds/xziel/enchant/round_omen.wav")' not in s:
    if anchor not in s:
        raise SystemExit("WaW audio init anchor missing")
    s = s.replace(anchor, insert, 1)

# Add a subtle positional magical bed at the actual Nacht Mystery Box origin.
ambient_anchor = '    xziel_waw_roundover_path = "sounds/xziel/waw/waw_round_over.wav";
'
if 'mystery_hum.wav", 0.10' not in s:
    if ambient_anchor not in s:
        raise SystemExit("WaW path anchor missing")
    s = s.replace(
        ambient_anchor,
        ambient_anchor + '''
    ambientsound('1080 2368 72', "sounds/xziel/enchant/mystery_hum.wav", 0.10, ATTN_STATIC);
''',
        1,
    )

# Round 1: original omen by default, exact WaW cue only when explicitly
# imported by the developer.
old = '''				string splash_tune = "sounds/rounds/splash.wav";
				splash_tune = Gamemode_GetSplashTune(splash_tune);
				if ((mapname == "ndu_enchanted" || (mapname == "ndu" && cvar("xziel_nacht_enhanced") >= 0.5)) && xziel_waw_round1_ready)
					splash_tune = xziel_waw_round1_path;'''
new = '''				string splash_tune = "sounds/rounds/splash.wav";
				splash_tune = Gamemode_GetSplashTune(splash_tune);
				if (mapname == "ndu_enchanted")
					splash_tune = "sounds/xziel/enchant/round_omen.wav";
				if ((mapname == "ndu_enchanted" || (mapname == "ndu" && cvar("xziel_nacht_enhanced") >= 0.5)) && xziel_waw_round1_ready)
					splash_tune = xziel_waw_round1_path;'''
if 'splash_tune = "sounds/xziel/enchant/round_omen.wav";' not in s:
    if old not in s:
        raise SystemExit("round splash override anchor missing")
    s = s.replace(old, new, 1)
main.write_text(s, encoding="utf-8")

damage = root / "source/server/damage.qc"
s = damage.read_text(encoding="utf-8")
old = '''		string endgame_tune = "sounds/music/end.wav";
		if ((mapname == "ndu_enchanted" || (mapname == "ndu" && cvar("xziel_nacht_enhanced") >= 0.5)) && xziel_waw_gameover_ready)
			endgame_tune = xziel_waw_gameover_path;'''
new = '''		string endgame_tune = "sounds/music/end.wav";
		if (mapname == "ndu_enchanted")
			endgame_tune = "sounds/xziel/enchant/gameover_guitar.wav";
		if ((mapname == "ndu_enchanted" || (mapname == "ndu" && cvar("xziel_nacht_enhanced") >= 0.5)) && xziel_waw_gameover_ready)
			endgame_tune = xziel_waw_gameover_path;'''
if 'endgame_tune = "sounds/xziel/enchant/gameover_guitar.wav";' not in s:
    if old not in s:
        raise SystemExit("game-over audio override anchor missing")
    s = s.replace(old, new, 1)
damage.write_text(s, encoding="utf-8")

print("Wired original Enchanted audio cues with optional private WaW overrides.")
