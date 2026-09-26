#!/usr/bin/env python3
"""Validate the committed BO3 weaponfile source snapshot against XZIEL catalog.

The snapshot preserves source rows verbatim. It is deliberately stricter about
provenance than gameplay readiness:
- every catalog entry with sourceWeaponFile must have exactly one source row;
- Zombies rows and MP-reference-only rows must never be conflated;
- raw fields remain strings so source values are not silently reinterpreted;
- source coverage never promotes native gameplay readiness by itself.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "assets/weapons/xziel_weapon_catalog_v1.json"
SNAPSHOT = ROOT / "assets/weapons/bo3_weapon_source_stats_v1.json"

EXPECTED_SOURCE = {
    "repository": "luqmaan/cod-charts",
    "commit": "ca12bc436332e4f8518facfd84d1e1b81d0415a0",
    "path": "src/data/raw_weapons.csv",
    "blobSha": "246d1e0e298955e458d958a5f8f5b76a2f011044",
}
EXPECTED_RAW_FIELD_COUNT = 249


def fail(message: str) -> None:
    raise SystemExit(f"BO3_WEAPON_SOURCE_STATS_FAIL: {message}")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    catalog = load(CATALOG)
    snapshot = load(SNAPSHOT)

    if snapshot.get("schemaVersion") != 1:
        fail("schemaVersion must be 1")
    if snapshot.get("snapshotId") != "bo3_weapon_source_stats_v1":
        fail("unexpected snapshotId")
    if snapshot.get("scope") != "raw_weaponfile_metadata_snapshot":
        fail("unexpected snapshot scope")

    source = snapshot.get("source", {})
    for key, expected in EXPECTED_SOURCE.items():
        if source.get(key) != expected:
            fail(f"source provenance drift for {key}: {source.get(key)!r}")

    policy = snapshot.get("interpretationPolicy", {})
    if policy.get("preserveRawValues") is not True:
        fail("raw source values must remain preserved")
    if policy.get("mpRowsAreNotZombiesAuthority") is not True:
        fail("MP source rows must never be treated as Zombies authority")
    if policy.get("startAmmoAndMaxAmmoSemanticConversion") != (
        "unresolved_do_not_treat_as_reserve_without_semantic_proof"
    ):
        fail("startAmmo/maxAmmo interpretation policy drift")
    if policy.get("multishotSemantics") != (
        "preserve_raw_until_exact_model_is_verified"
    ):
        fail("multishot interpretation policy drift")

    weapons = catalog.get("weapons", [])
    catalog_by_id = {w["weaponId"]: w for w in weapons}
    expected = [w for w in weapons if w.get("sourceWeaponFile")]

    entries = snapshot.get("entries", [])
    if not isinstance(entries, list):
        fail("entries must be a list")
    ids = [e.get("weaponId") for e in entries]
    if len(ids) != len(set(ids)):
        fail("duplicate weaponId in snapshot")
    if set(ids) != {w["weaponId"] for w in expected}:
        fail("snapshot coverage does not match catalog sourceWeaponFile coverage")

    zm_count = 0
    mp_count = 0
    raw_field_counts = set()

    for entry in entries:
        wid = entry["weaponId"]
        weapon = catalog_by_id[wid]
        if entry.get("displayName") != weapon.get("displayName"):
            fail(f"displayName drift for {wid}")
        if entry.get("sourceWeaponFile") != weapon.get("sourceWeaponFile"):
            fail(f"sourceWeaponFile drift for {wid}")

        expected_zm = weapon.get("zombiesStatsAvailable") is True
        expected_scope = (
            "zombies_weaponfile" if expected_zm
            else "multiplayer_reference_only"
        )
        if entry.get("authorityScope") != expected_scope:
            fail(
                f"authorityScope drift for {wid}: "
                f"{entry.get('authorityScope')!r} != {expected_scope!r}"
            )
        if entry.get("zombiesGameplayAuthority") is not expected_zm:
            fail(f"zombiesGameplayAuthority drift for {wid}")

        raw = entry.get("raw")
        if not isinstance(raw, dict):
            fail(f"raw source row missing for {wid}")
        raw_field_counts.add(len(raw))
        if len(raw) != EXPECTED_RAW_FIELD_COUNT:
            fail(
                f"{wid} raw field count {len(raw)} "
                f"!= {EXPECTED_RAW_FIELD_COUNT}"
            )
        if raw.get("WEAPONFILE") != weapon.get("sourceWeaponFile"):
            fail(f"raw WEAPONFILE mismatch for {wid}")
        if raw.get("displayName") != weapon.get("displayName"):
            fail(f"raw displayName mismatch for {wid}")
        if any(not isinstance(v, str) for v in raw.values()):
            fail(f"{wid} contains retyped/non-string raw source values")

        if expected_zm:
            zm_count += 1
            if not weapon["sourceWeaponFile"].endswith("_zm"):
                fail(f"Zombies-authoritative source does not end in _zm: {wid}")
        else:
            mp_count += 1
            if weapon["sourceWeaponFile"].endswith("_zm"):
                fail(f"MP-reference-only row unexpectedly uses _zm: {wid}")

    counts = snapshot.get("counts", {})
    expected_counts = {
        "catalogWeapons": len(weapons),
        "catalogWeaponsWithSourceWeaponFile": len(entries),
        "zombiesWeaponfileRows": zm_count,
        "multiplayerReferenceOnlyRows": mp_count,
    }
    if counts != expected_counts:
        fail(f"snapshot counts drift: {counts} != {expected_counts}")

    if len(entries) != 36:
        fail(f"expected 36 source-matched catalog weapons, got {len(entries)}")
    if zm_count != 26:
        fail(f"expected 26 Zombies-authoritative rows, got {zm_count}")
    if mp_count != 10:
        fail(f"expected 10 MP-reference-only rows, got {mp_count}")
    if raw_field_counts != {EXPECTED_RAW_FIELD_COUNT}:
        fail(f"raw field-width drift: {raw_field_counts}")

    print(
        "BO3_WEAPON_SOURCE_STATS_OK",
        {
            "catalogWeapons": len(weapons),
            "sourceRows": len(entries),
            "zombiesRows": zm_count,
            "mpReferenceRows": mp_count,
            "rawFieldsPerRow": EXPECTED_RAW_FIELD_COUNT,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
