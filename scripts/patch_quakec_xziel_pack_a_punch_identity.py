#!/usr/bin/env python3
"""Compile the source-verified BO3 Pack-a-Punch identity map into QuakeC.

This patch is identity-only. It provides deterministic base <-> upgraded ID
mapping for all 36 Nacht prototype upgrade pairs so GobbleGum and future PaP
runtime code can resolve the correct identity without guessing.

It deliberately does NOT:
- change damage/ammo;
- grant upgraded weapons;
- expose unfinished PaP variants to the player;
- mark native Pack-a-Punch runtime complete.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_quakec_xziel_pack_a_punch_identity.py <quakec-root>")

quakec_root = Path(sys.argv[1])
repo_root = Path(__file__).resolve().parents[1]
registry = json.loads(
    (repo_root / "assets/weapons/xziel_weapon_id_registry_v1.json").read_text(
        encoding="utf-8"
    )
)
pap = json.loads(
    (repo_root / "assets/weapons/bo3_pack_a_punch_catalog_v1.json").read_text(
        encoding="utf-8"
    )
)

base_by_id = {row["weaponId"]: row for row in registry.get("entries", [])}
upgrade_by_id = {
    row["upgradeWeaponId"]: row for row in registry.get("upgradeEntries", [])
}

pairs = []
for row in pap.get("variants", []):
    base_id = row["baseWeaponId"]
    upgrade_id = row["upgradeWeaponId"]
    base = base_by_id.get(base_id)
    if base is None:
        raise SystemExit(f"missing base registry identity for {base_id}")

    upgrade = upgrade_by_id.get(upgrade_id) or base_by_id.get(upgrade_id)
    if upgrade is None:
        raise SystemExit(f"missing upgraded registry identity for {upgrade_id}")

    pairs.append(
        {
            "baseWeaponId": base_id,
            "upgradeWeaponId": upgrade_id,
            "baseDefine": base["quakecDefine"],
            "upgradeDefine": upgrade["quakecDefine"],
        }
    )

if len(pairs) != 36:
    raise SystemExit(f"expected 36 PaP identity pairs, got {len(pairs)}")

base_defines = [row["baseDefine"] for row in pairs]
upgrade_defines = [row["upgradeDefine"] for row in pairs]
if len(base_defines) != len(set(base_defines)):
    raise SystemExit("duplicate base define in PaP identity map")
if len(upgrade_defines) != len(set(upgrade_defines)):
    raise SystemExit("duplicate upgraded define in PaP identity map")

stats_path = quakec_root / "source/shared/weapon_stats.qc"
stats = stats_path.read_text(encoding="utf-8")

begin = "// XZIEL_PACK_A_PUNCH_IDENTITY_MAP_BEGIN"
end = "// XZIEL_PACK_A_PUNCH_IDENTITY_MAP_END"

if begin not in stats:
    lines = [
        "",
        begin,
        "float(float weapon_id) XZIEL_GetPackAPunchWeaponID =",
        "{",
        "    switch (weapon_id) {",
    ]
    for row in pairs:
        lines.append(
            f"        case {row['baseDefine']}: return {row['upgradeDefine']};"
        )
    lines.extend(
        [
            "        default: return W_NOWEP;",
            "    }",
            "};",
            "",
            "float(float weapon_id) XZIEL_GetBaseWeaponIDFromPackAPunch =",
            "{",
            "    switch (weapon_id) {",
        ]
    )
    for row in pairs:
        lines.append(
            f"        case {row['upgradeDefine']}: return {row['baseDefine']};"
        )
    lines.extend(
        [
            "        default: return W_NOWEP;",
            "    }",
            "};",
            "",
            "float(float weapon_id) XZIEL_HasPackAPunchIdentity =",
            "{",
            "    return XZIEL_GetPackAPunchWeaponID(weapon_id) != W_NOWEP;",
            "};",
            "",
            "float(float weapon_id) XZIEL_IsPackAPunchIdentity =",
            "{",
            "    return XZIEL_GetBaseWeaponIDFromPackAPunch(weapon_id) != W_NOWEP;",
            "};",
            end,
            "",
        ]
    )
    stats += "\n".join(lines)

if stats.count(begin) != 1 or stats.count(end) != 1:
    raise SystemExit("PaP identity map marker mismatch")

for row in pairs:
    forward = f"case {row['baseDefine']}: return {row['upgradeDefine']};"
    reverse = f"case {row['upgradeDefine']}: return {row['baseDefine']};"
    if stats.count(forward) != 1:
        raise SystemExit(f"missing PaP forward identity mapping for {row['baseWeaponId']}")
    if stats.count(reverse) != 1:
        raise SystemExit(f"missing PaP reverse identity mapping for {row['upgradeWeaponId']}")

stats_path.write_text(stats, encoding="utf-8")
print("Applied XZIEL Pack-a-Punch identity map: 36 base <-> upgraded pairs.")
