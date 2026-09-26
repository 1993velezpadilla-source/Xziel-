#!/usr/bin/env python3
"""Validate XZIEL catalog against the complete BO3 prototype Zombies weapon table."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "assets/weapons/xziel_weapon_catalog_v1.json"
SNAPSHOT = ROOT / "assets/weapons/bo3_zm_prototype_weapons_v1.json"

EXPECTED_SOURCE = {
    "repository": "ate47/bo3-source",
    "ref": "main",
    "path": "gamedata/weapons/zm/zm_prototype_weapons.csv",
    "blobSha": "1700efd635d77951d64ad8feec1cfc2ed1a16e2b",
}
EXPECTED_FIELDS = 20
EXPECTED_ROWS = 41


def fail(message: str) -> None:
    raise SystemExit(f"BO3_ZM_PROTOTYPE_TABLE_FAIL: {message}")


def parse_bool(value: str):
    if value == "TRUE":
        return True
    if value == "FALSE":
        return False
    if value == "":
        return None
    fail(f"invalid boolean token {value!r}")


def parse_number(value: str):
    if value == "":
        return None
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            fail(f"invalid numeric token {value!r}")


def main() -> int:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))

    if snapshot.get("schemaVersion") != 1:
        fail("schemaVersion must be 1")
    if snapshot.get("snapshotId") != "bo3_zm_prototype_weapons_v1":
        fail("unexpected snapshotId")

    source = snapshot.get("source", {})
    for key, expected in EXPECTED_SOURCE.items():
        if source.get(key) != expected:
            fail(f"source provenance drift for {key}: {source.get(key)!r}")

    fields = snapshot.get("fieldNames", [])
    entries = snapshot.get("entries", [])
    if len(fields) != EXPECTED_FIELDS:
        fail(f"expected {EXPECTED_FIELDS} fields, got {len(fields)}")
    if snapshot.get("rowCount") != EXPECTED_ROWS or len(entries) != EXPECTED_ROWS:
        fail(f"expected {EXPECTED_ROWS} rows, got {len(entries)}")

    names = [row.get("weapon_name") for row in entries]
    if any(not name for name in names) or len(names) != len(set(names)):
        fail("weapon_name values must be non-empty and unique")

    catalog_by_id = {w["weaponId"]: w for w in catalog.get("weapons", [])}
    catalog_proto = {
        w["weaponId"]
        for w in catalog.get("weapons", [])
        if w.get("nachtPrototype", {}).get("present") is True
    }
    if catalog_proto != set(names):
        fail(
            "catalog prototype identity coverage differs from BO3 table: "
            f"missing={sorted(set(names)-catalog_proto)} "
            f"extra={sorted(catalog_proto-set(names))}"
        )

    in_box = 0
    wonder = 0
    limited = 0
    upgraded = 0

    for raw in entries:
        wid = raw["weapon_name"]
        weapon = catalog_by_id.get(wid)
        if not weapon:
            fail(f"missing catalog identity: {wid}")
        proto = weapon.get("nachtPrototype", {})

        expected = {
            "present": True,
            "sourceTable": "gamedata/weapons/zm/zm_prototype_weapons.csv",
            "upgradeId": raw.get("upgrade_name") or None,
            "inBox": parse_bool(raw.get("in_box", "")),
            "upgradeInBox": parse_bool(raw.get("upgrade_in_box", "")),
            "isLimited": parse_bool(raw.get("is_limited", "")),
            "limit": parse_number(raw.get("limit", "")),
            "class": raw.get("class") or None,
            "isWonderWeapon": parse_bool(raw.get("is_wonder_weapon", "")),
            "wallBuyAutospawn": parse_bool(raw.get("wallbuy_autospawn", "")),
        }
        if proto != expected:
            fail(f"{wid} catalog prototype metadata drift: {proto} != {expected}")

        if expected["inBox"] is True:
            in_box += 1
        if expected["isWonderWeapon"] is True:
            wonder += 1
        if expected["isLimited"] is True:
            limited += 1
        if expected["upgradeId"]:
            upgraded += 1

    if in_box != 34:
        fail(f"expected 34 prototype box entries, got {in_box}")
    if upgraded != 36:
        fail(f"expected 36 prototype upgrade identities, got {upgraded}")

    print(
        "BO3_ZM_PROTOTYPE_TABLE_OK",
        {
            "rows": len(entries),
            "fields": len(fields),
            "boxEntries": in_box,
            "upgradeIdentities": upgraded,
            "wonderFlagsTrue": wonder,
            "limitedFlagsTrue": limited,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
