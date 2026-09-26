#!/usr/bin/env python3
"""Compile the exact BO3 Nacht Disorderly Combat pool and readiness gate.

This is intentionally an eligibility backend, not the 300-second rotation
state machine. It proves the exact 26-weapon pool in QuakeC and blocks
activation until the complete pool is native-runtime ready. If the player
starts Disorderly with a PaP weapon, all corresponding PaP variants must also
be runtime-ready so XZIEL never substitutes a reduced/biased pool.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_quakec_xziel_gobblegum_disorderly.py <quakec-root>")

root = Path(sys.argv[1])
repo_root = Path(__file__).resolve().parents[1]

pool = json.loads(
    (repo_root / "assets/nacht_reference/bo3_disorderly_combat_pool_v1.json").read_text(
        encoding="utf-8"
    )
)
registry = json.loads(
    (repo_root / "assets/weapons/xziel_weapon_id_registry_v1.json").read_text(
        encoding="utf-8"
    )
)

registry_by_id = {row["weaponId"]: row for row in registry.get("entries", [])}
eligible = pool.get("eligible", [])
if len(eligible) != 26:
    raise SystemExit(f"expected 26 Disorderly Combat pool entries, got {len(eligible)}")

mapped = []
for index, row in enumerate(eligible):
    wid = row["weaponId"]
    reg = registry_by_id.get(wid)
    if reg is None:
        raise SystemExit(f"Disorderly Combat weapon missing XZIEL registry ID: {wid}")
    mapped.append(
        {
            "index": index,
            "weaponId": wid,
            "quakecDefine": reg["quakecDefine"],
        }
    )

custom_path = root / "source/server/defs/custom.qc"
utils_path = root / "source/server/utilities/weapon_utilities.qc"
custom = custom_path.read_text(encoding="utf-8")
utils = utils_path.read_text(encoding="utf-8")

if "// XZIEL_GOBBLEGUM_DISORDERLY_STATE_BEGIN" not in custom:
    custom += r'''

// XZIEL_GOBBLEGUM_DISORDERLY_STATE_BEGIN
#define XZIEL_GUM_DISORDERLY_COMBAT 18
#define XZIEL_GUM_DISORDERLY_POOL_SIZE 26
#define XZIEL_GUM_DISORDERLY_DURATION_SECONDS 300
#define XZIEL_GUM_DISORDERLY_SWITCH_SECONDS 10
#define XZIEL_GUM_DISORDERLY_WARNING_SECONDS 5
// XZIEL_GOBBLEGUM_DISORDERLY_STATE_END
'''

begin = "// XZIEL_GOBBLEGUM_DISORDERLY_POOL_BEGIN"
end = "// XZIEL_GOBBLEGUM_DISORDERLY_POOL_END"

if begin not in utils:
    lines = [
        "",
        begin,
        "float(float index) XZIEL_GobbleGumDisorderlyWeaponAtIndex =",
        "{",
        "    switch (index) {",
    ]
    for row in mapped:
        lines.append(
            f"        case {row['index']}: return {row['quakecDefine']};"
        )
    lines.extend(
        [
            "        default: return W_NOWEP;",
            "    }",
            "};",
            "",
            "float() XZIEL_GobbleGumDisorderlyReadyBaseCount =",
            "{",
            "    float ready = 0;",
            "    for (float i = 0; i < XZIEL_GUM_DISORDERLY_POOL_SIZE; i++) {",
            "        float weapon_id = XZIEL_GobbleGumDisorderlyWeaponAtIndex(i);",
            "        if (weapon_id != W_NOWEP && XZIEL_WeaponRuntimeReady(weapon_id))",
            "            ready++;",
            "    }",
            "    return ready;",
            "};",
            "",
            "float() XZIEL_GobbleGumDisorderlyReadyPapCount =",
            "{",
            "    float ready = 0;",
            "    for (float i = 0; i < XZIEL_GUM_DISORDERLY_POOL_SIZE; i++) {",
            "        float base_id = XZIEL_GobbleGumDisorderlyWeaponAtIndex(i);",
            "        float upgraded_id = XZIEL_GetPackAPunchWeaponID(base_id);",
            "        if (base_id != W_NOWEP &&",
            "            XZIEL_WeaponRuntimeReady(base_id) &&",
            "            upgraded_id != W_NOWEP &&",
            "            XZIEL_PackAPunchRuntimeReady(upgraded_id))",
            "            ready++;",
            "    }",
            "    return ready;",
            "};",
            "",
            "float(float preserve_pap) XZIEL_GobbleGumDisorderlyPoolRuntimeReady =",
            "{",
            "    if (XZIEL_GobbleGumDisorderlyReadyBaseCount() != XZIEL_GUM_DISORDERLY_POOL_SIZE)",
            "        return false;",
            "",
            "    if (preserve_pap &&",
            "        XZIEL_GobbleGumDisorderlyReadyPapCount() != XZIEL_GUM_DISORDERLY_POOL_SIZE)",
            "        return false;",
            "",
            "    return true;",
            "};",
            "",
            "float(entity player) XZIEL_GobbleGumDisorderlyCanActivate =",
            "{",
            "    if (player == world || player.classname != \"player\")",
            "        return false;",
            "    if (player.downed || player.health <= 0)",
            "        return false;",
            "    if (player.xziel_gum_held_identity != XZIEL_GUM_DISORDERLY_COMBAT)",
            "        return false;",
            "",
            "    float preserve_pap = IsPapWeapon(player.weapons[0].weapon_id);",
            "    return XZIEL_GobbleGumDisorderlyPoolRuntimeReady(preserve_pap);",
            "};",
            end,
            "",
        ]
    )
    utils += "\n".join(lines)

if utils.count(begin) != 1 or utils.count(end) != 1:
    raise SystemExit("Disorderly Combat pool marker mismatch")
for signature in (
    "float(float index) XZIEL_GobbleGumDisorderlyWeaponAtIndex =",
    "float() XZIEL_GobbleGumDisorderlyReadyBaseCount =",
    "float() XZIEL_GobbleGumDisorderlyReadyPapCount =",
    "float(float preserve_pap) XZIEL_GobbleGumDisorderlyPoolRuntimeReady =",
    "float(entity player) XZIEL_GobbleGumDisorderlyCanActivate =",
):
    if utils.count(signature) != 1:
        raise SystemExit(f"Disorderly Combat signature mismatch: {signature}")

for row in mapped:
    line = f"case {row['index']}: return {row['quakecDefine']};"
    if utils.count(line) != 1:
        raise SystemExit(f"missing Disorderly Combat compiled pool entry: {row['weaponId']}")

custom_path.write_text(custom, encoding="utf-8")
utils_path.write_text(utils, encoding="utf-8")
print(
    "Applied XZIEL Disorderly Combat exact pool backend: "
    "26 identities, full-pool readiness gate, activation currently dormant."
)
