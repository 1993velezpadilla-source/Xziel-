#!/usr/bin/env python3
"""Visible, bounded Nacht Enhanced atmosphere.

Adds real Enhanced-only fire particles, intermittent electrical sparks and
cold lightning flashes using particle effects already shipped by NZ:P. The
effects are client-side presentation only and do not touch collision, AI,
damage, economy or map entities.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_quakec_nacht_fx_v2.py <quakec-root>")

root = Path(sys.argv[1])
client = root / "source" / "client" / "main.qc"


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


s = client.read_text(encoding="utf-8")

globals_block = r'''
float xziel_nacht_fx_next_fire;
float xziel_nacht_fx_next_spark;
float xziel_nacht_fx_next_lightning;
float xziel_nacht_fx_next_box;
float xziel_nacht_fx_lightning_until;

'''
sig = "void() Xziel_NachtEnhanced_Render ="
pos = s.find(sig)
if pos < 0:
    raise SystemExit("Nacht Enhanced render function missing")
if "float xziel_nacht_fx_next_fire;" not in s:
    s = s[:pos] + globals_block + s[pos:]

render = r'''void() Xziel_NachtEnhanced_Render =
{
    if (mapname != "ndu_enchanted" && (mapname != "ndu" || cvar("xziel_nacht_enhanced") < 0.5))
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

    // Practical lamps.
    dynamiclight_add('1448 2096 72', 92, '0.82 0.48 0.22');
    dynamiclight_add('1032 2656 90', 86, '0.78 0.44 0.20');

    // Cold moon contribution at the breach.
    dynamiclight_add('687 2096 112', 76, '0.18 0.30 0.48');

    // Mystery Box: cold violet supernatural pool centered on the authored box
    // position. Keep it pulsing rather than fullbright so the bunker remains
    // dark and the box reads as a destination from either floor.
    float boxpulse = 0.82 + 0.18 * sin(cltime * 2.4);
    dynamiclight_add('1080 2368 76', 128 * boxpulse, '0.36 0.12 0.62');

    if (xziel_nacht_fx_next_box <= cltime) {
        pointparticles(particleeffectnum("weapons.impact"), '1080 2368 92', '0 0 10', 1);
        xziel_nacht_fx_next_box = cltime + 0.55 + random() * 0.35;
    }

    // Real Enhanced-only particles. Use existing NZ:P effects so there are no
    // new licensing or package-size costs. Bounded to ~20 flame emissions/sec.
    if (xziel_nacht_fx_next_fire <= cltime) {
        pointparticles(particleeffectnum("flames.flame_particle"), '1404 1596 102', '0 0 18', 1);
        pointparticles(particleeffectnum("flames.flame_particle"), '1936 2680 214', '0 0 18', 1);
        pointparticles(particleeffectnum("flames.flame_particle"), '1328 770 84', '0 0 16', 1);
        pointparticles(particleeffectnum("flames.flame_particle"), '2338 2620 88', '0 0 16', 1);
        xziel_nacht_fx_next_fire = cltime + 0.20;
    }

    // Sparse electrical-fault sparks at authored lamp/fault locations.
    if (xziel_nacht_fx_next_spark <= cltime) {
        float spark_pick = floor(random() * 4);
        vector spark_org;
        if (spark_pick == 0) spark_org = '1116 1844 112';
        else if (spark_pick == 1) spark_org = '1448 2096 72';
        else if (spark_pick == 2) spark_org = '1992 2552 68';
        else spark_org = '1919 2189 145';

        pointparticles(particleeffectnum("weapons.impact"), spark_org, '0 0 18', 1);
        dynamiclight_add(spark_org, 72, '0.48 0.62 1.05');
        xziel_nacht_fx_next_spark = cltime + 1.10 + random() * 2.20;
    }

    // Intermittent exterior lightning flash. Very short-lived and infrequent,
    // so it adds horror atmosphere without flattening Nacht's darkness.
    if (xziel_nacht_fx_next_lightning == 0)
        xziel_nacht_fx_next_lightning = cltime + 8 + random() * 10;

    if (cltime >= xziel_nacht_fx_next_lightning) {
        xziel_nacht_fx_lightning_until = cltime + 0.10;
        xziel_nacht_fx_next_lightning = cltime + 13 + random() * 20;
    }

    if (xziel_nacht_fx_lightning_until > cltime) {
        dynamiclight_add('700 2080 280', 430, '0.46 0.58 0.86');
        dynamiclight_add('1320 930 260', 300, '0.35 0.46 0.72');
    }
};'''

s = replace_function(s, sig, render)
client.write_text(s, encoding="utf-8")
print("Applied visible bounded Nacht Enhanced particles/sparks/lightning.")
