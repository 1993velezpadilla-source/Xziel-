#!/usr/bin/env python3
"""Make NZ:P's Mystery Box large enough and safe enough for XZIEL's full catalog.

Key properties:
- raises the fixed box table from 28 to 64 entries;
- supports sparse allow-lists without auto-filling legacy weapons;
- prevents unbounded recursive selection when no eligible weapon exists;
- refuses a purchase instead of charging the player when the runtime-ready
  allow-list is empty.

This patch changes capacity/control flow only. It does not mark any XZIEL
weapon as gameplay-ready.
"""

from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_quakec_xziel_mystery_box_capacity.py <quakec-root>")

root = Path(sys.argv[1])
custom_path = root / "source/server/defs/custom.qc"
box_path = root / "source/server/entities/mystery_box.qc"

custom = custom_path.read_text(encoding="utf-8")
box = box_path.read_text(encoding="utf-8")

if "XZIEL_FULL_BOX_CAPACITY" not in custom:
    old = "#define MAX_BOX_WEAPONS \t\t28"
    if old not in custom:
        raise SystemExit("could not find MAX_BOX_WEAPONS=28")
    custom = custom.replace(
        old,
        "// XZIEL_FULL_BOX_CAPACITY\n"
        "#define XZIEL_LEGACY_BOX_WEAPON_COUNT 28\n"
        "#define MAX_BOX_WEAPONS \t\t64",
        1,
    )

old_random = """float(entity user) MBOX_GetRandomBoxWeapon =
{
    float weapon_index = rint((random() * (MAX_BOX_WEAPONS - 1)));
    float weapon_id = mystery_box_weapons[weapon_index].weapon_id;
    float weapon_allowed = mystery_box_weapons[weapon_index].allowed && 
\t\t\t\t\t\t\t!mystery_box_weapons[weapon_index].already_obtained;

    if (weapon_allowed == true && MBOX_CanPlayerReceiveWeapon(user, weapon_id))
        return weapon_id;
    else
        return MBOX_GetRandomBoxWeapon(user);
};
"""

new_random = """float(entity user) MBOX_GetRandomBoxWeapon =
{
    // XZIEL_BOUNDED_BOX_SELECTION
    // Count eligible entries first. The upstream recursive retry path can
    // recurse forever when a generated allow-list has zero ready weapons.
    float eligible_count = 0;
    for (float i = 0; i < MAX_BOX_WEAPONS; i++) {
        float weapon_id = mystery_box_weapons[i].weapon_id;
        if (mystery_box_weapons[i].allowed &&
            weapon_id != W_NOWEP &&
            !mystery_box_weapons[i].already_obtained &&
            MBOX_CanPlayerReceiveWeapon(user, weapon_id)) {
            eligible_count++;
        }
    }

    if (eligible_count <= 0)
        return W_NOWEP;

    float target = floor(random() * eligible_count);
    if (target >= eligible_count)
        target = eligible_count - 1;

    float seen = 0;
    for (float i = 0; i < MAX_BOX_WEAPONS; i++) {
        float weapon_id = mystery_box_weapons[i].weapon_id;
        if (mystery_box_weapons[i].allowed &&
            weapon_id != W_NOWEP &&
            !mystery_box_weapons[i].already_obtained &&
            MBOX_CanPlayerReceiveWeapon(user, weapon_id)) {
            if (seen == target)
                return weapon_id;
            seen++;
        }
    }

    return W_NOWEP;
};
"""

if "XZIEL_BOUNDED_BOX_SELECTION" not in box:
    if old_random not in box:
        raise SystemExit("could not find upstream MBOX_GetRandomBoxWeapon body")
    box = box.replace(old_random, new_random, 1)

if "XZIEL_MBOX_PARSE_BOUND" not in box:
    anchor = """        } else if (parsing_state == 1) {
            // Get the weapon ID from it's name.
"""
    if anchor not in box:
        raise SystemExit("could not find .mb2 parser weapon-state anchor")
    replacement = """        } else if (parsing_state == 1) {
            // XZIEL_MBOX_PARSE_BOUND
            if (weapons_parsed >= MAX_BOX_WEAPONS)
                error("MBOX_ParseMB2File: Too many weapons for Mystery Box registry");

            // Get the weapon ID from it's name.
"""
    box = box.replace(anchor, replacement, 1)

old_fill = """    // At this point, the file has been parsed with all of the
    // allowed/denied weapons, now we have to automatically
    // fill in the rest for the opposite list.
    for (float i = weapons_parsed; i < MAX_BOX_WEAPONS; i++) {
        // We need to pick an ID to assign that hasn't already
        // been used.
        weapon_id = MBOX_GetUnusedWeaponID();
        mystery_box_weapons[i].weapon_id = weapon_id;
\t\tmystery_box_weapons[i].allowed = MBOX_WeaponAllowedByDefault(is_allow_not_deny, weapon_id);
    }
"""

new_fill = """    // XZIEL_SPARSE_BOX_ALLOWLIST
    // For allow-lists, unmentioned slots stay explicitly disabled. This lets
    // XZIEL ship a readiness-gated pool without NZ:P silently adding legacy
    // weapons that are not part of the BO3 target.
    //
    // Deny-lists keep legacy behavior for the original 28-weapon domain only;
    // the expanded XZIEL capacity stays disabled unless named explicitly.
    for (float i = weapons_parsed; i < MAX_BOX_WEAPONS; i++) {
        if (is_allow_not_deny) {
            mystery_box_weapons[i].weapon_id = W_NOWEP;
            mystery_box_weapons[i].allowed = false;
            mystery_box_weapons[i].rarity = -1;
        } else if (i < XZIEL_LEGACY_BOX_WEAPON_COUNT) {
            weapon_id = MBOX_GetUnusedWeaponID();
            mystery_box_weapons[i].weapon_id = weapon_id;
            mystery_box_weapons[i].allowed = MBOX_WeaponAllowedByDefault(is_allow_not_deny, weapon_id);
            mystery_box_weapons[i].rarity = -1;
        } else {
            mystery_box_weapons[i].weapon_id = W_NOWEP;
            mystery_box_weapons[i].allowed = false;
            mystery_box_weapons[i].rarity = -1;
        }
    }
"""

if "XZIEL_SPARSE_BOX_ALLOWLIST" not in box:
    if old_fill not in box:
        raise SystemExit("could not find upstream .mb2 opposite-list filler")
    box = box.replace(old_fill, new_fill, 1)

if "XZIEL_EMPTY_BOX_GUARD" not in box:
    anchor = """\t\t\tif (other.points >= mystery_box_cost)
\t\t\t{\t\t\t\t\t
\t\t\t\tSound_PlaySound(self, mystery_box_open_sound, SOUND_TYPE_ENV_MUSIC, SOUND_PRIORITY_PLAYALWAYS);
"""
    if anchor not in box:
        raise SystemExit("could not find Mystery Box purchase anchor")
    replacement = """\t\t\tif (other.points >= mystery_box_cost)
\t\t\t{
                // XZIEL_EMPTY_BOX_GUARD
                // Never charge the player or open the box when every catalog
                // entry is still blocked by readiness gates.
                if (MBOX_GetRandomBoxWeapon(other) == W_NOWEP) {
                    centerprint(other, "Mystery Box weapon pool is not ready.");
                    Sound_PlaySound(other, "sounds/misc/denybuy.wav", SOUND_TYPE_ENV_CHING, SOUND_PRIORITY_PLAYALWAYS);
                    return;
                }

\t\t\t\tSound_PlaySound(self, mystery_box_open_sound, SOUND_TYPE_ENV_MUSIC, SOUND_PRIORITY_PLAYALWAYS);
"""
    box = box.replace(anchor, replacement, 1)

required = [
    "XZIEL_FULL_BOX_CAPACITY",
    "XZIEL_BOUNDED_BOX_SELECTION",
    "XZIEL_MBOX_PARSE_BOUND",
    "XZIEL_SPARSE_BOX_ALLOWLIST",
    "XZIEL_EMPTY_BOX_GUARD",
]
combined = custom + "\n" + box
for marker in required:
    if combined.count(marker) != 1:
        raise SystemExit(f"marker count mismatch: {marker}")

custom_path.write_text(custom, encoding="utf-8")
box_path.write_text(box, encoding="utf-8")
print("Applied XZIEL Mystery Box capacity/readiness safety patch (64 slots).")
