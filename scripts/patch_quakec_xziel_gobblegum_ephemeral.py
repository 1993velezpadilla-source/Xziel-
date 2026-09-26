#!/usr/bin/env python3
"""Add the source-backed Ephemeral Enhancement state machine.

BO3 source authority:
scripts/zm/bgbs/_zm_bgb_ephemeral_enhancement.gsc

Semantics implemented here:
- activation is rejected while Death Machine is active;
- current weapon must have a source-verified PaP identity whose native runtime
  is explicitly ready;
- on activation, save the original active weapon/ammo state and replace only
  that weapon with its upgraded identity using fresh upgraded start ammo;
- effect duration is 60 seconds;
- if the temporary upgraded weapon is replaced/lost, clear the effect without
  recreating the original weapon;
- if the timer expires during last stand/down, defer restoration until revive;
- when restoring, preserve the BO3 anti-extra-ammo reconciliation rule;
- if the temporary upgraded weapon is not currently active, restore it in its
  current inventory slot without forcing a weapon switch.

The readiness gate keeps this code dormant while nativeRuntimeStatus is pending.
"""

from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_quakec_xziel_gobblegum_ephemeral.py <quakec-root>")

root = Path(sys.argv[1])
custom_path = root / "source/server/defs/custom.qc"
utils_path = root / "source/server/utilities/weapon_utilities.qc"
weapon_core_path = root / "source/server/weapons/weapon_core.qc"

custom = custom_path.read_text(encoding="utf-8")
utils = utils_path.read_text(encoding="utf-8")
weapon_core = weapon_core_path.read_text(encoding="utf-8")

if "// XZIEL_GOBBLEGUM_EPHEMERAL_STATE_BEGIN" not in custom:
    custom += r'''

// XZIEL_GOBBLEGUM_EPHEMERAL_STATE_BEGIN
#define XZIEL_GUM_EPHEMERAL_ENHANCEMENT 19
#define XZIEL_GUM_EPHEMERAL_DURATION_SECONDS 60
.float xziel_gum_ephemeral_active;
.float xziel_gum_ephemeral_until;
.float xziel_gum_ephemeral_original_weapon;
.float xziel_gum_ephemeral_original_magazine;
.float xziel_gum_ephemeral_original_magazine_left;
.float xziel_gum_ephemeral_original_reserve;
.float xziel_gum_ephemeral_original_tier;
.float xziel_gum_ephemeral_original_skin;
.float xziel_gum_ephemeral_original_mulekick;
.float xziel_gum_ephemeral_upgrade_weapon;
// XZIEL_GOBBLEGUM_EPHEMERAL_STATE_END
'''

if "// XZIEL_GOBBLEGUM_EPHEMERAL_RUNTIME_BEGIN" not in utils:
    utils += r'''

// XZIEL_GOBBLEGUM_EPHEMERAL_RUNTIME_BEGIN
float(entity player, float weapon_id) XZIEL_GobbleGumFindExactWeaponSlot =
{
    if (player == world || player.classname != "player")
        return -1;

    for (float i = 0; i < MAX_PLAYER_WEAPONS; i++) {
        if (player.weapons[i].weapon_id == weapon_id)
            return i;
    }

    return -1;
};

void(entity player) XZIEL_GobbleGumEphemeralClear =
{
    if (player == world)
        return;

    player.xziel_gum_ephemeral_active = false;
    player.xziel_gum_ephemeral_until = 0;
    player.xziel_gum_ephemeral_original_weapon = W_NOWEP;
    player.xziel_gum_ephemeral_original_magazine = 0;
    player.xziel_gum_ephemeral_original_magazine_left = 0;
    player.xziel_gum_ephemeral_original_reserve = 0;
    player.xziel_gum_ephemeral_original_tier = -1;
    player.xziel_gum_ephemeral_original_skin = 0;
    player.xziel_gum_ephemeral_original_mulekick = false;
    player.xziel_gum_ephemeral_upgrade_weapon = W_NOWEP;
};

float(entity player) XZIEL_GobbleGumEphemeralCanActivate =
{
    if (player == world || player.classname != "player")
        return false;

    if (player.downed || player.health <= 0)
        return false;

    if (player.xziel_gum_ephemeral_active)
        return false;

    if (XZIEL_DeathMachineActive(player))
        return false;

    if (player.xziel_gum_held_identity != XZIEL_GUM_EPHEMERAL_ENHANCEMENT)
        return false;

    float base_weapon = player.weapons[0].weapon_id;
    float upgraded_weapon = XZIEL_GetPackAPunchWeaponID(base_weapon);

    if (upgraded_weapon == W_NOWEP)
        return false;

    if (!XZIEL_PackAPunchRuntimeReady(upgraded_weapon))
        return false;

    return true;
};

float(entity player) XZIEL_GobbleGumActivateEphemeralEnhancement =
{
    if (!XZIEL_GobbleGumEphemeralCanActivate(player))
        return false;

    float base_weapon = player.weapons[0].weapon_id;
    float upgraded_weapon = XZIEL_GetPackAPunchWeaponID(base_weapon);

    player.xziel_gum_ephemeral_original_weapon = base_weapon;
    player.xziel_gum_ephemeral_original_magazine = player.weapons[0].weapon_magazine;
    player.xziel_gum_ephemeral_original_magazine_left = player.weapons[0].weapon_magazine_left;
    player.xziel_gum_ephemeral_original_reserve = player.weapons[0].weapon_reserve;
    player.xziel_gum_ephemeral_original_tier = player.weapons[0].weapon_tier;
    player.xziel_gum_ephemeral_original_skin = player.weapons[0].weapon_skin;
    player.xziel_gum_ephemeral_original_mulekick = player.weapons[0].is_mulekick_weapon;
    player.xziel_gum_ephemeral_upgrade_weapon = upgraded_weapon;
    player.xziel_gum_ephemeral_active = true;
    player.xziel_gum_ephemeral_until = time + XZIEL_GUM_EPHEMERAL_DURATION_SECONDS;

    // BO3 consumes the activated gum only after validation succeeds.
    player.xziel_gum_held_identity = 0;
    player.xziel_gum_held_uses_remaining = 0;

    // BO3 gives the temporary upgraded weapon its start ammo.
    Weapon_AssignWeapon(0, upgraded_weapon, 0, 0, 0);
    player.weapons[0].is_mulekick_weapon = player.xziel_gum_ephemeral_original_mulekick;

    return true;
};

void(entity player, float slot) XZIEL_GobbleGumEphemeralRestore =
{
    if (player == world || slot < 0 || slot >= MAX_PLAYER_WEAPONS)
        return;

    float base_weapon = player.xziel_gum_ephemeral_original_weapon;
    float upgraded_weapon = player.xziel_gum_ephemeral_upgrade_weapon;

    if (base_weapon == W_NOWEP || upgraded_weapon == W_NOWEP) {
        XZIEL_GobbleGumEphemeralClear(player);
        return;
    }

    float temporary_mag = player.weapons[slot].weapon_magazine;
    float temporary_left = player.weapons[slot].weapon_magazine_left;
    float temporary_reserve = player.weapons[slot].weapon_reserve;
    float temporary_total = temporary_mag + temporary_left + temporary_reserve;

    float final_mag = player.xziel_gum_ephemeral_original_magazine;
    float final_left = player.xziel_gum_ephemeral_original_magazine_left;
    float final_reserve = player.xziel_gum_ephemeral_original_reserve;
    float saved_total = final_mag + final_left + final_reserve;

    // BO3 rule: if the temporary upgraded weapon currently contains more ammo
    // than the original saved amount, restore no more than base start ammo.
    if (temporary_total > saved_total) {
        float start_mag = getWeaponMag(base_weapon);
        float start_left = 0;
        if (IsDualWeapon(base_weapon))
            start_left = start_mag;
        float start_reserve = getWeaponAmmo(base_weapon);
        float start_total = start_mag + start_left + start_reserve;

        final_mag = start_mag;
        final_left = start_left;
        final_reserve = start_reserve;

        // If the temporary weapon fell below base start-ammo total, preserve
        // its remaining amount without exceeding any base magazine capacity.
        if (temporary_total < start_total) {
            final_mag = temporary_mag;
            if (final_mag > start_mag)
                final_mag = start_mag;

            float remaining = temporary_total - final_mag;

            if (remaining < 0)
                remaining = 0;

            if (IsDualWeapon(base_weapon)) {
                final_left = temporary_left;
                if (final_left > start_left)
                    final_left = start_left;

                remaining -= final_left;
                if (remaining < 0)
                    remaining = 0;
            } else {
                final_left = 0;
            }

            final_reserve = remaining;
            if (final_reserve > start_reserve)
                final_reserve = start_reserve;
        }
    }

    float was_active = (slot == 0);
    float mulekick = player.xziel_gum_ephemeral_original_mulekick;
    float tier = player.xziel_gum_ephemeral_original_tier;

    // Replace only the temporary PaP entry in-place so weapon cycling performed
    // during the 60-second effect is preserved.
    player.weapons[slot].weapon_id = base_weapon;
    player.weapons[slot].weapon_magazine = final_mag;
    player.weapons[slot].weapon_magazine_left = final_left;
    player.weapons[slot].weapon_reserve = final_reserve;
    player.weapons[slot].weapon_skin = player.xziel_gum_ephemeral_original_skin;
    player.weapons[slot].weapon_tier = tier;
    player.weapons[slot].is_mulekick_weapon = mulekick;

    XZIEL_GobbleGumEphemeralClear(player);

    if (was_active)
        Weapon_SetActiveInSlot(0, false);
};

void(entity player) XZIEL_GobbleGumEphemeralTick =
{
    if (player == world || !player.xziel_gum_ephemeral_active)
        return;

    // BO3 terminates the thread on death/bled-out.
    if (player.health <= 0) {
        XZIEL_GobbleGumEphemeralClear(player);
        return;
    }

    float slot = XZIEL_GobbleGumFindExactWeaponSlot(
        player, player.xziel_gum_ephemeral_upgrade_weapon
    );

    // BO3 ends without recreating the original when the temporary upgraded
    // weapon was replaced before the timer completed.
    if (slot < 0) {
        XZIEL_GobbleGumEphemeralClear(player);
        return;
    }

    if (time < player.xziel_gum_ephemeral_until)
        return;

    // BO3 waits for player_revived if the timer expires during last stand.
    if (player.downed)
        return;

    XZIEL_GobbleGumEphemeralRestore(player, slot);
};
// XZIEL_GOBBLEGUM_EPHEMERAL_RUNTIME_END
'''

tick_marker = "// XZIEL_GOBBLEGUM_EPHEMERAL_TICK"
if tick_marker not in weapon_core:
    anchor = '''    // XZIEL_DEATH_MACHINE_STATE_TICK
    XZIEL_DeathMachineTick(self);
'''
    if anchor not in weapon_core:
        raise SystemExit("could not find Death Machine tick anchor in weapon_core.qc")
    replacement = anchor + '''
    // XZIEL_GOBBLEGUM_EPHEMERAL_TICK
    XZIEL_GobbleGumEphemeralTick(self);
'''
    weapon_core = weapon_core.replace(anchor, replacement, 1)

unique = {
    "custom": (
        custom,
        [
            "// XZIEL_GOBBLEGUM_EPHEMERAL_STATE_BEGIN",
            "// XZIEL_GOBBLEGUM_EPHEMERAL_STATE_END",
            ".float xziel_gum_ephemeral_upgrade_weapon;",
        ],
    ),
    "utils": (
        utils,
        [
            "// XZIEL_GOBBLEGUM_EPHEMERAL_RUNTIME_BEGIN",
            "// XZIEL_GOBBLEGUM_EPHEMERAL_RUNTIME_END",
            "float(entity player) XZIEL_GobbleGumEphemeralCanActivate =",
            "float(entity player) XZIEL_GobbleGumActivateEphemeralEnhancement =",
            "void(entity player, float slot) XZIEL_GobbleGumEphemeralRestore =",
            "void(entity player) XZIEL_GobbleGumEphemeralTick =",
        ],
    ),
    "weapon_core": (weapon_core, [tick_marker]),
}
for file_name, (text_value, markers) in unique.items():
    for marker in markers:
        if text_value.count(marker) != 1:
            raise SystemExit(
                f"{file_name}: unique marker/signature count mismatch for {marker}"
            )

custom_path.write_text(custom, encoding="utf-8")
utils_path.write_text(utils, encoding="utf-8")
weapon_core_path.write_text(weapon_core, encoding="utf-8")

print(
    "Applied XZIEL Ephemeral Enhancement state machine "
    "(60s, inventory-aware restore, PaP-runtime readiness gated)."
)
