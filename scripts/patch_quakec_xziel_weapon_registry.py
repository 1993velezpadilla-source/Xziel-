#!/usr/bin/env python3
"""Reserve stable QuakeC IDs and .mb2 tokens for the full XZIEL weapon catalog.

This patch is identity-only. It registers the global catalog identities plus
dedicated Pack-a-Punch upgrade identities. It deliberately does not make pending
weapons playable. Runtime readiness is controlled separately by the completion
contract and the generated Mystery Box runtime pool.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_quakec_xziel_weapon_registry.py <quakec-root>")

quakec_root = Path(sys.argv[1])
repo_root = Path(__file__).resolve().parents[1]
registry_path = repo_root / "assets/weapons/xziel_weapon_id_registry_v1.json"
catalog_path = repo_root / "assets/weapons/xziel_weapon_catalog_v1.json"
contract_path = repo_root / "assets/nacht_reference/bo3_nacht_completion_contract_v1.json"
registry = json.loads(registry_path.read_text(encoding="utf-8"))
catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
contract = json.loads(contract_path.read_text(encoding="utf-8"))
entries = registry.get("entries", [])
upgrade_entries = registry.get("upgradeEntries", [])
all_entries = entries + upgrade_entries

runtime_required_lanes = (
    "source_stats",
    "behavior_spec",
    "native_gameplay",
    "model",
    "audio",
    "recoil",
    "spread",
    "animations",
    "penetration",
    "android_exposure",
    "regression_test",
)
complete_states = {"ready", "not_applicable"}
catalog_by_id = {row["weaponId"]: row for row in catalog.get("weapons", [])}
contract_weapons = contract.get("weapons", {})
runtime_ready_weapon_ids = set()
for e in entries:
    wid = e["weaponId"]
    weapon = catalog_by_id.get(wid)
    tracked = contract_weapons.get(wid)
    if weapon is None or tracked is None:
        raise SystemExit(f"weapon readiness source missing for {wid}")
    lanes = tracked.get("lanes", {})
    if (
        weapon.get("nativeBindingStatus") == "ready"
        and all(lanes.get(lane) in complete_states for lane in runtime_required_lanes)
    ):
        runtime_ready_weapon_ids.add(wid)

defs_path = quakec_root / "source/shared/shared_defs.qc"
stats_path = quakec_root / "source/shared/weapon_stats.qc"
defs = defs_path.read_text(encoding="utf-8")
stats = stats_path.read_text(encoding="utf-8")

if len(entries) != registry.get("validation", {}).get("expectedCatalogCount"):
    raise SystemExit("weapon ID registry count mismatch")
if len(upgrade_entries) != registry.get("validation", {}).get("expectedDedicatedPackAPunchIdCount"):
    raise SystemExit("Pack-a-Punch ID registry count mismatch")

ids = [int(e["quakecId"]) for e in all_entries]
defines = [e["quakecDefine"] for e in all_entries]
tokens = [e["mboxToken"] for e in all_entries]
if len(ids) != len(set(ids)):
    raise SystemExit("duplicate QuakeC IDs in XZIEL registry")
if len(defines) != len(set(defines)):
    raise SystemExit("duplicate QuakeC defines in XZIEL registry")
if len(tokens) != len(set(tokens)):
    raise SystemExit("duplicate .mb2 tokens in XZIEL registry")

block_start = "// XZIEL_FULL_WEAPON_ID_REGISTRY_BEGIN"
block_end = "// XZIEL_FULL_WEAPON_ID_REGISTRY_END"

if block_start not in defs:
    anchor = "#define W_CUSTOM4 \t   73"
    pos = defs.find(anchor)
    if pos < 0:
        raise SystemExit("could not find W_CUSTOM4 anchor")
    line_end = defs.find("\n", pos)
    if line_end < 0:
        raise SystemExit("could not find end of W_CUSTOM4 line")

    lines = ["", block_start]
    for e in all_entries:
        lines.append(f"#define {e['quakecDefine']:<36} {int(e['quakecId'])}")
    lines.append(block_end)
    block = "\n".join(lines) + "\n"
    defs = defs[: line_end + 1] + block + defs[line_end + 1 :]

# Inject all stable Mystery Box token -> ID mappings before the native default.
if "XZIEL_FULL_MBOX_NAME_REGISTRY_BEGIN" not in stats:
    func = "float(string weapon) WepDef_GetWeaponIDFromName ="
    start = stats.find(func)
    if start < 0:
        raise SystemExit("could not find WepDef_GetWeaponIDFromName")
    default_anchor = '\t\tdefault: return W_NOWEP;'
    default_pos = stats.find(default_anchor, start)
    if default_pos < 0:
        raise SystemExit("could not find WepDef_GetWeaponIDFromName default")

    lines = [
        "\t\t// XZIEL_FULL_MBOX_NAME_REGISTRY_BEGIN",
    ]
    for e in all_entries:
        lines.append(
            f'\t\tcase "{e["mboxToken"]}": return {e["quakecDefine"]};'
        )
    lines.append("\t\t// XZIEL_FULL_MBOX_NAME_REGISTRY_END")
    insertion = "\n".join(lines) + "\n"
    stats = stats[:default_pos] + insertion + stats[default_pos:]

# Compile the same zero-broken-reward readiness policy used by higher-level
# systems. Identity existence alone never makes a weapon safe to grant.
ready_begin = "// XZIEL_WEAPON_RUNTIME_READINESS_BEGIN"
ready_end = "// XZIEL_WEAPON_RUNTIME_READINESS_END"
if ready_begin not in stats:
    lines = [
        "",
        ready_begin,
        "float(float weapon_id) XZIEL_WeaponRuntimeReady =",
        "{",
        "    switch (weapon_id) {",
    ]
    for e in entries:
        if e["weaponId"] in runtime_ready_weapon_ids:
            lines.append(f"        case {e['quakecDefine']}: return true;")
    lines.extend(
        [
            "        default: return false;",
            "    }",
            "};",
            ready_end,
            "",
        ]
    )
    stats += "\n".join(lines)

# Registry must be exact and idempotent.
if defs.count(block_start) != 1 or defs.count(block_end) != 1:
    raise SystemExit("XZIEL weapon registry marker mismatch")
if stats.count("XZIEL_FULL_MBOX_NAME_REGISTRY_BEGIN") != 1:
    raise SystemExit("XZIEL .mb2 registry marker mismatch")
if stats.count(ready_begin) != 1 or stats.count(ready_end) != 1:
    raise SystemExit("XZIEL weapon runtime-readiness marker mismatch")
if stats.count("float(float weapon_id) XZIEL_WeaponRuntimeReady =") != 1:
    raise SystemExit("XZIEL weapon runtime-readiness helper signature mismatch")

for e in all_entries:
    define_line = f"#define {e['quakecDefine']:<36} {int(e['quakecId'])}"
    if define_line not in defs:
        identity = e.get("weaponId", e.get("upgradeWeaponId"))
        raise SystemExit(f"missing QuakeC ID definition: {identity}")
    case_line = f'case "{e["mboxToken"]}": return {e["quakecDefine"]};'
    if case_line not in stats:
        identity = e.get("weaponId", e.get("upgradeWeaponId"))
        raise SystemExit(f"missing .mb2 token mapping: {identity}")

defs_path.write_text(defs, encoding="utf-8")
stats_path.write_text(stats, encoding="utf-8")
print(
    "Applied XZIEL weapon ID registry: "
    f"{len(entries)} catalog identities + "
    f"{len(upgrade_entries)} dedicated Pack-a-Punch identities; "
    f"{len(runtime_ready_weapon_ids)} catalog weapons runtime-ready."
)
