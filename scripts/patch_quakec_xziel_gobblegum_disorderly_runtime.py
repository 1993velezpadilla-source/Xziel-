#!/usr/bin/env python3
"""Add dormant BO3 Disorderly Combat rotation state machine.

Source-backed behavior:
- 300 second duration;
- new weapon every 10 seconds;
- five-second warning state before the next switch;
- exact 26-weapon Nacht pool from the separately validated pool backend;
- randomized no-repeat cycle, reshuffled after exhaustion;
- skip weapons the player already owns;
- preserve whether the original weapon was Pack-a-Punched;
- disable manual weapon cycling and offhand/grenade input while active;
- restore the original active weapon when the effect ends;
- pause weapon replacement/restoration while downed.

Zero-broken-reward policy:
- the exact full 26 base pool must be runtime-ready;
- if the original weapon is PaP, all 26 PaP variants must be runtime-ready;
- the AAT preservation bridge is explicitly NOT ready yet, so activation stays
  dormant even if all weapon readiness lanes later turn green.
"""

from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit(
        "usage: patch_quakec_xziel_gobblegum_disorderly_runtime.py <quakec-root>"
    )

root = Path(sys.argv[1])
custom_path = root / "source/server/defs/custom.qc"
utils_path = root / "source/server/utilities/weapon_utilities.qc"
weapon_core_path = root / "source/server/weapons/weapon_core.qc"

custom = custom_path.read_text(encoding="utf-8")
utils = utils_path.read_text(encoding="utf-8")
weapon_core = weapon_core_path.read_text(encoding="utf-8")

if "// XZIEL_GOBBLEGUM_DISORDERLY_RUNTIME_STATE_BEGIN" not in custom:
    custom += r'''

// XZIEL_GOBBLEGUM_DISORDERLY_RUNTIME_STATE_BEGIN
.float xziel_gum_disorderly_active;
.float xziel_gum_disorderly_until;
.float xziel_gum_disorderly_next_switch;
.float xziel_gum_disorderly_warning_at;
.float xziel_gum_disorderly_warning_fired;
.float xziel_gum_disorderly_used_low;
.float xziel_gum_disorderly_used_high;
.float xziel_gum_disorderly_current_temp;
.float xziel_gum_disorderly_preserve_pap;
.float xziel_gum_disorderly_original_weapon;
.float xziel_gum_disorderly_original_magazine;
.float xziel_gum_disorderly_original_magazine_left;
.float xziel_gum_disorderly_original_reserve;
.float xziel_gum_disorderly_original_tier;
.float xziel_gum_disorderly_original_skin;
.float xziel_gum_disorderly_original_mulekick;
// XZIEL_GOBBLEGUM_DISORDERLY_RUNTIME_STATE_END
'''

if "// XZIEL_GOBBLEGUM_DISORDERLY_RUNTIME_BEGIN" not in utils:
    utils += r'''

// XZIEL_GOBBLEGUM_DISORDERLY_RUNTIME_BEGIN

// AAT preservation is part of the BO3 source contract. XZIEL does not expose
// Disorderly Combat until this bridge becomes source-verified and native-ready.
float() XZIEL_GobbleGumDisorderlyAATRuntimeReady =
{
    return false;
};

float(float local_index) XZIEL_GobbleGumDisorderlyBitForLocalIndex =
{
    switch (local_index) {
        case 0: return 1;
        case 1: return 2;
        case 2: return 4;
        case 3: return 8;
        case 4: return 16;
        case 5: return 32;
        case 6: return 64;
        case 7: return 128;
        case 8: return 256;
        case 9: return 512;
        case 10: return 1024;
        case 11: return 2048;
        case 12: return 4096;
        default: return 0;
    }
};

float(entity player, float index) XZIEL_GobbleGumDisorderlyIndexUsed =
{
    if (index < 0 || index >= XZIEL_GUM_DISORDERLY_POOL_SIZE)
        return true;

    float bit;
    if (index < 13) {
        bit = XZIEL_GobbleGumDisorderlyBitForLocalIndex(index);
        return (player.xziel_gum_disorderly_used_low & bit) != 0;
    }

    bit = XZIEL_GobbleGumDisorderlyBitForLocalIndex(index - 13);
    return (player.xziel_gum_disorderly_used_high & bit) != 0;
};

void(entity player, float index) XZIEL_GobbleGumDisorderlyMarkIndexUsed =
{
    if (index < 0 || index >= XZIEL_GUM_DISORDERLY_POOL_SIZE)
        return;

    float bit;
    if (index < 13) {
        bit = XZIEL_GobbleGumDisorderlyBitForLocalIndex(index);
        player.xziel_gum_disorderly_used_low =
            player.xziel_gum_disorderly_used_low | bit;
        return;
    }

    bit = XZIEL_GobbleGumDisorderlyBitForLocalIndex(index - 13);
    player.xziel_gum_disorderly_used_high =
        player.xziel_gum_disorderly_used_high | bit;
};

void(entity player) XZIEL_GobbleGumDisorderlyResetCycle =
{
    player.xziel_gum_disorderly_used_low = 0;
    player.xziel_gum_disorderly_used_high = 0;
};

float(entity player, float base_weapon) XZIEL_GobbleGumDisorderlyOwnsBase =
{
    if (base_weapon == W_NOWEP)
        return true;

    // The BO3 implementation keeps the original weapon in inventory while an
    // extra temporary slot is active. XZIEL emulates the visible behavior by
    // replacing slot 0, so explicitly treat the saved original as still owned.
    float original_base =
        EqualNonPapWeapon(player.xziel_gum_disorderly_original_weapon);
    if (base_weapon == original_base)
        return true;

    return Weapon_PlayerHasWeapon(player, base_weapon, true) != 0;
};

void(entity player) XZIEL_GobbleGumDisorderlyConsumeUnavailable =
{
    for (float i = 0; i < XZIEL_GUM_DISORDERLY_POOL_SIZE; i++) {
        if (XZIEL_GobbleGumDisorderlyIndexUsed(player, i))
            continue;

        float base_weapon = XZIEL_GobbleGumDisorderlyWeaponAtIndex(i);
        if (XZIEL_GobbleGumDisorderlyOwnsBase(player, base_weapon))
            XZIEL_GobbleGumDisorderlyMarkIndexUsed(player, i);
    }
};

float(entity player) XZIEL_GobbleGumDisorderlyRemainingCount =
{
    float count = 0;

    for (float i = 0; i < XZIEL_GUM_DISORDERLY_POOL_SIZE; i++) {
        if (!XZIEL_GobbleGumDisorderlyIndexUsed(player, i))
            count++;
    }

    return count;
};

float(entity player) XZIEL_GobbleGumDisorderlyPickNextBase =
{
    XZIEL_GobbleGumDisorderlyConsumeUnavailable(player);

    float remaining = XZIEL_GobbleGumDisorderlyRemainingCount(player);
    if (remaining <= 0) {
        // BO3 reshuffles after exhausting the randomized array.
        XZIEL_GobbleGumDisorderlyResetCycle(player);
        XZIEL_GobbleGumDisorderlyConsumeUnavailable(player);
        remaining = XZIEL_GobbleGumDisorderlyRemainingCount(player);
    }

    if (remaining <= 0)
        return W_NOWEP;

    float target = floor(random() * remaining);
    float seen = 0;

    for (float i = 0; i < XZIEL_GUM_DISORDERLY_POOL_SIZE; i++) {
        if (XZIEL_GobbleGumDisorderlyIndexUsed(player, i))
            continue;

        if (seen == target) {
            XZIEL_GobbleGumDisorderlyMarkIndexUsed(player, i);
            return XZIEL_GobbleGumDisorderlyWeaponAtIndex(i);
        }

        seen++;
    }

    return W_NOWEP;
};

void(entity player) XZIEL_GobbleGumDisorderlyClear =
{
    if (player == world)
        return;

    player.xziel_gum_disorderly_active = false;
    player.xziel_gum_disorderly_until = 0;
    player.xziel_gum_disorderly_next_switch = 0;
    player.xziel_gum_disorderly_warning_at = 0;
    player.xziel_gum_disorderly_warning_fired = false;
    player.xziel_gum_disorderly_used_low = 0;
    player.xziel_gum_disorderly_used_high = 0;
    player.xziel_gum_disorderly_current_temp = W_NOWEP;
    player.xziel_gum_disorderly_preserve_pap = false;
    player.xziel_gum_disorderly_original_weapon = W_NOWEP;
    player.xziel_gum_disorderly_original_magazine = 0;
    player.xziel_gum_disorderly_original_magazine_left = 0;
    player.xziel_gum_disorderly_original_reserve = 0;
    player.xziel_gum_disorderly_original_tier = -1;
    player.xziel_gum_disorderly_original_skin = 0;
    player.xziel_gum_disorderly_original_mulekick = false;
};

float(entity player) XZIEL_GobbleGumDisorderlyCanActivateFull =
{
    if (!XZIEL_GobbleGumDisorderlyCanActivate(player))
        return false;

    if (player.xziel_gum_disorderly_active)
        return false;

    if (XZIEL_DeathMachineActive(player))
        return false;

    if (player.xziel_gum_ephemeral_active)
        return false;

    if (!XZIEL_GobbleGumDisorderlyAATRuntimeReady())
        return false;

    return true;
};

float(entity player) XZIEL_GobbleGumDisorderlyAdvanceWeapon =
{
    if (player == world || !player.xziel_gum_disorderly_active)
        return false;

    float base_weapon = XZIEL_GobbleGumDisorderlyPickNextBase(player);
    if (base_weapon == W_NOWEP)
        return false;

    float final_weapon = base_weapon;
    if (player.xziel_gum_disorderly_preserve_pap) {
        final_weapon = XZIEL_GetPackAPunchWeaponID(base_weapon);
        if (final_weapon == W_NOWEP ||
            !XZIEL_PackAPunchRuntimeReady(final_weapon))
            return false;
    } else if (!XZIEL_WeaponRuntimeReady(base_weapon)) {
        return false;
    }

    // Manual cycling is disabled while active, so replacing active slot 0 is
    // externally equivalent to BO3's hidden extra temporary-weapon slot while
    // staying within NZ:P's fixed three-slot storage.
    Weapon_AssignWeapon(0, final_weapon, 0, 0, 0);
    player.weapons[0].is_mulekick_weapon = false;
    player.xziel_gum_disorderly_current_temp = final_weapon;
    player.xziel_gum_disorderly_next_switch =
        time + XZIEL_GUM_DISORDERLY_SWITCH_SECONDS;
    player.xziel_gum_disorderly_warning_at =
        player.xziel_gum_disorderly_next_switch -
        XZIEL_GUM_DISORDERLY_WARNING_SECONDS;
    player.xziel_gum_disorderly_warning_fired = false;

    return true;
};

void(entity player) XZIEL_GobbleGumDisorderlyRestore =
{
    if (player == world)
        return;

    float original = player.xziel_gum_disorderly_original_weapon;
    if (original == W_NOWEP) {
        XZIEL_GobbleGumDisorderlyClear(player);
        return;
    }

    float mag = player.xziel_gum_disorderly_original_magazine;
    float left = player.xziel_gum_disorderly_original_magazine_left;
    float reserve = player.xziel_gum_disorderly_original_reserve;
    float tier = player.xziel_gum_disorderly_original_tier;
    float skin = player.xziel_gum_disorderly_original_skin;
    float mulekick = player.xziel_gum_disorderly_original_mulekick;

    player.weapons[0].weapon_id = original;
    player.weapons[0].weapon_magazine = mag;
    player.weapons[0].weapon_magazine_left = left;
    player.weapons[0].weapon_reserve = reserve;
    player.weapons[0].weapon_tier = tier;
    player.weapons[0].weapon_skin = skin;
    player.weapons[0].is_mulekick_weapon = mulekick;

    XZIEL_GobbleGumDisorderlyClear(player);
    Weapon_SetActiveInSlot(0, false);
};

float(entity player) XZIEL_GobbleGumActivateDisorderlyCombat =
{
    if (!XZIEL_GobbleGumDisorderlyCanActivateFull(player))
        return false;

    player.xziel_gum_disorderly_original_weapon =
        player.weapons[0].weapon_id;
    player.xziel_gum_disorderly_original_magazine =
        player.weapons[0].weapon_magazine;
    player.xziel_gum_disorderly_original_magazine_left =
        player.weapons[0].weapon_magazine_left;
    player.xziel_gum_disorderly_original_reserve =
        player.weapons[0].weapon_reserve;
    player.xziel_gum_disorderly_original_tier =
        player.weapons[0].weapon_tier;
    player.xziel_gum_disorderly_original_skin =
        player.weapons[0].weapon_skin;
    player.xziel_gum_disorderly_original_mulekick =
        player.weapons[0].is_mulekick_weapon;

    player.xziel_gum_disorderly_preserve_pap =
        IsPapWeapon(player.weapons[0].weapon_id);
    player.xziel_gum_disorderly_active = true;
    player.xziel_gum_disorderly_until =
        time + XZIEL_GUM_DISORDERLY_DURATION_SECONDS;
    XZIEL_GobbleGumDisorderlyResetCycle(player);

    // BO3 consumes the held time-based gum only after activation succeeds.
    player.xziel_gum_held_identity = 0;
    player.xziel_gum_held_uses_remaining = 0;

    if (!XZIEL_GobbleGumDisorderlyAdvanceWeapon(player)) {
        XZIEL_GobbleGumDisorderlyRestore(player);
        return false;
    }

    return true;
};

void(entity player) XZIEL_GobbleGumDisorderlyTick =
{
    if (player == world || !player.xziel_gum_disorderly_active)
        return;

    // BO3 waits until last stand is over before replacement/restoration work.
    if (player.downed)
        return;

    if (player.health <= 0) {
        // A bleed-out/death ends the effect without recreating inventory.
        XZIEL_GobbleGumDisorderlyClear(player);
        return;
    }

    if (time >= player.xziel_gum_disorderly_until) {
        XZIEL_GobbleGumDisorderlyRestore(player);
        return;
    }

    if (!player.xziel_gum_disorderly_warning_fired &&
        time >= player.xziel_gum_disorderly_warning_at) {
        // Presentation/audio is a separate readiness lane. This state marker
        // preserves the exact five-second warning timing without pretending
        // the BO3 sound asset is already available.
        player.xziel_gum_disorderly_warning_fired = true;
    }

    if (time >= player.xziel_gum_disorderly_next_switch) {
        if (!XZIEL_GobbleGumDisorderlyAdvanceWeapon(player))
            XZIEL_GobbleGumDisorderlyRestore(player);
    }
};
// XZIEL_GOBBLEGUM_DISORDERLY_RUNTIME_END
'''

# Tick every player frame after the existing Ephemeral tick.
tick_marker = "// XZIEL_GOBBLEGUM_DISORDERLY_RUNTIME_TICK"
if tick_marker not in weapon_core:
    anchor = '''    // XZIEL_GOBBLEGUM_EPHEMERAL_TICK
    XZIEL_GobbleGumEphemeralTick(self);
'''
    if anchor not in weapon_core:
        raise SystemExit("could not find Ephemeral tick anchor")
    weapon_core = weapon_core.replace(
        anchor,
        anchor + '''
    // XZIEL_GOBBLEGUM_DISORDERLY_RUNTIME_TICK
    XZIEL_GobbleGumDisorderlyTick(self);
''',
        1,
    )

# BO3 disables manual weapon cycling for the full Disorderly duration.
switch_marker = "// XZIEL_GOBBLEGUM_DISORDERLY_BLOCK_WEAPON_CYCLE"
if switch_marker not in weapon_core:
    anchor = '''	// Switch Button Pressed
	if (self.button4) {
'''
    if anchor not in weapon_core:
        raise SystemExit("could not find weapon-cycle input anchor")
    weapon_core = weapon_core.replace(
        anchor,
        '''	// Switch Button Pressed
	if (self.button4) {
        // XZIEL_GOBBLEGUM_DISORDERLY_BLOCK_WEAPON_CYCLE
        if (self.xziel_gum_disorderly_active) {
            // BO3 DisableWeaponCycling: consume the input and keep temp weapon.
        }
        else
''',
        1,
    )

# BO3 disables offhand weapons. NZ:P's primary grenade input is button3.
grenade_marker = "// XZIEL_GOBBLEGUM_DISORDERLY_BLOCK_OFFHAND"
if grenade_marker not in weapon_core:
    anchor = '''	// Grenade Button Pressed
	if (self.button3) {
		WeaponCore_GrenadeButtonPressed();
'''
    if anchor not in weapon_core:
        raise SystemExit("could not find grenade input anchor")
    weapon_core = weapon_core.replace(
        anchor,
        '''	// Grenade Button Pressed
	if (self.button3) {
        // XZIEL_GOBBLEGUM_DISORDERLY_BLOCK_OFFHAND
        if (!self.xziel_gum_disorderly_active)
		    WeaponCore_GrenadeButtonPressed();
''',
        1,
    )

# Secondary grenade / Betty-related impulses are offhand as well.
impulse_marker = "// XZIEL_GOBBLEGUM_DISORDERLY_BLOCK_OFFHAND_IMPULSE"
if impulse_marker not in weapon_core:
    anchor = '''void () Impulse_Functions =
{
	if (!self.impulse)
		return;
'''
    if anchor not in weapon_core:
        raise SystemExit("could not find Impulse_Functions anchor")
    weapon_core = weapon_core.replace(
        anchor,
        '''void () Impulse_Functions =
{
	if (!self.impulse)
		return;

    // XZIEL_GOBBLEGUM_DISORDERLY_BLOCK_OFFHAND_IMPULSE
    if (self.xziel_gum_disorderly_active &&
        (self.impulse == 25 || self.impulse == 33)) {
        self.impulse = 0;
        return;
    }
''',
        1,
    )

unique = {
    "custom": (
        custom,
        [
            "// XZIEL_GOBBLEGUM_DISORDERLY_RUNTIME_STATE_BEGIN",
            "// XZIEL_GOBBLEGUM_DISORDERLY_RUNTIME_STATE_END",
            ".float xziel_gum_disorderly_original_weapon;",
        ],
    ),
    "utils": (
        utils,
        [
            "// XZIEL_GOBBLEGUM_DISORDERLY_RUNTIME_BEGIN",
            "// XZIEL_GOBBLEGUM_DISORDERLY_RUNTIME_END",
            "float() XZIEL_GobbleGumDisorderlyAATRuntimeReady =",
            "float(entity player) XZIEL_GobbleGumDisorderlyCanActivateFull =",
            "float(entity player) XZIEL_GobbleGumActivateDisorderlyCombat =",
            "void(entity player) XZIEL_GobbleGumDisorderlyTick =",
            "void(entity player) XZIEL_GobbleGumDisorderlyRestore =",
        ],
    ),
    "weapon_core": (
        weapon_core,
        [
            tick_marker,
            switch_marker,
            grenade_marker,
            impulse_marker,
        ],
    ),
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
    "Applied XZIEL Disorderly Combat dormant runtime: 300s, 10s rotation, "
    "5s warning state, no-repeat pool cycles, input lock, restore; "
    "activation remains blocked by AAT readiness."
)
