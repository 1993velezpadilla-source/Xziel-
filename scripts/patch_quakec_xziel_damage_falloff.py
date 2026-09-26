#!/usr/bin/env python3
"""Add a server-authoritative distance-damage hook to NZ:P QuakeC.

Stock NZ:P weapons remain byte-for-byte equivalent in damage behavior because
the XZIEL scale helper returns 1.0 for every existing weapon. Future XZIEL
weapon IDs can add verified BO3 Zombies range curves without rewriting FireTrace.
"""

from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_quakec_xziel_damage_falloff.py <quakec-root>")

root = Path(sys.argv[1])
core_path = root / "source/server/weapons/weapon_core.qc"
core = core_path.read_text(encoding="utf-8")

marker = "XZIEL_DAMAGE_FALLOFF_HOOK"
helper_name = "XZIEL_WeaponDamageFalloffScale"

if helper_name not in core:
    anchor = "void (float shotcount, float sprd, float Damage, float side) FireTrace =\n"
    if anchor not in core:
        raise SystemExit("Could not find FireTrace declaration")

    helper = """//
// XZIEL_WeaponDamageFalloffScale(weapon, distance_units)
// Server-authoritative distance damage hook.
// 1.0 preserves every stock NZ:P weapon. Verified XZIEL weapon IDs add cases.
//
float(float weapon, float distance_units) XZIEL_WeaponDamageFalloffScale =
{
    return 1;
};

"""
    core = core.replace(anchor, helper + anchor, 1)

if marker not in core:
    anchor = """\t\t\tif (trace_fraction != 1.0)
\t\t\t\tTraceAttack (Damage, dir, trace_endpos, trace_plane_normal, trace_ent, side);
"""
    if anchor not in core:
        raise SystemExit("Could not find FireTrace damage call")

    replacement = """\t\t\tif (trace_fraction != 1.0) {
\t\t\t\t// XZIEL_DAMAGE_FALLOFF_HOOK
\t\t\t\t// Measure from the original muzzle position so penetration does
\t\t\t\t// not reset the distance curve for later hits.
\t\t\t\tfloat xziel_damage_scale = XZIEL_WeaponDamageFalloffScale(
\t\t\t\t\tself.weapon, vlen(trace_endpos - src));
\t\t\t\tTraceAttack (Damage * xziel_damage_scale, dir, trace_endpos, trace_plane_normal, trace_ent, side);
\t\t\t}
"""
    core = core.replace(anchor, replacement, 1)

if core.count(marker) != 1:
    raise SystemExit("XZIEL damage falloff hook count mismatch")
if core.count("float(float weapon, float distance_units) XZIEL_WeaponDamageFalloffScale =") != 1:
    raise SystemExit("XZIEL damage falloff helper count mismatch")
if core.count("Damage * xziel_damage_scale") != 1:
    raise SystemExit("XZIEL damage scaling call count mismatch")

core_path.write_text(core, encoding="utf-8")
print("Applied generic XZIEL distance-damage hook (stock scale = 1.0).")
