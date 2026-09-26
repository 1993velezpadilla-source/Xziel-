#!/usr/bin/env python3
"""Validate the complete BO3 Pack-a-Punch identity/evidence catalog.

This validator intentionally separates:
- upgrade identity truth (36/36 from the Nacht prototype table),
- BO3 statstable/interface metadata,
- attachment mapping metadata,
- ballistic gameplay stats,
- native runtime/presentation readiness.

A PaP identity is never allowed to become "gameplay ready" merely because its
_upgrade name exists.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROTOTYPE = ROOT / "assets/weapons/bo3_zm_prototype_weapons_v1.json"
PAP = ROOT / "assets/weapons/bo3_pack_a_punch_catalog_v1.json"

EXPECTED_UPGRADES = 36
EXPECTED_STATSTABLE = 30
EXPECTED_ATTACHMENTS = 26
EXPECTED_SPECIAL = 6

EXPECTED_RUNTIME_SOURCE = {
    "repository": "ate47/bo3-source",
    "path": "scripts/zm/_zm_weapons.gsc",
    "blobSha": "d336d2544b307ccf5de63fc5c29546a56a607506",
}
EXPECTED_STAT_SOURCE = {
    "repository": "ate47/bo3-source",
    "path": "gamedata/stats/zm/zm_statstable.csv",
    "blobSha": "c3f341262c495765b042aeff61400403bcfb23ef",
}
EXPECTED_ATTACHMENT_SOURCE = {
    "repository": "ate47/bo3-source",
    "path": "gamedata/weapons/common/attachmentmappingstable.csv",
    "blobSha": "22ca4036eab92f098238c6e139c9e5083824d8aa",
}

EXPECTED_NO_STATSTABLE = {
    "cymbal_monkey_upgraded",
    "ray_gun_upgraded",
    "thundergun_upgraded",
    "ar_stg44_upgraded",
    "smg_mp40_1940_upgraded",
    "raygun_mark2_upgraded",
}

EXPECTED_NO_ATTACHMENT = {
    "pistol_standard_upgraded",
    "pistol_m1911_upgraded",
    "cymbal_monkey_upgraded",
    "ray_gun_upgraded",
    "thundergun_upgraded",
    "ar_stg44_upgraded",
    "launcher_standard_upgraded",
    "smg_mp40_1940_upgraded",
    "smg_sten_upgraded",
    "raygun_mark2_upgraded",
}


def fail(message: str) -> None:
    raise SystemExit(f"BO3_PAP_CATALOG_FAIL: {message}")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def assert_source(actual: dict, expected: dict, label: str) -> None:
    for key, value in expected.items():
        if actual.get(key) != value:
            fail(f"{label} source drift for {key}: {actual.get(key)!r} != {value!r}")


def main() -> int:
    prototype = load(PROTOTYPE)
    pap = load(PAP)

    if pap.get("schemaVersion") != 1:
        fail("schemaVersion must be 1")
    if pap.get("catalogId") != "bo3_pack_a_punch_catalog_v1":
        fail("unexpected catalogId")

    authority = pap.get("sourceAuthority", {})
    assert_source(authority.get("weaponRuntime", {}), EXPECTED_RUNTIME_SOURCE, "runtime")
    assert_source(authority.get("statstable", {}), EXPECTED_STAT_SOURCE, "statstable")
    assert_source(authority.get("attachmentMapping", {}), EXPECTED_ATTACHMENT_SOURCE, "attachments")

    proto_upgrades = {
        row["weapon_name"]: row["upgrade_name"]
        for row in prototype.get("entries", [])
        if row.get("upgrade_name")
    }
    if len(proto_upgrades) != EXPECTED_UPGRADES:
        fail(f"prototype must expose {EXPECTED_UPGRADES} upgrade identities")

    variants = pap.get("variants", [])
    if len(variants) != EXPECTED_UPGRADES:
        fail(f"expected {EXPECTED_UPGRADES} PaP variants, got {len(variants)}")

    bases = [v.get("baseWeaponId") for v in variants]
    upgrades = [v.get("upgradeWeaponId") for v in variants]
    if len(bases) != len(set(bases)):
        fail("duplicate PaP base weapon identity")
    if len(upgrades) != len(set(upgrades)):
        fail("duplicate PaP upgrade identity")
    if set(bases) != set(proto_upgrades):
        fail("PaP base identity set differs from prototype table")

    stat_count = 0
    attachment_count = 0
    special_count = 0
    no_stat = set()
    no_attachment = set()

    proto_by_base = {row["weapon_name"]: row for row in prototype["entries"]}

    for row in variants:
        base = row["baseWeaponId"]
        upgrade = row["upgradeWeaponId"]
        raw = proto_by_base[base]

        if proto_upgrades[base] != upgrade:
            fail(f"{base} PaP upgrade drift: {upgrade!r} != {proto_upgrades[base]!r}")
        if row.get("identityStatus") != "verified":
            fail(f"{base} PaP identity must remain verified")

        proto = row.get("prototype", {})
        expected_proto = {
            "source": "assets/weapons/bo3_zm_prototype_weapons_v1.json",
            "inBox": raw.get("in_box", ""),
            "upgradeInBox": raw.get("upgrade_in_box", ""),
            "isLimited": raw.get("is_limited", ""),
            "limit": raw.get("limit", ""),
            "upgradeLimit": raw.get("upgrade_limit", ""),
            "isAatExempt": raw.get("is_aat_exempt", ""),
            "weaponClass": raw.get("class", ""),
            "isWonderWeapon": raw.get("is_wonder_weapon", ""),
            "forceAttachments": raw.get("force_attachments", ""),
        }
        if proto != expected_proto:
            fail(f"{base} prototype PaP metadata drift")

        stat = row.get("statstable", {})
        if stat.get("present") is True:
            stat_count += 1
            raw_row = stat.get("rawRow")
            if not isinstance(raw_row, list) or upgrade not in raw_row:
                fail(f"{upgrade} statstable row does not contain its upgrade identity")
            if stat.get("blobSha") != EXPECTED_STAT_SOURCE["blobSha"]:
                fail(f"{upgrade} statstable blob drift")
        else:
            no_stat.add(upgrade)
            if stat.get("rawRow") is not None:
                fail(f"{upgrade} absent statstable row must be null")

        att = row.get("attachmentMapping", {})
        if att.get("present") is True:
            attachment_count += 1
            raw_row = att.get("rawRow")
            if not isinstance(raw_row, list) or not raw_row or raw_row[0] != upgrade:
                fail(f"{upgrade} attachment row identity drift")
            raw_tokens = (
                raw_row[1].split()
                if len(raw_row) > 1 and isinstance(raw_row[1], str) and raw_row[1]
                else []
            )
            if att.get("attachmentTokens") != raw_tokens:
                fail(f"{upgrade} attachment token parsing drift")
            if att.get("blobSha") != EXPECTED_ATTACHMENT_SOURCE["blobSha"]:
                fail(f"{upgrade} attachment source blob drift")
        else:
            no_attachment.add(upgrade)
            if att.get("rawRow") is not None:
                fail(f"{upgrade} absent attachment row must be null")
            if att.get("attachmentTokens") != []:
                fail(f"{upgrade} absent attachment row must have no parsed tokens")

        special = row.get("specialEvidence", [])
        if special:
            special_count += 1

        if row.get("ballisticUpgradeStatsStatus") != "pending":
            fail(f"{upgrade} ballistic upgrade stats must remain pending")
        if row.get("nativeRuntimeStatus") != "pending":
            fail(f"{upgrade} native runtime must remain pending")
        if row.get("presentationStatus") != "pending":
            fail(f"{upgrade} presentation must remain pending")
        if row.get("androidStatus") != "pending":
            fail(f"{upgrade} Android status must remain pending")
        if row.get("regressionTestStatus") != "pending":
            fail(f"{upgrade} regression test must remain pending")

        blockers = row.get("blockers", [])
        required_blockers = {
            "ballistic_upgrade_stats_not_exposed_in_current_source_snapshot",
            "native_pack_a_punch_runtime_pending",
            "model_audio_animation_parity_pending",
        }
        if not required_blockers.issubset(set(blockers)):
            fail(f"{upgrade} missing required readiness blockers")

    if stat_count != EXPECTED_STATSTABLE:
        fail(f"expected {EXPECTED_STATSTABLE} statstable rows, got {stat_count}")
    if attachment_count != EXPECTED_ATTACHMENTS:
        fail(f"expected {EXPECTED_ATTACHMENTS} attachment mappings, got {attachment_count}")
    if special_count != EXPECTED_SPECIAL:
        fail(f"expected {EXPECTED_SPECIAL} special-evidence variants, got {special_count}")
    if no_stat != EXPECTED_NO_STATSTABLE:
        fail(f"unexpected statstable gaps: {sorted(no_stat)}")
    if no_attachment != EXPECTED_NO_ATTACHMENT:
        fail(f"unexpected attachment mapping gaps: {sorted(no_attachment)}")

    counts = pap.get("counts", {})
    expected_counts = {
        "upgradeIdentities": EXPECTED_UPGRADES,
        "statstableRows": EXPECTED_STATSTABLE,
        "attachmentMappingRows": EXPECTED_ATTACHMENTS,
        "specialEvidenceVariants": EXPECTED_SPECIAL,
        "ballisticUpgradeStatsReady": 0,
        "nativeRuntimeReady": 0,
    }
    if counts != expected_counts:
        fail(f"PaP counts drift: {counts} != {expected_counts}")

    semantics = pap.get("runtimeSemantics", {})
    if "level.zombie_weapons[base].upgrade" not in semantics.get("identityMapping", ""):
        fail("PaP identity mapping semantics lost")
    if "Do not synthesize" not in semantics.get("safetyRule", ""):
        fail("PaP no-synthetic-stats safety rule lost")

    print(
        "BO3_PAP_CATALOG_OK",
        {
            "upgrades": EXPECTED_UPGRADES,
            "statstable": stat_count,
            "attachments": attachment_count,
            "specialEvidence": special_count,
            "runtimeReady": 0,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
