#!/usr/bin/env python3
"""Wire classic WaW Zombies audio hooks + richer Nacht game-over stats.

Copyrighted WaW audio is NOT embedded by this patch. Runtime only uses the
classic paths when authorized local files were packaged; otherwise NZ:P
fallback audio remains active.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_quakec_waw_legacy_audio.py <quakec-root>")

root = Path(sys.argv[1])

# ---------------------------------------------------------------------------
# Shared server globals.
# ---------------------------------------------------------------------------
defs = root / "source/server/defs/custom.qc"
s = defs.read_text(encoding="utf-8")
anchor = "float music_override;\n"
payload = r'''
// Xziel optional classic WaW Zombies audio slots.
// Audio bytes are local-import only; these flags are set during worldspawn
// after checking the virtual filesystem.
float xziel_waw_round1_ready;
float xziel_waw_gameover_ready;
float xziel_waw_chalk_ready;
float xziel_waw_roundover_ready;
string xziel_waw_round1_path;
string xziel_waw_gameover_path;
string xziel_waw_chalk_path;
string xziel_waw_roundover_path;

'''
if "xziel_waw_round1_ready" not in s:
    if anchor not in s:
        raise SystemExit("server defs anchor missing")
    s = s.replace(anchor, anchor + payload, 1)
defs.write_text(s, encoding="utf-8")

# ---------------------------------------------------------------------------
# Worldspawn: detect and precache only files actually packaged.
# ---------------------------------------------------------------------------
main = root / "source/server/main.qc"
s = main.read_text(encoding="utf-8")
anchor = "float useprint_revive;\n"
helper = r'''
float(string path) Xziel_OptionalSoundExists =
{
    float h = fopen(path, FILE_READ);
    if (h == -1)
        return false;
    fclose(h);
    return true;
};

void() Xziel_WaWLegacyAudio_Init =
{
    xziel_waw_round1_ready = false;
    xziel_waw_gameover_ready = false;
    xziel_waw_chalk_ready = false;
    xziel_waw_roundover_ready = false;

    if (mapname != "ndu" || cvar("xziel_nacht_enhanced") < 0.5)
        return;

    xziel_waw_round1_path = "sounds/xziel/waw/waw_round_start_laugh.wav";
    xziel_waw_gameover_path = "sounds/xziel/waw/waw_game_over.wav";
    xziel_waw_chalk_path = "sounds/xziel/waw/waw_chalk.wav";
    xziel_waw_roundover_path = "sounds/xziel/waw/waw_round_over.wav";

    if (Xziel_OptionalSoundExists(xziel_waw_round1_path)) {
        precache_sound(xziel_waw_round1_path);
        xziel_waw_round1_ready = true;
    }
    if (Xziel_OptionalSoundExists(xziel_waw_gameover_path)) {
        precache_sound(xziel_waw_gameover_path);
        xziel_waw_gameover_ready = true;
    }
    if (Xziel_OptionalSoundExists(xziel_waw_chalk_path)) {
        precache_sound(xziel_waw_chalk_path);
        xziel_waw_chalk_ready = true;
    }
    if (Xziel_OptionalSoundExists(xziel_waw_roundover_path)) {
        precache_sound(xziel_waw_roundover_path);
        xziel_waw_roundover_ready = true;
    }
};

'''
if "void() Xziel_WaWLegacyAudio_Init" not in s:
    if anchor not in s:
        raise SystemExit("main audio helper anchor missing")
    s = s.replace(anchor, helper + "\n" + anchor, 1)

# Run before the existing Nacht ambience initializer / Gamemode init.
call_anchor = "\tXziel_NachtEnhanced_Init();\n\n\tGamemode_Init();"
if "\tXziel_WaWLegacyAudio_Init();\n" not in s:
    if call_anchor in s:
        s = s.replace(call_anchor, "\tXziel_WaWLegacyAudio_Init();\n\tXziel_NachtEnhanced_Init();\n\n\tGamemode_Init();", 1)
    else:
        fallback = "\tGamemode_Init();"
        if fallback not in s:
            raise SystemExit("worldspawn init call anchor missing")
        s = s.replace(fallback, "\tXziel_WaWLegacyAudio_Init();\n\n" + fallback, 1)

# Replace the stock splash cue at the exact initial-round presentation point.
# This avoids starting two SOUND_TYPE_MUSIC_ROUND cues on the same frame, where
# the stock splash could immediately stomp the optional classic laugh.
splash_needle = r'''\t\t\tif (cvar("sv_startround") == 0) {
\t\t\t\tstring splash_tune = "sounds/rounds/splash.wav";
\t\t\t\tsplash_tune = Gamemode_GetSplashTune(splash_tune);
\t\t\t\tRounds_PlayTransition(splash_tune);
\t\t\t}'''
splash_repl = r'''\t\t\tif (cvar("sv_startround") == 0) {
\t\t\t\tstring splash_tune = "sounds/rounds/splash.wav";
\t\t\t\tsplash_tune = Gamemode_GetSplashTune(splash_tune);
\t\t\t\tif (mapname == "ndu" && cvar("xziel_nacht_enhanced") >= 0.5 && xziel_waw_round1_ready)
\t\t\t\t\tsplash_tune = xziel_waw_round1_path;
\t\t\t\tRounds_PlayTransition(splash_tune);
\t\t\t}'''
if "splash_tune = xziel_waw_round1_path;" not in s:
    if splash_needle not in s:
        raise SystemExit("Round-1 splash audio anchor missing")
    s = s.replace(splash_needle, splash_repl, 1)

main.write_text(s, encoding="utf-8")

# ---------------------------------------------------------------------------
# Round transition accents: optional classic round-over and chalk sounds.
# - exact classic Round-1 laugh can accompany the existing white->red tally.
# - optional classic round-over and chalk accents.
# ---------------------------------------------------------------------------
rounds = root / "source/server/rounds.qc"
s = rounds.read_text(encoding="utf-8")

needle = '''\t} else {
\t\tend_round_tune = "sounds/rounds/eround.wav";
\t\tend_round_tune = Gamemode_GetEndRoundTune(end_round_tune);
\t}

\tif (cvar("sv_fastrounds") == 0)
\t\tRounds_PlayTransition(end_round_tune);'''
repl = '''\t} else {
\t\tend_round_tune = "sounds/rounds/eround.wav";
\t\tend_round_tune = Gamemode_GetEndRoundTune(end_round_tune);
\t}

\tif (mapname == "ndu" && cvar("xziel_nacht_enhanced") >= 0.5 && xziel_waw_roundover_ready)
\t\tend_round_tune = xziel_waw_roundover_path;

\tif (cvar("sv_fastrounds") == 0)
\t\tRounds_PlayTransition(end_round_tune);'''
if "xziel_waw_roundover_ready" not in s:
    if needle not in s:
        raise SystemExit("EndRound audio anchor missing")
    s = s.replace(needle, repl, 1)

needle = "\trounds = rounds + 1;\n"
repl = '''\trounds = rounds + 1;

\t// Optional original chalk accent for subsequent round transitions.
\tif (rounds > 1 && mapname == "ndu" && cvar("xziel_nacht_enhanced") >= 0.5 && xziel_waw_chalk_ready)
\t\tSound_PlaySound(world, xziel_waw_chalk_path, SOUND_TYPE_MUSIC_ROUND, SOUND_PRIORITY_PLAYALWAYS);
'''
if "Optional original chalk accent" not in s:
    if needle not in s:
        raise SystemExit("round increment anchor missing")
    s = s.replace(needle, repl, 1)

rounds.write_text(s, encoding="utf-8")

# ---------------------------------------------------------------------------
# End game: swap the stock NZ:P end sound only when local classic audio exists.
# ---------------------------------------------------------------------------
damage = root / "source/server/damage.qc"
s = damage.read_text(encoding="utf-8")
needle = '''\tif (in_endgame_sequence == false) {
\t\tRounds_PlayTransition("sounds/music/end.wav");
\t\tNotifyGameEnd();
\t}'''
repl = '''\tif (in_endgame_sequence == false) {
\t\tstring endgame_tune = "sounds/music/end.wav";
\t\tif (mapname == "ndu" && cvar("xziel_nacht_enhanced") >= 0.5 && xziel_waw_gameover_ready)
\t\t\tendgame_tune = xziel_waw_gameover_path;
\t\tRounds_PlayTransition(endgame_tune);
\t\tNotifyGameEnd();
\t}'''
if "xziel_waw_gameover_ready" not in s:
    if needle not in s:
        raise SystemExit("damage endgame audio anchor missing")
    s = s.replace(needle, repl, 1)
damage.write_text(s, encoding="utf-8")

# ---------------------------------------------------------------------------
# Client game-over presentation: rounds survived + core Zombies statistics.
# ---------------------------------------------------------------------------
hud = root / "source/client/hud.qc"
s = hud.read_text(encoding="utf-8")
old = '''void() HUD_Endgame = {
\tstring game_over = "GAME OVER";
\tstring survive;
\tstring round;

\tif (rounds == 1)
\t\tround = " Round";
\telse
\t\tround = " Rounds";

\tsurvive = strcat("You Survived ", ftos(rounds), round);

\tfloat game_over_width = getTextWidth(game_over, 24);
\tHUD_DrawStringWithBackdrop([g_width/2 - game_over_width/2, 100], game_over, [24, 24], [1, 1, 1], 1, 0);

\tfloat survive_width = getTextWidth(survive, 18);
\tHUD_DrawStringWithBackdrop([g_width/2 - survive_width/2, 135], survive, [18, 18], [1, 1, 1], 1, 0);
}'''
new = '''void() HUD_Endgame = {
\tstring game_over = "GAME OVER";
\tstring survive;
\tstring round;

\tif (rounds == 1)
\t\tround = " Round";
\telse
\t\tround = " Rounds";

\tsurvive = strcat("You Survived ", ftos(rounds), round);

\tfloat game_over_width = getTextWidth(game_over, 24);
\tHUD_DrawStringWithBackdrop([g_width/2 - game_over_width/2, 88], game_over, [24, 24], [1, 1, 1], 1, 0);

\tfloat survive_width = getTextWidth(survive, 18);
\tHUD_DrawStringWithBackdrop([g_width/2 - survive_width/2, 123], survive, [18, 18], [1, 1, 1], 1, 0);

\tif (mapname == "ndu" && cvar("xziel_nacht_enhanced") >= 0.5) {
\t\tentity me = findfloat(world, playernum, getstatf(STAT_PLAYERNUM));
\t\tif (me != world) {
\t\t\tstring stats1 = sprintf("KILLS  %d     HEADSHOTS  %d", me.kills, me.headshots);
\t\t\tstring stats2 = sprintf("DOWNS  %d     REVIVES  %d", me.downs, me.revives);
\t\t\tstring stats3 = sprintf("SCORE  %d", getstatf(STAT_TOTALSCORE));
\t\t\tfloat w1 = getTextWidth(stats1, 12);
\t\t\tfloat w2 = getTextWidth(stats2, 12);
\t\t\tfloat w3 = getTextWidth(stats3, 12);
\t\t\tHUD_DrawStringWithBackdrop([g_width/2 - w1/2, 160], stats1, [12, 12], [0.85, 0.85, 0.85], 1, 0);
\t\t\tHUD_DrawStringWithBackdrop([g_width/2 - w2/2, 178], stats2, [12, 12], [0.85, 0.85, 0.85], 1, 0);
\t\t\tHUD_DrawStringWithBackdrop([g_width/2 - w3/2, 196], stats3, [12, 12], [0.65, 0.15, 0.12], 1, 0);
\t\t}
\t}
}'''
if "KILLS  %d     HEADSHOTS" not in s:
    if old not in s:
        raise SystemExit("HUD_Endgame function anchor missing")
    s = s.replace(old, new, 1)
hud.write_text(s, encoding="utf-8")

print("Wired optional classic WaW audio slots and Nacht end-game statistics.")
