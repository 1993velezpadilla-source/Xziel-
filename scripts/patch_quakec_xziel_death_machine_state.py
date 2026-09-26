#!/usr/bin/env python3
"""Add BO3 Death Machine state/timer and confirmed interaction restrictions.

This is intentionally state-only. It does NOT hook the Death Machine power-up
pickup or assign the Death Machine weapon yet, because the exact Zombies damage
formula, firing presentation, model/audio/animation and restoration path are
still separately gated.

Implemented from BO3 behavior evidence:
- 30 second duration state;
- weapon-switch cancels the remaining state;
- purchasing / Mystery Box / Perk / Pack-a-Punch interactions are blocked;
- barricade repair is blocked;
- manual teammate revive is blocked.

Door/debris behavior is intentionally left untouched until BO3-specific parity
is verified.
"""

from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_quakec_xziel_death_machine_state.py <quakec-root>")

root = Path(sys.argv[1])

custom_path = root / "source/server/defs/custom.qc"
weapon_utils_path = root / "source/server/utilities/weapon_utilities.qc"
wall_path = root / "source/server/entities/wall_weapon.qc"
mbox_path = root / "source/server/entities/mystery_box.qc"
perk_path = root / "source/server/entities/perk_a_cola.qc"
pap_path = root / "source/server/entities/pack_a_punch.qc"
window_path = root / "source/server/entities/window.qc"
last_stand_path = root / "source/server/player/last_stand.qc"
weapon_core_path = root / "source/server/weapons/weapon_core.qc"
damage_path = root / "source/server/damage.qc"

custom = custom_path.read_text(encoding="utf-8")
weapon_utils = weapon_utils_path.read_text(encoding="utf-8")
wall = wall_path.read_text(encoding="utf-8")
mbox = mbox_path.read_text(encoding="utf-8")
perk = perk_path.read_text(encoding="utf-8")
pap = pap_path.read_text(encoding="utf-8")
window = window_path.read_text(encoding="utf-8")
last_stand = last_stand_path.read_text(encoding="utf-8")
weapon_core = weapon_core_path.read_text(encoding="utf-8")
damage = damage_path.read_text(encoding="utf-8")

if "// XZIEL_DEATH_MACHINE_STATE_FIELDS_BEGIN" not in custom:
    custom += r'''

// XZIEL_DEATH_MACHINE_STATE_FIELDS_BEGIN
.float xziel_dm_active;
.float xziel_dm_until;
.float xziel_dm_backup_weapon_id;
.float xziel_dm_backup_magazine;
.float xziel_dm_backup_magazine_left;
.float xziel_dm_backup_reserve;
.float xziel_dm_backup_tier;
.float xziel_dm_backup_skin;
// XZIEL_DEATH_MACHINE_STATE_FIELDS_END
'''

if "// XZIEL_DEATH_MACHINE_STATE_RUNTIME_BEGIN" not in weapon_utils:
    weapon_utils += r'''

// XZIEL_DEATH_MACHINE_STATE_RUNTIME_BEGIN
#define XZIEL_DEATH_MACHINE_DURATION_SECONDS 30

void(entity player) XZIEL_DeathMachineClearState =
{
    if (player == world)
        return;

    player.xziel_dm_active = false;
    player.xziel_dm_until = 0;
};

float(entity player) XZIEL_DeathMachineActive =
{
    if (player == world || player.classname != "player")
        return false;

    if (!player.xziel_dm_active)
        return false;

    if (player.xziel_dm_until <= time) {
        XZIEL_DeathMachineClearState(player);
        return false;
    }

    return true;
};

float(entity player) XZIEL_DeathMachineInteractionBlocked =
{
    return XZIEL_DeathMachineActive(player);
};

// State-only entrypoint. This deliberately saves the current active-slot weapon
// but does not replace it yet. The real power-up pickup must not call this until
// W_XZ_SPECIAL_DEATH_MACHINE has complete weapon/presentation parity.
float(entity player) XZIEL_DeathMachineBeginStateOnly =
{
    if (player == world || player.classname != "player" || player.downed)
        return false;

    // BO3 refresh behavior: a second pickup while active raises remaining time
    // back to 30 seconds if it had fallen below 30; it never shortens a longer
    // override duration.
    if (XZIEL_DeathMachineActive(player)) {
        if (player.xziel_dm_until < time + XZIEL_DEATH_MACHINE_DURATION_SECONDS)
            player.xziel_dm_until = time + XZIEL_DEATH_MACHINE_DURATION_SECONDS;
        return true;
    }

    player.xziel_dm_backup_weapon_id = player.weapons[0].weapon_id;
    player.xziel_dm_backup_magazine = player.weapons[0].weapon_magazine;
    player.xziel_dm_backup_magazine_left = player.weapons[0].weapon_magazine_left;
    player.xziel_dm_backup_reserve = player.weapons[0].weapon_reserve;
    player.xziel_dm_backup_tier = player.weapons[0].weapon_tier;
    player.xziel_dm_backup_skin = player.weapons[0].weapon_skin;

    player.xziel_dm_active = true;
    player.xziel_dm_until = time + XZIEL_DEATH_MACHINE_DURATION_SECONDS;
    return true;
};

// BO3 weapon switch cancels the remaining Death Machine power-up duration.
// State-only builds simply clear the state; full weapon restoration will be
// enabled together with the actual Death Machine weapon binding.
void(entity player) XZIEL_DeathMachineCancelStateOnly =
{
    if (!XZIEL_DeathMachineActive(player))
        return;

    XZIEL_DeathMachineClearState(player);
};

void(entity player) XZIEL_DeathMachineTick =
{
    if (player == world || !player.xziel_dm_active)
        return;

    if (player.downed || player.health <= 0) {
        XZIEL_DeathMachineClearState(player);
        return;
    }

    if (player.xziel_dm_until <= time)
        XZIEL_DeathMachineClearState(player);
};

// Exact BO3 source formula from _zm_powerup_weapon_minigun.gsc:
// base damage + 34%-75% of the victim's CURRENT health for zombies/dogs.
// The helper is dormant until the actual Death Machine weapon binding is used.
float(entity victim, entity attacker, float base_damage) XZIEL_DeathMachineAdjustDamage =
{
    if (victim == world || attacker == world || attacker.classname != "player")
        return base_damage;

    if (attacker.weapons[0].weapon_id != W_XZ_SPECIAL_DEATH_MACHINE)
        return base_damage;

    if (victim.classname != "ai_zombie" && victim.classname != "ai_dog")
        return base_damage;

    float health_fraction = 0.34 + (random() * 0.41);
    return base_damage + (victim.health * health_fraction);
};
// XZIEL_DEATH_MACHINE_STATE_RUNTIME_END
'''

def inject_once(text: str, anchor: str, insertion: str, marker: str) -> str:
    if marker in text:
        return text
    if anchor not in text:
        raise SystemExit(f"missing anchor for {marker}")
    return text.replace(anchor, insertion, 1)

wall = inject_once(
    wall,
    '''	if (other.classname != "player" || other.downed || other.isBuying || (map_compatibility_mode != MAP_COMPAT_BETA && !PlayerIsLooking(other, self))) {
		return;
	}
''',
    '''	if (other.classname != "player" || other.downed || other.isBuying || (map_compatibility_mode != MAP_COMPAT_BETA && !PlayerIsLooking(other, self))) {
		return;
	}

    // XZIEL_DEATH_MACHINE_BLOCK_WALLBUY
    if (XZIEL_DeathMachineInteractionBlocked(other))
        return;
''',
    "XZIEL_DEATH_MACHINE_BLOCK_WALLBUY",
)

mbox = inject_once(
    mbox,
    '''	if (other.classname != "player" || other.downed)
		return;
''',
    '''	if (other.classname != "player" || other.downed)
		return;

    // XZIEL_DEATH_MACHINE_BLOCK_MBOX
    if (XZIEL_DeathMachineInteractionBlocked(other))
        return;
''',
    "XZIEL_DEATH_MACHINE_BLOCK_MBOX",
)

perk = inject_once(
    perk,
    '''	if (other.classname != "player" || other.downed || other.isBuying == true || !PlayerIsLooking(other, self))
		return;
''',
    '''	if (other.classname != "player" || other.downed || other.isBuying == true || !PlayerIsLooking(other, self))
		return;

    // XZIEL_DEATH_MACHINE_BLOCK_PERK
    if (XZIEL_DeathMachineInteractionBlocked(other))
        return;
''',
    "XZIEL_DEATH_MACHINE_BLOCK_PERK",
)

pap = inject_once(
    pap,
    '''	if (other.classname != "player" || other.downed || !PlayerIsLooking(other, self) || game_modifier_can_packapunch == false) {
		return;
	}
''',
    '''	if (other.classname != "player" || other.downed || !PlayerIsLooking(other, self) || game_modifier_can_packapunch == false) {
		return;
	}

    // XZIEL_DEATH_MACHINE_BLOCK_PAP
    if (XZIEL_DeathMachineInteractionBlocked(other))
        return;
''',
    "XZIEL_DEATH_MACHINE_BLOCK_PAP",
)

window = inject_once(
    window,
    '''void() window_touch =
{
	if (self.owner)
		return;
''',
    '''void() window_touch =
{
	if (self.owner)
		return;

    // XZIEL_DEATH_MACHINE_BLOCK_BARRICADE
    if (other.classname == "player" && XZIEL_DeathMachineInteractionBlocked(other))
        return;
''',
    "XZIEL_DEATH_MACHINE_BLOCK_BARRICADE",
)

last_stand = inject_once(
    last_stand,
    '''    if (other.classname != "player" || other == self.owner)
        return;
''',
    '''    if (other.classname != "player" || other == self.owner)
        return;

    // XZIEL_DEATH_MACHINE_BLOCK_REVIVE
    if (XZIEL_DeathMachineInteractionBlocked(other))
        return;
''',
    "XZIEL_DEATH_MACHINE_BLOCK_REVIVE",
)

weapon_core = inject_once(
    weapon_core,
    '''	// Call to the client to do some update
	// checks specific to them.
	CheckPlayer();
''',
    '''	// Call to the client to do some update
	// checks specific to them.
	CheckPlayer();

    // XZIEL_DEATH_MACHINE_STATE_TICK
    XZIEL_DeathMachineTick(self);
''',
    "XZIEL_DEATH_MACHINE_STATE_TICK",
)

weapon_core = inject_once(
    weapon_core,
    '''	// Switch Button Pressed
	if (self.button4) {
		W_PutOut();
	} else {
''',
    '''	// Switch Button Pressed
	if (self.button4) {
        // XZIEL_DEATH_MACHINE_SWITCH_CANCEL
        if (XZIEL_DeathMachineActive(self))
            XZIEL_DeathMachineCancelStateOnly(self);
        else
		    W_PutOut();
	} else {
''',
    "XZIEL_DEATH_MACHINE_SWITCH_CANCEL",
)

damage = inject_once(
    damage,
    '''void(entity victim, entity attacker, float damage, float d_style) DamageHandler = {
''',
    '''void(entity victim, entity attacker, float damage, float d_style) DamageHandler = {
    // XZIEL_DEATH_MACHINE_DAMAGE_HOOK
    damage = XZIEL_DeathMachineAdjustDamage(victim, attacker, damage);
''',
    "XZIEL_DEATH_MACHINE_DAMAGE_HOOK",
)

unique_markers = {
    "custom": (
        custom,
        [
            "// XZIEL_DEATH_MACHINE_STATE_FIELDS_BEGIN",
            "// XZIEL_DEATH_MACHINE_STATE_FIELDS_END",
            ".float xziel_dm_until;",
        ],
    ),
    "weapon_utils": (
        weapon_utils,
        [
            "// XZIEL_DEATH_MACHINE_STATE_RUNTIME_BEGIN",
            "// XZIEL_DEATH_MACHINE_STATE_RUNTIME_END",
            "float(entity player) XZIEL_DeathMachineActive =",
            "float(entity player) XZIEL_DeathMachineBeginStateOnly =",
            "void(entity player) XZIEL_DeathMachineCancelStateOnly =",
            "void(entity player) XZIEL_DeathMachineTick =",
            "float(entity victim, entity attacker, float base_damage) XZIEL_DeathMachineAdjustDamage =",
        ],
    ),
    "wall": (wall, ["// XZIEL_DEATH_MACHINE_BLOCK_WALLBUY"]),
    "mbox": (mbox, ["// XZIEL_DEATH_MACHINE_BLOCK_MBOX"]),
    "perk": (perk, ["// XZIEL_DEATH_MACHINE_BLOCK_PERK"]),
    "pap": (pap, ["// XZIEL_DEATH_MACHINE_BLOCK_PAP"]),
    "window": (window, ["// XZIEL_DEATH_MACHINE_BLOCK_BARRICADE"]),
    "last_stand": (last_stand, ["// XZIEL_DEATH_MACHINE_BLOCK_REVIVE"]),
    "weapon_core": (
        weapon_core,
        [
            "// XZIEL_DEATH_MACHINE_STATE_TICK",
            "// XZIEL_DEATH_MACHINE_SWITCH_CANCEL",
        ],
    ),
    "damage": (damage, ["// XZIEL_DEATH_MACHINE_DAMAGE_HOOK"]),
}
for file_name, (text_value, markers) in unique_markers.items():
    for marker in markers:
        if text_value.count(marker) != 1:
            raise SystemExit(f"{file_name}: unique marker/signature count mismatch for {marker}")

custom_path.write_text(custom, encoding="utf-8")
weapon_utils_path.write_text(weapon_utils, encoding="utf-8")
wall_path.write_text(wall, encoding="utf-8")
mbox_path.write_text(mbox, encoding="utf-8")
perk_path.write_text(perk, encoding="utf-8")
pap_path.write_text(pap, encoding="utf-8")
window_path.write_text(window, encoding="utf-8")
last_stand_path.write_text(last_stand, encoding="utf-8")
weapon_core_path.write_text(weapon_core, encoding="utf-8")
damage_path.write_text(damage, encoding="utf-8")

print(
    "Applied XZIEL BO3 Death Machine state-only runtime: "
    "30s timer/refresh, down cleanup, switch-cancel, interaction gates, exact BO3 percent-health damage hook."
)
