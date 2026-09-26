#!/usr/bin/env python3
"""Validate source provenance coverage for every XZIEL weapon identity."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "assets/weapons/xziel_weapon_catalog_v1.json"
STATS = ROOT / "assets/weapons/bo3_weapon_source_stats_v1.json"
PROTOTYPE = ROOT / "assets/weapons/bo3_zm_prototype_weapons_v1.json"
COVERAGE = ROOT / "assets/weapons/bo3_weapon_source_coverage_v1.json"

EXPECTED_CATALOG = 52
EXPECTED_ANY_SOURCE = 52
EXPECTED_ZM_WEAPONFILE_STATS = 26
EXPECTED_NON_ZM_STATS_REFS = 10
EXPECTED_NO_SOURCE = 0


def fail(message: str) -> None:
    raise SystemExit(f"BO3_WEAPON_SOURCE_COVERAGE_FAIL: {message}")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    catalog = load(CATALOG)
    stats = load(STATS)
    prototype = load(PROTOTYPE)
    matrix = load(COVERAGE)

    if matrix.get("schemaVersion") != 1:
        fail("schemaVersion must be 1")
    if matrix.get("matrixId") != "bo3_weapon_source_coverage_v1":
        fail("unexpected matrixId")

    weapons = catalog.get("weapons", [])
    entries = matrix.get("entries", [])
    if len(weapons) != EXPECTED_CATALOG or len(entries) != EXPECTED_CATALOG:
        fail(f"expected {EXPECTED_CATALOG} catalog/coverage rows")

    catalog_by_id = {w["weaponId"]: w for w in weapons}
    coverage_by_id = {e["weaponId"]: e for e in entries}
    if set(catalog_by_id) != set(coverage_by_id):
        fail("coverage identity set differs from weapon catalog")

    stat_by_id = {e["weaponId"]: e for e in stats.get("entries", [])}
    proto_by_id = {e["weapon_name"]: e for e in prototype.get("entries", [])}

    any_source = 0
    zm_identity_behavior = 0
    zm_stats = 0
    non_zm_refs = 0
    no_source = 0

    for wid, weapon in catalog_by_id.items():
        row = coverage_by_id[wid]
        if row.get("displayName") != weapon.get("displayName"):
            fail(f"displayName drift for {wid}")
        if row.get("kind") != weapon.get("kind"):
            fail(f"kind drift for {wid}")
        if row.get("category") != weapon.get("category"):
            fail(f"category drift for {wid}")
        if row.get("mysteryBoxEligible") is not weapon.get("mysteryBoxEligible"):
            fail(f"Mystery Box eligibility drift for {wid}")

        sources = row.get("sources", [])
        if not isinstance(sources, list):
            fail(f"sources must be a list for {wid}")

        source_types = [s.get("type") for s in sources]
        stats_row = stat_by_id.get(wid)
        proto_row = proto_by_id.get(wid)

        if stats_row:
            if source_types.count("raw_weaponfile_row") != 1:
                fail(f"{wid} must have exactly one raw_weaponfile_row source")
            src = next(s for s in sources if s.get("type") == "raw_weaponfile_row")
            if src.get("authorityScope") != stats_row.get("authorityScope"):
                fail(f"raw stats authority drift for {wid}")
            if src.get("sourceWeaponFile") != stats_row.get("sourceWeaponFile"):
                fail(f"raw sourceWeaponFile drift for {wid}")
        elif "raw_weaponfile_row" in source_types:
            fail(f"{wid} has orphan raw_weaponfile_row source")

        if proto_row:
            if source_types.count("bo3_zm_prototype_table") != 1:
                fail(f"{wid} must have exactly one prototype-table source")
            src = next(s for s in sources if s.get("type") == "bo3_zm_prototype_table")
            if src.get("weaponName") != wid:
                fail(f"prototype source identity drift for {wid}")
            if src.get("upgradeName") != (proto_row.get("upgrade_name") or None):
                fail(f"prototype upgrade identity drift for {wid}")
        elif "bo3_zm_prototype_table" in source_types:
            fail(f"{wid} has orphan prototype-table source")

        if wid == "special_death_machine":
            scripts = [s for s in sources if s.get("type") == "bo3_zm_runtime_scripts"]
            if len(scripts) != 1:
                fail("Death Machine must have one BO3 Zombies runtime script source")
            src = scripts[0]
            if src.get("implementationBlobSha") != (
                "9d3f0cbe0d1dd9ac72289cad9531d91a46eccaf8"
            ):
                fail("Death Machine implementation source blob drift")
            if src.get("genericBlobSha") != (
                "8965a32e1d9f426f94f24e83c095fda8b9c00512"
            ):
                fail("Death Machine generic source blob drift")
        elif "bo3_zm_runtime_scripts" in source_types:
            fail(f"unexpected Zombies runtime script source for {wid}")

        coverage = row.get("sourceCoverage", {})
        expected_any = bool(sources)
        expected_zm_stats = (
            stats_row is not None
            and stats_row.get("authorityScope") == "zombies_weaponfile"
        )
        expected_non_zm_ref = (
            stats_row is not None
            and stats_row.get("authorityScope") != "zombies_weaponfile"
        )
        expected_zm_identity = proto_row is not None or wid == "special_death_machine"

        expected_flags = {
            "anySource": expected_any,
            "zombiesIdentityOrBehavior": expected_zm_identity,
            "zombiesWeaponfileStats": expected_zm_stats,
            "nonZombiesStatsReference": expected_non_zm_ref,
        }
        if coverage != expected_flags:
            fail(f"coverage flags drift for {wid}: {coverage} != {expected_flags}")

        blockers = row.get("blockers", [])
        if not expected_zm_stats and "zombies_weaponfile_stats_not_yet_available" not in blockers:
            fail(f"{wid} missing Zombies-stats blocker")
        if expected_zm_stats and "zombies_weaponfile_stats_not_yet_available" in blockers:
            fail(f"{wid} has stale Zombies-stats blocker")
        expected_native = f"native_binding_{weapon.get('nativeBindingStatus')}"
        if weapon.get("nativeBindingStatus") != "ready":
            if expected_native not in blockers:
                fail(f"{wid} missing native readiness blocker")
        elif any(b.startswith("native_binding_") for b in blockers):
            fail(f"{wid} has stale native readiness blocker")

        any_source += int(expected_any)
        zm_identity_behavior += int(expected_zm_identity)
        zm_stats += int(expected_zm_stats)
        non_zm_refs += int(expected_non_zm_ref)
        no_source += int(not expected_any)

    counts = matrix.get("counts", {})
    expected_counts = {
        "catalogWeapons": EXPECTED_CATALOG,
        "anySource": any_source,
        "zombiesIdentityOrBehavior": zm_identity_behavior,
        "zombiesWeaponfileStats": zm_stats,
        "nonZombiesStatsReference": non_zm_refs,
        "noSource": no_source,
    }
    if counts != expected_counts:
        fail(f"matrix counts drift: {counts} != {expected_counts}")

    if any_source != EXPECTED_ANY_SOURCE:
        fail(f"expected source evidence for all {EXPECTED_ANY_SOURCE} identities")
    if zm_stats != EXPECTED_ZM_WEAPONFILE_STATS:
        fail(f"expected {EXPECTED_ZM_WEAPONFILE_STATS} Zombies weaponfile rows")
    if non_zm_refs != EXPECTED_NON_ZM_STATS_REFS:
        fail(f"expected {EXPECTED_NON_ZM_STATS_REFS} non-Zombies stat references")
    if no_source != EXPECTED_NO_SOURCE:
        fail(f"no-source identities remain: {no_source}")

    print(
        "BO3_WEAPON_SOURCE_COVERAGE_OK",
        {
            "catalog": EXPECTED_CATALOG,
            "anySource": any_source,
            "zombiesIdentityOrBehavior": zm_identity_behavior,
            "zombiesWeaponfileStats": zm_stats,
            "nonZombiesStatsReference": non_zm_refs,
            "noSource": no_source,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
