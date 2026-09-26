#!/usr/bin/env python3
"""Add a generic post-burst cooldown hook to current NZ:P QuakeC.

The stock burst scheduler correctly spaces shots inside a burst, but once the
last shot fires it has no separate inter-burst tail. XZIEL weapons such as RK5
and Pharo need distinct intra-burst and overall RPMs. This patch adds the
primitive only; existing NZ:P weapons keep a zero tail and are unchanged.
"""

from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_quakec_xziel_burst_timing.py <quakec-root>")

root = Path(sys.argv[1])
stats_path = root / "source/shared/weapon_stats.qc"
core_path = root / "source/server/weapons/weapon_core.qc"

stats = stats_path.read_text(encoding="utf-8")
core = core_path.read_text(encoding="utf-8")

if "WepDef_GetWeaponBurstTailDelay" not in stats:
    anchor = """float(float weapon) WepDef_GetWeaponBurstCount =
{
\tswitch(weapon) {
\t\tcase W_RAYMK2:
\t\tcase W_PORTERMK2:
\t\t\treturn 3;
\t}

\treturn 0;
}
"""
    if anchor not in stats:
        raise SystemExit("Could not find current WepDef_GetWeaponBurstCount body")

    block = anchor + """
//
// WepDef_GetWeaponBurstTailDelay(weapon)
// Time from the final shot of a burst until another burst may begin.
// Zero preserves stock NZ:P behavior. XZIEL weapon patches add explicit cases.
//
float(float weapon) WepDef_GetWeaponBurstTailDelay =
{
\tswitch(weapon) {
\t\tdefault:
\t\t\treturn 0;
\t}

\treturn 0;
}
"""
    stats = stats.replace(anchor, block, 1)

marker = "XZIEL_BURST_TAIL_COOLDOWN"
if marker not in core:
    anchor = """\t\t\t} else {
\t\t\t\t// Final shot
\t\t\t\tself.weapon_burst_count = 0;
\t\t\t\tSet_W_Frame(startframe, endframe, delay, 0, FIRE, SUB_Null, modelname, FALSE, side, false);
\t\t\t\tself.switch_delay = self.knife_delay = self.sprint_delay = self.grenade_delay = delay + time;
\t\t\t}
"""
    if anchor not in core:
        raise SystemExit("Could not find current final-burst branch")

    replacement = """\t\t\t} else {
\t\t\t\t// Final shot
\t\t\t\tself.weapon_burst_count = 0;
\t\t\t\tSet_W_Frame(startframe, endframe, delay, 0, FIRE, SUB_Null, modelname, FALSE, side, false);
\t\t\t\tself.switch_delay = self.knife_delay = self.sprint_delay = self.grenade_delay = delay + time;

\t\t\t\t// XZIEL_BURST_TAIL_COOLDOWN
\t\t\t\t// Some burst weapons have a faster cyclic rate inside the burst
\t\t\t\t// than their average sustained RPM. Enforce only the extra
\t\t\t\t// post-burst firing lock; stock weapons return zero here.
\t\t\t\tfloat burst_tail_delay = WepDef_GetWeaponBurstTailDelay(self.weapon);
\t\t\t\tif (burst_tail_delay > 0) {
\t\t\t\t\tif (side == S_RIGHT)
\t\t\t\t\t\tself.fire_delay = time + burst_tail_delay;
\t\t\t\t\telse if (side == S_LEFT)
\t\t\t\t\t\tself.fire_delay2 = time + burst_tail_delay;
\t\t\t\t}
\t\t\t}
"""
    core = core.replace(anchor, replacement, 1)

if stats.count("WepDef_GetWeaponBurstTailDelay") != 3:
    # comment + declaration/definition name + core-independent textual comment
    # can vary upstream, so use structural checks below instead of accepting
    # silent duplicate insertions.
    if stats.count("float(float weapon) WepDef_GetWeaponBurstTailDelay =") != 1:
        raise SystemExit("Burst-tail helper injection count mismatch")

if core.count(marker) != 1:
    raise SystemExit("Burst-tail core integration count mismatch")
if core.count("WepDef_GetWeaponBurstTailDelay(self.weapon)") != 1:
    raise SystemExit("Burst-tail helper call count mismatch")

stats_path.write_text(stats, encoding="utf-8")
core_path.write_text(core, encoding="utf-8")

print("Applied generic XZIEL post-burst cooldown support.")
