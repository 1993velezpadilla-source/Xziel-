#!/usr/bin/env python3
"""Reserve stable QuakeC IDs and .mb2 tokens for the full XZIEL weapon catalog.

This patch is identity-only. It deliberately does not make pending weapons
playable. Runtime readiness is controlled separately by the completion contract
and the generated Mystery Box runtime pool.
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
registry = json.loads(registry_path.read_text(encoding="utf-8"))
entries = registry.get("entries", [])

defs_path = quakec_root / "source/shared/shared_defs.qc"
stats_path = quakec_root / "source/shared/weapon_stats.qc"
defs = defs_path.read_text(encoding="utf-8")
stats = stats_path.read_text(encoding="utf-8")

if len(entries) != registry.get("validation", {}).get("expectedCatalogCount"):
    raise SystemExit("weapon ID registry count mismatch")

ids = [int(e["quakecId"]) for e in entries]
defines = [e["quakecDefine"] for e in entries]
tokens = [e["mboxToken"] for e in entries]
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
    for e in entries:
        lines.append(f"#define {e['quakecDefine']:<28} {int(e['quakecId'])}")
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
    for e in entries:
        lines.append(
            f'\t\tcase "{e["mboxToken"]}": return {e["quakecDefine"]};'
        )
    lines.append("\t\t// XZIEL_FULL_MBOX_NAME_REGISTRY_END")
    insertion = "\n".join(lines) + "\n"
    stats = stats[:default_pos] + insertion + stats[default_pos:]

# Registry must be exact and idempotent.
if defs.count(block_start) != 1 or defs.count(block_end) != 1:
    raise SystemExit("XZIEL weapon registry marker mismatch")
if stats.count("XZIEL_FULL_MBOX_NAME_REGISTRY_BEGIN") != 1:
    raise SystemExit("XZIEL .mb2 registry marker mismatch")

for e in entries:
    define_line = f"#define {e['quakecDefine']:<28} {int(e['quakecId'])}"
    if define_line not in defs:
        raise SystemExit(f"missing QuakeC ID definition: {e['weaponId']}")
    case_line = f'case "{e["mboxToken"]}": return {e["quakecDefine"]};'
    if case_line not in stats:
        raise SystemExit(f"missing .mb2 token mapping: {e['weaponId']}")

defs_path.write_text(defs, encoding="utf-8")
stats_path.write_text(stats, encoding="utf-8")
print(f"Applied XZIEL full weapon ID registry: {len(entries)} identities.")
