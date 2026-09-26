#!/usr/bin/env python3
"""Validate the exact BO3 Nacht Disorderly Combat eligible weapon pool."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POOL = ROOT / "assets/nacht_reference/bo3_disorderly_combat_pool_v1.json"
PROTOTYPE = ROOT / "assets/weapons/bo3_zm_prototype_weapons_v1.json"
GUMS = ROOT / "assets/nacht_reference/bo3_gobblegum_catalog_v1.json"

EXPECTED_ELIGIBLE = [
    "pistol_standard",
    "ar_accurate",
    "ar_cqb",
    "ar_damage",
    "ar_longburst",
    "ar_standard",
    "ar_garand",
    "ar_stg44",
    "lmg_cqb",
    "lmg_heavy",
    "lmg_light",
    "lmg_slowfire",
    "pistol_fullauto",
    "shotgun_fullauto",
    "shotgun_precision",
    "shotgun_pump",
    "shotgun_semiauto",
    "smg_burst",
    "smg_capacity",
    "smg_fastfire",
    "smg_standard",
    "smg_versatile",
    "smg_mp40_1940",
    "smg_sten",
    "smg_ak74u",
    "lmg_rpk",
]

EXPECTED_EXPLICIT = [
    "ar_marksman",
    "launcher_standard",
    "none",
    "pistol_burst",
    "pistol_c96",
    "pistol_m1911",
    "pistol_revolver38",
    "sniper_fastbolt",
    "sniper_powerbolt",
]

PRIMARY = {
    "repository": "shiversoftdev/t7-source",
    "commit": "07cbfcd113fb5031dc717296f73b371478d4eb77",
    "path": "scripts/zm/bgbs/_zm_bgb_disorderly_combat.gsc",
    "blobSha": "1a8d0e5208b70d04d9cc4b79a77240d4f728405c",
}
EXPECTED_START = {
    "repository": "ate47/bo3-source",
    "ref": "main",
    "path": "scripts/zm/zm_prototype.gsc",
    "blobSha": "f23c1f739a30f4922c3851527a93ce1f0fc593a5",
    "rule": (
        "level.default_laststandpistol = pistol_m1911; "
        "level.start_weapon = level.default_laststandpistol"
    ),
}
EXPECTED_CORROBORATION_BLOBS = {
    "b8a3f4c25816a97acd56a4aa1ebf243b04f09a85",
    "d2a88b5d63078f2b50a0e1e47e2f3d96ce567f7a",
}


def fail(message: str) -> None:
    raise SystemExit(f"BO3_DISORDERLY_POOL_FAIL: {message}")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    pool = load(POOL)
    prototype = load(PROTOTYPE)
    gums = load(GUMS)

    if pool.get("schemaVersion") != 1:
        fail("schemaVersion must be 1")
    if pool.get("poolId") != "bo3_nacht_disorderly_combat_pool_v1":
        fail("unexpected poolId")

    primary = pool.get("sourceAuthority", {}).get("primary", {})
    if primary != PRIMARY:
        fail(f"primary source drift: {primary!r}")

    source_authority = pool.get("sourceAuthority", {})
    start_source = source_authority.get("startWeaponEvidence", {})
    if start_source != EXPECTED_START:
        fail(f"start weapon source drift: {start_source!r}")

    corroboration = source_authority.get("corroboration", [])
    corroboration_blobs = {row.get("blobSha") for row in corroboration}
    if not EXPECTED_CORROBORATION_BLOBS.issubset(corroboration_blobs):
        fail(
            "missing Disorderly corroboration blobs: "
            f"{sorted(EXPECTED_CORROBORATION_BLOBS-corroboration_blobs)}"
        )

    filter_rule = pool.get("filterRule", {})
    if filter_rule.get("explicitSourceExclusions") != EXPECTED_EXPLICIT:
        fail("explicit source exclusion list drift")
    if filter_rule.get("startWeapon") != "pistol_m1911":
        fail("Nacht Disorderly start weapon must remain pistol_m1911")
    if filter_rule.get("prototypeEligibleBeforeStartWeaponExclusion") != 27:
        fail("Disorderly pre-start-weapon eligible count drift")
    if filter_rule.get("finalEligibleAfterStartWeaponExclusion") != 26:
        fail("Disorderly final eligible count drift")
    if "MR6/pistol_standard remains eligible" not in filter_rule.get("note", ""):
        fail("MR6 eligibility clarification lost")

    semantics = pool.get("runtimeSemantics", {})
    expected_semantics = {
        "durationSeconds": 300,
        "weaponIntervalSeconds": 10,
        "warningSecondsBeforeSwitch": 5,
        "selection": (
            "randomize complete eligible array, walk sequentially, "
            "reshuffle after exhaustion, skip weapons player already has"
        ),
        "preserveInitialPackAPunchState": True,
        "preserveInitialAatState": True,
        "disableWeaponCycling": True,
        "disableOffhandWeapons": True,
        "runtimeActivationRule": (
            "Do not activate with a reduced readiness subset; the full 26-weapon "
            "eligible pool must be available to preserve BO3 probabilities and "
            "cycle semantics."
        ),
    }
    for key, value in expected_semantics.items():
        if semantics.get(key) != value:
            fail(f"runtime semantic drift for {key}: {semantics.get(key)!r}")

    eligible = [row.get("weaponId") for row in pool.get("eligible", [])]
    if eligible != EXPECTED_ELIGIBLE:
        fail(f"eligible pool drift: {eligible}")
    if len(eligible) != len(set(eligible)):
        fail("eligible pool contains duplicates")
    if "pistol_standard" not in eligible:
        fail("MR6/pistol_standard must remain eligible on Nacht")
    if "pistol_m1911" in eligible:
        fail("M1911 must remain excluded as Nacht start weapon")

    excluded_rows = pool.get("excluded", [])
    excluded = [row.get("weaponId") for row in excluded_rows]
    if len(excluded) != len(set(excluded)):
        fail("excluded pool contains duplicates")
    if set(eligible) & set(excluded):
        fail("weapon appears in both eligible and excluded pool")

    proto_ids = [row["weapon_name"] for row in prototype.get("entries", [])]
    if set(eligible) | set(excluded) != set(proto_ids):
        fail("eligible + excluded pool must cover all prototype identities")
    if len(proto_ids) != 41 or len(eligible) != 26 or len(excluded) != 15:
        fail("prototype/eligible/excluded count drift")

    proto_by = {row["weapon_name"]: row for row in prototype["entries"]}
    for row in excluded_rows:
        wid = row["weaponId"]
        reasons = set(row.get("reasons", []))
        raw = proto_by[wid]

        if wid in {"cymbal_monkey","cymbal_monkey_upgraded","frag_grenade","knife","bowie_knife"}:
            if "melee_or_grenade" not in reasons:
                fail(f"{wid} missing melee/grenade exclusion reason")
        if wid in {
            "ar_marksman","launcher_standard","pistol_burst","pistol_m1911",
            "sniper_fastbolt","sniper_powerbolt",
        } and "explicit_source_exclusion" not in reasons:
            fail(f"{wid} missing explicit-source exclusion reason")
        if raw.get("is_wonder_weapon") == "TRUE" and "wonder_weapon" not in reasons:
            fail(f"{wid} missing wonder-weapon exclusion reason")
        if wid == "pistol_m1911" and "start_weapon" not in reasons:
            fail("pistol_m1911 missing start-weapon exclusion reason")

    counts = pool.get("counts", {})
    if counts != {"prototypeRows": 41, "eligible": 26, "excluded": 15}:
        fail(f"pool count drift: {counts}")

    gum = next((row for row in gums.get("entries", []) if row.get("id") == "disorderly_combat"), None)
    if gum is None:
        fail("Disorderly Combat missing from GobbleGum catalog")
    spec = gum.get("effectSpec", {})
    primitive = gum.get("runtimePrimitive", {})
    if spec.get("exactEligiblePoolFilterStatus") != "verified":
        fail("Disorderly pool filter must be verified")
    if spec.get("eligiblePoolCount") != 26:
        fail("Disorderly eligible pool count drift in GobbleGum catalog")
    if primitive.get("fullPoolRequired") is not True:
        fail("Disorderly must require the full eligible pool")
    if primitive.get("requiredPoolCount") != 26:
        fail("Disorderly required runtime pool count drift")
    if primitive.get("activationAllowed") is not False:
        fail("Disorderly activation must remain blocked while runtime pool is incomplete")

    print(
        "BO3_DISORDERLY_POOL_OK",
        {"prototype": 41, "eligible": 26, "excluded": 15, "activationAllowed": False},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
