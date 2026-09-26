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
runtime_ready_upgrades = set()
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
    if row.get("nativeRuntimeStatus") == "ready":
        runtime_ready_upgrades.add(upgrade_id)

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
            "",
            "float() XZIEL_PackAPunchMapScopeActive =",
            "{",
            "    if (strlen(mapname) < 6)",
            "        return false;",
            "    return substring(mapname, 0, 6) == \"xziel_\";",
            "};",
            "",
            "float(float weapon_id) XZIEL_PackAPunchRuntimeReady =",
            "{",
            "    switch (weapon_id) {",
        ]
    )
    for row in pairs:
        if row["upgradeWeaponId"] in runtime_ready_upgrades:
            lines.append(
                f"        case {row['upgradeDefine']}: return true;"
            )
    lines.extend(
        [
            "        default: return false;",
            "    }",
            "};",
            end,
            "",
        ]
    )
    block = "\n".join(lines)
    legacy_anchor = "float(float wep) IsPapWeapon = {"
    insert_pos = stats.find(legacy_anchor)
    if insert_pos < 0:
        raise SystemExit("could not find legacy IsPapWeapon anchor")
    stats = stats[:insert_pos] + block + "\n" + stats[insert_pos:]

if stats.count(begin) != 1 or stats.count(end) != 1:
    raise SystemExit("PaP identity map marker mismatch")

for row in pairs:
    forward = f"case {row['baseDefine']}: return {row['upgradeDefine']};"
    reverse = f"case {row['upgradeDefine']}: return {row['baseDefine']};"
    if stats.count(forward) != 1:
        raise SystemExit(f"missing PaP forward identity mapping for {row['baseWeaponId']}")
    if stats.count(reverse) != 1:
        raise SystemExit(f"missing PaP reverse identity mapping for {row['upgradeWeaponId']}")


legacy_bridge_specs = (
    (
        "// XZIEL_PAP_LEGACY_ISPAP_BRIDGE",
        "float(float wep) IsPapWeapon = {\n\n",
        """float(float wep) IsPapWeapon = {

    // XZIEL_PAP_LEGACY_ISPAP_BRIDGE
    // Only XZIEL maps opt into the extended PaP identity domain. This avoids
    // reinterpreting historical W_CUSTOM1/W_CUSTOM* aliases on legacy maps.
    if (XZIEL_PackAPunchMapScopeActive() &&
        XZIEL_IsPackAPunchIdentity(wep))
        return true;

""",
    ),
    (
        "// XZIEL_PAP_LEGACY_NONPAP_BRIDGE",
        "float(float wep)  EqualNonPapWeapon =\n{\n\n",
        """float(float wep)  EqualNonPapWeapon =
{
    // XZIEL_PAP_LEGACY_NONPAP_BRIDGE
    if (XZIEL_PackAPunchMapScopeActive() &&
        XZIEL_GetBaseWeaponIDFromPackAPunch(wep) != W_NOWEP)
        return XZIEL_GetBaseWeaponIDFromPackAPunch(wep);

""",
    ),
    (
        "// XZIEL_PAP_LEGACY_PAP_BRIDGE",
        "float(float wep)  EqualPapWeapon = \n{\n\n",
        """float(float wep)  EqualPapWeapon = 
{
    // XZIEL_PAP_LEGACY_PAP_BRIDGE
    // Identity knowledge alone is not enough to expose a weapon. The generic
    // helper only returns an XZIEL upgrade after that variant is runtime-ready.
    if (XZIEL_PackAPunchMapScopeActive() &&
        XZIEL_GetPackAPunchWeaponID(wep) != W_NOWEP &&
        XZIEL_PackAPunchRuntimeReady(XZIEL_GetPackAPunchWeaponID(wep)))
        return XZIEL_GetPackAPunchWeaponID(wep);

""",
    ),
)

for marker, anchor, replacement in legacy_bridge_specs:
    if marker not in stats:
        if anchor not in stats:
            raise SystemExit(f"could not find legacy PaP helper anchor for {marker}")
        stats = stats.replace(anchor, replacement, 1)
    if stats.count(marker) != 1:
        raise SystemExit(f"legacy PaP bridge marker mismatch: {marker}")

if stats.count("float() XZIEL_PackAPunchMapScopeActive =") != 1:
    raise SystemExit("XZIEL PaP map-scope helper signature mismatch")

stats_path.write_text(stats, encoding="utf-8")
print("Applied XZIEL Pack-a-Punch identity map: 36 base <-> upgraded pairs.")
