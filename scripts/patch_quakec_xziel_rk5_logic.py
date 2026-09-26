#!/usr/bin/env python3
"""Wire verified RK5 gameplay-core behavior into reserved NZ:P custom slot 70.

Intentionally excluded: models, sounds, recoil, spread, penetration tuning,
animations, Pack-a-Punch, Mystery Box spawning, and wall-buy exposure.
"""

from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_quakec_xziel_rk5_logic.py <quakec-root>")

root = Path(sys.argv[1])
defs_path = root / "source/shared/shared_defs.qc"
stats_path = root / "source/shared/weapon_stats.qc"
core_path = root / "source/server/weapons/weapon_core.qc"

defs = defs_path.read_text(encoding="utf-8")
stats = stats_path.read_text(encoding="utf-8")
core = core_path.read_text(encoding="utf-8")

if "W_XZ_RK5" not in defs:
    anchor = "#define W_CUSTOM4 \t   73\n"
    if anchor not in defs:
        raise SystemExit("Could not find reserved custom weapon slots")
    defs = defs.replace(
        anchor,
        anchor
        + "\n// XZIEL logic-only binding. Do not expose until native gate is ready.\n"
        + "#define W_XZ_RK5       W_CUSTOM1\n",
        1,
    )

def inject_switch_case(text: str, signature: str, marker: str, case_text: str) -> str:
    if marker in text:
        return text
    start = text.find(signature)
    if start < 0:
        raise SystemExit(f"Could not find function: {signature}")
    sw = text.find("switch", start)
    brace = text.find("{", sw)
    if sw < 0 or brace < 0:
        raise SystemExit(f"Could not find switch body for: {signature}")
    return text[: brace + 1] + "\n" + case_text + text[brace + 1 :]

stats = inject_switch_case(
    stats,
    "string(float wep, float weapon_tier) GetWeaponName =",
    "XZIEL_RK5_NAME",
    '\t\t// XZIEL_RK5_NAME\n\t\tcase W_XZ_RK5:\n\t\t\tweapon_name = "RK5";\n\t\t\tbreak;\n',
)
stats = inject_switch_case(
    stats,
    "float(float wep) GetFiretype =",
    "XZIEL_RK5_FIRETYPE",
    "\t\t// XZIEL_RK5_FIRETYPE\n\t\tcase W_XZ_RK5:\n\t\t\treturn FIRETYPE_SEMIAUTO;\n",
)
stats = inject_switch_case(
    stats,
    "float(float wep) getWeaponMag =",
    "XZIEL_RK5_MAG",
    "\t\t// XZIEL_RK5_MAG\n\t\tcase W_XZ_RK5:\n\t\t\treturn 15;\n",
)
stats = inject_switch_case(
    stats,
    "float(float wep) getWeaponAmmo =",
    "XZIEL_RK5_RESERVE",
    "\t\t// XZIEL_RK5_RESERVE\n\t\tcase W_XZ_RK5:\n\t\t\tweapon_ammo = 120;\n\t\t\tbreak;\n",
)
stats = inject_switch_case(
    stats,
    "float(float wep, float weapon_tier) getWeaponDamage =",
    "XZIEL_RK5_DAMAGE",
    "\t\t// XZIEL_RK5_DAMAGE\n\t\tcase W_XZ_RK5:\n\t\t\tweapon_damage = 100;\n\t\t\tbreak;\n",
)
stats = inject_switch_case(
    stats,
    "float(float wep, float current_perks, float type) getWeaponMultiplier =",
    "XZIEL_RK5_HITLOC",
    """\t\t// XZIEL_RK5_HITLOC
\t\tcase W_XZ_RK5:
\t\t\tswitch (type)
\t\t\t{
\t\t\t\tcase HEAD_X: multiplier = 2; break;
\t\t\t\tcase UPPER_TORSO_X: multiplier = 1; break;
\t\t\t\tcase LOWER_TORSO_X: multiplier = 1; break;
\t\t\t\tcase LIMBS_X: multiplier = 1; break;
\t\t\t}
\t\t\tbreak;
""",
)
stats = inject_switch_case(
    stats,
    "float(float wep, float delaytype) getWeaponDelay =",
    "XZIEL_RK5_DELAYS",
    """\t\t// XZIEL_RK5_DELAYS
\t\tcase W_XZ_RK5:
\t\t\tif (delaytype == RELOAD)
\t\t\t\treturn 1.500;
\t\t\telse if (delaytype == RELOAD_EMP)
\t\t\t\treturn 1.850;
\t\t\telse if (delaytype == FIRE)
\t\t\t\treturn 0.066;
\t\t\tbreak;
""",
)
stats = inject_switch_case(
    stats,
    "float(float weapon) WepDef_GetWeaponBurstCount =",
    "XZIEL_RK5_BURST_COUNT",
    "\t\t// XZIEL_RK5_BURST_COUNT\n\t\tcase W_XZ_RK5:\n\t\t\treturn 3;\n",
)
stats = inject_switch_case(
    stats,
    "float(float weapon) WepDef_GetWeaponBurstTailDelay =",
    "XZIEL_RK5_BURST_TAIL",
    "\t\t// XZIEL_RK5_BURST_TAIL\n\t\tcase W_XZ_RK5:\n\t\t\treturn 0.100;\n",
)

constFalloff = "float(float weapon, float distance_units) XZIEL_WeaponDamageFalloffScale ="
falloff_start = core.find(constFalloff)
if falloff_start < 0:
    raise SystemExit("Generic XZIEL damage falloff helper must run before RK5 binding")
if "XZIEL_RK5_FALLOFF" not in core[falloff_start:]:
    body = core.find("{", falloff_start)
    if body < 0:
        raise SystemExit("Could not find XZIEL falloff helper body")
    logic = """
    // XZIEL_RK5_FALLOFF
    if (weapon == W_XZ_RK5) {
        if (distance_units <= 200)
            return 1;
        if (distance_units >= 751)
            return 0.25;
        return 1 - (((distance_units - 200) / 551) * 0.75);
    }

"""
    core = core[: body + 1] + logic + core[body + 1 :]

required = [
    "XZIEL_RK5_NAME",
    "XZIEL_RK5_FIRETYPE",
    "XZIEL_RK5_MAG",
    "XZIEL_RK5_RESERVE",
    "XZIEL_RK5_DAMAGE",
    "XZIEL_RK5_HITLOC",
    "XZIEL_RK5_DELAYS",
    "XZIEL_RK5_BURST_COUNT",
    "XZIEL_RK5_BURST_TAIL",
]
for marker in required:
    if stats.count(marker) != 1:
        raise SystemExit(f"RK5 patch marker count mismatch: {marker}")
if core.count("XZIEL_RK5_FALLOFF") != 1:
    raise SystemExit("RK5 falloff marker count mismatch")

# Hard safety boundary: this patch is logic-only.
for text in (stats, core):
    for forbidden in (
        "models/weapons/rk5",
        "sounds/weapons/rk5",
    ):
        if forbidden in text:
            raise SystemExit(f"Unexpected RK5 presentation binding: {forbidden}")

defs_path.write_text(defs, encoding="utf-8")
stats_path.write_text(stats, encoding="utf-8")
core_path.write_text(core, encoding="utf-8")
print("Applied XZIEL RK5 logic-only binding (W_CUSTOM1 / id 70).")
