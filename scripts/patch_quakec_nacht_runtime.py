#!/usr/bin/env python3
"""Nacht Enhanced runtime atmosphere: spatial audio + bounded client lights.

This is deliberately presentation-only and runs only on ndu_enchanted.
zombie rules, doors, windows, purchases, scoring or navigation.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_quakec_nacht_runtime.py <quakec-root>")

root = Path(sys.argv[1])
server = root / "source" / "server" / "main.qc"
client = root / "source" / "client" / "main.qc"

# ---------------------------------------------------------------------------
# SERVER: use stock NZ:P audio already shipped in the APK.
# ---------------------------------------------------------------------------
s = server.read_text(encoding="utf-8")

runtime = r'''
// ---------------------------------------------------------------------------
// Xziel Nacht Enhanced presentation runtime.
// Stock NZ:P sounds are reused here so the first Enhanced test does not add
// unlicensed audio to the APK.  Commercial-safe replacements can be swapped
// in later without touching gameplay.
// ---------------------------------------------------------------------------
void() Xziel_NachtEnhanced_AmbientOneShotThink =
{
    if (mapname != "ndu_enchanted") {
        remove(self);
        return;
    }

    if (self.impulse == 1)
        sound(self, CHAN_VOICE, "sounds/misc/electric_bolt.wav", 0.30, ATTN_STATIC);
    else if (self.impulse == 2)
        sound(self, CHAN_VOICE, "sounds/misc/wood_door.wav", 0.22, ATTN_STATIC);
    else if (self.impulse == 3)
        sound(self, CHAN_VOICE, "sounds/misc/debris.wav", 0.18, ATTN_STATIC);

    self.nextthink = time + self.wait + random() * self.speed;
};

void(vector org, float style, float base_wait, float jitter) Xziel_NachtEnhanced_SpawnOneShot =
{
    entity emitter = spawn();
    emitter.classname = "xziel_nacht_enhanced_audio";
    emitter.impulse = style;
    emitter.wait = base_wait;
    emitter.speed = jitter;
    emitter.solid = SOLID_NOT;
    emitter.movetype = MOVETYPE_NONE;
    setorigin(emitter, org);
    emitter.think = Xziel_NachtEnhanced_AmbientOneShotThink;
    emitter.nextthink = time + 1 + random() * jitter;
};

void() Xziel_NachtEnhanced_Init =
{
    if (mapname != "ndu_enchanted")
        return;

    // Explicitly precache everything this optional layer can emit.
    precache_sound("sounds/ambience/wind2.wav");
    precache_sound("sounds/ambience/echoes.wav");
    precache_sound("sounds/misc/electric_bolt.wav");
    precache_sound("sounds/misc/wood_door.wav");
    precache_sound("sounds/misc/debris.wav");

    // Broken-window / exterior wind beds.  Low gain + positional attenuation
    // keeps zombie localization and weapon transients readable.
    ambientsound('992 928 112', "sounds/ambience/wind2.wav", 0.12, ATTN_STATIC);
    ambientsound('1384 784 112', "sounds/ambience/wind2.wav", 0.12, ATTN_STATIC);
    ambientsound('992 2164 112', "sounds/ambience/wind2.wav", 0.10, ATTN_STATIC);
    ambientsound('2128 2712 256', "sounds/ambience/wind2.wav", 0.11, ATTN_STATIC);
    ambientsound('1456 2824 256', "sounds/ambience/wind2.wav", 0.11, ATTN_STATIC);

    // Sparse electrical faults near real Nacht lamp positions.
    Xziel_NachtEnhanced_SpawnOneShot('1116 1844 112', 1, 8, 14);
    Xziel_NachtEnhanced_SpawnOneShot('1448 2096 64', 1, 10, 16);
    Xziel_NachtEnhanced_SpawnOneShot('1992 2552 68', 1, 9, 15);
    Xziel_NachtEnhanced_SpawnOneShot('1919 2189 145', 1, 12, 18);

    // Building movement and debris: intentionally slow, irregular horror bed.
    Xziel_NachtEnhanced_SpawnOneShot('1280 1824 192', 2, 17, 23);
    Xziel_NachtEnhanced_SpawnOneShot('1524 2328 88', 2, 21, 27);
    Xziel_NachtEnhanced_SpawnOneShot('1832 2680 88', 2, 20, 28);
    Xziel_NachtEnhanced_SpawnOneShot('1357 1671 328', 3, 18, 26);
    Xziel_NachtEnhanced_SpawnOneShot('2061 2559 328', 3, 23, 31);
};

'''

anchor = "float useprint_revive;\n\n//called when map loaded"
if "Xziel_NachtEnhanced_Init" not in s:
    if anchor not in s:
        raise SystemExit("server insertion anchor missing")
    s = s.replace(anchor, runtime + "\n" + anchor, 1)

call_anchor = "\tGamemode_Init();\n}"
if "\tXziel_NachtEnhanced_Init();\n\n\tGamemode_Init();" not in s:
    if call_anchor not in s:
        raise SystemExit("worldspawn call anchor missing")
    s = s.replace(call_anchor, "\tXziel_NachtEnhanced_Init();\n\n" + call_anchor, 1)

server.write_text(s, encoding="utf-8")

# ---------------------------------------------------------------------------
# CLIENT: a tiny fixed-budget lighting pass around existing Nacht fire/lamp
# locations.  Seven dlights max; no allocations, entity scans or BSP edits.
# ---------------------------------------------------------------------------
s = client.read_text(encoding="utf-8")

render = r'''
void() Xziel_NachtEnhanced_Render =
{
    if (mapname != "ndu_enchanted")
        return;

    // Small independent phase offsets prevent synchronized "breathing".
    float f0 = 0.92 + 0.08 * sin(cltime * 8.2);
    float f1 = 0.90 + 0.10 * sin(cltime * 7.1 + 1.7);
    float f2 = 0.93 + 0.07 * sin(cltime * 9.4 + 3.1);
    float f3 = 0.91 + 0.09 * sin(cltime * 6.7 + 4.6);

    // Existing fire clusters: warm transient bounce.
    dynamiclight_add('1404 1596 108', 122 * f0, '1.15 0.40 0.10');
    dynamiclight_add('1936 2680 222', 118 * f1, '1.12 0.36 0.09');
    dynamiclight_add('1328 770 90', 104 * f2, '1.08 0.32 0.08');
    dynamiclight_add('2338 2620 94', 112 * f3, '1.10 0.34 0.08');

    // Practical lamps: restrained warmer fill rather than fullbright sprites.
    dynamiclight_add('1448 2096 72', 92, '0.82 0.48 0.22');
    dynamiclight_add('1032 2656 90', 86, '0.78 0.44 0.20');

    // A cold exterior contribution near the first-floor breach helps separate
    // moonlit openings from the warm interior without changing visibility.
    dynamiclight_add('687 2096 112', 76, '0.18 0.30 0.48');
};

'''

anchor = "// CALLED EVERY CLIENT RENDER FRAME"
if "void() Xziel_NachtEnhanced_Render" not in s:
    if anchor not in s:
        raise SystemExit("client render insertion anchor missing")
    s = s.replace(anchor, render + "\n" + anchor, 1)

call_anchor = "\t//does what you think it does\n\trenderscene();"
if "\tXziel_NachtEnhanced_Render();" not in s:
    if call_anchor not in s:
        raise SystemExit("renderscene anchor missing")
    s = s.replace(call_anchor, "\tXziel_NachtEnhanced_Render();\n\n" + call_anchor, 1)

client.write_text(s, encoding="utf-8")
print("Applied Nacht Enhanced spatial audio and bounded dynamic-light pass.")
